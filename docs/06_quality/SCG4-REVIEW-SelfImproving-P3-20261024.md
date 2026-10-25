# SCG-4 PR Review 報告 — SelfImproving P3（PRD FR-SI-22～27：量測、回滾偵測、劣化暫停、退役、容量；鍵 `monorepo-si-p3-measure-retire`）

**審查日期**: 2026-10-25（一審 09:0x～10:4x；二審 11:2x～11:5x）　**審查者**: SCG-4 獨立 QA（Sonnet，唯讀；未參與規格撰寫與實作——規格作者＝SA 棒（三審 PASS 後凍結）、實作者＝headless hooks-ON Sonnet Developer＋修復棒，三方不同）　**主控親驗**: 2026-10-25 06:2x（SI 子集）、09:1x（V22／V23 真帳本唯讀煙霧）、11:1x（修復棒後三個根層鎖、ruff、LOC、`si check`、`git diff --check`、探針）
**審查範圍**: 根層 `tools/lib/selfimproving/` 新檔 `mea.py`、`meaplan.py`、`meastat.py`、`meacheck.py`、`meawrite.py`、`capacity.py`、`retire.py`、`churn.py`；改檔 `card`、`consoleaudit`、`decwrite`、`defs`、`evcheck`、`events`、`evwrite`、`export`、`fold`、`obsrows`、`obswrite`、`params`、`props`、`status`、`writeverbs`；入口 `tools/selfimproving.py`（`measure`、`capacity`）；探針 `tools/probe/selfimproving_measure.py`；`tools/tests/_selfimproving_p3_fixtures.py` 與五個新測試檔、R134 同步站點；`docs/06_quality/SelfImproving_Protocol/params.json`（+2 鍵）；`docs/05_development/SelfImproving_Operations_SOP.md`〈P3 動詞〉；連動＝AgentConsole P1b 差分黃金檔三處副本重產（主控）。
**基準規格**: `docs/03_testing/contracts/TCS-SelfImproving-P3-20261024.md`（Stage-2 凍結 `sha256:f7150d4a…1a170`；AC 23／AT 78；R111～R136；D1～D14；V16～V31）　**上位**: `docs/01_requirements/SelfImproving_PRD.md` v0.10 §1.3、§5.2 FG-G／FG-H、§8.1 P3 出口、§9.1～§9.3、§9.6；研究 SOP；`AutoSDD_Defect_Log.md` DEF-200-568（D12）
**判決檔（逐字）**: 審查者兩次交卷全文在本 session 子代理逐字稿（主控 scratchpad `tasks\a88f296101c1bd1e7.output`；分析腳本在 `scratchpad\qa\`）；修復棒交卷 `scratchpad\si_p3\out_p3fix.txt`；本檔為入庫摘要，數字皆為審查者、修復棒或主控當回合親跑。

### 審查歷程

| 輪 | 判決 | P1／P2／P3／P4 | 處置 |
|----|------|----------------|------|
| 一審 | FAIL | 0／3／3／9 | P2＝三個新測試撞根層鎖（D-01 E501 棘輪 136→159、D-02 測試內字面 DEF 編號、D-03 對整份活文件做缺席斷言）；P3＝D-04 `churn` 群鍵認了未確認 root attr（R118 (c)）、D-05 型別壞 `mea.*` 使 `status`／`export`／`measure`／探針 traceback、D-06 R122 (d) OBS 帳本不可解析仍寫空基線；P4-1＝12 個存活突變對應 13 條沒有 AT 的條文。主控親跑重現三個 P2 ⇒ 修復棒（headless Sonnet，10:47～11:09）：D-01～D-06 全修、補 18 個 AT（78→96）、P4-2／P4-7／P4-8 就地修 |
| 二審 | PASS | 0／0／0／2 | D-01～D-06 全數修好（審查者以自己的重現腳本 E1～E8 重跑：D-04 未確認 root attr 不屬同群 rc 0；D-05 十個變體加十三個加碼變體皆不 traceback、`status`／探針 rc 0、`measure` rc 1 零寫入；D-06 空檔／非 UTF-8／無表頭皆 rc 1 `OBS-LEDGER-UNAVAILABLE` 零寫入、只有表頭 rc 0 基線 `opp=[]`）；18 個新 AT 錨定各恰收一、單跑 18／18 綠，突變重放 R1～R18 全紅；P4-2／P4-7／P4-8 已修；新 P4 兩項＝N-1（勘誤補 `window` null 與 `measure` rc 1 兩個對外行為，已入勘誤一第 12 項）、N-2（`ctx.bad` 全帳本旗標的設計註記與 SOP 逃生口，已入勘誤一第 12 項與 SOP〈P3 動詞〉）。PASS 前提＝主控收尾完成棘輪重釘並 `git add` 新檔 |

### A. FRD 功能規格一致性（AC 23／23；AT 96／96，一審時 78）

| AC-ID | 驗收摘要 | 實作座標 | AT（正／負） | 結論 |
|-------|----------|----------|--------------|------|
| AC-322-1 | 探針輸出 M1～M5、n、窗、指紋；NE 規則 | probe `build_report`；`meastat.metrics`／`_per_prop`／`_m1`／`_m5`／`_median`／`_global_m1` | 2／4 | Pass（AT-322-1-E-4 補 R124 (b)） |
| AC-322-2 | 分區、M5 兩值並列、指紋敏感、不接閘門 | probe `render_text`；`meastat.fingerprint` | 1／2 | Pass |
| AC-322-3 | 提案者隔離 | SOP〈P3 動詞〉〈提案者〉；`p3_meta.sop_p3_problems` | 1／1 | Pass（P4-7 措辭已改） |
| AC-323-1 | 基線→開窗→關窗四值、amend、確定性 | `mea.baseline`／`window`／`owner_of`／`covers`；`meaplan.plan`／`amend_for`；`meawrite.measure`／`plan_amends`；`writeverbs.attr_settle`；`evwrite._append_locked`；`fold._amend` | 7／9 | Pass（E-6～E-9 補 R120 (a)、R121 (b)(e)） |
| AC-323-2 | 回滾提案卡、不自動回滾 | `meawrite._card_text`／`_cards`；`meaplan.rollback_pending` | 1／2 | Pass |
| AC-324-1 | SUSPENDED 重釘（pending 不計不打斷） | `fold._finish`（未改）、`_amend` | 2／2 | Pass（`stop_after_bad` 2／3／4） |
| AC-324-2 | SUSPENDED 下觀察照常、prop-new／revise 拒收 | 同上；`props` | 1／1 | Pass |
| AC-325-1 | 退役兩欄與目標在役 | `retire.form_problems`／`field_codes`／`in_service`／`target_codes`；`props` 呼叫點 | 1／2 | Pass |
| AC-325-2 | 只提議；R 類 `set_maturity` 提示 | `card.R_RETIRE_HINT`；capability 禁 `set_maturity` | 1／1 | Pass |
| AC-326-1 | `CHURN-EXCEEDED`（`churn_max` 2／3） | `churn.group_of`／`cycles`／`codes`；`fold.confirmed_root_causes` | 1／3 | Pass（D-04 修；E-2 補 R128 (b)、E-3 未確認 root attr） |
| AC-326-2 | `CAPABILITY-DELTA-MISSING`（同日／前一日 DEF） | `churn._new_evidence` | 1／2 | Pass（E-2 補 R128 (d)） |
| AC-327-1 | 門檻（恰等於／少一單位）、逐字候選、KB／偏好只報告 | `capacity.evaluate`／`_candidates`／`_memory_axis`／`_kb_axis`／`_prefs_axis` | 2／2 | Pass |
| AC-327-2 | 截斷風險、載入上限恰等於＝無風險 | `capacity.truncation_risk` | 1／2 | Pass（E-2 補 R129 (f)） |
| AC-340-1 | 欄位表、`events.mea`（33 項、REV 4）、載體缺席 NE | `meacheck`；`evcheck.compute`；`params.CHECK_RULES_REV` | 1／4 | Pass（E-3／E-4 補 R113 兩條） |
| AC-340-2 | 冪等、鎖內重算、無人值守、輸入不可用、`--record-check` | `meawrite.measure`／`_check_event`；`meaplan.input_problems`；`mea.obs_ok` | 2／6 | Pass（D-05、D-06 修；E-3～E-6 補） |
| AC-340-3 | `capacity` 動詞契約（rc 0／3） | `capacity.run`；入口 `_capacity` | 1／1 | Pass |
| AC-340-4 | 32 鍵、能力登記 48 鍵（36／8／2／2） | `params.PARAM_SPECS`；`params.json`；登記表 | 2／2 | Pass |
| AC-340-5 | status 15 鍵、export `window`、NE 值 | `status.measure_value`／`build`；`export._proposals`；`meaplan.window_rows`／`export_window` | 2／3 | Pass（E-2 補 R130 (e)；E-3 型別壞欄位 NE） |
| AC-340-6 | 探針確定性、零寫入、單一窗規則、純度 | probe；純度測試 | 1／4 | Pass（E-4 探針對壞欄位 rc 0 NE） |
| AC-340-7 | SOP〈P3 動詞〉 | SOP | 1／1 | Pass（P4-8 rc 1 清單已補） |
| AC-340-8 | 零退化與夾具 | `_selfimproving_p3_fixtures.py`；R134 站點 (a)～(i) | 1／1 | Pass（D-01～D-03 修後根層鎖綠；棘輪紅＝收尾重釘） |
| AC-340-9 | AT 錨定 | `p3_meta.py`（`EXTRA_ATS` 容 78／96 兩態） | 1／1 | Pass |
| AC-340-10 | D12 寫入前四碼 | `consoleaudit.body_guard`；`events.dec_key_problems`；`decwrite`／`obsrows`／`obswrite` 呼叫點 | 1／5 | Pass（V31 真 CLI 重現：修前 rc 0 且 `check` 紅、修後 rc 1 零寫入） |

R 條文逐項對帳（一審讀碼加實跑；二審覆核修法）：R111～R115（23 個動詞、未知動詞 rc 3、欄位表與 `meacheck._SPEC` 逐鍵一致、`check` 33 項、REV 4、九碼齊）；R116～R121（instant、同刻兩側皆不屬、窗序、再現優先、基線確定性）；R122（(d) 一審缺、修復棒補 `obs_ok` 判準）；R123～R126（D-05 使探針 rc 契約在壞欄位下成立）；R127；R128（(a) 一審缺、修復棒共用 `confirmed_root_causes`）；R129～R133；R134 站點 (a)～(h)＋`DROP`（勘誤一 (i)）；R135；R136（V31）。黃金檔差分逐檔結構比對 HEAD：10 檔每檔只有 `buckets`（既有欄）、`proposals.items[].window`、`status.items[].console_pending`、`status.items[].measure`、`capacity.reason`→`export-reads-no-home`，沒有多餘欄位。

### B. Contract 一致性
`params.json` 與 `PARAM_SPECS` 同為 32 鍵、兩新鍵 200／25600、檔內鍵序為位元組序、diff 僅 +2 行；能力登記對真實樹（AT-340-4-2）48 鍵 36／8／2／2；SOP〈P3 動詞〉與 PRD AC-SI-22-3 語意一致（提案者隔離措辭依 P4-7 改為「只對掌舵者與量測者（主控、QA）呈現」）；SOP 內 PowerShell／bash 指令對真 CLI `--help` 語法有效；`尚無該動詞`／`待補`／`TODO` 零命中。新 NE 理由 `mea-events-invalid`（D-05）與 `params-invalid`（⚖7）列入勘誤一第 12、14 列。

### C. Business Invariants（親驗）
`python -X importtime`：`status`、`check`、`export`、`scan`、`card`、`capacity` 各載入 31 個 `selfimproving` 模組、探針 10 個，皆不含十二個非 ro 模組（evwrite、propfiles、writeverbs、decwrite、sandbox、promote、obswrite、meawrite、fetch、research、runner、verify）；`measure` 只寫 `mea.*`（AT-323-2-E-2 加審查者 E5：10 個 promoted PROP 收斂 30 個事件）；`capacity`／探針零寫入（真 repo 前後 porcelain、HEAD、`~/.autosdd` 檔案數 208→208）；`AUTOSDD_UNATTENDED`（`0`、`1`）下 `measure` rc 1 `UNATTENDED-REFUSED` 零寫入；真帳本零寫入；不自動回滾、不寫 DEC。

### D. RTM 覆蓋率確認
AC 23／23；AT 一審 78／78（`--collect-only` 107 個節點、錨定名各恰收 1 個、78 個判定指令單跑皆 rc 0）、二審 96／96（`--collect-only` 125 個節點、18 個新 AT 錨定各恰收一個、單跑 18／18 `1 passed`）；腳本模式七檔各 `Ran N tests … OK`、`__main__` 守衛在檔尾；V29：`_parse_contracts` 得 78 個合約（勘誤一後以 96 現查）、`_unmapped_at_ids` 為空。

### E. 審查證據（當回合親跑；rc 先存變數）
| 項目 | 結果 |
|------|------|
| V17 `check --json`（真 repo ×3） | rc 0；33 項、`events.mea` PASS、`check_rules_rev` 4；牆鐘 2.9／2.7／2.7 s；前後 porcelain 相同 |
| V18 SI 既有十一檔逐檔 `-p no:xdist -o addopts=` | 全 rc 0（check 42、events 48、events_p2 25、export_status 11、p2_meta 12、props 41、decide 18、promote 13、research_scan 46、sandbox 17、verify 23）；`git diff -U0 -- tools/tests/` 的 hunk 逐一對 R134 (a)～(h)，站點外只有 `DROP` 三處（勘誤一 (i)） |
| V19 新檔逐檔 | 一審：measure 21、verb 10、probe 12、capacity_retire 17、p3_meta 10、console_obs 29 全綠；capability 7 綠 1 紅（唯一紅＝既有 `test_AT_240_5_E_2` 內嵌的棘輪下限帶，主控重釘）；二審 measure 25、measure_verb 18、measure_probe 14、capacity_retire 21、p3_meta 10、console_obs 29 全綠；capability 7 綠 1 紅（同一條棘輪下限帶） |
| V20 護欄 | `ruff check` 40 個 `.py` 0 錯；`check_loc_budget --json` rc 0（fold 384 最大，皆 ≤400；入口 314）；`sync_onboarding_baselines --check-snapshot` rc 0；`git diff --check` rc 0；字面 ID 掃描一審命中 `DEF-200-99`（D-02，已改執行期組出）；三個根層鎖修後 8 passed；官方 `run_root_unittests.py` 因 `tools/tests` 檔數下限過期早退——以 `pytest tools/tests` 代替並如實標記，非 SI 失敗全屬棘輪／登記／untracked-import（commit 後消失）與一個偶發（`test_context_budget_guard::EmitToModelSystemMessageTest` 平行下紅、單跑綠） |
| V21 | 32 鍵、200／25600、`params.keys` PASS；AT-340-4-1／4-2 綠 |
| V22（主控＋QA 各自親跑） | 探針 rc 0、兩次逐位元相同、牆鐘約 1 s；M1 NE（no-evaluable-window）n=0、M4 0、M5 main／all NE（sample-below-w-min）、提案數 2、OBS 列數 296、unplaced_rows 14、M2 0.0000 n=34、全域窗 M1 0.0000 n=20、`falsified=None missing=no-evaluable-window`、`fingerprint=sha256:c7ae9570…abeaf1`；修復棒後輸出只差 `head_sha`（出口 (a) 達成） |
| V23 | `capacity --json`／`status --json`／`export --kind status --json` 皆 rc 0（0.1～0.3 s）；status 15 鍵末鍵 `measure`；`capacity.memory_index` read（used 20353／limit 25600、frac 0.795）；export 的 `capacity` 恆 NE `export-reads-no-home`；零寫入 |
| V24／V25 | **未達成（前置未成立）**：真帳本 2 筆 PROP 皆 `proposed`、`window=null`、`mea.*` 0 筆；無 promoted PROP＝無在役工件可退役、無掌舵者指定的退役對象（PRD §8.3 📎 驗收資料殘留） |
| V26 | 主控執行：`measure --record-check` rc 0（`ok measure events=1 props=0`、`check-report appended=true`）；事件帳本 seq 14 `mea.report`（report=check、`falsified=null`、`missing=[no-evaluable-window, sample-below-w-min]`、`fingerprint=sha256:c7ae9570…abeaf1`＝探針指紋）；`check` 的 `events.mea` PASS、overall PASS |
| V27 | SOP 條文語意與 PRD 一致（P4-7、P4-8 已改）；流程摩擦入帳 OBS-SI-298～307（收尾） |
| V28 | Windows 11 `10.0.26300`：AT-340-6-1、AT-327-1-E-2、AT-323-1-E-2 各 1 passed；macOS／Linux **未驗** |
| V29 | 78 個合約（勘誤一後 96）、`unmapped_at_ids` 為空；`-k AT_340_9_` 2 passed |
| V30 | (a) 達成（V22）；(b)(c) 未達成（前置未成立）；(d) 達成（V26：反證條件已檢查並留紀錄，`falsified` 為 null、`missing` 如實列出缺什麼）；FR-SI-22／24／26／27 與 AC-340-1～10 機制面 ✅；FR-SI-23／25 📎 驗收資料殘留；KB 與偏好退役提案 ➖（PRD §9.7 #23 MVP 只印報告）；無「未分類」 |
| V31（D12） | 修前（`git show HEAD:` 四檔遮蔽）：approve 帶 `reason`／`flags`、reject 空理由或含 `\n`、obs-add `symptom` 含 `\n`、obs-close `disposition` 含 `\n` 皆 rc 0 入帳而 `check` 紅（`EVENT-KEY-UNKNOWN`／`EVENT-TYPE`／`ROW-ARITY`／`ROW-MUTATED`）；修後各 rc 1、碼 `EVENT-KEY-UNKNOWN`／`REASON-EMPTY`／`CTRL-CHAR`／`DISPOSITION-INVALID`、輸出帶 `obs-draft:`、兩帳本位元組不變、`check` 仍綠；控制組合法三份 rc 0。DEF-200-568 翻 `fixed@<P3 commit>`（收尾） |
| 突變複核（一審 42 個；二審 18 個（R1～R18，含一審 12 個存活者）全紅、全數還原（42 個變動檔聚合雜湊相同）） | 一審 29 個被 P3 AT 殺、1 個只被 P1 AT 殺（`retire.field_codes` 去 M 類排除→AT-109-3-E-1）、12 個存活（R120 (a)、R121 (e)×2、R121 (b)、R122 (b)(g)、R113×2、R124 (b)、R128 (b)(d)、R129 (f)、R130 (e)）⇒ 修復棒補 AT 各自殺掉（交卷表）；全數還原（21 個候選檔逐檔 SHA256 相同、42 個變動檔聚合雜湊相同） |

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符；一審 D-04～D-06 已修並驗收；P4 七項不阻擋） |
| Contract 一致性 | Pass |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 23／23；AT 96／96） |
| 測試強度（突變） | Pass（一審 42 個：29 殺＋12 存活→修復棒補 AT；二審 18 個全殺） |

**SCG-4 建議**: [通過]（範圍＝Windows 單機；macOS／Linux 未驗；出口 (b)(c) 前置未成立如實標未達成）

### 必修項目
無（P≤2 為零）。**P4（已處置）**：N-1 勘誤一第 12 項；N-2 勘誤一第 12 項設計註記＋SOP〈P3 動詞〉逃生口；P4-2／P4-7／P4-8 修復棒已修；P4-3 勘誤一 R134 (i)；P4-4～P4-6、P4-9 登記為理論洞（勘誤一末段）。**收尾單人窗口（主控）**：tools/lib 掃描檔數下限 98→122、`tools/tests` tmpdir 下限 89→109、`_TREE_FILE_FLOORS['tools/tests']` 84→88、護欄層行數棘輪 R214 第八列與一次性例外名冊精確淨額、shrink-only 桶 `prose`／`guard_self` 依實測重釘、兩站點 guard-total、DEF-200-568 翻 `fixed@<P3 commit>`、OBS-SI-299／300 翻 `fixed@<P3 commit>`。

### 未驗（如實標記）
macOS／Linux 實跑（AT-340-6-1、AT-327-1-E-2、AT-323-1-E-2 的平台替身只在 Windows 實跑）；`ci-gate.ps1` rc 0 與「改前基線 discover 325 OK」為 [他包回報]；V24／V25 前置未成立；官方 `run_root_unittests.py` 全套待主控收尾重釘後實跑；P2b 側碼表與 R136 四碼對表（主控連動：P2b TCS 勘誤一第 12 列與 W12 兩端防線）。

### 流程摩擦（已入帳 OBS-SI-298～301、305）
Developer 官方 runner 早退未退而跑 pytest 子集，三個真紅藏到 QA 才現形；預期紅清單不完整；TCS 條文↔AT 對帳缺口（SA 棒）；R113 不擴 `_CONSUMED` 造成 D-05；TCS 單行 R 條文過長逼分段讀；審查期間 HEAD 移動（P2b 兩個 commit）。審查者用量：一審約 0.6M、二審 約 0.17M；修復棒約 0.3M。
