# CrossPlatform R209 技術債結案輪證據檔（28 筆未結列的唯讀分診 → Architect 裁決 → 結案／修復）

- **輪籤**：R209（2026-10-09，macOS；主控 Fable 5.1 兼 Architect；SA 分診 4 包、Developer 3 包、QA 複審皆 Sonnet）
- **輪型**：結案輪（`docs/04_planning/TechDebt_Paydown_Cycle_Prompt.md` §2）。掌舵者本輪原話：「請徹底將這個任務，是否可以在三輪內完成？若無法達成，原因為何？請想盡所有辦法完成收斂任務」。
- **起點**：`python tools/check_defect_log_crossref.py --unresolved-count` ＝ **28**（本場開場實跑；外部阻塞軌 3、結構性長債軌 7）。
- **終點**：`--unresolved-count` ＝ **2**（DEF-200-207、DEF-101-887；本場實跑，見〈四〉）。外部阻塞軌 3→5、結構性長債軌 7 不變。
- **體例**：不使用前瞻輪號的「延後／交給」句型；本檔每個數字皆本場親跑或分診報告逐字（分診報告的數字標〔SA〕，主控重跑過的標〔親跑〕）。帳本列內「詳 CrossPlatform_R209_Debt_Closure_Evidence.md」即指本檔。

---

## 〇、一句話結論

28 筆未結列經四包唯讀分診、逐筆 Architect 裁決、QA 零信任複審一輪 REJECT→修→複審：**20 筆** closed-by-decision（含 2 筆移入外部阻塞軌、每筆帶可觀測的重開條件）、**6 筆** fixed（2 筆現況已修、4 筆本輪修復：CI yml ×3、帳本閘門接線 ×1）、**2 筆**留 open——DEF-200-207 刻意留作本輪的交接載體（也是 ADR-XPLAT-013 狀態翻轉與「時鐘凍結」兩件結構性工作的帳本錨），DEF-101-887 主控原改判 closed-by-decision 被 QA 以活載體自述證偽（nightly G0 收尾仍每晚消費三軌樣本），改留 open 並附修法設計（見〈五〉）。未結 28→**2**。

---

## 一、分診與裁決總表（28 筆；判決欄＝Architect 終裁，與分診包建議不同者加註）

| ID | 包 | 嚴重度 | 裁決 | 一句話理由 | 驗證（親跑者標〔親跑〕，其餘〔SA〕） |
|---|---|---|---|---|---|
| DEF-101-675 | A | P3 | **修復**（包 1） | macos-compat-ci 的 zsh source step 仍是「斷言在 zsh -c 引號內」的失明形狀；改行程外側證物檔 | 本機模擬：舊形狀＋壞 dev_start rc=0、新形狀 rc=1〔SA／Developer 各一次〕；結構鎖 TestMacZshSourceStepAssertsOutOfProcess 對改前 yml 紅〔Developer〕 |
| DEF-200-361 | A | P2 | **修復**（包 1） | 四個 CI linked-worktree 拒絕 step 只比 rc=1、零標記斷言 | yml 補輸出捕捉＋標記雙斷言；同步鎖 TestCiWorktreeRejectStepsAssertMarker 對改前 yml 紅〔Developer〕；雲端驗收見〈四〉 |
| DEF-200-381 | A | P3 | **修復**（包 2；裁「納入」） | chaos-latest 排程 run 2026-09-26～10-08 連 13 次 success（job 層直驗 5 次）〔SA〕；觀察期已滿 | GATING_JOB_NAMES 改多名＋streak needs＋同步鎖翻轉；真 jq 行為鎖 9 變異皆紅、真 gh＋bash 端到端 S1 streak=4／S3 streak=2〔Developer〕 |
| DEF-200-403 | A | P3 | closed-by-decision | mac `.sh` 無 chaos stage 是 ONBOARDING §8「薄聚合」的刻意設計；承載者（雲端 chaos-nightly 15/15、Windows 本機兩 stage）活著 | `grep -n "STAGE_TOTAL=\|^run_stage" AutoClaude/tools/run_local_nightly.sh`〔SA〕 |
| DEF-200-252 | A | P2 | **fixed**（現況） | mac 真機實跑 census 內全部 [MAC-NATIVE-ONLY] 測試 37 支全 passed、標籤 0 skip（六腿合計 52 passed／1 skipped） | 附錄 A 腳本六腿各 rc=0、script_rc=0〔親跑；QA 重跑逐腿相同〕 |
| DEF-200-395 | A | P3 | closed-by-decision | 分流修法兩項已於 a7ec2772 落地；只有 Windows 能重現，重開條件由症狀驅動 | `test_install_windows_nightly.py` 45 passed, 5 skipped rc=0〔親跑〕 |
| DEF-200-311 | A | P2 | closed-by-decision | 09-26 20/20＋本輪 5/5 綠；模組自 09-12 無異動；斷言為資料完整性（僅子行程 wait(timeout=120) 一處時間界）；未重現≠已修，重開＝再現且逐字輸出落檔 | `-k concurrent_writers -p no:xdist` 1 passed rc=0〔親跑 1 次；SA 5 次〕 |
| DEF-200-165 | B | P3 | closed-by-decision | 傳染面已有全庫 CR 零容忍鎖；剩餘是陳舊 Windows 工作樹的機器歷史，無症狀暴露 | `git ls-files --eol '*.toml' '*.json'`：170 支、w/crlf 0〔親跑〕；tree_fingerprint 先正規化行尾（`sync_onboarding_baselines.py` 的 `_normalize_eol`）〔親跑 grep〕 |
| DEF-101-974 | B | P2 | closed-by-decision | POSIX runtime 面已補位；函式體 skipTest 33 筆中方向可判 9、Windows 方向缺標 0（對稱方向 1 筆見〈三〉2） | SA 的 session 內 AST 探針 rc=0〔SA 探針；QA 重跑同數〕 |
| DEF-200-253 | B | P2 | **移外部阻塞軌**（Windows 實機） | win32+nopg+nested 剖面只在 Windows 機、Docker 停、巢狀 CC 內量得到 | 解鎖條件見 AutoSDD_External_Blocked_Log.md 該列 |
| DEF-200-418 | B | P4 | closed-by-decision | 第一步已做；餘為 P4 理論洞（R197 量、不挖） | 掃描面 glob 23＋具名 11＝34 支〔親跑 ls=23〕 |
| DEF-200-124 | B | P2 | closed-by-decision（SA 推薦 B，採） | R89 症狀已由 exclusive 估計量＋一次性例外程序吸收；修法會逼 prose 重釘且無暴露證據 | `guard_layer_bucket_census.py --grain chunk` rc=0〔親跑〕 |
| DEF-101-887 | B | P1 | **留 open**（SA 判 fix-small；主控原改判 closed-by-decision **被 QA 證偽後撤回**） | 主控原依據「SD_09 觀察期已結束、現無閘門消費樣本」無 repo 證據且與活載體自述相反：`run_local_nightly.ps1` G0 收尾區塊自述「唯一活載體」、每晚呼叫 ac4_progress_check／observability_ga_check／drift_log_ga_check 並寫 .g0_readiness.json；autoclaude-ci.yml 仍跑 ac4_progress_check。成立的只有「起跑 SAMPLE VALIDITY 行逐輪記錄」這一道緩解。修法設計見〈五〉 | `grep -n porcelain AutoClaude/tools/run_local_nightly.ps1`〔親跑〕；G0 活載體引文〔QA 重讀〕 |
| DEF-101-736 | C | P2 | closed-by-decision | 729 退場的跨樹保障已有等價替代；557 已 fixed、649 無症狀、880 逐字稿不在 repo | 兩支對拍鎖 54 tests OK (skipped=3) rc=0〔親跑〕 |
| DEF-200-182 | C | P1 | closed-by-decision | ②已結；①是散文完整性缺口、無機械物可判、無第二例；pre-push 依路徑自動路由 | `test_root_infra_parity` 13 tests OK〔SA；僅佐證〕 |
| DEF-200-188 | C | P1 | closed-by-decision | 承接閘門已在線；B8 規格本體不存在於任何 tracked 檔，無定義即無從鎖 | `check_handoff_carriers.py` rc=0＋`--self-test` rc=0〔親跑〕 |
| DEF-200-134 | C | P1 | closed-by-decision（**有意推翻 R100 的「不可結案」**） | 輸入面（並行包回報住系統暫存）結構上不在 repo；「倒進去之後」已有閘門（check_handoff_carriers 判準①②＋交棒書體例鎖），「倒進去」僅流程約束（鐵律七檢查表第 1 條：並行包禁寫帳本）；立案後無人回報第二例；R207 症狀驅動 | 同上〔親跑〕 |
| DEF-200-207 | C | P1 | **留 open**（本輪交接載體） | ADR-XPLAT-013 翻 Accepted 須處理 U1～U4 四方複審＋U7／U9 長債化＋到期輪常數；屬收尾單人窗口的結構工作，見〈五〉 | `check_loc_budget.py --json` 的 cap_basis_pinned=True〔SA〕 |
| DEF-101-938 | C | P3 | closed-by-decision | 本機未接 pre-push 屬有意；唯一執行者＝雲端 shellcheck-ci（近 6 次 push 皆 success） | `tools/run_shellcheck.py` rc=0「與基線一致」〔親跑〕 |
| DEF-200-265 | C | P3 | **fixed**（實質由 DEF-200-305 落地） | seed_kb 預設不寫 fixture；09-15 起該檔零更動 | `test_seed_kb.py` 6 passed rc=0〔親跑〕；`git log --since=2026-09-15 -- <fixture>` 0 行〔親跑〕 |
| DEF-200-118 | D | P1 | closed-by-decision（**反轉 R121 方向 A、採其方向 B**） | 帳號無 usage credits ⇒ 靜默計費的對象不存在；守衛面新增碼無暴露證據不准入；PRD 處方保留在紀錄、未修憲 | `~/autosdd_quota.json` posture.credits_present=false〔SA 讀檔〕；本場 `--pace` 印 `kind=spend 0% … note=missing`、`gate_excluded=spend`〔親跑〕 |
| DEF-200-234 | D | P3 | closed-by-decision | 偵測面已落地；處置面無暴露證據（R111 同池同死、未實燒） | `grep -n cap_prepare tools/lib/quota_escalation.py` rc=1〔SA〕 |
| DEF-200-458 | D | P3 | closed-by-decision | 症狀端 198 已 fixed、W5 已落；W4／W6 是功能願望、bursting_ok 無生產呼叫端 | `grep -rn "bursting_ok("` 只命中定義與測試〔SA〕 |
| DEF-200-251 | D | P2 | closed-by-decision（SA 建議立 ADR，**改為不立**） | 重構願望、無症狀、跨檔參照稅高（git grep -l 排除 docs／*.md 引用檔 24）；三支目標形態各約 1045 行會超過 guardrail_lib 預算 400 與絕對上限 750（check_loc_budget.py 常數）⇒ 須先重設計；重開條件可機械查；不開新文件、不入長債軌（長債軌成長棘輪須掌舵者具名裁決） | `wc -l tools/lib/skip_*.py` 合計 3136〔SA；QA 重跑同數〕 |
| DEF-101-981 | D | P2 | closed-by-decision（同上） | hook_wiring.py 三塊混居是設計味道、查無缺陷；引用檔多（git grep -l 排除 docs／*.md 共 25，含 2 支 hook、4 支 AISDLC_SDD 檔）參照稅高 | `git grep -l hook_wiring`〔QA 重跑〕 |
| DEF-101-796 | D | P1 | closed-by-decision | 原 0/6 出自有兩處缺陷的舊探針；繼任量測 TestXplatInjectionMatrix 在庫；未攔 4 類＝構造性理論洞 | `TestXplatInjectionMatrix` OK，Win2mac=8/12 mac2Win=5/10〔親跑〕 |
| DEF-101-856 | D | P2 | **移外部阻塞軌**（Windows 實機） | 3 支測試仍是 [DEBT] skip 空殼；staging 僅 Windows 11 備得出；解鎖探針已機械化 | 解鎖條件見 AutoSDD_External_Blocked_Log.md 該列 |
| DEF-200-129 | B | P2 | **修復**（包 3） | 自列「改派」出口的輪號下限接線（接線後真帳本恰紅 938／974 兩列，兩列本輪結案） | `check_defect_log_crossref.py` 不帶參數 rc=0〔親跑〕；回歸鎖 TestDef200129SelfRowExitNamesAFreshRound 先紅再綠〔Developer〕 |

**三個被推翻的歷史裁決**（Architect 依掌舵者 2026-08-29「裁決題以最佳理想化代決」規則作成，掌舵者可否決）：
1. DEF-200-134（R100 判「不可結案」）→ 結案：R207 之後只由症狀驅動，立案後無人回報第二例（此類事件依定義不留 repo 痕跡，只能說無人回報）。
2. DEF-200-118（R121 裁方向 A「落地差量告警」）→ 採同一份呈報單的方向 B：帳號根本沒有 credits，告警的對象不存在；重開條件寫明。
3. DEF-200-251／981（R121 駁回「動機消失」型 wontfix）→ 以「無症狀＋參照稅＋目標形態與 LOC 分級衝突須先重設計」為論據結案，重開條件可機械查。

---

## 二、改了什麼（逐檔；`git diff --stat`：13 支既有檔＋1 支新證據檔，淨額見〈六〉）

- `docs/06_quality/AutoSDD_Defect_Log.md`：27 列依 R124 瘦身體例改寫——「現象與證據」欄改一句話＋本檔附錄 B 指針、「分流去向」欄縮短、狀態欄改寫（20 列 closed-by-decision 含 2 列側軌索引、6 列 fixed、1 列 DEF-101-887 留 open 改述）；整列 ≤700 bytes（套用腳本逐筆量測，最大 697）；28 列改寫前原文逐字保全於附錄 B（含未改寫的 DEF-200-207）。
- `docs/06_quality/AutoSDD_External_Blocked_Log.md`：+2 列（DEF-200-253、DEF-101-856；具名阻塞源＝Windows 實機；解鎖條件可機械查；複查日 2026-10-09）。
- `tools/lib/governance_docs.py`：登記本檔。
- 包 1（DEF-101-675＋DEF-200-361）：`.github/workflows/macos-compat-ci.yml` +38／−3、`.github/workflows/windows-compat-ci.yml` +31／−3（五個 step 的 `name:` 逐字不變）、`tools/tests/test_smoke_ci_sync.py` +78（新類別 TestMacZshSourceStepAssertsOutOfProcess 與 TestCiWorktreeRejectStepsAssertMarker；對改前 yml 紅、helper 紅綠自證）。改前雲端 log（macos run 37816340302、windows run 37816340254）顯示四個 worktree step 其實已印標記、zsh step 的斷言區有被執行 ⇒ 兩筆都是「潛在」失明／空洞，非已發生。
- 包 2（DEF-200-381）：`.github/workflows/aisdlc-sdd-fsm-chaos-nightly.yml` 改 GATING_JOB_NAMES 為 `|` 分隔的兩個顯示名（顯示名逐字不改）、streak 以任一 gating job failure／timed_out 計 +1、`needs: [chaos, chaos-latest]`、三段觀察期註解改現況（無日期、無到期字樣）；`tools/tests/test_workflow_permission_concurrency_lock.py` 淨 +65（(b) 集合比對、(c)(d) 翻轉、單名形態禁令、真 jq 行為鎖：7 組合成 jobs JSON、9 個變異體逐一轉紅；本機真 gh＋真 bash 端到端 S1 streak=4、S3 只有 chaos-latest 紅 streak=2）。
- 包 3（DEF-200-129）：`tools/check_defect_log_crossref.py` 淨 0 行（+10／−10；自列「改派」出口加輪號下限、刪「暫未接線」句、成功訊息改措辭）；`tools/tests/test_check_defect_log_crossref.py` 淨 −26（舊債釘類改寫為 TestDef200129SelfRowExitNamesAFreshRound 31 行：陳舊自列轉紅／邊界放行／未指派放行／跨列路徑不變，先紅再綠＋5 組變異；刪一支以陳舊自列出口為母體的真帳本測試；對照組測試改合成帳本，見〈四〉）。接線後真帳本恰紅 DEF-101-938／974（兩列本輪結案後 rc=0）。
- 護欄層重釘：見〈六〉。

## 三、不改什麼＋理論洞清單（P4；只登記不修——R197〈守衛面准入〉：沒有暴露證據不立輪、不同輪修）

- 守衛面（`.claude/hooks/**`、`.claude/settings*.json`、指定七支 `tools/lib`、`session_resume_planner.py`）零改動；五問協定、輪帳本零改動；根 CLAUDE.md 零改動。
- 不新增任何 ADR／RFC／HANDOFF；本檔是本輪唯一的新文件（掌舵者本輪要求「省去非必要文件」）。
- 不動 `current_round()` 的取值方式；不動結構性長債軌（成長棘輪須掌舵者具名裁決）。
- **理論洞清單**（每條附「何時會變成症狀」）：
  1. `check_defect_log_crossref.current_round()` 由帳本「發現情境」欄最大 R 數推得，而該欄自 R100 起刻意零輪號 ⇒ 當前輪停在 R100（真實 R209）。後果 ⇒ 硬規則② 與 DEF-200-129 接線後的輪號下限對 R100～R209 失明；`check_handoff_carriers.py` 判準① 的 `N ≥ cur` 也以 100 為界。症狀＝全部未結列結案時（carriers 清空）判準① 對 4 個舊 commit（`2a74853d`／`5c724baa` R109、`772e28bd`／`f5607fae` R100）轉紅（包 C 以該檔純函式對 737 則 commit 模擬〔SA〕）。本輪刻意留 DEF-200-207（承接 117）當載體，所以不紅；最後一列結案的那個 commit 必須同時處理此洞（出口見〈五〉）。
  2. `tools/tests/test_context_budget_guard.py` 約 :4406 的函式體 skipTest（條件 `sys.platform != "darwin"`）缺 NON_WINDOWS 標籤，且 `untagged_non_windows_skip_decorators` 對函式體同樣失明（DEF-101-974 的對稱缺口，1 筆）。症狀＝該站點在 Windows 被 skip 而剖面計數對不上。
  3. DEF-101-796 的四類未攔（反斜線拼接／.exe 後綴／cp950／大小寫不敏感比對）；舊探針 `tools/probe/xplat_injection_matrix.py` 仍會印誤導的 0/6（加作廢橫幅或刪檔屬淨減法、收尾單人窗口）。症狀＝mac/Linux 專屬失敗逃逸到雲端 CI。
  4. DEF-200-418 的 hook 載具傳遞 import 圖未枚舉（`.claude/hooks/*.py` 既存 import 邊）。症狀＝Windows 真機閃窗回報。
  5. DEF-200-165 的 Windows 陳舊工作樹 frozen／active 分帳實數未量。症狀＝位元組比對類閘門兩平台結果不同。
  6. ADR-XPLAT-013 §7 的 U8／U10 文字落後現況（E2／E5 已 fixed、cap_basis_pinned=True）；U9 到期輪 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 連續具名展延至 213，仍是輪號型義務。載體＝DEF-200-207。
  7. `AutoClaude/tools/run_local_nightly.ps1` 的 chaos-latest stage 註解仍寫「觀察期」（DEF-200-381 納入後過時；純文字）。
  8. 側軌帳本的「最近複查日 >14 天」提醒（warn-only）與 R207「不製造日曆義務」有張力：本場 crossref 對外部軌 3 列、長債軌 7 列各印一則 warn。本輪未複查那 10 列（不在結案輪範圍）。

## 四、驗證（本場親跑；rc 與關鍵輸出行逐字；沒跑的標「未驗證」）

| 閘門 | 指令 | 結果（逐字） |
|---|---|---|
| 帳本全套 | `python tools/check_defect_log_crossref.py` | rc=0；「✅ 缺陷帳本跨文件狀態一致：帳本 207 筆有效狀態紀錄、19 份掃描目標皆無矛盾」 |
| 未結存量 | `python tools/check_defect_log_crossref.py --unresolved-count` | rc=0；「未結列數＝2／全部 207 列｜warn=86 fail=98」「未結列 ID：DEF-101-887、DEF-200-207」；外部阻塞軌 5 筆、結構性長債軌 7 筆 |
| 交接載體 | `python tools/check_handoff_carriers.py` | rc=0；「[census] 當前輪＝R100（帳本「發現情境」欄現查；未結承接輪號＝[117]）」「✅ 每一筆前瞻延後宣稱都有帳本承接載體」；`--self-test` rc=0 |
| 封存門檻 | `python tools/check_archive_required.py` | rc=0；「✅ 未觸發歸檔強制門檻」 |
| 護欄棘輪 | `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` | rc=0；「# 淨額 114790→114790 (+0)」「# 逐檔漂移 0 支」 |
| 棘輪鎖檔 | `pytest test_adr_xplat001_c1c2_lock.py -p no:xdist` | rc=0；「192 passed, 436 subtests passed」 |
| 帳本鎖檔 | `pytest test_check_defect_log_crossref.py test_archive_defect_log.py -p no:xdist` | rc=0；「459 passed, 461 subtests passed」 |
| ruff | `ruff check` 改到的六支 .py（含 test_adr_xplat001_c1c2_lock.py） | rc=0；「All checks passed!」 |
| 根層全套 | `python tools/run_root_unittests.py` | ROOT_RC=0（QA 複審修正前的樹跑兩次皆綠；其後只改帳本／本檔文字與 jq 分支 3 行，鎖檔、帳本鎖檔、文件鎖重跑綠，pre-push 再跑全套）；「✅ unittest 數量下限釘選通過：發現 5207 個測試（下限 5101）」；skip census tools/tests@darwin 47 支、欠債型 0；M6 id 集合 ✅；真實 TEMP 圍籬 ✅（autosdd_pace*.json 零變動） |
| 幽靈符號鎖 | `pytest test_doc_loc_baseline_freshness_r60.py -k GhostSymbol` | rc=0；「12 passed」 |
| DEF-200-252 親跑 | 附錄 A 腳本 | script_rc=0；六腿 rc=0（輸出見附錄 A） |
| 其餘結案列親跑 | 265／311／395／736／796／938／188／124／418／165 的 verify（見〈一〉） | 皆 rc=0（265：6 passed；311：1 passed；395：45 passed, 5 skipped；736：OK (skipped=3)；796：Win2mac=8/12 mac2Win=5/10；938：與基線一致；188：rc=0＋self-test rc=0；124：census rc=0、prose 4261；418：glob 23；165：170 支 w/crlf 0） |
| QA 零信任複審 | Sonnet 鏡（一審 REJECT：P2 ×1＝887 改判前提不實；P3 ×6＝側軌列位置、252 算術、134 措辭、311 時間界、〈五〉標題、待填與 pwsh 敘述；P4 ×7）→ 主控全數採納修正（887 改留 open；jq 缺席改真 ubuntu runner 上 fail-loud）→ 複審 CONDITIONAL（P2 已消除；餘 P3 ×4＝本檔與帳本文字未同步、P4 ×4 含 act 映像缺 jq）→ 主控逐條修正（本表數字與帳本同步、jq 分支排除 ACT、251／981 統一 git grep 口徑） | 一審 REJECT → 複審 CONDITIONAL → 修正後主控自核；QA 報告住 session scratchpad |
| pre-push 全 leg | `git push`（背景） | 〔待填〕 |
| 雲端 CI | `gh run list --commit <sha>` | 〔待填：逐支 conclusion〕 |

未驗證（只能在該環境驗）：三支 workflow 改動的雲端實跑（本輪 push 後的 run 寫在上表）；Windows yml 的 run 本體在 PowerShell 5.1／windows-latest 的實跑（QA 鏡已在本機 pwsh 7 以 GitHub `shell: pwsh` 包裝對跑新舊版本體與真安裝腳本，新版正確；主控未親跑）；Windows 機表② 欄回填（該機才量得到）；DEF-200-381 的 streak job 只在真失敗時才跑，雲端綠燈驗不到計數邏輯（憑證＝本機真 jq 行為鎖與真 gh＋bash 端到端）。

## 五、收尾單人窗口清單（事實驅動、非日曆義務；輪號屆時現查）

1. **DEF-200-207 ＋ 時鐘**（收尾單人窗口，同一個 commit）：(a) `current_round()` 改以「R 系列證據檔／交棒書的最大號」為來源（`docs/06_quality/CrossPlatform_R<N>_*.md` ∪ `docs/04_planning/R<N>_HANDOFF.md`，數字排序），並同步 `check_handoff_carriers.py` 判準① 的消費面與 `tools/tests/test_check_defect_log_crossref.py` 的合成帳本預期；(b) ADR-XPLAT-013 翻 Accepted：U1～U4 以 R110／R116 既有四方紀錄追認或補一次唯讀四方；U8／U10 改已達成；U7／U9 改症狀驅動（退役 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 的輪號展延）；(c) 結 DEF-200-207 與 DEF-101-887（第 4 項）⇒ `--unresolved-count` 歸 0；(d) 依 TechDebt 循環令 §7 輸出總結帳（起點 49@R125 → 0）並逐筆列側軌 10 列現況與複查日。
2. **Windows 機該做的**（只在 Windows）：`git pull` → `gh auth status` → 跑 `tools/lib/clean_venv_carrier.py` 回填表② Windows 欄 → `sync_onboarding_baselines.py --check-snapshot` 看到「相符」→ 一併 commit；順手複查外部阻塞軌 DEF-200-253／DEF-101-856／DEF-200-313／DEF-101-693 四列是否仍成立（能解鎖的就解鎖）。
3. **雲端驗收**：包 1／包 2 改的三支 workflow 只能 push 後看；本輪 push 後的 run id 記在〈四〉。
4. **DEF-101-887 修法**（平台中性程式碼，但首筆真樣本只會由 Windows nightly 產出，故排在 Windows 機上做）：新增 `AutoClaude/tools/tree_state.py`（git rev-parse HEAD＋`git status --porcelain` 是否非空；取不到回 unknown、不 fail；subprocess 帶 encoding 與 Windows 無視窗旗標，約 20 行）；`observability_snapshot.py`／`drift_log_snapshot.py`／`ac4_nightly_collector.py` 的 record 各加 `tree` 欄位（起跑時抓一次經由 env 傳給 collector，寫入時再抓一次、不等即標 invalid）；`ga_window.evaluate` 與 `ac4_progress_check.filter_recent` 在算 streak／window 前剔除 `tree.dirty` 的紀錄並回報 `excluded_dirty` 計數（缺欄位視為有效、不追溯作廢；全 dirty ⇒ 證據不足不過）；測試約 70 行（AutoClaude/tests 為指紋樹 ⇒ 表② 回填是 commit 前最後一步；AutoClaude 舊債檔碰到即整檔 ruff 須乾淨）。驗收＝該機下一次 nightly 後 `AutoClaude/.ac4_history.jsonl` 末筆含 `tree` 欄位且 G0 收尾區塊印出 excluded_dirty。

## 六、護欄層重釘（`test_adr_xplat001_c1c2_lock.py`）

- 軌別與淨額：歸回歸鎖軌（四筆真缺陷的結案回歸鎖）。主表淨額 114659→114790（+131）＝M；回歸鎖軌申報 131 ≤ 軌上限 309；主軌 0 ≤ 0（款(11) 連升維持歸零）。`--print-guard-lines` 末態印「淨額 114790→114790 (+0)」「逐檔漂移 0 支」。
- M 的構成（逐檔）：`test_smoke_ci_sync.py` +78（兩個新類別）；`test_workflow_permission_concurrency_lock.py` +65（含 QA 複審後把 ubuntu CI 缺 jq 改為 fail）；`test_check_defect_log_crossref.py` −26（舊債釘類改寫、刪無牙 live 對照、對照組改合成帳本）；本檔自身 +14（重釘列、回歸鎖軌同輪列、接鏈列）。
- 到期義務：本輪無——`_REPIN_NET_CAP_DUE_ROUND` 210、U9 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 213、`_PHASE2_REVIEW_LOG` 到期 213 皆未到，三者皆不動。
- 凍結前綴：`_REPIN_LOG_FROZEN_PREFIX_LEN` 328→329、`_REPIN_LOG_HISTORY_SHA256` 重釘為 715cab76…、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加接鏈列（1e22b76a4c99 → 715cab768f05，DEF-200-129）。
- 兩份常設檔的 `<!-- guard-total:R209 -->` 行：`docs/04_planning/AutoSDD_improving_112.md`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`（檔尾各一行）。
- 其餘表：`tools/lib/skip_tag_policy.py` 的樹檔數下限不變（本輪無新測試檔）；E501 存量債上限不變（新增行 EAW 實量零超線，見〈四〉ruff）。

## 附錄 A：DEF-200-252 的 mac 真機驗證腳本與輸出（唯讀；每腿獨立行程、rc 直讀）

```bash
#!/bin/bash
# DEF-200-252 verify: run ONLY the [MAC-NATIVE-ONLY] tests on a macOS host.
R=/Users/wuweihong/Antigravity/AISDCL_Agent
PY=$R/.venv/bin/python
OUT=${1:-/tmp}
export AUTOSDD_SENTINEL_OFF=1 PYTHONUTF8=1
unset VIRTUAL_ENV
[ "$(uname)" = "Darwin" ] || { echo "NOT Darwin - evidence invalid"; exit 2; }
leg() {
  label=$1; cwd=$2; shift 2
  ( cd "$cwd" && "$PY" -m pytest "$@" -q -rs -p no:cacheprovider > "$OUT/A_252_verify_$label.txt" 2>&1 )
  rc=$?
  echo "leg=$label rc=$rc :: $(tail -n 1 "$OUT/A_252_verify_$label.txt")"
}
T=$R/tools/tests
leg zsh_carrier   $T test_dev_start_ps1_lastexitcode.py::TestDevStartShShellCarrier::test_zsh_sourced_happy_path test_dev_start_ps1_lastexitcode.py::TestDevStartShShellCarrier::test_zsh_core_failure_propagates_and_does_not_activate test_dev_start_ps1_lastexitcode.py::TestDevStartShShellCarrier::test_zsh_executed_not_sourced -p no:xdist
leg launchd_real  $T test_context_budget_guard.py::Inv5SingleOwnerTest::test_real_launchd_listing_feeds_other_owner_for_session -p no:xdist
leg zsh_cli       $T test_smoke_ci_sync.py::TestMacSmokeCliContract::test_zsh_invocation_fails_loud_with_the_correct_reason -p no:xdist
leg heartbeat_zsh $T test_dev_start.py::TestNightlyHeartbeatCrossSiteBehavioralEquivalence test_dev_start.py::TestPickPythonGeMin::test_candidate_chain_word_splits_under_zsh -p no:xdist
leg mac_nightly   $T test_dev_start.py -k TestMacNightly -p no:xdist
leg perception    $R/AutoClaude tests/test_perception_platform_honesty.py -n0
```

主控親跑輸出（script_rc=0；六腿輸出合計 52 passed／1 skipped；其中 [MAC-NATIVE-ONLY] 標籤測試 37 支＝AST census 3＋1＋1＋6＋25＋perception 腿 1 全 passed、標籤 0 skip；perception 腿的 1 skipped 是 [WINDOWS-NATIVE-ONLY]）：

```
leg=zsh_carrier rc=0 :: 3 passed in 1.03s
leg=launchd_real rc=0 :: 1 passed in 0.18s
leg=zsh_cli rc=0 :: 1 passed in 0.09s
leg=heartbeat_zsh rc=0 :: 6 passed, 12 subtests passed in 0.82s
leg=mac_nightly rc=0 :: 25 passed, 261 deselected in 8.73s
leg=perception rc=0 :: 16 passed, 1 skipped in 0.90s
```

## 附錄 B：28 列在本輪改寫前（HEAD 999c53f3）的帳本原文逐字保全（R124 瘦身體例；列已瘦身為一句話＋本檔指針，本附錄是唯一的全文載體，不得再改）

```
| DEF-101-675 | 2026-08-01 | R67 GATE 包落地時對 C 維探針做鑑別力驗證（本機注入實測） | **`macos-compat-ci.yml:395-401` 的 zsh 探針對它要抓的故障模式結構性失明**：`zsh -c 'source dev_start.sh; <斷言>'` 形狀下，注入「sourced 偵測壞掉」後 `dev_start.sh` 的 `exit` 直接殺掉整個 shell，斷言全未執行而 rc 仍 0（全綠） | P3（載具鑑別力缺陷，非生產碼；CI 停擺故活體影響零） | 本機側已修；CI yml 側需 workflows 授權包 | partial：本機改行程外側證物檔已釘住抗失明結構；CI step 本身仍失明，未指派。全文詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-675 |
| DEF-101-736 | 2026-08-02 | R69 終審 R3（P2 #18；QA 覆核 archive_48 已結列的殘留待辦） | **承接項只寫在已結列內⇒結構上零機械追蹤**：`DEF-101-729`(fixed/archive_48)同欄承接項（跨樹一致性保障退場後無等價替代）無任何載體，孤兒承接稽核只掃未結列 | P2 | 根層護欄層／帳本流程 | open（承接輪次：未指派）：待辦＝補 `DEF-101-729` 退場的跨樹一致性保障等價替代，或裁決「不需要」；並承接 `DEF-101-557`／`649`／`880` 三筆真待辦（`560` wontfix@R128：archive 側屬史料），不另立列。全文詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-736 |
| DEF-101-796 | 2026-08-04 | R74 Scan-N（雙向落差缺陷注入實測） | **六類「只在 mac/Linux 會炸」的注入，11 道本機閘門只攔下 2 類**，pre-commit 對六類全數放行（0/6）；Windows 專屬 skip 有可見度機械物，macOS 專屬 skip 一個都沒有（無對稱物） | P1 | 本輪修復（`check_sh_eol` 上移根層＋pre-commit 行尾閘＋mac 對稱物） | partial：解鎖條件的 `--apply` 已實跑，但印出的 0/6 因載體自身兩筆缺陷而失實，不結案，未指派。全文詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-796 |
| DEF-101-856 | 2026-08-05 | R76 收斂包彙整七包 `not_done` | **收斂包判定不宜當場做者，原七項經拆列**：①已由 `DEF-101-865` 同輪完成；②③④⑤ 已各自拆為獨立列 `DEF-200-247`～`250`；⑦（§6.2 稽核表零載體之慮）因拆列而消解——各發現皆已有獨立可稽核載體；⑥ pgvector recall 3 支測試需 staging，保留本列 | P2 | 根層護欄層（pgvector staging 部分） | open（承接輪次：未指派）：待辦＝pgvector recall 3 支需 staging 覆核；R128 現查本機 Docker 非等價（pg18、bge_m3=0 列、斷言未實作）。詳 CrossPlatform_R128_Debt_Closure.md §DEF-101-856 |
| DEF-101-887 | 2026-08-07 | R78 nightly 診斷（T1 與 T3 三層） | **觀察期取證鏈斷裂**：排程在收輪作業進行中觸發，量到從未存在於版本史上的中間態工作樹，該紅既非缺陷亦非綠而是無效樣本；obs／drift／ac4 三軌既有樣本全部零樹狀態欄位⇒汙染程度回溯不可判定 | P1 | 四個 collector 各加樹狀態欄位並在 GA 判準側排除無效樣本 | open：已落地＝nightly 起跑印樹狀態指紋與 WARN。未做＝四個 collector 寫入端仍不記樹狀態，統計仍無法自動排除無效樣本，未指派。全文詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-887 |
| DEF-101-938 | 2026-08-08 | R80 包 F S8-02 接線缺口 | 上一列的 shellcheck 閘門**本機零接線**：未接進 `tools/git-hooks/pre-push`。以 `python3 tools/*.py` 形態出現的守門受 `tools/tests/test_root_infra_parity.py` 雙向鎖要求同步接進 pre-push 快層，實測加入後該檔立刻三紅（含 `_FLOOR_CI_PYTHON_TOOLS：現查 11、已釘 9`），且載具是 docker 或 shellcheck | P3 | 交棒（需與 pre-push 持有者共同決定接線層級與載具缺席時的處置） | open（承接輪次：**R81**）：**不宣稱本地已有對等防線**。詳見 CrossPlatform_R80_PackF_Posix_Evidence.md S8-02 節｜R82 改派：承接輪次 **R83** |
| DEF-101-974 | 2026-08-08 | R80 收尾（act Linux 紅的真因） | 靜態面對「函式體內 skipTest 的方向」結構性失明：`site_class` 對它先回 `runtime-skipTest` 就 return、抽取面又把 condition 設空 ⇒ 判準①恆不成立。而 runtime 面在 Windows 整組早退 ⇒ 同一個漏標，裝飾器形態兩平台都紅、函式體形態只有 Linux 紅 | P2 | 判準①改讀 `skipped_platform`，或抽取面補捕外層 if 條件 | open（承接輪次：**R81**）：本輪只補兩支漏標；不動抽取面因 `_SITE_CLASS_CENSUS` 是相等棘輪會逼別包重釘。詳見 CrossPlatform_R80_Scan_Findings.md §D｜R82 改派：承接輪次 **R83** |
| DEF-101-981 | 2026-08-09 | R81 收尾單人窗口（彙整各包 not_done） | 本輪不宜當場做者六項，經拆列：①②③④⑤已各自拆為獨立列 `DEF-200-252`～`256`；⑥`tools/lib/hook_wiring.py` 解析 settings 與探測載具混在一起，保留本列 | P2 | 重構（hook_wiring.py 職責分離） | open（未指派）：待辦＝`hook_wiring.py` 解析 settings 與探測載具兩職責分離並附實測；詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-981 |
|DEF-200-118|2026-08-15|R89 收尾／SA 複審條件 3|**靜默計費在節流帶零觀測者**：PRD `:878`／`:1386`（§15.6 處方「FREEZE ＋對 overage 類告警」）的**告警半邊零實作**；R89 把保險軸移出 cap 聚合後，它在 notice/converge/prepare 帶完全沒有觀測者。另：主 session 每輪**不受 cap 管**（只約束扇出型工具）＝致動器缺口|P1|未修。🔴 措辭（SA）：改動前**不是**靜默計費的保護（100% 才反應）；誠實說法＝移除保險軸在 halt 帶的唯一反應，而 PRD 指定的替代從未存在。減輕：屬 §15.4 P4 相位，`:878` 不在該表|open（承接輪次：**R95**）→承接R98→承接R101|
|DEF-200-124|2026-08-15|R89 收尾窗口|`prose` 分桶棘輪量的是 **chunk 歸類**不是行數 ⇒ 兩向訊號皆假：塊內有一路徑 token 即整塊計入。`test_quota_policy.py` 三塊因搬遷體例的 `docs/` 指標，實質 **+6 行**讀出 **+157**；反向壓掉判準理由得 **−74**／**−69** 假減法（各 2 行）|P2|未修。候選＝指標行單獨形成的 prose 歸屬比照 `reference_counts()` 的 `self_name` 先例。需四方複審|open（承接輪次：**R95**）：代價＝壓回綠在 14 支無關鎖檔刪 **110 行**史料 ⇒ 棘輪指定的正解觸發棘輪自己。逐筆＝`CrossPlatform_R89_Closure_Evidence.md`〈分桶棘輪〉節→承接R101|
|DEF-200-129|2026-08-15|R90 帳本單人窗口（硬規則② 關鍵字出口存量普查）|硬規則② 的「改派」關鍵字出口存量**不是個位數**：當回合普查未結列中走該出口者共 **49** 筆，其中 **28 筆早在 R89 之前就已靜默過期**（承接輪號分佈 R79:9／R82:11／R83:7／R85:1）⇒ 交棒書 §5a 把「收緊這條出口」列為另案時所據的量級失實。普查腳本與逐筆見 CrossPlatform_R89_Closure_Evidence.md §DEF-200-129|P2|收緊＝自列「改派」也須指名 ≥ 當前輪的輪號（跨列回執那一半 R84 已做）；上線前先量假紅| open（交由R112）R111：函式已落、閘門接線待結案輪 |
|DEF-200-134|2026-08-15|R90 收尾（掌舵者指出）|**並行包自陳「沒做到什麼」後誰承接，零機械物**：包 F §5 列 8 項未完成，第 8 項（本三列入帳）主控未接手即靜默遺失。subagent 回報只住系統暫存、永不進 repo ⇒ 帳本／交棒書／幽靈路徑鎖＋四方複審全看不到（同 R77／R79 第②層）。本輪三包（F／D／縮減複審 2）各留未完成清單，核銷靠主控記得|P1|未完成項須倒進既有載具（帳本／交棒書列）才算交件；載具已存在（含包 E 條件式承接），缺強制傾倒門。判準面＝交棒書未完成項節 ↔ 帳本 open 列|open（承接輪次：**R95**）|
| DEF-200-165 | 2026-08-19 | R96 四方複審（Architect） | **`.toml`／`.json` 的工作樹行尾漂移無人守**：當回合實測 tracked `.toml`／`.json` 共 **165 支**，其中 **142 支**宣告 `text eol=lf` 卻在工作樹是 CRLF；`git status` 與雲端 fresh clone 對此結構上不可見（正規化只作用 index，見 R78 判例）。現有三道行尾鎖的射程只有 `.ps1`／`.py`／`.sh` | P3 | 判準擴面到 `.toml`／`.json`（比照 `.py` 的活躍面止血＋凍結面只登記），寫入點補 `newline="\n"` | open｜mac複驗0/165，需Windows復驗，未指派｜Win11複驗140/165，與R96量級一致，mac 0為假陰性 |
| DEF-200-182 | 2026-08-21 | 同上（R98 交件驗證清單稽核） | 🔴 **假綠 B（沒跑）**：`ea304b2` 的〈驗證〉節只列四項 ⇒ DEF-200-179／180 從未被量到。原文另有一句「繞過 pre-push」推論，R128 親驗為假，原文逐字保全於證據檔 | P1 | ①「驗證清單須涵蓋哪幾套閘門」缺機械物（平台無關）②已查清 | open（未指派）：②結案＝非繞過，是 leg 依路徑路由合法不觸發（親驗 count=0）；①原設計對立案案例失明，待重新拍板。詳 CrossPlatform_R128_Debt_Closure.md §DEF-200-182 |
| DEF-200-188 | 2026-08-22 | 交接載體根治包（發現情境刻意不寫輪號，見狀態欄） | **交接項只寫在散文裡就沒有機械承接單位**：R99 宣告延後六項，「B8 額度術語機械化」另稱「規格已完成」，當回合實查全 0 命中（`docs/` grep rc=1、`git log --all -S` 0 commit、帳本指向 R100 的承接列 0 列）。唯一載體＝commit `f5607fa`／`772e28b` 訊息，不可改也不在閘門輸入面 | P1 | 新增 `tools/check_handoff_carriers.py`（取證與三判準見其檔頭） | open（承接輪次：**R101**）：判準當回合抓到這三筆。未做＝B8 規格本體＋回歸鎖（須落 `tools/tests/`，鐵律七） |
| DEF-200-207 | 2026-08-23 | R100 收尾窗口（護欄層治理 C1） | **`ADR-XPLAT-013` 仍是 `Proposed` 而機械物已在生產跑**（`:3` 逐字 Proposed、`:181` 自陳程序後補、§7 的 U1~U7 全為 ☐）。🔴 豁免鎖**前提已反轉**：`17032 not greater than 17070`（baseline≤total⇒量不到「未重釘」）。見 §D-12 | P1 | 四方已重開並裁決 E1/E4；E3 R101 已改判 provenance；`--repin-cap`／`--update` 已於 R102 push 收尾追加回合實跑（`6fea8a3`） | partial（承接：**R117+**）：R116 追加 U5/U6/U9 進度，詳見 `CrossPlatform_R116_Scan_Findings.md`；`ADR-XPLAT-013` 仍為 Proposed |
| DEF-200-234 | 2026-08-29 | 429 同池同死鑑識複盤（哨兵事故；本欄刻意零輪號＝不推當前輪時鐘） | 主控死於 API 層 429 時，存活的背景 agent／Monitor／背景任務**無任何機制轉入無主模式**（節流／收斂／向哨兵登記皆無）——本次因同池同死未實燒；異池或純本地長任務時結構上無人統籌（詳 CrossPlatform_R111_Sentinel_Forensics_Mac.md §4-6） | P3 | 修法方向＝哨兵巡邏 tick 增列「主控死亡但 tasks/ 有活體」分支 | partial（承接輪次：**未指派**）：偵測面 fixed@09-01；解鎖＝處置面落地過複審（R116_HANDOFF §二第 7 項；載體訂正 v2.1.12 REQ-W2） |
| DEF-200-251 | 2026-09-03 | `DEF-200-065` 收集列拆出（本欄刻意零輪號，原第①項） | **ARCH-09**：`skip_*` 六模組族正在複製 quota 族的形態（`skip_source_io` 僅 35 loc＝一支模組的固定成本＞內容），應收斂成政策／掃描／門面三支，目前只登記診斷、未動工 | P2 | 重構（skip_* 六模組族收斂） | open（未指派）：待辦＝六模組族收斂為政策／掃描／門面三支並附實測；詳 CrossPlatform_R124_Row_Slimming.md §DEF-200-065 |
| DEF-200-252 | 2026-09-03 | `DEF-101-981` 收集列拆出（本欄刻意零輪號，原第①項） | **`[MAC-NATIVE-ONLY]` 零覆蓋證據**：缺 mac 真機，非缺程式，該類測試在本機結構上跑不到 | P2 | 缺硬體（需 macOS 真機） | open（未指派）：待辦＝取得 macOS 真機後補覆蓋證據，或明文 wontfix 並附理由；詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-981 |
| DEF-200-253 | 2026-09-03 | `DEF-101-981` 收集列拆出（本欄刻意零輪號，原第②項） | **win32+nopg+nested 剖面的 skip 基線 stale-high 無牙**：基線設太寬，實際 skip 數低於基線也不會被抓到 | P2 | 重構（skip 基線判準收緊） | open（未指派）：待辦＝收緊該剖面 skip 基線使其有牙並附紅綠自證；詳 CrossPlatform_R124_Row_Slimming.md §DEF-101-981 |
| DEF-200-265 | 2026-09-04 | ONBOARDING 表② 回填跑完 AutoClaude 全套後查 `git status`（本欄刻意零輪號） | **隨機重生的 fixture 被 tracked ⇒ 每輪固定 2000 行 diff 噪音**：`tests/fixtures/pgvector_real_ground_truth.json` 的內容是每次 seed 重新生成的隨機 UUID 清單，跑一次即整檔改寫（單檔 numstat 實測 1000／1000） | P3 | 二擇一：改衍生產物不入庫，或改固定種子讓內容可重現 | open（未指派）：待辦＝擇一落地並附紅綠自證；兩層危害與判準面詳 CrossPlatform_R128_Scan_Findings.md §3 |
| DEF-200-311 | 2026-09-15 | 本輪 push 的 pre-push AISDLC_SDD v0.30 ci-gate 腳（本欄刻意零輪號） | **`test_conversation_ledger.py::test_concurrent_writers_do_not_tear` 在 pre-push 並行負載下偶發紅**：`1 failed, 1934 passed` | P2 | 疑 DEF-200-287 殘餘；承接輪次：**未指派**；解鎖條件：v0.30 下該測試 `-k concurrent_writers -p no:xdist` 連跑 20 次任一紅即開修復窗口 | open（2026-09-15）；2026-09-26 mac 加壓 20/20 綠，未重現≠已修，解鎖條件不變。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗 III〉。 |
| DEF-200-361 | 2026-09-22 | DEF-200-359 設計審查 D5 2:2 裁決延後的後續項（本欄刻意零輪號） | **CI 四個 linked-worktree 拒絕 step 仍只比 rc=1，未比對 LINKED-WORKTREE-REJECTED 標記**：`windows-compat-ci.yml` 與 `macos-compat-ci.yml` 各兩處，rc=1 空洞通過的同型風險（DEF-200-359）在雲端未關閉 | P2 | 比照 DEF-200-359 補 SSOT ASCII 標記斷言（yml 無法 import 常數，需字面複本＋同步鎖） | open（未指派）：只能 push 後驗，待下一輪 CI 修復窗口 |
| DEF-200-381 | 2026-09-25 | 掌舵者裁決加軌 DEF-200-379 觀察期追蹤，主控登記（本欄刻意零輪號） | **`aisdlc-sdd-fsm-chaos-nightly.yml` 新增 `chaos-latest` job 尚未進入 `GATING_JOB_NAMES`（Rule 9.9.4 連敗計數不含它），觀察期未開始 ⇒ 首次排程 run 前無法驗證其穩定性** | P3 | 2026-10-03 起查 7 次排程 conclusion，全綠則裁決是否納入 GATING_JOB_NAMES | open（未指派）：觀察期 2/7（2026-09-26 新增一次成功排程，日曆 2026-10-03 未到），同步鎖 `test_gating_job_names_does_not_yet_include_chaos_latest`。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗 III〉。 |
| DEF-200-395 | 2026-09-26 | 前輪誠實劃界遺留，收斂後複驗 QA 重現（本欄刻意零輪號） | **`test_install_windows_nightly.py` 的 WhatIf 測試曾於並行全套紅一次、當時輸出未保留；本輪 30 次壓力（含與全套並行）全綠，根因未明** | P3 | 四處 subprocess 補 timeout；WhatIf 斷言訊息帶 before／after 與 PowerShell rc／stdout／stderr 尾段 | open（2026-09-26）：未重現≠已修；mac 上 [WINDOWS-NATIVE-ONLY] 皆 skip（2 skipped×20），只有 Windows 能重現；承接輪次：**未指派**。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗 III〉。 |
| DEF-200-403 | 2026-09-27 | 設計調查過程新發現（本欄刻意零輪號） | **`AutoClaude/tools/run_local_nightly.sh` 從未有 `sdd-fsm-chaos-latest`（或任何 chaos_runner）字樣——DEF-200-379 落地時只加了 `.ps1`，parity 缺口先於本輪存在** | P3 | 承接輪次：**未指派**（解鎖條件：mac 真機現查 `.sh` 是否已補上該 stage，若否再評估搬遷整條 chaos stage） | open：本輪不修（Rule 3 外科手術式；範圍是整條 chaos stage 搬遷，非本輪圍籬可比）。詳見 CrossPlatform_R178_ChaosRunner_Governance_Writeback_Evidence.md |
| DEF-200-418 | 2026-09-28 | 同上輪追蹤者 B 的 AST 普查（本欄刻意零輪號） | **`ConsoleFreeSpawnTest` 射程是策展式允許清單**：`tools/*.py` 16 站點（git／powershell 字面、無 creationflags）、`tools/lib` 非 quota_*／sentinel_* 14 支、`tools/probe` 皆不在掃描面；判準看不穿 `_run()` 類包裝函式 | P4 | 見狀態欄 | open（承接輪次：**未指派**；第一步已做 2026-09-29：掃描面策展式納 tools/probe 四支、實測假紅 3；餘 tools/*.py 16 站點與 tools/lib 待跨函式呼叫圖判準後逐站判，見 CrossPlatform_R183_SessionGate_Windows_Recheck5_Evidence.md） |
| DEF-200-458 | 2026-10-02 | DEF-200-198 拆殘（施工圖 §9 W4／W6；本欄刻意零輪號） | **施工圖 W4／W6 未落地**：(b) `bursting_ok` 階段 B1 接線只出聲＋六條件輸入落款（W4）、B2 `pace_near` 條件制＋(c) `T_wrap` 升 30 分＋引擎反向契約（W6，三件須同窗）；W5 已落 `T_wrap`=5 分 | P3 | W4 可單包（需新 lib 檔或餘裕）；W6 需 W4 樣本＋引擎側改動 | open（承接：未指派；DEF-200-458） |
```
