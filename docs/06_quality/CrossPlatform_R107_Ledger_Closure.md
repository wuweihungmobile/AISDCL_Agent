# CrossPlatform R107 Ledger Closure（結案輪逐筆結案證據）

本檔性質：R107 結案輪（結案包 #1，單線窗口）逐筆結案證據。量測於 2026-08-27，Windows 11 真機、`.venv` python。每筆一節：驗證指令逐字、rc、輸出關鍵行、結案判定理由。主帳本（`AutoSDD_Defect_Log.md`）各列狀態欄只留短句＋指向本檔的指針，長證據一律住本檔。

結案前基線：`check_defect_log_crossref.py --unresolved-count` → 未結列 **84**／全部 158 列（warn=86 fail=98），外部阻塞軌 7 筆。

### DEF-101-739

- 驗證①：`& D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe AutoClaude\tools\check_loc_budget.py --json` → **rc=0**；輸出 `"policy_version": "v3-assertion-only+sd08-special"`（ADR-XPLAT-013 assertion-only 計價已生效：`guard_taxonomy` 逐檔分列 narrative／assertion／blank，`narrative_total=19023` 不再計入 assertion 預算 ⇒ 本列 (c)「寫理由本身要付預算」已解）。另 `special_warn_band` 顯示 `../tools/run_root_unittests.py` 現值 759／759（棘輪已隨演進重釘，非凍結在 754）。
- 驗證②：Read `tools/run_root_unittests.py` — `_THIRD_PARTY_PREREQS` 存在於 :106-111（四組 (import 名, pip 名)），:398 作為 `prereqs` 預設參數接進 fail-fast 檢查、:492 失敗訊息點名本清單；檔頭 :26 自述「R68 補第四層 `_THIRD_PARTY_PREREQS`」⇒ 本列 (a) 被放棄的 fail-fast 已補回。
- 判定：解鎖條件為「(i)(ii) 任一落地並附 rc 實測」，實況 (i)(ii) **兩者皆已落地**（(i)=fail-fast 補回；(ii)=計價改 assertion-only，比「非註解行」更精準的裁決）→ **fixed@R107**。

### DEF-101-769

- 環境：Windows 11 真機，`$PSVersionTable.PSVersion` → **7.6.5**（當回合實測）。
- 驗證①：`python -m unittest tools.tests.test_dev_start.TestResolveNativeExecutableOnRealPwsh7 -v`（PYTHONPATH=tools/tests，同目錄 helper 需要）→ **Ran 3 tests, OK, rc=0，零 skip**。三支＝載具自證「真的是 PS 7 在跑」＋本體「PS 7 on Windows 仍照 PATHEXT 過濾」＋正控「Windows 分支是活的」⇒ (a) 的 `Major >= 6` 分支已有**真 pwsh 行程**證據，非 harness 副本。
- 驗證②：`python -m unittest tools.tests.test_ps51_compat -v` → **Ran 10 tests, OK, rc=0**；輸出逐行清點 `... ok`=10、`skipped`=0 ⇒ R99 書記複驗記載「mac 上 3 支 [WINDOWS-NATIVE-ONLY] skip」的那幾支（skip 標籤在 `test_ps51_compat.py:470`）本機**真的執行非 skip** ⇒ (b) 的 5.1 行為鎖（含 Legacy argv 重組例外面）已在原生 powershell.exe 5.1 上真跑。
- 判定：帳本列「殘留兩項仍需真 Windows」的兩項皆已在真 Windows 補齊執行級證據 → **fixed@R107**。

### DEF-101-876

- 性質：R77 收輪「三包未執行＋四方複審零次」的流程事實列。三個半邊當回合逐一親驗：
  - 四方複審半邊：`CrossPlatform_R78_Review.md:31` 逐字「產出：**30 筆 finding（9 blocking）**」＝R77 積欠的四方複審已由 R78 補跑。
  - skipped 治理半邊：`tools/lib/skip_tag_policy.py` 存在（Glob 命中；同回合 `check_loc_budget --json` 的 guard_taxonomy 亦列出該檔）＝R79~R84 skip 治理已落地。
  - 承接稽核半邊：當回合 `check_defect_log_crossref.py` rc=0 輸出逐字含「全部未結案列的承接輪次皆 ≥ 當前輪 R100 或已載明改派（硬規則②）」＝承接稽核已由孤兒判準機械覆蓋。
- 殘餘實質＝依賴債（三包之一），與 `DEF-101-060`（18 條相依無上限，open、改派 R82）同根因——當回合 Read 帳本 :75 確認 060 仍 open 且為該債唯一活載體。
- 判定：同一筆債不應被計兩次（先例＝DEF-101-217 併入 886 的體例）→ **closed-by-decision**（殘餘由 DEF-101-060 單一載體承接）。

### DEF-200-053

- 驗證①（Read `tools/lib/ledger_rotation.py`，當回合）：本列分流欄指定的治本「天花板由寫死常數改為『現查值 ≤ 史料末元素』」已落地——
  - `ratchet_history_problems()`（:247-277）三向判準：序列非空／單調不增（任一段上升即紅並指名）／**末元素 == 現行常數**（:273-276，改常數不追史料即紅）；
  - 三常數皆已入史料：`OVERSIZE_ROW_CEILING_HISTORY`（:43，末元素 45）、`OVERSIZE_ROW_EXCESS_CEILING_HISTORY`（:58-62，末元素 37058）、`UNPINNED_HANDOVER_CEILING_HISTORY`（:71，末元素 0）；
  - 前綴封印成對執行：`ratchet_direction_problems()`（:280-309）對每條史料跑 `sealed_prefix_problems`（:307-308）＋整表 `seal_table_problems()`（:309），防史料被無聲改寫／砍短。
- 驗證②：改列後 `check_defect_log_crossref.py` → **rc=0**（當回合實測；判準④＋方向鎖＋封印全綠。過程實錄：第一版狀態欄 792 bytes 被判準④ 當場擋下並拒絕加豁免＝鎖有牙，壓短至 ≤700 後轉綠；本列瘦身跌破 700 後豁免自動過期，動態下修無需手動改常數）。
- 判定：立案時「棘輪實測餘裕皆 0 ⇒ 加一個位元組即紅」的死結已由「同一次變更內縮回等量」出口＋shrink-only 史料機制化解（本輪多列瘦身即走此路徑，History 追加註記可證機制活著）→ **fixed@R107**。

### DEF-200-190

- 背景：R100 曾標 fixed 被複審退回，理由＝「整檔全跑」非針對性驗證。本次改為**逐項對映**（行號皆當回合 Read 實查，與分類包線索略有漂移、以實讀為準）。
- 驗證：`python -m pytest tools/tests/test_claim_provenance_r86.py -q` → **40 passed, 20 subtests passed, rc=0**。
- 本列訴求「無量測時間戳的水位數字不可查證＝等於未量測」→ 具名測試逐項對映：
  - 事故形狀本身：`test_a_four_hour_old_self_quoted_stamp_still_gets_flagged`（`tools/tests/test_claim_provenance_r86.py:376`）——貼四小時前的「量測於」**不是**豁免，仍命中且訊息帶 age（:381 斷言 age_s > 4h−60s）；
  - 逃生口紅綠自證：`test_a_stamp_that_really_is_fresh_is_the_silent_case`（:390）——真的剛量（0.5 分鐘）→ 回空＝本列分流欄指定的逃生口「把量測時間戳一起貼出來」已落地，且是**算術驗證**（算 age）而非「在場即抑制」（:357 class docstring 記載規格版方向被否決權複審翻正）；
  - 無時間戳讀數不放行：`test_an_unanchorable_reading_is_its_own_class_not_silently_dropped`（:505）——錨不到的讀數判 `unanchored` 自成一類可數、`age_s=None` 不得捏造；
  - 繞過面：全角 `％` 不靜音（:474）、軸-值距離窗覆蓋真實散文 p90（:480）；訊息教材面 `test_it_tells_you_to_rerun_not_merely_to_paste_a_timestamp`（:413）——訊息必含「重跑」「--pace」「算 age」。
- 設計偏離（如實記載）：TTL 未沿用本列分流欄建議的 `QUOTA_CACHE_TTL_SECONDS`，而是 per-axis 導出式 `PACE_TTL_S`（`check_claim_provenance.py:322`＝`3600/rate` 期望漂移 1pp；:413 逐軸取用；`test_the_boundary_is_the_axis_own_measured_ttl` :398 釘住「單一全域門檻有 35% 慢軸假紅」）⇒ **更嚴格的取代**，非缺漏。
- 判定：訴求逐項有具名測試對應、非整檔籠統宣稱 → **fixed@R107**。

### DEF-200-157

- 驗證①：`python -m unittest tools.tests.test_quota_policy` → **Ran 241 tests, OK, rc=0**（stderr 僅兩則「遲滯已降級」環境提示，非 failure）。
- 驗證②（Read 當回合）：立案訴求「cap 無模型維度 ⇒ 切小模型出口機制上不存在」的兩半皆已閉合——
  - 判定層（R98）：`tools/lib/quota_policy.py:574-579` `_model_active()`（scope_model↔active_model casefold 相等才命中，任一邊缺席不算命中＝「量不到≠量到零」方向）＋ :582-587 `_in_cap_gate()`（`MODEL_SCOPED_KINDS` 軸只有命中本次模型才進 cap 聚合）＋ :597-599 `decide(..., active_model=...)`。
  - 接線層（R105，DEF-200-202 fixed@R105）：`tools/lib/quota_gate.py:837-839` `quota_gate(..., active_model=None)` 簽名＋ :830-836 註解記載 hook 主檔掃逐字稿取 model 經 `model_family()` 正規化後傳入＋ :885 `decide(state, now, policy, active_model=active_model)` 真的接到判定入口。
- 判定：`weekly_scoped` 這種 model-scoped 桶現已依 active_model 決定是否進 cap 聚合 ⇒「切小模型」的出口機制上存在了；立案時要求的 PRD 層裁決已由 R98（機制設計）＋R105（接電）兌現 → **fixed@R107**。

### DEF-200-023

- 訴求：「撞線→轉續航→探測／重排」最後一哩從未真跑過；分流欄指定「以受控注入把撞線餵給 `--sentinel-tick`，端到端跑一次並留憑證」。本回合照做（Windows 11 真機、零 API 呼叫）：
- 受控注入材料（scratchpad）：合成逐字稿 `synth_transcript_r107def023.jsonl`（一行 `type=assistant`＋`model=<synthetic>`＋文字 `You've hit your session limit · resets 11:59pm (Asia/Taipei)`、timestamp=2026-08-27T16:00:00Z、無後續成功回應 ⇒ `unhandled_limit_event` 判未處理）＋合成任務書 `synth_plan_r107def023.md`（合法 relay 狀態塊：11 個 `RELAY_REQUIRED` 鍵、schema=autosdd.resume/1、state=armed、reset_source=operator）。
- 執行：`python tools\session_resume_planner.py --sentinel-tick --plan <合成任務書> --task-name AutoSDD_Sentinel_R107SYNTH` → **rc=0**，stdout 逐字：「哨兵判定 arm_reset：偵測到未處理的撞線；觀測 reset=2026-08-28 23:59:00+08:00 尚未到 ⇒ 要求排程器改在那個時刻醒」。
- 憑證（resume log 實際行，住 `log_path` 指定檔）：
  - `{"event": "sentinel_woken", "at": "2026-08-28T00:08:42+08:00"}`（開場留痕，%TEMP% 那份）
  - `{"action": "arm_reset", ..., "event": "sentinel_decided", "at": "2026-08-28T00:08:45+08:00"}`
  - `{"action": "arm_reset", "fire_at": "2026-08-29T00:01:00+08:00", "credential": "2026/8/29 上午 12:01:00", "event": "sentinel_rearmed", "at": "2026-08-28T00:08:46+08:00"}`——credential＝schtasks 回報的 **NextRunTime 值**（reset 23:59＋skew 120s）。
  - 順手驗證的另一半：`sentinel_armed_drift_healed`（patrol_housekeeping 對「狀態塊說 armed 但排程器查無工作」的漂移自癒）也真的觸發並取回憑證。
- 任務書被寫回：state=armed→**waiting**、reset_at=2026-08-28T23:59:00+08:00、reset_source=**transcript-verbatim**、next_run_time=2026/8/29 上午 12:01:00 ⇒「撞線→判定→轉續航排程→取證」全鏈走通。
- 清理（配方要求）：`Get-ScheduledTask -TaskName 'AutoSDD_Sentinel_R107SYNTH'` 先確認存在（NextRunTime=2026/8/29 上午 12:01:00），`Unregister-ScheduledTask -Confirm:$false` 後複查回「No MSFT_ScheduledTask objects found」＝已刪除。
- 判定：立案時 `probed`／`resumed`／`arm_reset` 合計 0 命中的「最後一哩」已有 arm_reset 全鏈實跑憑證（probe 分支刻意不跑：它會花真額度做探測，且其機器與 `--resume-tick` 共用、已有既有覆蓋）→ **fixed@R107**。

### DEF-200-075

- 三半邊現況（當回合核對）：②`ONBOARDING.md:226` 已修@R100、③`[DEBT]` 承接輪次已由 R90 平台條件機制解決（原列狀態欄自載）；餘 ①mac 側 AutoClaude 樹 115 支欠債型 skip——**darwin 執行面量測值，Windows 真機結構上量不到也修不了** ⇒ 屬 E 類外部阻塞（阻塞源＝macOS 實機），非本機可修的 A 類債。
- 動作：外部阻塞軌 `AutoSDD_External_Blocked_Log.md` 總表加一列（DEF-200-075｜`其他-macOS實機（darwin執行面量測值，Windows結構上量不到也修不了）`｜2026-08-27｜解鎖條件＝回 mac 真機後第一動作重量 AutoClaude 樹 skip census、macos-compat-ci 長期紅不可依賴｜2026-08-27）；主帳本該列收斂為指向本表的索引。
- 形態說明（照配方預查）：配方原示首詞 `routed`，但當回合 Read `tools/lib/ledger_closing_guards.py::external_blocked_log_problems()`（:235-239）確認交叉鎖判 `def_id in main_unresolved_ids` 而 `routed` ∈ 未結分類 ⇒ routed 首詞結構上必觸發交叉鎖 fail。故照既有 7 筆的現成範本（DEF-200-147 列）採 `closed-by-decision｜移入外部阻塞軌…` 形態。
- 驗證：`check_defect_log_crossref.py` → **rc=0**，輸出「外部阻塞軌…**8 筆**」（7→8，含 DEF-200-075）、交叉鎖綠、具名阻塞源枚舉綠（`其他-<具體理由>` 形態 fullmatch）。

### DEF-200-128

- 訴求：R89 交棒書「待驗清單」漏 6 筆 ⇒ 治本「待驗清單須附可重跑腳本」。採等效兌現方案：原失效模式（改派出口靜默過期、靠人工清單核對）已由機械判準覆蓋——人工清單漏列的列會被判準自己抓到，毋須第二份同知識的腳本。
- 驗證①（Read 當回合）：`tools/tests/test_check_defect_log_crossref.py:3145` `_REASSIGN_FRESHNESS_FROM = 84`（發現輪 ≥84 的列，「改派」出口輪號 < 當前輪即**阻斷**）＋ :3148 `_EXPIRED_REASSIGN_LEGACY_CENSUS = 25`／:3150 `_UNPARSEABLE_REASSIGN_CENSUS = 3`（生效輪外存量走 shrink-only 相等棘輪，只准變小）＋ :3153 `_reassign_escape_rows()` 三堆分類純函式。
- 驗證②：`python -m pytest tools/tests/test_check_defect_log_crossref.py -q` → **241 passed, 46 subtests passed, rc=0**。
  - 過程實錄（誠實記載）：第一次跑出 2 failed，皆為本包自身動作的連帶而非本列判準失效——(a) `governance_docs.py:321` 註解「R107」超前帳本時鐘 R100（round-label 鎖抓到，照該鎖訊息的正解加 `round-label-ok` 豁免）；(b) 多列瘦身使超標總量 37058→36796，零餘裕相等自檢（`test_the_real_ledger_baselines_are_exact_not_padded`）要求下修——**兩道鎖都有牙**。依取值紀律重釘：`defect_ledger_index.py` `OVERSIZE_ROW_EXCESS_CEILING` 37058→**36796**（收緊）；`ledger_rotation.py` 史料尾端追加 36796、封印延長納入 37058、`_SEAL_TOTAL_MIN_LEN` 35→36、`_SEAL_TABLE_SHA256` 重釘為當回合 `seal_table_digest()` 實測值 `e72801a4b9a300cf`。重跑即全綠。
- 判定：既有機制等效兌現、避免第二份同知識 → **closed-by-decision**。

## 收尾自檢（結案包 #1）

- `check_defect_log_crossref.py`（完整檢查）→ **rc=0**；`--unresolved-count` → 未結列 **84 → 75**（本包結掉 9 列：739／769／876／053／190／157／023／128 共 8 筆＋075 移軌 1 筆）；外部阻塞軌 **7 → 8** 筆。
- 棘輪重釘的消費面複驗：`pytest tools/tests/test_check_defect_log_crossref.py` → 241 passed rc=0；`pytest tools/tests/test_archive_defect_log.py tools/tests/test_adr_xplat001_c1c2_lock.py` → **331 passed, 465 subtests passed, rc=0**。
- 本包連帶改動（非帳本）：`tools/lib/governance_docs.py`（登記本檔進 `_GOVERNANCE_DOCS`＋round-label 豁免）；`tools/lib/defect_ledger_index.py`／`tools/lib/ledger_rotation.py`（excess 棘輪 37058→36796 重釘五件套，全屬收緊方向）。
- 合成材料清理：schtasks 工作 `AutoSDD_Sentinel_R107SYNTH` 已 Unregister 並複查確認不存在；合成任務書／逐字稿／log 留在 session scratchpad（session 結束自然回收）。

## 結案包 #2／#3／needs-user／收尾複審 逐列處置對照（收尾書記落列，2026-08-28）

> 本節＝主帳本各結案列狀態欄指針的落點（列上只留首詞＋指針，敘事全數住這裡）；亦即
> `DEF-200-106` 的結案憑證本體。四包原始回報住 session 暫存（已蒸發），素材（各包
> notesForScribe）由本節逐字承接；收尾複審四鏡判決全文＝`CrossPlatform_R107_Review.md`。

### 結案包 #2（文件級）

- **DEF-200-215**（fixed@R107）：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 新增〈🧾 派工紀律〉節（:220-233）第 1 條＝任務書內每一條驗收指令派工前由主控親跑一次，或只准引用 repo 具名腳本（如 `python tools/run_root_unittests.py`）；未親跑過的驗收指令不得寫進任務書（引 unittest discover 跑不起來、兩包各撞實例）。驗證＝Select-String '驗收指令' 命中 :221/:223。
- **DEF-200-216**（fixed@R107）：同節第 2 條＝外部端點輪詢派工必須明定間隔下限且 ≥ 該端點快取 TTL（低於 TTL 只是重讀快取非新觀測，卻照樣耗請求額度；引 15 秒輪詢→真 429→cap=0 約 3 分鐘實案）；第 3 條＝自造事件（自家探針打出的 429/halt）只證線路接通，不得寫成「活體驗證」——判準＝非自家流量引發的真實外部事件（方向同 DEF-200-197）。驗證＝Select-String '間隔下限' :226/:227、'活體驗證' :230-232。
- **DEF-200-125**（fixed@R107，劃界結案）：2026-08-28 單發真打 `/api/oauth/usage`（走 token_detail→fetch_usage 既有入口，http 200）。limits[] 三項（session／weekly_all／weekly_scoped）鍵集合逐字完全一致＝`['group','is_active','kind','percent','resets_at','scope','severity']`；status／state／allowed_warning／rejected 等 status 類鍵於 limits[] 與頂層桶（extra_usage/five_hour/nimbus_quill/seven_day/spend）全部 0 命中 ⇒ 本源結構上無此鍵；PRD 所引 `:1529` 的 status 枚舉屬回應標頭通道、與本源不同源。🔴 立案行號（:79/:1372/:1529）已漂移，現行座標＝PRD :2436 紅線 7。bucket_readings 帶出面已完整、零代碼改動；test_quota_policy 241 passed。附帶觀測：頂層鍵本次實測 18 個（快取史料 17），drift 判準只記錄不阻斷。

### PRD v2.1.4 落款包

- **DEF-200-141**（fixed@R107）：四站點「待四方複審」改生效語（PRD :9 版本表／:241 升格依據標題／:250 §6 整合句／:2430 紅線 1；殘留唯 :10＝v2.1.5 合法站點）；:9 與 :246 過期 cap=4 改 `Policy.degraded_cap` 現查指針（源碼實值 2 親驗 quota_policy.py:232）；§6 裁決落字＝kill-switch 鍵移除、未文件化端點遙測恆啟用、防護＝紅線 1 四條件（現 :1736-1740），旗標全庫 Grep 僅文件 3 處零程式消費端。程序事實＝§12 憑證條（原 :2263）曾先行生效，本次落款後瑕疵消失。cap=4 殘留逐筆交代：唯一字面殘留 :344 已加落款注、:14 的「實查出廠 4」已由收尾書記補同款落款注。機械驗證＝test_quota_policy Ran 241 OK＋test_context_budget_guard Ran 466 OK＋crossref rc=0。
- **DEF-200-142**（fixed@R107）：三修復（converge 錨點免除 quota_pace.py:345-348／pace_index 同檔 :213／model_hint_line quota_messages.py:267-272）QA 鏡逐字驗實；`CrossPlatform_R95_Pace_Actuator_Evidence.md`:66-69 已改 R107 生效標注（含 Review.md 紀錄指針）。
- **DEF-200-157**（補注）：§4.2.3 補完備性句（現 :474）隨 v2.1.4 批次於 R107 複審通過（紀錄＝Review.md）；結案理由立足 R98（MODEL_SCOPED_KINDS/_in_cap_gate）＋R105（active_model 接線），不依賴本次複審——結案時刻早於落款 11 小時的表觀矛盾由此消除（QA-F4）。
- **未落地承接（→ DEF-200-230）**：紅線 1 條件 (b) 單站點回歸鎖——現況不變式成立（全庫 .py 完整 URL 字面恰 1 命中＝quota_meter.py:72），落點 test_quota_policy.py 須同窗付 lock:743 釘值 3055 重釘稅（鐵律七，單人窗口）。

### 結案包 #3（代碼級，共用一次護欄棘輪重釘）

- **DEF-200-166**（fixed@R107）：`doc_guard_total_problems()` 由標記行數改判相異檔數（sites 收 set[rel]、門檻 len(sites)<min_sites，[未登記] 訊息明寫同檔兩行不算兩站點）；永久紅綠＝`test_two_marks_in_one_file_are_still_one_site`；真文件紅面訊息實測「[未登記] 帶 guard-total:R106 標記的相異檔只有 1 份」。
- **DEF-200-171**（fixed@R107）：`sc10_coverage_table_has_a_row_for_the_current_round()` 補內容禁詞判準（`_SC10_DRAFT_TOKENS` 三則草稿警語；只判當前輪列、史料輪不判）；第二支注入 `_taint_current_round_row` 走既有零串音框架（Ran 10 OK，注入恰只紅 SC-10）；連帶依 R73 判例「改指稱不引文」訂正 ADR-XPLAT-002 §6 R100 列的逐字引述。
- **DEF-200-225**（fixed@R107）：`test_quota_policy.py::TestM8bCacheHomeStaysInSync::test_the_cache_dir_env_literal_matches_verbatim_in_both_homes` 逐字 assertEqual 兩家 CACHE_DIR_ENV（tools/lib/quota_meter.py:161／AutoClaude file_quota_meter.py:59），抽不到字面亦紅；紅綠自證通過；未新增鎖檔（併入既有檔，符合 _FROZEN_GUARD_FILE_COUNT 紀律）。
- **DEF-101-950**（fixed@R107，含配方前提訂正）：測試側政策值自 R79 已現查 .gitattributes（親驗，非本輪新做）；真缺口＝hook 側 `check_ps1_encoding.py` 的 PS_SUFFIXES 無人對帳 ⇒ 新增 `test_platform_neutral_paths.py::TestWorktreeEolPolicyIsMeasuredFromGitattributes::test_the_ps1_hooks_private_crlf_targets_match_the_declaration` 釘住 hook 射程逐字對 .gitattributes eol=crlf；hook 位元組字面依 R80 S5-09 裁決保留；hook 行為不變（AutoClaude pytest -k ps1 → 21 passed）。
- **DEF-200-201**（fixed@R107）：`quota_pace.py` explain() 顯示片段改自帶語意——pace_index 標明「分母＝短窗自身流逝比，與本窗餘裕不同軸、不可互抵」；ceiling 已可經 AUTOSDD_QUOTA_PACE_CEILING 調 ⇒ 保留 index；`--pace` 實測第三行為證。
- **護欄層記帳**：R107 稽核列 (89125, 89124, -1)；到期義務 (107,630) 兌現＋重新武裝 (109,610)；prefix 75→76→（B2/B3 訂正後）SHA 重釘 abd0dc217e2b…、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 ("R107","6d3be18839b6","b42d19e1db20","DEF-200-166") 與 ("R107","b42d19e1db20","abd0dc217e2b","DEF-200-141")。淨額 ≤0 靠 8 段散文搬遷 `CrossPlatform_Guard_Line_History.md`〈站點級守衛四種罩法 WHY〉至〈SC-2/3/5 射程收窄 WHY〉八節（原文全文保全、知識零刪除；僅指稱詞隨載體必要調整）——量測面內的減法，不是總量的減法（結構缺口既有載體＝DEF-200-211／ADR-XPLAT-013 Phase 2）。

### needs-user 兩筆（掌舵者 2026-08-28 在場裁決）

- **DEF-101-338**（closed-by-decision@R107）：掌舵者核准（原話「核准 git rm（推薦）」）後 git rm 凍結版 v0.01 四支測試假 SHA drift 殘留檔（COMMIT-sha-3rd/high/low/testsha-001.yaml；真 SHA 形態 COMMIT-769eea4e3f66.yaml 刻意保留，屬 DEF-101-329 族）。R60 解鎖條件已答：現行 test_drift_monitor.py 全用 tmp_path（34 處實查、零 build/reports 引用），寫檔根因不存在，4 檔為歷史殘留 artifact。凍結版例外存證＝`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md`「凍結基線例外」節（比照 R44/45/46 八欄格式；純刪測試產物、不計入破例回補次數 3）。驗證＝git status 4 列 D、v0.01 檔級 10 passed rc=0、凍結軌全套 1478 passed/4 skipped rc=0。
- **DEF-101-559**（closed-by-decision@R107，routed→closed）：掌舵者條件式裁決（原話「是否以後會用, 最佳化是否該升? 若真的都用不到, 當然不升」），查證落「會用」分支＝該升：hub-push.yml 檔頭 L7-8 明文供下游複製到 Hub repo 真實執行、REGISTRY-SPEC.md L11/62/110/206/217 定為 D-30.10 驗證 pipeline。落地＝LATEST hub-push.yml 8 站點升版（checkout v4→v5 ×4、setup-python v5→v6 ×3、upload-artifact v4→v6 ×1）＋檔頭決策註記；`tools/check_gha_action_versions.py` `_NESTED_DISCLOSED_GENERATION` 改兩世代聯集（誠實劃界：聯集級登記分辨不出單檔版本，凍結區單檔翻版不轉紅，該面由 Copy-on-Evolve 與人工複審守）；EVOLUTION_LOG.md 補 ADR-XPLAT-011 §4 條件② blob 分裂記錄；ADR-XPLAT-011 :70/:79 已由收尾書記補日期化訂正注。ADR §4 條件①②已履行、③不適用。驗證＝check_gha rc=0＋快照一致訊息實印、unittest 53 OK。🔴「30 版同一 blob」在 index 現仍單顆——分裂在收尾 commit 後才 materialize，屆時 `git ls-files -s` 預期恰 2 顆（SD 鏡 F4 建議機械化為斷言，交棒 R108 候選）。

### 收尾複審 blocking 兌現＋承接列

- **B1**＝`CrossPlatform_R107_Review.md` 落盤＋五落款站點補紀錄指針（PRD :9/:241/:250/:2430＋R95 Evidence）。**B2**＝9 處「原文一字不漏」改誠實措辭（Guard_Line_History 八節標頭＋lock 稽核列）＋`_REPIN_LOG_HISTORY_SHA256` 重釘（b42d19e1db20→abd0dc217e2b）＋rewrite ledger 追加列（錨 DEF-200-141）。**B3**＝3 處「§21~§28」改具名節標題起訖；guard-total:R107 標記與「89125 → 89124（-1）」三元組不動。驗證＝lock 全模組 Ran 159 OK、GLC_LINES=89124 持平、鎖檔行數 6282 持平。
- **DEF-200-106**（fixed@R107）：治本訴求「需專輪處理」由本結案輪兌現——84 筆全分類（快照固化於 `AutoSDD_TechDebt_Paydown_Playbook.md` 附錄 A）、未結 84→64、外部軌 7→8、可重複使用計畫＝該 Playbook；本節即逐列處置對照憑證。
- **承接列**：`DEF-200-230`（紅線 1 單站點回歸鎖，重釘稅移交下輪單人窗口）／`DEF-200-231`（自動化續跑鏈三缺陷：planner 時刻 fallback／headless 許可層／哨兵存活監測，取證＝R107_RESUME.md 根因節）。
- 帳本量測（收尾書記當回合）：`--unresolved-count` 75→**64**／160 列（13 結案＋2 新增承接）；crossref 完整 rc=0；OVERSIZE 五件套重釘 36796→**36440**（−356，338 瘦身 −381／559 結案語 +25，membership 45 列不變）。
