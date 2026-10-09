# CrossPlatform R211 ＝ AutoSDD_improving_113 零信任審計證據檔（Token 監控 PRD 剩餘收斂輪）

> 軌道① 第 113 輪的「四件套」第 2 件（範本名 AutoSDD_ZeroTrust_Audit_113）；冠 `CrossPlatform_R211_` 前綴是因帳本時鐘
> （`tools/check_defect_log_crossref.py` 的 `current_round()`）讀 R 系列證據檔檔名最大號——本檔建立即把時鐘自 210 推進到 **211**，
> 護欄棘輪重釘列、接鏈列、ADR-XPLAT-002 §6 覆蓋表列與本檔同一輪號。計畫書＝`docs/04_planning/AutoSDD_improving_113.md`（§1～§3 先落地、§4～§8 回填）。
> 平台：macOS 真機（當回合現查 `python -c "import sys,platform;print(sys.platform, platform.platform())"` → `darwin macOS-26.6.2-arm64-arm-64bit`）；`HEAD=93929947`。
> 主控 Fable 5.1 兼 Architect；盤點／實作／審查 agent 皆 Sonnet（`model: sonnet`）；審查鏡一律唯讀。

## 〈一〉本輪範圍、基線與角色

- W1 模型角色參數化（掌舵者 2026-10-09 立案；三鍵進 `ENV_SPEC`、新純函式 tools/lib/model_roles.py、喚醒續跑 argv `--model`、喚醒窗口子代理預設、降級建議字面、付費探針模型）。
- W2 `resume_cost_pp` 喚醒成本落帳（tools/lib/resume_cost.py＋relay_machine settle_window 接線）。
- W3 AutoClaude 引擎無人值守硬化（分片休眠＋拒絕長睡＋CLI 已驗證清單 2.1.295）。
- 改動前基線（主控親跑、逐字）：AutoClaude `4864 passed, 156 skipped in 36.69s`；`Contracts: 9 kept, 0 broken.`；SDD ci-gate `✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）` 逐軌 1475／1979／362；根層 `✅ unittest 數量下限釘選通過：發現 5207 個測試（下限 5101）` rc=0。
- 盤點交件（唯讀 Sonnet）：PRD 覆蓋度 (a)＝60.3%（⚠️ 計 0.5）、敏感度 0.72 權重＝73.5%、R98 12 項嚴格 25%；完整矩陣保全於本檔〈七〉附錄 A。

## 〈二〉四方複審 findings 落檔（逐條原文；依 DEF-200-090 教訓，先落檔才進修復）

### 二-1 W3 QA 零信任複審鏡（VERDICT: CONDITIONAL，條件 QA3-01）
（原文逐字保全於姊妹檔 `docs/06_quality/CrossPlatform_R211_Review_Transcripts_113.md` 〈T-1 W3 QA 鏡〉；本節只留判決與條件 ID。）


### 二-2 W3 SD／Architect 設計符合性鏡（VERDICT: CONDITIONAL，條件 SD3-01～SD3-04）
（原文逐字保全於姊妹檔 `docs/06_quality/CrossPlatform_R211_Review_Transcripts_113.md` 〈T-2 W3 SD／Architect 鏡〉；本節只留判決與條件 ID。）


### 二-3 主控對 W3 條件的裁決（修復包任務書逐字要點）
- QA3-01／SD3-03：`sleep_slice_seconds` 出廠改 30（對齊 PRD §6 區塊 9）；`clock_jump_tolerance_seconds` 保留 5（兩鏡皆證 PRD 的 120 對增量帳演算法病態：每片 <120s 的差被忽略會無界累積、最壞晚醒約 4 小時），於 config.py 註解與 PRD v2.1.16 落款載明偏離理由；`max_inprocess_wait_seconds` 出廠改 18000（一個五小時額度視窗；本機 3 個真實等待 episode 54.5／189.6／224.2 分校準，PRD §15.7「以資料校準」；HEAD 上無任何根層元件承接被拒絕的等待）。
- SD3-01：所有「交棒由根層哨兵承接」字樣改為「本版無自動承接者：拒絕長睡時引擎 rc=1 退出並於 stderr 明示需外部重啟」；自動承接列入 improving_114 候選。
- SD3-02：拒絕分支寫回真實續跑時刻到 checkpoint `scheduled_resume_at`。SD3-04：牆鐘倒退 warning 文字改為「忽略倒退、以單調鐘續睡」。QA3-02／QA3-04：補測試。QA3-03：不接 hotkey（既存缺口），只改敘述。
- P4（QA3-06～09、SD3-05～14）：只做 ERROR→stderr 與訊息順序兩條便宜項，其餘登記〈三〉。

### 二-3b W3 修復包結果（Sonnet 修復 Developer 交件摘要；全文＝scratchpad w3_fix_log_113.md，收尾抄錄要點）
- QA3-01／SD3-03 fixed：`sleep_slice_seconds` 出廠 30；`clock_jump_tolerance_seconds` 保留 5（起手實測 tol=120 最壞晚醒 +14280s、tol=5 為 +588s）；`max_inprocess_wait_seconds` 出廠 18000；config.py 章節誤引改「PRD §6 設定檔區塊 9」；defaults 測試拆成對齊／偏離各一支；tol 補 `le=3600`、max 補 `le=86400`＋邊界測試。
- SD3-01 wording：example、`_wait` 註解、ERROR 訊息改「本版無自動承接者」。SD3-02 fixed：新 `_pin_resume_time()` 把 checkpoint 的 `scheduled_resume_at` 改寫為真實等待終點（ceil 到分鐘、寧晚勿早；只改寫讀得回的 checkpoint）；兩種拒絕結果皆帶時刻。SD3-04 wording＋caplog 雙向斷言。QA3-02／QA3-04 fixed（邊界測試＋上界 `60 < sum <= 305`）。QA3-03 wording（入口未註冊 hotkey，不接線）。
- P4 兩條：INFO 改「排定等待／距今」；「ERROR 改寫 stderr」skipped（logger 只有 stdout console handler，屬全域 logging 政策，所有文字改稱「log 的 ERROR 行」）。
- 突變證明：M1（`>`→`>=`）、M7（續跑等待執行兩次）等 7 個突變全數被擊殺；cp 備份／還原 sha256 相同。
- 驗收逐字：五支目標檔 `210 passed in 2.04s`；全套 `4919 passed, 156 skipped in 37.85s`（基線 4910／156，+9）；`Contracts: 9 kept, 0 broken.`；ruff `All checks passed!`；LOC violations 空；snapshot_sync rc=0；真 FileStateRepository 端到端 22 PASS／0 FAIL；本機三個真實額度等待（54.5／189.6／224.2 分）在新預設下不被拒絕。
- 殘留（收尾處置）：auto_resume.py 295 行（tier ≤500）；`resume_delay_minutes` > 300 分現在會被拒絕（出廠 30 不受影響）；auto_resume.py 既存 R82 註解仍寫「OS 級喚醒由根層哨兵負責」（收尾改字）；PG／Dual 後端 pin 路徑未實跑；只在 macOS 驗。

### 二-4 W1 SD／Architect 設計符合性鏡（VERDICT: CONDITIONAL，條件 SD1-01、SD1-02）
（原文逐字保全於姊妹檔 `docs/06_quality/CrossPlatform_R211_Review_Transcripts_113.md` 〈T-3 W1 SD／Architect 鏡〉；本節只留判決與條件 ID。）



### 二-4b W1 QA 零信任複審鏡（VERDICT: CONDITIONAL，條件 QA1-01）
（原文逐字保全於姊妹檔 `docs/06_quality/CrossPlatform_R211_Review_Transcripts_113.md` 〈T-4 W1 QA 鏡〉；本節只留判決與條件 ID。）



### 二-4c 主控對 W1 條件的裁決（修復包任務書要點）
- SD1-01（P2）：`tools/lib/model_roles.py`（與 W2 新檔若鎖要求）補進兩支 compat-ci workflow 的 paths（push＋PR 共 4 處），以 AISDLC_SDD 側 `test_ci_paths_cover_root_consumers` 鎖親驗。
- SD1-02／PRD-01～12：PRD 草稿第 2 版全數採納（只印設定值、版本條件、三項行為披露、命名交叉參照、日期與紀錄指針、單一 v2.1.16 涵蓋 W1＋W3）。
- SD1-03：`AUTOSDD_MODEL_SUBAGENT=inherit` 合法且＝不注入（child_env 回空）、僅限 SUBAGENT 鍵；降級建議行不得印 `inherit/`；ENV_SPEC 說明補字、`.env.example` 重生；+4 測試。
- SD1-05（留痕）：P4 只登記；實際採用模型的真相源＝該窗口轉錄檔 `message.model`，另由 W2 落帳 record 的 `model` 欄承接（零成本）。
- QA1-01：下游落款一律寫「call2 的 modelUsage＝haiku（累計舊回合）＋sonnet（本回合，與頂層 usage 逐項相等）」，不寫「只含 sonnet」。QA1-02：檔數下限由收尾單人窗口以最終實測重釘。
- QA1 P4：quota_gate 的 `model_hint_line` 無消費者 re-export → 若無測試引用即移除（淨 −1）；其餘登記〈三〉。
- 流程缺陷（自我登記）：主控任務書允許 QA 鏡在共用工作樹就地突變並 cp 還原，導致 SD 鏡在 00:54:58 讀到暫態（SD1-13）；違反範本「突變 tracked 檔 → worktree」紀律（新檔雖 untracked，共用樹仍是共用樹）。登記〈三〉並寫入主控記憶：突變實驗一律在隔離副本。

### 二-4d W1 修復包結果（Sonnet 修復 Developer 交件摘要；全文＝scratchpad w1_fix_log_113.md）
- SD1-01 fixed：`.github/workflows/macos-compat-ci.yml` 與 `.github/workflows/windows-compat-ci.yml` 的 push＋pull_request 四處各補 `tools/lib/model_roles.py` 與 `tools/lib/resume_cost.py`（AISDLC_SDD 側 `test_ci_paths_cover_root_consumers` 鎖同時要求 W2 新檔）；該鎖改前 `2 failed, 47 passed` → 改後 `49 passed in 13.19s`。
- SD1-03 fixed：`inherit` 只限 SUBAGENT（精確拼法；HELMSMAN／DOWNGRADE 仍拒收＋出聲）、child_env 回 `{}`、角色行印「子代理=inherit（不注入，沿用視窗模型）」、新 property `pinned_subagent`／`hint_first`，`quota_messages` 只改一個引用（守衛面 +0）；ENV_SPEC 說明補句並重生 `.env.example`。`--pace` 逐字：預設「子代理=sonnet」、降級建議仍 `model: sonnet/haiku`；`AUTOSDD_MODEL_SUBAGENT=inherit` ⇒「子代理=inherit（不注入，沿用視窗模型）」與「建議派工帶 model: haiku 續跑」。
- QA1 P4 fixed：全 repo 無消費者 ⇒ 移除 `tools/lib/quota_gate.py` 的 `model_hint_line` re-export（斷言行 495→494；本檔二-4 原文所引 quota_gate.py:136 的 re-export 已不存在）。W3 殘留：auto_resume.py 的 R82 舊註解改為「本版無自動承接者；拒絕長睡時以 rc=1 退出並明示需外部重啟（improving_113）」。
- 紅綠：新 4 支測試中 3 支先紅（如 `{'CLAUDE_CODE_SUBAGENT_MODEL': 'inherit'} != {}`）；拒收那支以行程內 7 個變異全 KILLED 證鑑別力。驗收逐字：14 組 unittest `Ran 867 tests in 121.724s`／`OK`；test_model_roles `Ran 60 tests`／`OK`；ruff 六檔 `All checks passed!`；`.env.example` diff 零輸出；check_loc_budget 四類 violations 皆 `[]`；AutoClaude 抽驗 `test_r86_pace_contract`＋`test_auto_resume` 100 passed、`test_r82_…` 97 passed。
- 收尾計入：tests +4、test_model_roles.py 573 行；守衛面斷言行淨 −1。未驗證：根層與 AutoClaude 全套（收尾單人窗口跑）、Windows／PS 5.1、`inherit` 的行為層（真子代理是否跟隨視窗模型，只有文件＋二進位字串證據）。

### 二-5 W2 SD＋QA 合一審查鏡（VERDICT: APPROVE；附三份補丁）
（原文逐字保全於姊妹檔 `docs/06_quality/CrossPlatform_R211_Review_Transcripts_113.md` 〈T-5 W2 SD＋QA 合一鏡〉；本節只留判決與條件 ID。）



### 二-5b 主控對 W2 補丁的裁決與套用（2026-10-10 親跑）
- 三份補丁全部採納並由主控以 `patch -p0` 套進工作樹：spawn 錨改讀 planner 於 spawn 前落的 `relay_snapshot_before` 事件 `at`（接力窗與 reset_at 空路徑不再恆 measured:false——🔴 但補丁不含 `settle_window` 那一行 `log=log` 接線，最終 QA 以 FQ-01 抓到，見 二-6；resume_cost.py 140→153 行，超出規格「≤90 斷言行」的估計、仍遠低於 tier 400）；`settle_window` 接線加 `contextlib.suppress(Exception)` 第二道網（relay_machine 254→256 斷言行）；測試補丁 +4 行不新增測試方法（MIN_TESTS 零相依餘裕）。
- 套用後主控親跑逐字：`test_resume_cost`＋`ResumeTickWritesStateOnlyAfterConfirmingTest`＋`test_wake_chain_halt_r278`＋`test_mac_readiness_r82`＋`test_platform_utils_dedup` ⇒ `OK`；relay 相關測試類 `rc 0 fail 0 err 0`；ruff 一度 `Found 1 error.`（E501：補丁 docstring 101 欄）⇒ 縮短一字後 `All checks passed!`；`check_loc_budget --json` 五類 violations 皆 `[]`。
- W2-06（FRESH 路由窗與 RESUME 量不到列同形）：P4 登記〈三〉，不加欄。

- 收尾單人窗口補抓（2026-10-10，主控親跑）：乾淨 venv 回填第一次 rc=1，真因＝SDD 側 `scripts/tests/test_ci_paths_cover_root_consumers.py::test_no_unresolvable_sys_path_inserts` 對 `tools/tests/test_resume_cost.py` 的 `sys.path.insert(0, str(_TOOLS))` 靜態解析失敗——而 `_TOOLS` 竟是**寫死的本機絕對路徑** `Path("/Users/wuweihong/…/tools")`（四面鏡與 Developer 皆未抓到；只在乾淨環境的 ci-gate 現形）。修法＝改成與 `tools/tests/test_model_roles.py` 相同的 `Path(__file__).resolve().parents[2]` 相對寫法；全部新檔 grep `/Users/wuweihong` 零命中。重驗：`test_resume_cost` OK、ruff `All checks passed!`（UP017 要求 `datetime.UTC`，為 repo 的 py311 目標規則）、該鎖 `49 passed in 14.08s`。


### 二-6 最終 QA 零信任複審鏡（VERDICT: REJECT，FQ-01；28 項閉環 26 closed／2 open）
（原文逐字保全於姊妹檔 `docs/06_quality/CrossPlatform_R211_Review_Transcripts_113.md` 〈T-6 最終 QA 鏡〉；本節只留判決與條件 ID。）



### 二-6b 主控對最終 QA 的處置（2026-10-10 親跑）
- FQ-01 fixed：`tools/lib/relay_machine.py` 接線改 `resume_cost.record_window(state, log=log)`；QA 於隔離副本寫好的鎖測試 `test_a_relay_window_is_measured_from_its_own_spawn_not_from_reset_at` 落地（`tools/tests/test_resume_cost.py` 183→197 行、6 支）；接線前該鎖 RED（QA 實跑）、接線後 `Ran 9 tests`／`OK`（主控親跑，含 ResumeTick 鎖）；ruff `All checks passed!`。
- FQ-02 wording：PRD D 段「stderr」改「log 的 ERROR 行」；E 段改寫接力窗以 spawn 錨定、落帳位置為 settle_window 入口；v2.1.16 修訂列擴充涵蓋 W2。FQ-03：計畫書 §3.1(1)／§3.3 殘留與 §4 數字（resume_cost 99／153、sliced_sleep 32／58、W3 53 案、W2 6 支）全數訂正。FQ-04 fixed：主控自己 4 行 E501（governance_docs.py、skip_tag_policy.py）改行；`ruff check tools/ .claude/hooks/` rc=0。
- FQ-05：SD1-04（`--pace` 角色行只有 `inspect.getsource` 子字串鎖）處置＝P4 登記〈三〉#13：行為面已由三面鏡各自真跑 `--pace` 逐字驗（預設／inherit 兩態），`SessionBriefRolesTest` 4 支守簡報面；`pace_report` 住守衛面 hub（quota_gate 494/500），本輪不另加行為鎖。FQ-06～08：P4 登記。
- 收尾另抓：乾淨 venv 回填首跑 rc=1 揭露 `test_resume_cost.py` 寫死本機絕對路徑（見 二-5b 末段），已改相對寫法。

## 〈三〉理論洞與只登記（P4；不修、不立輪；再開條件＝症狀驅動，見五問 README S1～S6）

| # | 洞 | 來源 | 再開症狀 |
|---|---|---|---|
| 1 | hook 對未帶 `model` 的 Agent 以視窗模型判額度軸，與官方序位（general-purpose 跟 `CLAUDE_CODE_SUBAGENT_MODEL`）有落差；典型配置偏保守、反向配置會少擋；hook SPECIAL 1089/1089 零餘裕 | SD1-10／survey A4 | 一次「sonnet 週軸比視窗軸緊」配置下的真實漏擋（sid＋seq） |
| 2 | `python -m autoclaude` 入口從未呼叫 `HotkeyHandler.register()`；等待期間按鍵不會中斷（既存缺口，W3 只改敘述） | QA3-03 | 掌舵者真機要用中斷鍵 |
| 3 | 拒絕長睡的自動承接者缺席：HEAD 無任何根層元件重啟 `python -m autoclaude` 或消費引擎 checkpoint；出廠上限 18000 使本機三個真實 episode 皆不被拒 | SD3-01 | 一次真實 >18000s 等待被拒後無人續跑 |
| 4 | AutoClaude 引擎獨立跑時額度軸不存在（缺第三方刷新者；`AutoClaude/autoclaude/core/ports/quota_meter.py:15-45` 自陳；全 docs 零追蹤列） | 盤點 §6.5 | 引擎無 Claude Code session 獨立跑的真實撞線 |
| 5 | 無人喚醒窗口壞模型值只退預設不另出聲；真相源＝該窗轉錄檔 `message.model`／W2 record 的 `model` 欄 | SD1-05 | 一次真實喚醒窗跑錯模型且無人發現 |
| 6 | 值域：大小寫未正規化、`default`／`best` 被拒、第三方雲端 id（`:`／`@`）被拒、錯誤訊息漏寫「首字須英數」 | SD1-07 | 帳號換 Bedrock／Foundry |
| 7 | `_GOV_EXACT` 保護面不含 `tools/lib/resume_route.py`／`model_roles.py`（無人窗口可 Write／Edit 改自己的模型角色邏輯） | SD1-11 | 一次無人窗口改這兩檔的實錄 |
| 8 | W2 v1：`pct_before`／`pct_after` 恆 None（spawn 前讀數無持久來源）；timeout 砍掉的窗不落帳；FRESH 路由窗與 RESUME 量不到列同形（無 strategy 欄）；§9 Prometheus 指標未接 | W2-06～10 | 要用 pp 校準 RESUME 門檻時 |
| 9 | W3：拒絕長睡時 `resume_delay_minutes` > 300 分亦被拒（出廠 30 不受影響）；PG／Dual 後端 pin 路徑未實跑；機器睡眠下單調鐘行為只依文件 | w3_fix_log | PG 後端真跑拒絕路徑 |
| 10 | 流程：主控任務書曾允許 QA 鏡在共用樹就地突變，SD 鏡讀到暫態（SD1-13）；已寫入主控記憶（突變一律隔離副本） | SD1-13 | 再次發生即違反記憶 |
| 11 | PRD 修憲候選 12 筆＋程序債 1 筆（修訂表 L10／L11／L13／L14 字面、§6 78 鍵中 28 鍵無對映、`RESET_CONFIRM_PERCENT` 等已廢字面）＋R108 BURN-DOWN Adopted 零落地、R121 Proposed 零落地 | 盤點 §5 | 下一輪 W-A 修憲整理批 |
| 12 | 本機 ONBOARDING 表② AutoClaude 欄為乾淨 venv 值（本輪回填 4819／222）；開發 venv 值（4919／156）不可相減；Windows 欄本輪未量測 | 基線 | 收尾回填 |
| 13 | SD1-04：`--pace` 角色行只有 `inspect.getsource` 子字串鎖；行為面由三面鏡真跑逐字驗、簡報面有 4 支行為測試；`pace_report` 住守衛面 hub 零餘裕 | FQ-05 | `--pace` 角色行真實消失而無鎖出聲 |


## 〈四〉雲端驗收（push 後回填 run id 與 conclusion）
## 〈五〉結案帳（收尾單人窗口，2026-10-10）
- 帳本：新立 DEF-200-507（模型角色零參數化）、DEF-200-508（喚醒成本零資料），同 commit fixed；`--unresolved-count` 逐字「未結列數＝0／全部 209 列｜warn=86 fail=98」；外部阻塞軌 5、結構性長債軌 6 不變。
- 時鐘：本檔建檔即推進 `current_round()` 210→211；ADR-XPLAT-002 §6 R211 列、governance_docs 登記三檔（本檔、PRD 覆蓋矩陣、審查逐字稿）。
- 護欄棘輪：`--print-guard-lines` 收斂「淨額 115598→115598 (+0)」；重釘列 R211（114811→115598，+787）、回歸鎖軌 309、主軌 478 ≤ 517（款(11) 連升第 1 輪）、`_REPIN_LOG_FROZEN_PREFIX_LEN` 330→331、sha 重釘、接鏈列（R211, bcdb57dd180d→d034314bdd87, DEF-200-507）、guard-total:R211 標記三站（improving_112／improving_113／R145_Scan_Findings）。
- 檔數下限：`tools/tests` 70→71、`AutoClaude/tests` 223→224（皆照 runner 逐字指示）；MIN_TESTS 5101→5273（discovery 實測）；ONBOARDING 表② macOS 欄以乾淨 venv 回填（AutoClaude 4819 passed／222 skipped；autoclaude 指紋 1975dfb92b6d；LOC 17413）、活格同步。
- 本機 `.env`（gitignored）設 `AUTOSDD_MODEL_HELMSMAN=fable`／`SUBAGENT=sonnet`／`DOWNGRADE=haiku`；主控親跑 `resume_argv` 逐字含 `'--model', 'fable'`（`--settings` 之後、`--add-dir` 之前）、`role_env()`＝`{'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'}`。
- 最終閘門（主控親跑，逐字）：AutoClaude `4919 passed, 156 skipped in 37.34s`；`Contracts: 9 kept, 0 broken.`；snapshot_sync OK；ci-gate `✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）` 1475／1979／362；LOC 五類 violations 皆 `[]`；crossref rc=0（未結 0／209、治理文件 165 份登記）；carriers rc=0；archive --check rc=0；sync --check／--check-snapshot rc=0；nightly 錨 --check-head rc=0；`ruff check tools/ .claude/hooks/` All checks passed；四支文件鎖模組 `Ran 517 tests`／`OK`、三支鎖模組（E501 存量債／棘輪／文件新鮮度）`Ran 476 tests`／`OK`；根層全套最終實跑逐字＝`✅ unittest 數量下限釘選通過：發現 5273 個測試（下限 5273）`，rc=0；skip 47 支全數有標籤；真實 TEMP 圍籬零變動

## 〈六〉Windows 機待辦（本輪 mac 開發；improving_113 期間 Windows 側未驗證）
1. `git pull` 後 `powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1`；重點：`tools/tests/test_model_roles.py`／`test_resume_cost.py` 在 PS 5.1 環境、`.env.example` CRLF 無異常。
2. 無人喚醒 argv 帶 `--model`（`AUTOSDD_MODEL_HELMSMAN` 非空時）在 schtasks 叫起的 tick 行程實跑一次：Windows 機 `.env` 若留空＝沿用現況，不必動。
3. AutoClaude 引擎 Windows nightly 首筆樣本：`sleep_slice_seconds=30` 下 `run_local_nightly.ps1` 的等待 log 應出現「排定等待／距今」字樣。
4. 沿用 `CrossPlatform_R210_Debt_Closure_Final_Evidence.md`〈八〉未結項（表② Windows 欄回填、tree 欄首筆樣本）。

## 〈七〉附錄 A：PRD 覆蓋度矩陣
盤點 agent 交件原文另存為同輪姊妹檔 `docs/06_quality/CrossPlatform_R211_PRD_Coverage_Matrix_113.md`（已登記 governance_docs；供下一輪重盤對照）。
