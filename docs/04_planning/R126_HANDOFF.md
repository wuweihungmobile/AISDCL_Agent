# R126 交棒書（落地輪；技術債總清償循環令 v2 第一投）

- **輪籤**：R126（2026-09-04，Windows 11）
- **輪型**：**落地輪**——R125 已明言「重跑指令就綠」的低垂果子摘完，本輪對 R121 裁決包已選定方向、
  帳本列仍 open 的 needs-dev 項真的動手實作，動碼前過四方設計複審、動碼後過四方程式碼定點複審。
- **帳本**：未結列 **49 → 36**（淨降 13；`--unresolved-count` 實跑見下方〈已驗證〉）。
- **護欄層**：<!-- guard-total:R126 --> 行數 `91990→92306`（淨額 +316）。款(10) 上限 559 未撞；
  款(11) 本輪為連續上升第 2 輪 ⇒ 下一輪淨額必須 ≤ 0；款(12) 兌現 `(126, 555)`、重新武裝 `128／552`。
  逐檔清單＝`docs/06_quality/CrossPlatform_R126_Scan_Findings.md` §1。
- **commit／push／雲端 CI**：本檔刻意**不寫死** commit sha／push_rc／雲端結論——寫死就得再開一個
  docs-only commit，而那個 commit 又讓本行過期。現查：`git log -3 --oneline`、
  `gh run list --branch main --limit 6 --json headSha,name,status,conclusion`；本輪結案回覆已逐支列出。
- **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；所有數字皆本 session 親跑。

## 本輪方法

1. 四張需要設計裁決的卡（`DEF-200-241`／`DEF-200-137`／`DEF-200-244`／`DEF-200-243`）先寫設計卡，
   派四方（Architect／SA／SD／QA，`model: sonnet`，Workflow `wf_44dc4d34-d14`）**動碼前**複審；
   結論與被採納的條件見 `docs/06_quality/CrossPlatform_R126_Debt_Closure.md` §D——其中 D4 原設計
   「純絕對門檻」被三份實算一致否決（session 後半窗 far→mid 放寬、觸 R110 Q9(i)），改採「與絕對
   門檻取較緊」；D2 常數改進 `Policy`＋`ENV_SPEC` 受 live fail-safe 保護。
2. 其餘小項（803／257／951／217／263／248／172／247）不涉設計分歧，直接實作。
3. 全部程式碼與帳本編修由本單一窗口序列完成；並行包只做唯讀複審（鐵律七檢查表第 1 項）。
4. 實作 diff 過四方程式碼定點複審（Workflow `wf_94b54756-2fb`，一審全查＋對抗式證偽 blocking），
   結論見證據檔 §E。

## 本輪結案 13 筆（逐筆取證在證據檔同名 §）

| ID | 一句話 | 針對驗證（親跑） |
|---|---|---|
| `DEF-200-241` | 交接載體判準祖父化改讀**帳本結案事實**（判準①② 皆吃 `done_ids`），豁免表 5→0 | self-test 全過；真倉庫 rc=0；`-k Def200241` 9 passed |
| `DEF-200-213` | 卡在 241 死結的帳本治理殘留，隨治本結案（①F3/F4 觀察級、②③已滿足） | crossref rc=0 |
| `DEF-200-137` | `draining()` 補 PRD 3pp 邊際；常數進 `Policy.compact_cost_budget_pp`＋不變式 6 live fail-safe | `-k PrdDrainPercentMapsToTheBandsTest` 5 passed |
| `DEF-200-244` | PRD v2.1.14 §4.2.2-b (4c)（新增補檔）＋ `gate_excluded=` 痕跡 | `-k Def200244` 4 passed |
| `DEF-200-243` | `resolve()` 對文法解不出的軸套 `tightest`（spend 504 分 near→far、session 逐位元不變） | `test_quota_policy.py` 261 passed |
| `DEF-101-803` | floor 探針守門失守轉具名 fail | `-k ZeroDepEnvironmentDiscriminationTest` 3 passed |
| `DEF-200-257` | `SentinelWiringTest` 等待窗具名＋靜態／動態方向鎖 | `-k SentinelWiringTest` 13 passed |
| `DEF-101-951` | 根層同步鎖：4 處 compat-CI paths 複本 == `tools/lib/*skip*.py` | 3 passed, 4 subtests |
| `DEF-200-217` | E5：harness import 第三種洗白形態（`sys.path`＋裸名）判準 | `test_r82_…` 97 passed |
| `DEF-200-263` | `setup_logger` 換 `log_dir` 出聲不再靜默 | `test_logger.py` 36 passed |
| `DEF-200-248` | `AISDLC_SDD/conftest.py` 反方向 skip 報表＋版本樹 re-export | 16 passed |
| `DEF-200-172` | ③.3 根 CLAUDE.md 三軌表補列 R 系列；③.1③.2 closed-by-decision | `test_doc_loc_…` 全檔綠（見下） |
| `DEF-200-247` | 死碼 `verify_token_guard_e2e` 載具與其測試 `git rm`；登記面同步 | parity／baseline-sites／LOC rc=0 |

## 已驗證（本 session 實測；rc 皆自成一句讀取）

- 三本帳：`check_defect_log_crossref.py` rc=0（未結存量 **36** 列、192 筆有效狀態紀錄、逐列 ≤700 bytes
  ——過程中 5 列超標，依 R124 體例把長文搬進證據檔並瘦身，`DEF-200-137`／`213`／`217` 的原欄位
  逐字保全於證據檔同名 §）；`check_archive_required.py` rc=0；`check_handoff_carriers.py` rc=0
  （過程中判準① 因 241 結案而轉紅一次——commit `0398226` 的 R118 延後段落失去承接輪——同原則
  補 `done_ids` 到判準①，見證據檔 §DEF-200-241 追加段）。
- ONBOARDING：`--check` rc=0（LOC live 17246→17256）；`--check-snapshot` rc=0——表② 以全新乾淨 venv
  `autoclaude_cleanvenv_20260904`（pgextras absent）`--write --with-slow` 回填：AutoClaude
  4604 passed／175 skipped、ci-gate v0.01 1478／v0.30 1746／scripts 352（舊 cleanvenv 的 pytest 已損毀
  `No module named pytest.__main__`，故重建）。
- 針對測試逐筆見上表；ruff 對全部改動檔 `All checks passed!`（root 用 tools/ruff.toml 自動探索，
  **不帶 `--config`**——帶了會對同一批檔報 49 筆存量 E501，那是 R73 已判過的坑）。
- `check_loc_budget.py` violations=0；`context_budget_guard.py` raw-line 維持 1089（餘裕 0，兩處文字
  皆同行數改字）。
- 守衛線：`--print-guard-lines` 重釘後現查 `91990→92306 (+316)`（六支鎖檔回歸鎖 +296 ＋ 鎖檔自身重釘
  +20），逐檔漂移 0；重釘與到期義務兌現見下方〈守衛線〉節。
- 守衛線鎖檔自身 `pytest tools/tests/test_adr_xplat001_c1c2_lock.py` → `192 passed, 223 subtests passed`
  （重釘過程被自己的鎖抓到三次：鎖檔自身漂移未計入淨額、`13 筆` 裸計數、指紋鏈未接上現值——
  皆修正後才綠）。
- 全套 `python tools/run_root_unittests.py`：在帳本／文件全部定稿後最後跑一次（背景執行、親讀 log 尾端
  `rc=`），結果寫在本輪結案回覆；commit 前必須是 rc=0。AutoClaude／AISDLC_SDD 兩棵樹的全套已由
  ONBOARDING 表② 回填在乾淨 venv 實跑（見上），之後只動根層 tools 與文件。

## 守衛線（款(10)(11)(12)）

- 本輪淨額 +316 < 上限 559（款(10)）。款(11)：R123 +322 為連續上升第 1 輪、R124／R125 淨額 0 未記列，
  本輪為**第 2 輪** ⇒ **下一個結案窗口（mac）淨額必須 ≤ 0**（合法出口＝史料搬遷抵銷／刪行／合併鎖檔，
  先例 R122 Guard Prose Migration）。款(12)：到期輪 124／目標 555 已到期，本輪兌現 `(126, 555)` 並
  重新武裝 `128／552`（步伐 3 < 前段 4）。分桶棘輪：prose 桶一度 +41（新測試類別的參照面只有
  docs/ ⇒ 被歸 exclusive prose），改為指名受測模組路徑後回到基準以下（實測值見證據檔）。

## 還沒做（不塗綠；每筆帶現查指令）

1. **`DEF-200-242`（free 帶時窗限定 cap）**：R121 方向 A 要求先出 `quota_burn.jsonl` 翻頁後第一拍扇出量測
   再動碼；本輪只做了不需量測的四筆配速項，探針尚未量測、程式尚未動。現查
   `git grep -n "reset 翻頁後第一拍" -- tools`（有命中＝探針已寫）。
   <!-- absent-if: def first_tick_after_reset -->
2. **R121 呈報單檔頭狀態仍未改為 `Adopted`**（`docs/04_planning/AutoSDD_Adjudication_Packet_R121.md:3` 仍是
   `Proposed`），但其推薦已被掌舵者 2026-09-02 採用並逐筆結案（R121 8 筆＋本輪 13 筆皆引用它）——屬呈報單項，
   見下方〈呈報單〉①。現查 `Select-String -Path docs/04_planning/AutoSDD_Adjudication_Packet_R121.md -Pattern "Status"`。
3. **剩餘 36 筆未結列還沒動工**（現查 `python tools/check_defect_log_crossref.py --unresolved-count`），分類：
   - 需掌舵者拍板（呈報單②～⑦）：`DEF-200-259`／`DEF-200-182`／`DEF-200-256`／`DEF-200-255`／
     `DEF-101-736`／`DEF-101-856`。
   - mac 真機或雙平台：`DEF-200-252`／`DEF-101-675`／`DEF-200-231`（mac 側 User 層值）／`DEF-200-165`。
   - 落地輪候選（裁決已在、只差實作）：`DEF-200-124`（M）、`DEF-200-118`（M）、`DEF-101-938`（M）、
     `DEF-200-206`（M）、`DEF-200-242`（M，先量測）、`DEF-200-253`（S）、`DEF-200-133`（S~M）、
     `DEF-200-260`（M，逐站盤點）。
   - 結構性／多子項：`DEF-200-207`（U1~U4 四方審查）、`DEF-200-197`／`198`／`199`／`203`／`193`
     （配速修憲 Adopted 待落地批）、`DEF-101-887`／`796`／`974`／`981`／`DEF-200-086`／`129`／`134`／
     `183`／`188`／`246`／`251`／`234`。
4. **側軌現況**（不計入分母；帳本會對複查日 >14 天出聲）：外部阻塞軌 6 筆（`DEF-101-518`／`693`／`703`／
   `DEF-200-075`／`174`／`186`）、結構性長債軌 7 筆（`DEF-101-018`／`398`／`701`／`702`／`886`／`960`／
   `980`）。本輪尚未複查兩側軌（落地輪射程外）；現查 `python tools/check_defect_log_crossref.py`
   輸出首兩行。

## 呈報單（需掌舵者拍板的新裁決件，附現查依據）

1. **R121 呈報單檔頭 `Status: Proposed` → 建議改 `Adopted`**：其 10 筆 closed-by-decision 中 8 筆已於 R121
   結案（`CrossPlatform_R121_Debt_Closure.md`）、本輪再依其方向落地 5 筆 needs-dev；帳本字面與檔頭狀態
   對不上正是循環令 v2 點名的「closed-by-decision 宣告與原始檔案不符」形態。
2. **`DEF-200-259`（歷史列漂移座標）三選一**：(a) 明文豁免 append-only 就地訂正；(b) 做 R96 原建議的
   「行號解析不到即警告」advisory 掃描器；(c) wontfix（歷史記錄本就允許過期座標）。R125 分診已判
   needs-decision。
3. **`DEF-200-182` ①**：驗證清單「須涵蓋哪幾套閘門」判準的 SSOT 家歸屬（建議收進
   `check_handoff_carriers.py`），核准後派工；② 已由 R121 裁 closed-by-decision（取證載體不存在）。
4. **`DEF-200-256`**：`hub-push.yml` 兩處 quotepath 是否比照凍結版例外（Copy-on-Evolve 政策擁有者）。
5. **`DEF-200-255`**：perf p95 門檻 50ms 壓在量測中位（實測 51.7ms），重訂或明文 opt-in 終態。
6. **`DEF-101-736`**：子項 560 wontfix 是否正式落款；649 待 macOS；880 待以新尺重算。
7. **`DEF-101-856` ⑥**：pgvector recall 3 支——本機 Docker（pgvector pg18、alembic head）算不算「staging」
   等價替代；不算則依 R121 裁決遷外部阻塞軌。

## 證據位置

- 落地取證＋四方兩審結論：`docs/06_quality/CrossPlatform_R126_Debt_Closure.md`（已登記 `governance_docs.py`）。
- 設計卡與兩次複審 journal（本機 session 暫存，不隨 repo 走）：
  `C:\Users\wuwei\AppData\Local\Temp\claude\d--CursorProject-AISDCL-Agent\6580b890-791d-4431-af7e-0766749819c5\scratchpad\R126_design_cards.md`、
  同目錄 `design_review.txt`、`r126_code.diff`；Workflow journal 住
  `%USERPROFILE%\.claude\projects\d--CursorProject-AISDCL-Agent\6580b890-791d-4431-af7e-0766749819c5\subagents\workflows\wf_44dc4d34-d14\`
  與 `…\wf_94b54756-2fb\`。
- 乾淨 venv：`C:\Users\wuwei\AppData\Local\Temp\autoclaude_cleanvenv_20260904`（下次回填表② 用它；
  舊的 `_20260827` 已壞）。

## 下一步（下一個窗口＝mac）

- 🔴 **守衛線款(11)：下一輪淨額必須 ≤ 0**——先做搬遷抵銷（候選：`test_context_budget_guard.py` 9902 行、
  `test_quota_policy.py` 3402 行內的沿革散文，依 R122 `Guard Prose Migration` 體例逐字搬進
  `docs/06_quality/`）再加任何回歸鎖。
- mac 專屬列（`DEF-200-252`／`DEF-101-675`／`DEF-200-231` mac 側）在 mac 真機結案；Windows 實測值不外推。
- 落地輪候選見〈還沒做〉③；每筆動碼前先重跑帳本原文比對現況（本輪 13 筆裡 3 筆的帳本描述已與現況
  有落差，證據檔逐筆訂正）。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、push 不帶 `AUTOSDD_NET_RATCHET_OFF`。
- 不准把〈還沒做〉③ 的 36 筆順手改成已結——皆逐筆核實仍需動工、裁決或 mac 真機。
- 不准同時派多個 agent 平行編修帳本或同一鎖持有面（鐵律七檢查表）。
- 全套 `tools/run_root_unittests.py` 一律親讀 log 尾端 `rc=`；push 一律背景執行並讀 `push_rc=`；
  逾時（rc=143）先 `git fetch` ＋ `git log origin/main..HEAD` 判斷是否已送達。
- ONBOARDING 表② 回填一律乾淨 venv，禁 `--allow-pg-extras`。
