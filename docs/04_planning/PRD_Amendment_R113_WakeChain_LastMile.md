# PRD 修憲草案 — 喚醒鏈最後一哩（無頭續跑收尾閉環）

> **Status：Adopted（掌舵者 2026-08-31 落款生效）**——R114 四方複審收斂（紀錄＝
> `docs/06_quality/CrossPlatform_R114_WakeChain_Review.md` §2）後，掌舵者以互動裁決落款；
> 落款載體＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.13 列。
> 批次序＝v2.1.10（配速）→ v2.1.11（ADR-XPLAT-014 五歧異）→ v2.1.12（R112 喚醒鏈）→ **本批 v2.1.13**；
> 依 R110 判例「未生效修憲不疊層」：v2.1.10~12 仍 Proposed、**不因本批落款而生效**。R112 案為本案
> 前提語意的三節（§5-2/§3-3/§3-4）之設計內容已由本案 §3 常數化承接——實作以本案為唯一施工圖。
> 本檔＝R113 PRD 設計包產出（一人分飾 Architect／SA／SD／QA，掌舵者 2026-08-31 直接指令）。
> 程式座標凡標行號者＝2026-08-31 現查快照，動工前一律現查。
> **2026-08-31 R114 四方複審後修訂；同日落款，G1~G4 實作批解凍**。

---

## §0 Status 與載體

- **帳本載體三列**（`docs/06_quality/AutoSDD_Defect_Log.md`）：DEF-200-234（主控死亡時背景活體無主統籌）／DEF-200-235（跨 reset 等待 Monitor 到期無人接手→headless 接力）／DEF-200-236（halt 期通知投遞失敗不重投）。三列解鎖條件**逐列各異**：234 原指向 ADR-XPLAT-014 §4＋巡邏 tick 分支；235 原指向 R112 案 §5-2/§3-3；236 原指向 R112 案 §3-4。本案落款後：234 的解鎖條件改寫為「ADR-XPLAT-014 §4 **與** R112＋R113 兩案」**併列**（保留 ADR 指向，不得靜默覆蓋）；235/236 改指向「R112＋R113 兩案設計落地」。
- **R114 四方複審（Arch REJECT／SA AWC／SD AWC／QA REJECT，13 blocking）已全數修訂納入**（2026-08-31）。
- **與 R112 案（`PRD_Amendment_R112_WakeChain.md`，Proposed）的關係＝實戰修訂，不是推翻**：R112 是撞線前設計、本案是 2026-08-30 深夜實戰全通後對「最後一哩」的收斂。逐節承接：R112 §3-3（接力鏈雙煞車）→本案 §3(c) 給定可量測常數與狀態機表；R112 §3-4（補投佇列）→原樣保留，本案 §3(b) 補「可見性」的正面（handback 檔）；R112 §3-5（heal_latched）→原樣承接，本案 §3(d) 補「fire 後重掛」缺的另一半；R112 批2（DEF-200-231②＝acceptEdits argv）→本案 §3(a) 擴成三層白名單。R112 §5-2（主控復活語意＝統籌權移交 headless 接力窗口）為本案全部設計的前提語意，不重述。

## §1 實戰事件摘要（證據座標＝`docs/06_quality/CrossPlatform_R113_Ledger_Closure.md` §8，不重抄）

2026-08-30 23:40 主控撞 429 死亡 → mac 哨兵「偵測→武裝→00:10 reset 喚醒→無頭續跑 20 分鐘」**四段全通（mac 首次實戰全通）**，敗在最後一哩四缺口：

| # | 缺口 | 實戰表徵 | 承接節 |
|---|---|---|---|
| G1 | 無頭窗口權限姿態 | Write 新檔（含 scratchpad 任務書）全被無人核准權限牆擋，只能做既核准過的編輯，收不了尾 | §3(a) |
| G2 | 交接可見性 | 交接總結只在逐字稿＋一則推播；使用者終端零回饋，自陳「被消耗 9% 且不知情」 | §3(b) |
| G3 | 無配額內自循環 | 續跑單回合即止；剩餘工作明明有額度也不繼續 | §3(c) |
| G4 | 哨兵不自癒 | fire 一次後 launchd 工作消失（00:32 bootout 後無重掛）；08-31 上午 armed-stamp 與 launchctl 脫鉤＝喚醒鏈斷線，`--pace` 自己報警 | §3(d) |

## §2 需求（SA；掌舵者原文提煉 → 可驗收條目）

| REQ | 掌舵者原文提煉 | 承接（R112 對應） |
|---|---|---|
| REQ-L1 | usage 接近滿水位即武裝喚醒——**已存在**，本案只做誠實劃界不重做（「不重做」射程**只含 §3(e)**，不含 §3(d) 新做的 fire 後重掛——那一半歸 REQ-L5） | R112 REQ-W4 |
| REQ-L2 | reset 後自動續跑不需人類——續跑窗口必須**收得了尾**（寫得了任務書／證據檔／交接檔） | R112 REQ-W1(c) 擴 |
| REQ-L3 | 續跑必須**可見＋受統籌**——人回來的第一個終端畫面就看得到「誰、何時、做了什麼、燒了多少」 | R112 REQ-W2／W7 |
| REQ-L4 | 不得空轉浪費——有額度且有未完項就繼續，零推進或額度收緊就停，全程留稽核痕跡 | R112 REQ-W6＋§3-3 |
| REQ-L5 | 喚醒鏈自癒——fire／收窗後必須**自動回到武裝態**、失效可偵測（§3(d)） | R112 REQ-W1(e)＋§3-5 |

橫切約束（R112 REQ-W5 原樣）：每條演算法落程式機制、判準收在值域，不得靠模型判斷。

## §3 設計（Architect/SD；每條＝可實作判準／狀態機／常數＋落點）

### §3(a) 無頭窗口權限姿態：三層白名單（G1）

**設計**：權限＝「收窄的放行」，不是關護欄。三層：

| 層 | 內容 | 載體 |
|---|---|---|
| L1 可寫 | ① 任務書所在暫存目錄（既有 `--add-dir` 已帶）② 持久交接目錄 `~/.autosdd/handback/`（§3(b)）③ 具名證據檔（當輪 `docs/06_quality/CrossPlatform_R*_*.md` glob）④ repo 工作樹既有檔編輯（acceptEdits 語意） | spawn argv `--permission-mode acceptEdits` [需核對] ＋ 無頭專屬 settings 的 `permissions.allow`／`permissions.additionalDirectories` |
| L2 可跑 | 具名驗證腳本**唯讀清單**：`session_resume_planner.py --pace`／`--check`、`check_defect_log_crossref.py`、`python -m unittest`／`pytest`（唯讀跑）、`git status`／`diff`／`log` | 同檔 `permissions.allow` 的 `Bash(<前綴>*)`＋`PowerShell(<前綴>*)` **孿生條目**（Windows 側 Bash 工具被 PreToolUse 硬擋〔鐵律一〕，缺孿生＝L2 在 Windows 無頭窗口零可執行；語法 [需核對]） |
| L3 永遠禁止 | `git commit`／`push`、棘輪常數檔（`tools/tests/test_adr_xplat001_c1c2_lock.py` 等鎖檔）、治理保護面全部——**紅線 10 語意不變**：`AUTOSDD_UNATTENDED=1` 下保護面唯讀照舊由 `block_destructive_git.py` 硬擋；保護面**成員清單**於實作批新增 `.claude/settings.unattended.json` 與 `tools/tests/test_adr_xplat001_c1c2_lock.py` 二檔入 `_GOV_EXACT`（依保護面自身收錄判準「改它可直接改變 cap/band/武裝裁決/守衛自身行為」；動 hook＋測試＝治理面，由收尾單人窗口執行） | `permissions.deny`（deny 優先於 mode；每個 L3 檔案同列 Write/Edit/NotebookEdit 形態）＋既有 hook（雙保險） |

**確切鍵名草案**（新檔 `.claude/settings.unattended.json`，僅無頭 spawn 以 `--settings <絕對路徑>` [需核對] 載入，**不動**主 `.claude/settings.json`——2026-08-31 現查其頂層鍵僅 `$schema/description/autoCompactEnabled/outputStyle/env/hooks`，無 `permissions` 鍵；主檔屬治理保護面，無頭姿態塞進去會讓互動 session 一起變寬，方向錯）：

```json
{"permissions": {
  "defaultMode": "acceptEdits",
  "additionalDirectories": ["~/.autosdd/handback"],
  "allow": ["Bash(python tools/session_resume_planner.py --pace*)",
            "Bash(python tools/session_resume_planner.py --check*)",
            "Bash(python tools/check_defect_log_crossref.py*)",
            "Bash(python -m unittest*)", "Bash(python -m pytest*)",
            "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)",
            "PowerShell(python tools/session_resume_planner.py --pace*)",
            "PowerShell(python tools/session_resume_planner.py --check*)",
            "PowerShell(python tools/check_defect_log_crossref.py*)",
            "PowerShell(python -m unittest*)", "PowerShell(python -m pytest*)",
            "PowerShell(git status*)", "PowerShell(git diff*)", "PowerShell(git log*)"],
  "deny":  ["Bash(git commit*)", "Bash(git push*)", "Bash(git rebase*)",
            "PowerShell(git commit*)", "PowerShell(git push*)", "PowerShell(git rebase*)",
            "Write(./tools/tests/test_adr_xplat001_c1c2_lock.py)",
            "Edit(./tools/tests/test_adr_xplat001_c1c2_lock.py)",
            "NotebookEdit(./tools/tests/test_adr_xplat001_c1c2_lock.py)",
            "Write(./.claude/settings.json)", "Edit(./.claude/settings.json)",
            "NotebookEdit(./.claude/settings.json)",
            "Write(./.claude/settings.unattended.json)",
            "Edit(./.claude/settings.unattended.json)",
            "NotebookEdit(./.claude/settings.unattended.json)"]
}}
```

> 草案註記（R114 修訂）：① `PowerShell(...)` 孿生條目語法標 [需核對]，實作批以官方 permissions 文件現查為準——Windows 側 Bash 工具被 PreToolUse 硬擋（鐵律一），無孿生條目時 allow 清單在 Windows 無頭窗口結構上零可執行；② `additionalDirectories` 的 `~` 展開 [需核對]，替代案＝planner 產檔時把 `Path.home()` 展開後的**絕對路徑**寫入；③ deny 對每個 L3 檔案同列 `Write(...)`／`Edit(...)`／`NotebookEdit(...)` 形態——acceptEdits 語意下 Edit 是自動放行的主要寫入通道，只列 Write 罩不住。

**落點**：`tools/session_resume_planner.py::choose_resume_route()`（:1120；RESUME 與 FRESH 兩條 argv 現查**皆無** `--permission-mode`——G1 的機械根因）兩路同補 `--permission-mode acceptEdits --settings <上述檔>`；預檢＝R112 §2 P-3 A-PRE 增一格「unattended settings 檔存在且 JSON 可解析，缺席 ⇒ 拒 spawn＋loud」。旗標名依 PRD §4.5.4 慣例標 [需核對]，實作批以 `claude --help` 現查為準（R112 Dev ②-A 靜態層同型）。

### §3(b) 交接可見性：handback 檔＋SessionStart 偵測（G2）

**判準**：「沒寫 handback 的續跑」必須可偵測——寫入義務雙載體，模型合作只是其一：

1. **路徑**：`~/.autosdd/handback/<sessionId>.md`（持久目錄，與 `~/.autosdd/traces` 同壽命紀律；逃生口共用 SSOT＝`tools/lib/endurance_env.py`——R112 §6-1 懸案**分兩個 artifact**：**handback 檔載體**在此落定為「共用」；**任務書（P-1）持有面**同判例比照辦理、實作批確認）。
2. **內容四項**（機器可驗 marker）：`## 做了什麼`／`## 驗了什麼`（附實測 rc）／`## 卡在哪`／`## 下一步指令`。
3. **prompt 收尾義務**：`_RESUME_RULES`（planner :1089）增句「收窗前必寫 handback 檔（路徑由 prompt 注入），四節齊備」。
4. **planner 側後檢（不依賴模型合作）**：`_run_resume()`（:1155）返回後檢 handback 檔「存在 ∧ mtime ≥ spawn 時刻 ∧ 四 marker 齊」三值 `handback_verdict ∈ {written, missing, stale}`；非 written ⇒ resume log 落 `handback_missing` 事件＋`escalation.alert(loud=True)`。`resumed` 事件（:1199）增欄 `handback_path`／`handback_written`。
5. **SessionStart 偵測未讀**：SessionStart hook 掃 `~/.autosdd/handback/*.md`（排除 `*.ack` sidecar 已確認者），有未讀 ⇒ 以 additionalContext 在終端出聲（列檔名＋「做了什麼」首行＋「下一步指令」節），並落 `.ack` 於使用者可見後。PushNotification 保留（R112 §3-4 佇列照舊，本案不重述）。落點候選＝`context_budget_guard.py` SessionStart 臂——**該檔 raw 1089/1089（餘裕 0，動工前現查）零增量鐵則（R112 §4 已載）**。SessionStart 的 additionalContext 只能由 hook 行程**自身 stdout** 發出 ⇒ hook 側至少需 import＋呼叫行 ⇒ 可行路＝⓿ 型瘦身，或付 SPECIAL_FILES repin 代價（受 `repin_growth_problems()` 淨額上限管）；若要指名被呼叫端，指 hook **已 import** 的 sentinel_lifecycle 家族並明列 hook 側增行成本（`tools/lib/quota_escalation.py` 是 planner 的被呼叫端、hook 全檔零 import 它，不得作為本 hook 的落點），落點裁決留給實作批。

### §3(c) 配額內自循環：接力狀態機（G3；R112 §3-3 的常數化）

**現查根因**：resume 終局（planner :1303-1315）＝`_run_resume` 一次 → 狀態寫 `resumed` → `_schtasks_remove` → 返回。fire-once，結構上無下一窗。

**常數**（家＝`quota_policy.ENV_SPEC`，依 R-4.5.10-3 判例值可 ENV 調；出廠建議值如下）：
`AUTOSDD_RELAY_MAX_SPAWNS`（每 reset 視窗 spawn 上限，出廠 **2**）／`AUTOSDD_RELAY_NO_PROGRESS_LIMIT`（連續無新進度停止閾，出廠 **1**＝對齊 R112「零推進即停」語意；上調＝有意放寬，走 ENV 實測、不再修憲）。

**每次 spawn 前置判準（全 AND，缺一不排）**：
① `relay_seq < AUTOSDD_RELAY_MAX_SPAWNS`；② `--pace` **現查** band ∈ {free, notice}（converge 以上不續燒；`unmeasured` 視同不合格——量不到 ≠ free，保守向收斂）；③ 任務書仍有未完項；④ 非連續 ≥ `AUTOSDD_RELAY_NO_PROGRESS_LIMIT` 窗零新進度（新進度＝`handback_verdict=written ∧ files_changed>0`；files_changed＝**spawn 前、子行程結束後兩次 `git status --porcelain` 快照的差集**，前快照落 resume log 痕跡——承接 R112 P-4「planner 自量」的機械半格並補前快照：可重啟點 SOP 用 `git stash create` 保全＝窗前常態帶髒污，事後單量會把既有髒污計成本窗進度；porcelain 取數走 `tools/lib/git_paths.py` SSOT（或自帶 `-c core.quotepath=false`／`-z`），對齊鐵律三登記面與 `TestGitPathEnumerationIsQuotepathSafe`，防非 ASCII 檔名差集失真；不信模型自報）。

**狀態機表**（收窗時判定，取代現行「直接返回」）：

| 現態 | 輸入 | 次態 | 動作＋痕跡 |
|---|---|---|---|
| WINDOW_DONE | ①②③④ 全真 | RELAY_NEXT | 重排下一窗（同 `_register_and_record`）＋`relay_spawned {seq, band, files_changed_prev}` |
| WINDOW_DONE | ③ 假（無未完項） | DONE | 正常收尾＋`relay_done` |
| WINDOW_DONE | ④ 假（連續 ≥ `AUTOSDD_RELAY_NO_PROGRESS_LIMIT` 窗零推進） | NO_PROGRESS_STOP | `escalate(loud)` 恰一次＋`relay_stopped {why=no_progress}`，不再燒 |
| WINDOW_DONE | ② 假（band 收緊/量不到） | QUOTA_STOP | `relay_stopped {why=band}`＋交回哨兵巡邏（§3(d) 判準1） |
| WINDOW_DONE | ① 假（達上限） | RELAY_EXHAUSTED | `relay_stopped {why=cap}`＋loud（留任務書給人） |
| WINDOW_DONE | ①②③④ 全真但重排失敗（`_register_and_record` rc≠0） | 視同停止次態（SD-4） | `relay_spawn_failed {seq, band, rc}`＋loud＋拆 -Once＋重掛哨兵（§3(d) 判準1）；不記 `relay_spawned`、回傳沿用排程 rc |
| WINDOW_DONE | 收窗主體未捕捉例外（SD-8 兜底） | 視同停止次態 | `relay_settle_crashed {error}`＋loud＋拆 -Once＋重掛哨兵；回傳沿用 resume_rc 既有契約 |

**表列判定順序＝③→④→②→①（自上而下短路）**：正常結束優先，其次連續零推進（故障訊號、loud），再 band 收緊（交回哨兵），達 spawn 上限最後；多判準同時為假時以此序取唯一次態。
**失敗態歸屬**：rc=None（spawn 例外）／`resume_failed`／REFUSE 一律進 WINDOW_DONE 判定（`handback_verdict` 必 `missing`、`files_changed` 視同 0），依上序走狀態機；**所有停止次態（含失敗路徑）皆重掛哨兵**（§3(d) 判準1）。實作前置：`_run_resume`（:1155-1202）現行只回傳 `int | None`，REFUSE 分支（:1164-1166 `return 1`）與「子行程真的跑完但回非零 rc」型別上無法區分、:1307 三元判斷會把 REFUSE 也寫成 `state="resumed"`——**回傳需附帶 route strategy（或等價訊號，例如把 `route["strategy"]` 寫回 state），供收窗判定辨識 REFUSE；REFUSE 不得寫成 `state="resumed"`**。
**計數持久化**：`relay_seq`／`relay_no_progress_streak` 連續計數住 relay 狀態塊（每窗為獨立排程行程，計數必須落磁碟載體）；歸零邊界＝觀測到 `reset_at` 變更。

R112 §3-3 三布林 AND 承接；煞車一以出廠值 1 對齊 R112「零推進即停」紅綠（零推進格斷言 escalate 恰一次＋零續排），煞車二（cap）原樣。本案新增的只有：常數收斂為出廠值＋ENV 可調（實測後改 ENV 不再修憲）、band 現查判準②、以及狀態機表本身。落點＝`_resume_tick` resume 分支收尾（planner 749/750，餘裕 1，動工前現查 ⇒ 胖身體照 R112 批0 判例下 `tools/lib/resume_route.py` 或新 lib）。

### §3(d) 哨兵自癒：fire 後重掛＋patrol 自檢（G4）

**現查根因**：resume 終局刪排程（:1314）但**不清 arm stamp、不重掛哨兵** ⇒ stamp 說武裝、launchctl 空——正是 08-31 上午 `--pace` 的 🔴 警語（`tools/lib/sentinel_lifecycle.py::liveness_problem()` :128 逐字「armed stamp 說 … 已武裝，排程器現查卻沒有這支工作 ⇒ 哨兵已死、喚醒鏈斷線」；接線 `liveness_line()` :131 由 `--pace`／`--check` 共用，planner :1487/:1517）。且 stale stamp 會把 `maybe_arm()`（`tools/lib/sentinel_lifecycle_arm.py` :161）閂在 `latched` 臂（:172）——**閂死射程只及「人未回來（無 SessionStart）」期間**：SessionStart 既有接線每次開場都清閂鎖（`context_budget_guard.py` :757/:772），人一回來武裝評估即恢復。

**判準1（fire 後重掛）**：`_resume_tick` resume 分支收尾（rc 落定＋§3(b) 後檢＋§3(c) 狀態機判定之後）：次態 ∈ {DONE, NO_PROGRESS_STOP, QUOTA_STOP, RELAY_EXHAUSTED} 一律 `--arm-sentinel` 重新武裝——**含失敗路徑**（rc=None／resume_failed／REFUSE 依 §3(c) 失敗態歸屬進 WINDOW_DONE 判定，落入上述停止次態同樣重掛）（既有手法＝PATROL_HANDBACK 分支 :1287-1288：`args.task_name` 歸位 `DEFAULT_TASK_NAME` 再 `_arm_sentinel`）；RELAY_NEXT 則由下一窗接手、不重掛。判準1 的價值＝**不等人開 session 即自癒**（fire 側自己閉合，不依賴人回來觸發 SessionStart 清閂）。重掛失敗 ⇒ loud＋**清 arm stamp**（`clear_arm_latch()`，`tools/lib/sentinel_lifecycle_arm.py` :148），讓下一個互動 session 的 `maybe_arm` 走正常武裝路＝R112 §3-5「自癒的自癒」同型。
**判準2（每次 patrol 自檢＋自動重掛）**：patrol 臂 rearm 前以既有 `armed_but_missing()`（:139）比對 stamp ↔ 排程器現查，真漂移 ⇒ 走既有 `quota_escalation._heal_armed_drift()`（:304，PRD §4.5.8 v2.1.7 機械物）。**誠實劃界**：patrol 自檢的觸發前提是 tick 還醒得來（工作還在）；「工作消失型」漂移（今晚形狀）patrol 結構上蓋不到——那一半由判準1（fire 側）＋R112 §3-5 heal_latched（session 側，原樣承接不重述）合力閉合，三處判準互為冗餘、持有面各異。

### §3(e) usage 高水位預防性武裝：現查劃界（不發明已存在的東西）

**已存在、本案不重做**：① 額度四帶（notice/converge/prepare/halt；百分比現查 `quota_policy.py --print-env-example`）＋prepare 帶「進帶第一次工具呼叫出聲＋寫可重啟點任務書、一窗一次」（CLAUDE.md SOP＋quota_gate）；② halt/arm 分支喚醒武裝 `arm_quota_wakeup()`（`context_budget_guard.py` :826）；③ SessionStart 清閂鎖＋孤兒回收（`arm_sentinel` :756，R82 起**不再直接武裝**）＋PostToolUse `arm_when_earned()` 夠格才武裝（:808）；④ 哨兵 900s 零 token 巡邏＋復原證據判「已處理」（`unhandled_limit_event`）；⑤ `tick_plan` PATROL_HANDBACK 不永眠（PRD §4.5.10）；⑥ stamp 漂移出聲（`liveness_line`，今晚實戰命中）＋patrol 側自癒（PRD §4.5.7/§4.5.8）；⑦ R112 REQ-W4 P1~P6 全鏈預檢（Proposed，落地歸 R112 批次）。
**結論**：「usage 接近滿水位即武裝」**無新缺口**——預防性武裝已是 **session 生命週期內機械常態（PostToolUse 觸發）**且今晚實戰走通；本案缺口只有 G1~G4 四項，全部在「武裝之後」的最後一哩。（註：根 CLAUDE.md〈額度哨兵〉「SessionStart 自動 `--arm-sentinel`」同措辭另案對齊，不在本案射程。）

## §4 驗收判準（QA；每條可機械查）

| # | 對應 | 指令 | 預期輸出形態 |
|---|---|---|---|
| V-a1 | §3(a) | `grep -c "permission-mode" tools/session_resume_planner.py`（或抽出後的 lib） | ≥2（RESUME／FRESH 兩路 argv 皆帶）；選路單元測試斷言 argv 含 `--permission-mode` 與 `--settings` 兩字面 |
| V-a2 | §3(a) | 注入測試：unattended settings 缺席時呼叫 spawn 預檢 | 拒 spawn＋rc≠0＋`resume_authz_preflight_failed` 痕跡（R112 P-3 增格） |
| V-a3 | §3(a) L3 | 合成無頭回合內 `git push` 形態 | 被 deny／hook 擋下（exit 2），痕跡可稽核；紅線 10 測試零改動仍綠 |
| V-a4 | §3(a) L2 | 兩平台 allow 條目集合對 L2 清單**雙向對齊**（單元斷言） | allow 集合＝L2 清單 × {Bash, PowerShell}（雙向：缺一即紅、多一即紅） |
| V-b1 | §3(b) | 合成續跑（模擬 spawn）後 `ls ~/.autosdd/handback/<sid>.md` ＋ grep 四 marker | 檔在、四節齊；`resumed` 事件含 `handback_written=true` |
| V-b2 | §3(b) | 注入「模型沒寫 handback」的合成收窗 | resume log 逐字出現 `handback_missing` ＋ alert 痕跡（loud） |
| V-b3 | §3(b) | 注入未讀 handback 後跑 SessionStart hook | stdout/additionalContext 含該檔「下一步指令」節；`.ack` 落地後重跑轉安靜 |
| V-c1 | §3(c) | 狀態機真值表單元測試（①②③④ 十六格，依 ③→④→②→① 判定序） | **十六格各寫死唯一期望次態＋期望痕跡事件（`relay_spawned`／`relay_done`／`relay_stopped.why=…`；SD-4/SD-8 追補：全真格重排失敗＝`relay_spawn_failed`、收窗主體例外兜底＝`relay_settle_crashed`）**；僅全真格產生 RELAY_NEXT；連續 ≥ `AUTOSDD_RELAY_NO_PROGRESS_LIMIT` 窗零推進格斷言 escalate 恰一次＋零續排 |
| V-c2 | §3(c) | 合成第 `AUTOSDD_RELAY_MAX_SPAWNS+1` 窗 | 必不排；`relay_stopped {why=cap}` 落痕跡 |
| V-c3 | §3(c) 判準④ | 窗前注入既有髒污＋窗內零改動 | 斷言 `files_changed=0`（前快照痕跡在 resume log）——守「兩次 porcelain 快照差集」量法，事後單量必把窗前髒污誤計成進度 |
| V-d1(mac) | §3(d) | 重演 fire→resume→收窗後 `launchctl list \| grep AutoSDD_Sentinel_`＋plist 回讀（照 §6-2） | rc=0（**mac 憑證是 rc 不是時間值**）＋plist 回讀吻合 |
| V-d1(win) | §3(d) | 同重演後 `Get-ScheduledTask -TaskName AutoSDD_Sentinel_<sid> \| Get-ScheduledTaskInfo` | **NextRunTime 非空值**憑證（CLAUDE.md 反事後諸葛既定形態） |
| V-d1(正面) | §3(d) | rearm 成功路徑單元斷言 | **armed stamp 存在 ∧ 排程器現查含該工作**；🔴 `--pace` liveness 警語空字串**不得作成功憑證**（「重掛失敗＋清 stamp」路徑同樣為空＝成功與失敗同綠） |
| V-d2 | §3(d) | 注入「stamp 在、排程不在」後跑 patrol tick | `_heal_armed_drift` 重掛痕跡；重掛失敗注入 ⇒ stamp 被清＋loud |
| V-d3 | §3(c)/(d) 失敗態 | 注入 spawn 例外（rc=None） | 斷言**仍重掛哨兵**＋痕跡（`handback_verdict=missing`、`files_changed=0`，依判定序落停止次態） |
| V-d4 | §3(c)/(d) 失敗態 | 注入 REFUSE（如 plan_path 缺席） | 斷言 `state` **不得為 `"resumed"`**、進 WINDOW_DONE 判定且 `handback_verdict=missing`、`files_changed=0` |
| V-e2e | 全部 | 端到端演練腳本 `tools/probe/replay_r113_lastmile.sh`（草案名）：合成撞線事件→哨兵 arm→模擬 reset（注入固定時刻）→假 spawn（`--pace` band 注入）→驗 handback＋重掛＋relay 上限 | 單腳本 rc=0＝重演今晚事件且四缺口全閉合；全程零真實額度消耗、零真 spawn `claude`（探針與 spawn 皆注入 fake）；刻意不進 CI（理由＝**真實排程器副作用＋開發機出聲層**，同 `tools/check_hooks_liveness.py` 的 CI-skip 家族） |

> Windows 對照載具（R114 修訂）：上表各列以**單元測試斷言為主判準**，grep 字面檢查降為輔助（Windows 側用 Select-String 或 Grep 工具形態，不經 bash）；V-b1 的 `ls` 在 Windows 側＝Glob 工具／`Test-Path`；`.sh` 腳本（V-e2e）Windows 側一律走 Find-GitBash SSOT（`tools/lib/Find-GitBash.ps1`），❌ 裸 `bash`。

## §5 落地拆包（映射帳本三列；相依順序＝(a)→(b)→(c)，(d) 可並行）

| 帳本列 | 承接本案節 | 併同承接（R112） | Windows 輪可執行？ |
|---|---|---|---|
| DEF-200-234（無主統籌） | §3(c) 受統籌自循環（統籌權移交接力窗口那一半） | §3-1 A-4 orphan_scan | ✅ 狀態機純函式＋常數平台中性 |
| DEF-200-235（等待到期無人接手） | §3(c) 接力鏈＋§3(d) fire 後重掛 | §5-2 復活語意、§3-3 | 設計/純函式 ✅；mac launchd 重掛**驗收**需 mac 窗口 |
| DEF-200-236（通知不重投） | §3(b) handback 可見性（可見面）＋SessionStart 偵測 | §3-4 補投佇列（投遞面） | ✅ handback 路徑用 `Path.home()` 平台中性 |
| （前置，無獨立列） | §3(a) 權限姿態——無它則 (b)(c) 寫檔全被擋，**必須最先落地** | 批2（R113-a）原樣 | settings 條目**雙平台孿生**（Bash/PowerShell 各一，Windows 側 Bash 工具被硬擋）、驗收各平台一條 |

鎖持有面預檢（鐵律七）：§3(a) 動 planner＋新 settings 檔、§3(b) 動 planner＋escalation＋SessionStart 臂、§3(c)(d) 動 planner resume 分支＋`tools/lib/quota_policy.py`（ENV_SPEC 增二常數）＋新 lib（`tools/lib/resume_route.py` 或新檔）——**同檔多包必撞**，實作批需依上表順序串行或由單人窗口收尾；planner 749/750（餘裕 1，動工前現查），胖身體一律下 lib（R112 批0 判例）。

## §6 誠實劃界

1. **睡著的 Mac 不會醒**：`pmset repeat` 需 sudo，本專案維持不碰；交付的仍是「失效可偵測」（`endurance_env.py` 姿態出聲），本案不改此界。
2. **launchd 不報 NextRunTime**：mac 憑證＝`launchctl` rc＋plist 回讀（`schedule_backend.py` 檔頭三憑證），本案全部 mac 驗收照此，不得寫成時間值斷言。
3. **修憲未過前零實作**：本檔是 R113 設計包唯一產出；§3 全部行號＝2026-08-31 快照，實作批動工前現查。
4. **acceptEdits＋allowlist 解的是權限牆，不解「模型不寫 handback」**——那一半由 §3(b) 判準 4 的 planner 後檢承重（不依賴模型合作）。
5. **SessionStart 出聲依賴人真的再開一個互動 session**：人整夜不開機 ⇒ 可見性只剩推播（R112 §3-4 佇列＋TTL 承接），本案不宣稱能叫醒不開終端的人。
6. **自循環判準②在無頭行程內量不到 band 時＝不續排**：保守向收斂（量不到 ≠ free），代價是可能少燒一窗——方向刻意，與 §4.1.5 fail-safe 判例同向。
7. **§3(d) 判準2（patrol 自檢）蓋不到「工作消失型」漂移**：已明標，由判準1＋R112 §3-5 補齊；三判準持有面各異＝刻意冗餘，不是重複建設。
8. **files_changed 差集量法的誤計面**：共用工作樹的並行寫入（人回來動檔）落在兩次快照之間會被計成本窗進度——已明標；headless 窗口常態（人不在）下風險低，本案不加鎖。
9. **`govwrite_hit()` 大小寫正規化在 Windows 對「尚不存在的目標」失手**（R114 實機探針新發現）：該函式以 `os.path.realpath` 還原大小寫，但目標尚不存在時無檔可還原 ⇒ 字面比對失手。R114 實測 `.AUTOCLAUDE/state.json`（目錄不存在）與 `.claude/hooks/NEW_GUARD.PY`（新檔、大寫副檔名）皆繞過；**已存在檔的大小寫變體全數命中**。含義：實作批把 `settings.unattended.json` 納入 `_GOV_EXACT` 時，必須同修大小寫正規化（射程先普查再定，防 R96「normcase 修復加寬 fail-open 面」教訓重演）。證據＝`docs/06_quality/CrossPlatform_R114_WakeChain_Review.md`（R114 收尾落檔）；可重跑探針＝對 `block_destructive_git.govwrite_hit()` 餵 `.AUTOCLAUDE/state.json`／`.claude/hooks/NEW_GUARD.PY`（皆應回 None＝繞過）與既存檔大小寫變體（應回正確小寫 rel）。
