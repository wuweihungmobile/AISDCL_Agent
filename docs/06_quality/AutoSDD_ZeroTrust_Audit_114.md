# AutoSDD_ZeroTrust_Audit_114 — 軌道① 終輪四方零信任審查證據（improving_114）

> 體例：範本〈📤 本輪輸出〉第 2 件（`AutoSDD_ZeroTrust_Audit_{{N}}.md`，improving_114 起首次實證；不冠 `CrossPlatform_R` 前綴，帳本時鐘維持 211）。計畫書＝`docs/04_planning/AutoSDD_improving_114.md`，逐條處置表住該檔 §5。四面鏡皆 Sonnet 唯讀鏡、主控（Fable 5.1）為提案者不投票；findings 依 DEF-200-090 教訓先落本檔再進修復。〈二〉為四份交件逐字保全（以本檔為唯一落地；原檔住 session scratchpad、不隨 repo 走），各鏡的 P 級與修法以其自述為準，主控處置見計畫書 §5。

## 〈一〉角色、範圍與判決

| 鏡 | 範圍 | VERDICT | P≤2 |
|---|---|---|---|
| QA 零信任鏡 | 全變更集（101 列歸格完整性、§16.3 算術、禁字、E501 鎖變異自證、棘輪算術、五條守門親跑）；二審＝驗修復 | CONDITIONAL → 二審 APPROVE | 一審 F-01／F-02／F-03（皆「文字宣稱強於實況」，同批處置）；二審 P1／P2 無，P3 N-01～N-07 同批改字、P4 N-08～N-12 登記（原文 §7） |
| Architect 鏡 | 終點設計閉合性、同輪第二列、仍在走的機器時鐘、決策記錄形態、範本互斥、五永動源復發路徑 | CONDITIONAL | ARCH-01（審查閉環無嚴重度終止條件＝輪內迴圈；同批處置） |
| SA 鏡 | PRD §16.2 的 ➖ 33 列與 📎 8 列逐列核（依據座標存在、無安全／合規／財務要求被悄悄丟掉） | APPROVE | 無（P3 SA-01～SA-11 同批處置） |
| SD 鏡 | PRD §16.2 的 ⏸ 31 列現況與症狀、19 處 v2.1.17 註記座標、E501 退役碼 | APPROVE | 無（P3 SD-01～SD-06 同批處置） |

## 〈二〉四方 findings 原文（逐字保全，各以 ```` 圍住以免被文件掃描器當成本檔的宣稱）

### 二-1 QA 零信任鏡

````text
# QA 零信任複審鏡（唯讀）— 軌道① 終輪 improving_114 變更集 findings

- 審查者：QA 零信任複審鏡（Sonnet 5.5，唯讀）｜日期：2026-10-10｜基準：HEAD＝origin/main＝`cec520baa895597664896206322369755816744a`
- 變更集（`git status --short` 現查）：10 個 tracked 修改＋1 個 untracked 新檔 `docs/04_planning/AutoSDD_improving_114.md`。

## 0. 判決

**VERDICT: CONDITIONAL**

- P1：無。
- P2：F-01、F-02、F-03（三條皆為「宣稱與檔案／規則不符」的文字或揭露層問題，修法都不需要改程式碼；修完即可 APPROVE）。
- P3：11 條（P3-01～P3-11）；P4：7 條（P4-01～P4-07）。
- 通過的主體（逐項證據見 §5、§6 與 §7 附錄）：101 列母體對帳、§16.3 三個數字、PRD 既有條文零字更動、E501 反向鎖有牙、棘輪重釘算術、cec520ba 雲端對帳、五條機械守門全綠。

## 0.1 審查範圍與誠實劃界（先講我沒做什麼）

- 全程唯讀：repo 零寫入（我寫的檔只有 scratchpad 內的 `qa114_*`／本檔）；未做任何 git 寫入操作、未起背景任務、未打任何網路端點（`gh run list` 讀 GitHub API 例外，任務書允許）。
- 沒跑根層全套（`run_root_unittests.py`）、沒跑 AutoClaude／AISDLC_SDD 全套。我單跑過的模組與單檔：`test_subprocess_encoding_hygiene`（整模組與 `-k TestRootToolsLintPolicy`）、`test_adr_xplat001_c1c2_lock`、`test_doc_loc_baseline_freshness_r60`、`test_context_budget_guard -k Prd`、`test_defect_id_reference_integrity`、`test_check_script_parity`、`test_doc_env_prefix_platform_parity_r60`、`test_negative_existence_claims_r82`、`test_check_pytest_baseline_sites`、`test_mac_readiness_r82`、`test_block_destructive_git_r83`（皆 OK），以及 AutoClaude 單檔 `tests/test_r100_boot_self_check.py`（`42 passed`，以 `-o addopts="" -p no:cacheprovider` 跑）。
- 我**沒有**重判 `[SA 判讀]` 18 列（⏸ 6／➖ 10／📎 2）的四選一歸格結論；我只驗：結構（101／72 列）、算術、⏸ 症狀的可觀測性與禁字、約 50 項事實座標抽查。improving_114 §7「`[SA 判讀]` 的列未經第二雙眼」仍然為真，不得因本鏡改寫成「已覆核」。
- improving_114.md 目前是 untracked，而 `check_handoff_carriers` 只掃 tracked 載體；我另用它的 `carrier_doc_problems()`（cur=211）對該檔手動跑判準②＝零命中（commit 後 pre-push 才會真掃它）。
- 我單跑 unittest 時沿用真實 HOME、未設 `AUTOSDD_SENTINEL_OFF`；事後唯讀查 `launchctl list`，兩個 `AutoSDD_Sentinel_*` 與 `com.autoclaude.nightly` 仍在（本機哨兵未被動到）。

## 1. Findings 一覽

| ID | P | 標題 | 處置分類 |
|---|---|---|---|
| F-01 | P2 | 「R211〈三〉13 條理論洞全部落在 §16.2」不成立（只有 7 條有 PRD 承接），休眠判準 3 的依據句失真 | 本輪文字修正 |
| F-02 | P2 | 審查規模的依據（範本〈🏁〉瘦身規則）與該規則自己的條文相反：PRD 修憲要四方、且要 1 設計鏡 | 本輪文字修正（或補一面設計鏡） |
| F-03 | P2 | improving_114 §8「沒有任何待辦會自動長出來」被兩個仍在走的機器時鐘反駁（nightly 錨 14 天、側軌複查 14 天） | 本輪文字揭露；側軌 warn 建議退役 |
| P3-01 | P3 | improving_114 §2 ①「PRD 2657 行」過期（HEAD 為 2699 行） | 本輪文字修正 |
| P3-02 | P3 | 接鏈列／ruff.toml 引用的 DEF-101-791 帳本內容與 E501 無關 | 本輪文字修正（登記） |
| P3-03 | P3 | ⏸ 再開症狀三處可觀測性偏弱（T1 反事實歸因、§4.5.4 的 `weekly_warn` 無實作對照、§8 列 12 無痕跡面） | 本輪文字修正（可選） |
| P3-04 | P3 | §13 條款列歸 📎 並計入 (c) 的「落地」，與 📎 定義不合 | 本輪文字修正，或延後（⏸）＋症狀 |
| P3-05 | P3 | CLI 已驗證清單（版本號型永動源）已登記但歸格與持續性揭露不足（H 的直接提問） | 退役（建議）；或延後（⏸）＋症狀 |
| P3-06 | P3 | 權威歸屬字樣：根 CLAUDE.md 寫「掌舵者裁決」，實為「授權主控代決」 | 本輪文字修正 |
| P3-07 | P3 | 範本 L41／L410 殘留「下一份檔名」義務句；improving_113 §8 末兩句與 PRD §16.3／§16.5 字面相衝 | 本輪文字修正（可選） |
| P3-08 | P3 | PRD §16.1 沒有列示母體外章節（§0／§1／§2／§15.1–15.3／§15.6–15.8…），「唯一判準與唯一帳」缺劃界 | 本輪文字修正 |
| P3-09 | P3 | 本鏡複審範圍描述與 findings 落檔義務（範本〈審查閉環〉DEF-200-090） | 本輪流程修正 |
| P3-10 | P3 | Windows 待辦清單落在休眠判準 3 的三分類之外 | 本輪文字修正，或立案（外部阻塞軌） |
| P3-11 | P3 | auto mode 分類器拒絕後改用 Edit 工具重做同一改動，「非繞過」只是主控自己的判定 | 本輪文字修正（補追認） |
| P4-01 | P4 | 「同輪第二列」技巧容量有限（主軌 469／上限 517，餘 48 行） | 延後（⏸）＋症狀 |
| P4-02 | P4 | DEF-200-242 帳本列的「待承重標註」在 PRD 零命中 | 只登記 |
| P4-03 | P4 | E501 反向鎖的已揭露盲區＋一個自觸發邊緣 | 只登記 |
| P4-04 | P4 | R211〈八〉「paths 白名單不含 docs/06_quality/*.md」字面略不精確 | 只登記 |
| P4-05 | P4 | T2／T3 與 R 系列驅動器重疊；PRD §16.5 無 T3 對應；「立案」須以 closed-by-decision／側軌承接 | 只登記 |
| P4-06 | P4 | F7① 維持外部軌，與 R210 的建議（改長債軌）相反且未回應其前提 | 只登記 |
| P4-07 | P4 | 兩份治理檔逼近體積上限（活動驅動，非日曆） | 只登記 |

## 1.1 最小修復包（把 CONDITIONAL 轉為 APPROVE 所需的全部動作；皆為文字，零程式碼）

1. `AutoSDD_improving_114.md:12`／`:65` → F-01 的措辭。
2. `AutoSDD_improving_114.md:42`／`:59`＋PRD 修訂表 L22 的審查描述 → F-02 (a) 的措辭（或改補一面設計鏡）；同批把 L22 的審查描述寫成實際範圍（P3-09 i）。
3. `AutoSDD_improving_114.md:76` 改有條件宣稱，並在 §7 加「休眠的已知機器時鐘」小表 → F-03。
4. 建議同批順手（不影響判決）：P3-01（2657→2699）、P3-06（CLAUDE.md:38 字樣）、P3-09 (ii)（把本檔 findings 落到 repo）。
5. 修完後的重驗清單：`test_doc_loc_baseline_freshness_r60`（會掃 docs 與根 CLAUDE.md）、`check_defect_log_crossref.py`；**improving_114.md 要先 `git add`（讓 `git ls-files` 看得到）再跑一次 `python tools/check_handoff_carriers.py`**——它只掃 tracked 載體，目前 untracked 的 improving_114 從未被它掃過（我手動跑判準② 為零命中，但 pre-push 才是真判官）；PRD／CLAUDE.md／`tools/tests/**` 變動使 macos-compat-ci 與 windows-compat-ci 在 push 後會跑（附錄 G2）。

## 2. P2 findings（會讓結案不誠實；皆為文字／揭露層修法）

### F-01 [P2] 「13 條理論洞全部落在 §16.2」不成立（休眠判準 3 的依據句失真）

- 位置：`docs/04_planning/AutoSDD_improving_114.md:65`（§6 判準 3）、`:12`（§1 表第 1 列）；`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md:142`（〈八〉末條）。
- 證據逐字：
  - improving_114.md:65 ＝ `3. 本檔無「下一輪候選」：improving_113 的四項「刻意沒做」與 R211〈三〉13 條理論洞全部落在 §16.2 的 ⏸（附再開症狀）或 ➖（附依據）✓`
  - improving_114.md:12 ＝ `…＋ 13 條理論洞 | 全部改寫進 PRD v2.1.17 §16 結案帳（⏸ 附再開症狀、或 ➖ 附依據）…`
  - 現查 PRD：`grep -o '〈三〉#[0-9]*'` 去重只剩 #1（L2648）、#2（L2638）、#3（L2657）、#4（L2643）、#7（L2684）、#8（L2707）、#9（L2657）＝**7 條**。
  - R211〈三〉的 #5（無人喚醒窗口壞模型值只退預設不另出聲）、#6（值域：大小寫／default／best／第三方雲端 id）、#13（`--pace` 角色行只有 `inspect.getsource` 子字串鎖）、#10（流程）、#12（ONBOARDING 表② Windows 欄）在 PRD 內零承接；以原始編號（SD1-05／SD1-07／FQ-05／SD1-13／SD1-04）再搜 PRD 亦零命中。#11 由 §16.4 完成。
  - R211〈八〉:142 ＝ `〈三〉理論洞表的「再開症狀」欄自本輪起正式成為 PRD v2.1.17 §16 結案帳 ⏸ 列的再開條件`，但 PRD §16.5(iii) 只認「§16.2 某個 ⏸ 列登記的再開症狀」⇒ 上述 5 條的再開症狀在 PRD 側沒有接線。
  - 對照（成立的那一半）：improving_113 的四項「刻意沒做」皆有列——引擎額度刷新者→§4.1.1 引擎列 ⏸、拒絕長睡的自動承接者→§4.5.2 列 ⏸、PRD 12 筆修憲整理→§16.4、R121→施工圖 A7 列 ⏸。
- 為什麼是 P2：休眠判準 3 是授權休眠的三條之一，而依據句含「全部」且可機械反駁（7／13）。實質風險低（那 5 條皆為 P4、再開症狀仍寫在 R211〈三〉），但宣稱與檔案不符就是不誠實，且正是本輪要拆的「載體不明的之後再看」。
- 修法（一句）：把 improving_114:12／:65 改寫為「7 條（#1／2／3／4／7／8／9）對映 §16.2 列；#11 由 §16.4 完成；#5／6／10／12／13 為實作面或流程 P4、無對應 PRD 列，再開症狀維持住在 R211〈三〉並由〈八〉末條承接」；（可選）PRD §16.5(iii) 加半句「R211〈三〉理論洞表的再開症狀同為觸發源」以補接線。
- 處置分類：本輪文字修正（不立案、不延後）。

### F-02 [P2] 審查規模的依據與其引用的規則相反

- 位置：`docs/04_planning/AutoSDD_improving_114.md:42`（設計期誠實劃界 (1)）、`:59`（§5 標題）；`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md:363,366`；PRD 修訂表 L22（v2.1.17 列「一面 Sonnet QA 唯讀鏡複審」）。
- 證據逐字：
  - improving_114.md:42 ＝ `(1) §16 的四格分類是 SA 判讀＋主控裁決，未經四方（本輪只改 docs＋一支 tools/tests，依範本〈🏁〉瘦身規則走 1 面 QA 鏡；…）`
  - improving_114.md:59 ＝ `## §5 審查閉環（依範本〈🏁〉瘦身規則：本輪只改 docs＋一支鎖檔，走 1 面 QA 零信任鏡）`
  - 範本:363 ＝ `### 產品輪的固定成本瘦身（再開後適用）`；範本:366 ＝ `- 審查＝1 面設計鏡（SA／SD）＋1 面 QA 零信任鏡（取代上方審查閉環步驟 1 的預設）；**碰守衛面／安全／PRD 修憲才四方**。`
  - 本輪就是 PRD 修憲：修訂表新列 v2.1.17、§16.4 的 C1～C12 十二筆就地修憲註記（improving_114:12 自己寫「修憲 12 筆以 §16.4 就地註記本輪完成」）、33 列退役歸格；而設計面（SA／SD／Architect）零獨立鏡——SA agent 是作者、不是鏡。
  - 因此引用的規則有三處不支持結論：(a) 該節標題「再開後適用」，本輪是終輪、不是再開後的產品輪；(b) 規則要求 1 設計鏡＋1 QA 鏡，本輪只有 QA 鏡；(c) 規則明文把 PRD 修憲列為「才四方」。
  - 先例對照（PRD 修訂表）：同一份 PRD 的前一次修訂 v2.1.16（L20）走了 W1／W2／W3 SD／Architect 鏡＋QA 鏡＋最終 QA 複審；唯一無四方的先例是 v2.1.12（L17：`獨立四方複審紀錄＝零…掌舵者 2026-09-01 技術債總清償循環令 D2 裁決直接落款生效`），那次的依據是掌舵者的直接落款令，不是瘦身規則。
- 為什麼是 P2：被引用的規則反過來要求更重的審查，現文把降階審查寫成「依規則」，是依據錯置；而被降階的恰是本輪風險最高的一塊（PRD 範圍重定義）。
- 修法（一句，二擇一）：(a) 改寫依據——「瘦身規則『再開後適用』且對 PRD 修憲要求四方，本輪不適用；本輪 PRD 修憲依掌舵者 2026-10-10 授權代決（improving_114:5 原文）＋v2.1.12 無四方先例，降階為 1 面 QA 鏡；殘留風險＝`[SA 判讀]` 18 列與 33 列退役歸格僅作者自審，T1／T4 成立時優先覆核」；(b) 補一面設計鏡（SD／Architect）使其至少符合該規則的「1 設計鏡＋1 QA 鏡」。PRD 修訂行的審查描述同步改成實際範圍（見 P3-09）。
- 處置分類：本輪文字修正（或補鏡）。

### F-03 [P2] 「沒有任何待辦會自動長出來」被仍在走的機器時鐘反駁

- 位置：`docs/04_planning/AutoSDD_improving_114.md:76`（§8 末句）；對照 §6 與 §2 ⑤。
- 證據逐字：improving_114.md:76 ＝ `…在掌舵者立案前，本 repo 沒有任何待辦會自動長出來。`
- 我找到的、休眠期間仍會走的時鐘（皆為現查，非推測）：
  1. **nightly 錨 14 天（會讓 pre-push 與 root-infra-ci 轉紅，非 warn）**
     - `ONBOARDING.md:552` 錨值：`nightly-checked-at=2026-10-05T14:26:01+00:00`；`tools/refresh_nightly_anchor.py:42` ＝ `NIGHTLY_MAX_AGE_DAYS = 14`；`:327-330` ＝ `age = (now - stamp).days` / `if age > NIGHTLY_MAX_AGE_DAYS:`。
     - `tools/git-hooks/pre-push:503` 與 `.github/workflows/root-infra-ci.yml:531-532` 都跑 `python3 tools/refresh_nightly_anchor.py --check-head`（驗的是 **HEAD**）。
     - 以工具自己的 `_stamp_problems()` 注入時鐘實測（附錄 H1）：2026-10-20T14:00Z → ok；**2026-10-20T14:27Z → RED**（`已是 15 天前（上限 14 天）`）。⇒ 若 HEAD 的錨不更新，**約 10 天後起任何 push 都會被擋**。
     - 本機 nightly 第 5 階段（`AutoClaude/tools/run_local_nightly.sh:343` ＝ `run_stage 5 nightly_anchor "$PY" "$ROOT/tools/refresh_nightly_anchor.py" --write`）每晚把新錨寫回**工作樹**，但不 commit；工具自己的處置句（`tools/refresh_nightly_anchor.py:66-68` ADVICE_COMMIT）＝`處置：工作樹的 ONBOARDING.md 已是新的（本機 nightly 已回填、只是沒被 commit 帶走）⇒ git add ONBOARDING.md 併入 commit，再 push`。⇒ 休眠期間 `ONBOARDING.md` 會被 nightly 自動弄髒（這本身就是一個自動長出來的待辦），且第一次 push 前必須先 commit 它。
     - 休眠更久的後果（平台行為，**我未能在本機驗證**）：GitHub 對公開 repo 於 60 天無活動後停用排程 workflow；那時 nightly 取不到新的 completed run，錨無法回填，本機 nightly 的 root_unittests 會在錨滿 14 天後每晚自己轉紅。root-infra-ci 另有「nightly-full 排程陳舊度哨兵」（`.github/workflows/root-infra-ci.yml:566` ＝ `MAX_AGE_DAYS: "10"`；`:582` ＝ `WAIVER_UNTIL: ""` 無豁免）。
  2. **側軌帳本「最近複查日」14 天（warn，rc 不變）**
     - `tools/lib/ledger_closing_guards.py:205` ＝ `STALE_REVIEW_DAYS = 14`；`:263` ＝ `if days > STALE_REVIEW_DAYS:`；`:341-342` 把 warn 印到 stderr（`check_defect_log_crossref.py` 每次都會走到）。
     - 真帳本（外部軌 5 列＋長債軌 6 列，複查日皆 2026-10-09）以注入日期模擬（附錄 H2）：2026-10-23 → 0 warn；**2026-10-24 → 5＋6＝11 條 ⚠️**。⇒ 14 天後起，每次 crossref／pre-push 都會印 11 條「請確認阻塞是否仍成立」，要讓它消失只能人工改兩本帳的日期欄。
  3. **CLI 已驗證清單漂移**（版本號型，細節見 P3-05）。
- 與 improving_114 §2 ⑤ 的關係：R210 證據檔 L49 稱 E501 日期是「repo 內唯一會在無人動工時自己轉紅的日曆義務」——就「無人動工時自己轉紅」這個狹義而言我同意（錨靠 nightly 回填維持、側軌只 warn）。我反對的只是 §8 把它外推成「沒有任何待辦會自動長出來」：上列 1、2 就是會自動長出來的待辦（一個髒檔、11 條 warn），1 還會在約 10 天後擋 push。
- 修法（一句）：(a) 把 improving_114:76 改為有條件宣稱——「沒有任何『輪』會自動長出來；剩餘機器時鐘只在 push／crossref 時出聲，清單與一次性處置見 §7」；(b) 在 improving_114 §7（或範本〈休眠期間開新視窗的第一動作〉）加「休眠的已知機器時鐘」小表（錨 14 天＋處置＝`git add ONBOARDING.md`／必要時 `gh workflow run` 後再 `refresh_nightly_anchor.py --write`；側軌 14 天 warn；nightly-full 陳舊度哨兵 10 天；CLI 清單漂移）；(c) 錨本身是排程通道活性哨兵，建議保留。
- 處置分類：本輪文字揭露（a）（b）；側軌複查日 warn（`STALE_REVIEW_DAYS`）建議**退役**（與 R207／R210 退役日曆義務同源；改碼在 `tools/lib/ledger_closing_guards.py`，不在〈守衛面准入〉清單，但受 LOC 分級管轄，本輪不強制）。

## 3. P3 findings（文字訂正／登記）

### P3-01 improving_114 §2 ①「PRD 2657 行」過期
- 位置：`docs/04_planning/AutoSDD_improving_114.md:21`。證據：該格「證據（本輪現查）」寫 `…PRD_v2.1.md` 2657 行；`git show HEAD:docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md | wc -l` ＝ **2699**（變更後 `wc -l` ＝ 2901）。2657 是矩陣在 HEAD 93929947（v2.1.16 之前）撰寫時的值，不是本輪現查。同格「修憲 16 次」成立（HEAD 修訂表 `^| \*\*v2\.1\.` 共 17 列＝v2.1.0＋16 次修訂）。
- 修法：改「2699 行（HEAD）」或刪行數。處置：本輪文字修正。

### P3-02 接鏈列／ruff.toml 引用的 DEF-101-791 與 E501 無內容關聯
- 位置：`tools/tests/test_adr_xplat001_c1c2_lock.py:3678`（`("R211", "d034314bdd87", "8fea64d22cb1", "DEF-101-791")`）、`tools/ruff.toml:70`（`R74／DEF-101-791 的「到期日要真的會到期」訂正隨之退役`）。
- 證據：帳本列在 `docs/06_quality/AutoSDD_Defect_Log_archive_56.md:34`，內容＝「**缺陷帳本死結**：主檔 248,048 bytes 已越 warn 線…歸檔判準把已結列誤判成活躍…`fail-open` 這個設計術語」，全文無 E501／到期日。舊 ruff.toml（`git show HEAD:tools/ruff.toml` L67）已有同一引用＝繼承而非本輪新造；鎖只要求「帳本家族存在該 ID」，所以綠。引入該測試的 commit 是 `a3710684`（R74），其 commit 訊息也沒提 E501。
- 修法：R211〈八〉加半句「DEF-101-791 係沿用 R74 舊註記的引用，帳本列內容為歸檔死結、與 E501 豁免無內容關聯」；或改掛內容相符的 DEF。處置：本輪文字修正（登記）。

### P3-03 ⏸ 再開症狀可觀測性偏弱的三處（整體並非「不可觀測」）
- 全體檢查（附錄 B）：30 個 ⏸ 列全有 `再開症狀＝`；症狀子句內零輪號、零日期、零「候選／待排程／下輪」；28 列帶明確「附…」證據指標，其餘 2 列（§4.5.1、施工圖 A7）寫「有 sid＋seq 的…實錄」。`[SA 判讀]` 的 6 個 ⏸ 列逐列判定：§3.2 OK（掌舵者真機要用中斷鍵／畫面原文）、§4.1.1 T1 偏弱（見 a）、§4.5.1 OK（sid＋seq）、§6.1 OK（commit／sid 座標）、§15.4 P4 OK（`quota_burn.jsonl` 列或帳單座標）、施工圖 A4 OK（`--pace` 畫面＋掌舵者清倉指令）。另抽查 T2／T3／引擎／§4.2.3／§4.4.3／§4.5.2／§4.5.10（planner 以 `append_log(log, "probed", rc=…, kind=…)` 逐次落痕，`tools/session_resume_planner.py:1288`）／§8 列 1／2／3／9／§9／§12 寫入範圍等，皆有可附證據的事件面。
- 三處偏弱：
  - (a) §4.1.1 T1 列（PRD L2639，`[SA 判讀]`）：「一次決策因缺 OTel 才有的量測…而做不了或做錯」是反事實歸因，沒有可 grep 的事件。建議改成可現查形態（例如 `quota_burn.jsonl` 出現 unmeasured 列，且該窗內有人明示要逐 token／成本明細）。
  - (b) §4.5.4 列（PRD L2659）：症狀用「週軸已達 `weekly_warn` 等級」，但 `weekly_warn` 在 tools／.claude／AutoClaude 全零命中（只存在於 PRD L1122 與 §6 字面 `WEEKLY_WARN_PERCENT=70`〔L1832，C8 註記已將該區塊降為歷史字面〕）；觀察者無法判定「達沒達」。建議列內寫明採實作哪一帶（例如 `AUTOSDD_QUOTA_CONVERGE_PCT` 出廠 70）。
  - (c) §8 列 12（PRD L2678）：「觸發向外部網址的外送請求」在 repo 內沒有任何痕跡面（沒有出站日誌），實務只能偶然發現。建議改寫為逐字稿可現查形態（無人窗口逐字稿出現對外 URL 的 curl／wget／requests 呼叫）。
- 處置：本輪文字修正（可選）。

### P3-04 §13 條款列歸 📎 並計入 (c)「落地」
- 位置：PRD L2688（§16.2 §13 條款列）、§16.3 (c)。證據：§16.1 的 📎 定義＝「機制已 ✅，只欠校準值、fixture 或驗收證據」，§13 條款是純人工（矩陣原判 ❌、「非程式碼缺口」），而 PRD 自己（附錄 B.3 #1、§15.1 #2）稱它是「唯一可能讓整個專案作廢的風險項」。(c)＝(✅＋📎)÷(101−➖)＝38÷68 的分子因此含 3 列「從未發生的人工／長跑證據」（§13 條款、§11.1、§11.8）。
- 修法：§16.3「讀法」補一句說明 (c) 的 📎 含人工／長跑證據列且 §13 條款是 PRD 自稱最高風險項；或把 §13 條款改 ⏸（再開症狀＝收到 Anthropic 條款變更通知或帳號警告，附原文）。處置：本輪文字修正，或延後（⏸）＋症狀。

### P3-05 CLI 已驗證清單：版本號型永動源（H 的直接提問）——已登記，但歸格與持續性揭露不足
- 事實（現查）：本機 `claude --version` → `2.1.296 (Claude Code)`；`AutoClaude/autoclaude/utils/verified_cli_versions.py` 只有 `2.1.223`／`2.1.233`／`2.1.295`（improving_113 才剛補進 2.1.295，不到一天又落後）。未驗證版本在啟動路徑上的實際效果（`AutoClaude/autoclaude/main.py:121-122` 與 `:149` 的 `cleanup=lambda: cleanup_merged_worktrees(Path.cwd(), dry_run=dry_run)`）＝每次啟動一則桌面通知（`AutoClaude/tests/test_r100_boot_self_check.py:215` 斷言 `# loud 恰好一次`）＋略過合併 worktree 清理；`dry_run` 刻意不接執行器（main.py 該段註解自述）⇒ 傷害只是雜訊＋略過清理。測試不會因 CLI 升版轉紅（`test_the_real_cli_version_is_readable_or_honestly_unknown` 不斷言機器狀態）。improving_113.md:165-166 自己寫過「每次 `python -m autoclaude` 啟動 loud＋DRY_RUN，R-6.2-2 的 loud 失去鑑別力」。
- §16 的登記現況：§16.2 §6.2 R-6.2-2 列（PRD L2669）與 §8 列 13 歸 📎，並寫「隨 CLI 升版漂移的清單資料——寫本列當下本機 `claude --version`＝2.1.296、清單最新 2.1.295，啟動仍 loud 一次、不阻止啟動；補清單屬程式碼維護、不開修憲」。⇒ 已誠實登記「會漂移」與當下落差，**不算漏登**。
- 不足：(i) 📎 的定義是一次性驗收證據殘留，不是無終點的持續維護面；(ii) 沒有 owner、沒有觸發，休眠下只會一直 loud；(iii) (c) 把它算成已落地；(iv) 同型條款已被 R207 在五問協定退役（`docs/06_quality/FiveQuestion_Audit_Protocol/README.md:76`：「時間型觸發在沒有任何症狀時也會開輪，是再評永遠做不完的永動機…版本變更若真改了權限姿態由 S6 接住」）。
- 修法：§16.2 兩列補一句「每次 CLI 升版即重現、無終點；未驗證版本的後果＝每次啟動一則通知＋略過合併 worktree 清理，不影響執行」。
- 處置分類：**退役**（建議：把「版本不在清單」從 loud 降為單行 log，AutoClaude 改碼、非守衛面）；若不改碼→**延後（⏸）**，再開症狀＝「未驗證版本的 boot 通知導致一次真實的 CLI 介面變動被忽略（附通知逐字與 sid）」。

### P3-06 權威歸屬字樣：「掌舵者裁決」vs「授權主控代決」
- 位置：根 `CLAUDE.md:38`（`🔴 軌道① 系列可**休眠**（2026-10-10 掌舵者裁決，improving_114 終輪）`）；PRD 修訂表 L22（`掌舵者 2026-10-10 直接立案`）。
- 證據：improving_114.md:5 引的掌舵者原文是「若需要我決策，請依照最佳化、最理想、最適當的解決方案，我授權幫我決策」＝授權代決；improving_114 §3 抬頭也寫「主控依掌舵者『最佳理想化』授權代為決策」。本 repo 對代決有明確體例，例：DEF-200-199 列＝「closed-by-decision（2026-10-05，主控代決；R199 開場否決窗口已過、掌舵者未否決＝維持結案，非明示追認）」。根 CLAUDE.md 每個視窗都讀，「掌舵者裁決」會被後續視窗當成比實況更強的權威。
- 修法：CLAUDE.md:38 改「2026-10-10 掌舵者授權主控代決（非明示追認；掌舵者可隨時以 T1 推翻），improving_114 終輪」；PRD 修訂行的「直接立案」只對 root-cause 指令成立，具體歸格標「主控代決」。處置：本輪文字修正（CLAUDE.md 被測試釘住，改後需重跑 `test_doc_loc_baseline_freshness_r60`）。

### P3-07 範本殘留「下一份檔名」義務句；improving_113 §8 末兩句與新規相衝
- 位置：範本 `AutoSDD_Iteration_Prompt_Template.md:41`、`:410`（`每輪須明確標示本輪在哪一柱（A/B/C）推進、下一份檔名`／`防混淆機制不變：每輪標示在哪一柱（A/B/C）、下一份檔名`）；`docs/04_planning/AutoSDD_improving_113.md:224-225`。
- 證據：範本:334 的「效力」句已明示覆蓋 L41（improving_114 §7 也已揭露），所以不是缺口；但 L41 與 L410 逐字仍是義務句。improving_113.md:224 `下一輪若主軌仍為正即連升第 2 輪，第三輪必須 ≤0`、:225 `下一輪重盤請沿用 R211 姊妹檔矩陣的同一算法`，與 PRD §16.3（`之後不重算、不當門檻、不當開輪理由`）字面相衝。除此之外，範本 grep（`下輪|下一輪|N+1|候選|下一份|下次|遞增|延後`）其餘命中皆為否定語境或史料（L173／L184／L330-331／L347／L357／L378／L382／L385／L403／L411）。
- 修法：範本 L41／L410 刪該片語；improving_113.md:225 行尾加「（已由 improving_114 §6 與 PRD §16.3／§16.5 取代，保留為史料）」。處置：本輪文字修正（可選）。

### P3-08 PRD §16.1 沒有列示母體外章節
- 位置：PRD §16.1〈邊界〉與 §16 開場（L2605：`本章是「v2.1 做完了沒」的唯一判準與唯一帳`）。
- 證據：101 列母體是矩陣的點名範圍；PRD 的 §0／§0.6／§1／§2／§14／§15.1～§15.3／§15.6～§15.8／附錄 A／B 不在其中。矩陣只聲明 §14、附錄 A、附錄 B 不計列；§1、§2、§15.1–15.3、§15.6–15.8 連不計列的聲明都沒有。這些章節含規範性或半規範性文字：§15.1「必須人工確認三件事」（其中超額用量＝「本專案最危險的單一失敗模式」，已由 §15.4 P4 ⏸ 列間接承接）、§15.6 失敗模式表、§15.8 目錄結構（Daemon 形態，換形態後無對映）。§16.1 的邊界段只談矩陣內部的章節，對母體外的 PRD 章節沒有一句劃界。
- 修法：§16.1〈邊界〉補一段「母體外章節＝導言／定義／方法論／史料／建議架構與目錄（逐章列名），其規範性內容已由母體列承接或屬 Daemon 形態建議，不入母體」。處置：本輪文字修正。

### P3-09 本鏡複審範圍描述與 findings 落檔義務
- (i) 本鏡實際範圍＝結案帳結構（101 列對帳）、§16.3 算術、⏸ 症狀可觀測性與禁字、約 50 項事實座標抽查、E501 鎖變異自證、棘輪算術、守門親跑；**未**重判 `[SA 判讀]` 18 列歸格。PRD 修訂行的「一面 Sonnet QA 唯讀鏡複審」宜寫明範圍，避免被讀成「18 列歸格已獨立覆核」。
- (ii) 範本〈審查閉環〉（DEF-200-090 教訓，範本內「四方複審產出一律先落檔，才可進入收斂」整段）要求複審逐條 findings 先落成 repo 內具名檔案才進修復；本檔在 scratchpad，主控須把 findings（含證據）落到 repo（建議 R211〈八〉或 improving_114 §5 的逐條表）再處置，派工書轉述不算落地。
- 處置：本輪流程修正。

### P3-10 Windows 待辦清單落在休眠判準 3 的三分類之外
- 位置：`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md:128-133`（〈六〉）、`docs/06_quality/CrossPlatform_R210_Debt_Closure_Final_Evidence.md:130-134`（〈八〉）；improving_114.md:70；範本 :347-348。
- 證據：〈六〉4 項與 R210〈八〉3 項（表② Windows 欄回填、tree 欄首筆樣本、PS 5.1 實跑…）既非帳本 DEF 列、也非 §16.2 ⏸ 列、也非 ➖；improving_114:70 揭露為「無輪號、只在該機做」。範本:347-348 ＝ `三類之外的「之後再看」不是載體，不得存在。`
- 修法：improving_114 §7 明寫該清單「非載體、無義務、僅供 T1／T4 事件發生時參考」，或以外部阻塞軌 DEF 列（阻塞源＝Windows 實機）承接（DEF-101-693／DEF-200-313／DEF-200-253／DEF-101-856 已是同型列）。處置：本輪文字修正，或立案（外部阻塞軌）。

### P3-11 分類器拒絕後改用 Edit 工具重做同一改動
- 位置：improving_114.md:42 (4)。證據逐字：`(4) 主控曾被 auto mode 分類器擋下一次「Bash 改棘輪常數」（[Self-Modification]），改以 Edit 工具逐筆做同一程序——同檔、同改法、同守衛測試，非繞過。`；根 `CLAUDE.md:74`：`auto 下被拒一次 ⇒ /permissions → Recently denied → 按 r 人工核准重試。不要改派子代理或換路徑繞過`（該句語境為 `.claude/` 批次，但精神同）。
- 我已獨立重算重釘內容（§5-F 與附錄 F1／F2）：`--print-guard-lines` ＝ `淨額 115589→115589 (+0)`、逐檔漂移 0 支，鎖模組 187 支 OK ⇒ 無完整性風險。問題只在程序透明：「非繞過」是主控自己的判定。
- 修法：improving_114:42 (4) 補「掌舵者授權代決已涵蓋此重釘；若掌舵者另有意見以其為準」，或請掌舵者追認。處置：本輪文字修正。

## 4. P4 findings（只登記；皆不構成本輪結案條件）

- **P4-01 「同輪第二列」技巧容量有限**：`tools/tests/test_adr_xplat001_c1c2_lock.py` 現值 `_REPIN_ROUND_NET_CAP = 517`、`_REPIN_NET_CAP_DUE_ROUND = 212`、`_PHASE2_DUE_ROUND = 213`（末列 208＋視窗 5）、重釘日誌末兩列 `('R211', 114811, 115598, 787)`／`('R211', 115598, 115589, -9)`；R211 主軌合併淨額 469 ⇒ 之後若再用 R211 標籤追加，主軌只剩 48 行餘裕（回歸鎖軌另計），用盡即必須開 R212（帳本時鐘前進、到期義務醒來）。範本〈證據檔命名〉與 improving_114 §2④ 已寫「真的要動根層護欄層才開 R 輪並承擔其義務」，但沒有給這個容量數字。分類：延後（⏸），再開症狀＝一次重釘被 517 夾住。
- **P4-02 DEF-200-242 帳本列的字面落差**：`docs/06_quality/AutoSDD_Defect_Log.md:160` 寫「PRD §11.2 待承重標註維持」，PRD 在 HEAD 與變更後 `待承重` 皆零命中（SA agent 自己發現）；C1 註記（PRD L592、L2329）以「未承重的目標句」實質承接。不改帳本（結案編修單線），登記即可。
- **P4-03 E501 反向鎖的盲區與自觸發邊緣**：盲區已寫在 `e501_no_calendar_verdict` docstring（`tools/tests/test_subprocess_encoding_hygiene.py:1381`），實測半形冒號、斜線日期、他種措辭皆回 None（附錄 E）。自觸發邊緣：ruff.toml 的退役記載用「退役到期日（2026-10-10，…」（全形括號）；若日後改成「退役到期日：2026-10-10」（全形冒號），`_E501_CALENDAR_EXPIRY_RE` 會命中而自己轉紅（附錄 E 末列實測）。
- **P4-04 R211〈八〉的 paths 描述**：`CrossPlatform_R211_ZeroTrust_Audit_113.md` 〈八〉寫「三支 workflow 的 `paths` 白名單不含 `docs/06_quality/*.md`」；macOS／Windows compat 的白名單含兩個具名檔 `docs/06_quality/CrossPlatform_Maturity_Criteria.md` 與 `docs/06_quality/FiveQuestion_Audit_Protocol/params.json`，只是不含被改的 R211 證據檔。結論（cec520ba 只觸發 root-infra-ci）我以白名單比對函式確認成立（附錄 G2）。
- **P4-05 觸發器對應與詞義**：(a) 範本 T2「缺陷帳本新立 P≤2 未結列」與根 CLAUDE.md 的 R 系列驅動器（帳本未結列＋循環令）同源，未寫新 P≤2 缺陷走軌道①還是 R 系列；(b) PRD §16.5 只有 (i)(ii)(iii)，無 T3（CI／nightly 轉紅）對應；(c) 範本三態只說明「宣告」時檢查休眠判準，宣告後狀態只由 T1～T4 改變，未明說；(d) 「立案」必須以 closed-by-decision 或側軌承接，否則判準 2（未結列＝0）不成立，範本未明寫。
- **P4-06 F7① 與 R210 建議相反**：R210 證據檔〈六〉（L116-121）呈報單第 1 件＝DEF-200-075 軌別，建議改長債軌（「它是內部債、不是外部阻塞」，今日判定「部分（量測已做、欠債 103 支未清）」）；improving_114 F7① 維持外部軌，理由＝「解除判準＝mac 真機 skip census 環境量測值」。本機就是 mac 且每晚量測（`AutoSDD_External_Blocked_Log.md:39` 複查記錄逐字 `[skip census] AutoClaude/tests@darwin+nopg+solo+pgext 共 157 支…欠債型 103 支（目標 0）`）。兩軌行為相同（皆 14 天 warn、皆不計入未結分母），代價低；登記決策依據即可。呈報單第 2 件（E501 到期日）＝F5 退役，成立。
- **P4-07 治理檔逼近體積上限（活動驅動，非日曆）**：`check_defect_log_crossref.py` 現查警告 `CrossPlatform_Guard_Line_History.md 250457 bytes（距上限 262144 剩 11687）`、`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md 255168 bytes（剩 6976）`；只在有人 append 時才咬人，不屬時間／輪號／版本號型永動源，登記。

## 5. 各審查項結果（A～I；通過項的證據）

### A 結案是否真的「無未分類列」——通過（唯一不通過的是 13 條理論洞的宣稱，見 F-01）
- 矩陣 §2.1＝90 列（✅23／⚠️49／❌9／➖9）、§2.2＝11 列（✅6／⚠️2／❌2／➖1）⇒ 101 列（✅29／⚠️51／❌11／➖10）；無重複 ID；非 ✅＝72 列。
- PRD §16.2 表＝72 列、與矩陣非 ✅ 列**同序**逐列對應，判定欄 0 筆不符；PRD 列的 ✅ 29 個矩陣 ID 與矩陣 ✅ 集合雙向差集皆空。
- 結案格：➖33／⏸30／📎9（＋✅29＝101）；交叉表與 PRD 自列一致：⚠️51→➖19／⏸25／📎7；❌11→➖4／⏸5／📎2；➖10→➖10。
- §16.3：(a) (22＋0.5×44)÷73＝60.27%→60.3% ✓；101 列版 (29＋0.5×51)÷91＝59.89%→59.9% ✓；(c) (29＋9)÷(101−33)＝38÷68＝55.88%→55.9% ✓。
- 「四項刻意沒做」皆有列 ✓；「13 條理論洞」✗（F-01）。

### B ⏸ 再開症狀可觀測性——通過，三處偏弱（P3-03）
- 見 P3-03 與附錄 B：30／30 列有症狀、0 禁字；整個新增 PRD 文字（202 行）掃禁字（候選／下一輪／待排程／日後／到期…）命中僅限否定句與機制敘述；輪號皆為史料引用；日期 4 筆（2026-08-31 事件紀錄、2026-10-10 授權日×3）。

### C PRD 既有條文零字更動——通過
- `git diff --numstat` ＝ `202	0`；以 HEAD 版與工作樹版做 diff，僅 HEAD 有的行數＝0；新增行中符合 `^[A-Z][A-Z0-9_]{2,}=` 者＝0（沒有任何 KEY=value 形狀的新增行）；3 條新增 `#` 註解行只在 .env 圍籬內（L1834、L1835、L1920）；`test_context_budget_guard -k Prd` ＝ `Ran 5 tests … OK`。

### D 範本〈🏁〉與其他段落——通過，殘留見 P3-07／P4-05
- T1～T4（範本:352-355）、休眠三判準（範本:344-348）、improving_114 §6、根 CLAUDE.md:38 三處一致（皆指向 T1～T4、都說「不開輪、不產四件套、直接做產品工作」）。PRD §16.5 為三觸發（無 T3），屬層級不同（PRD 層 vs 系列層），見 P4-05。
- 範本 grep 結果：`{{N+1}}`／「列入下輪」已無殘留；「候選」只剩否定語境（:347、:357）。

### E E501 退役的鎖有牙——通過
- 變異自證（只在行程內，不改檔；附錄 E）：(i) 現 ruff.toml 加回 `到期日：2026-12-31` → 回「又出現日曆到期」（紅）；HEAD 版舊 ruff.toml → 回「又出現日曆到期 '到期日：2026-11-02'」（紅）；(ii) 現 ruff.toml 去掉所有「退役到期日」→ 回「不再記載「退役到期日」」（紅）；現檔 → None（綠）。(iii) `_E501_DEBT_CEILING = 139` 與 `test_e501_debt_only_shrinks` 仍在（`TestRootToolsLintPolicy` 8 支 OK，含兩支新鎖）。
- 判決函式簽名 `(text) -> str | None`，無 today 參數；測試檔 `date.today()`／`datetime.now()` 用量＝0。
- 幽靈符號：ruff.toml 註解引用的 `_E501_DEBT_CEILING`（:1355）、`TestRootToolsLintPolicy`（:1399）、`test_the_e501_waiver_has_no_calendar_expiry_by_decision`（:1463）、`test_e501_debt_only_shrinks`（:1450）、`test_the_no_calendar_criterion_is_red_when_it_should_be`（:1480）全部存在；R207 決議檔存在。被退役的 `e501_waiver_verdict`／`_E501_WAIVER_MAX_DAYS`／`_E501_EXPIRY_RE`／兩支舊測試名只剩在歷史字串（重釘日誌列、R76 掃描檔、R211〈八〉）。
- 全 repo 新增文字的幽靈符號普查（附錄 ghost）：路徑類 0 缺（只有指令片段／runtime 檔／佔位符）；零命中識別字皆為 PRD 明言「未實作」的名稱。
- 補充：改動後 `tools/tests/test_subprocess_encoding_hygiene.py` 與 HEAD 皆為 39 個 `def test_`（lock 檔 187／187）⇒ MIN_TESTS 5273 的 discovery 數不變；`sync_onboarding_baselines.py --check`／`--check-snapshot` 皆 rc=0（無指紋漂移）。

### F 棘輪重釘算術——通過
- `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` → `# 淨額 115589→115589 (+0)`、`# 逐檔漂移 0 支`（rc=0）；`cd tools/tests && python -m unittest test_adr_xplat001_c1c2_lock` → `Ran 187 tests … OK`。
- 同輪第二列 `('R211', 115598, 115589, -9)`：`test_subprocess_encoding_hygiene.py` 1559→1542（−17；`wc -l` 現值 1542，`git diff --numstat` ＝ +38／−55＝淨 −17）＋`test_adr_xplat001_c1c2_lock.py` 8727→8735（+8；`wc -l` 現值 8735，numstat ＝ +12／−4＝淨 +8）＝ −9 ✓。這兩支的 guard lines 計數＝檔案總行數，與 numstat 淨值逐支相符（沒有計數規則差異要解釋）。
- 三站 guard-total 標記（improving_112:175、improving_113:227、R145_Scan_Findings:800；另 improving_114:78 自帶一份）：114811→115589（+778）＝787−9 ✓；「回歸鎖軌 309、主軌 469」＝478−9 ✓（主軌 469 ≤ 上限 517）。
- 接鏈與凍結前綴：`_REPIN_LOG_FROZEN_PREFIX_LEN` 331→332 ✓（日誌現 332 列）；sha 前 12 碼 `d034314bdd87`→`8fea64d22cb1` ✓（`_REPIN_LOG_HISTORY_SHA256` 全值 `8fea64d22cb14c95…`）；接鏈列 `("R211","d034314bdd87","8fea64d22cb1","DEF-101-791")`（引用內容問題見 P3-02）。

### G improving_114 的數字與宣稱——除 P3-01 外全數對得上
- cec520ba：`gh run list --commit cec520baa895597664896206322369755816744a --json …` ＝ 僅一筆 `root-infra-ci`、`databaseId 37988736282`、`conclusion success`、`createdAt 2026-10-09T20:42:07Z`（附錄 G1）；`git show --stat cec520ba` ＝ 只改 `docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md`；以各 workflow `on.push.paths` 白名單比對（附錄 G2）：其餘 workflow 皆 not triggered ⇒「另三支依 paths 未觸發」成立。
- 本變更集的觸發預測（附錄 G2）：root-infra-ci（無 paths 過濾）＋macos-compat-ci＋windows-compat-ci（paths 含 `CLAUDE.md`／PRD／`tools/ruff.toml`／`tools/tests/**`）；AutoClaude CI、aisdlc-sdd-ci、shellcheck-ci 不觸發。與 improving_114 §7「windows-compat-ci 的 paths 含 tools/tests/**，push 後會跑」相符。
- `--unresolved-count` 逐字 `未結列數＝0／全部 209 列｜warn=86 fail=98` ✓；外部軌 5／長債軌 6 ✓。
- `.github/workflows/root-infra-ci.yml:582-583`：`WAIVER_UNTIL: ""`，理由欄含「不得以「日期到了」當解除依據」✓（improving_114 §2 ⑤）。
- R210〈六〉呈報單兩件＝DEF-200-075 軌別、`tools/ruff.toml` E501 到期日 2026-11-02 ✓（裁決是否妥當見 P4-06）。
- §4 矩陣本輪實測欄：護欄棘輪（Ran 187 OK）、E501 鎖（Ran 39 OK）、文件鎖（281 支 OK）、PRD 直讀鎖（Ran 5 OK；`test_r100_boot_self_check.py` 42 passed）、crossref／carriers／archive `--check` 皆 rc=0 ——我獨立重跑全部吻合；`ruff check tools/ .claude/hooks/` → `All checks passed!`（rc=0，主控標為待回填的那一格，我已跑出同值）。
- improving_114 §2 ④：`_REPIN_NET_CAP_DUE_ROUND`＝212、`_PHASE2_DUE_ROUND`＝213 ✓（import 該鎖檔現查）。
- PRD §16.2／註記事實座標抽查（約 50 項，全數吻合）：`_ROLLOVER_EPS = 0.5`（quota_pace.py:112）、`RESET_SKEW_SECONDS = 120`（session_resume_planner.py:217）、`RESUME_MAX_TRANSCRIPT_DEFAULT = 32 * 1024 * 1024`（:1100）、`endpoint_probe_verdict`（quota_gate.py:741）、`UNATTENDED_SETTINGS` 與 `--permission-mode acceptEdits --settings`（resume_route.py:45/138）、`max_spawns()`／`AUTOSDD_RELAY_MAX_SPAWNS` 出廠 2（relay_machine.py）、`timeout=3600`（session_resume_planner.py:1227）、`_GOV_EXACT` 內容（含 `.env`、不含 `resume_route.py`／`model_roles.py`）與 `.autoclaude/` 前綴、`AUTOSDD_QUOTA_{NOTICE,CONVERGE,PREPARE,HALT}_PCT` 出廠 50／70／85／95 與 `PACE_CEILING` 1.0、`step_timeout_seconds = 600`、`sleep_slice_seconds=30`／`clock_jump_tolerance_seconds=5`／`max_inprocess_wait_seconds=18000`、`permission_mode` 含 `bypassPermissions`、unattended settings deny `git commit*`／`git push*`、`main.py:246-247` 自陳不呼叫 `hotkey.register()`、`claude --help` 對 `--max-turns` 計數 0（rc=0）、`claude --version`＝2.1.296、`.claude/settings.json` 無 PreCompact、R206 證據檔的瞬時 `index.lock`、DEF-200-242 列內容（50 次翻頁／7 次 cap→free／暴露 0）、11 個具名檔案存在、`_orphan_watch`／`bursting_ok`／`read_context_feed` 符號存在、`statusline_context_feed.py` 無 `rate_limits`、13 個 DEF 的狀態（458／198／234／246／507／508／197／199／206／244／231／235／236）、N1 段的 DEF-200-146／148／204／205 皆 fixed 且「R102 四方終審 4/4 APPROVE_WITH_FIXES」（R102_Scan_Findings.md:15）、§4.1.2 退役的理由（PRD §4.1.5 與 `quota_gate.py` 的 `draining()` 對 unmeasured 回 unknown）。

### H 漏網永動源——見 F-03、P3-05、P4-01／P4-07
- 日期型：搜尋 `date.today()`／`datetime.now()` 與寫死日期的比對（tools、.claude/hooks、AutoClaude 的 tests／autoclaude／tools、AISDLC_SDD 的 scripts／v0.01 凍結基線／v0.30 LATEST 三處），**沒有**第二個「以真時鐘比寫死日期」的測試或守門（命中皆為相對時間運算、固定注入的合成夾具，或 SDD 兩軌 `date.today()` 的檔名／時戳用途，無到期比對）；`WAIVER_UNTIL` 空。仍在走的時鐘＝F-03 的 1、2（皆為「資料欄日期＋14 天」型，非寫死日期）。
- 輪號型：`_REPIN_NET_CAP_DUE_ROUND` 212／`_PHASE2_DUE_ROUND` 213 仍在，靠「帳本時鐘不前進＋同輪第二列」休眠（P4-01）；R210 已登記為 P4、本輪不動，符合〈守衛面准入〉。
- 版本號型：CLI 清單（P3-05）；五問協定的版本／時間型觸發已被 R207 退役（README.md:67、:76）。
- Q4′ JSON「效期」（`tools/session_gate_acceptance.py:17`：`generated_at 距今 ≤14 天`；README.md:54、:79）只被按需執行的 `tools/probe/fivequestion_ledger.py` 消費；`grep -rln 'protocol-status|protocol_status|symptom_streak' tools .claude .github` 只命中該 probe、`audit_session.py` 與 `test_claim_provenance_r86.py`（測試以固定「現在」注入，該檔 L50 註明不用 `datetime.now()`）⇒ pre-push／CI／nightly 都不呼叫它，不在任何閘門的真時鐘路徑上，不構成休眠危害。

### I 機械守門——全綠（逐字輸出見 §6）

## 6. §1-I 五條機械守門——我自己親跑的逐字輸出（rc 先導檔再 echo 取得；每條前置 source .venv/bin/activate、unset AUTOSDD_PARALLEL_TESTS）

### 6.1 python tools/check_handoff_carriers.py　→ rc=0
```
[census] 當前輪＝R211（R 系列證據檔／交棒書檔名最大號現查；未結承接輪號＝空）
[census] tracked 交接載體＝202 份（glob ['docs/04_planning/R*_HANDOFF.md', 'docs/04_planning/AutoSDD_improving_*.md', 'docs/06_quality/CrossPlatform_R*.md']）；其中前瞻延後行 1 筆
[census] commit 訊息＝743 則；其中含前瞻延後宣告 0 筆

✅ 每一筆前瞻延後宣稱都有帳本承接載體
```

### 6.2 python tools/check_defect_log_crossref.py　→ rc=0
```
⚠️  治理文件 CrossPlatform_Guard_Line_History.md 250457 bytes 已逼近上限 262144（距 11687 bytes），請規劃拆分——append 前務必先 `wc -c`
⚠️  治理文件 CrossPlatform_DEF200274_Parallel_Tests_Evidence.md 255168 bytes 已逼近上限 262144（距 6976 bytes），請規劃拆分——append 前務必先 `wc -c`
⚠️  已結列殘留待辦 3 筆（已結分類使它們結構上進不了承接稽核；真待辦請拆出獨立 DEF 列承接，敘事引述可忽略）：:74 DEF-101-060(closed-by-decision)=下一輪、:137 DEF-200-129(fixed)=backlog、:168 DEF-200-277(fixed)=留待
✅ 缺陷帳本跨文件狀態一致：帳本 209 筆有效狀態紀錄、19 份掃描目標皆無矛盾；另全部表格列的狀態欄首詞皆落在《格式定義》宣告的 7 個合法值內（散文與程式常數雙向綁定，且每個合法值都有分類器對應）；全部表格列的欄數皆等於表頭欄數、狀態欄由表頭定位（非 cells[-1] 位置猜測）；具名治理文件 165 份皆已登記且未逾體積上限（登記面對 CrossPlatform_*.md／Quota_*.md／AutoSDD_External_Blocked_Log.md／AutoSDD_Structural_Debt_Log.md 發現面雙向核對）；全部未結案列的承接輪次皆 ≥ 當前輪 R211 或改派至≥當前輪／未指派（硬規則②；已實測不涵蓋的形態見 orphan_backlog_problems docstring）；未結存量 0 列（唯一量測入口＝`--unresolved-count`；warn 86／fail 98 列）且皆二擇一（承接輪號／字面「未指派」，存量豁免 0 筆／棘輪上限 0，只准變小）；另 3 筆已結列殘留待辦，見 warning。
🔴 當前輪 R211 係由 R 系列證據檔／交棒書檔名最大號**現查**推得（不寫死）——本輪的證據檔／交棒書尚未建立時，此值仍停在上一輪，屆時「交棒給剛結束的那一輪」會合法通過（刻意選的 fail-open 方向：漏抓而非假紅，窗口於本輪證據檔／交棒書落地時自動關閉，見 lagging_clock_notes()）
外部阻塞軌（AutoSDD_External_Blocked_Log.md，不計入未結列 warn/fail 分母）：5 筆｜DEF-101-693、DEF-101-856、DEF-200-075、DEF-200-253、DEF-200-313
結構性長債軌（AutoSDD_Structural_Debt_Log.md，不計入未結列 warn/fail 分母）：6 筆｜DEF-101-018、DEF-101-398、DEF-101-701、DEF-101-702、DEF-101-960、DEF-101-980
```

### 6.3 cd tools/tests && python -m unittest test_doc_loc_baseline_freshness_r60　→ rc=0
```
...........................................................❌ 模式旗標互斥，實得 ['--check', '--json']——請一次只給一個
❌ 模式旗標互斥，實得 ['--write', '--check-snapshot']——請一次只給一個
..❌ --platform 不得與 --write 併用：回填一律只寫**本機平台**那一欄。跨平台代填等於替另一台機器捏造 provenance，那正是 R67-D1 本體
❌ --platform 不得與 --write 併用：回填一律只寫**本機平台**那一欄。跨平台代填等於替另一台機器捏造 provenance，那正是 R67-D1 本體
.usage: python tools/sync_onboarding_baselines.py [-h] [--check] [--write]
                                                 [--with-slow]
                                                 [--check-snapshot] [--json]
                                                 [--platform {darwin,win32}]
                                                 [--allow-pg-extras]
python tools/sync_onboarding_baselines.py: error: unrecognized arguments: --check-snapsho
usage: python tools/sync_onboarding_baselines.py [-h] [--check] [--write]
                                                 [--with-slow]
                                                 [--check-snapshot] [--json]
                                                 [--platform {darwin,win32}]
                                                 [--allow-pg-extras]
python tools/sync_onboarding_baselines.py: error: unrecognized arguments: --check-snap
.usage: python tools/sync_onboarding_baselines.py [-h] [--check] [--write]
                                                 [--with-slow]
                                                 [--check-snapshot] [--json]
                                                 [--platform {darwin,win32}]
                                                 [--allow-pg-extras]
python tools/sync_onboarding_baselines.py: error: unrecognized arguments: --totally-bogus-flag
usage: python tools/sync_onboarding_baselines.py [-h] [--check] [--write]
                                                 [--with-slow]
                                                 [--check-snapshot] [--json]
                                                 [--platform {darwin,win32}]
                                                 [--allow-pg-extras]
python tools/sync_onboarding_baselines.py: error: unrecognized arguments: --wtih-slow
usage: python tools/sync_onboarding_baselines.py [-h] [--check] [--write]
                                                 [--with-slow]
                                                 [--check-snapshot] [--json]
                                                 [--platform {darwin,win32}]
                                                 [--allow-pg-extras]
python tools/sync_onboarding_baselines.py: error: unrecognized arguments: --checks
.❌ --with-slow 只在 --write 下有意義（它是回填模式）
❌ --with-slow 只在 --write 下有意義（它是回填模式）
...............................⏳ 實跑 ci-gate ＋ AutoClaude pytest（分鐘級）…
.⏳ 實跑 ci-gate ＋ AutoClaude pytest（分鐘級）…
.⏳ 實跑 ci-gate ＋ AutoClaude pytest（分鐘級）…
........................................................................................................................................................................................
----------------------------------------------------------------------
Ran 281 tests in 105.172s

OK
✅ [loc-baseline-live:] {'total': 17413, 'cap': 20438, 'violations': 0}（來源：AutoClaude/tools/check_loc_budget.py --json）
✅ [rootunit-baseline-live:] {'tests': 5273}（來源：tools/run_root_unittests.py 的 MIN_TESTS）
✅ 已回填 [loc-baseline-live:] → {'total': 17413, 'cap': 20438, 'violations': 0}
✅ 已回填 [rootunit-baseline-live:] → {'tests': 5273}
✅ 已回填 [autoclaude-pytest-snapshot:]（macOS 欄）→ {'passed': 3, 'skipped': 0}（來源：cd AutoClaude && python -m pytest tests/ -q（plain 形態））
✅ 已回填 [cigate-v001-snapshot:]（macOS 欄）→ {'passed': 3}（來源：bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行）
✅ 已回填 [cigate-v030-snapshot:]（macOS 欄）→ {'passed': 3}（來源：bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行）
✅ 已回填 [cigate-scripts-snapshot:]（macOS 欄）→ {'passed': 3}（來源：bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行）
✅ 已回填 [snapshot-fingerprints-darwin:] → {'v001': '83a9e001afe1', 'v030': '6dca140b0905', 'scripts': 'a39cb8e812af', 'autoclaude': '43ee7bc2885e'} ＋ {'measured-at': '2026-10-10', 'host': 'Darwin-25.6.0-arm64', 'docker': 'down', 'pgextras': 'absent', 'interpreter': '.venv/bin@3.11.15', 'sdk-extra': 'present', 'baseline-origin': 'self-recorded'}
✅ 已回填 [loc-baseline-live:] → {'total': 17413, 'cap': 20438, 'violations': 0}
✅ 已回填 [rootunit-baseline-live:] → {'tests': 5273}
✅ 已回填 [autoclaude-pytest-snapshot:]（macOS 欄）→ {'passed': 3, 'skipped': 0}（來源：cd AutoClaude && python -m pytest tests/ -q（plain 形態））
✅ 已回填 [cigate-v001-snapshot:]（macOS 欄）→ {'passed': 3}（來源：bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行）
✅ 已回填 [cigate-v030-snapshot:]（macOS 欄）→ {'passed': 3}（來源：bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行）
✅ 已回填 [cigate-scripts-snapshot:]（macOS 欄）→ {'passed': 3}（來源：bash AISDLC_SDD/scripts/ci-gate.sh 的『逐軌計數』自證行）
✅ 已回填 [snapshot-fingerprints-darwin:] → {'v001': '83a9e001afe1', 'v030': '6dca140b0905', 'scripts': 'a39cb8e812af', 'autoclaude': '43ee7bc2885e'} ＋ {'measured-at': '2026-10-10', 'host': 'Darwin-25.6.0-arm64', 'docker': 'down', 'pgextras': 'absent', 'interpreter': '.venv/bin@3.11.15', 'sdk-extra': 'present', 'baseline-origin': 'self-recorded'}
ℹ️ Windows 欄上次量測 2026-10-04（距今 6 天），此後 4/4 棵樹已變動（v001:8ffe3c3dabbd→83a9e001afe1, v030:6d46814f9084→6dca140b0905, scripts:ec35ee2838d0→a39cb8e812af, autoclaude:69fdad8c334d→43ee7bc2885e）——單機交替工作流下這是**結構性常態**、不是新問題——**不計入本機 rc**（本機修不動：回填必須在該平台上實跑）。真正有牙的是**本機平台欄**，見同段的 ✅／❌ 那一行
✅ §7 表② 指紋相符 macOS 欄（v001=83a9e001afe1, v030=6dca140b0905, scripts=a39cb8e812af, autoclaude=43ee7bc2885e）
   [macOS 欄] macOS 欄 provenance 完整：上次量測 2026-10-10（距今 0 天）於 Darwin-25.6.0-arm64
     provenance={'measured-at': '2026-10-10', 'host': 'Darwin-25.6.0-arm64', 'docker': 'down', 'pgextras': 'absent', 'baseline-origin': 'self-recorded'}
     nightly 證據：本機無 AutoClaude/logs/nightly_mac_latest.log——**這只代表本機不是跑該 nightly 的那台機器**（心跳檔 untracked＋14 天輪替，只存在於產出它的機器上），**不得**據此推論該平台沒有 nightly 或沒有真機
     smoke 證據：macos_smoke_local.sh 是 run_local_nightly.sh 的 stage [1/5] ⇒ **不是**第二條獨立證據，其 `===== 彙總：PASS=n FAIL=n SKIP=n =====` 已含在同一輪 nightly 的 RunId log 內；上一行的 nightly 心跳綠即代表該輪 smoke 也跑過
     [autoclaude-pytest-snapshot:] {'passed': 3, 'skipped': 0}
     [cigate-v001-snapshot:] {'passed': 3}
     [cigate-v030-snapshot:] {'passed': 3}
     [cigate-scripts-snapshot:] {'passed': 3}
   [Windows 欄] Windows 欄 provenance 完整：上次量測 2026-10-04（距今 6 天）於 Windows-10-AMD64
     provenance={'measured-at': '2026-10-04', 'host': 'Windows-10-AMD64', 'docker': 'up', 'pgextras': 'absent', 'baseline-origin': 'self-recorded'}
     nightly 證據：本機無 AutoClaude/logs/nightly_latest.log——**這只代表本機不是跑該 nightly 的那台機器**（心跳檔 untracked＋14 天輪替，只存在於產出它的機器上），**不得**據此推論該平台沒有 nightly 或沒有真機
     smoke 證據：本機無 AutoClaude/logs/windows_smoke_latest.log——**這只代表本機不是跑該 smoke 的那台機器**（transcript untracked＋日期輪替）；AutoClaude_WindowsSmoke 每日獨立觸發（獨立於 nightly；時刻現查 `Get-ScheduledTask -TaskName AutoClaude_WindowsSmoke | Get-ScheduledTaskInfo`）。log 落點**存在**：`AutoClaude/logs/windows_smoke_latest.log`（Start-Transcript，R71 起）＋ `windows_smoke_<日期>_<時分秒>.log` 14 天輪替。R74 起本工具**已**把它接成探針，故本行前半段是量測值、這條每日真機證據已在平台覆蓋判定視野內。🔴 但落地產物 untracked、只存在於產出它的那台機器上 ⇒ 「本機無此檔」**不得**讀成「Windows smoke 沒在跑」（DEF-101-756 換載體）
     [autoclaude-pytest-snapshot:] {'passed': 4736, 'skipped': 172}
     [cigate-v001-snapshot:] {'passed': 1478}
     [cigate-v030-snapshot:] {'passed': 1979}
     [cigate-scripts-snapshot:] {'passed': 363}
   ℹ️ 🔴 **本工具不是平台覆蓋的權威**：它只知道「表② 這一欄的數字在什麼環境量的」。「哪一輪在哪個平台跑過真機」請查 docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md §6 逐輪覆蓋表／docs/06_quality/AutoSDD_Defect_Log.md 的「發現情境」欄／ONBOARDING.md §8 nightly（DEF-101-756）
```

### 6.4 cd tools/tests && python -m unittest test_subprocess_encoding_hygiene　→ rc=0
```
.......................................
----------------------------------------------------------------------
Ran 39 tests in 14.817s

OK
```

### 6.5 cd tools/tests && python -m unittest test_context_budget_guard -k Prd　→ rc=0
```
.....
----------------------------------------------------------------------
Ran 5 tests in 0.015s

OK
```

## 7. 附錄（其他親跑輸出，逐字；皆唯讀）

### 附錄 A　矩陣對帳腳本（scratchpad/qa114_countA.py）輸出
```
matrix 2.1 rows: 90  2.2 rows: 11  total: 101
matrix verdict counts (all 101): {'➖': 10, '⚠️': 51, '❌': 11, '✅': 29}
2.1 only: {'➖': 9, '⚠️': 49, '❌': 9, '✅': 23}  2.2 only: {'✅': 6, '➖': 1, '❌': 2, '⚠️': 2}
dup IDs: []
green count: 29  non-green count: 72
PRD 16.2 table rows: 72  (header line 2635 )
cells per row set: {4}
positional verdict mismatches: 0
closure cells in 16.2: {'➖': 33, '⏸': 30, '📎': 9}
cross ➖ {'➖': 10} sum 10
cross ⚠️ {'⏸': 25, '➖': 19, '📎': 7} sum 51
cross ❌ {'⏸': 5, '➖': 4, '📎': 2} sum 11
PRD green list len: 29
green in matrix but not in PRD list: []
in PRD list but not in matrix green: []
wrote /private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/643984e1-5aaf-4196-9e79-db2aea7b37ce/scratchpad/qa114_162_rows.txt
```

### 附錄 B　⏸ 列再開症狀檢查腳本（scratchpad/qa114_B.py）輸出
```
⏸ rows: 30
2638 | §3.2 10 態 FSM＋單向鎖存＋轉移圖             | [SA判讀]   | has再開症狀=Y | 附證據=Y | flags=[]
2639 | §4.1.1 T1（OTel 本機遙測）               | [SA判讀]   | has再開症狀=Y | 附證據=Y | flags=[]
2640 | §4.1.1 T2（逐字稿本機加總）                 |          | has再開症狀=Y | 附證據=Y | flags=[]
2641 | §4.1.1 T3（statusLine 回寫）           |          | has再開症狀=Y | 附證據=Y | flags=[]
2643 | §4.1.1 引擎獨立執行（無 Claude Code sessio |          | has再開症狀=Y | 附證據=Y | flags=[]
2648 | §4.2.3 致動器表：併發／模型降級／任務類別／硬預算       |          | has再開症狀=Y | 附證據=Y | flags=[]
2652 | §4.3 上下文壓縮策略（三 AND）                |          | has再開症狀=Y | 附證據=Y | flags=[]
2655 | §4.4.3 Agent 硬性預算（turns／wall／quota |          | has再開症狀=Y | 附證據=Y | flags=[]
2656 | §4.5.1 凍結流程 7 步                    | [SA判讀]   | has再開症狀=Y | 附證據=N | flags=[]
2657 | §4.5.2 分片休眠＋時鐘跳躍偵測                 |          | has再開症狀=Y | 附證據=Y | flags=[]
2659 | §4.5.4 喚醒策略 AUTO／RESUME／FRESH      |          | has再開症狀=Y | 附證據=Y | flags=[]
2660 | §4.5.10 醒來確認額度 E1～E5               |          | has再開症狀=Y | 附證據=Y | flags=[]
2667 | §6.1 啟動自檢不變式 1～13                  | [SA判讀]   | has再開症狀=Y | 附證據=Y | flags=[]
2671 | §8 列 1 非預期 429（推論端）                |          | has再開症狀=Y | 附證據=Y | flags=[]
2672 | §8 列 2 重置時間漂移                      |          | has再開症狀=Y | 附證據=Y | flags=[]
2673 | §8 列 3 git index.lock 陳舊檢查         |          | has再開症狀=Y | 附證據=Y | flags=[]
2676 | §8 列 9 Agent 卡死／NEEDS_HUMAN        |          | has再開症狀=Y | 附證據=Y | flags=[]
2678 | §8 列 12 Prompt injection           |          | has再開症狀=Y | 附證據=Y | flags=[]
2680 | §9 12 個 Prometheus 指標              |          | has再開症狀=Y | 附證據=Y | flags=[]
2681 | §9 結構化決策日誌                         |          | has再開症狀=Y | 附證據=Y | flags=[]
2682 | §9 告警（DRAINING 以上／DIRTY_UNSAVED／NE |          | has再開症狀=Y | 附證據=Y | flags=[]
2683 | §12 權限旗標（不預設 skip-permissions／bypa |          | has再開症狀=Y | 附證據=Y | flags=[]
2684 | §12 寫入範圍／治理檔禁寫                     |          | has再開症狀=Y | 附證據=Y | flags=[]
2685 | §12 prompt injection／狀態回報 schema   |          | has再開症狀=Y | 附證據=Y | flags=[]
2686 | §12 日誌遮蔽                           |          | has再開症狀=Y | 附證據=Y | flags=[]
2687 | §12 供應鏈（不得無人確認新增依賴／postinstall）    |          | has再開症狀=Y | 附證據=Y | flags=[]
2693 | §15.4 P4 韌性                        | [SA判讀]   | has再開症狀=Y | 附證據=Y | flags=[]
2705 | 施工圖 A4：R108 BurnDown 增補（擬 §4.2.9 清 | [SA判讀]   | has再開症狀=Y | 附證據=Y | flags=[]
2707 | 施工圖 A5c：R112 REQ-W6 喚醒成本治理         |          | has再開症狀=Y | 附證據=Y | flags=[]
2708 | 施工圖 A7：R121 無人續跑受控 commit／push（擬 § |          | has再開症狀=Y | 附證據=N | flags=[]
rows without 再開症狀＝: []
```

### 附錄 E　E501 反向鎖變異自證（scratchpad/qa114_E.py；只在行程內餵變異輸入，不改任何 repo 檔）
```
current ruff.toml                                -> None
(i) current + '到期日：2026-12-31'                   -> tools/ruff.toml 的 E501 存量債豁免又出現日曆到期 '到期日：2026-12-31' —— 掌舵者 2026-10-07
(i') HEAD ruff.toml (old waiver w/ date)         -> tools/ruff.toml 的 E501 存量債豁免又出現日曆到期 '到期日：2026-11-02' —— 掌舵者 2026-10-07
(ii) current minus every '退役到期日'                 -> tools/ruff.toml 的 E501 存量債豁免不再記載「退役到期日」—— 那段記載是「為什麼沒有日期」的唯一答案，刪掉會讓下一個人
blind spot: half-width colon                     -> None
blind spot: slash date                           -> None
blind spot: other wording                        -> None
self-trigger edge: '退役到期日：2026-10-10'            -> tools/ruff.toml 的 E501 存量債豁免又出現日曆到期 '到期日：2026-10-10' —— 掌舵者 2026-10-07
_E501_DEBT_CEILING = 139 | signature: (text: 'str') -> 'str | None'
date.today/datetime.now usages in test file: 0
```

### 附錄 E2　TestRootToolsLintPolicy（-v）
```
test_both_executors_cover_the_claude_hooks_tree (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_both_executors_cover_the_claude_hooks_tree)
test_e501_debt_only_shrinks (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_e501_debt_only_shrinks)
test_root_tools_has_its_own_ruff_config (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_root_tools_has_its_own_ruff_config) ... ok
test_rule_set_is_identical_to_the_autoclaude_side (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_rule_set_is_identical_to_the_autoclaude_side)
test_the_claude_hooks_tree_extends_the_same_config (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_the_claude_hooks_tree_extends_the_same_config)
test_the_config_actually_covers_the_root_tools_tree (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_the_config_actually_covers_the_root_tools_tree)
test_the_e501_waiver_has_no_calendar_expiry_by_decision (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_the_e501_waiver_has_no_calendar_expiry_by_decision)
test_the_no_calendar_criterion_is_red_when_it_should_be (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_the_no_calendar_criterion_is_red_when_it_should_be)
Ran 8 tests in 0.424s
OK
```

### 附錄 F1　python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines（rc=0；摘首尾）
```
# 淨額 115589→115589 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
  …（中間 91 檔逐檔表略）…
# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 115589, 115589, +0, "<理由>"),
# _REPIN_LOG_FROZEN_PREFIX_LEN = 333  # 追加新列後的總列數
#   （下面這個 sha 要在**貼上新列之後**重跑本指令才算得出來；本次印的是尚未追加時的值）
# _REPIN_LOG_HISTORY_SHA256 = "8fea64d22cb14c95456c136ba8eab578d5dbf7ae9a2112a3dc1434b42f98589d"
# [觀測欄][D-4] test 函式數=5291 assert 呼叫數=11314（只印不擋，ADR-XPLAT-013 Phase2 (c) 降級觀測；不接任何棘輪）
```

### 附錄 F2　cd tools/tests && python -m unittest test_adr_xplat001_c1c2_lock（rc=0）
```
----------------------------------------------------------------------
Ran 187 tests in 13.595s

OK
[Scan-H triplet] UEP=5 AC=47 GLC_FILES=91 GLC_LINES=115589
```

### 附錄 G1　gh run list --commit cec520baa895597664896206322369755816744a --json databaseId,name,conclusion,status,createdAt,headSha（rc=0）
```
[{"conclusion":"success","createdAt":"2026-10-09T20:42:07Z","databaseId":37988736282,"headSha":"cec520baa895597664896206322369755816744a","name":"root-infra-ci","status":"completed"}]

```

### 附錄 G2　workflow paths 白名單比對（scratchpad/qa114_G_trig.py；GitHub glob 語意以 ** ／ * ／ ? 近似實作）
```
== commit cec520ba files: ['docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md']
  aisdlc-sdd-ci.yml                  not triggered
  autoclaude-ci.yml                  not triggered
  autoclaude-mutation-on-change.yml  not triggered
  macos-compat-ci.yml                not triggered
  root-infra-ci.yml                  ALWAYS (no paths filter)
  shellcheck-ci.yml                  not triggered
  windows-compat-ci.yml              not triggered
== predicted for current change set: 11 files
  aisdlc-sdd-ci.yml                  not triggered
  autoclaude-ci.yml                  not triggered
  autoclaude-mutation-on-change.yml  not triggered
  macos-compat-ci.yml                TRIGGERED by ['CLAUDE.md', 'docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md', 'tools/ruff.toml']
  root-infra-ci.yml                  ALWAYS (no paths filter)
  shellcheck-ci.yml                  not triggered
  windows-compat-ci.yml              TRIGGERED by ['CLAUDE.md', 'docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md', 'tools/ruff.toml']
```

### 附錄 G3　--unresolved-count、archive --check、ruff
```
外部阻塞軌（AutoSDD_External_Blocked_Log.md，不計入未結列 warn/fail 分母）：5 筆｜DEF-101-693、DEF-101-856、DEF-200-075、DEF-200-253、DEF-200-313
結構性長債軌（AutoSDD_Structural_Debt_Log.md，不計入未結列 warn/fail 分母）：6 筆｜DEF-101-018、DEF-101-398、DEF-101-701、DEF-101-702、DEF-101-960、DEF-101-980
未結列數＝0／全部 209 列｜warn=86 fail=98
判準＝狀態欄 _classify() ∈ ['None', 'open', 'routed']
未結列 ID：
--- archive_defect_log.py --check rc=0（末行）
✅ 帳本保全稽核通過（70 檔／1618 個 ID／12 個「立帳見」指針＋24 個「見主檔／現居」居所指針＋0 個裸「現居」居所註記＋125 處引述；歸檔索引 68 條 bullet 對 68 支 archive）：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針
--- ruff check tools/ .claude/hooks/ rc=0
All checks passed!
```

### 附錄 H1　nightly 錨首個紅燈時刻（以工具自己的 _stamp_problems() 注入時鐘；錨值取 ONBOARDING.md:552）
```
2026-10-19T14:00Z -> ok 
2026-10-20T14:00Z -> ok 
2026-10-20T14:27Z -> RED `nightly-checked-at=2026-10-05T14:26:01+00:00` 已是 15 天前（上限 14 天）⇒ 任一排程通道已逾 14 天沒有 completed run，或回填沒
```

### 附錄 H2　側軌複查日 warn（以 ledger_closing_guards.external_blocked_log_problems 對真帳本注入日期）
```
2026-10-10 external fails/warns = 0 0 | structural fails/warns = 0 0
2026-10-23 external fails/warns = 0 0 | structural fails/warns = 0 0
2026-10-24 external fails/warns = 0 5 | structural fails/warns = 0 6
STALE_REVIEW_DAYS = 14
```

### 附錄 P　預飛：讀根 CLAUDE.md／PRD 的其他模組（皆單跑，非根層全套）
```
test_defect_id_reference_integrity: Ran 11 tests in 3.646s OK
test_check_script_parity: Ran 124 tests in 1.979s OK
test_doc_env_prefix_platform_parity_r60: Ran 13 tests in 0.008s OK
test_negative_existence_claims_r82: Ran 12 tests in 1.729s OK
test_check_pytest_baseline_sites: Ran 20 tests in 3.827s OK
test_mac_readiness_r82: Ran 24 tests in 0.772s OK
test_block_destructive_git_r83: Ran 238 tests in 9.104s OK
AutoClaude/tests/test_r100_boot_self_check.py: 42 passed in 1.04s
sync_onboarding_baselines.py --check-snapshot rc=0；--check rc=0（末行：✅ [rootunit-baseline-live:] {'tests': 5273}（來源：tools/run_root_unittests.py 的 MIN_TESTS））
```

### 附錄 ghost　新增文字（PRD／範本／R211〈八〉／ruff.toml／improving_114）的幽靈符號普查
```
== MISSING PATH-LIKE TOKENS ==
PRD ['--permission-mode acceptEdits --settings .claude/settings.unattended.json', 'autosdd_quota_degraded.jsonl', 'model_roles.py', 'quota_burn.jsonl', 'resume_route.py']
TEMPLATE ['AutoSDD_improving_NN.md', 'docs/06_quality/AutoSDD_ZeroTrust_Audit_{{N}}.md']
IMPROVING_114 ['python tools/run_root_unittests.py', 'test_adr_xplat001_c1c2_lock.py', 'test_r100_boot_self_check.py']
identifier candidates: 115
== IDENTIFIERS WITH ZERO HITS IN CODE/TOOLS TREES ==
  ALERT_WEBHOOK_URL ['PRD']
  ALLOW_PERMISSION_BYPASS ['PRD']
  API_AUTO_CONTINUE ['PRD']
  AUTH_MODE ['PRD']
  AUTOSDD_QUOTA_BURNDOWN ['PRD']
  AUTOSDD_UNATTENDED_PUSH_OFF ['PRD']
  CLAUDE_CODE_ENABLE_TELEMETRY ['PRD']
  CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS ['PRD']
  CLOCK_JUMP_TOLERANCE_SECONDS ['PRD']
  COMPACT_MIN_INTERVAL_SECONDS ['PRD']
  DRAIN_BUDGET_FACTOR ['PRD']
  FIVE_HOUR_PACE_CEILING ['PRD']
  HALTED_MANUAL ['PRD']
  MAX_INPROCESS_WAIT_SECONDS ['PRD']
  MAX_STEP_QUOTA_PP ['PRD']
  MAX_STEP_TURNS ['PRD']
  METRICS_EXPORT ['PRD']
  NEEDS_HUMAN ['PRD']
  OTEL_ ['PRD']
  OVERAGE_ALERT_ON_FIRST_USE ['PRD']
  PACE_MIN_UTILIZATION ['PRD']
  PACING_MODE ['PRD']
  PREPARE_PCT ['PRD']
  REDACT_SECRETS_IN_LOGS ['PRD']
  RESET_BUFFER_SECONDS ['PRD']
  RESET_CONFIRM_PERCENT ['PRD']
  RESET_DROP_THRESHOLD ['PRD']
  RESUME_MAX_TRANSCRIPT_TOKENS ['PRD']
  T_MIN ['PRD']
  V_safe ['PRD']
  WEEKLY_DRAIN_PERCENT ['PRD']
  WEEKLY_HALT_PERCENT ['PRD']
  burn_down ['PRD']
  daemon_id ['PRD']
  otlp ['PRD']
  prometheus ['PRD']
  quota_snapshot ['PRD']
  resume_plan ['PRD']
  weekly_warn ['PRD']
  zzzz ['PRD']
```

---
（本檔由 QA 零信任複審鏡唯讀產出；repo 零寫入。逐字輸出皆取自本場 tool_result 導出的 scratchpad 檔。）

---

## 7. 複驗（二審；驗修復，不重做一審）

> 註：上方既有「## 7. 附錄」是一審附錄、保留不動；本節是二審，章內編號一律以 §7.x 標示。基準：HEAD 仍是 `cec520ba`；工作樹＝14 個異動（12 個 ` M`＋improving_114 與 audit_114 兩個已 staged 的新檔，`git status --short` 現查）。

### 7.0 判決

**VERDICT: APPROVE**（前提：commit 前完成 §7.8 第 1～3 項「待主控最後一棒」＝PRD 修訂表 L22 的審查描述、improving_114 §5 收尾回填、L53 全套格重確認，尤其 L22；若 L22 仍寫「一面 Sonnet QA 唯讀鏡複審」就 commit，一審 F-02 所指的「審查規模描述不實」會在 PRD 本體復活，屆時應改判 P2）

- **P1／P2：無。** 一審三條 P2（F-01／F-02／F-03）全部消失，逐字對照見 §7.1；Architect 鏡的 P2（ARCH-01，審查閉環無終止語意）的修復我也一併驗過，見 §7.1 末。
- PASS 的定義是「無 P≤2」（範本〈審查閉環的終止〉），不是零發現；P3×7、P4×5 依範本當輪改字或登記，**本二審即終審**，改字後不需第三審（§7.8）。
- 二審新發現：**P3 × 7（N-01～N-07）、P4 × 5（N-08～N-12）**，皆為文字精度或登記，無一阻擋結案；建議同批順手修（見 §7.3）。
- 一審 P3-01～P3-11 逐條驗修復（§7.2）：11／11 落地（P3-09 (i) 的 PRD L22 屬已知待辦，列 §7.8）；P4-01～P4-07 皆有歸宿（登記〈三〉或就地訂正）。

### 7.0.1 範圍與誠實劃界

- **唯讀**：repo 零寫入（我寫的只有 scratchpad 內 `qa114b_*`／`qa114c_*`／本檔；§7.7 起另以 `git status --short` 複核仍是 14 項）。沒跑根層全套（背景跑中）、AutoClaude／SDD 全套；沒打任何端點（二審期間未呼叫 gh；一審的 `gh run list` 見一審附錄 G1）；沒跑額度配速指令。單跑測試模組時 `TMPDIR` 指到 scratchpad 子目錄（避免碰真實 TEMP 圍籬）並以 `nice -n 19` 執行（避免搶背景全套的 CPU）。
- **一項我無法排除的干擾面**：純讀工具（carriers／crossref／archive／anchor／ntfs／ruff 與我的 python 小腳本）沒有隔離 `TMPDIR`，我沒有量測它們是否寫過系統暫存；若背景全套尾行的「真實 TEMP 圍籬」出現非零變動，請先排除是否為本鏡這幾個工具所致，再下結論。
- **不重做一審**：沒有重判 `[SA 判讀]` 18 列的歸格；對 Architect／SA／SD 三鏡的 findings，我只驗三件事——(1) 編號與級別計數是否與 improving_114 §5 的宣稱相符、(2) 宣稱的處置落點是否真的存在且說的是那件事、(3) 修訂後的文字有沒有又比實況強。對 PRD §16.2 的修訂列，我以「讀列＋現查程式碼／帳本／證據檔」抽驗（所抽的列見 §7.2、§7.5 與附錄），不是逐列重審；另以腳本對 72 列做了結構性全檢（列數、格數、矩陣判定欄位置對照、✅ 清單雙向）。
- **逐位元組驗得了的只有我自己那份**：audit_114〈二-1〉（L19–592）與我一審原檔（574 行、71,440 bytes）逐位元組相同（附錄 R-B）；其餘三份我無原檔可比，只能驗上述 (1)(2)(3)。

### 7.1 (a) 一審三條 P2：逐字對照（消失與否）

**F-01（「13 條理論洞全部落在 §16.2」）——已消失**

- 舊句（一審引）：improving_114 原 L65 `3. 本檔無「下一輪候選」：improving_113 的四項「刻意沒做」與 R211〈三〉13 條理論洞全部落在 §16.2 的 ⏸（附再開症狀）或 ➖（附依據）✓`；原 L12 `全部改寫進 PRD v2.1.17 §16 結案帳…`。現查：`grep -rn '全部落在 §16.2\|全部改寫進 PRD v2.1.17' docs CLAUDE.md tools`（排除 audit_114 的逐字保全）＝零命中。
- 新句三處互相一致：improving_114 L12（§1 表）＝「…13 條理論洞：#1／#2／#3／#4／#7／#8／#9 七條各有 §16.2 ⏸ 列承接；#11 由 §16.4 完成；#5／#6／#10／#12／#13 五條為實作面或流程面 P4、無對應 PRD 列，再開症狀維持住在 R211〈三〉並由 PRD §16.5 (iii) 明文認該表為同款觸發源」；improving_114 L94（§8 判準 3）＝「R211〈三〉13 條理論洞 7 條有 §16.2 ⏸ 列、1 條由 §16.4 完成、5 條留在〈三〉並由 §16.5 (iii) 接線」；R211〈八〉L142＝「〈三〉13 條理論洞的歸宿（逐條）…」；PRD §16.5 (iii)（L2759）＝「`CrossPlatform_R211_ZeroTrust_Audit_113.md`〈三〉理論洞表中**沒有**對應 §16.2 列的條目（#5／#6／#10／#12／#13）以其「再開症狀」欄為同款觸發源」。
- 機械重驗（附錄 R-F01）：以腳本解析新版 PRD §16.2（72 列），`〈三〉#n` 引用去重＝{1,2,3,4,7,8,9}，七個被引列（§4.2.3、§3.2、§4.5.2×2、§4.1.1 引擎、§12 寫入範圍、施工圖 A5c）結案格**全為 ⏸**；PRD 全檔去重亦同。⇒ 「7 條各有 ⏸ 列」逐字成立。

**F-02（審查規模依據與其引用的規則相反）——已消失（改走四方，比我一審給的兩條路中較輕的那條更重）**

- 舊依據：improving_114 原 L42 `依範本〈🏁〉瘦身規則走 1 面 QA 鏡`、原 L59 `走 1 面 QA 零信任鏡`。現查：improving_114 全檔 `grep '瘦身規則走 1 面\|走 1 面 QA'` ＝零命中；repo 內唯一殘留的「一面 Sonnet QA 唯讀鏡複審」是 PRD 修訂表 L22（主控已告知待改，§7.8 (1)）。
- 新做法：improving_114 L42（§3 設計期誠實劃界 (5)）＝「本輪是終輪＋PRD 修憲，依範本〈🏁〉自己的規則走四方（非瘦身規則的 1＋1）」；L59（§5 標題）＝四方零信任審查閉環；證據檔 `docs/06_quality/AutoSDD_ZeroTrust_Audit_114.md` 存在（1531 行），〈二〉含四份 findings。**計數與 §5 宣稱吻合**（腳本計 `### <ID> [P?]` 標題）：Architect P2×1／P3×9（ARCH-02～10）／P4×8（ARCH-11～18）；SA P3×11（SA-01～11）／P4×2（SA-12／13）；SD P3×6（SD-01～06）／P4×3（SD-07～09）。§5 表欄位與 ADR-XPLAT-013 §7.1 的具名記錄表（`角色／審查者／結論／日期／範圍／條件／證據`）同體例，主控列同樣註明「提案者，不投票」。
- 殘留（已知）：PRD L22；以及 improving_114 L63 QA 列結論／L67／L69 的佔位（§7.8）。

**F-03（「沒有任何待辦會自動長出來」）——已消失**

- 舊句：improving_114 原 L76 `…在掌舵者立案前，本 repo 沒有任何待辦會自動長出來。` 現查全 repo（排除 audit_114）零命中。
- 新文：improving_114 L89（§7 第 3 點）＝「在上述立案之前，本 repo 沒有任何**需要人判斷的待辦**會自動長出來；會自動出現的只有 §6 表列的機器產物…」；§6 L72–79 四列「仍在走的機器時鐘」表；範本 L364 條列三個時鐘（①nightly 錨 14 天、②root-infra-ci 陳舊度哨兵 10 天、③側軌複查 14 天 warn）並明寫「預期產物，不是待辦、不是 T3」；側軌 warn 的退役登記為 audit_114〈三〉#1（附再開症狀）。
- 事實核對（新文裡每個可驗的時鐘宣稱）：錨——`ONBOARDING.md:552` 取樣時刻 `2026-10-05T14:26:01+00:00`、`NIGHTLY_MAX_AGE_DAYS = 14`，我一審以工具自己的 `_stamp_problems()` 注入時鐘實測首個紅燈在 2026-10-20T14:27Z（improving_114 §6 表只寫「閒置 ≥14 天後第一次 push 被擋」、未寫死日期，不衝突）；陳舊度哨兵——`.github/workflows/root-infra-ci.yml` 腳本逐條讀過：取 `windows-compat-ci.yml`／`macos-compat-ci.yml` 各自 schedule 與 workflow_dispatch 兩事件最近一次 **success**、較新者算天數，`age > MAX_AGE_DAYS(10)` 即 `::error::`（有豁免才降 warning）、`WAIVER_UNTIL: ""`——「近 10 天無成功 run 時 push／PR 轉紅」成立；側軌 warn——`STALE_REVIEW_DAYS = 14`，真帳本注入日期 2026-10-23 → 0 warn、2026-10-24 → 5＋6＝11 條（improving_114 L78 的「2026-10-24 起…11 條」成立）；CLI 清單——本機 `claude --version` 2.1.296、清單最新 2.1.295。GitHub 60 天停排程一句寫明「平台行為，未驗證」，沒有被寫成事實。
- 殘留 → N-02（§7 第 3 點末句「處置都是一條指令」只對錨成立）。

**Architect 鏡 ARCH-01（P2）修復——一併驗過，成立**

- 範本 L292 標題改為「（強制，無 P≤2 才准結案；終止口徑見〈🏁〉〈審查閉環的終止〉）」；L324 步驟 2 改為「P≤2 發現…徹底修完；P3 當輪改文字或退役、P4 只登記」；L326 步驟 3 改為「複審至多二審（一審全查、二審驗修復），PASS＝無 P≤2，不是零發現」；新節〈審查閉環的終止〉（L370）：PASS＝無 P≤2、複審至多二審（引 `TechDebt_Paydown_Cycle_Prompt.md`〈4. 品質與驗證〉L109「一審全查、二審驗修復」——該行存在）、P≤2 口徑分兩套（產品／文件輪 vs 守衛面暴露度口徑，引 `severity.md`——該檔存在且 P2＝「且有暴露證據」）、「對擴張中的面做對抗搜尋沒有不動點」（引根 CLAUDE.md〈守衛面准入〉R179～R196，該節存在）。與 `severity.md` 的 P2／P3／P4 定義無衝突。

### 7.2 一審 P3／P4 逐條驗修復

| 一審 ID | 修復落點（現查） | 結果 |
|---|---|---|
| P3-01 | improving_114 L21 ＝「（HEAD 2699 行）自 2026-08-14 起修憲 16 次」；§6 末也註「R211 矩陣撰寫時 2657，QA P3-01 訂正」 | ✓ |
| P3-02 | `tools/tests/test_adr_xplat001_c1c2_lock.py:3678` 接鏈列 `("R211","d034314bdd87","8fea64d22cb1","DEF-200-504")`；DEF-200-504 帳列（`AutoSDD_Defect_Log.md` L277）＝「宣告收斂後有期限的維護義務（…ONBOARDING §7 表③ nightly 錨的 14 天過期帶）」closed-by-decision（2026-10-07），內容與日期型義務退役同源；`tools/ruff.toml:71` 只寫「（舊註記引 DEF-101-791）隨之退役」、不再暗示內容關聯；R211〈八〉L139 明寫「舊註記引的 DEF-101-791 帳列內容為歸檔死結、與 E501 無內容關聯，故不沿用」。接鏈列只改 DEF-ID、sha 不變（`8fea64d22cb1`）。 | ✓（比我建議的「補半句」更好：改掛內容相符的 DEF） |
| P3-03 | PRD L2640（T1）症狀改為「`autosdd_quota_degraded.jsonl` 出現 `state` 為 unmeasured 的列…或 `quota_burn.jsonl` 相鄰列出現超過 5 小時的空洞，且同一窗內有人明示需要逐 token／逐請求的成本明細…」——現查 `tools/lib/quota_gate.py:205` `QUOTA_TRACE_NAME = "autosdd_quota_degraded.jsonl"`、`:685` 寫入 `"state": quota_policy.BAND_UNMEASURED`（值 `"unmeasured"`），欄位屬實；L2660（§4.5.4）改為「週軸讀數已達實作的 converge 帶（門檻鍵與出廠值現查 `python tools/lib/quota_policy.py --print-env-example`；條文的 `weekly_warn` 在實作面零命中）」；L2679（§8 列 12）改為「無人窗口逐字稿中出現…對外 URL 呼叫（curl／wget／requests 等字樣與目的網址可逐字引用；附 sid＋逐字稿座標）」 | ✓ 三處皆改成可現查形態 |
| P3-04 | L2689（§13）改 ⏸，現況句「人工（法務）檢核從未發生…不以 📎 計入落地」，再開症狀＝「收到 Anthropic 使用條款變更通知、帳號警告或任何對自動化用量的官方詢問（附原文），或掌舵者決定上線前親自檢核（附落款）」；§16.3（L2711 起）重算為 ✅29／➖33／⏸31／📎8、(c)＝37÷68＝54.4%，「讀法」改寫為「§11.1 與 §11.8 是尚未發生的長跑證據，仍計入 (c) 分子——這是 (c) 偏高的方向；§13…列 ⏸ 不計入落地」；修訂表 L22 同步 | ✓（數字重算見 §7.5-C） |
| P3-05 | L2670（§6.2 R-6.2-2）末加「**誠實揭露**：此殘留每次 CLI 升版即重現、無終點（版本號型永動源）；未驗證版本的後果＝每次啟動一則桌面通知＋略過已合併 worktree 清理，不影響執行；把「不在清單」從 loud 降為單行 log、或改以能力探針取代精確版本比對，屬 AutoClaude 設計變更，依 §16.5 (i) 由掌舵者立案」；L2680（§8 列 13）同步「每次升版即重現、無終點，見該列誠實揭露」；audit_114〈三〉#14 登記 | ✓（歸格仍是 📎，但揭露句涵蓋了我指出的 (i)(ii)；(iii)「(c) 計入」見 N-08） |
| P3-06 | 根 `CLAUDE.md:38` ＝「2026-10-10 掌舵者授權主控代決、非明示追認，掌舵者可隨時以 T1 推翻；improving_114 終輪」；PRD 修訂表 L22 ＝「各列歸格＝主控代決（掌舵者授權「依最佳理想化代為決策」，非逐列明示追認；掌舵者可隨時以 §16.5 (i) 推翻任一格）」；`tools/ruff.toml` 條 2 ＝「掌舵者授權主控代決；原則＝掌舵者 2026-10-07 裁決」；improving_114 L5（開場指令段末句）＝「掌舵者授權主控代決（非逐項明示追認…）」 | ✓ |
| P3-07 | 範本 L41 ＝「…防跨軌誤指；「下一份檔名」義務已由〈🏁〉節退役」；範本 L429（設計說明表）＝「每輪標示在哪一柱（A/B/C）；「下一份檔名」自〈🏁〉節起不再是義務」；improving_113.md L224／L225 行尾加「（史料：…）」註記 | ✓ |
| P3-08 | PRD L2630（§16.1〈邊界〉）新增「**母體外章節**（不入 101 列，亦不構成未結項）：§0／§0.6…§14…§15.1～§15.3 與 §15.6～§15.8 執行方法論（含 Daemon 形態的目錄結構建議）、附錄 A／B…其中規範性內容已由母體列承接（例：§15.1「超額用量」由 §15.4 P4 列、§15.6 失敗模式表由 §8 各列）」 | ✓ |
| P3-09 | (ii) findings 落檔：audit_114〈二〉存在，我的部分逐位元組相同（附錄 R-B）；(i) PRD L22 審查描述 | (ii) ✓；(i) 待主控最後一棒（§7.8） |
| P3-10 | 範本 L364–368 ＝「…該機專屬待驗清單（如 Windows 真機項）＝非再開事件：不開輪，只在該機做該機的事」；improving_114 L81 ＝「Windows 真機待驗清單（R211 證據檔〈六〉、R210〈八〉）＝**非載體、無義務**…（範本〈休眠期間〉已明寫；證據檔〈三〉#6）」；audit_114〈三〉#6 | ✓ |
| P3-11 | improving_114 L42（§3 誠實劃界 (4)）＝「…QA 鏡獨立重算確認淨額 +0、187 支鎖 OK；掌舵者授權代決已涵蓋此重釘，若掌舵者另有意見以其為準」 | ✓ |
| P4-01 | audit_114〈三〉#7（再開症狀＝一次重釘被該標籤 cap 夾住）；容量數字我以鎖檔函式重算吻合（附錄 R-RATCHET：R211 主軌 469／cap 517 餘 48、回歸鎖軌 309／309 餘 0） | ✓ |
| P4-02／03 | 〈三〉#8／#9 | ✓ |
| P4-04 | R211〈八〉L140 已改為「白名單在 `docs/06_quality/` 下只點名 `CrossPlatform_Maturity_Criteria.md` 與 `FiveQuestion_Audit_Protocol/params.json` 兩個具名檔」（就地訂正，非登記） | ✓ |
| P4-05 | 範本 L354（T2 走哪軌）、L355（T3 先入帳再依 T2 判）、L337–339（三態：只評估一次、宣告後只由 T1～T4 改變）、L348–351（立案須同輪 fixed／closed-by-decision 或落側軌，否則判準 2 不成立）——就地訂正；PRD §16.5 標題與 (ii) 補「CI／nightly 轉紅、經入帳而根因在本 PRD 機制者亦屬本款」 | ✓ |
| P4-06／07 | 〈三〉#10／#11 | ✓ |

**一審 P2 以外的間接修復，我另驗了這些（皆成立）**：improving_114 L4 兩個鐘的說明、ADR-XPLAT-010 L50 增補（錨定在 L48 真實存在的「豁免到期日機械核對」一句）、`AutoSDD_Defect_Log.md:54` 格式說明改為「入帳本表、不預開下一輪（2026-10-10 起；再開＝範本〈🏁〉T2）」、CLAUDE.md L28／L32／L35 三處（標題「系列休眠時「下一份」欄無義務」、① 列「下一份」欄「系列休眠時本欄無義務，先查範本〈🏁〉T1～T4」、(附) R 系列列改以 `check_handoff_carriers.py` 首行 `[census] 當前輪＝R<N>`＋1 現查並註明「不是休眠的後門」——該首行格式與我實跑輸出逐字相符）。

### 7.3 (b) 修訂後宣稱 vs 實況：新發現（P3；皆文字精度，無一阻擋）

**N-01 [P3]** improving_114 L92（§8 判準 1）「…且經 SA／SD 鏡逐列覆核 ✓」比實況寬。實況：SA 鏡覆核 ➖ 33＋📎 8＝41 列的依據與承接、SD 鏡覆核 ⏸ 31 列的現況與症狀，合計 72 列；✅ 29 列沿用矩陣原判、兩鏡皆未覆核（SA 鏡自述「沒重判 ✅ 的 29 列」）；SD 鏡自述「沒有重判 101 列的四選一歸格結論…`[SA 判讀]` 六列仍只有作者自審＋本鏡的事實對照」；SA 鏡另自述逐列重判了 `[SA 判讀]` 18 列中落在 ➖／📎 的 12 列歸格（audit_114 L886），所以「歸格判斷只有作者自審＋事實對照」的是 6 列 ⏸ `[SA 判讀]`（§3.2、§4.1.1 T1、§4.5.1、§6.1、§15.4 P4、施工圖 A4；audit_114 L886）。同檔 L42（§3 (1)）寫得精確（「SA 鏡逐列核 ➖ 33 列與 📎 8 列…SD 鏡逐列核 ⏸ 31 列現況…`[SA 判讀]` 標記保留，以示該列為判斷而非事實」），但休眠宣告是最後被讀的那句。修法：L92 改為「（➖／📎 41 列經 SA 鏡、⏸ 31 列經 SD 鏡逐列核依據與現況；✅ 29 列沿用矩陣原判；歸格判斷仍為作者判讀＋主控代決）」。（我的嚴重度判斷：一審 F-01 是 P2，因為該句在判準本體內且「全部」可被機械反駁；本條是結論句的縮寫、且同檔 §3 (1) 已精確揭露，故 P3。）

**N-02 [P3]** improving_114 L89（§7 第 3 點）「會自動出現的只有 §6 表列的機器產物，處置都是一條指令」——只對第 1 列（錨：`--check-head`＋`git add ONBOARDING.md`）成立；第 2 列（陳舊度哨兵）紅時的處置是 `gh workflow run windows-compat-ci.yml`／`macos-compat-ci.yml`（腳本自己印出，確為指令，但屬兩條且要等 run 完成）；第 3 列（側軌 warn）與第 4 列（CLI 清單）的處置是「建議退役、掌舵者立案」，不立案就是持續出聲、沒有一條指令能讓它消失。修法：改為「多數處置是一條指令（錨、陳舊度哨兵）；側軌 warn 與 CLI 清單兩列需掌舵者立案才會消失，不立案只是持續出聲（rc 不變、不影響執行）」。

**N-03 [P3]** improving_114 L57（§4「雲端」列）「PRD／CLAUDE.md／`tools/tests/**` 皆在 macOS／Windows compat 的 `paths` 白名單 ⇒ **四支** gating workflow 都會跑」——依目前工作樹的 14 個異動以各 workflow `on.push.paths` 比對（附錄 R-G）：只觸發 root-infra-ci（無 paths 過濾）、macos-compat-ci、windows-compat-ci **三支**；autoclaude-ci 不觸發（它的白名單是 `AutoClaude/**`、`tools/lib/**`、`tools/_stdio_utf8.py`、`tools/check_defect_log_crossref.py`、SDD 三個凍結版，本變更集一個都沒碰）；aisdlc-sdd-ci、shellcheck-ci 亦不觸發。「四支」是 R211 那輪（改了 `AutoClaude/`）的舊數字。影響：push 後主控若期待四支 run，會把缺席的 AutoClaude CI 誤讀成失敗或漏跑。修法：改「root-infra-ci／macos-compat-ci／windows-compat-ci 三支會跑；autoclaude-ci 因零 `AutoClaude/**`／`tools/lib/**` 異動不觸發」。

**N-04 [P3]** 「P4 全部登記〈三〉」的涵蓋面說得過頭（兩處同型）：improving_114 L94（§8 判準 3）「本輪四方 P4 全部落在 `AutoSDD_ZeroTrust_Audit_114.md`〈三〉理論洞清單」與 §5 L63（QA 列）「P4-01～P4-07 登記證據檔〈三〉」。實況：〈三〉#1～#15 涵蓋 QA P4-01／02／03／06／07、ARCH-11／12／15／17／18、SA-12／13、SD-07／08／09；其餘是就地處置——QA P4-04（R211〈八〉就地訂正）、QA P4-05（範本 T2／T3／三態／立案語意）、ARCH-13（PRD §16.5 末句）、ARCH-14（improving_114 自帶標記刪除）、ARCH-16（範本 WHY 改為 10-07 原話逐字）。§5 的 Architect 列自己已註明 ARCH-13／14 的去向，但 §8 與 QA 列沒有。同段 L94 還有第二處：「improving_113 的四項『刻意沒做』落在 §16.2 ⏸ 列」——四項中三項是 ⏸ 列、**一項（PRD 12 筆修憲整理）在 §16.4**（§1 L12 寫得對，§8 縮寫成全是 ⏸ 列）。修法：L94 改「…四項（三項在 §16.2 ⏸ 列、PRD 12 筆修憲整理在 §16.4）…；本輪四方 P4 落在〈三〉或已就地處置（§5 表）」。另 §5 L63 QA 列把 F-01 的落點寫成「§1／§6 改寫」，實為 §1 L12 與 §8 L94（§6 是機器時鐘表）——改「§1／§8」。

**N-05 [P3]** 範本承認〈理論洞清單〉為第二種「延後」載體（L348：「**延後**（PRD 結案帳 ⏸ 列，或本輪證據檔〈理論洞清單〉列——限 P4——各附一句**可觀測**的再開症狀）」），但〈再開觸發〉沒有對應接線：T4（L356）只認「PRD 結案帳某 ⏸ 列的再開症狀」；PRD §16.5 (iii)（L2759）只點名 R211〈三〉的五條。結果＝audit_114〈三〉#1～#15 的「再開症狀」欄（audit_114 L1512 標題寫「再開＝各列『再開症狀』欄」）沒有任何條文說「症狀發生時走哪條觸發」。實務上它會經 severity.md 的暴露度規則升為 P2、入帳、依 T2 判，但這條路徑沒寫在範本裡。修法（一句）：T4 或判準 3 補「〈理論洞清單〉列的再開症狀實際發生＝依 `severity.md`〈暴露度〉升 P2 並入帳，依 T2 判」。

**N-06 [P3]** improving_114 L53（§4「根層 tools/tests 全套」格）的證據時態：該格已填「`✅ unittest 數量下限釘選通過：發現 5273 個測試（下限 5273）`，ROOT_RC=0；skip 47 支全數有標籤（platform=47、欠債型 0）；`✅ 真實 TEMP 圍籬：…零變動`」，而 §4 標題寫「收尾單人窗口、最終工作樹、主控親跑」。我能獨立驗到的只有**發現數**：以 runner 自己的 `discover_suite()` 在當前工作樹做 discover-only（不執行任何測試；附錄 R-DISC）得 `countTestCases=5273`、`MIN_TESTS=5273`、佔位測試 0 ⇒「發現 5273／下限 5273」在當前樹成立。`ROOT_RC=0`、skip 47（platform=47）、TEMP 圍籬零變動三項只能由全套執行本身產生；背景全套此刻仍在跑，我無從核對該格取自哪一棵樹。這不是缺失（主控已告知會等全套跑完）；處置＝背景全套完成後逐字比對已填值（rc、發現數、skip 數、圍籬行），任一不同即重填；全套尾行才是證據、不是本鏡的口頭背書。列 §7.8 (3)。

**N-07 [P3]** improving_114 §5 L67–69 的收尾佔位：「主控｜…全部 P2／P3 處置後請 QA 鏡複驗（結果見本列下註）」＋「複驗：（收尾回填：QA 複驗）」＋ QA 列結論「CONDITIONAL → P2 全數處置」。待本次 VERDICT 後回填（建議字面：QA 鏡「CONDITIONAL → 二審 APPROVE（P1／P2 無；二審 P3×7、P4×4 同批處置）」）。列 §7.8 (2)。

### 7.4 新發現（P4；只登記）

- **N-08 (c) 的 📎 分子構成只點名了 8 列中的 2 列**：PRD §16.3「讀法」（L2729）只把 §11.1 與 §11.8 說成「計入 (c) 分子的長跑證據」；§16.2 的 📎 共 8 列（§6.2 R-6.2-2、§8 列 13、§11.1、§11.2、§11.3、§11.7、§11.8、§15.5），其餘 6 列同樣計入分子、讀法未提——其中 §6.2 R-6.2-2 與 §8 列 13 兩列是無終點的 CLI 清單維護面（兩列自己已誠實揭露）。(c) 已明寫「偏高的方向」且「不是給人追的目標」，影響只在精度；一句話可補全：「📎 8 列全數計入分子（含 CLI 清單兩列與 §11.2／§11.3／§11.7／§15.5）」。
- **N-09 範本「兩個鐘」節的兩處精度**：範本 L381 起 (b)「餘裕現查 `repin_growth_problems`」——該函式回傳的是問題字串（超 cap 才有內容），不是餘裕；餘裕＝`net_cap_for_round(標籤)` 減該標籤主軌淨額（總淨額減回歸鎖軌淨額）與回歸鎖軌 cap（我以這些函式現算 R211：517−469＝48、309−309＝0，附錄 R-RATCHET）；`--print-guard-lines` 只印總淨額。(c)「兌現到期列＋Phase-2 列」——`phase2_review_problems` 的紅燈條件是 `live > due`（due＝末列 208＋視窗 5＝213 ⇒ 標籤 ≥214 才紅），第一個新標籤 R212 只需兌現 (212,516)（`net_cap_for_round(212)` 現為 517、`_REPIN_NET_CAP_DUE_TARGET`＝516，款(12)「到期未下修」以 `live_round >= due_round` 判）；Phase-2 列是 R213／R214 的事。「只有追加標籤 ≥ 下一輪的重釘列才會喚醒它們」作為**必要條件**成立，不是充分條件。
- **N-10 休眠期間時鐘清單三 vs 四**：範本 L364 條列三個機器時鐘（錨、陳舊度哨兵、側軌 warn），improving_114 §6 表列四個（多 CLI 清單）；CLI 清單只影響 `python -m autoclaude` 啟動雜訊，不在 push／crossref 路徑上，分列有理，但兩處數字不同、讀者會問。可在範本補「④ CLI 已驗證清單漂移（只影響 AutoClaude 啟動通知；見證據檔〈三〉#14）」。
- **N-11 audit_114 的圍籬結構**：新檔 233,455 bytes；〈二〉四份原文各以四反引號圍住，內含大量三反引號（我那份 36 行）。CommonMark 下安全；若某個掃描器以「任一行以三反引號開頭即翻轉圍籬狀態」的樸素方式判斷，會與內層圍籬失同步（附錄 R-C：L862 在樸素判法下落在圍籬外、CommonMark 判法下在內）。目前沒有任何掃描面這樣讀這個檔（carriers 的 glob 不含它、`defer_rounds` 對全檔零命中；docfresh／crossref／archive 皆綠），僅登記：日後若把 `docs/06_quality/AutoSDD_ZeroTrust_Audit_*.md` 納入任何新掃描面，需先處理嵌套圍籬。
- **N-12 §7 建議理由沒有證據座標**：improving_114 L87「主控建議北極星 **A 柱**…因為三點北極星中只有它尚未被真實使用驗證過」是主控判斷（句首已標「主控建議」），沒有附座標說明 B／C 柱「已被真實使用驗證」的判準；我只查到旁證（improving_111／112／113 的抬頭皆寫「A 柱 無」，與該句不衝突），不足以證實或證偽。不影響結案；可在該句加「（主控判斷）」。

### 7.5 (b) 四項指定核對——修訂後的宣稱 vs 實況

**(b-1) improving_114 §5 表（L59–69）**
- 吻合：四面 VERDICT 與 audit_114〈一〉表逐列相同（QA／Architect＝CONDITIONAL、SA／SD＝APPROVE；各鏡原文的 VERDICT 行 audit_114 L26／L606／L890／L1208 亦同）；P 級計數＝§5 宣稱（附錄 R-CNT：Architect P2×1／P3×9／P4×8、SA P3×11／P4×2、SD P3×6＋表列 P4×3；QA 見一審 §0）；表頭體例＝ADR-XPLAT-013 §7.1 具名記錄表，主控列註「提案者，不投票」。
- 處置落點逐項找過（皆存在、且說的是該件事）：QA 列 11 條（§7.2）；Architect 列 L64 的 12 個處置片語——證據檔用範本原名（範本 L382）、宣告移至末節（improving_114 §8 L91）、兩個鐘與三條路（範本 L381–391）、三態鎖存（範本 L337–342）、延後載體與判準 1 通式（L345／L348）、⏸ 觀察者（L356＋PRD L2759）、覆蓋度不重盤（L378）、T3 併入 T2（L355）、三個機器時鐘揭露（L364–368）、ADR-010 增補（ADR-010 L50）、本表＝ADR-013 §7.1 體例、不另立 ADR（§5 表本身即決策記錄）；SA／SD 列各抽 PRD 落點 3～4 處（§4.6、§15.4 P4、§4.1.1 T1、§4.5.4）皆在。
- 殘留：N-04（L63 的「§1／§6」與「P4 全登記〈三〉」）、N-07（L63／L67／L69 佔位）。另建議 L64 結論欄補「（ARCH-01 修復經 QA 二審驗證）」——Architect 鏡自己沒有二審，驗證者是本鏡，如實寫出處。

**(b-2) §8 三條（L91–94）與結語段（L96）**
- 判準 1：「101 列全部歸格、無未分類列」機械成立（附錄 R-A：§16.2 共 72 列、每列恰 4 格、無重複 ID、✅ 29 清單與矩陣雙向零差、29＋72＝101）；後半句「經 SA／SD 鏡逐列覆核」比實況寬 → N-01。
- 判準 2：`--unresolved-count`＝0 逐字相符（§7.7 重跑：「未結列數＝0／全部 209 列｜warn=86 fail=98」，rc=0）。
- 判準 3：數字 7＋1＋5＝13 與 §1 L12、R211〈八〉L142、PRD §16.5 (iii) L2759 三處一致；「四項落在 §16.2 ⏸ 列」與「P4 全部落在〈三〉」兩處說過頭 → N-04。
- 結語段（L96）：「宣告後狀態不因時間、版本、覆蓋度數字或未結列數事後 >0 而改變」＝範本 L340；「沒有『下一份檔名』義務」＝範本 L358／L429、CLAUDE.md L28／L32；「北極星不因此視為達成」＝範本 L339——三處皆一致。

**(b-3) PRD §16.3 三個數字與交叉表**——全部成立（附錄 R-A）
- (a) 60.3%：矩陣 §1.1（`CrossPlatform_R211_PRD_Coverage_Matrix_113.md` L14／L32）原文「80 列：✅22／⚠️44／❌7／➖7；分母 73；44.0；60.3%」與「再加 7 份施工圖 11 列＝59.9%」，PRD 兩個數字逐字出自矩陣；我重算 44.0÷73＝60.27%、54.5÷91＝59.89%。
- (b) ✅29／➖33／⏸31／📎8＝101：腳本解析 §16.2 得 ➖33／⏸31／📎8（72 列、每列 4 格、「R211 矩陣判定」欄與矩陣原判逐位置零不符）；✅ 清單 29 項與矩陣 ✅ 雙向零差。
- (c) 54.4%：(29＋8)÷(101−33)＝37÷68＝54.41%。
- 交叉表逐格＝腳本重算，無一差異（⚠️51→➖19／⏸25／📎7；❌11→➖4／⏸6／📎1；➖10→➖10；欄合計 29／33／31／8）。
- 「讀法」：「§13 …列 ⏸ 不計入落地」＝§16.2 §13 列（L2689）；殘留 → N-08。

**(b-4) 範本〈證據檔命名與護欄棘輪〉的「兩個鐘」對程式碼**——敘述成立，兩處精度 → N-09

| 範本宣稱（L381–391） | 程式碼座標（現查） | 結果 |
|---|---|---|
| 檔名鐘＝`current_round()`，讀 `CrossPlatform_R*_*.md` 檔名最大號 | `tools/check_defect_log_crossref.py:480`（`round_from_doc_names` L474；來源 glob＝R 系列證據檔與交棒書，L469 註） | 成立 |
| 前進時喚醒 SC-10／承接輪次判準／parity 錨點上界 | SC-10＝`tools/tests/test_adr_xplat001_c1c2_lock.py:6643`（`sc10_coverage_table_has_a_row_for_the_current_round`）；承接輪次＝`check_defect_log_crossref.py:542`（`orphan_backlog_problems`）；parity＝`tools/check_script_parity.py:626`／`:1057`（`N <= current_round()+1`） | 成立（`check_handoff_carriers.py:654` 也吃檔名鐘，範本未列、無礙） |
| 棘輪到期義務用另一個鐘＝重釘日誌最大輪標籤 `live_repin_round()` | 同鎖檔 `:7834`；消費端＝款(12) `:3883`（`live_round >= due_round and cap > due_target`）、`phase2_review_problems` `:7963-7965`（`live > due`）；常數 `:3245`（212）／`:3246`（516）／`:7831`（213） | 成立 |
| 同輪第二列使兩個鐘都不動 | 現值 `live_repin_round()`＝211、`current_round()`＝211（附錄 R-RATCHET；§7.7 crossref 輸出「當前輪 R211」）；R211 標籤 +787／−9＝+778、主軌 469≤517、回歸鎖軌 309／309；鎖檔 187 支 OK | 成立 |
| 餘裕用盡才換新標籤＝兌現到期列 | `net_cap_for_round(212)`＝517 大於 `_REPIN_NET_CAP_DUE_TARGET`＝516，且 212≥212 ⇒ 款(12) 在標籤 212 即紅（兌現＝新增 (212,516) 一列） | 成立 |
| 正淨額第二列須依款(9) 指名既有 R 檔 | 款(9) `[未附刪除清單]` 只判 `delta > 0`（本輪 −9 不適用） | 成立 |

### 7.6 (c) 新檔 `docs/06_quality/AutoSDD_ZeroTrust_Audit_114.md`：命名、掃描面、字樣

- **命名**：不冠 `CrossPlatform_R<N>_` 前綴，故檔名鐘不被推進（crossref 輸出仍是「當前輪 R211」，§7.7）。
- **carriers 掃描面**：`carrier_files()` 回 203 份，audit_114 不在其中、improving_114 在其中（附錄 R-C1）；掃描 glob＝`docs/04_planning/R*_HANDOFF.md`、`docs/04_planning/AutoSDD_improving_*.md`、`docs/06_quality/CrossPlatform_R*.md`（carriers 輸出 `[census]` 行），audit_114 兩者皆不命中。
- **字樣掃描**（全檔 1531 行；附錄 R-C）：
  - `R21[2-9]`：7 行命中——L186（QA 區塊）、L628／L629／L630／L709／L711／L862（Architect 區塊）；內容皆是**機制描述**（「R212 起算新 cap」「標籤走到 R212 時款(12) 紅」之類），沒有一行是把工作交給或延後到某輪。
  - `improving_11[5-9]`、`improving_1[2-9][0-9]`、`R2[2-9][0-9]`：各 0 行。
  - 「延後到／留給／交給／改派至／承接輪」＋R<NN>（我的寬鬆正則，間距 ≤12 字）：1 行＝L260，命中片段是「承接輪次皆 ≥ 當前輪 R211」——那是 crossref 工具輸出原文（我一審 §6.2 逐字貼的），描述帳本規則、R211 是當前輪而非後續輪，不是延後宣告。
  - carriers 自己的偵測器 `check_handoff_carriers.defer_rounds()` 對全檔 1531 行（不分圍籬內外）＝0 行命中。
- **圍籬**：四份原文皆以四反引號圍住，上述 7 行在 CommonMark 判法下全在圍籬內；以 carriers 式樸素判法（任一行以三反引號開頭即翻轉）只有 L862 落在圍籬外——不影響結果（不在掃描面、`defer_rounds` 零命中）。
- **建議：不需要以 HTML 註解標記**。理由：(1) 不在掃描面；(2) 偵測器零命中；(3) 在四反引號圍籬內插入註解行會改動「逐字保全」的原文（註解在圍籬內只是字面文字）。若日後有人把 `AutoSDD_ZeroTrust_Audit_*.md` 納入任何新掃描面，需先處理嵌套圍籬與這 7 行（N-11）。
- **improving_114 本身**（在掃描面內）：`R21[2-9]`／`improving_11[5-9]`／延後片語三類皆 0 行，`defer_rounds` 0 行（附錄 R-C3）。census 的「前瞻延後行 1 筆」＝R211 證據檔 L123（`git diff -U0` 該檔只有一個 `@@ -135,0 +136,7 @@` 純新增 hunk，L123 是既有行），不是本輪新增。

### 7.7 最終工作樹的閘門——本場親跑、逐字輸出

- 時點：2026-10-10 11:50 起；14 個異動檔 mtime 最晚＝improving_114 11:22:52，早於本節全部閘門的執行時刻，輸出對的就是現在這棵樹。
- 單跑模組的 `TMPDIR` 指到 scratchpad 子目錄並以 `nice -n 19` 執行，沒碰背景全套的 TEMP；沒跑任何全套、沒打任何端點、沒跑額度配速指令。
- rc 一律先導檔再 echo 取得，未接管線。

#### 7.7.1 rc 總表（各行為該指令自己的 `$?`，緊接在導檔之後讀取）
```
check_handoff_carriers rc=0
check_defect_log_crossref rc=0
check_defect_log_crossref --unresolved-count rc=0
archive_defect_log --check rc=0
refresh_nightly_anchor --check-head rc=0
check_ntfs_paths rc=0
unittest test_adr_xplat001_c1c2_lock rc=0
unittest test_context_budget_guard -k Prd rc=0
unittest test_defect_id_reference_integrity rc=0
unittest test_subprocess_encoding_hygiene -k TestRootToolsLintPolicy rc=0
test_adr_xplat001_c1c2_lock.py --print-guard-lines rc=0
AutoClaude pytest test_r100_boot_self_check rc=0
unittest test_doc_loc_baseline_freshness_r60 rc=0
unittest test_subprocess_encoding_hygiene (整模組) rc=0
ruff check tools/ .claude/hooks/ rc=0
discover-only (qa114b_discover.py) rc=0
```

#### 7.7.2 `python tools/check_handoff_carriers.py`（全文）
```
[census] 當前輪＝R211（R 系列證據檔／交棒書檔名最大號現查；未結承接輪號＝空）
[census] tracked 交接載體＝203 份（glob ['docs/04_planning/R*_HANDOFF.md', 'docs/04_planning/AutoSDD_improving_*.md', 'docs/06_quality/CrossPlatform_R*.md']）；其中前瞻延後行 1 筆
[census] commit 訊息＝743 則；其中含前瞻延後宣告 0 筆

✅ 每一筆前瞻延後宣稱都有帳本承接載體
```

#### 7.7.3 `python tools/check_defect_log_crossref.py`（全文）
```
⚠️  治理文件 CrossPlatform_Guard_Line_History.md 250457 bytes 已逼近上限 262144（距 11687 bytes），請規劃拆分——append 前務必先 `wc -c`
⚠️  治理文件 CrossPlatform_DEF200274_Parallel_Tests_Evidence.md 255168 bytes 已逼近上限 262144（距 6976 bytes），請規劃拆分——append 前務必先 `wc -c`
⚠️  AutoSDD_Defect_Log.md 相對 git HEAD 有未 commit 的修改（staged 或 unstaged）——上一次跑本閘門的結論可能是對著修改前的帳本算的，`current_round()` 等判準吃的是磁碟現狀，建議在最後一次改帳本之後重跑本檢查（DEF-200-163）
⚠️  已結列殘留待辦 3 筆（已結分類使它們結構上進不了承接稽核；真待辦請拆出獨立 DEF 列承接，敘事引述可忽略）：:74 DEF-101-060(closed-by-decision)=下一輪、:137 DEF-200-129(fixed)=backlog、:168 DEF-200-277(fixed)=留待
✅ 缺陷帳本跨文件狀態一致：帳本 209 筆有效狀態紀錄、19 份掃描目標皆無矛盾；另全部表格列的狀態欄首詞皆落在《格式定義》宣告的 7 個合法值內（散文與程式常數雙向綁定，且每個合法值都有分類器對應）；全部表格列的欄數皆等於表頭欄數、狀態欄由表頭定位（非 cells[-1] 位置猜測）；具名治理文件 165 份皆已登記且未逾體積上限（登記面對 CrossPlatform_*.md／Quota_*.md／AutoSDD_External_Blocked_Log.md／AutoSDD_Structural_Debt_Log.md 發現面雙向核對）；全部未結案列的承接輪次皆 ≥ 當前輪 R211 或改派至≥當前輪／未指派（硬規則②；已實測不涵蓋的形態見 orphan_backlog_problems docstring）；未結存量 0 列（唯一量測入口＝`--unresolved-count`；warn 86／fail 98 列）且皆二擇一（承接輪號／字面「未指派」，存量豁免 0 筆／棘輪上限 0，只准變小）；另 3 筆已結列殘留待辦，見 warning。
🔴 當前輪 R211 係由 R 系列證據檔／交棒書檔名最大號**現查**推得（不寫死）——本輪的證據檔／交棒書尚未建立時，此值仍停在上一輪，屆時「交棒給剛結束的那一輪」會合法通過（刻意選的 fail-open 方向：漏抓而非假紅，窗口於本輪證據檔／交棒書落地時自動關閉，見 lagging_clock_notes()）
外部阻塞軌（AutoSDD_External_Blocked_Log.md，不計入未結列 warn/fail 分母）：5 筆｜DEF-101-693、DEF-101-856、DEF-200-075、DEF-200-253、DEF-200-313
結構性長債軌（AutoSDD_Structural_Debt_Log.md，不計入未結列 warn/fail 分母）：6 筆｜DEF-101-018、DEF-101-398、DEF-101-701、DEF-101-702、DEF-101-960、DEF-101-980
```

#### 7.7.4 `python tools/check_defect_log_crossref.py --unresolved-count`（全文）
```
外部阻塞軌（AutoSDD_External_Blocked_Log.md，不計入未結列 warn/fail 分母）：5 筆｜DEF-101-693、DEF-101-856、DEF-200-075、DEF-200-253、DEF-200-313
結構性長債軌（AutoSDD_Structural_Debt_Log.md，不計入未結列 warn/fail 分母）：6 筆｜DEF-101-018、DEF-101-398、DEF-101-701、DEF-101-702、DEF-101-960、DEF-101-980
未結列數＝0／全部 209 列｜warn=86 fail=98
判準＝狀態欄 _classify() ∈ ['None', 'open', 'routed']
未結列 ID：
```

#### 7.7.5 `python tools/archive_defect_log.py --check`（只摘 ✅ 行；全文 135 行屬既有史料列清單）
```
135:✅ 帳本保全稽核通過（70 檔／1618 個 ID／12 個「立帳見」指針＋24 個「見主檔／現居」居所指針＋0 個裸「現居」居所註記＋125 處引述；歸檔索引 68 條 bullet 對 68 支 archive）：(1)行尾：帳本家族每一份檔在磁碟上不得含 CR（`.gitattributes` 宣告 eol=lf）、(2)重複列：同一 ID 在同一份檔內不得出現兩列、(3)跨檔矛盾：同一 ID 同時存在主檔與 archive 時，兩邊狀態分類不得各說各話、(4)立帳指針：稽核面每一處「立帳見」都要跟得上可解析 DEF-ID，且居所宣稱與實況一致、(5)歸檔索引涵蓋性：磁碟上每支 archive 都要在歸檔索引檔有一條以它為主體的 bullet（雙向）、(6)非「立帳見」方言的居所宣稱：`見主檔 DEF-x`／`見 DEF-x（現居 archive_NN）` 同樣驗居所；裸「現居 archive_NN」（無「見」動詞）另受對等硬要求，須跟得上可解析 DEF-ID、(7)表格列欄數：每列切出的欄數等於該檔表頭欄數；archive 側既有列具名基線、主檔零豁免、(8)跨檔宣稱可解析：掃描目標的每一句狀態宣稱都要能在帳本家族（主檔 ∪ archive）解析到，且狀態一致（判準③ 改寫後的事後條件，R68）；判準(4)(6) 稽核面含 165 份具名治理文件（scope `缺陷帳本`）
```

#### 7.7.6 `python tools/refresh_nightly_anchor.py --check-head`（全文）
```
✅ nightly 錨判準通過（HEAD）：nightly-run=37324659627 nightly-checked-at=2026-10-05T14:26:01+00:00（4 天前，上限 14 天）nightly-red=none
```

#### 7.7.7 `python tools/check_ntfs_paths.py`（全文）
```
📏 checkout 根前綴預算（含結尾分隔符，UTF-16 單位；未開 core.longpaths 時）：
   檔案面 259 − 最長 tracked 路徑 142 = 117
   目錄面 247 − 最深 tracked 目錄 124 = 123
   ⇒ 現況根前綴上限 = min(117, 123) = 117 字元
   fail 門檻 200 對應的根前綴預留 = 259 − 200 = 59 字元（本閘只保證這一種 checkout；上一行才是 repo 現況）
   🔴 本閘量的是 repo **相對**長度，對 checkout 根前綴結構上失明 ⇒ clone 一律帶 `-c core.longpaths=true`（R76-01：168 字元的根 → 27,523 檔只落地 301 檔、rc=128、無聲半套 checkout）。開箱指引：ONBOARDING.md §2 第 0 步
✅ NTFS 檔名檢查通過（27972 個 tracked 路徑，0 違規；最長 142 字元，warn>180/fail>200）
```

#### 7.7.8 `cd tools/tests && python -m unittest test_adr_xplat001_c1c2_lock`（尾 5 行）與 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（頭 2 行）
```
----------------------------------------------------------------------
Ran 187 tests in 13.616s

OK
[Scan-H triplet] UEP=5 AC=47 GLC_FILES=91 GLC_LINES=115589
--- --print-guard-lines head
# 淨額 115589→115589 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
```

#### 7.7.9 `cd tools/tests && python -m unittest test_subprocess_encoding_hygiene`（整模組，全文）與 `-k TestRootToolsLintPolicy`（尾 4 行）
```
.......................................
----------------------------------------------------------------------
Ran 39 tests in 14.647s

OK
--- -k TestRootToolsLintPolicy
----------------------------------------------------------------------
Ran 8 tests in 0.374s

OK
```

#### 7.7.10 `cd tools/tests && python -m unittest test_doc_loc_baseline_freshness_r60`（只摘 Ran／OK 行；輸出全文 9.4KB 為資訊段）
```
42:Ran 281 tests in 105.219s
44:OK
```

#### 7.7.11 PRD 直讀鎖與其他讀 PRD／CLAUDE.md 的模組
```
--- unittest test_context_budget_guard -k Prd
----------------------------------------------------------------------
Ran 5 tests in 0.015s

OK
--- unittest test_defect_id_reference_integrity
----------------------------------------------------------------------
Ran 11 tests in 3.620s

OK
--- AutoClaude: pytest tests/test_r100_boot_self_check.py -q -p no:xdist -o addopts=
..........................................                               [100%]
AUTOCLAUDE-PG-DSN-IN-EFFECT=0 AUTOCLAUDE-NESTED-SESSION=1
[PG autodetect] localhost:5432 沒有在聽 ⇒ 不注入（PG 相關測試維持 skip）
42 passed in 0.99s
```

#### 7.7.12 `ruff check tools/ .claude/hooks/`（全文）
```
All checks passed!
```

#### 7.7.13 discover-only：以 runner 自己的 `discover_suite()` 計收集數（不執行任何測試）
```
discover-only (no test executed): countTestCases=5273  MIN_TESTS=5273  placeholders=0  elapsed=0.9s
```

#### 7.7.14 零寫入複核：`git status --short` 與 14 個異動檔 mtime（閘門全部跑完之後取得；最後一行 `now=` 是取樣時刻）
```
 M CLAUDE.md
 M "docs/01_requirements/AutoClaude_Token_\347\233\243\346\216\247\350\210\207\345\226\232\351\206\222\346\251\237\345\210\266_PRD_v2.1.md"
 M docs/04_planning/ADR/ADR-XPLAT-010-root-subproject-boundary.md
 M docs/04_planning/AutoSDD_Iteration_Prompt_Template.md
 M docs/04_planning/AutoSDD_improving_112.md
 M docs/04_planning/AutoSDD_improving_113.md
AM docs/04_planning/AutoSDD_improving_114.md
 M docs/06_quality/AutoSDD_Defect_Log.md
A  docs/06_quality/AutoSDD_ZeroTrust_Audit_114.md
 M docs/06_quality/CrossPlatform_R145_Scan_Findings.md
 M docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md
 M tools/ruff.toml
 M tools/tests/test_adr_xplat001_c1c2_lock.py
 M tools/tests/test_subprocess_encoding_hygiene.py
--- mtime（HH:MM:SS，由早到晚排序；`now=` 行為取樣時刻，排序後落在最後）
09:05:10  tools/tests/test_subprocess_encoding_hygiene.py
09:19:13  docs/04_planning/AutoSDD_improving_112.md
09:19:14  docs/06_quality/CrossPlatform_R145_Scan_Findings.md
10:21:22  docs/04_planning/AutoSDD_improving_113.md
10:21:24  tools/tests/test_adr_xplat001_c1c2_lock.py
10:21:27  docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md
11:10:11  docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md
11:12:18  docs/04_planning/AutoSDD_Iteration_Prompt_Template.md
11:12:22  CLAUDE.md
11:12:24  docs/06_quality/AutoSDD_Defect_Log.md
11:12:25  docs/04_planning/ADR/ADR-XPLAT-010-root-subproject-boundary.md
11:12:27  tools/ruff.toml
11:16:04  docs/06_quality/AutoSDD_ZeroTrust_Audit_114.md
11:22:52  docs/04_planning/AutoSDD_improving_114.md
now=2026-10-10 12:05:37
```

### 7.8 待主控最後一棒（不是缺陷；也是 §7.0 VERDICT 的前提）

分類：以下全是**本輪收尾的同輪動作**，既不是立案、也不是延後，也不指派給任何後續輪次；做完即結，不開輪、不立帳。依範本〈審查閉環的終止〉，**本二審即終審**——P3／P4 改字不需要第三審，只需重跑 §7.7 的閘門清單；只有改到本單未列的結構性內容時才需要另審。

1. **PRD 修訂表 L22 的審查描述**（現為「一面 Sonnet QA 唯讀鏡複審」，與四方實況不符；一審 F-02 的殘影）。建議只換這一段、外圍粗體標記不動，改為：
   「四方零信任審查（Architect／SA／SD／QA，皆 Sonnet 唯讀鏡；主控為提案者不投票；findings 逐字＝`docs/06_quality/AutoSDD_ZeroTrust_Audit_114.md`〈二〉；Architect／QA 一審 CONDITIONAL、處置後經 QA 二審 APPROVE，SA／SD 一審 APPROVE；`[SA 判讀]` 18 列的歸格仍是作者判讀，SA 鏡重判其中 12 列、其餘 6 列僅有 SD 鏡的事實對照）」
   改完重跑：`test_context_budget_guard -k Prd`（應 Ran 5）、`AutoClaude/tests/test_r100_boot_self_check.py`（應 42 passed）、`test_doc_loc_baseline_freshness_r60`（應 Ran 281 OK）；並確認 `git diff --numstat` 對 PRD 仍是「新增 N、刪除 0」。
2. **improving_114 §5 收尾回填**（與下列各項在同一次編修完成）：
   - L63 QA 列結論→「CONDITIONAL → 二審 APPROVE（P1／P2 無；二審 P3×7、P4×5 同批處置）」；同列「§1／§6 改寫」改「§1／§8」；「P4-01～P4-07 登記證據檔〈三〉」改「P4-01／02／03／06／07 登記〈三〉，P4-04／05 就地訂正」（N-04）。
   - L64 Architect 列結論補「（ARCH-01 修復經 QA 二審驗證）」。
   - L67 主控列「（結果見本列下註）」→「（見下行）」；L69「複驗：（收尾回填：QA 複驗）」→「複驗：QA 鏡二審 APPROVE（2026-10-10；findings＝證據檔〈二-1〉末「## 7. 複驗」）」（N-07）。
   - 同次編修順手改字：N-01（L92）、N-02（L89）、N-03（L57）、N-04（L94）、N-12（L87）；各自的一句修法見 §7.3／§7.4。
3. **improving_114 L53 根層全套格**：背景全套跑完後，逐字比對已填值（ROOT_RC、發現數、skip 數、TEMP 圍籬行），任一不同即重填（N-06）；我只獨立驗到發現數 5273＝下限 5273（§7.7.13）。
4. **把本二審落檔進證據檔**（DEF-200-090 教訓：findings 先落 repo 再結案；scratchpad 不隨 repo 走）：把本檔「## 7. 複驗」§7.0～§7.8 逐字追加到 audit_114〈二-1〉末尾（該區塊已有四反引號外圍，內層三反引號安全），〈一〉表 QA 列結論改「CONDITIONAL → 二審 APPROVE」。§7.9 附錄是大量逐字輸出，可不入檔，我保留在 scratchpad。
5. **P3／P4 處置**：N-01～N-07 各改一句（§7.3，皆在 improving_114 與範本）；N-09／N-10 就地訂正範本兩處（§7.4）；N-08、N-11 建議登記 audit_114〈三〉為 #16／#17，各附可觀測的再開症狀——
   - #16｜PRD §16.3 (c) 分子含 8 個 📎（含 CLI 清單兩列與 §11.2／§11.3／§11.7／§15.5），讀法只點名其中 2 個｜QA 二審 N-08｜有人把 (c) 當進度數字引用或據以立案（附原文）
   - #17｜〈二〉以四反引號內嵌含三反引號的原文；任何以樸素圍籬判法掃 `AutoSDD_ZeroTrust_Audit_*.md` 的新掃描面都會與圍籬狀態失同步｜QA 二審 N-11｜新掃描面對該檔誤報（附輸出）
6. 全部編修完成後、commit 前，再跑一次 §7.7 的閘門清單（至少 carriers／crossref／docfresh／PRD 直讀鎖／鎖檔 187 支），以背景全套尾行為準。

### 7.9 附錄（二審；皆唯讀；逐字取自 scratchpad 檔）

#### 附錄 R-A　矩陣與 §16.2 對帳（qa114b_A.txt，重跑 qa114_countA.py）
```
matrix 2.1 rows: 90  2.2 rows: 11  total: 101
matrix verdict counts (all 101): {'➖': 10, '⚠️': 51, '❌': 11, '✅': 29}
2.1 only: {'➖': 9, '⚠️': 49, '❌': 9, '✅': 23}  2.2 only: {'✅': 6, '➖': 1, '❌': 2, '⚠️': 2}
dup IDs: []
green count: 29  non-green count: 72
PRD 16.2 table rows: 72  (header line 2636 )
cells per row set: {4}
positional verdict mismatches: 0
closure cells in 16.2: {'➖': 33, '⏸': 31, '📎': 8}
cross ➖ {'➖': 10} sum 10
cross ⚠️ {'⏸': 25, '➖': 19, '📎': 7} sum 51
cross ❌ {'⏸': 6, '➖': 4, '📎': 1} sum 11
PRD green list len: 29
green in matrix but not in PRD list: []
in PRD list but not in matrix green: []
wrote /private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/643984e1-5aaf-4196-9e79-db2aea7b37ce/scratchpad/qa114_162_rows.txt
```

#### 附錄 R-CNT　四面鏡 findings 的 P 級計數（qa114c_counts.py：以 `### <ID> [P?]` 標題計；SD 的 P4 在表列，QA 的 P3／P4 在一審 §0）
```
QA (二-1)           L19-L592: P2x3
    P2: F-01..F-03 (3)
Architect (二-2)    L598-L877: P2x1, P3x9, P4x8
    P2: ARCH-01..ARCH-01 (1)
    P3: ARCH-02..ARCH-10 (9)
    P4: ARCH-11..ARCH-18 (8)
SA (二-3)           L882-L1196: P3x11, P4x2
    P3: SA-01..SA-11 (11)
    P4: SA-12..SA-13 (2)
SD (二-4)           L1201-L1510: P3x6
    P3: SD-01..SD-06 (6)
QA (二-1) VERDICT lines: [(26, '**VERDICT: CONDITIONAL**')]
Architect (二-2) VERDICT lines: [(606, '**VERDICT: CONDITIONAL**')]
SA (二-3) VERDICT lines: [(890, '**VERDICT: APPROVE**')]
SD (二-4) VERDICT lines: [(1208, '**VERDICT: APPROVE**')]
```

#### 附錄 R-F01／R-C1／R-B／R-RATCHET／R-PRD　（qa114b_adhoc.txt）
```
### R-F01：PRD §16.2 的〈三〉#n 引用與被引列結案格（腳本內聯）
16.2 rows: 72
  hole #1 -> [(2649, '§4.2.3 致動器表：併發／模型降級／任務類別／硬', '⏸')]
  hole #2 -> [(2639, '§3.2 10 態 FSM＋單向鎖存＋轉移圖', '⏸')]
  hole #3 -> [(2658, '§4.5.2 分片休眠＋時鐘跳躍偵測', '⏸')]
  hole #4 -> [(2644, '§4.1.1 引擎獨立執行（無 Claude Cod', '⏸')]
  hole #7 -> [(2685, '§12 寫入範圍／治理檔禁寫', '⏸')]
  hole #8 -> [(2708, '施工圖 A5c：R112 REQ-W6 喚醒成本治理', '⏸')]
  hole #9 -> [(2658, '§4.5.2 分片休眠＋時鐘跳躍偵測', '⏸')]
distinct cited: [1, 2, 3, 4, 7, 8, 9] | non-⏸ cited rows: []

### R-C1：carrier_files() 成員檢查
carrier files: 203 | second return value: False
audit_114 in carrier set: False
improving_114 in carrier set: True

### R-B：audit_114〈二-1〉(L19-592) 對一審原檔 qa_mirror_114_findings.md（追加複驗節之前）
IDENTICAL byte-for-byte:      574 lines /    71440 bytes

### R-RATCHET：R211 標籤容量（鎖檔函式現算）
R209: total=131 lane=131 main=0 main_cap=518 lane_cap=309
R210: total=21 lane=21 main=0 main_cap=517 lane_cap=309
R211: total=778 lane=309 main=469 main_cap=517 lane_cap=309
headroom R211: main 48 | lane 0
net_cap_for_round(212) = 517 | _REPIN_NET_CAP_DUE_TARGET = 516 | _REPIN_NET_CAP_DUE_ROUND = 212 | _PHASE2_DUE_ROUND = 213
live_repin_round() = 211

### R-PRD：新版 PRD 零字更動檢查
HEAD-only lines (expect 0): 0
numstat: 211	0
added KEY=value-shaped lines (expect 0): 0
triple-backtick fence lines now / HEAD: 74 / 74
```

#### 附錄 R-C　audit_114 全檔字樣掃描（qa114b_C.py → qa114b_C.txt；每行輸出摘至 150 字）
```
total lines: 1531

== pattern R21[2-9]: 7 hit lines
  L  186 naive_fence=True  commonmark_fence=True  | - **P4-01 「同輪第二列」技巧容量有限**：`tools/tests/test_adr_xplat001_c1c2_lock.py` 現值 `_REPIN_ROUND_NET_CAP = 517`、`_REPIN_NET_CAP_DUE_ROUND = 212`、`_PHASE2_DUE_R
  L  628 naive_fence=True  commonmark_fence=True  | - 現查：R211 標籤合計 +778、回歸鎖軌 309（`_REGRESSION_LANE_ROUND_CAP=309`，已頂格）、主軌 469、cap 517 ⇒ 該標籤餘裕 48。餘裕是**每標籤**的，不是累計：新標籤 R212 起算新 cap（兌現後 516）。
  L  629 naive_fence=True  commonmark_fence=True  | - `_REPIN_NET_CAP_DUE_ROUND`（212）與 `_PHASE2_DUE_ROUND`（213）的鐘是**重釘日誌的最大輪標籤** `live_repin_round()`，不是檔名鐘 `current_round()`——範本〈證據檔命名〉與 improving_114 §2
  L  630 naive_fence=True  commonmark_fence=True  | - 因為淨額 −9 不適用款(9)，同輪第二列本輪合法且比開 R212 便宜；正淨額的第二列也可行（指名一份既有 `CrossPlatform_R*_*.md` 即可），但共用該標籤的 cap。
  L  709 naive_fence=True  commonmark_fence=True  |   1. 因果句對這兩個常數是錯的：它們在**重釘日誌的最大標籤**前進時才醒；檔名鐘前進喚醒的是 SC-10／承接輪次／parity 錨點上界。⇒「不得冠 R 前綴」對範本點名的那兩個常數既非必要（可以建 R212 檔而不 append R212 標籤）也非充分（可以不建檔而 append R21
  L  711 naive_fence=True  commonmark_fence=True  |   3. 容量與後果沒寫：餘裕是每標籤的（R211：517−469＝48；回歸鎖軌 309/309＝0）；用盡＝換新標籤（R212 起算兌現後的 516），喚醒 (212,516) 兌現＋R213 的 `_PHASE2_REVIEW_LOG` 列（皆既有便宜儀式）；款(11)（`max_consec
  L  862 naive_fence=False commonmark_fence=True  | ratchet problems @212 (no ritual): ['[到期未下修] 稽核痕跡已經走到 R212（到期輪＝R212），而現行上限仍是 517、高於到期目標 516——款(10']

== pattern R2[2-9]x: 0 hit lines

== pattern improving_11[5-9]: 0 hit lines

== pattern improving_1[2-9]x: 0 hit lines

== pattern 延後到/留給/交給 + R<N>: 1 hit lines
  L  260 naive_fence=False commonmark_fence=True  | ✅ 缺陷帳本跨文件狀態一致：帳本 209 筆有效狀態紀錄、19 份掃描目標皆無矛盾；另全部表格列的狀態欄首詞皆落在《格式定義》宣告的 7 個合法值內（散文與程式常數雙向綁定，且每個合法值都有分類器對應）；全部表格列的欄數皆等於表頭欄數、狀態欄由表頭定位（非 cells[-1] 位置猜測）；具名治理文

== check_handoff_carriers.defer_rounds(line) hits (target round n); cur=211 ==
lines with any defer_rounds hit: 0
```

#### 附錄 R-C3　L260 命中片段、improving_114 同類掃描、census 的唯一前瞻延後行（qa114b_C3.py → qa114b_C3.txt）
```
audit_114 L260: matched=[承接輪次皆 ≥ 當前輪 R211] context=[.md 發現面雙向核對）；全部未結案列的承接輪次皆 ≥ 當前輪 R211 或改派至≥當前輪／未指派（硬規則②；已]
improving_114 pattern R21[2-9]: 0 hit(s) []
improving_114 pattern improving_11[5-9]: 0 hit(s) []
improving_114 pattern defer-phrase+R<N>: 0 hit(s) []
improving_114 defer_rounds hit lines: 0
fwd-deferral line: docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md L 123 [('列 R…（backlog 指派）', 211)] - 護欄棘輪：`--print-guard-lines` 收斂「淨額 115598→115598 (+0)」；重釘列 R211（114811→115598，+787）、回歸鎖軌 309、主軌 478 ≤ 517（款(11) 連升第 1 輪）
forward-deferral lines (n>=211) across 203 carrier files: 1
```

#### 附錄 R-G　workflow paths 比對（qa114b_G_trig.txt；對象＝cec520ba 與目前工作樹 14 個異動）
```
== commit cec520ba files: ['docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md']
  aisdlc-sdd-ci.yml                  not triggered
  autoclaude-ci.yml                  not triggered
  autoclaude-mutation-on-change.yml  not triggered
  macos-compat-ci.yml                not triggered
  root-infra-ci.yml                  ALWAYS (no paths filter)
  shellcheck-ci.yml                  not triggered
  windows-compat-ci.yml              not triggered
== predicted for current change set: 14 files
  aisdlc-sdd-ci.yml                  not triggered
  autoclaude-ci.yml                  not triggered
  autoclaude-mutation-on-change.yml  not triggered
  macos-compat-ci.yml                TRIGGERED by ['CLAUDE.md', 'docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md', 'docs/06_quality/AutoSDD_Defect_Log.md']
  root-infra-ci.yml                  ALWAYS (no paths filter)
  shellcheck-ci.yml                  not triggered
  windows-compat-ci.yml              TRIGGERED by ['CLAUDE.md', 'docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md', 'docs/06_quality/AutoSDD_Defect_Log.md']
```

#### 附錄 R-DISC　discover-only 腳本（輸出見 §7.7.13）
```
import sys, pathlib, time
R = pathlib.Path("/Users/wuweihong/Antigravity/AISDCL_Agent")
sys.path.insert(0, str(R / "tools"))
import run_root_unittests as r
t0 = time.time()
suite = r.discover_suite(R / "tools" / "tests")
n = suite.countTestCases()
ph = r.discovery_placeholders(suite)
print(f"discover-only (no test executed): countTestCases={n}  MIN_TESTS={r.MIN_TESTS}  placeholders={len(ph)}  elapsed={time.time()-t0:.1f}s")
```

#### 附錄 R-SELF　本二審敘事文字（§7.0～§7.8）自掃（qa114c_selfscan2.py：`defer_rounds()` 加禁用字詞表；附錄 §7.9 為工具輸出原文、不在掃描範圍）
```
scope: 7.0-7.8 narrative = lines 578..868 (appendix 7.9 excluded: verbatim tool output)
word hit L 600 '下一輪' | ing_114 原 L65 `3. 本檔無「下一輪候選」：improving_113 的四項「
word hit L 600 '候選' | _114 原 L65 `3. 本檔無「下一輪候選」：improving_113 的四項「刻意
word hit L 631 '下一份' | 07 | 範本 L41 ＝「…防跨軌誤指；「下一份檔名」義務已由〈🏁〉節退役」；範本 L429
word hit L 631 '下一份' | 明表）＝「每輪標示在哪一柱（A/B/C）；「下一份檔名」自〈🏁〉節起不再是義務」；improv
word hit L 642 '下一輪' | md:54` 格式說明改為「入帳本表、不預開下一輪（2026-10-10 起；再開＝範本〈🏁〉
word hit L 642 '下一份' | 8／L32／L35 三處（標題「系列休眠時「下一份」欄無義務」、① 列「下一份」欄「系列休眠時
word hit L 642 '下一份' | 題「系列休眠時「下一份」欄無義務」、① 列「下一份」欄「系列休眠時本欄無義務，先查範本〈🏁〉T
word hit L 663 '下一輪' | 213／R214 的事。「只有追加標籤 ≥ 下一輪的重釘列才會喚醒它們」作為**必要條件**成
word hit L 679 '下一份' | 後 >0 而改變」＝範本 L340；「沒有『下一份檔名』義務」＝範本 L358／L429、CL
word hit L 704 '延後到' | (12) 紅」之類），沒有一行是把工作交給或延後到某輪。
word hit L 706 '延後到' |   - 「延後到／留給／交給／改派至／承接輪」＋R<NN>（
word hit L 706 '留給' |   - 「延後到／留給／交給／改派至／承接輪」＋R<NN>（我的寬
word hit L 752 '下一輪' | 0(closed-by-decision)=下一輪、:137 DEF-200-129(fixe
word-hit count: 13
```
（說明：`defer_rounds()` 命中 0 行；禁用字詞表命中的 13 處全是引用他人原文、描述我自己的掃描正則、或原文引文內的字樣，沒有一處是本鏡自己的待辦或延後宣告。）
````

### 二-2 Architect 鏡

````text
# Architect 唯讀審查鏡 — 軌道① 終輪 improving_114 變更集 findings

- 審查者：Architect 唯讀鏡（Sonnet 5.5；提案者＝主控，不投票）｜日期：2026-10-10｜基準：HEAD＝cec520ba；`git status --short` 與開場相同（10 個 tracked 修改＋untracked `docs/04_planning/AutoSDD_improving_114.md`）。
- 角度：結構一致性與終點設計。QA 鏡（`.../scratchpad/qa_mirror_114_findings.md`）已確認的算術、三個誠實數字、守門結果、F-01～F-03 不重複；本檔只在它沒審的結構面加證據。
- 讀的是**目前工作樹**：PRD §16.3 已是 ✅29／➖33／⏸31／📎8、§13 條款列已改 ⏸、`tools/tests/test_adr_xplat001_c1c2_lock.py` 的接鏈列已改 `DEF-200-504`（QA 後的處置）；improving_114 本檔尚未同步（見 ARCH-14）。

## 0. 判決

**VERDICT: CONDITIONAL**

- P2：**ARCH-01**（範本審查閉環沒有終止語意，且與〈🏁〉判準 3／severity.md 互斥——永動源②只切了「跨輪」那一半，「輪內」迴圈與三分類的准入規則都還是空的）。
- P3：9 條（ARCH-02～ARCH-10）；P4：8 條（ARCH-11～ARCH-18）。
- 沒有 P1。B、C、D 三問的答案都**不需要改碼**（見 §1）。

## 0.1 我做了什麼／沒做什麼（先講劃界）

- 全程唯讀：repo 零寫入（`git status --short` 前後相同；唯一副作用＝python import 鎖檔時 gitignored 的 `__pycache__`）。我只寫了 scratchpad 內的 `arch114_*` 與本檔。
- 現跑（皆唯讀）：`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（rc=0）；以 python 就地 import 鎖模組讀 `repin_round_nets`／`regression_lane_round_nets`／`net_cap_for_round`／`live_repin_round`（不寫檔）；`python tools/refresh_nightly_anchor.py --check-head`（離線，rc=0）；`python AutoClaude/tools/check_loc_budget.py --json`（輸出導到 scratchpad）；`check_defect_log_crossref.current_round()`＝211；PRD §16.2 以腳本重數（72 列：➖33／⏸31／📎8，與 §16.3 一致）。逐字輸出見 §5。
- 沒做：沒跑根層全套／AutoClaude 全套／SDD 全套；沒重判 `[SA 判讀]` 18 列的歸格；沒驗 GitHub 平台行為（60 天無活動停用排程、失敗通知信）——凡涉及處皆標「平台行為，未驗證」。

## 1. 六問答案（先給結論，證據在 §3）

**A 終點設計閉合嗎——主體閉合，邊角不閉合。**
- 四處（範本〈🏁〉／PRD §16／CLAUDE.md:38／improving_114 §6）的核心命題一致：休眠＝不開輪、再開只由事件、判準三條、都不成立就做產品工作。
- **沒有任何時間路徑把休眠自動變回進行中**：範本 T 集合無日曆／版本項（L358）；`grep 'HANDOFF|improving_|下一輪|下輪' tools/lib/session_brief.py .claude/hooks/*.py` 只有史料註解，沒有任何機器會提示「開輪」。
- 文字路徑有一條：範本把「進行中」寫成謂詞、又把「休眠」寫成鎖存（ARCH-04），未結列數事後 ≥1 時兩句話讀出相反結論。
- 一致性殘差：兩個「唯一真相源」且 T3 單邊（ARCH-08c）；判準 1 硬綁單一 PRD、再開後的新規格沒有結案帳（ARCH-05b）；效力句射程外還有三處「下一份／下輪」活句（ARCH-08a／b）。
- T1～T4 沒漏「再開」事件；漏的是兩個「**非再開**」事件的處置：掌舵者換平台（ARCH-18）與凍結後新發現的 PRD↔實作落差（ARCH-13）。五問 S5／S6 已接守衛面與權限姿態，我同意。

**B 同輪第二列——是配給，不是炸彈；但範本講錯了「鐘」、也沒寫容量。不改碼（R197「量、不挖」）。**
- 現查：R211 標籤合計 +778、回歸鎖軌 309（`_REGRESSION_LANE_ROUND_CAP=309`，已頂格）、主軌 469、cap 517 ⇒ 該標籤餘裕 48。餘裕是**每標籤**的，不是累計：新標籤 R212 起算新 cap（兌現後 516）。
- `_REPIN_NET_CAP_DUE_ROUND`（212）與 `_PHASE2_DUE_ROUND`（213）的鐘是**重釘日誌的最大輪標籤** `live_repin_round()`，不是檔名鐘 `current_round()`——範本〈證據檔命名〉與 improving_114 §2④ 的因果句與程式碼不符（ARCH-03）。用盡的後果＝換新標籤＋兌現 (212,516)＋R213 的 Phase-2 列（便宜的既有儀式）；淨減法只在「連續第三個正輪」才被款(11) 強制，不是用盡就強制。
- 因為淨額 −9 不適用款(9)，同輪第二列本輪合法且比開 R212 便宜；正淨額的第二列也可行（指名一份既有 `CrossPlatform_R*_*.md` 即可），但共用該標籤的 cap。

**C 兩個機器時鐘（實為三個）——保留錨與陳舊度哨兵；退役側軌 14 天 warn；只揭露不改碼可接受，但要四個條件（ARCH-09）。**

**D 決策記錄——不必另立 ADR-XPLAT-016；但有三處非補不可（ARCH-10）**：ADR-XPLAT-010:48 現在是假句子、PRD v2.1.17 狀態欄沒有生效依據、四方具名記錄表與 findings 落檔尚缺。

**E 範本互斥——本輪走四方是對的**（〈🏁〉瘦身規則標題寫「再開後適用」、且寫明 PRD 修憲才四方；本輪是終輪＋PRD 修憲），但 improving_114 L42／L59 與 PRD L22 的文字還停在「1 面 QA 鏡」（QA F-02 同源，ARCH-02e）。〈🏁〉效力句涵蓋範本**內**的全部殘留（`下輪|下一輪|N\+1|候選|下一份|遞增|下次|延後` 在範本的 13 處命中逐一判定＝否定語境或史料，附 ARCH-08 的清單）；涵蓋不到的是範本**外**三處（ARCH-08）。範本內仍有兩處真互斥：審查閉環（ARCH-01）、覆蓋度重盤句（ARCH-07）。

**F 五個永動源——① ② ④ 的復發路徑還開著；③ 已切；⑤ 只切了 E501。⏸ 不是無限收納桶，是「有界但靜默」的症狀索引。**

| 永動源 | 拆法落地後，同一個病還能從哪復發 | 對應 |
|---|---|---|
| ① PRD 無「做完」定義 | 範本 L366「覆蓋度重盤只在 PRD 變動時做」與 PRD §16.5「不重量覆蓋度」互斥；範本北極星 L0–L10 成熟度落差是同屬「沒有完工定義的進度量」，〈明文沒有〉清單漏列；再開後的新規格沒有 §16 同型結案帳 | ARCH-07、ARCH-05 |
| ② 範本只遞增 | 審查閉環「任何發現徹底修完／循環直到 PASS」（輪內迴圈）；Defect_Log:54「→ 下輪 A 軌 W 項」；CLAUDE.md:28／30／35「下一份」；T3 是唯一零人為事件即可觸發的 T | ARCH-01、ARCH-08 |
| ③ 雲端對帳自我指涉 | 已切（回填不再回填）；殘留：終輪「不回填」的例外只寫在 improving_114、範本 L377 仍寫「結論寫入本輪證據檔」；T3 的事件源未寫 | ARCH-17 |
| ④ 棘輪輪號到期義務 | 休眠靠「重釘列沿用最新標籤」這個**未寫成規則**的慣例；範本規則（不得冠 R 前綴）既非必要也非充分；R 系列下一次進入即喚醒（設計內、便宜） | ARCH-03 |
| ⑤ 日期炸彈 | E501 已清；錨 14 天／陳舊度哨兵 10 天／側軌 warn 14 天仍在 | ARCH-09 |

⏸ 的架構判定：**母體有界**（凍結 31 列；新增只能經 PRD 修憲或證據檔 P4 登記）、**不產生任何義務**，所以不是無限收納桶；但它**靜默**——我用關鍵字粗分 31 列的再開症狀面：24 列是 sid／jsonl／log 型痕跡面、1 列純人眼（§13）、6 列混合；沒有任何掃描器讀這些痕跡去對 §16.2（PRD 也不在 ghost-symbol 引用面）。「沒有人看＝只在被人撞見時才開」是事實，這與五問協定 S1～S6 的「由掌舵者或主控看到時啟動」同款，**可接受，但必須寫明**（ARCH-06）。一句話修法見 ARCH-06。

## 2. Findings 一覽

| ID | P | 標題 | 處置分類 |
|---|---|---|---|
| ARCH-01 | **P2** | 審查閉環沒有終止語意，與〈🏁〉判準 3／severity.md／TechDebt 循環令互斥 | 本輪文字修正 |
| ARCH-02 | P3 | 首例不合自家規（五處）：證據檔名／末節宣告／「T1 時先覆核」／第三條路未寫入／審查規模 | 本輪文字修正 |
| ARCH-03 | P3 | 到期義務的鐘是重釘標籤不是檔名鐘；容量與用盡後果未寫 | 本輪文字修正（不改碼） |
| ARCH-04 | P3 | 三態：「進行中」謂詞 vs 「休眠」鎖存互相矛盾 | 本輪文字修正 |
| ARCH-05 | P3 | 「延後」載體說法不一（已有第四種）＋判準 1 硬綁 Token PRD＋PRD 無「凍結後立案項」表 | 本輪文字修正 |
| ARCH-06 | P3 | ⏸ 沒有寫明觀察者與入口（F 的一句話修法） | 本輪文字修正 |
| ARCH-07 | P3 | 覆蓋度重盤句與 PRD 互斥；成熟度落差同源未封；「DONE」 | 本輪文字修正 |
| ARCH-08 | P3 | 效力句射程外的「下一份／下輪」活句；雙「唯一真相源」；T3 單邊 | 本輪文字修正 |
| ARCH-09 | P3 | 三個仍在走的機器時鐘：歸類、保留／退役判定、休眠再進入稅 | 本輪文字揭露＋立案（長債軌 P4） |
| ARCH-10 | P3 | 決策記錄形態：不必 ADR-016；ADR-010:48 假句子／狀態欄／具名記錄表 | 本輪文字修正 |
| ARCH-11 | P4 | 休眠宣告本體沒有機械載體（指標可懸空） | 延後（⏸＋症狀） |
| ARCH-12 | P4 | PRD 現況欄／座標是凍結日快照、不在 ghost-symbol 引用面；憲法指進證據檔表格 | 只登記 |
| ARCH-13 | P4 | 凍結後新發現的 PRD↔實作落差沒有路徑 | 只登記（一句話寫進 §16.5） |
| ARCH-14 | P4 | 本檔與程式碼的文字同步殘差（接鏈列 DEF 號、行數、guard-total 自帶標記） | 本輪文字修正／退役 |
| ARCH-15 | P4 | 詞彙：「休眠」與 PRD §4.5「分片休眠」撞詞 | 只登記 |
| ARCH-16 | P4 | WHY 節「兩次指出這是浪費」對 10-07 是轉述 | 本輪文字修正 |
| ARCH-17 | P4 | 範本 L378 的 paths 概括與 T3 事件源 | 只登記 |
| ARCH-18 | P4 | 「換平台」不是再開事件，但需要一句非再開處置 | 延後（⏸＋症狀） |

## 3. Findings 明細

### ARCH-01 [P2] 審查閉環沒有終止語意，且與〈🏁〉判準 3 互斥

- 位置：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md:292`、`:324`、`:325-326`、`:327` 對 `:347-350`；`docs/06_quality/FiveQuestion_Audit_Protocol/severity.md:7-8`；`docs/04_planning/TechDebt_Paydown_Cycle_Prompt.md:109-110`。
- 證據逐字：
  - 範本:292 ＝ `## 🔍 多專家 Zero-Trust 審查閉環（強制，全 PASS 才准結案）`
  - 範本:324 ＝ `2. 任何發現（文件問題 + 技術問題）→ 派全能修復 agent **徹底修完**，不留 partial。`
  - 範本:325-326 ＝ `3. QA 專家複審：…不通過 → 回步驟 2 再修，循環直到 PASS。`
  - 範本:347-348 ＝ `3. 本輪產出**沒有**「下一輪候選」——所有未做項目只准三分類：**立案**（帳本 DEF 列）／**延後**（PRD 結案帳 ⏸ 列＋一句**可觀測**的再開症狀）／**退役**（➖＋依據座標）。`
  - severity.md:7-8 ＝ `- P3：…與附屬細節（行號、措辭、歸屬）只列不改判。` ／ `- P4：理論洞…只登記、不立輪、不同輪修。`
  - TechDebt:109-110 ＝ `實作項過四方定點複審（一審全查、二審驗修復；model: sonnet 可）；收斂標準＝四方無新 blocking。`
- 為什麼是 P2：improving_114 §2② 的診斷是「審查鏡每輪必產 P3／P4 ⇒ 自動成為下一輪輸入」，拆法只切了**跨輪**交接（〈本輪輸入〉#3、〈缺陷回流分流〉、判準 3）。**輪內**那條路沒切：步驟 2 要求任何發現都徹底修完、步驟 3 要求循環到 PASS，而 PASS 沒有嚴重度定義——字面讀＝零發現。對擴張中的面做對抗搜尋沒有不動點（根 CLAUDE.md:80〈守衛面准入〉自己記 R179～R196 `發現率約 0.8 P2／輪、結構上無不動點`），所以照字面執行的視窗不會停。同時三分類缺「哪些發現可以留著不做」的准入規則：全修＝輪內迴圈、全丟進「延後」＝F 問的收納桶；兩邊都是自由裁量。repo 其實**已經握有這條規則的兩半**（severity.md 的 P3／P4 口徑；TechDebt 循環令的一審全查／二審驗修復／無新 blocking），而驅動它的範本兩者都沒引用。佐證：本鏡的任務書寫「無 P≤2 ⇒ APPROVE（可附 P3／P4）」——這條規則今天只活在任務書裡；一個只讀範本＋CLAUDE.md 的新視窗沒有停止條件。
- 修法（一句）：在〈🏁〉加「審查閉環的 PASS＝無 P≤2；P3 當輪改文字或退役、P4 只登記（口徑引 severity.md）；複審至多二審（一審全查、二審驗修復，同 TechDebt〈品質與驗證〉）；步驟 2『任何發現徹底修完』與步驟 3『循環直到 PASS』以此為準」，並把「全 PASS 才准結案」（:292）改成「無 P≤2 才准結案」；P≤2 的口徑須一併寫明（產品／文件輪＝結案不成立、不誠實、終點設計有結構漏洞；守衛面行為缺陷仍用 severity.md 的暴露度口徑——兩套尺不得混用）。
- 處置分類：本輪文字修正。

### ARCH-02 [P3] 首例（improving_114）不合自己剛寫的規則——五處

規則第一次被使用就有五處偏離，代表規則沒被走過一遍；要嘛讓首例照做，要嘛把首例實際走的路寫成規則。

- (a) **證據檔名**：範本:370 ＝ `產品輪的審計證據檔用本範本原名 docs/06_quality/AutoSDD_ZeroTrust_Audit_{{N}}.md。`；improving_114:4 ＝ `逐檔清單與雲端對帳住既有的 docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md〈八〉`。現查：`ls docs/06_quality | grep -i zerotrust` 只有 `CrossPlatform_R211_ZeroTrust_Audit_113.md`；`AutoSDD_ZeroTrust_Audit_01～100` 現全在 `docs/06_quality/Archive/`（最後一次動它們的 commit＝99cd35a4「R72 … 歷史文件歸檔」），現行層沒有任何一份；improving_113 的審計證據走 `CrossPlatform_R211_*`。⇒ 這條命名規則是在復活一個已歸檔的名字，現行層沒有任何一輪走過它。另：`check_handoff_carriers` 的掃描面＝`['docs/04_planning/R*_HANDOFF.md','docs/04_planning/AutoSDD_improving_*.md','docs/06_quality/CrossPlatform_R*.md']`，範本指定的檔名不在其中⇒該檔內的前瞻延後字樣不在判準②的掃描面內。
- (b) **宣告在末節**：範本:339 ＝ `…且已寫在該系列最後一份 AutoSDD_improving_NN.md 的末節。`；improving_114 的休眠宣告是 §6（共 §1～§8，§7 §8 在後）。
- (c) **判準 3 的「之後再看」**：improving_114:42 ＝ `標 [SA 判讀] 的列供日後 T1 立案時覆核`，:71 ＝ `再開觸發 T1 時先覆核`——附事件條件的「之後再看」，不在立案／延後／退役三類內（範本:349 ＝ `三類之外的「之後再看」不是載體，不得存在`），且 PRD §16.2 前言寫的是 `[SA 判讀]`＝`供複審逐列覆核`（即本輪），兩處說法不同。`carrier_doc_problems` 抓不到這種寫法（QA 手跑判準②＝零命中）。
- (d) **碰了護欄層卻沒開 R 輪**：範本:374 ＝ `產品輪不碰根層 tools/tests/／守衛面時不需要 R 輪；真的要動根層護欄層才開 R 輪，並承擔其義務。`；本輪改了 `tools/tests/test_subprocess_encoding_hygiene.py`、`tools/tests/test_adr_xplat001_c1c2_lock.py`、`tools/ruff.toml`，走的是**第三條路**（淨額 ≤0 的同標籤第二列），範本只列兩條路。
- (e) **審查規模**：improving_114:42 ＝ `依範本〈🏁〉瘦身規則走 1 面 QA 鏡`、:59 ＝ `走 1 面 QA 零信任鏡`；PRD:22 ＝ `一面 Sonnet QA 唯讀鏡複審`；範本:364 標題 `（再開後適用）`、:367 ＝ `碰守衛面／安全／PRD 修憲才四方`。目前四面鏡實際在跑，做法對、文字沒跟上（QA F-02 同源）。
- 修法（一句）：把第三條路與證據落點寫進〈證據檔命名〉（見 ARCH-03），把四面鏡 findings 落到範本自己規定的 `docs/06_quality/AutoSDD_ZeroTrust_Audit_114.md`（同時是該命名的首次實證——落檔前先用 `git add -n` 與 crossref／carriers 驗該名字不被任何 R 前綴鎖要求；我未驗證），並把 improving_114:42／:59／:71 與 PRD:22 改寫成實況。
- 處置分類：本輪文字修正。

### ARCH-03 [P3] 到期義務的鐘是重釘標籤不是檔名鐘；容量與用盡後果沒寫（B）

- 位置：範本:371-374；improving_114:24（§2④）、:42（劃界(2)）；`tools/tests/test_adr_xplat001_c1c2_lock.py:3881-3884`、`:7834-7841`、`:6665-6700`；`tools/check_defect_log_crossref.py:470-491`。
- 證據逐字：
  - 範本:371-373 ＝ `帳本時鐘 tools/check_defect_log_crossref.py::current_round() 讀該前綴檔名的最大號；時鐘一前進，就會喚醒護欄棘輪的輪號到期義務（_REPIN_NET_CAP_DUE_ROUND／_PHASE2_DUE_ROUND，見 tools/tests/test_adr_xplat001_c1c2_lock.py）。`
  - 鎖:3881-3884 ＝ `live_round = (max((no for no, _d in repin_round_nets(_GUARD_LINES_REPIN_LOG), default=0) if latest_round is None else latest_round)`；:7834 `live_repin_round()` docstring ＝ `稽核痕跡上的最大輪號＝本檔各到期判準共用的時鐘`；款(12)訊息字樣＝`稽核痕跡已經走到 R{live_round}（到期輪＝R{due_round}）`。該鎖檔對 `current_round()` 的唯一引用是 SC-10（:6696-6700，ADR-XPLAT-002 §6 要有當前輪那一列）。檔名鐘的其他消費者：`tools/check_script_parity.py:626`、`tools/check_handoff_carriers.py:654`、crossref 的承接輪次判準。
  - 現查（唯讀 import）：`live_repin_round()=211`、`_REPIN_NET_CAP_DUE_ROUND=212`、`_PHASE2_DUE_ROUND=213`；R211＝total 778／lane 309／main 469／`net_cap_for_round(211)=517`；`_REGRESSION_LANE_ROUND_CAP=309`；`latest_round=212` 且無兌現列時回 `[到期未下修]`。
- 判定：
  1. 因果句對這兩個常數是錯的：它們在**重釘日誌的最大標籤**前進時才醒；檔名鐘前進喚醒的是 SC-10／承接輪次／parity 錨點上界。⇒「不得冠 R 前綴」對範本點名的那兩個常數既非必要（可以建 R212 檔而不 append R212 標籤）也非充分（可以不建檔而 append R212 標籤）；必要且充分的是「不追加標籤 ≥R212 的重釘列」。（規則方向仍對：它確實避開 SC-10／承接輪次／parity 這些檔名鐘的消費者——理由寫錯、結論沒錯。）本輪的實際做法＝**標籤沿用**，這個慣例沒有任何文字、也沒有任何鎖；休眠是**當前狀態**的性質，不是規則的產物。
  2. 兩個標籤聯動只有慣例：款(9) 對**正**淨額列要求理由欄指名一份**既有**的 `CrossPlatform_R<N>_*.md`（`_PER_FILE_LIST_RE`，:3263；存在性由 :5948 一格驗），不要求它是新檔、也不要求 N＝該列輪號；所以 improving_114:24 的 `improving_113 為了讓新測試的重釘列對上時鐘而建 CrossPlatform_R211_* 檔把時鐘推到 211` 是便利、不是強制（我讀碼沒找到把重釘標籤綁到檔名鐘的鎖；若有，請主控指出座標）。
  3. 容量與後果沒寫：餘裕是每標籤的（R211：517−469＝48；回歸鎖軌 309/309＝0）；用盡＝換新標籤（R212 起算兌現後的 516），喚醒 (212,516) 兌現＋R213 的 `_PHASE2_REVIEW_LOG` 列（皆既有便宜儀式）；款(11)（`max_consecutive_rising=2`）要到**連續第三個正輪**才強制 ≤0。主控任務書寫的「用盡＝棘輪要做一次淨減法」只在連升第三輪成立。
- B 的判定：誠實的配給（rationing），不是延後的炸彈；但範本把原因講錯、把容量與後果省略。**不需改碼**：改碼＝擴張守衛面（R197）。
- 修法（一句）：〈證據檔命名〉改寫為「護欄棘輪的到期義務以重釘日誌最大輪標籤（`live_repin_round()`）為鐘，與檔名鐘（`current_round()`，另喚醒 SC-10／承接輪次）是兩個鐘；產品輪的重釘列沿用最新標籤（淨額 ≤0 免逐檔 R 檔；>0 須指名一份既有 `CrossPlatform_R*_*.md`，款(9)）；餘裕現查 `repin_growth_problems`（cap－主軌、回歸鎖軌 cap），用盡＝新標籤＝兌現 (R,≤cap−1)＋Phase-2 列；本節不寫數字」。
- 處置分類：本輪文字修正（不改碼）。

### ARCH-04 [P3] 三態：謂詞與鎖存互相矛盾（A）

- 位置：範本:338 與 :340。
- 證據逐字：:338 ＝ `- **進行中**：驅動本系列的規格仍有未分類項目，或下列〈休眠判準〉尚未全數成立。`；:340 ＝ `宣告後的狀態只由 T1～T4 改變；時間流逝、版本升級、覆蓋度數字都不會把休眠變回進行中。`
- 為什麼：判準 2 是 `--unresolved-count`＝0。主線（R 系列）持續入帳（帳本現 209 列），宣告後任何一筆 P3 新立列就讓判準 2 不成立；依 :338 這時是「進行中」，依 :340 仍是休眠，而 T2 只認 P≤2。CLAUDE.md:38 的「開輪前先看 T1～T4」實質採鎖存讀法，所以實務上無害；但這正是「同一件事兩種說法」。
- 修法（一句）：:338 改「進行中＝尚未宣告休眠」；判準三條**只在宣告當下評估一次**，宣告後唯一的狀態變化是 T1～T4，並補「未結列數事後 >0 不改變狀態（T2 只認 P≤2）」。
- 處置分類：本輪文字修正。

### ARCH-05 [P3] 「延後」載體說法不一（已有第四種）＋判準 1 硬綁 Token PRD（A／F）

- 位置：範本:345、:347-349；根 `CLAUDE.md:79`；PRD:2611、:2759、:2763；improving_114:76。
- 證據逐字：
  - (a) 範本:349 ＝ `三類之外的「之後再看」不是載體，不得存在。`；CLAUDE.md:79（〈守衛面准入〉）＝ `…沒有就登記證據檔〈理論洞清單〉（P4）、不立輪、不同輪修`；PRD:2759（§16.5 (iii)）＝ `…〈三〉理論洞表中**沒有**對應 §16.2 列的條目（#5／#6／#10／#12／#13）以其「再開症狀」欄為同款觸發源`——「證據檔理論洞表＋再開症狀欄」已是第四種載體，本輪自己用了它（QA F-01 的處置）。三處對「延後的載體」說法不同。
  - (b) 範本:345 ＝ `1. 驅動本系列的 PRD／規格已「範圍凍結」，且其結案帳沒有任何未分類列（本系列＝Token 治理 PRD v2.1.17 §16）。`；PRD:2611 ＝ `本版之後才出現的需求不是「母體缺口」，而是 §16.5 (i) 的新需求，立案時自帶其結案格。`；PRD:2763 ＝ `母體本身凍結：新需求立案時自帶結案格，不併入 101 列。`——「自帶結案格」沒有表可放（只有修訂表的自由文字格）。improving_114:76 建議的下一步是 A 柱，其驅動規格不是 Token PRD：判準 1 對再開後的輪要嘛永遠成立（Token PRD 已凍結＝空轉）、要嘛永遠不成立。
  - (c) improving_114:42／:71 的「T1 時先覆核」＝附事件條件的之後再看（ARCH-02c）。
  - (d) 再開沒有比例原則：範本:341-342 ＝ `…編號＝現存最大號＋1（動工前以 ls 實查）——這只是命名規則，不是開輪義務。`，:364 ＝ `### 產品輪的固定成本瘦身（再開後適用）`，兩者並存卻沒寫「什麼樣的 T1 不需要輪」；範本本體是整輪的提示詞，第一個 T1（improving_114:76 建議的 A 柱）會以預設走整輪——在掌舵者問「可以開發新任務了嗎」的當下，把浪費縮小版再造一次。
- 修法（一句）：延後＝「PRD ⏸ 列『或』證據檔〈理論洞清單〉列（附可觀測再開症狀，僅限 P4）」；判準 1 改通式「本次再開所驅動的規格已範圍凍結，且逐列歸入四格（立案書自帶 §16 體例的結案帳）」；PRD 增 §16.6「凍結後立案項結案帳」空表（同四格，母體 101 列不動）；另補一句「T1 的最小響應＝直接做事＋commit（訊息引掌舵者原文）；只有碰 PRD 修憲／守衛面／需跨軌設計才開 improving_N」。
- 處置分類：本輪文字修正。

### ARCH-06 [P3] ⏸ 沒有寫明觀察者與入口（F 的一句話修法）

- 位置：PRD:2759（§16.5 (iii)）；範本:356（T4）；對照 `docs/06_quality/FiveQuestion_Audit_Protocol/README.md`〈收斂宣告後的再評觸發〉。
- 證據：PRD (iii) 只寫 `附 sid、log 或痕跡列座標`，沒有觀察者；五問 README 逐字寫 `沒有任何日曆、版本號或證據效期觸發，退役後也沒有任何自動排程的再評（S1～S6 由掌舵者或主控看到時啟動）`。我對 31 個 ⏸ 列「再開症狀」子句的關鍵字粗分：24 列痕跡面型（sid／jsonl／log／痕跡）、1 列純人眼（§13）、6 列混合；沒有任何機器讀這些痕跡去對 §16.2（`_SYMBOL_REF_GLOBS` 不含 PRD，見 ARCH-12）。另外 repo 現在有**兩套互不相容的看門模型**：側軌帳本靠日曆 warn（`STALE_REVIEW_DAYS`）、⏸ 什麼都沒有。
- 判定：不是無限收納桶（母體凍結 31、新增要修憲或走 P4 登記、不生義務）；但**靜默**＝「附逃生口的退役，由人的注意力當絆線」。這與 S1～S6 同款、可接受；不誠實的版本是把它留成隱含。
- 修法（一句）：在 PRD §16.5 (iii) 與範本 T4 各補「⏸ 沒有掃描器，是症狀索引不是待辦清單；觀察者＝掌舵者回報，或任一視窗於新立 DEF／寫證據檔時對照 §16.2 再開症狀欄，命中者在該 DEF 列『分流去向』標 §16.2 座標（T4 的唯一入口）」。
- 處置分類：本輪文字修正。

### ARCH-07 [P3] 覆蓋度重盤句與 PRD 互斥；成熟度落差同源未封；「DONE」（E／F）

- 位置：範本:366、:358、:339、:9-38（北極星段）；PRD:2763、§16.3 讀法。
- 證據逐字：
  - 範本:366 ＝ `- 覆蓋度重盤只在 PRD 變動時做；三軸成熟度只在掌舵者要求時量。`；PRD:2763 ＝ `…不重量覆蓋度、不重算 §16.3、不重排母體。`；§16.3 ＝ `(a)(b)(c) 皆為 v2.1.17 當日快照：之後不重算、不當門檻、不當開輪理由（§16.5）。`——T4／T1 的再開本身就是「PRD 變動」，範本等於邀請重開 §16 剛切掉的永動源①。
  - 範本北極星段 ＝ `終極目標＝進化為 Level 10 自治開發流程`、`三軸必須一起升才推得動北極星`、`每輪須階段一實測分評三軸現級`；範本設計說明表記錄實測位約 L3–L4。「沒有完工定義的進度量」與覆蓋度百分比同屬一類，〈🏁〉:358 的〈明文沒有〉清單（日曆／版本號／覆蓋度百分比／下一份檔名／候選清單）沒列它；:339 把狀態命名為 `休眠（DONE）`，而北極星沒有達成。
- 修法（一句）：:366 改「覆蓋度：不重盤（PRD §16.3／§16.5）」；:358 加「成熟度層級落差」；:339 改「休眠（範圍結案；北極星不因此視為達成）」。
- 處置分類：本輪文字修正。

### ARCH-08 [P3] 效力句射程外的「下一份／下輪」活句；雙「唯一真相源」；T3 單邊（A／E）

- (a) 範本內的 13 處命中逐一判定：L41／L173／L184／L334／L358 ＝否定語境；L330／L383／L404／L411／L412 ＝歷史說明；L347／L348 ＝判準本身；L386 `本輪輸出（檔名遞增…）`＝描述一輪自己的輸出、不產生下一輪。**範本內無殘留**（QA P3-07 的 L41／L410 已改）。
  但效力句（:334）在範本裡，管不到範本外：
  - 根 `CLAUDE.md:28` ＝ `## 🔴 三條改進軌道（動工前先用本表對齊「本輪在哪一柱（A/B/C）、下一份檔名」）`，:30 欄名 `下一份`，:32 ①列 `docs/04_planning/ 現存最大號＋1…`，:35（附）列 ＝ `（本 repo 實際運轉的主線）`＋`現存 R*_HANDOFF.md 最大號＋1`。(附)列已不是現實：`ls docs/04_planning | grep -E '^R[0-9]+_HANDOFF'` 最大＝R128，`current_round()`＝211（我跑的）；字面照做會造出 R129_HANDOFF.md；而「實際運轉的主線」與休眠並存，讀者會把 R 系列當作不必查 T1～T4 的後門。
  - `docs/06_quality/AutoSDD_Defect_Log.md:54` ＝ `整合層（AutoClaude 側）缺陷 → 下輪 A 軌 W 項。`——範本〈缺陷回流分流〉同一列已改寫（範本:173），帳本格式定義這一份沒改；repo 內除 improving_114（引用它）外唯一的活句（`grep -rIl '下輪 A 軌'` 只有這兩份）。
  - `docs/04_planning/TechDebt_Paydown_Cycle_Prompt.md:150,154`（`交給下一輪`、`給我下輪可以大力降帳本的策略建議`）屬 R 系列循環令，其終止條件（§7 未結列＝0）可達、且 R210 已達成，是**有界**的（只要帳本入帳是事件驅動）；不列為缺陷，僅註記。
- (b) 兩個「唯一真相源」：範本:352 ＝ `### 再開觸發（唯一真相源＝本節；**只由事件驅動**）`；PRD:2753 ＝ `### 16.5 再開規則（唯一真相源）`。T2／T3 對 (ii)：T3 ＝ `CI／nightly 轉紅，且根因落在本系列範圍內的機制`（無入帳前置、「本系列範圍」未定義＝Token PRD 或 A／B／C 三柱），PRD (ii) ＝ `（CI／nightly 轉紅、經入帳而根因在本 PRD 機制者亦屬本款）`。雲端有 7 支 workflow、8 條 active cron（現查 `grep -nE '^\s*-\s*cron:' .github/workflows/*.yml`：3 條日頻＝SDD artifact-cleanup／drift-daily／fsm-chaos-nightly；5 條週頻＝arch-fitness、autoclaude-ci×2、macOS／Windows compat），所以 T3 是**唯一不需要任何人為事件就可能成立**的 T（紅了誰被叫醒＝GitHub 失敗通知，屬平台行為，未驗證）。
- 修法（一句）：CLAUDE.md:28／30／35 各補半句「系列休眠時此欄無義務；R 系列同樣只由事件驅動（未結列／S1～S6）」並把 (附) 列的「下一份」改為 `current_round()` 現查；Defect_Log:54 改「入帳，不預開下一輪（見範本〈🏁〉T2）」；取一個真相源（軌道① 再開＝範本 T1～T4；PRD §16.5 只管「是否修憲」並引用），並把 T3 併入 T2（紅先入帳、入帳後才判）。
- 處置分類：本輪文字修正（CLAUDE.md 被測試釘住，改後重跑 `test_doc_loc_baseline_freshness_r60`；Defect_Log 屬帳本結案編修單線）。

### ARCH-09 [P3] 三個仍在走的機器時鐘：歸類、判定、休眠再進入稅（C）

QA F-03 列了兩個；我現查是三個（第三個是 CI 的陳舊度哨兵）。

| # | 時鐘 | 座標 | 何時咬人 | 歸類 | 判定 |
|---|---|---|---|---|---|
| 1 | nightly 錨 14 天 | `tools/refresh_nightly_anchor.py:42`；`tools/git-hooks/pre-push:493-503`（快層，「任何 push 皆跑」，在慢層 :474 之後）；`.github/workflows/root-infra-ci.yml:531-532`；本機 nightly stage 5 `AutoClaude/tools/run_local_nightly.sh:343` | push 時（HEAD 的錨 >14 天）；我現跑 `--check-head`＝rc=0「（4 天前，上限 14 天）」 | **感測器活性**：它是雲端 job 層 fail-open nightly 的唯一觀察者（`nightly-red` 欄）的新鮮度；R208 已機械化回填（DEF-200-506 fixed；R207 決策檔明列「CI 錨過期帶、不是再評觸發」） | **保留** |
| 2 | nightly-full 排程陳舊度哨兵 10 天 | `.github/workflows/root-infra-ci.yml:534-583`（`MAX_AGE_DAYS: "10"` :566；`WAIVER_UNTIL: ""` :582） | 每次 push／PR（線上 `gh`）：近 10 天無成功的 schedule／dispatch run 即紅 | 同 1（排程通道活性），線上版 | **保留**（兩者門檻 10 vs 14 重疊，屬整理、不是現在） |
| 3 | 側軌複查日 14 天 warn | `tools/lib/ledger_closing_guards.py:205`（`STALE_REVIEW_DAYS = 14`）、`:263`（`if days > STALE_REVIEW_DAYS:`）；測試 `tools/tests/test_check_defect_log_crossref.py:3617-3640`、`:3735-3740`；除該檔外無其他消費者（`grep STALE_REVIEW_DAYS`） | 每次 crossref／pre-push 印 ⚠️，rc 不變 | **純日曆催辦**＝「待辦清單」模型；與 ARCH-06 的「症狀索引」原則、掌舵者 2026-10-07 的「不製造日期義務」相衝；原碼 docstring 自承「硬擋只會逼人把日期改成今天而不解決真正的問題」 | **退役** |

- 為什麼 1、2 該留：它們咬的是**活動**（push），不是日曆；刪掉它們＝靜默關掉 T3 的雲端那一半，而「感測器壞了與修好了表徵相同」正是根 CLAUDE.md〈不對稱風險〉的形狀；反應已機械化／印在失敗訊息末行（`refresh_nightly_anchor.py:66-72` 的 `ADVICE_COMMIT`／`ADVICE_WRITE`）。
- 3 的退役形態（事件驅動）：刪掉 `days > STALE_REVIEW_DAYS` 分支與常數，「最近複查日」欄保留為資料（格式不合仍 fail）；側軌列由自己的解鎖事件喚醒（Windows 視窗、mac 真機量測…）加入帳時的 intake 對照（ARCH-06）。動檔：`tools/lib/ledger_closing_guards.py`（344 行；`--json` 的 assertion 計價 183；tier `guardrail_lib` ≤400，只降不升）＋上列兩處測試案例；**不碰守衛面**（不在根 CLAUDE.md〈守衛面准入〉清單）、不碰 LOC 分級（只降）；動 `tools/tests` ⇒ 重釘列，淨額為負 ⇒ 可走同標籤第二列、不必開 R 輪。
- 「本輪只揭露不改碼」**可接受**，但要同時滿足四條：
  1. improving_114:76 的 `在掌舵者立案前，本 repo 沒有任何待辦會自動長出來` 改寫（QA F-03）；
  2. 範本〈休眠期間開新視窗的第一動作〉加一行：`ONBOARDING.md` 被 nightly 改髒（錨回填）、push 被錨／陳舊度哨兵擋、側軌 warn＝預期的機器產物，不是待辦也不是 T3；**閒置 ≥14 天後，開工前先跑 `python tools/refresh_nightly_anchor.py --check-head`（離線、看 rc）**——驚喜才是失敗模式（推送涉根層檔時，慢層 :474 先跑完才輪到 :503）；
  3. 退役項登記為**立案＝結構性長債軌**一列（P4；不進主帳本，判準 2 維持 0；來源枚舉須符該軌規則）；
  4. T3 文字排除這三者（併入 T2 後自然成立）。
- 休眠本身的再進入稅（誠實揭露）：閒置 ≥14 天後第一次 push 會被錨擋；本機 nightly 持續跑時只需 `git add ONBOARDING.md`，nightly 沒跑時要 `gh workflow run`×2 等 completed 再 `--write`（ADVICE_WRITE）。GitHub 對公開 repo 長期無活動停用排程屬平台行為，**未驗證**。
- 處置分類：本輪文字揭露＋立案（長債軌 P4）。

### ARCH-10 [P3] 決策記錄形態——不必另立 ADR-XPLAT-016，但三處非補不可（D）

- 判定：improving_114 §3（裁決表）＋PRD 修訂表 v2.1.17 列＋範本〈🏁〉WHY，是本 repo **PRD 修憲類決策的既有形態**：v2.1.16 ← improving_113（PRD:20）、v2.1.13 ← `PRD_Amendment_R113_WakeChain_LastMile.md`；R207 退役時間型觸發用的是決策檔 `CrossPlatform_R207_FiveQuestion_Retire_Time_Triggers_Decision.md`、沒有 ADR；R210 退役到期輪機制是**增補既有 ADR 的一節**（ADR-XPLAT-013 §9.5，且 SD 條件寫「§9.3 第 3 點須同批推翻」），不是新 ADR。ADR（001～015）是機制協定＋Status＋§7 解鎖清單＋具名四方表（ADR-013 §7.1 體例）。休眠是流程規則、不是機制協定；唯一的機制變更（E501 日期退役）落在既有 Accepted ADR 之下。⇒ 增補、不新立。
- 必補：
  1. **ADR-XPLAT-010:48**（Status：Accepted）逐字 ＝ `對齊性由 tools/tests/test_subprocess_encoding_hygiene.py::TestRootToolsLintPolicy 鎖住（規則集逐字相等、.loc_baseline-style 存量債棘輪只准縮小、豁免到期日機械核對）。`——現在是假句子（日期核對已退役）。ADR-010 的立案理由正是「下一個人改鎖時無從判斷是否在推翻一個決定」。`grep -rn '豁免到期日\|到期日機械' docs/04_planning docs/01_requirements ONBOARDING.md CLAUDE.md tools` 的活句只此一處（其餘為 guard-total 史料標記與 improving_114 本檔的敘述）。修法：ADR-010 追加帶日期的增補註記（引 improving_114 §3 F5 與 R207 先例），同批（先例：R210 SD-C）。
  2. **PRD 修訂表 v2.1.17 列的「狀態」格沒有生效依據**（PRD:22 只寫 `範圍凍結（Scope Frozen）…一面 Sonnet QA 唯讀鏡複審`），對照 v2.1.4（PRD:9）＝ `…R107 四方複審通過…＝已生效（2026-08-28；…紀錄＝…）`。R110「未生效修憲不疊層」使這格承重：§16.5 的再開規則要 v2.1.17 生效後才運作。四方 APPROVE 後補 `已生效（日期；四方鏡紀錄＝<檔>；各列歸格＝主控代決）`。
  3. **四方具名記錄與 findings 落檔**：improving_114:59-60 只有 `QA 鏡（Sonnet，唯讀）：（收尾回填 VERDICT 與處置）`；本 repo 體例＝ADR-013 §7.1 的表（角色／審查者／結論／日期／範圍／條件／證據），且範本:293-301（DEF-200-090）要求 findings 先落成 repo 內具名檔案才進修復（QA findings 與本檔目前在 scratchpad）。把 §5 填成 §7.1 體例的表、findings 落檔（見 ARCH-02a）。
- 若掌舵者仍想要單一決策錨（我不建議：那是同一個決定的第五份拷貝，見 ARCH-08b）——最小骨架：狀態（Accepted by 授權代決；追認＝未明示）／決策（休眠＋T1～T4＋PRD 凍結＋E501 退役）／否決方案（續跑 N+1；日曆兜底；覆蓋度門檻）／後果（五永動源拆除帳；仍在走的機器時鐘）／推翻條件（T1）／四方具名記錄（§7.1 體例）。
- 處置分類：本輪文字修正。

### ARCH-11 [P4] 休眠宣告本體沒有機械載體（指標可懸空）

- 證據：`grep -rln '終止條件・休眠・再開\|休眠' tools/tests AutoClaude/tests` 的命中全是睡眠機制測試；沒有任何測試點名〈🏁〉或 T1～T4。CLAUDE.md:38 以標題字串指向範本，範本改名／刪節時不會有東西轉紅；範本 T1～T4 與 PRD §16.5 的一致性也沒有鎖。
- 處置：延後（⏸）——再開症狀＝一個視窗（附 sid）因找不到〈🏁〉或 T1～T4 而照舊開輪。不立鎖（R197 量、不挖；`tools/tests` 成長要付重釘稅）。

### ARCH-12 [P4] PRD 現況欄／座標是凍結日快照；憲法指進證據檔表格

- 證據：ghost-symbol 引用面 `tools/tests/test_doc_loc_baseline_freshness_r60.py:3637-3643`（`_SYMBOL_REF_GLOBS`）＝CLAUDE.md＋`tools/**/*.py`＋`AutoClaude/tools/*.py`＋`CrossPlatform_Maturity_Criteria.md`＋`Skipped_Test_Inventory*.md`＋`docs/04_planning/*HANDOFF*.md`＋`docs/04_planning/ADR/*.md`，**不含 PRD**——§16.2 的數百個程式座標與「零命中」現況句不會因程式搬動而轉紅，只會靜默腐敗（T4 事件才被發現）。PRD:2759 把證據檔 R211〈三〉的表格當觸發源＝高層文件依賴低層可變表格（層次倒置；該檔是封閉史料，風險低）。
- 處置：只登記。可選一句：§16.2 前言補「現況欄為 2026-10-10 凍結日快照，以現查為準」。

### ARCH-13 [P4] 凍結後新發現的 PRD↔實作落差沒有路徑

- 證據：PRD:2755 ＝ `修憲只由下列三種觸發之一開啟`；§16.4 的 C1～C12 是結案當日快照。凍結後程式照常演進（R 系列的主線），新落差（C13…）不屬 T1～T4（除非是 P≤2），§16.5 又不准修憲；憲法「實作沒照 PRD 做→修實作」的分支對「PRD 已過時」不適用。
- 處置：只登記；一句話：§16.5 補「凍結後新發現的條文↔實作落差一律不修憲、不開輪，以現查為準；僅當它使某 ⏸ 症狀發生才走 (iii)」。

### ARCH-14 [P4] 與程式碼的文字同步殘差

- improving_114:40 ＝ `接鏈列（R211, d034314bdd87→8fea64d22cb1, DEF-101-791）`，程式碼 `tools/tests/test_adr_xplat001_c1c2_lock.py:3678`（現）＝`("R211", "d034314bdd87", "8fea64d22cb1", "DEF-200-504")`（QA P3-02 處置後）。
- improving_114:21 的 `2657 行`（QA P3-01）。
- improving_114:78 自帶 `<!-- guard-total:R211 -->`：成為同標籤後續重釘的第 4 個必改站點；`_GUARD_TOTAL_DOC_MIN_SITES = 2`（`tools/tests/test_adr_xplat001_c1c2_lock.py:3284`）已由 improving_112／improving_113／R145_Scan_Findings 滿足，本檔那一行不被任何判準要求（可刪＝退役）。
- 處置：本輪文字修正／退役。

### ARCH-15 [P4] 詞彙：「休眠」撞詞

- PRD §4.5.x／§6 區塊 9 的「分片休眠」「休眠喚醒」＝額度 reset 前的睡眠；同一個 agent 兩份文件都讀。範本:360 的「休眠期間開新視窗」可被誤讀成「等 reset 的睡眠期間」。改名成本現在最低（範本／CLAUDE.md:38／improving_114 三處）。
- 處置：只登記。

### ARCH-16 [P4] WHY 節對 10-07 的轉述

- 範本:382 ＝ `掌舵者 2026-10-07 與 2026-10-10 兩次指出這是浪費。`；R207 決策檔原文＝`裁決來源：掌舵者 2026-10-07 明示「除非必要不要有特定日期的義務；再評只由症狀驅動」`——10-07 是「不製造日期義務」，不是「指出這是浪費」。10-10 的原文引在 improving_114:5，成立。
- 處置：本輪文字修正（改成引原文）。

### ARCH-17 [P4] 範本 L378 的 paths 概括與 T3 事件源

- 範本:378 ＝ `docs-only commit 依各 workflow 的 paths 只觸發 root-infra-ci`：對 paths 內的檔不成立（CLAUDE.md／PRD／`tools/**` 也觸發 macOS／Windows compat，QA 附錄 G2）。T3 的真實事件源（GitHub 失敗通知信／`gh run list` 現查）沒寫；信件行為屬平台，**未驗證**。範本:377 `結論寫入本輪證據檔` 與 improving_114 的終輪「不回填」例外沒有互相交代。
- 處置：只登記。

### ARCH-18 [P4] 「換平台」不是再開事件，但需要一句非再開處置

- 證據：Windows 待辦清單（R211〈六〉、R210〈八〉、外部阻塞軌 5 列）沒有任何事件面喚醒：`session_brief.py` 屬守衛面（R197 不加碼），`grep 'External_Blocked|外部阻塞|Structural_Debt' tools/lib/session_brief.py .claude/hooks/*.py` 零命中。QA P3-10 同源。
- 處置：延後（⏸）——再開症狀＝一個 Windows 視窗（附 sid）重踩清單內已登記的待驗項。文字：範本〈休眠期間第一動作〉補「該機專屬待驗清單＝非再開事件，不開輪，只做該機的事」。

## 4. 處置分類彙總（不產生「下一輪候選」）

- **本輪文字修正**（落在本變更集或其直接引用處）：ARCH-01～10、ARCH-14、ARCH-16。
- **立案**（建議 DEF 列；**落結構性長債軌**以維持判準 2＝0）：側軌 14 天複查 warn（`STALE_REVIEW_DAYS`）的日曆型催辦退役（P4；觸發＝下一次有人進入 `tools/lib/ledger_closing_guards.py`；同標籤第二列即可，不開 R 輪）。
- **延後（⏸＋可觀測症狀）**：ARCH-11（症狀＝視窗附 sid 因找不到〈🏁〉而照舊開輪）、ARCH-18（症狀＝Windows 視窗附 sid 重踩已登記待驗項）。
- **退役**：ARCH-14 的 improving_114 自帶 guard-total 標記；ARCH-08 的 T3（併入 T2）。
- **只登記**：ARCH-12、13、15、17。

## 5. 附錄：現跑指令與逐字輸出

```
$ git status --short   # 前後相同
 M CLAUDE.md / PRD / 範本 / improving_112 / improving_113 / R145_Scan_Findings / R211_ZeroTrust_Audit_113 / tools/ruff.toml / test_adr_xplat001_c1c2_lock.py / test_subprocess_encoding_hygiene.py
?? docs/04_planning/AutoSDD_improving_114.md

$ python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines   # rc=0
# 淨額 115589→115589 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
# _REPIN_LOG_FROZEN_PREFIX_LEN = 333  # 追加新列後的總列數      （現值 332；列數 332、前綴 332）

# 就地 import 鎖模組（唯讀）
209 total 131 lane 131 main 0 cap 518
210 total 21 lane 21 main 0 cap 517
211 total 778 lane 309 main 469 cap 517
cap_212_if_not_ritual 517
DUE 212 516 PHASE2_DUE 213 live 211
lane cap 309
ratchet problems @212 (no ritual): ['[到期未下修] 稽核痕跡已經走到 R212（到期輪＝R212），而現行上限仍是 517、高於到期目標 516——款(10']

$ python tools/refresh_nightly_anchor.py --check-head   # rc=0
✅ nightly 錨判準通過（HEAD）：nightly-run=37324659627 nightly-checked-at=2026-10-05T14:26:01+00:00（4 天前，上限 14 天）nightly-red=none

$ python -c 'import check_defect_log_crossref as m; print(m.current_round())'
211

$ ls docs/04_planning | grep -E '^R[0-9]+_HANDOFF' | sed ... | sort -n | tail -1
128

$ PRD §16.2 重數（腳本）：rows 72；{'➖': 33, '⏸': 31, '📎': 8}；交叉 ⚠→➖19/⏸25/📎7、❌→➖4/⏸6/📎1、➖→➖10   （與 §16.3 一致）

$ python AutoClaude/tools/check_loc_budget.py --json   # rc=0；tools/lib/ledger_closing_guards.py：narrative 120／assertion 183／blank 41；root_tools_violations []、special_violations []
```
````

### 二-3 SA 鏡

````text
# SA 唯讀審查鏡（四方之一）— PRD v2.1.17 §16.2「➖ 33 列＋📎 8 列」退役／殘留理由逐列覆核

- 審查者：SA 唯讀審查鏡（Sonnet 5.5）｜日期：2026-10-10｜角色：獨立覆核 §16.2 作者（SA agent）與主控的歸格；作者不是鏡，本鏡不採信矩陣與作者判讀。
- **我讀的是哪一份（先講清楚）**：git HEAD＝`cec520baa895597664896206322369755816744a`（HEAD 的 PRD 還沒有 §16）；**被審對象是工作樹的 PRD**：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`，2902 行，mtime `Oct 10 10:20:13 2026`，sha256 `a7430528f314e537bb37b675d4a7dd7a4defaccacf7121507329f22d2841a934`。本檔「PRD Lnnnn」一律指該 sha 的行號（行號會漂移，座標以章節＋逐字引文為準）。
- QA 鏡第一輪（`qa_mirror_114_findings.md`）的 P3-04（§13 條款列歸 📎）已反映在現行 PRD（該列現為 ⏸）；F-01／F-02／F-03 屬流程文件，本鏡不重審。QA 明說沒有重判 18 列 `[SA 判讀]`——本鏡逐列重判其中落在 ➖／📎 的 12 列（➖ 10＋📎 2），另 6 列 ⏸ 的 `[SA 判讀]` 不在本鏡任務書範圍（§3.2、T1、§4.5.1、§6.1、P4、施工圖 A4），只在互引抽查時碰到 P4。

## 0. 判決

**VERDICT: APPROVE**

- **P≤2：無。** 33 列 ➖ 的依據座標在工作樹／HEAD 全數查得到、且說的就是該列宣稱的事（6 個 DEF-ID 逐筆讀帳列；DEF-200-246 的 tripwire 本場單跑 `6 passed`；列內 14 個檔案路徑＋符號機械核對、DEF-ID 全在）；8 列 📎 的「機制已 ✅」逐列落到檔案或測試。**沒有任何一列把安全／合規／財務要求悄悄丟掉**——每一條帶風險的要求，不是落在另一列（⏸／✅／📎），就是已被 PRD 自己的 v2.1.8／9／10 條文改寫過。
- **P3 × 11（SA-01～SA-11）**：依據句或殘留句與現查實況有落差、實質成立，全部是文字修法（零程式碼、零 PRD 本文改字，只動 §16.2 列內文字或 §16.1／§16.4 一句）。最值得修的三條：**SA-05**（§4.6「刻意不做 keep-awake」沒有任何決策紀錄，R85／R86 交棒書反而寫 `caffeinate`＝可行解）、**SA-08**（§11.3 殘留漏了一個現設計下不可能成立的驗收子句）、**SA-11**（P4 ⏸ 的現況句引了 R87 墓碑明文警告「不可信」的旗標，且那一列是 §6 區塊 1～4b ➖ 與紅線 2 📎 的承接目標）。
- **P4 × 2（SA-12、SA-13）**：只登記。

### 0.1 我做了什麼、沒做什麼（誠實劃界）

- 讀了：PRD §0～§16 與附錄 B 的相關段落（§16.2 全表 72 列以程式解析：➖ 33／⏸ 31／📎 8，交叉表四格逐格重算與 §16.3 相符）、R211 覆蓋度矩陣 §0～§2、§5～§7（§7 78 鍵逐鍵重算：✅14／⚠️21／❌28／➖15，與列內數字相符）、R211 ZeroTrust 審計〈三〉、QA 鏡第一輪 findings、`AutoSDD_improving_114.md`。
- 現查：6 個 DEF 帳列（198／234／242／246／458／508）、`docs/06_quality/CrossPlatform_R85_Ledger_Closure.md` §P9-5、R85／R86 交棒書、ADR-XPLAT-007、R98 差距分析、`tools/lib/*.py`／`AutoClaude/autoclaude/**` 的列內符號、`.claude/settings*.json`、`block_destructive_git.py` 治理檔清單、`~/.autosdd/traces`（唯讀）、`claude --version`／`claude --help`（本機零 token）。
- 跑過的指令（全部唯讀）：`AutoClaude/tests/contract/test_def200246_integration_queue_tripwire.py` 單檔（`-o addopts="" -p no:cacheprovider`，`6 passed`）；`python tools/session_resume_planner.py --pace` **一次**（零 token；輸出 `來源=cache 量測於=2026-10-10T10:48:19+08:00`、當時距量測約 2～3 分鐘＜TTL 180s，依其 `--help` 自述「快取不可用時才補量」，本次應未打端點；它可能順手更新 `~/.autosdd/traces` 的 per-model 穩定狀態檔——在 repo 之外；repo 樹無變動）。
- **沒做**：沒重判 ✅ 的 29 列；沒跑任何全套測試；沒起背景任務；沒打任何網路端點；Windows 側事實全未驗（本機 macOS）；沒驗 `claude -p` 在環境帶 `ANTHROPIC_API_KEY` 時的認證優先序（SA-12 標「未驗證」）。
- 唯讀自證：收尾時 `git status --short` 與開場逐字相同（10 個 ` M`＋1 個 `??`），見附錄 G。

## 1. Findings 一覽

| ID | P | PRD 列 | 標題 | 改判 |
|---|---|---|---|---|
| SA-01 | P3 | §4.5.3 ➖ | 列名含「C=1 起步」，依據句只涵蓋步驟 1、2；§15.6 仍指 §4.5.3 為預防 | 維持 ➖，補一句連到 C1／DEF-200-242 |
| SA-02 | P3 | §4.1.2 ➖ | 第三段（1200s→FREEZING）無逐字依據＝作者類推；「不隨時間升級」才是退役的實際內容卻沒寫 | 維持 ➖，補依據 |
| SA-03 | P3 | §4.1.2／§4.5.3／§6.2 R-6.2-1／§8 列 11 ➖ | 四列以 v2.1.8／9 改寫文為「PRD 自身替代路線」，而 §16.4 N1 說這兩版是否生效「不在本版」 | 不改格，§16.1 或 N1 補一句 |
| SA-04 | P3 | §4.7／§8 列 7／§7 ➖、§11.7 📎 | §15.2 把仲裁與狀態持久化列為「必建」，兩列卻以「多 Daemon 形態」退役；漏講失效姿態差異（派發帳壞＝不節流） | 維持 ➖，依據句改以「功能等價物」領頭並補失效姿態 |
| SA-05 | P3 | §4.6／§8 列 5／§11.5 ➖ | 「刻意不做 keep-awake」無決策紀錄；DEF-200-020 否決的是 `pmset repeat`；R85／R86 交棒書記 `caffeinate`＝可行解；ADR-XPLAT-007 §3.6 形狀 A 為 Proposed | 維持 ➖ 並補依據；**較誠實＝改 ⏸**（給了再開症狀） |
| SA-06 | P3 | §4.2.7 ➖ ⇄ §11.2 📎 | 兩列互指（「斷言形態見 §11.2」⇄「缺七情境斷言，§4.2.7 已判 ➖」） | 維持 ➖，依據句改寫 |
| SA-07 | P3 | §11.2 📎 | 殘留描述漏三件事：未入 C1～C12 的被推翻子句、模擬器是交付物不是資料、H1 母體已不可重建 | 維持 📎，殘留欄補三項 |
| SA-08 | P3 | §11.3 📎 | 殘留只寫「計時」，漏「各 worktree git status clean」子句（現設計下不可能成立） | 維持 📎，殘留欄補一句 |
| SA-09 | P3 | §15.4 P0 ➖ | 「§4.4.3（單 Step 額度成本資料）」沒有被 §4.4.3 列承接 | 維持 ➖，改指向 §9 指標或補 §4.4.3 症狀半句 |
| SA-10 | P3 | §10 ➖ | 依據座標「R98 §1.11」指錯章（該節是 §7 schema） | 維持 ➖，改座標 |
| SA-11 | P3 | §15.4 P4 ⏸（§6 區塊 1～4b ➖、§15.5 📎 的承接目標） | 現況句引 `is_enabled=false`，與 `quota_meter.py` R87 墓碑相衝；再開症狀偏事後 | P4 列改現況句並補一個前置症狀 |
| SA-12 | P4 | 多列 | 文字精度彙整（T4／EWMA／§4.4.2／「沿用矩陣」／§6「鍵無對映」／§5 API key 環境變數／P3 退役的 env 半邊／§15.5 殘留欄） | 只登記 |
| SA-13 | P4 | §6.2 R-6.2-2／§8 列 13 📎 | 殘留是無終點的運維資料＋一個 by-decision 的未接線半邊；同意 QA P3-05 的觀察，現行揭露已足 | 不要求改 |

### 1.1 最小修復包（把所有 P3 收掉所需的全部動作；皆為 §16.2 列內文字或 §16.1／§16.4 各一句）

1. §4.5.3 列（SA-01）：依據句末補「步驟 4『C=1 起步』＝同 C1／DEF-200-242（free 帶直通為設計，暴露 0）；§15.6 失敗模式表『以 C_min 起步爬升』讀作歷史字面」。
2. §4.1.2 列（SA-02）：補「§4.1.5『為什麼不是 cap=0』同理適用 1200s→FREEZING；全失效姿態＝cap≤cap_prepare、不隨時間升級，機械上能把它升成 halt 的只有逐字稿撞線地板」。
3. §16.1 或 §16.4 N1（SA-03）：補「本章把 N1 所列已落地並經複審的 v2.1.8／9 內容視為現行文；未決的只有修訂表狀態字面」。
4. §4.7／§7 列（SA-04）：依據句改以「§15.2 必建模組以功能等價物承接：…」領頭；§4.7 補失效姿態句；§7 列把 `quota_snapshot`／結構化 `resume_plan` 的承接指向 RELAY 狀態塊（`RELAY_REQUIRED`）與 `PlaybookCheckpoint`。
5. §4.6 列（SA-05）：依據改寫為「PRD §4.6 自身『長等待改用排程器交棒、失效→醒來偵測時鐘跳躍』（哨兵路徑無短等待）＋DEF-200-020（否決的是 `pmset repeat`）；ADR-XPLAT-007 §3.6 形狀 A（`caffeinate` 有界斷言）為 Proposed、未採用亦未否決」；或改 ⏸（症狀見 SA-05）。§8 列 5／§11.5 隨之。
6. §4.2.7 列（SA-06）：刪「見 §11.2」互指，改「七情境以已退役運算元（§4.2.1／§4.2.2／§3.2）寫成，#6 與 §4.1.5 F3 相反；等價斷言＝`TestDecisionTable`（S4 15 列）」。
7. §11.2 列（SA-07）：殘留欄補 (a)(b)(c)；(a) 的兩個被推翻子句同時列入 §16.4 追加註記（不改條文）。
8. §11.3 列（SA-08）：殘留欄補「『各 worktree git status clean』以 §4.5.1 ⏸ 列為前提，現行救援為 patch 不動工作樹，視為歷史字面」。
9. §15.4 P0 列（SA-09）：「§4.4.3（單 Step 額度成本資料）」改指 §9 指標，或 §4.4.3 列症狀補「或要為 `MAX_STEP_QUOTA_PP` 定值而查無單 Step pp 資料」。
10. §10 列（SA-10）：座標改「v1 四鍵全庫零命中＋PRD §10 的『Daemon 讀到 schema_version 1.0.0』前提隨 Daemon 退役」。
11. §15.4 P4 列（SA-11）：現況句改「R87 同形 payload 曾 `is_enabled:false` 而 used 610＞limit 500（撞頂後果，非暴露 0 證據）；現況以 `--pace`『派工前置』行現查」，再開症狀補「`--pace` 派工前置行由『此帳號沒有 usage credits』變為有 credits（附該行畫面）」。
12. 重驗：`python tools/check_defect_log_crossref.py` 與 `test_doc_loc_baseline_freshness_r60`（會掃 docs）；PRD 被 `PrdDrainPercentMapsToTheBandsTest._PAIRS` 直讀——只動 §16.2 列內文字不碰 §6 `KEY=value` 行即不影響。


## 2. Findings 詳述（P3 之前先講不是 P2 的理由；每條附 HEAD／工作樹現查座標、證據逐字、改判一句）

### SA-01 [P3] §4.5.3 ➖：列名含「C=1 起步」，依據句只涵蓋步驟 1、2

- PRD 列：§16.2 §4.5.3（PRD L2659）。
- 證據逐字：
  - §4.5.3 步驟 4（PRD L1101）＝「以 C=1 起步，成功接手後才交還配速控制器（避免喚醒瞬間齊發撞牆）」。
  - §15.6（PRD L2542）＝「重置後立刻再撞牆｜每個視窗開頭 20 分鐘就燒掉 40%｜重置後以 `C_min` 起步爬升（§4.5.3）；`pace_index` 天然免疫此問題」。
  - §16.2 該列依據只寫「步驟 2 的固定級距階梯已由 §4.5.10…重寫…；步驟 1 的 `RESET_CONFIRM_PERCENT` 門檻在實作面不存在…」，**零字提步驟 4**。
  - 實況：`tools/lib/quota_stability.py` 檔頭逐字「`cap is None`（`BAND_FREE`，不設限）刻意**不**進本狀態機、直接放行且清空持久狀態……與 R82 訴求 6b「50% 以下無事可做」的既有設計衝突」；`docs/06_quality/AutoSDD_Defect_Log.md` L160 DEF-200-242＝「closed-by-decision（2026-10-05）：本機落款 50 次翻頁、7 次 cap→free、翻頁後首列 live 全 ≤1＝暴露 0；free 直通為設計」。
- 為什麼不是 P2：承接在帳上齊全（§16.4 C1＋DEF-200-242 已把「重置後不暴衝」判為未承重目標句且暴露 0），丟的是「連線」不是「承接」；但 C1 的註記只落在 §11.2（PRD L2329）與 §4.2.4(c)（PRD L592），§4.5.3 與 §15.6 讀者看不到。
- 改判一句：維持 ➖；依據句補「步驟 4『C=1 起步』＝同 C1／DEF-200-242（free 帶直通為設計、暴露 0）；§15.6『以 C_min 起步爬升』讀作歷史字面」。

### SA-02 [P3] §4.1.2 ➖：第三段（1200s→FREEZING）無逐字依據

- PRD 列：§16.2 §4.1.2（PRD L2646，`[SA 判讀]`）。
- 證據逐字：
  - §4.1.2 本文（PRD L266–L275）三段＝「age > POLL_INTERVAL × 3 (180s) → 強制 THROTTLING」「age > TELEMETRY_TIMEOUT (600s) → 強制 DRAINING」「age > TELEMETRY_TIMEOUT × 2 → 強制 FREEZING（視為額度狀態不明）」。
  - §4.1.5（PRD L347 起）「原條文（§8-6／§4.1.2）：全部失效 → `DRAINING` + 告警…；`age > TELEMETRY_TIMEOUT (600s)` → 強制 `DRAINING`」——**只改寫了 DRAINING 兩處**，沒提 1200s→FREEZING；§16.2 該列的「1200s→FREEZING 同理無狀態物件可落」是作者類推（本列已標 `[SA 判讀]`，誠實）。
  - R-4.1.5-1（PRD L368）「為什麼不是 `cap = 0`：0＝靜默鎖死，本實作已明文禁止」——這句同理涵蓋第三段，所以類推成立。
  - 實況：`tools/lib/quota_policy_env.py` L98 `AUTOSDD_QUOTA_DEGRADED_CAP` 出廠 2（≤ `cap_prepare`）；`tools/lib/quota_gate.py` `quota_floor_reading` docstring「L3 地板：逐字稿裡有**未復原**的撞線 ⇒ 水位下界 100%……meter 全死時唯一還算數的證據」＝量不到時唯一還算數的證據（可把水位地板推到 100%→halt）；`draining()` 對 unmeasured 回 `"unknown"` ✓。
- 為什麼不是 P2：行為方向是 PRD v2.1.8 自己白紙黑字選的；L275 的「指數退避」目的（不轟炸端點）由 `claim_refresh_slot()`（`tools/lib/quota_gate.py` L591：每 TTL 至多補量一次）承接。但「**不隨時間升級**」才是第二、三段退役的實際內容，列內沒寫。
- 改判一句：維持 ➖；補「§4.1.5『不是 cap=0』同理適用 1200s→FREEZING；全失效姿態＝cap≤cap_prepare、不隨時間升級，機械上能把它升成 halt 的只有逐字稿撞線地板」。

### SA-03 [P3] 四個 ➖ 列的依據對 §16.4 N1 懸空

- 受影響列：§4.1.2、§4.5.3（依據＝v2.1.8 §4.1.5／§4.5.10）、§6.2 R-6.2-1 與 §8 列 11（依據＝v2.1.8 §6.2＋R196 註記）。
- 證據逐字：修訂表 v2.1.8 列狀態＝「經掌舵者裁決「走理想版」立案，本版僅完成規格化，實作由後續階段接手」（PRD L13）；v2.1.9 列＝「…逐條修訂後待再審」（L14）；§16.4 N1（PRD L2751）＝「…是否算已生效的程序裁決不在本版，也不構成未結項」。同一章又把這兩版的改寫文當成「PRD 自身指定替代路線」。
- 實質：落地紀錄齊（N1 自列 DEF-200-146／148／204／205 fixed、R102 四方終審 4/4 APPROVE_WITH_FIXES；§4.1.5 另有 F5 `_PAIRS` 鎖與 R100 出廠值收緊，DEF-200-206 ④ 記 F5 綠）。風險只在形式：依據句靠一個「未決是否生效」的修憲。
- 為什麼不是 P2：改寫文是 PRD 本文的現行字面（§4.2.4 逐字「新條文（v2.1.8 起生效）」），實作與測試皆照它。
- 改判一句：不改格；§16.1 或 N1 補一句「本章把 N1 所列已落地並經複審的 v2.1.8／9 內容視為現行文；未決的只有修訂表狀態字面」。

### SA-04 [P3] §4.7 ➖（連帶 §8 列 7 ➖、§7 ➖、§11.7 📎）：兩個「必建模組」以功能等價物退役，依據句未點名、也漏講失效姿態

- PRD 列：§4.7（PRD L2663，`[SA 判讀]`）、§8 列 7（L2676）、§7（L2671）、§11.7（L2702）。
- 證據逐字：
  - §15.2（PRD L2443／L2448）＝「依此矩陣，**真正必須自建的只有四項**」，表內含「帳號層級配額仲裁（§4.7）」與「治理層狀態持久化（縮減版 `state.json`）」；§15.3（L2465）縮減版架構圖仍畫「讀 governance.json + 帳號仲裁鎖」。⇒ 仲裁**不是**「Daemon 形態所以不要」——縮減版架構自己還留著它。列內「lease TTL／daemon_id／daemon.lock 是多 Daemon 形態的機制，本 repo 刻意不做 Daemon」只處置了機制名，真正的依據是後半句「功能等價物＝目錄項派發帳」。
  - 等價物現查成立：`tools/lib/quota_ledger.py` `claim_dispatch`／`count_dispatches`（L99／L133）；`tools/lib/quota_gate.py` `FANOUT_WINDOW_SECONDS = 300`（L163）；派發帳在 `tempfile.gettempdir()`（`fanout_ledger_path()`）＝同一 OS 使用者共享，註解逐字「🔴 **刻意不帶 session id**…額度是 per-account 的單一池」。
  - **失效姿態差異（列內沒講）**：PRD §4.7＝「無法取得鎖 → 視為遙測不可得 → fail-safe 降級」＋紅線 6（PRD L2530）「鎖搶不到 → 一律當成「額度不明」而降級，絕不「先跑再說」」。實作 `tools/lib/quota_ledger.py` `claim_dispatch` docstring「`None`＝寫不進去（不得升級為守衛失敗）」；`tools/lib/quota_gate.py` `live_dispatches` docstring「讀不到一律回 0（量不到 ≠ 節流）」且 `if quota_ledger is None: return 0` 靜默；只有「讀不懂的目錄項」走 `note_degraded("ledger-unreadable", …)`。⇒ 派發帳壞掉＝finite cap 帶（notice／converge／prepare）不節流（fail-open，有限度出聲）；halt 帶 cap=0 在派發帳之前就回 rc，不受影響（`quota_gate.py` halt 分支先於 `claim_dispatch`）。
  - §7 列同型：「`agents[]`／`quota_snapshot`／結構化 `resume_plan` 屬多 Agent 並行形態」只有 `agents[]` 成立；`quota_snapshot` 與 `resume_plan` 單 agent 也成立，承接是 RELAY 狀態塊（`tools/session_resume_planner.py` L257 `RELAY_REQUIRED`＝schema／session_id／plan_path／state／kind／reset_at／reset_source／attempts／max_attempts／allow_resume／task_name）與 `PlaybookCheckpoint`（`checkpoint_manager.py` L83，checksum＋原子寫入 `file_state_repository.py` L36／L134／L211）。
- 為什麼不是 P2：功能等價成立、破壞面只有「系統暫存目錄寫不進」；fail-open 是 hook P0 的既有取捨（`tools/lib/quota_ledger.py` 檔頭 R81 收斂立案段：`.claude/settings.json` 記載過 P0「hook 誤觸會把所有工具硬鎖死」），不是本輪新造。
- 改判一句：維持 ➖；§4.7／§7 依據句改以「§15.2 必建模組以功能等價物承接：…」領頭，§4.7 補「失效姿態：PRD『鎖搶不到→fail-safe』在本實作為派發帳寫不進／讀不到＝不節流（fail-open，unreadable 目錄項出聲）；halt 帶不受影響」。

### SA-05 [P3] §4.6 ➖（連帶 §8 列 5 ➖、§11.5 ➖）：「刻意不做 keep-awake」沒有決策紀錄

- PRD 列：§4.6（PRD L2662）、§8 列 5（L2675，`[HEAD 現查]`）、§11.5（L2700）。
- 證據逐字：
  - 列內依據＝「（沿用矩陣）刻意不做 keep-awake」＋根 CLAUDE.md〈mac 已知邊界〉。後者逐字是「睡著的 Mac 不會被喚醒；`pmset repeat` 需 sudo、本專案刻意不碰」＝**喚醒憑證**，不是防休眠。
  - `docs/06_quality/AutoSDD_Defect_Log_archive_67.md` L83 DEF-200-020 處置欄「改走由 repo 自己下的喚醒憑證（`pmset schedule wake`／`caffeinate`）並納入取證｜closed-by-decision@R85：憑證與劃界見 §P9-5」；§P9-5 結案③（`docs/06_quality/CrossPlatform_R85_Ledger_Closure.md` L323 起、L331）逐字「另一半刻意不做：由 repo 自己下喚醒憑證（`pmset repeat`）需 sudo 且會改動掌舵者機器的電源行為，已由掌舵者否決」——否決對象是 `pmset repeat`，未提 `caffeinate`。
  - `docs/04_planning/R85_HANDOFF.md` L55＝「mac 不休眠的**可行解是 `caffeinate`**（不需 sudo、不改任何持久設定 ⇒ 不在已否決的 `pmset repeat` 射程內）」；`R86_HANDOFF.md` L64＝「mac 解＝`caffeinate`。本輪未新增量測」。
  - `docs/04_planning/ADR/ADR-XPLAT-007-frontier-token-governance.md`：狀態 **Proposed**（L3）；§3.6 形狀 A「`caffeinate` 有界斷言（建議採用）」（L598）；工作表 X-3（L836）；全庫 `caffeinate`／`SetThreadExecutionState`／`systemd-inhibit` 零程式碼命中——**從未實作，也從未被否決**。
  - 矩陣自己的 §0.3（矩陣 L16）把「已決策不做、暴露 0」限定為「DEF-200-246／458／199-L2L3／234／242」，**沒有** §4.6；R98 §1.7（`docs/06_quality/CrossPlatform_R98_PRD_Gap_Analysis.md` L83、L266）說「有意的架構選擇」，那是差距分析文，與 R85／R86 交棒書相左。
  - PRD §4.6 自身的替代路線（PRD L1726）＝「防休眠**只用於短等待**（`< MAX_INPROCESS_WAIT_SECONDS`）；長等待改用 §4.5.5 的排程器交棒。另需處理「防休眠失效、機器仍睡著」的情況：醒來後偵測時鐘跳躍 → 重新輪詢遙測 → 若已過重置點則直接進入 `RESUMING`」。哨兵路徑沒有短等待（全走排程器）；引擎路徑的行程內等待（出廠上限 18000 秒，`AutoClaude/autoclaude/utils/config.py` L270）理論上屬 PRD 說的「短等待」，卻無 keep-awake，只靠 W3 分片休眠的時鐘跳躍偵測（`sliced_sleep.py`）補位。
- 為什麼不是 P2：睡著＝晚醒，不是損失（排程路徑 `_SCHTASKS_SETTINGS` L112 `-StartWhenAvailable -WakeToRun`、`endurance_env.warn_if_sleepy` 出聲；引擎路徑時鐘跳躍偵測）；依據**存在**（PRD §4.6 自身的替代路線＋DEF-200-020），只是被標成了不存在的「刻意」。
- 改判一句：維持 ➖ 並把依據改為「PRD §4.6 自身替代路線＋DEF-200-020；ADR-XPLAT-007 §3.6 形狀 A 為 Proposed、未採用亦未否決」；**較誠實的是改 ⏸**，再開症狀＝「mac 或 Windows 筆電於引擎等待或續航窗期間進入睡眠，事後以 `pmset -g log`（mac）或系統電源事件（Windows）加逐字稿時間戳證實晚醒或漏醒（附 sid 與 `pmset -g custom` 輸出）」。

### SA-06 [P3] §4.2.7 ➖ ⇄ §11.2 📎：兩列互指

- 證據逐字：§4.2.7 列（PRD L2652）＝「依據＝（沿用矩陣）範例表；斷言形態見 §11.2（`TestDecisionTable`，`tools/tests/test_quota_policy.py`）」；§11.2 列（L2698）＝「缺獨立離線模擬器與 §4.2.7 七情境斷言（§4.2.7 已判 ➖）」；PRD §11.2（L2324）＝「必須提供**離線模擬器**…對 §4.2.7 的 7 個情境做斷言」。
- 現查：`tools/tests/test_quota_policy.py` L146–L148 `TestDecisionTable`＝「規格 S4 的 15 列逐列釘住」（實作側自己的決策表，**不是** PRD 的七情境）。七情境（PRD L938 起）以 v2.0 運算元寫成——`V_eff`（§4.2.1 ➖）、`C_cap(state)`（§3.2）、`DRAINING` 狀態；#6「遙測中斷 11 分鐘 → `DRAINING` c=0」與 §4.1.5 F3（cap≥1）直接相反。⇒ ➖ 成立，但「見 §11.2」只是互指（§4.2.7 列指向的 §11.2 列全文不含 `TestDecisionTable`，本鏡以程式比對）。
- 改判一句：維持 ➖；依據句改「七情境以已退役運算元（§4.2.1／§4.2.2／§3.2）寫成，#6 與 §4.1.5 F3 相反；實作側等價斷言＝`TestDecisionTable`（S4 15 列）」，刪互指。

### SA-07 [P3] §11.2 📎：殘留描述漏三件事（`[SA 判讀]`）

- PRD 列：L2698。機制 ✅ 成立：`decide()` 純函式、單調（`test_quota_policy.py` L795）與穩定性質測試（H2／H3／H4 注入式）。
- (a) **未入 C1～C12 的被推翻子句**：PRD L2332＝「**fail-safe**：注入遙測中斷 11 分鐘 → 併發歸零；注入 429 → 用量推估上修且退避有 jitter」。與 §4.1.5 R-4.1.5-1「為什麼不是 `cap = 0`：0＝靜默鎖死」／F3（cap≥1），以及 PRD §8 列 1b（施工圖 v2.1.10 §2.3；DEF-200-197 fixed、DEF-200-459 補列）「遙測端 429＝量不到、永不 halt」相反（推論端的『上修』字面無對應機制、亦未註記，落在 §8 列 1 ⏸ 列範圍）；現行實作該驗收會紅。列內殘留一字未提。
- (b) **「獨立離線模擬器」是 PRD 的交付物，不是校準值／fixture／證據**：PRD §11.2（L2324）「必須提供」；§15.8（L2591）`governor/simulate.py # 離線模擬器（P2 先寫這個）`；P2「絕對不要在真實額度上調參」。現況由 `decide()` 純函式＋注入時鐘性質測試承擔其目的——殘留句應如實寫「模擬器程式未建，由性質測試承擔其目的」，否則讀者以為只欠資料。
- (c) **H1 母體已不可重建（本機實證）**：`/var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/autosdd_quota_degraded.jsonl` 現存 167 列，首列 `at=2026-09-19T09:08:05+08:00`；`sysctl -n kern.boottime`＝`Sat Sep 19 09:04:19 2026`；`~/.autosdd/traces/quota_burn.jsonl` 現存 410 列、首列 `2026-08-12T22:45:43+08:00`（＝PRD §4.2.4 判決依據 1 所報 span 的起點，推定同一台機器）。⇒ 立案窗 `2026-08-21T18:56:59..08-22T07:01:10` 的未量到事件源（system temp）已隨 09-19 重開機蒸發；PRD H1 步驟 5（L702）「痕跡不可得時的姿態＝skip 並出聲，不得靜默降級成無時間戳版本」是唯一可行姿態。所以「補件」不是一個可完成的動作（母體指紋 37／19 會變，需先修憲換母體）。列內只說「原始痕跡…重開機即蒸發」，沒說「已蒸發」。
- 為什麼不是 P2：機制 ✅；(a) 是條文落差、(b) 是交付形態、(c) 是證據永久缺。
- 改判一句：維持 📎；殘留欄補 (a)(b)(c)，(a) 兩子句同時列入 §16.4 追加註記（不改條文）。

### SA-08 [P3] §11.3 📎：殘留只寫「計時」，漏「各 worktree git status clean」子句（`[HEAD 現查]`）

- 證據逐字：PRD L2335＝「人工注入 95% 訊號，斷言：**5 秒內**完成所有 worktree 的 checkpoint 與 state.json 原子寫入，**且 `git status` 在每個 worktree 皆為 clean**」；§4.5.1 步驟 2（L1066）「每個 worktree 各自 commit（不是只有一個！）」＝§16.2 §4.5.1 列 ⏸（缺逐 worktree commit，且「無人窗口不得 commit」）；`.claude/settings.unattended.json` deny＝`Bash(git commit*)`／`Bash(git push*)`／`Bash(git rebase*)`（現查）；§8 列 8（v2.1.8）「救援序列**只有一個動作且不動工作樹**」。⇒ 該子句在現行設計下**不可能成立**（無人窗口不得 commit；救援是 patch、不改工作樹）。
- 列內殘留＝「餘下為 5 秒內完成 checkpoint 的計時斷言與落帳的 `pct_before`／`pct_after`（v1 恆 null）」——兩個都是真的，但漏了這個。
- 現查其餘成立：`tools/lib/resume_cost.py`＋`tools/lib/relay_machine.py` L469 `resume_cost.record_window`；DEF-200-508 fixed（帳本 L281）；`AutoClaude/tests/test_r100_power_loss_protection.py` 存在。
- 為什麼不是 P2：底層缺口已在 §4.5.1 ⏸ 列登記並附症狀；機制（原子 checkpoint、kill -9 回退、FRESH 降級、喚醒成本落帳）✅。
- 改判一句：維持 📎；殘留欄補「『各 worktree git status clean』以 §4.5.1 ⏸ 列為前提，現行救援為 patch 不動工作樹，視為歷史字面」。

### SA-09 [P3] §15.4 P0 ➖：「§4.4.3（單 Step 額度成本資料）」沒有被該列承接

- 證據逐字：P0 出場題（PRD L2492）＝「…並回答：一次典型 Step 燒掉多少百分點？週額度平均一天燒幾 %？`pace_index` 的實際分布長什麼樣？」；列內「P0 對應 §4.1.1 T1／T3、§9 指標、§4.4.3（單 Step 額度成本資料）」。§4.4.3 ⏸ 列的再開症狀＝「一次單一 Step 失控（回合數或額度燒掉遠超預期，附 sid＋step_id）而牆鐘 timeout 未能攔住」＝控制面，不是「要定值而查無資料」。單 Step pp 的資料位——§7 `quota_cost_pp`（➖ 已退役）、§9 `autoclaude_step_quota_cost_pp`（⏸，症狀＝出現下游要讀指標）——也沒有「要校準而缺資料」的症狀。
- 為什麼不是 P2：非安全／合規／財務；`MAX_STEP_QUOTA_PP` 無致動器，資料沒有消費者。
- 改判一句：維持 ➖；P0 列改指 §9 指標（`autoclaude_step_quota_cost_pp`），或 §4.4.3 列症狀補「或要為 `MAX_STEP_QUOTA_PP` 定值而查無單 Step pp 資料」。

### SA-10 [P3] §10 ➖：依據座標「R98 §1.11」指錯章

- 證據：列內「v1 從未實作（R98 §1.11）」。`docs/06_quality/CrossPlatform_R98_PRD_Gap_Analysis.md` L105「### 1.11 §7 state.json Schema v2」，全檔 `grep -ci 'v1'`＝0（`1.11` 只出現在 L105 的小節標題），該節講的是「全 repo 零命中 schema_version…／兩套各自為政的替代品」，不是 v1。
- 實質成立（我自己查的）：`TOKEN_COMPACT_PERCENT`／`WEEKLY_LIMIT_HALT_PERCENT`／`BURNING_RATE_WINDOW_MINUTES`／`resumption_command` 在工作樹僅見於 PRD（`grep -rl` 全庫）；`git log --oneline -S'TOKEN_COMPACT_PERCENT'` 只有 `18dee831`（R89，該 commit 把 PRD 本檔加進 repo、diff 命中皆為 PRD 行）。⇒ v1 從未在程式裡存在＝無遷移對象。
- 改判一句：維持 ➖；座標改「v1 四鍵全庫零命中（本鏡 grep＋git -S）；PRD §10『Daemon 讀到 schema_version 1.0.0』的前提隨 Daemon 退役」。

### SA-11 [P3] §15.4 P4 ⏸（§6 區塊 1～4b ➖、§15.5 📎 紅線 2 的承接目標）：現況句與 `quota_meter.py` 的 R87 墓碑相衝，再開症狀偏事後

- 範圍說明：P4 是 ⏸ 列，不在本鏡 ➖／📎 清單；本條是互引抽查（§6 區塊 1～4b 的 OVERAGE_* 鍵、§15.5 紅線 2 都指向它）時發現的承接目標準確性問題。
- 證據逐字：§16.2 P4 列（PRD L2694）＝「…現況事實上 FREEZE（`tools/lib/quota_policy.py`、`tools/lib/quota_meter.py`），本機帳號曾觀測 `extra_usage.is_enabled=false`（`tools/lib/quota_meter.py` 註解，一次性觀測、非人工確認）；再開症狀＝帳號啟用付費超額後出現一次真實的超額軸被動用或超額計費而無人被告警」。同一個註解（`tools/lib/quota_meter.py` L363–L372）逐字：「🔴 R87 事故墓碑：**不要**因為桶自報 `enabled: false`／`is_enabled: false` 就把它排除在軸之外。R87 舵手這樣做過，代價是 13 個 subagent 全數撞 `You've hit your monthly spend limit`、燒掉 1,319,703 tokens、零產出。當時的 payload 逐字：`extra_usage {"is_enabled": false, "monthly_limit": 500, "used_credits": 610.0, "utilization": 100.0, "disabled_reason": "org_level_disabled_until"}`……`enabled:false` 是撞頂的**後果**，不是「這一軸不算數」」。⇒ 這個 `false` 不是「超額沒開」的證據（同形 payload 當時已真實花到 610／500）。
- 現況（本場 `--pace` 現查，非推論）：「派工前置：方案指紋=five_hour+session+seven_day+spend+weekly_all+weekly_scoped｜此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆」——這是個**機器可見的前置狀態**。
- PRD 自己的定級：§15.1（L2428）「**這是本專案最危險的單一失敗模式**」、§15.6（L2545）「靜默計費｜沒觸發過凍結，但帳單出現｜`OVERAGE_POLICY=FREEZE` + 對 `overage` 類額度告警」——預防有兩半（FREEZE＋告警），告警（`OVERAGE_ALERT_ON_FIRST_USE`）零落地；§15.5 紅線 2 的 📎「以預設 FREEZE、無 ALLOW_WITH_CAP 路徑滿足」只涵蓋前半。
- 為什麼不是 P2：承接存在且機械物在位——P4 ⏸ 列＋`FALLBACK_KINDS`（`quota_policy.py` L131）不進 cap 聚合＋月度 spend 撞線走 escalate（LIMIT_SPEND，§4.5.10 R-4.5.10-2 例外 1，E3 鎖）＋`--pace` 現況行；本帳號目前無可用 credits。
- 改判一句：P4 列現況句改「R87 同形 payload 曾 `is_enabled:false` 而 used 610＞limit 500（撞頂後果，非暴露 0 證據）；現況以 `--pace`『派工前置』行現查」，再開症狀補一個前置事件「`--pace` 派工前置行由『此帳號沒有 usage credits』變為有 credits（附該行畫面）」（可觀測、無輪號無日期）。

### SA-12 [P4] 文字精度彙整（只登記）

- **T4**：列內「PRD 自排最後」不精確——§4.1.1 表 T5 列在 T4 之後，T4 標的是「可靠性：低」（PRD L248）；B-06 的「優先用 B-05」指 statusLine（T3）不是 T5。§4.1.1（L241）「實作時必須全部支援並可降級」是 MUST；T4 的退役是 v2.1.17 新決策，不在 §16.1 列舉的三項（Daemon／多 agent worktree 整合／API_KEY）內，建議 §16.1 定義補列。
- **EWMA**：「`ewma_burn_rate` 庫在、生產呼叫端零（僅診斷）」——`grep -rn ewma_burn_rate`（排除 tests）只有定義（`tools/lib/quota_pace.py` L733）；診斷端也零呼叫端。
- **§4.4.2**：「見修訂表 v2.1.8 列 (B) 段」只支持「刻意不做 Daemon」半句；「多 agent worktree 整合」不做的依據是 DEF-200-246 結案欄逐字「② 隨多 agent worktree 整合落地」（未來條件式）、處置欄「closed-by-decision：Architect 附條件同意、其餘角色無記錄」（帳本 L161）——四個 ➖ 列（§4.4.2／§6.2 R-6.2-1／§7／§8 列 11；§11.6 經 §4.4.2）＋一個 📎（§6.2 R-6.2-2 的 DRY_RUN 半邊）以它為依據，建議本輪四方結論附進證據檔。
- **「（沿用矩陣）」不是座標**：§3.1／§4.1.1-LOCAL／§4.2.2／§4.2.6／§4.2.7／§4.4.1／§4.6／§10／§11.5／A3 共 10 列，矩陣列 ID 現成（`§4.1.1-LOCAL`…），§16.1「必附依據座標」宜補矩陣列 ID；§4.7／§8 列 7 兩列則完全沒有座標（只有機制描述）。
- **§6 三列「換形態後鍵無對映」過寬**：矩陣 §7（現算）78 鍵中 35 鍵（✅14／⚠️21）有對映；實際意思是「PRD §6 不再是設定契約，`ENV_SPEC`（`tools/lib/quota_policy_env.py`）才是」。
- **§5 API_KEY（理論洞，暴露未知）**：全庫零 `ANTHROPIC_API_KEY`／`ANTHROPIC_AUTH_TOKEN`（`grep -rniE` tools／.claude／AutoClaude/autoclaude／.github 零命中）。若無人窗口的環境帶該變數，`claude -p` 的計費路徑可能與 OAuth 額度治理脫鉤——CLI 的認證優先序**本輪未查證**。補充：本機 `claude --help` 現有 `--max-budget-usd <amount>`（「Maximum dollar amount to spend on API calls (only works with --print)」），日後 §5 若重開可優先評估。
- **P3 ➖ 退役的 env 半邊**：§15.3（PRD L2465、L2482）原設計是「PreToolUse hook＋調整 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`」；全庫零該變數（`.claude/settings.json` env 只有 `PYTHONUTF8`／`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`／`SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK`）。它是唯一不依賴 hook 存活的併發上限，而根 CLAUDE.md〈hook 載具〉自承載具解析不到時 fail-open。理論洞，只登記。
- **§15.5 殘留欄**：寫的是逐條對映，不是殘留；其中紅線 3／4 的「機械物」是設計選擇＋散文提示（`.claude/hooks/context_budget_guard.py` L935「不要用 `CronCreate`」、`tools/session_resume_planner.py` L885），不是機械擋——「各有機械物」略過度。

### SA-13 [P4] §6.2 R-6.2-2／§8 列 13 📎：殘留是無終點的運維資料＋一個 by-decision 的未接線半邊

- 現查：`AutoClaude/autoclaude/execution/boot_self_check.py` L155 `read_cli_version`／L181 `cli_version_verdict`；`verified_cli_versions.py` 含 2.1.295；本機 `claude --version`＝`2.1.296 (Claude Code)`（與列內「寫本列當下＝2.1.296、清單最新 2.1.295」相符）；`main.py` 註解「`dry_run` **刻意不接到執行器**」＝DEF-200-246 by-decision；G5 只對 cleanup 路徑成立。
- 判斷：機制（讀版本、比清單、loud 一次、清單 git-tracked 且帶「核實過什麼」欄）✅；列內已把「每次 CLI 升版即重現、無終點」與「DRY_RUN 未接執行器依設計」兩半並陳，歸格不構成不實。同意 QA P3-05 的觀察（📎 的定義是可補件的殘留，本列是持續維護面），但現行揭露已讓讀者不被誤導；不要求改。若要最乾淨：矩陣規則「僅資料缺漏仍計 ✅＋備註」下，R-6.2-2 的 DRY_RUN 半邊（by-decision）是它不能直接 ✅ 的唯一原因。


## 3. 逐列表——➖ 33 列

圖例：Q1＝依據座標在工作樹／HEAD 現查存在、且說的是該列宣稱的事（✓＝成立；△＝成立但有落差，編號指向 §2）。Q2＝退役有沒有悄悄丟掉安全／合規／財務要求（「無」＝已核；「有承接」＝要求落在別列；P4＝只登記）。`[SA]`＝作者自標 `[SA 判讀]`，`[HEAD]`＝作者自標 `[HEAD 現查]`。行號＝PRD 工作樹 sha `a7430528…`。

| # | PRD 列（行） | Q1 依據存在且說的是這件事？ | Q2 丟了安全／合規／財務要求？ | Q3 結論 |
|---|---|---|---|---|
| 1 | §3.1 架構圖：單一 Daemon＋7 模組（L2638） | ✓ PRD〈v2.1 的變更〉段（L24）「將建議架構從「大型自建 Daemon」縮減為「薄治理層 + 採用原生能力」」＋§15.3；`tools/lib/quota_boot_check.py` 檔頭「本 repo 沒有常駐 daemon」；載具 `context_budget_guard.py`／`session_resume_planner.py` 存在 | 無：七個模組各有自己的列 | 維持 |
| 2 | §4.1.1 T4（L2643）`[SA]` | △ B-06（L2847）逐字「可用但格式非契約；優先用 B-05」✓，但 B-05＝statusLine（T3）非 T5；「自排最後」不精確；T4 退役是 v2.1.17 新決策、不在 §16.1 列舉三項內（SA-12） | 無：§4.1.1 L241「必須全部支援」的 MUST 被豁免，但 T5 已是認可主源（L249）、T4 標「可靠性：低」 | 維持（SA-12 補文字） |
| 3 | §4.1.1 本機推估安全邊際 15pp（L2645） | ✓ `LOCAL_ESTIMATE_SAFETY_MARGIN` 在 tools／.claude／AutoClaude/autoclaude 零命中（本場 grep）；T5 為帳號級讀數 | 無：「只有本機推估」在實作＝量不到→`degraded_cap≤cap_prepare`（更緊）＋逐字稿撞線地板；紅線 8 兩半由此承接 | 維持 |
| 4 | §4.1.2 新鮮度三段式（L2646）`[SA]` | △ §4.1.5（L347–L368）確實把「全失效→DRAINING」「age>600s→DRAINING」改寫為 cap≤cap_prepare；1200s→FREEZING 無逐字依據（SA-02）；依據對 N1 懸空（SA-03）。180s 一段 `QUOTA_CACHE_TTL_SECONDS=180`（`quota_gate.py`）✓；`draining()` 對 unmeasured 回 `"unknown"` ✓ | 有承接：量不到＝cap≤cap_prepare（出廠 2，`quota_policy_env.py` L98），不隨時間升級——v2.1.8 明文選擇（L368）；L275「指數退避」目的（不轟炸端點）由 `claim_refresh_slot` 每 TTL 至多一次承接 | 維持＋補依據（SA-02／03） |
| 5 | §4.2.1 EWMA 燃燒率（L2647）`[SA]` | ✓ PRD §4.2.8（L972）逐字「完全免除冷啟動、EWMA 調參與視窗重置誤判…建議實作採用 `pace_index` 為主控訊號，`V_eff` 僅作為輔助診斷指標」；`pace_index` 在 `quota_pace.py`；`ewma_burn_rate` 只有定義（L733） | 無 | 維持（SA-12：「僅診斷」比實況寬，實為零呼叫端） |
| 6 | §4.2.2 安全燃燒率／目標併發公式（L2648） | ✓ 同 §4.2.8；`Policy.wrap_minutes`（`quota_policy.py` L287／L740；`AUTOSDD_QUOTA_WRAP_MINUTES` 出廠 5）、`V_FLOOR`（`quota_pace.py` L680） | 無：T_MIN hold 由 wrap 收尾保留段承接 | 維持 |
| 7 | §4.2.5 BURSTING 六條件（L2650） | ✓ DEF-200-458（帳本 L231）逐字「closed-by-decision@R209…bursting_ok 無生產呼叫端、查無實損。重開＝某窗 reset 時剩餘 ≥20pp 且 near 帶 cap 曾限制待派工作（附 --pace 畫面）」＝與列內「自載重開條件」逐字相符；`bursting_ok` 全庫僅 `quota_pace.py` L684 定義；DEF-200-198 fixed（帳本 L152） | 無：BURSTING 是「放寬」方向；不啟用＝§4.2.5 要被週額度否決的那條危險路徑不存在 | 維持 |
| 8 | §4.2.6 參考實作（L2651） | ✓ 同 §4.2.8；參考實作的 `State` 枚舉／`C_cap(state)` 皆 v2.0 運算元 | 無 | 維持（SA-12：座標補矩陣列 ID） |
| 9 | §4.2.7 情境試算表（L2652） | △ 與 §11.2 列互指（SA-06）；`TestDecisionTable` 存在（`test_quota_policy.py` L146「規格 S4 的 15 列」） | 無：七情境以已退役運算元寫成，#6 與 §4.1.5 F3 相反 | 維持＋改寫依據（SA-06） |
| 10 | §4.4.1 Worktree 建立（L2654） | ✓ §0.6 表（L83）「§4.4.1 自建 git worktree 管理→採用」＋B-20（L2862）；`.autoclaude/worktrees` 全庫零命中 | 無：「`.autoclaude/` 入 .gitignore」→§6.1 ⏸（不變式 9；現查 `.gitignore` 無該條）；「限制寫入範圍」→§12 寫入範圍 ⏸ | 維持 |
| 11 | §4.4.2 序列化整合佇列（L2655） | ✓ DEF-200-246（帳本 L161）＋tripwire 本場單跑 `6 passed`；PRD §6.2 R-6.2-2 ③ 註記載重開條件①②③；矩陣 §6.1 第 14 列「建議決策式收斂」。△ 「修訂表 v2.1.8 (B)」只支持「不做 Daemon」半句；DEF-200-246 結案欄「② 隨多 agent worktree 整合落地」＝未來條件式（SA-12） | 無：「衝突解決耗額度、DRAINING 以上禁止」由 R-6.2-1／G3 承接 | 維持 |
| 12 | §4.5.3 重置驗證與喚醒（L2659）`[SA]` | △ 步驟 1、2 的依據成立（§4.5.10＝L1564 起；C2 註記 L1104；`endpoint_probe_verdict` 本場讀碼＝「每軸 <100%」、回 `None` 才走付費探針）；步驟 4「C=1 起步」零字（SA-01）；對 N1 懸空（SA-03） | 有承接（缺連線）：C1／DEF-200-242＋§15.6「`pace_index` 天然免疫」 | 維持＋補依據（SA-01／03） |
| 13 | §4.6 跨平台防休眠（L2662） | △ 「刻意不做 keep-awake」無決策紀錄（SA-05）：DEF-200-020 否決的是 `pmset repeat`；R85／R86 交棒書記 `caffeinate`＝可行解；ADR-XPLAT-007 §3.6 形狀 A 為 Proposed。PRD §4.6 自身替代路線（L1726）才是真依據 | 無（睡著＝晚醒，不是損失） | 維持＋補依據；**較誠實＝改 ⏸**（SA-05） |
| 14 | §4.7 帳號配額仲裁（L2663）`[SA]` | △ 功能等價物成立（`claim_dispatch`／`count_dispatches`；`FANOUT_WINDOW_SECONDS=300`；派發帳在 `tempfile.gettempdir()`＝同 OS 使用者共享）；但 §15.2（L2443–L2448）把仲裁列為必建、§15.3（L2465）縮減版仍保留仲裁鎖；失效姿態漏講（SA-04） | 有承接；失效姿態差異（派發帳壞＝不節流）屬揭露缺口 | 維持＋補（SA-04） |
| 15 | §5 API_KEY 模式（L2664） | ✓ R98 L289「❌ §5 API Key 模式（全未實作，本 repo 純 OAuth）」＋L317「若無 API Key 自動化計畫可直接不做」（條件式，決策由 v2.1.17 補，§16.1 定義已含）；`AUTH_MODE`／`API_BUDGET`／`API_AUTO_CONTINUE` 全庫零命中；矩陣 §6.1 第 14 列 | 財務有承接：§1.3 非目標「API 模式必須有使用者自訂的硬性預算上限」保留為前提紀律（列內已寫）；§6.1 不變式 7 隨之（§6.1 ⏸ 列）。P4：無偵測 `ANTHROPIC_API_KEY` 的守衛（SA-12，未驗證） | 維持 |
| 16 | §6 區塊 1～4b（L2665） | ✓ 矩陣 §7 現算 78 鍵＝✅14／⚠️21／❌28／➖15，38.9%＝(14+0.5×21)/(78−15)；`ENV_SPEC` 存在；C8 註記（PRD L486、L979、L1834）。「鍵無對映」過寬（SA-12） | 有承接：28 個 ❌ 鍵逐一對映（AUTH_MODE→§5；WEEKLY_*／PACE_*→C8；OVERAGE_*→§15.4 P4 ⏸；TELEMETRY_SOURCE_ORDER→§4.1.1 各列）；OVERAGE_* 的承接目標有現況句問題（SA-11） | 維持 |
| 17 | §6 區塊 5～9（L2666） | ✓ 歸屬列全存在且現況句逐字提到該鍵：MAX_STEP_*→§4.4.3 ⏸、COMPACT_MIN_INTERVAL_SECONDS→§4.3 ⏸、BURSTING→§4.2.5、RESET_CONFIRM→C2；W3 三旋鈕 `sleep_slice_seconds=30`／`clock_jump_tolerance_seconds=5`／`max_inprocess_wait_seconds=18000`（`AutoClaude/autoclaude/utils/config.py` L268–L270） | 無 | 維持 |
| 18 | §6 區塊 10～15（L2667） | ✓ 歸屬列存在：INTEGRATION_*→§4.4.2；ALLOW_PERMISSION_BYPASS→§12 權限旗標 ⏸；REDACT_SECRETS_IN_LOGS→§12 日誌遮蔽 ⏸；METRICS_EXPORT／ALERT_WEBHOOK_URL→§9 三列 ⏸；DRY_RUN→§6.2 R-6.2-2 📎；API_*→§5 | 無 | 維持 |
| 19 | §6.2 R-6.2-1 殘留整合佇列：開機掃描重排（L2669） | ✓ DEF-200-246；掃描機制 G1～G3 測試存在（`AutoClaude/tests/test_r100_boot_self_check.py` L35、L91、L127）。PRD L2028「不得把它們標成「架構性不適用」而刪掉」與 ➖ 字面有張力，但 R196 註記（R-6.2-2 ③／G5／§7）已在 PRD 內以 closed-by-decision＋重開條件＋tripwire 處理，且掃描機制本身仍在——意圖未丟（建議列內補「掃描機制 ✅，退役的只是上游寫者」） | 無 | 維持 |
| 20 | §7 state.json schema v2（L2671） | ✓ 矩陣 §6.1 第 14 列；`PlaybookCheckpoint.integration_queue`（`checkpoint_manager.py` L83）；checksum／原子寫入（`file_state_repository.py` L36、L134、L211）；RELAY 狀態塊 `RELAY_REQUIRED`（`session_resume_planner.py` L257）。△ 把 `quota_snapshot`／結構化 `resume_plan` 也歸「多 Agent 並行形態」不精確；§15.2 把「治理層狀態持久化」列為必建（SA-04） | 無：「resume_plan 只存參數、不存可執行命令字串」由 §12 命令執行 ✅ 承接 | 維持＋補（SA-04） |
| 21 | §8 列 5 等待中睡著（L2675）`[HEAD]` | ✓ `_SCHTASKS_SETTINGS`（`session_resume_planner.py` L112 `-StartWhenAvailable -WakeToRun`）、`endurance_env.warn_if_sleepy`（L397）、`sliced_sleep.py` 時鐘跳躍增量帳；根 CLAUDE.md〈mac 已知邊界〉。依賴 §4.6（SA-05） | 無：PRD 列 5「記錄防休眠失效事件並告警」弱化成武裝時出聲＋痕跡（delay 非 loss） | 維持（隨 SA-05） |
| 22 | §8 列 7 同帳號多 Daemon 超燒（L2676） | ✓ 同 §4.7 | 同 §4.7 | 維持（SA-04） |
| 23 | §8 列 11 整合驗證失敗（L2678） | ✓ 同 R-6.2-1 | 無：`CONFLICT_POLICY=ABORT` 拒絕啟動、G3 DRAINING 以上只登記皆在碼（`test_r100_boot_self_check.py`） | 維持 |
| 24 | §15.4 P0 觀測（L2690）`[SA]` | ✓ §14 註（L2394）「請以 §15.4 的階段規劃為準」＝§14 被 §15.4 取代；出場題所指列皆存在。△ 「§4.4.3（單 Step 額度成本資料）」未被 §4.4.3 列承接（SA-09） | 無（校準資料路徑，非安全／合規／財務） | 維持＋改指向（SA-09） |
| 25 | §15.4 P1 保全（L2691）`[SA]` | ✓ §4.3 ⏸、§4.5.1 ⏸、§11.3 📎 三列現況句逐字涵蓋 PreCompact／逐 worktree commit／5 秒落盤 | 無 | 維持 |
| 26 | §15.4 P2 配速（L2692）`[SA]` | ✓ §4.2.8 在 ✅ 清單；§11.2 📎 列涵蓋模擬器／DRY_RUN 一週 | 無（「不要在真實額度上調參」是方法論，母體外） | 維持 |
| 27 | §15.4 P3 閘門（L2693）`[SA]` | ✓ §4.2.3 ⏸（模型降級致動器）、§4.4.1 ➖、§11.6 ➖；全庫零 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`＝「以 hook 直接 deny 取代」屬實 | 無（P4：退役的 env 半邊是唯一不依賴 hook 存活的併發上限；SA-12） | 維持 |
| 28 | §15.4 P5 硬化（L2695）`[SA]` | ✓ §12 六列 ⏸、§6.1 ⏸、§6.2 R-6.2-2 📎、§11.8 📎、§9 告警 ⏸ 皆存在 | 無 | 維持 |
| 29 | §10 v1→v2 設定遷移（L2696） | △ 座標「R98 §1.11」指錯章；實質成立（SA-10） | 無 | 維持＋改座標（SA-10） |
| 30 | §11.5 防休眠驗收（L2700） | ✓ 同 §4.6（隨 SA-05） | 無 | 維持（隨 SA-05） |
| 31 | §11.6 多 Agent 隔離與整合（L2701） | ✓ 同 §4.4.2 | 無：AutoClaude 引擎逐 step 順序執行；原生 `isolation: worktree`（B-20）承擔隔離 | 維持 |
| 32 | 施工圖 A3（L2705） | ✓ DEF-200-458（同 #7） | 無 | 維持 |
| 33 | 施工圖 A5b（L2707） | ✓ DEF-200-234（帳本 L158）逐字「偵測面已落地（quota_escalation.py 的 _orphan_watch…）；處置面…無暴露證據…重開＝主控 429 退場後背景 agent 仍燒 token（附 sid）」與列內逐字相符；`_orphan_watch` 在 `tools/lib/quota_escalation.py` L483 | 無 | 維持 |

統計：33 列中 Q1 全 ✓＝#1、3、5、6、7、8、10、11、15、16、17、18、19、21、22、23、25、26、27、28、30、31、32、33（24 列，其中 #5／#8／#11／#15／#16／#19／#27 附 P4 文字註）；Q1 △＝#2、4、9、12、13、14、20、24、29（9 列，皆 P3／P4，無一列「依據不存在」）。Q2 沒有任何一列「丟了要求而無承接」。

## 4. 逐列表——📎 8 列

| # | PRD 列（行） | Q1「機制已 ✅」逐項落到檔案或測試？ | Q2 殘留描述是否誠實／有沒有漏掉要求？ | Q3 結論 |
|---|---|---|---|---|
| 1 | §6.2 R-6.2-2 CLI 版本相容＋DRY_RUN（L2670）`[HEAD]` | ✓ `read_cli_version`／`cli_version_verdict`（`boot_self_check.py` L155／L181）；`VERIFIED_CLI_VERSIONS` 含 2.1.295 且每版帶 `verified` 與 `source`（G6）；本機 `claude --version`＝`2.1.296 (Claude Code)` 與列內相符；loud 一次由測試釘；DRY_RUN 真不動作半邊＝DEF-200-246 by-decision（`main.py` 注釋「`dry_run` 刻意不接到執行器」；G5 只對 cleanup 路徑成立） | 兩半並陳（無終點的清單資料＋by-decision 未接線），誠實；PRD §6.2 R-6.2-2 ③ 註記載重開條件 | 維持（SA-13 P4） |
| 2 | §8 列 13 CLI 版本升級（L2680） | ✓ 同上 | 同上 | 維持 |
| 3 | §11.1 零 Token 遙測 6h 驗證（L2697） | ✓ T5 零 token（`USAGE_URL` 註解；R90 實測）；v2.1.4「必做」的降級驗證由 `_UNMEASURABLE_REASONS` 注入式測試承擔（`test_quota_policy.py` L1529–L1534）；docs 無 6h 紀錄（本場 grep 零命中） | 誠實：「補件＝有人長跑一次並落款」可完成 | 維持 |
| 4 | §11.2 離線模擬器＋性質測試（L2698）`[SA]` | ✓ `decide()` 純函式＋單調（`test_quota_policy.py` L795）／穩定性質測試；H1 fixture 零命中（`grep` 該 37 符號序列全庫零命中）。△ 殘留漏三件事（SA-06／SA-07） | 漏：未入 C1～C12 的被推翻子句、模擬器是交付物、H1 母體已不可重建 | 維持＋補（SA-07） |
| 5 | §11.3 凍結與喚醒（L2699）`[HEAD]` | ✓ `tools/lib/resume_cost.py`＋`relay_machine.py` L469；DEF-200-508 fixed（帳本 L281）；`AutoClaude/tests/test_r100_power_loss_protection.py` 存在；FRESH 降級 `choose_resume_route`。△ 漏「各 worktree git status clean」子句（SA-08） | 漏一個現設計下不可能成立的子句 | 維持＋補（SA-08） |
| 6 | §11.7 多實例配額（L2702） | ✓ 派發帳測試 `test_context_budget_guard.py` L8605～L8677；「單測僅在該檔」屬實（`grep -rln claim_dispatch tools/tests AutoClaude/tests` 只該檔） | 誠實 | 維持 |
| 7 | §11.8 24h 端到端（L2703） | ✓ 修訂表 v2.1.13 列「2026-08-31 實戰佐證…全通」；docs 無 24h／≥4 次 reset 紀錄（本場 grep 零命中） | 誠實：補件可完成 | 維持 |
| 8 | §15.5 紅線 1～12（L2704）`[SA]` | △ 紅線 1＝`quota_meter.USAGE_URL` 單一站點；10＝`block_destructive_git.py` L1444–L1457 `_GOV_EXACT`（含 `.env`／`.claude/settings.json`／`settings.local.json`／`settings.unattended.json`）＋`.autoclaude/` 前綴；9＝`resume_route` acceptEdits＋settings；3／4＝設計選擇＋散文提示（非機械擋）；2＝無 ALLOW_WITH_CAP 路徑 | 「殘留」欄寫的是逐條對映、不是殘留；紅線 2「滿足」只含前半（FREEZE），告警半由 P4 ⏸ 承接（SA-11、SA-12） | 維持 |

統計：8 列 📎 中，「機制已 ✅」無一列不成立（無 P2）；§11.2、§11.3 的殘留描述不完整（P3）。


## 5. ➖／📎 ⇄ ⏸ 互相引用抽查（引用的目標列確實承接嗎？）

方法：對每個「功能面歸屬列見…」式引用，檢查目標列在 §16.2 存在、格別與來源列所述一致、且目標列文字**逐字**含該功能的關鍵詞（以程式比對 `sa114_rows.json` 解析出的 72 列；MISS 的兩筆反而是 SA-06／SA-09 的程式化佐證）。

| 來源列（格） | 引用的目標列（格） | 承接？ |
|---|---|---|
| §6 區塊 1～4b（➖） | §15.4 P4（⏸）；§16.4 C8 | ✓ 目標列逐字含 `OVERAGE_POLICY=ALLOW_WITH_CAP`／`OVERAGE_ALERT_ON_FIRST_USE`／月度超額利用率 halt；C8 註記在 PRD L486／L979／L1834。△ 現況句問題見 SA-11 |
| §6 區塊 5～9（➖） | §4.4.3（⏸）、§4.3（⏸）、§4.5.4（⏸）、§4.2.5（➖）；C2／C5／C6 | ✓ 目標列逐字含 `MAX_STEP_TURNS`、`COMPACT_MIN_INTERVAL_SECONDS`、`AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`；C2／C5／C6 註記在 PRD L1920 |
| §6 區塊 10～15（➖） | §12 權限旗標（⏸）、§12 日誌遮蔽（⏸）、§9 指標／告警（⏸）、§6.2 R-6.2-2（📎）、§4.4.2（➖）、§5（➖） | ✓ 逐字含 `ALLOW_PERMISSION_BYPASS`、`REDACT_SECRETS_IN_LOGS`、`autoclaude_*`、`NEEDS_HUMAN`、`DRY_RUN` |
| §4.5.3（➖） | §4.5.10（⏸）；C2 | ✓ 目標列逐字載「R-4.5.10-1 的行程內重量上限（≤3 次、總時長 ≤90s）零命中」；C2 註記 L1104。步驟 4 未被連到（SA-01） |
| §15.4 P0（➖） | T1（⏸）、T3（⏸）、§9 指標（⏸）、§4.4.3（⏸） | ✓ T1／T3／§9；△ §4.4.3 列不含「單 Step 額度成本資料」（程式比對 MISS；SA-09） |
| §15.4 P1（➖） | §4.3（⏸）、§4.5.1（⏸）、§11.3（📎） | ✓ 逐字含 PreCompact／逐 worktree commit／5 秒落盤 |
| §15.4 P2（➖） | §4.2.8（✅）、§11.2（📎） | ✓ §11.2 列逐字含「DRY_RUN 一週」與模擬器 |
| §15.4 P3（➖） | §4.2.3（⏸）、§4.4.1（➖）、§11.6（➖） | ✓ §4.2.3 列逐字含「模型降級」 |
| §15.4 P5（➖） | §12 六列（⏸）、§6.1（⏸）、§6.2 R-6.2-2（📎）、§11.8（📎）、§9 告警（⏸） | ✓ §6.1 列逐字含 7b／8／9 |
| §8 列 5／列 7／列 11（➖） | §4.6／§4.7／§6.2 R-6.2-1（➖） | ✓ 目標列存在；依賴鏈見 SA-04／SA-05 |
| §11.5／§11.6（➖） | §4.6／§4.4.2（➖） | ✓ |
| §7（➖） | DEF-200-246 重開條件②（§6.2 R-6.2-2 ③ 註記） | ✓ tripwire `6 passed` |
| §15.5（📎） | §15.4 P4（⏸）、§6.2 R-6.2-2（📎） | ✓ P4 列逐字含 FREEZE／ALLOW_WITH_CAP；現況句問題見 SA-11 |
| §11.7（📎） | §4.7（➖） | ✓ |
| §11.2（📎）⇄ §4.2.7（➖） | 互指 | △ 互指（SA-06）：§4.2.7 列指向的 §11.2 列不含 `TestDecisionTable`；§11.2 列說「缺七情境斷言（§4.2.7 已判 ➖）」 |
| 反向：§6.1（⏸） | 「7 隨 §5 判 ➖」「2、3、7c 矩陣判 ➖」 | ✓ 矩陣 §2.1 §6.1 列逐字「➖2,3,7c」；§5 在 ➖ |
| 反向：§4.5.4／§4.4.3（⏸） | C3／C4／C6 | ✓ 註記在 PRD L1056／L1125／L1140／L1142 |

## 6. 我確認「站得住」而沒有列 finding 的重點（避免讀者以為沒查）

1. **6 個 DEF-ID 逐筆讀帳列**（`docs/06_quality/AutoSDD_Defect_Log.md`）：DEF-200-198（L152 fixed）、234（L158）、242（L160）、246（L161）、458（L231）、508（L281 fixed）。列內引的「自載重開條件」與帳列逐字相符（§4.2.5／A3 的「某窗 reset 時剩餘 ≥20pp 且 near 帶 cap 曾限制待派工作（附 --pace 畫面）」＝DEF-200-458；A5b 的「主控 429 退場後背景 agent 仍燒 token（附 sid）」＝DEF-200-234；C1 的「50 次翻頁、7 次 cap→free、翻頁後首列 live 全 ≤1＝暴露 0」＝DEF-200-242）。
2. **DEF-200-246 的 tripwire**：`AutoClaude/tests/contract/test_def200246_integration_queue_tripwire.py` 單跑 `6 passed`（rc=0）；`integration_queue` 在 `autoclaude/` 僅有欄位定義（`checkpoint_manager.py` L83）與讀者（`boot_self_check.py`）。
3. **列內所有檔案路徑／符號／DEF-ID 機械核對**（41 列、程式解析反引號內容）：14 個路徑僅 `.autoclaude/worktrees` 不存在——那正是列內宣稱「零命中」的對象；6 個 DEF-ID 全在；列內宣稱零命中的識別字（`AUTH_MODE`／`ALLOW_PERMISSION_BYPASS`／`RESET_CONFIRM_PERCENT`／`COMPACT_MIN_INTERVAL_SECONDS`／`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`／`METRICS_EXPORT`／`ALERT_WEBHOOK_URL`／`daemon_id`／`quota_snapshot`…）在 tools／.claude／AutoClaude/autoclaude／AutoClaude/tests 全為零命中；其餘識別字皆命中。
4. **數字**：§16.2 解析＝72 列（➖33／⏸31／📎8）；交叉表四格重算與 §16.3 相符（⚠️51→➖19／⏸25／📎7；❌11→➖4／⏸6／📎1；➖10→➖10）；`[SA 判讀]` 18＝➖10／⏸6／📎2、`[HEAD 現查]` 6；矩陣 §7 現算 78 鍵＝✅14／⚠️21／❌28／➖15；(c)＝(29+8)/(101−33)＝37/68＝54.4%。
5. **沒有被悄悄丟掉的高風險要求（逐項落點）**：
   - 600／1200s 兩段 → v2.1.8 §4.1.5（量不到＝cap≤cap_prepare，不是 cap=0，R-4.1.5-1）；§8 列 6 同步改寫；`degraded_cap` 出廠 2。
   - 指數退避不轟炸端點 → `claim_refresh_slot`（`quota_gate.py` L591）每 TTL 至多補量一次，失敗亦占名額；紅線 1 四條件在 📎 §15.5 列。
   - RESET_CONFIRM_PERCENT／full-jitter → C2＋§4.5.10（`endpoint_probe_verdict`：端點新鮮且每軸 <100% 才算 open；負向由付費探針或掛回零成本巡邏；月度 spend 撞線仍 escalate，E3 鎖）。
   - BURSTING 的週額度否決 → BURSTING 未啟用（`bursting_ok` 零呼叫端），否決路徑不存在；DEF-200-198 已讓 cap 真的限制派工。
   - §4.7 → 派發帳（跨 session 單一帳；SA-04 失效姿態除外）。
   - §5 → §1.3 非目標前提紀律；全庫無 API_KEY 模式；`claude --help` 無 `--max-turns`（0 命中）。
   - §7 → `PlaybookCheckpoint`（checksum＋`os.replace`＋fsync）＋RELAY 狀態塊；「不存可執行命令字串」→ §12 命令執行 ✅。
   - §6 超額鍵 → P4 ⏸（`FALLBACK_KINDS` 不進 cap 聚合、LIMIT_SPEND escalate、`--pace` 現況行）。
   - §8 列 5／§4.6 → OS 排程 `StartWhenAvailable`／`WakeToRun`＋睡眠姿態出聲＋引擎 `sliced_sleep` 時鐘跳躍增量帳（睡著＝晚醒，不是損失）。
   - §15.4 P0～P5 → 出場題所指功能列逐項在 §16.2 或 ✅ 清單（§5 表）；P 系列不是第二份需求（§14 L2394 明文「請以 §15.4 為準」，§15.4 自身是施工順序）。
   - §13／§12／§6.1 這些 PRD 自稱「必要」「必須實作」的列沒有被退役（皆 ⏸）。
6. **「決策式收斂」的權威**：§16.1 把 Daemon／多 agent worktree 整合／API_KEY 三項寫進 ➖ 定義，修訂表 v2.1.17 列寫明「各列歸格＝主控代決（掌舵者授權…非逐列明示追認；掌舵者可隨時以 §16.5 (i) 推翻任一格）」——揭露誠實。新增決策（T4、§5、§4.4.2、§7、§11.6）本身合理：AutoClaude 是逐 step 順序的單 agent 引擎，tripwire 釘住前提。

### 6.1 我認真考慮過 P2、最後否決的候選（讓 APPROVE 可被反駁）

| 候選 | 為什麼曾像 P2 | 為什麼否決（現查事實） | 落在 |
|---|---|---|---|
| §4.6 防休眠「刻意不做」無決策紀錄 | ➖ 的依據若「不存在」即 P2 | 依據座標存在（矩陣列、`endurance_env.py`、PRD §4.6 自身「長等待改用排程器交棒」L1726、DEF-200-020），只是「刻意」二字無紀錄；後果＝晚醒不是損失（`StartWhenAvailable`／`WakeToRun`／時鐘跳躍增量帳） | SA-05 |
| §4.7／§7 以「Daemon 形態」退役，但 §15.2 列為必建 | 兩個 PRD 自稱必建的模組被 ➖ | 功能等價物現查成立（派發帳＋RELAY 狀態塊＋`PlaybookCheckpoint`，皆有測試）；缺的是「依據句領頭」與失效姿態揭露 | SA-04 |
| 派發帳壞掉＝不節流（fail-open），違反紅線 6「鎖搶不到→降級」字面 | 安全姿態與 PRD 條文相反 | 這是 `quota_ledger` 的既有 P0 取捨（守衛失敗會硬鎖所有工具）；halt 帶不經派發帳；破壞面＝系統暫存目錄寫不進；非本輪新造 | SA-04 |
| §4.5.3 步驟 4「C=1 起步」被靜默丟 | 重置後暴衝是安全／財務面 | C1＋DEF-200-242（暴露 0：50 次翻頁、7 次 cap→free、首列 live 全 ≤1）＋§15.6「pace_index 天然免疫」已承接；缺的是連線 | SA-01 |
| §11.3 殘留漏「git status clean」 | 📎 的「機制已 ✅」可能不成立 | 原子 checkpoint／kill -9 回退／FRESH 降級／喚醒成本落帳皆 ✅ 且有檔有測；「clean」那半依賴 §4.5.1 ⏸（已登記附症狀） | SA-08 |
| §11.2 的「獨立離線模擬器」是交付物不是資料 | 📎 定義只收校準值／fixture／證據 | 模擬器的目的由 `decide()` 純函式＋注入時鐘性質測試承擔；機制在、測試在 | SA-07 |
| P4 ⏸ 的 `is_enabled=false` 現況句（財務、PRD 自稱最危險） | 財務風險的承接目標有不準確的現況句 | 承接本身存在：`FALLBACK_KINDS`、LIMIT_SPEND escalate、`--pace` 現況行（本場「此帳號沒有 usage credits」）；P4 ⏸ 非本鏡退役範圍 | SA-11 |
| §5 退役後無 `ANTHROPIC_API_KEY` 偵測 | 財務：API 計費無硬預算 | §1.3 前提紀律保留；全庫無 API_KEY 模式；CLI 認證優先序未驗證、暴露未知，只登記 | SA-12 |
| §15.4 P0～P5「施工順序退役」是否真被承接 | 5 列 ➖ 可能丟出場題 | 逐項對照（§5 表）：出場題所指功能列皆在 §16.2／✅ 清單；唯 P0 的「單 Step 額度成本資料」指向不準 | SA-09 |

## 7. 附錄：現查指令與逐字輸出摘要（皆唯讀）

A. 基準：`git rev-parse HEAD`＝`cec520baa895597664896206322369755816744a`；PRD 工作樹 `shasum -a 256`＝`a7430528f314e537bb37b675d4a7dd7a4defaccacf7121507329f22d2841a934`（開場與收尾兩次相同）、`stat -f '%Sm'`＝`Oct 10 10:20:13 2026`、`wc -l`＝2902。

B. §16.2 解析（`sa114_parse.py`，scratchpad）：`72`、`Counter({'➖': 33, '⏸': 31, '📎': 8})`；交叉表 `('⚠️','⏸') 25／('⚠️','➖') 19／('⚠️','📎') 7／('❌','⏸') 6／('❌','➖') 4／('❌','📎') 1／('➖','➖') 10`；`SA flagged: 18 Counter({'➖': 10, '⏸': 6, '📎': 2})`；`HEAD flagged: 6`。

C. 矩陣 §7：`78 Counter({'❌': 28, '⚠️': 21, '➖': 15, '✅': 14})`。

D. tripwire：`cd AutoClaude && python -m pytest tests/contract/test_def200246_integration_queue_tripwire.py -q -o addopts="" -p no:cacheprovider` → `6 passed in 0.38s`、rc=0（輸出落 `sa114_tripwire.txt`）。

E. 本機 CLI：`claude --version`＝`2.1.296 (Claude Code)`；`claude --help` 落檔 `sa114_claude_help.txt`，`grep -c -- '--max-turns'`＝`0`；含 `--max-budget-usd <amount>`「Maximum dollar amount to spend on API calls (only works with --print)」與 `--permission-mode <mode>`、`--allowedTools, --allowed-tools <tools...>`。

F. `python tools/session_resume_planner.py --pace`（一次）：「現在可派 1 個 agent（硬上限 cap=1，本視窗已用 0 次）｜band=prepare｜最緊的一條＝five_hour 37% 剩 188 分鐘」…「派工前置：方案指紋=five_hour+session+seven_day+spend+weekly_all+weekly_scoped｜此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆」…「來源=cache 量測於=2026-10-10T10:48:19+08:00」。

G. 收尾 `git status --short`（落 `sa114_gitstatus_end.txt`）與開場逐字相同：` M CLAUDE.md`、` M docs/01_requirements/…PRD_v2.1.md`、` M docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`、` M docs/04_planning/AutoSDD_improving_112.md`、` M docs/04_planning/AutoSDD_improving_113.md`、` M docs/06_quality/CrossPlatform_R145_Scan_Findings.md`、` M docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md`、` M tools/ruff.toml`、` M tools/tests/test_adr_xplat001_c1c2_lock.py`、` M tools/tests/test_subprocess_encoding_hygiene.py`、`?? docs/04_planning/AutoSDD_improving_114.md`（共 10 個 M＋1 個 ??）。我寫的檔只有 scratchpad 內的 `sa114_*` 與本檔。

H. H1 母體證據（SA-07 (c)）：`wc -l /var/folders/ld/fkzj758537q6sf9dgzdw83zr0000gn/T/autosdd_quota_degraded.jsonl`＝167；首列 `{"at": "2026-09-19T09:08:05+08:00", "source": "no-account-key", …}`、末列 `at=2026-10-10T09:00:21+08:00`；`sysctl -n kern.boottime`＝`{ sec = 1789779859, usec = 946095 } Sat Sep 19 09:04:19 2026`；`~/.autosdd/traces/quota_burn.jsonl`＝`rows 410 first 2026-08-12T22:45:43+08:00 last 2026-10-10T10:48:19+08:00`。37 符號序列 `UMMMUMMMMUMUMMUMMUUUMMMMUMMMUUMUUMUMM` 在 tools／AutoClaude／.claude 零命中。

I. SA-05 證據原文：`docs/04_planning/R85_HANDOFF.md` L55「mac 不休眠的**可行解是 `caffeinate`**（不需 sudo、不改任何持久設定 ⇒ 不在已否決的 `pmset repeat` 射程內）」；`docs/04_planning/R86_HANDOFF.md` L64「R85 已實測否決「每 50 分鐘」；mac 解＝`caffeinate`。本輪未新增量測」；`docs/06_quality/CrossPlatform_R85_Ledger_Closure.md` L331「**另一半刻意不做**：由 repo 自己下喚醒憑證（`pmset repeat`）需 sudo 且會改動掌舵者機器的電源行為，**已由掌舵者否決**」。

J. SA-04 失效姿態原文：`tools/lib/quota_ledger.py`「`claim_dispatch`…回它自己的那一個目錄項；`None`＝寫不進去（不得升級為守衛失敗）」；`tools/lib/quota_gate.py` `live_dispatches`「視窗內還算數的派發數。讀不到一律回 0（量不到 ≠ 節流）」＋`if quota_ledger is None: return 0`＋`note_degraded("ledger-unreadable", f"派發帳裡有 {unreadable} 個讀不懂的目錄項")`。

K. SA-11 證據原文：`tools/lib/quota_meter.py` L363–L372（見 SA-11）；`--pace` 現況行見 F。

— 完 —
````

### 二-4 SD 鏡

````text
# SD 唯讀審查鏡（Sonnet 5.5）— improving_114 終輪變更集：⏸ 現況對照／19 處註記／E501 退役碼

- 審查者：SD（系統設計／實作對照）唯讀鏡｜日期：2026-10-10｜基準：HEAD＝`cec520ba`（`git status --short` 與開場快照逐字相同：10 個 tracked 修改＋untracked `docs/04_planning/AutoSDD_improving_114.md`；本鏡全程零寫入 repo，結束時再比對一次仍相同）。
- 審的是工作樹**現況**（PRD 現為 2902 行、`git diff --numstat` ＝ `203	0`；QA 鏡第一輪看到的是 2901 行／202 行新增，主控在 QA 之後又補了 §16.1「母體外章節」段並把 §13 條款列由 📎 改 ⏸，所以 ⏸＝31、📎＝8）。

## 0. 判決

**VERDICT: APPROVE**

- P1／P2：無。
- P3：6 條（SD-01～SD-06），皆為文字／可觀測性訂正；歸格（四格結論）沒有任何一列因此翻面。
- P4：3 條（SD-07～SD-09），只登記，無動作。
- SD-01～SD-06 皆只改 PRD 文字、零程式碼；PRD 被直讀鎖釘住，改後須重跑 `test_context_budget_guard -k Prd`、`AutoClaude/tests/test_r100_boot_self_check.py`、`test_doc_loc_baseline_freshness_r60`（本鏡只跑了前兩者且皆綠；`test_doc_loc_baseline_freshness_r60` 本鏡未跑，QA 鏡第一輪跑過 281 支 OK，PRD 修動後須重跑）。
- 通過的主體：31 列 ⏸ 引用的檔案／函式／常數全數存在且行為如宣稱（逐列表見 §2；「零命中／不存在」類宣稱逐項以 grep 重驗，全部成立；字面上唯二的例外＝`autoclaude_*` 通配（SD-07）與 `index.lock` 的同形字串 `_ledger_index.lock_target_claims`〔列 16，實質成立〕）；19 處註記的實作座標在 HEAD 全為真（CLI 三條以 `claude --version`／`--help`／`--permission-mode …` 零 token 親跑重現，見 §6）；註記是**純插入**（difflib 20 個 insert 區塊、0 個 delete／replace，`git diff -U0` 的 `-` 行＝0，新增行中符合 `KEY=value` 形狀者＝0）；E501 反向鎖在現行 `tools/ruff.toml` 上＝綠、兩個紅條件各自真紅；被刪的識別字在 repo 內零個活的引用。

## 0.1 範圍與誠實劃界（先講我沒做什麼）

- 全程唯讀、零 git 寫入、零背景任務。跑過的只有：`python -m unittest test_subprocess_encoding_hygiene`（39 支）、`python -m unittest test_context_budget_guard -k Prd`（5 支）、`pytest AutoClaude/tests/test_r100_boot_self_check.py`（42 支）、`ruff check tools/tests/test_subprocess_encoding_hygiene.py`、以及零 token 的 `claude --version`／`claude --help`／帶非法旗標的 `--help`／`--version`／`python tools/lib/quota_policy.py --print-env-example`，外加純 Python 探針（import 測試模組函式餵合成輸入、`difflib` 比對 HEAD 與工作樹的 PRD、`git show HEAD:…`）與大量 `grep`／`sed -n`。單跑 unittest 前先 `export AUTOSDD_SENTINEL_OFF=1`（主控記憶：隔離 HOME 下單跑 tools/tests 會讓哨兵 GC 卸載活哨兵）。沒跑根層全套、AutoClaude 全套、SDD 全套；沒跑任何會燒 token 的 `claude -p`。
- 我**沒有**重判 101 列的四選一歸格結論（`[SA 判讀]` 六列仍只有作者自審＋本鏡的事實對照，improving_114 §7 的揭露仍然為真）；我也沒有重審 ✅ 29 列、➖ 33 列、📎 8 列的內容，只查了 ⏸ 列與註記**引用**到的其他列（§4.6／§4.7／§4.5.5／§11.3 等）是否互相一致。
- 取自 R211〈三〉理論洞表原文、本鏡**未獨立重跑**的行為宣稱：〈三〉#1（hook 對未帶 `model` 的 Agent 以視窗模型判額度軸）、#3／#9（PG／Dual 後端拒絕路徑未實跑、機器睡眠下單調鐘只依文件）、#8 中「被 timeout 砍掉的窗不落帳」。我只核了它們與〈三〉表文字一致、且相關檔案／函式存在。
- 列 24（§12 狀態回報 schema）與列 26（引擎路徑供應鏈）的「現況」是定性句、沒有座標，我只能判「方向與 HEAD 一致」，不是逐點驗證。
- 本鏡的 findings 正文落在 scratchpad（本檔）；依範本〈審查閉環〉DEF-200-090，主控須把它們抄進 repo 內具名檔案後才算落地（沿用 QA 鏡 P3-09 (ii) 的同一點）。

## 1. Findings 一覽

| ID | P | 位置 | 標題 |
|---|---|---|---|
| SD-01 | P3 | PRD:2640（§16.2 列 2，§4.1.1 T1） | 再開症狀點名的 `quota_burn.jsonl` 結構上不會有 unmeasured 列（症狀字面不可達；此錯誤沿自 QA 鏡 P3-03(a) 的建議） |
| SD-02 | P3 | PRD:2668（列 13，§6.1） | 「現況」漏列不變式 5、10，且把不變式 1 概括為已有機械物（其「HALT−DRAIN≥5」子句零機械物） |
| SD-03 | P3 | PRD:2694（列 28，§15.4 P4） | `extra_usage.is_enabled=false` 的出處是 R87 撞頂 payload，註解自己寫明它是「撞頂的後果」；本列引用時省略語境 |
| SD-04 | P3 | PRD:1161（C10 註記） | 「解不出時刻→掛回零成本巡邏」只對喚醒後確認路徑（`tick_plan`）成立；撞線首判路徑仍 `escalate` 且哨兵自我解除，註記的處置句跨情境套用 |
| SD-05 | P3 | PRD:2708（列 30，A5c） | 再開症狀「遠超同門檻下 FRESH 的預期」沒有可觀測判準；落帳列沒有 strategy 欄，無法從列本身分辨 RESUME／FRESH |
| SD-06 | P3 | PRD:2729（§16.3「讀法」） | 敘事寫「退役之後仍有 30 列」，表 (b)／交叉表／修訂表 L22 皆為 ⏸ 31（§13 條款列改 ⏸ 後未同步） |
| SD-07 | P4 | PRD:2653／2672／2677／2681／2683 等 | ⏸ 列「現況」措辭的幾處不精確（只登記） |
| SD-08 | P4 | PRD:2640／2661／2673 | 症狀所依的 planner／degraded 痕跡住系統暫存、重開機蒸發（只登記） |
| SD-09 | P4 | `tools/tests/test_subprocess_encoding_hygiene.py`、`tools/ruff.toml` | E501 退役碼的三個邊緣（棘輪常數本身無外部釘；全形冒號自觸發；「掌舵者裁決」字樣）（只登記） |

## 2. A．§16.2 的 31 列 ⏸ 逐列表（現況宣稱 vs HEAD）

符號：✓＝逐項現查成立；✗＝不成立或語境缺漏；PRD:行＝本工作樹的行號。「零命中」一律指 `tools/`、`.claude/`、`AutoClaude/autoclaude/` 三處以 `grep -rIE`（不走 ignore 規則）逐處計數皆為 0。症狀欄的禁字掃描（輪號／ISO 日期／「待排程」／下輪／候選／日後／到期／「輪」）對 31 列的「再開症狀＝」子句皆零命中，31 列皆有該子句。

| 列 | PRD:行／座標 | 現況宣稱逐項（✓／✗＋座標） | 症狀可觀測 | 改法 |
|---|---|---|---|---|
| 1 | 2639 §3.2 FSM | ✓ 無狀態 `decide()`（`tools/lib/quota_policy.py:682`）＋halt 閂鎖（`tools/lib/quota_gate.py:814-874`）；✓ v2.1.8 改 cap 語意（PRD:13 (D)(d)）；✓ `HALTED_MANUAL` 零命中；✓ `AutoClaude/autoclaude/plugins/hotkey_plugin.py:19-51` 只回 `VetoResult`、無 pause／resume；✓ 入口不呼叫 `register()`（`AutoClaude/autoclaude/main.py:246-249` 自陳；全樹唯一呼叫＝`execution/playbook_runner.py:375`）；✓〈三〉#2 | ✓（掌舵者真機事件，附畫面原文／sid） | 無 |
| 2 | 2640 §4.1.1 T1 | ✓ `CLAUDE_CODE_ENABLE_TELEMETRY`／`OTEL_` 零命中；✓ T5 升格＝v2.1.4（PRD:9） | **偏弱（SD-01）**：`quota_burn.jsonl` 不會有 unmeasured 列 | 見 SD-01 |
| 3 | 2641 T2 | ✓ `quota_floor_reading`（`tools/lib/quota_gate.py:767`）← `unhandled_limit_event`（`tools/lib/quota_limits.py:378`，呼叫點 `quota_gate.py:779`）；✓ 無視窗 token 加總（`tools/lib/resume_cost.py` 與 hook 的 usage 讀取＝單窗首請求／context 佔用，不是 T2 的本機消耗加總） | 偏弱（輕）：「T5 連續 unmeasured 滿 5h 窗」只能以 `quota_burn.jsonl` 的**空洞**為證，不是「列」 | 隨 SD-01 把「以空洞為證」寫明（可選） |
| 4 | 2642 T3 | ✓ `read_context_feed`（`.claude/hooks/context_budget_guard.py:500`）、`tools/install_statusline.py`、`tools/statusline_context_feed.py` 俱在；✓ feed 無 `rate_limits`（`statusline_context_feed.py:84-100`，鍵＝schema／session_id／ts／model／context_window／exceeds_200k_tokens／version；三檔 `rate_limits` 零命中）；〔P4：「只含 model 與 context_window」漏列 3 鍵，見 SD-07〕 | ✓（feed 樣本＋statusLine 輸入） | 無 |
| 5 | 2644 引擎獨立 | ✓ `AutoClaude/autoclaude/infra/adapters/file_quota_meter.py:82,115-122`（過期回 None）；✓ `core/ports/quota_meter.py:15-45` 自陳缺刷新者；✓ 守衛測試 `AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py:798`；✓〈三〉#4 | ✓ | 無 |
| 6 | 2649 §4.2.3 | ✓ `tools/lib/model_roles.py` 存在（三角色鍵）；✓ §6 區塊 4c（PRD:1849）；✓ 無任務類別過濾（`任務類別／task_class／大規模重構` 於 `.py` 非測試零命中）、無自動降級致動器；✓ THROTTLING＝converge 帶（`quota_policy.py:470-471`）；✓〈三〉#1（表文字一致，行為未重跑） | ✓（sid＋seq、`--pace` 畫面） | 無 |
| 7 | 2653 §4.3 | ✓ `WARN_RATIO=0.84`（`.claude/hooks/context_budget_guard.py:196`）；✓ 成本邊際 `compact_cost_budget_pp`（`quota_policy.py:284`、`quota_gate.py:495-514`）；✓ 機械 autocompact（`.claude/settings.json` env `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90`）；✓ `COMPACT_MIN_INTERVAL_SECONDS` 零命中；✓ `.claude/settings.json` hook 事件僅 SessionStart／PreToolUse／PostToolUse／Stop（無 PreCompact）；〔P4：「三 AND 已落地；缺 …」措辭互相打架，見 SD-07〕 | ✓（sid＋逐字稿座標） | 無 |
| 8 | 2656 §4.4.3 | ✓ `AutoClaude/autoclaude/utils/config.py:166` `step_timeout_seconds=600`、`core/kernel.py:184`；✓ `MAX_STEP_TURNS`／`MAX_STEP_QUOTA_PP`／`DRAIN_BUDGET_FACTOR` 零命中；✓ `claude --help` 對 `--max-turns` 計數 0（2.1.296，親跑） | ✓ | 無 |
| 9 | 2657 §4.5.1 | ✓ `core/services/auto_resume.py:362` `_freeze_is_safe`；✓ `infra/adapters/dirty_worktree_rescue.py:3-6` 救援只產 patch、不 commit；✓ 5 秒計時驗收缺（PRD:2335／2499 有要求、HEAD 無計時；亦記於 §11.3 📎） | ✓（sid＋seq 實錄） | 無 |
| 10 | 2658 §4.5.2 | ✓ `AutoClaude/autoclaude/utils/sliced_sleep.py` 存在；✓ `config.py:268-270`（30／5／18000）；✓ `auto_resume.py:316-333` 拒絕長睡、`main.py:256` rc=1；✓ 無根層承接者（`external_resume_required`／`scheduled_resume_at`／`python -m autoclaude` 於 tools／.claude／.github 非測試零命中）；〈三〉#3／#9 與表一致（PG／Dual、單調鐘兩點取自〈三〉原文） | ✓（sid；PG 後端真跑） | 無 |
| 11 | 2660 §4.5.4 | ✓ `tools/session_resume_planner.py:1099-1100` 32MiB；✓ `choose_resume_route`（:1138）無 weekly 條件，`tools/lib/resume_route.py` 與 planner 內 weekly／seven_day／U7d 零行；✓ `weekly_warn` 零命中；✓ `python tools/lib/quota_policy.py --print-env-example` rc=0，NOTICE／CONVERGE／PREPARE／HALT＝50／70／85／95、PACE_CEILING＝1 | ✓（sid＋`quota_burn.jsonl` 前後列；measured 列確實會落） | 無 |
| 12 | 2661 §4.5.10 | ✓ `PATROL_HANDBACK`（planner:529）／`tick_plan`（:532-565）；✓ E5 鎖 `PatrolHandbackIsItsOwnOutcomeTest`（`tools/tests/test_context_budget_guard.py:1569`）；✓ 行程內上限零命中（`MAX_PROBE_ATTEMPTS=5` 是跨醒來:214；`probe_quota` 單次 `timeout=180` :508）。註：單次醒來至多一次付費探針，症狀的「>3 次」分句結構上到不了，「>90 秒」分句可達 | ✓（planner 每列帶 `at`；痕跡壽命見 SD-08） | 無 |
| 13 | 2668 §6.1 | ✓ 1（嚴格遞增＋[0,100]：`tools/lib/quota_policy_env.py:58-70,283-285`）／4（`tools/lib/quota_boot_check.py:90-102`；rc=2＝planner:1535-1538）／6（`quota_policy_env.py:300-306`）／11,12,13（`AutoClaude/autoclaude/execution/boot_self_check.py`）；✓ 7b／8／9 未做；**✗** 不變式 1 的「HALT−DRAIN≥5」子句無任何機械物；**✗** 「現況」漏列 5（H7 占位 60s：`quota_boot_check.py:43`）與 10（遙測來源／防休眠啟動自檢零命中），矩陣 L119 原記 ⚠️5、10 | ✓ | **SD-02** |
| 14 | 2672 §8-1 | ✓ `AutoClaude/autoclaude/plugins/token_guard/policy.py:194-201`＋`core/kernel.py:293`；✓ 地板（`quota_gate.py:767`）；✓ 推論端無 `Retry-After`／jitter／5 次；〔P4：通道未界定——usage 端點的 `retry_after_at`（`tools/lib/quota_meter.py:670-712`）只給人話面；Brain 通道的 `RetryPolicy(max_attempts=3, jitter=True)`〔`core/ports/brain.py:32-36`、`minimax_brain.py:38`〕是另一條路，見 SD-07〕 | ✓（run log＋`Retry-After` 值） | 無 |
| 15 | 2673 §8-2 | ✓ 同列 12 | ✓ | 無 |
| 16 | 2674 §8-3 | ✓ 零命中（唯一字面 `tools/archive_defect_log.py:616` 是 `_ledger_index.lock_target_claims`，不是 git 鎖）；✓ R206 證據檔:133「瞬時 `index.lock`、rc=128、數秒自解」 | ✓（sid＋git stderr） | 無 |
| 17 | 2677 §8-9 | ✓ `NEEDS_HUMAN` 零命中；✓ 無進度即停（`tools/lib/relay_machine.py:22,59-65`）；～ 逾時→ESCALATION 非專屬映射：`core/kernel.py:184-190` 只把 timeout 傳給 executor，ESCALATE 來自一般失敗→重試→`max_retries_exhausted`（:299-302）〔P4，SD-07〕 | ✓ | 無 |
| 18 | 2679 §8-12 | ✓ `infra/adapters/sdk_executor_adapter.py:60-71`（`build_tool_allowlist_predicate`，deny-by-default）；✓ `.claude/settings.unattended.json` allow 含 `Bash(python -m pytest*)` | ✓（逐字稿＋URL 可引） | 無 |
| 19 | 2681 §9 指標 | ✓ PRD §9 十二個 `autoclaude_*` 具名指標逐一零命中；✓ `prometheus`／`otlp` 零命中；〔P4：通配字面「`autoclaude_*` 零命中」不成立（20 檔測試名／logger／venv 名命中，皆非指標），見 SD-07〕 | ✓（需求原文） | 無 |
| 20 | 2682 §9 決策日誌 | ✓ 痕跡家族：`quota_gate.py:664-685`（`note_degraded`）、`tools/lib/quota_escalation.py:352`（`_append_trace`）、`quota_burn.jsonl` | ✓（sid＋seq 查無列） | 無 |
| 21 | 2683 §9 告警 | ✓ DIRTY_UNSAVED notifier（`dirty_worktree_rescue.py:278,297`、`main.py:150`）；✓ 桌面通知存在（`quota_escalation.py:549`）；〔P4：預設**關閉**，`NOTIFY_ENV=AUTOSDD_DESKTOP_NOTIFY`、:97-103，使用者 2026-08-09 直接指令；本列「已有」未註明 opt-in，見 SD-07〕；✓ `NEEDS_HUMAN`／429 突增零命中 | ✓ | 無 |
| 22 | 2684 §12 旗標 | ✓ `tools/lib/resume_route.py:138` acceptEdits＋settings；✓ `AutoClaude/autoclaude/utils/config.py:416-417` `permission_mode` Literal 含 `bypassPermissions`；✓ `ALLOW_PERMISSION_BYPASS` 零命中 | ✓（config＋sid） | 無 |
| 23 | 2685 §12 寫入 | ✓ `.claude/hooks/block_destructive_git.py:1444-1458`（`_GOV_DIR_PREFIX=".autoclaude/"`、`_GOV_EXACT` 含 `.env`；**不含** `resume_route.py`／`model_roles.py`）；✓ 專案根外一律放行（:1507-1508）；`.git/`、`~/.ssh` 不在表 | ✓ | 無 |
| 24 | 2686 §12 schema | 定性、無座標；方向與型別化 dataclass 的狀態物件一致，未逐點驗 | ✓ | 無 |
| 25 | 2687 §12 遮蔽 | ✓ `AutoClaude/autoclaude/infra/repositories/pg_state_repository.py:75` `_redact`（另 `factory.py:33`）；✓ `REDACT_SECRETS_IN_LOGS` 零命中 | ✓ | 無 |
| 26 | 2688 §12 供應鏈 | ✓ unattended settings allow 無 pip／npm、無 install／postinstall 規則；「引擎路徑未覆蓋」未獨立重測 | ✓ | 無 |
| 27 | 2689 §13 | ✓ PRD:2857（B-16「❌ 無法核實…仍為上線前必要檢核項」）、:2881（B.3 #1）；✓ 「使用條款」字面僅出現在 PRD、R98（:171,294,320）、R211 矩陣（:150,201,219；為此宣稱出處） | ✓（原文／落款） | 無 |
| 28 | 2694 §15.4 P4 | ✓ `OVERAGE_POLICY=ALLOW_WITH_CAP` 零落地（`quota_policy.py:113-117,707` 僅註解 FREEZE）；✓ `OVERAGE_ALERT_ON_FIRST_USE`／`OVERAGE_MONTHLY_UTILIZATION_HALT` 零命中；✓ §4.6／§4.7＝➖（PRD:2662-2663）、§4.5.5＝✅；**✗（語境）** `extra_usage.is_enabled=false` 取自 R87 撞頂 payload（`tools/lib/quota_meter.py:364-373`） | ✓（`quota_burn.jsonl` 列或帳單） | **SD-03** |
| 29 | 2706 A4 | ✓ `AUTOSDD_QUOTA_BURNDOWN`／`burn_down` 零命中；✓ Addendum Status＝Adopted（`docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md:5`）；✓ PRD 無 §4.2.9；✓ 無未結帳列（DEF-200-232 closed-by-decision，`docs/06_quality/AutoSDD_Defect_Log_archive_68.md:129`） | ✓（`--pace` 畫面＋sid） | 無 |
| 30 | 2708 A5c | ✓ `tools/lib/resume_cost.py`（落 `autosdd_resume_cost.jsonl` :33；pct 欄恆 None :17、`build_record` :90-106）；✓ DEF-200-508 fixed（`AutoSDD_Defect_Log.md:281`）；✓ spawn 前授權預檢（planner:1199、`resume_route.py:185`）；✓ 32MiB 仍是常數（planner:1100） | **偏弱（SD-05）** | **SD-05** |
| 31 | 2709 A7 | ✓ `docs/04_planning/PRD_Amendment_R121_UnattendedCommitPush.md:3` Status＝Proposed；✓ `AUTOSDD_UNATTENDED_PUSH_OFF` 零命中；✓ `.claude/settings.unattended.json` deny `Bash(git commit*)`／`Bash(git push*)`（另有 PowerShell 版） | ✓（sid＋seq 實錄） | 無 |

## 3. B．§16.4 的 19 處「🔴 【v2.1.17 註記】」逐處驗證

`grep -n "v2.1.17 註記" <PRD>` 共 21 行＝19 處註記（C1～C12 皆有）＋修訂表 L22＋§16.4 開場 L2733 的說明句。以下 19 處逐處讀過原文，座標在 HEAD 現查：

| # | PRD:行 | C-ID／所在節 | 實作座標與驗證結果 | 判 |
|---|---|---|---|---|
| 1 | 127 | C9 §1.2 原則 2 | `probe_quota`（`tools/session_resume_planner.py:478`）先問 L0 `endpoint_probe_verdict`（`tools/lib/quota_gate.py:741`，None 才付費）；無人模式 `UNATTENDED_ENV in os.environ` 即回「不付費探測」；`probe_argv` 用 `model or _roles().downgrade`（`tools/lib/resume_route.py:126-128`）；ADR-XPLAT-005 §3.3 確有「`probe_quota()` 先讀快取、讀不到才付費探測」 | ✓ |
| 2 | 288 | C12 §4.1.3 | `tools/lib/quota_pace.py:112` `_ROLLOVER_EPS = 0.5`；`segments()`（:549-567）任一軸下降超過 0.5 即斷點；`RESET_DROP_THRESHOLD` 在 PRD:280／532／2328 確被引用 | ✓ |
| 3 | 486 | C8 §4.2.3 | `WEEKLY_HALT_PERCENT`／`WEEKLY_DRAIN_PERCENT`（含 `WEEKLY_`、`ENABLE_WEEKLY_LIMIT_GUARD`）於三處零命中；單一 band 組 50／70／85／95（`quota_policy.py --print-env-example` rc=0）；halt 取「≥halt 各軸最早可 reset 者」（`quota_gate.py:849`） | ✓ |
| 4 | 592 | C1 §4.2.4 (c) | `tools/lib/quota_stability.py:36-40`（`cap is None`＝`BAND_FREE` 直通並清空持久狀態）；DEF-200-242 `closed-by-decision`（`AutoSDD_Defect_Log.md:160`：50 次翻頁／7 次 cap→free／首列 live 全 ≤1＝暴露 0）；PRD:575 的 (c) 論據確寫「已經有既有守衛」 | ✓ |
| 5 | 979 | C8 §4.2.8 | 單鍵 `AUTOSDD_QUOTA_PACE_CEILING` 出廠 1.0（`tools/lib/quota_policy_env.py:91`；`--print-env-example` 印 `PACE_CEILING=1`）；`WEEKLY_PACE_CEILING_*`／`FIVE_HOUR_PACE_CEILING` 零命中；PRD:976-977 確含 1.25／1.50 | ✓ |
| 6 | 1056 | C3 §4.4.3 | `claude --help` 對 `--max-turns` 計數 0；PRD:1047 `MAX_STEP_TURNS … # CLI 的最大回合數旗標` 確在 | ✓ |
| 7 | 1092 | C5 §4.5.2 | `session_resume_planner.py:217` `RESET_SKEW_SECONDS = 120`；`RESET_BUFFER_SECONDS=30` 在 PRD:1081／1913；ADR-XPLAT-014 §3.5 Q4 ② 即此題 | ✓ |
| 8 | 1104 | C2 §4.5.3 | `endpoint_probe_verdict`（`quota_gate.py:741-766`）：端點新鮮且每軸 <100% 回 open、否則 None；`RESET_CONFIRM_PERCENT` 三處零命中 | ✓ |
| 9 | 1125 | C6 §4.5.4 | `choose_resume_route`（planner:1138）以 `transcript.stat().st_size` 比 `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`（:1099-1100，32MiB）；`resume_route.py`／planner 內 weekly 規則零行；ADR Q4 ④「只登記」屬實 | ✓ |
| 10 | 1140 | C3 §4.5.4 | `claude --version`＝2.1.296；`--max-turns` 0；`claude --definitelynotaflag --help` rc=0 並印 usage（**「`--help` 會短路未知旗標」親跑成立**）；`resume_route.py` 零 `--max-turns`；`timeout=3600`（planner:1227）；`max_spawns()`（`tools/lib/relay_machine.py:107`，出廠 2＝:57）；INV4（`relay_machine.py:114`）；`AutoClaude/autoclaude/utils/verified_cli_versions.py` 於 2.1.295 條目前的註解逐字記載「`--max-turns` 不在本版 help」 | ✓ |
| 11 | 1142 | C4 §4.5.4 | `resume_route.py:45`（`UNATTENDED_SETTINGS`）、`:138`（`--permission-mode acceptEdits --settings …`）；`resume_route.py` 零 `--allowed-tools`；`tools/lib/unattended_authz.py` 存在；ADR Q4 ③ | ✓ |
| 12 | 1161 | C10 §4.5.5 | `tick_plan`（planner:532-565）「不猜」＋解不出→`PATROL_HANDBACK`（:529）屬實；**但處置句「以 §4.5.10 R-4.5.10-2 為準」所涵蓋的情境比這兩個座標寬**，見 SD-04 | ✓（座標）／SD-04 |
| 13 | 1606 | C2 §4.5.10 | 指向 §4.5.3 同項註記，屬實 | ✓ |
| 14 | 1834 | C8 §6 區塊 3／4（`.env` 圍籬內 `#` 行） | `WEEKLY_*`／`FIVE_HOUR_PACE_CEILING`／`PACING_MODE`／`PACE_MIN_UTILIZATION` 於三處各 0 命中；`ENV_SPEC`（`quota_policy_env.py:58-70,91`）與 50／70／85／95、1.0 相符 | ✓ |
| 15 | 1920 | C2／C5／C6 §6 區塊 9（圍籬內 `#` 行） | 同 #8／#7／#9；PRD:1913-1919 的 `RESET_BUFFER_SECONDS=30`／`RESET_CONFIRM_PERCENT=10`／`RESUME_MAX_TRANSCRIPT_TOKENS=60000` 鍵行原樣在 | ✓ |
| 16 | 2017 | C11 §6.1 末 | `load_policy` 越界＝整組退回 `DEFAULT_POLICY`＋回 problems（`quota_policy_env.py:283-306`）；CLI 側 `validate_dynamic_pacing_invariants` 越界→`return 2`（planner:1535-1538），H6／H7 標籤在 `tools/lib/quota_boot_check.py:90-102` | ✓ |
| 17 | 2329 | C1 §11.2 | 同 #4；「R198 證據檔〈四〉4.3 裁決表第 5 列」＝`docs/06_quality/CrossPlatform_R198_FiveQuestion_SymptomGate_FirstEval_Evidence.md:60` | ✓ |
| 18 | 2860 | C7 附錄 B-09 | `--permission-mode` choices＝acceptEdits／auto／bypassPermissions／manual／dontAsk／plan；`claude --permission-mode default --help` **rc=0**、`claude --permission-mode zzzz --help` **rc=1** 且逐字回 `Allowed choices are acceptEdits, auto, bypassPermissions, manual, dontAsk, plan.`（親跑，與註記逐字相同）；ADR Q4 ⑤ | ✓ |
| 19 | 2862 | C3 附錄 B-10 | 同 #6 | ✓ |

零改字證據（對「註記有沒有改到任何既有條文字」）：

- `git diff --numstat -- <PRD>` ＝ `203	0`；`git diff -U0` 以 `grep -c '^-[^-]'` 計 `-` 行＝**0**。
- 以 HEAD 版與工作樹版做 `difflib.SequenceMatcher`：非 equal 的 opcode 只有 `insert`（20 個區塊、203 行），**無 delete、無 replace**；因此既有 2699 行逐字不變。
- 新增行中符合 `^[A-Z][A-Z0-9_]{2,}=` 者＝**0**；§6 `.env` 圍籬內的新增行只有 3 行 `#` 註解（WT:1834、1835、1920）。`test_context_budget_guard -k Prd`＝`Ran 5 tests … OK`；`AutoClaude/tests/test_r100_boot_self_check.py`＝`42 passed`（PRD 直讀鎖，主控在 QA 之後又改過 PRD，本鏡重跑）。
- 註記全文出現的 DEF／ADR／docs 路徑（DEF-200-146／198／204／234／242／246／458／508；ADR-XPLAT-005／014；6 個 docs 路徑）皆存在；53 個路徑類反引號 token 中，不存在的只有 CLI 片段、runtime 痕跡檔名（`quota_burn.jsonl`／`autosdd_quota_degraded.jsonl`）與省略目錄前綴的 `model_roles.py`／`resume_route.py`（皆在 `tools/lib/`）。

## 4. C．E501 退役碼（`git diff tools/ruff.toml tools/tests/test_subprocess_encoding_hygiene.py`）

| 項 | 檢查 | 結果 | 證據 |
|---|---|---|---|
| (i) | `e501_no_calendar_verdict`（`tools/tests/test_subprocess_encoding_hygiene.py:1381`）在現行 `tools/ruff.toml` 上 | **綠**（回 `None`） | 退役記載 `# 退役到期日（2026-10-10，…`（全形括號，不是全形冒號）→ `_E501_CALENDAR_EXPIRY_RE`＝`到期日：\d{4}-\d{2}-\d{2}` 不命中；檔內另一處「到期日」是 `「到期日要真的會到期」`（無冒號＋日期）亦不命中 |
| (i) | 紅條件 A：加回 `到期日：YYYY-MM-DD` | **紅** | 對現檔附加 `到期日：2026-12-31` → `…又出現日曆到期 '到期日：2026-12-31' —— 掌舵者 2026-10-07 裁決不製造特定日期的義務…`；對 **HEAD 版**舊 ruff.toml（`到期日：2026-11-02`）亦紅（證明新鎖若早一天進來，舊 toml 過不了） |
| (i) | 紅條件 B：刪掉「退役到期日」記載 | **紅** | 對現檔把 `退役到期日` 全換掉 → `tools/ruff.toml 的 E501 存量債豁免不再記載「退役到期日」—— 那段記載是「為什麼沒有日期」的唯一答案…` |
| (i) | 判準是純函式、不讀時鐘 | ✓ | 簽名 `(text) -> str \| None`，無 `today` 參數；`git grep` 該檔 `date`／`datetime`／`today(`／`.now(` 皆 0 |
| (ii) | ruff.toml 註解引用的識別字存在 | ✓ | `_E501_DEBT_CEILING`（:1355）、`TestRootToolsLintPolicy`（:1399）、`test_the_e501_waiver_has_no_calendar_expiry_by_decision`（:1463）、`test_the_no_calendar_criterion_is_red_when_it_should_be`（:1480，測試 docstring 引用）、`test_e501_debt_only_shrinks`（:1450）、`test_rule_set_is_identical_to_the_autoclaude_side`；`docs/06_quality/CrossPlatform_R207_FiveQuestion_Retire_Time_Triggers_Decision.md`、ADR-XPLAT-010、`docs/04_planning/ADR-XPLAT-013_Phase2_Proposal_R108.md` 等其餘路徑皆在 |
| (iii) | 刪掉 `from datetime import date` 沒有其他使用者 | ✓ | `ruff check tools/tests/test_subprocess_encoding_hygiene.py` → `All checks passed!`（rc=0）；該檔對 `\bdate\b`、`datetime`、`today(`、`.now(` 零命中 |
| (iv) | `_E501_DEBT_CEILING` shrink-only 測試仍在且會紅 | ✓ | `_E501_DEBT_CEILING = 139`（:1355）、`test_e501_debt_only_shrinks`（:1450-1459）斷言 `assertLessEqual(actual, _E501_DEBT_CEILING)`；現值 actual＝139＝ceiling（餘裕 0）⇒ 任何新增的過長行即紅；在 scratchpad 複本加合成過長行，`_overlong_line_count` 逐行遞增（複本基底 1 → 加 1 行 2 → 再加 1 行 3），本檔改動不影響 actual（139 不變） |
| (v) | 被刪識別字（`e501_waiver_verdict`／`test_the_e501_waiver_expiry_is_actually_enforced`／`_E501_WAIVER_MAX_DAYS`，另加 `_E501_EXPIRY_RE`／`test_the_expiry_criterion_is_red_when_it_should_be`）的殘留 | ✓ 無活的引用 | 全 repo（排除 `.git`／`.venv`／`__pycache__`）共 7 行命中，皆為歷史敘述或快取：`tools/tests/test_adr_xplat001_c1c2_lock.py:2633`（重釘日誌字串）、`docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md:139`（〈八〉敘述）、`docs/06_quality/CrossPlatform_R76_Scan_Findings.md:201`（R76 史料）、`.pytest_cache`×2 與 `tools/tests/.pytest_cache`（`git ls-files` 0 筆、`.gitignore:10` 已排除的本機快取）；無 import、無 workflow、無測試呼叫 |
| 其他 | 測試數不變 | ✓ | `python -m unittest test_subprocess_encoding_hygiene` → `Ran 39 tests … OK`（刪 2、增 2；HEAD 與工作樹皆 39 個 `def test_`） |

## 5. Findings 明細

### SD-01 [P3] 列 2（T1）的再開症狀點名了結構上不存在的痕跡列
- 位置：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md:2640`。
- 證據逐字：PRD:2640＝`再開症狀＝\`quota_burn.jsonl\` 出現 unmeasured 列的同一窗內，有人明示需要逐 token／逐請求的成本明細才能決策，而 T5／T3 皆給不出（附該列座標與該次需求原文或 sid）`。
  - `tools/lib/quota_gate.py:360-363`：`def record_burn(...)` 首行 `if not state.usable() or not state.measured_at: return False`；`QuotaState.usable()`＝`len(self.axes) > 0`（`tools/lib/quota_policy.py:223-225`）⇒ **量不到就不落列**。
  - 列的結構只有 `ts／pct／live／fp／resets_at`（`tools/lib/quota_pace.py:625-636`），沒有「unmeasured」這種列型。
  - unmeasured 的痕跡在另一個檔：`tools/lib/quota_gate.py:682-685`（`note_degraded` 落 `autosdd_quota_degraded.jsonl`、`"state": quota_policy.BAND_UNMEASURED`）；PRD 自己在 L533 就寫了「measured 事件源＝burn ledger（只有量到才落款）／unmeasured 事件源＝`autosdd_quota_degraded.jsonl`」，PRD:2698 還寫了該檔「住系統暫存、重開機即蒸發」。
  - 來源：QA 鏡第一輪 P3-03(a)（`qa_mirror_114_findings.md:120`）的建議文字「例如 `quota_burn.jsonl` 出現 unmeasured 列」被原樣採納——鏡的建議也要零信任，這一條沒有人驗過機制。
- 為什麼是 P3 不是 P2：歸格（T1 仍是 ⏸）不受影響；症狀後半（有人明示需要逐 token 明細而 T5／T3 給不出）仍可觀測；改的只是「在哪個檔看 unmeasured」。但照字面這一支前提條件永遠到不了，違反 §16.1 自己的「再開症狀必須可觀測」紀律。
- 修法（一句）：把「`quota_burn.jsonl` 出現 unmeasured 列」改為「`autosdd_quota_degraded.jsonl` 出現 `state` 為 `unmeasured` 的列（系統暫存，當場附檔），或 `quota_burn.jsonl` 相鄰列出現超過 5 小時的空洞」；列 3、4 的「附 `quota_burn.jsonl` 列座標」同步寫成「空洞前後兩列座標」。

### SD-02 [P3] 列 13（§6.1）「現況」漏列 5／10、且把不變式 1 概括過頭
- 位置：PRD:2668。
- 證據逐字：PRD:2668＝`現況＝不變式 1、4、6、11、12、13 已有機械物，2、3、7c 矩陣判 ➖，7 隨 §5 判 ➖；未做＝7b／8／9（…）`；R211 矩陣 L119＝`✅1,4,6…；✅11,12,13…；⚠️5（H7 占位 60s）、10；➖2,3,7c；❌7,7b,8,9`。
  - 15 個子項只交代了 13 個；5、10 在矩陣是 ⚠️，本列沒提。5＝`tools/lib/quota_boot_check.py:43` `STEP_MEDIAN_WALL_SECONDS_PLACEHOLDER = 60.0`（待校準占位值，檔頭自陳「不是量出來的」）；10（至少一個遙測來源可用／防休眠驅動可用）在 `quota_boot_check.py`、`boot_self_check.py` 零命中。
  - 不變式 1 的完整式是 `0 < WARN < DRAIN < HALT ≤ 100 且 HALT − DRAIN ≥ 5`；HEAD 只有嚴格遞增＋`[0,100]` 值域（`tools/lib/quota_policy_env.py:58-70,283-285`），「HALT−DRAIN≥5」於 `tools/lib/`、`.claude/hooks/`、planner 零命中。
- 為什麼是 P3：歸格仍是 ⏸（7b／8／9 本來就未做）、症狀句「缺席的不變式所防之事實際發生」泛指也涵蓋 5／10；但「現況」欄是結案帳唯一的殘留清單，少列兩個部分落地的子項會讓它看起來比實況完整。
- 修法（一句）：本列「現況」補「5＝H7 中位牆鐘為占位值 60s、10＝啟動自檢無遙測來源／防休眠檢查（皆部分或未做）；1 僅機械化嚴格遞增與值域、『HALT−DRAIN≥5』子句未機械化」。

### SD-03 [P3] 列 28（§15.4 P4）引用 `extra_usage.is_enabled=false` 時省略它的語境
- 位置：PRD:2694；`tools/lib/quota_meter.py:364-373`。
- 證據逐字：PRD:2694＝`…現況事實上 FREEZE（…），本機帳號曾觀測 \`extra_usage.is_enabled=false\`（\`tools/lib/quota_meter.py\` 註解，一次性觀測、非人工確認）`；`quota_meter.py:364-371`＝`# 🔴 R87 事故墓碑 … **不要**因為桶自報 \`enabled: false\` / \`is_enabled: false\` 就把它排除在軸之外 … # 當時的 payload 逐字：\`extra_usage {"is_enabled": false, "monthly_limit": 500, "used_credits": 610.0, "utilization": 100.0, "disabled_reason": "org_level_disabled_until"}\` … \`enabled:false\` 是撞頂的**後果**，不是「這一軸不算數」`。
  - 即該觀測是「已經超出月度上限 610>500、額外用量購買因此被 org 層停用」的事故 payload，不是「本帳號沒有啟用超額」的平靜觀測；單句引用會被讀成後者。
- 為什麼是 P3：「零落地、現況 FREEZE」與「非人工確認」兩個結論都成立、歸格不變；錯讀的風險在於誤把 `is_enabled=false` 當成「超額池關著」的證據，而該註解正是為了禁止這種讀法而立。
- 修法（一句）：括號內補「（R87 當回合 payload 同時有 `used_credits 610 > monthly_limit 500`、`utilization 100`：`is_enabled=false` 是撞頂後果，不是池子關著，故不構成『本帳號未啟用超額』的證據）」。

### SD-04 [P3] C10 註記的處置句跨情境套用「掛回巡邏」
- 位置：PRD:1161（C10）；`tools/session_resume_planner.py:623-629`、`:1492-1504`；`tools/lib/quota_messages.py:90-99`；`tools/tests/test_context_budget_guard.py:2360`、`:1911`。
- 證據逐字：PRD:1161＝`…\`tick_plan\`… 明文「不猜」保留，解不出時刻不退回推估、而掛回零成本巡邏（\`PATROL_HANDBACK\`…）…處置＝上方「保守推估（…）」字面作廢，以 §4.5.10 R-4.5.10-2 為準`。
  - `tick_plan`（planner:532-565）：額度未恢復且探針輸出解不出新 reset ⇒ `PATROL_HANDBACK`（鎖＝`TickDecisionTest::test_still_closed_without_a_parseable_reset_refuses_to_guess`，:1911，斷言 `PATROL_HANDBACK` 且 `state != "abandoned"`）——**這是喚醒後確認路徑**。
  - 但 §4.5.5 被作廢的那句（PRD:1157-1158「若 weekly_reset_timestamp 不可得：→ 保守推估…」）對應的是**撞線首判**：`quota_messages.reset_branch(None)`→`QUOTA_BRANCH_ESCALATE`（`quota_messages.py:97-99`）；哨兵首次偵測到撞線事件但訊息解不出時刻 ⇒ `sentinel_decide` 回 `escalate`（planner:629，鎖＝`SentinelDecisionTest::test_an_unparseable_reset_refuses_to_guess`，test:2360，逐字斷言 `escalate`），`_sentinel_tick` 對 `escalate` 的處置是 `state="abandoned"`＋`_schtasks_remove`＋叫人（planner:1492-1504）＝終態，不是巡邏。
- 為什麼是 P3：註記所引兩個座標（`tick_plan`、`PATROL_HANDBACK`）與「不猜」都是真的；問題是處置句沒有限定情境，照它實作會把撞線首判也改成「掛回巡邏」，與 HEAD 兩支現行鎖相反。
- 修法（一句）：C10 補限定語——「解不出時刻：喚醒後確認路徑（`tick_plan`）掛回巡邏；撞線首判路徑（`reset_branch`／`sentinel_decide`）走 `escalate` 叫人（兩路皆不猜）；§4.5.5 的『保守推估』字面作廢」。

### SD-05 [P3] 列 30（A5c）的再開症狀沒有可觀測判準
- 位置：PRD:2708；`tools/lib/resume_cost.py:90-106`。
- 證據逐字：PRD:2708 症狀＝`落帳列（\`resume_cost\` jsonl）顯示某次 RESUME 窗首筆 assistant 輸入成本遠超同門檻下 FRESH 的預期、而 32MiB 位元組門檻放行了它（附 jsonl 列座標）`。
  - `build_record` 的欄位只有 `session_id／relay_seq／measured／first_assistant_ts／model／三個 usage 欄／pct_before／pct_after／reason／recorded_at`，**沒有 strategy 欄**（本列自己也寫「FRESH 路由窗與 RESUME 量不到列同形」）；要判某列是否 RESUME 得另以 `session_id` 去 planner 痕跡（`route_chosen`）對，而該痕跡住系統暫存。
  - 「遠超 FRESH 的預期」沒有基準：FRESH 窗的成本沒有被量過，也沒有任何數字門檻。
- 為什麼是 P3：機制與歸格（⏸）成立；只是這一句不能被第三者判定「發生了沒」，違反 §16.1 對症狀的要求。
- 修法（一句）：改成可現查形態——「`autosdd_resume_cost.jsonl` 某列三個 usage 欄合計的實數（附列座標）與同 `session_id` 在 planner 痕跡的 `route_chosen`＝`SESSION_RESUME`，並附掌舵者認定該成本不可接受的原話或帳單座標」。

### SD-06 [P3] §16.3 敘事的列數與表不一致
- 位置：PRD:2729。
- 證據逐字：PRD:2729＝`…退役之後仍有 30 列是「有意延後、等症狀」而不是「做完了」。`；同節表 (b)＝`✅ 29／➖ 33／⏸ 31／📎 8`，交叉表合計 ⏸ 31，修訂表 L22＝`✅29／➖33／⏸31／📎8`。我以腳本重算 §16.2 的 72 列：`⚠️→⏸25／➖19／📎7；❌→⏸6／➖4／📎1；➖→➖10`，閉格＝➖33／⏸31／📎8，與表一致；(c)＝(29＋8)÷(101−33)＝37÷68＝54.4%（✓）。
  - QA 鏡看到的是 30（§13 條款列當時在 📎）；主控把 §13 改 ⏸ 後，「讀法」段的這個 30 沒跟著改。
- 修法（一句）：PRD:2729「30 列」改「31 列」（或改成不寫死數字、引表 (b)）。

### SD-07 [P4，只登記] ⏸ 列「現況」的措辭不精確（皆不影響歸格）
- 列 4：feed 另含 `exceeds_200k_tokens`／`version`（`statusline_context_feed.py:94-99`）；列 7：「三 AND 已落地；缺 COMPACT_MIN_INTERVAL_SECONDS」（PRD 的三 AND＝K_ctx／成本／間隔，間隔缺）；列 14：Retry-After 的通道未界定；列 17：逾時→ESCALATION 是一般失敗路徑而非專屬映射；列 19：「`autoclaude_*` 零命中」通配字面不成立（`tools/` 20 檔與 AutoClaude/autoclaude 1 處註解含 `autoclaude_` 字樣：`autoclaude_logger`／`autoclaude_pytest`／`autoclaude_cleanvenv_*` 等，皆非指標；十二個具名指標確為零）；列 21：桌面通知 opt-in（`AUTOSDD_DESKTOP_NOTIFY`）。

### SD-08 [P4，只登記] 症狀所依的痕跡住系統暫存
- 列 12／15 的「planner 痕跡列」＝`autosdd_resume_log_<sid>.jsonl`，路徑＝`tempfile.gettempdir()`（`tools/session_resume_planner.py:436-439`），重開機即蒸發；列 2 的 degraded 痕跡同為 `tempfile.gettempdir()`（`quota_gate.py:632-633`）。PRD R-4.5.10-4 自述「查不到≠沒發生」，所以這些症狀要靠事發當下附檔，符合 §16.1「附 sid／log」的寫法，但觀察者得知道它會蒸發。

### SD-09 [P4，只登記] E501 退役碼的三個邊緣
- `_E501_DEBT_CEILING = 139` 本身沒有外部釘（機械面只有該測試檔自己引用它，docs／ruff.toml 的提及只是敘述；改大一行即放行，差別只在 diff 可見；本輪前後相同、不是新增）。
- `_E501_CALENDAR_EXPIRY_RE` 只認「全形冒號＋ISO 日期」；若日後把退役記載寫成 `退役到期日：2026-10-10`（全形冒號）會自己轉紅（我親跑 mutation D 重現；QA 附錄 E 末列同）。docstring 已誠實劃界盲區。
- `tools/ruff.toml` 與測試訊息寫「掌舵者裁決」；2026-10-10 這次實為授權主控代決（同 QA 鏡 P3-06 的字樣問題；2026-10-07 的「不製造日期義務」原則才是掌舵者直接裁決）。

## 6. 親跑輸出（逐字；每條前置 `source .venv/bin/activate; unset AUTOSDD_PARALLEL_TESTS`；rc 一律先導檔再 `echo rc=$?`；唯讀）

### 6.1 零命中普查（`grep -rIE`，不走 ignore 規則；tools 排除 `__pycache__`／`.git`／`.pytest_cache`）
註：`rate_limits` 的兩筆命中皆為註解（`tools/lib/quota_policy.py:129`、`AutoClaude/autoclaude/core/ports/quota_meter.py:107`：「不是 `rate_limits` 的 kind」），非 feed 實作；`external_resume_required|scheduled_resume_at|python -m autoclaude` 的 tools=2 皆為 `tools/tests/test_windowsapps_guard_cross_consistency.py` 的說明字串（非元件），autoclaude=72 是引擎自己的狀態庫；`index\.lock` 的唯一命中是 `tools/archive_defect_log.py:616` 的 `_ledger_index.lock_target_claims`；`ALLOW_WITH_CAP` 的唯一命中是 `quota_policy.py:117` 註解。
```
HALTED_MANUAL                                                            tools=0 .claude=0 autoclaude=0
CLAUDE_CODE_ENABLE_TELEMETRY|OTEL_                                       tools=0 .claude=0 autoclaude=0
rate_limits                                                              tools=1 .claude=0 autoclaude=1
COMPACT_MIN_INTERVAL_SECONDS                                             tools=0 .claude=0 autoclaude=0
MAX_STEP_TURNS|MAX_STEP_QUOTA_PP|DRAIN_BUDGET_FACTOR                     tools=0 .claude=0 autoclaude=0
weekly_warn                                                              tools=0 .claude=0 autoclaude=0
NEEDS_HUMAN                                                              tools=0 .claude=0 autoclaude=0
prometheus|otlp                                                          tools=0 .claude=0 autoclaude=0
ALLOW_PERMISSION_BYPASS                                                  tools=0 .claude=0 autoclaude=0
REDACT_SECRETS_IN_LOGS                                                   tools=0 .claude=0 autoclaude=0
OVERAGE_ALERT_ON_FIRST_USE|OVERAGE_MONTHLY_UTILIZATION_HALT              tools=0 .claude=0 autoclaude=0
AUTOSDD_QUOTA_BURNDOWN|burn_down                                         tools=0 .claude=0 autoclaude=0
AUTOSDD_UNATTENDED_PUSH_OFF                                              tools=0 .claude=0 autoclaude=0
RESET_CONFIRM_PERCENT|RESET_BUFFER_SECONDS                               tools=0 .claude=0 autoclaude=0
WEEKLY_|FIVE_HOUR_PACE_CEILING|PACING_MODE|PACE_MIN_UTILIZATION|ENABLE_WEEKLY_LIMIT_GUARD tools=0 .claude=0 autoclaude=0
external_resume_required|scheduled_resume_at|python -m autoclaude        tools=2 .claude=0 autoclaude=72
index\.lock                                                              tools=1 .claude=0 autoclaude=0
ALLOW_WITH_CAP                                                           tools=1 .claude=0 autoclaude=0
autoclaude_availability_flips_total                                      tools=0 .claude=0 autoclaude=0
autoclaude_burn_rate_pct_per_min                                         tools=0 .claude=0 autoclaude=0
autoclaude_concurrency                                                   tools=0 .claude=0 autoclaude=0
autoclaude_freeze_duration_seconds                                       tools=0 .claude=0 autoclaude=0
autoclaude_integration_outcome_total                                     tools=0 .claude=0 autoclaude=0
autoclaude_resume_cost_pp                                                tools=0 .claude=0 autoclaude=0
autoclaude_state_transitions_total                                       tools=0 .claude=0 autoclaude=0
autoclaude_step_quota_cost_pp                                            tools=0 .claude=0 autoclaude=0
autoclaude_step_wall_seconds                                             tools=0 .claude=0 autoclaude=0
autoclaude_telemetry_age_seconds                                         tools=0 .claude=0 autoclaude=0
PreCompact in .claude/settings*.json: .claude/settings.json:0 .claude/settings.unattended.json:0 
hook events in .claude/settings.json: ['SessionStart', 'PreToolUse', 'PostToolUse', 'Stop']
```

### 6.2 CLI（零 token；cwd＝/tmp）
```
$ claude --version
2.1.296 (Claude Code)
(rc=0)
$ claude --help | grep -c -- "--max-turns"   # 以導檔計數，等價
max-turns count: 0   （help 全文 311 行；任何大小寫變體 max.?turns 亦為 0）
$ claude --help  # --permission-mode 段
  --permission-mode <mode>              Permission mode to use for the session
                                        (choices: "acceptEdits", "auto",
                                        "bypassPermissions", "manual",
                                        "dontAsk", "plan")
  --permission-prompts <target>         Who answers permission prompts with
$ claude --definitelynotaflag --help   -> rc=0（印 usage，證實 --help 短路未知旗標）
Usage: claude [options] [command] [prompt]
$ claude --permission-mode default --help   -> rc=0
Usage: claude [options] [command] [prompt]
$ claude --permission-mode zzzz --help      -> rc=1
error: option '--permission-mode <mode>' argument 'zzzz' is invalid. Allowed choices are acceptEdits, auto, bypassPermissions, manual, dontAsk, plan.
$ claude --permission-mode default --version -> rc=0
2.1.296 (Claude Code)
```

### 6.3 PRD 純插入證據
```
HEAD lines = 2700  WT lines = 2903
non-equal opcode kinds: {'insert': 20}
insert blocks: 20  added lines: 203
added lines that look like KEY=value: []
git diff --numstat -- <PRD>：203	0；git diff -U0 的 '-' 行數：0
```

### 6.4 E501：判準函式 red／green（行程內餵輸入，不改任何 repo 檔）
```
ceiling = 139
actual overlong (tools/tests) = 139
current ruff.toml verdict = None
mutation A (append 到期日：2026-12-31) = "tools/ruff.toml 的 E501 存量債豁免又出現日曆到期 '到期日：2026-12-31' —— 掌舵者 2026-10-07 裁決不製造特定日期的義務；這道豁免唯一的機械物是 shrink-only 棘輪 `_E501_DEBT_CEILING`，不要把日期加回來"
mutation B (drop 退役到期日 record) = 'tools/ruff.toml 的 E501 存量債豁免不再記載「退役到期日」—— 那段記載是「為什麼沒有日期」的唯一答案，刪掉會讓下一個人把日期補回去'
HEAD ruff.toml verdict = "tools/ruff.toml 的 E501 存量債豁免又出現日曆到期 '到期日：2026-11-02' —— 掌舵者 2026-10-07 裁決不製造特定日期的義務；這道豁免唯一的機械物是 shrink-only 棘輪 `_E501_DEBT_CEILING`，不要把日期加回來"
mutation D (退役到期日：2026-10-10) = "tools/ruff.toml 的 E501 存量債豁免又出現日曆到期 '到期日：2026-10-10' —— 掌舵者 2026-10-07 裁決不製造特定日期的義務；這道豁免唯一的機械物是 shrink-only 棘輪 `_E501_DEBT_CEILING`，不要把日期加回來"
all 到期日 occurrences in current ruff.toml:
    '# 退役到期日（2026-10-10，掌舵者裁'
    '不再有續期；R74 的「到期日要真的會到期」訂正'
```

### 6.5 E501：過長行計數器變異（scratchpad 複本，已刪）
```
copy (hygiene file + 1 synthetic overlong line) count = 2
with 2 synthetic overlong files = 3
real tools/tests actual = 139 ceiling = 139
```

### 6.6 測試／lint
```
$ cd tools/tests && python -m unittest test_subprocess_encoding_hygiene   -> rc=0
.......................................
----------------------------------------------------------------------
Ran 39 tests in 15.363s

OK

$ ruff check tools/tests/test_subprocess_encoding_hygiene.py   -> rc=0
All checks passed!

$ cd tools/tests && python -m unittest test_context_budget_guard -k Prd   -> rc=0
----------------------------------------------------------------------
Ran 5 tests in 0.015s

OK

$ cd AutoClaude && python -m pytest tests/test_r100_boot_self_check.py -q -o addopts="" -p no:cacheprovider   -> rc=0
42 passed in 1.04s
```

### 6.7 收尾
```
$ git status --short   （結束前最後一次重跑；與開場快照 `diff` 無任何差異；本鏡未寫入 repo；暫存檔全在 scratchpad）
 M CLAUDE.md
 M "docs/01_requirements/AutoClaude_Token_\347\233\243\346\216\247\350\210\207\345\226\232\351\206\222\346\251\237\345\210\266_PRD_v2.1.md"
 M docs/04_planning/AutoSDD_Iteration_Prompt_Template.md
 M docs/04_planning/AutoSDD_improving_112.md
 M docs/04_planning/AutoSDD_improving_113.md
 M docs/06_quality/CrossPlatform_R145_Scan_Findings.md
 M docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md
 M tools/ruff.toml
 M tools/tests/test_adr_xplat001_c1c2_lock.py
 M tools/tests/test_subprocess_encoding_hygiene.py
?? docs/04_planning/AutoSDD_improving_114.md
```
````

## 〈三〉理論洞清單（P4；只登記、不立輪、不同輪修；再開＝各列「再開症狀」欄——本清單是範本〈🏁〉判準 3「延後」的第二種載體）

| # | 洞 | 來源 | 再開症狀 |
|---|---|---|---|
| 1 | 側軌帳本複查日 14 天 warn（`tools/lib/ledger_closing_guards.py` 的 `STALE_REVIEW_DAYS`）是純日曆催辦，與掌舵者 2026-10-07 原則相衝；建議退役為事件驅動（刪該分支與常數、「最近複查日」欄保留為資料；改碼走同標籤第二列、不開 R 輪） | ARCH-09③／QA F-03 | 下一次有人進入 `ledger_closing_guards.py`，或掌舵者對 crossref 的側軌 warn 表示噪音（附畫面） |
| 2 | 休眠宣告沒有機械載體（無測試點名〈🏁〉或 T1～T4；R197「量、不挖」刻意不立鎖） | ARCH-11 | 一個視窗（附 sid）因找不到〈🏁〉或 T1～T4 而照舊開輪 |
| 3 | PRD §16.2 現況欄與程式座標是凍結日快照；PRD 不在幽靈符號掃描面（已於 §16.2 前言揭露） | ARCH-12 | T4 事件發生時以現查為準 |
| 4 | 「休眠」撞詞：PRD 的「分片休眠／休眠喚醒」＝等 reset 的睡眠 | ARCH-15 | 一個視窗把「休眠期間」誤讀成等 reset 的睡眠（附 sid） |
| 5 | T3 的雲端事件源（GitHub 失敗通知）屬平台行為、未驗證 | ARCH-17 | 一次雲端紅而無人被通知（附 run id 與時間） |
| 6 | 該機專屬待驗清單（R211〈六〉、R210〈八〉、外部阻塞軌）無事件面喚醒；已明寫為非再開事件 | ARCH-18／QA P3-10 | 一個 Windows 視窗（附 sid）重踩清單內已登記的待驗項 |
| 7 | 同輪第二列容量有限（R211 標籤主軌餘裕現查 `repin_growth_problems`；用盡＝換新標籤＝開 R 輪） | QA P4-01／ARCH-03 | 一次重釘被該標籤 cap 夾住（附 `--print-guard-lines` 輸出） |
| 8 | DEF-200-242 帳本列「PRD §11.2 待承重標註維持」字面在 PRD 零命中（§16.4 C1 註記實質承接） | QA P4-02 | 帳本結案編修單線時順手訂正 |
| 9 | E501 反向鎖只認「到期日：YYYY-MM-DD」同形；退役記載若改寫成全形冒號＋日期會自觸發（docstring 已劃界） | QA P4-03／SD-09 | 該鎖出現一次非預期紅（附訊息） |
| 10 | DEF-200-075 軌別：主控維持外部阻塞軌，與 R210 呈報建議（改長債軌）相反；兩軌行為相同（皆 14 天 warn、皆不計未結分母） | QA P4-06 | 掌舵者另有意見時以 T1 推翻 |
| 11 | 治理檔逼近體積上限（`CrossPlatform_Guard_Line_History.md` 250457、`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md` 255168 bytes，上限 262144；活動驅動非日曆） | QA P4-07 | 下一次 append 時 crossref 轉紅 |
| 12 | ⏸ 列再開症狀所依的痕跡多住系統暫存（重開機即蒸發），觀察者需事發當場附檔 | SD-08 | — |
| 13 | ⏸ 列現況措辭不精確處（feed 另含 `exceeds_200k_tokens`／`version`、三 AND 的「間隔」缺、Retry-After 通道未界定、逾時→ESCALATION 非專屬映射、`autoclaude_*` 通配字面、桌面通知 opt-in） | SD-07 | T4 事件發生時以現查為準 |
| 14 | CLI 已驗證清單＝版本號型永動源（本機 2.1.296 vs 清單 2.1.295；每次升版即 boot loud＋略過合併 worktree 清理；設計變更屬 AutoClaude，依 PRD §16.5 (i) 由掌舵者立案） | QA P3-05／SA-13 | 一次真實的 CLI 介面變動因 boot 通知被忽略而漏接（附通知逐字與 sid），或掌舵者立案 |
| 15 | `ANTHROPIC_API_KEY` 存在時 `claude -p` 的認證優先序未查證 | SA-12 | 一次喚醒窗以非預期憑證啟動（附 sid） |

