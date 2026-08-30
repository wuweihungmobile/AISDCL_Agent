# PRD 修憲草案 — 喚醒鏈最後一哩（無頭續跑收尾閉環）

> **Status：Proposed**（待四方複審＋掌舵者落款；落款載體＝
> `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表，批次序＝
> v2.1.10（配速）→ v2.1.11（ADR-XPLAT-014 五歧異）→ v2.1.12（R112 喚醒鏈）→ **本批 v2.1.13**。
> 堆疊紀律照 R110 判例「未生效修憲不疊層」：本批依裁決鏈排在 v2.1.12 之後，是否合併同審交四方。
> 本檔＝R113 PRD 設計包產出（一人分飾 Architect／SA／SD／QA，掌舵者 2026-08-31 直接指令）。
> 修憲未過前本案**零實作**；程式座標凡標行號者＝2026-08-31 現查快照，動工前一律現查。

---

## §0 Status 與載體

- **帳本載體三列**（`docs/06_quality/AutoSDD_Defect_Log.md`）：DEF-200-234（主控死亡時背景活體無主統籌）／DEF-200-235（跨 reset 等待 Monitor 到期無人接手→headless 接力）／DEF-200-236（halt 期通知投遞失敗不重投）。三列解鎖條件原指向 R112 案 §3／§5——本案落款後解鎖條件改指向「R112＋R113 兩案設計落地」。
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
| REQ-L1 | usage 接近滿水位即武裝喚醒——**已存在**，本案只做誠實劃界不重做（§3(e)） | R112 REQ-W4 |
| REQ-L2 | reset 後自動續跑不需人類——續跑窗口必須**收得了尾**（寫得了任務書／證據檔／交接檔） | R112 REQ-W1(c) 擴 |
| REQ-L3 | 續跑必須**可見＋受統籌**——人回來的第一個終端畫面就看得到「誰、何時、做了什麼、燒了多少」 | R112 REQ-W2／W7 |
| REQ-L4 | 不得空轉浪費——有額度且有未完項就繼續，零推進或額度收緊就停，全程留稽核痕跡 | R112 REQ-W6＋§3-3 |

橫切約束（R112 REQ-W5 原樣）：每條演算法落程式機制、判準收在值域，不得靠模型判斷。

## §3 設計（Architect/SD；每條＝可實作判準／狀態機／常數＋落點）

### §3(a) 無頭窗口權限姿態：三層白名單（G1）

**設計**：權限＝「收窄的放行」，不是關護欄。三層：

| 層 | 內容 | 載體 |
|---|---|---|
| L1 可寫 | ① 任務書所在暫存目錄（既有 `--add-dir` 已帶）② 持久交接目錄 `~/.autosdd/handback/`（§3(b)）③ 具名證據檔（當輪 `docs/06_quality/CrossPlatform_R*_*.md` glob）④ repo 工作樹既有檔編輯（acceptEdits 語意） | spawn argv `--permission-mode acceptEdits` [需核對] ＋ 無頭專屬 settings 的 `permissions.allow`／`permissions.additionalDirectories` |
| L2 可跑 | 具名驗證腳本**唯讀清單**：`session_resume_planner.py --pace`／`--check`、`check_defect_log_crossref.py`、`python -m unittest`／`pytest`（唯讀跑）、`git status`／`diff`／`log` | 同檔 `permissions.allow` 的 `Bash(<前綴>*)` 條目 |
| L3 永遠禁止 | `git commit`／`push`、棘輪常數檔（`tools/tests/test_adr_xplat001_c1c2_lock.py` 等鎖檔）、治理保護面全部——**紅線 10 不動**：`AUTOSDD_UNATTENDED=1` 下保護面唯讀照舊由 `block_destructive_git.py` 硬擋，本案一字不改 | `permissions.deny`（deny 優先於 mode）＋既有 hook（雙保險） |

**確切鍵名草案**（新檔 `.claude/settings.unattended.json`，僅無頭 spawn 以 `--settings <絕對路徑>` [需核對] 載入，**不動**主 `.claude/settings.json`——2026-08-31 現查其頂層鍵僅 `$schema/description/autoCompactEnabled/outputStyle/env/hooks`，無 `permissions` 鍵；主檔屬治理保護面，無頭姿態塞進去會讓互動 session 一起變寬，方向錯）：

```json
{"permissions": {
  "defaultMode": "acceptEdits",
  "additionalDirectories": ["~/.autosdd/handback"],
  "allow": ["Bash(python tools/session_resume_planner.py --pace*)",
            "Bash(python tools/check_defect_log_crossref.py*)",
            "Bash(python -m unittest*)", "Bash(python -m pytest*)",
            "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)"],
  "deny":  ["Bash(git commit*)", "Bash(git push*)", "Bash(git rebase*)",
            "Write(./tools/tests/test_adr_xplat001_c1c2_lock.py)",
            "Write(./.claude/settings.json)", "Write(./.claude/settings.unattended.json)"]
}}
```

**落點**：`tools/session_resume_planner.py::choose_resume_route()`（:1120；RESUME 與 FRESH 兩條 argv 現查**皆無** `--permission-mode`——G1 的機械根因）兩路同補 `--permission-mode acceptEdits --settings <上述檔>`；預檢＝R112 §2 P-3 A-PRE 增一格「unattended settings 檔存在且 JSON 可解析，缺席 ⇒ 拒 spawn＋loud」。旗標名依 PRD §4.5.4 慣例標 [需核對]，實作批以 `claude --help` 現查為準（R112 Dev ②-A 靜態層同型）。

### §3(b) 交接可見性：handback 檔＋SessionStart 偵測（G2）

**判準**：「沒寫 handback 的續跑」必須可偵測——寫入義務雙載體，模型合作只是其一：

1. **路徑**：`~/.autosdd/handback/<sessionId>.md`（持久目錄，與 `~/.autosdd/traces` 同壽命紀律；逃生口共用 SSOT＝`tools/lib/endurance_env.py`——R112 §6-1 懸案在此落定為「共用」）。
2. **內容四項**（機器可驗 marker）：`## 做了什麼`／`## 驗了什麼`（附實測 rc）／`## 卡在哪`／`## 下一步指令`。
3. **prompt 收尾義務**：`_RESUME_RULES`（planner :1089）增句「收窗前必寫 handback 檔（路徑由 prompt 注入），四節齊備」。
4. **planner 側後檢（不依賴模型合作）**：`_run_resume()`（:1155）返回後檢 handback 檔「存在 ∧ mtime ≥ spawn 時刻 ∧ 四 marker 齊」三值 `handback_verdict ∈ {written, missing, stale}`；非 written ⇒ resume log 落 `handback_missing` 事件＋`escalation.alert(loud=True)`。`resumed` 事件（:1199）增欄 `handback_path`／`handback_written`。
5. **SessionStart 偵測未讀**：SessionStart hook 掃 `~/.autosdd/handback/*.md`（排除 `*.ack` sidecar 已確認者），有未讀 ⇒ 以 additionalContext 在終端出聲（列檔名＋「做了什麼」首行＋「下一步指令」節），並落 `.ack` 於使用者可見後。PushNotification 保留（R112 §3-4 佇列照舊，本案不重述）。落點候選＝`context_budget_guard.py` SessionStart 臂——**該檔 raw 1088/1089 零增量鐵則（R112 §4 已載）⇒ 實作批必先走 ⓿ 型瘦身或落在被呼叫端 `tools/lib/quota_escalation.py`**，落點裁決留給實作批。

### §3(c) 配額內自循環：接力狀態機（G3；R112 §3-3 的常數化）

**現查根因**：resume 終局（planner :1303-1315）＝`_run_resume` 一次 → 狀態寫 `resumed` → `_schtasks_remove` → 返回。fire-once，結構上無下一窗。

**常數**（家＝`quota_policy.ENV_SPEC`，依 R-4.5.10-3 判例值可 ENV 調；出廠建議值如下）：
`AUTOSDD_RELAY_MAX_SPAWNS`（每 reset 視窗 spawn 上限，出廠 **2**）／`AUTOSDD_RELAY_NO_PROGRESS_LIMIT`（連續無新進度停止閾，出廠 **2**）。

**每次 spawn 前置判準（全 AND，缺一不排）**：
① `relay_seq < AUTOSDD_RELAY_MAX_SPAWNS`；② `--pace` **現查** band ∈ {free, notice}（converge 以上不續燒；`unmeasured` 視同不合格——量不到 ≠ free，保守向收斂）；③ 任務書仍有未完項；④ 非連續第 2 窗零新進度（新進度＝`handback_verdict=written ∧ files_changed>0`；files_changed 由 planner 自量 `git status --porcelain` diff＝R112 P-4 雙寫的機械半格，不信模型自報）。

**狀態機表**（收窗時判定，取代現行「直接返回」）：

| 現態 | 輸入 | 次態 | 動作＋痕跡 |
|---|---|---|---|
| WINDOW_DONE | ①②③④ 全真 | RELAY_NEXT | 重排下一窗（同 `_register_and_record`）＋`relay_spawned {seq, band, files_changed_prev}` |
| WINDOW_DONE | ③ 假（無未完項） | DONE | 正常收尾＋`relay_done` |
| WINDOW_DONE | ④ 假（連續 2 窗零推進） | NO_PROGRESS_STOP | `escalate(loud)` 恰一次＋`relay_stopped {why=no_progress}`，不再燒 |
| WINDOW_DONE | ② 假（band 收緊/量不到） | QUOTA_STOP | `relay_stopped {why=band}`＋交回哨兵巡邏（§3(d) 判準1） |
| WINDOW_DONE | ① 假（達上限） | RELAY_EXHAUSTED | `relay_stopped {why=cap}`＋loud（留任務書給人） |

R112 §3-3 三布林 AND 與雙煞車語意原樣承接；本案新增的只有：常數收斂為出廠值＋ENV 可調（實測後改 ENV 不再修憲）、band 現查判準②、以及狀態機表本身。落點＝`_resume_tick` resume 分支收尾（planner loc 餘裕 0 ⇒ 胖身體照 R112 批0 判例下 `tools/lib/resume_route.py` 或新 lib）。

### §3(d) 哨兵自癒：fire 後重掛＋patrol 自檢（G4）

**現查根因**：resume 終局刪排程（:1314）但**不清 arm stamp、不重掛哨兵** ⇒ stamp 說武裝、launchctl 空——正是 08-31 上午 `--pace` 的 🔴 警語（`tools/lib/sentinel_lifecycle.py::liveness_problem()` :128 逐字「armed stamp 說 … 已武裝，排程器現查卻沒有這支工作 ⇒ 哨兵已死、喚醒鏈斷線」；接線 `liveness_line()` :131 由 `--pace`／`--check` 共用，planner :1487/:1517）。且 stale stamp 會把 `maybe_arm()`（`tools/lib/sentinel_lifecycle_arm.py` :161）閂在 `latched` 臂（:172）——下一個 session 也武裝不回來。

**判準1（fire 後重掛）**：`_resume_tick` resume 分支收尾（rc 落定＋§3(b) 後檢＋§3(c) 狀態機判定之後）：次態 ∈ {DONE, NO_PROGRESS_STOP, QUOTA_STOP, RELAY_EXHAUSTED} 一律 `--arm-sentinel` 重新武裝（既有手法＝PATROL_HANDBACK 分支 :1287-1288：`args.task_name` 歸位 `DEFAULT_TASK_NAME` 再 `_arm_sentinel`）；RELAY_NEXT 則由下一窗接手、不重掛。重掛失敗 ⇒ loud＋**清 arm stamp**（`clear_arm_latch()` 既有 :148），讓下一個互動 session 的 `maybe_arm` 走正常武裝路＝R112 §3-5「自癒的自癒」同型。
**判準2（每次 patrol 自檢＋自動重掛）**：patrol 臂 rearm 前以既有 `armed_but_missing()`（:139）比對 stamp ↔ 排程器現查，真漂移 ⇒ 走既有 `quota_escalation._heal_armed_drift()`（:304，PRD §4.5.8 v2.1.7 機械物）。**誠實劃界**：patrol 自檢的觸發前提是 tick 還醒得來（工作還在）；「工作消失型」漂移（今晚形狀）patrol 結構上蓋不到——那一半由判準1（fire 側）＋R112 §3-5 heal_latched（session 側，原樣承接不重述）合力閉合，三處判準互為冗餘、持有面各異。

### §3(e) usage 高水位預防性武裝：現查劃界（不發明已存在的東西）

**已存在、本案不重做**：① 額度四帶（notice/converge/prepare/halt；百分比現查 `quota_policy.py --print-env-example`）＋prepare 帶「進帶第一次工具呼叫出聲＋寫可重啟點任務書、一窗一次」（CLAUDE.md SOP＋quota_gate）；② halt/arm 分支喚醒武裝 `arm_quota_wakeup()`（`context_budget_guard.py` :826）；③ SessionStart 自動 `--arm-sentinel`＋PostToolUse `arm_when_earned()` 夠格才武裝（:808）；④ 哨兵 900s 零 token 巡邏＋復原證據判「已處理」（`unhandled_limit_event`）；⑤ `tick_plan` PATROL_HANDBACK 不永眠（PRD §4.5.10）；⑥ stamp 漂移出聲（`liveness_line`，今晚實戰命中）＋patrol 側自癒（PRD §4.5.7/§4.5.8）；⑦ R112 REQ-W4 P1~P6 全鏈預檢（Proposed，落地歸 R112 批次）。
**結論**：「usage 接近滿水位即武裝」**無新缺口**——預防性武裝已是 SessionStart 常態且今晚實戰走通；本案缺口只有 G1~G4 四項，全部在「武裝之後」的最後一哩。

## §4 驗收判準（QA；每條可機械查）

| # | 對應 | 指令 | 預期輸出形態 |
|---|---|---|---|
| V-a1 | §3(a) | `grep -c "permission-mode" tools/session_resume_planner.py`（或抽出後的 lib） | ≥2（RESUME／FRESH 兩路 argv 皆帶）；選路單元測試斷言 argv 含 `--permission-mode` 與 `--settings` 兩字面 |
| V-a2 | §3(a) | 注入測試：unattended settings 缺席時呼叫 spawn 預檢 | 拒 spawn＋rc≠0＋`resume_authz_preflight_failed` 痕跡（R112 P-3 增格） |
| V-a3 | §3(a) L3 | 合成無頭回合內 `git push` 形態 | 被 deny／hook 擋下（exit 2），痕跡可稽核；紅線 10 測試零改動仍綠 |
| V-b1 | §3(b) | 合成續跑（模擬 spawn）後 `ls ~/.autosdd/handback/<sid>.md` ＋ grep 四 marker | 檔在、四節齊；`resumed` 事件含 `handback_written=true` |
| V-b2 | §3(b) | 注入「模型沒寫 handback」的合成收窗 | resume log 逐字出現 `handback_missing` ＋ alert 痕跡（loud） |
| V-b3 | §3(b) | 注入未讀 handback 後跑 SessionStart hook | stdout/additionalContext 含該檔「下一步指令」節；`.ack` 落地後重跑轉安靜 |
| V-c1 | §3(c) | 狀態機真值表單元測試（①②③④ 十六格） | 僅全真格產生 RELAY_NEXT；連續 2 窗零推進格斷言 escalate 恰一次＋零續排 |
| V-c2 | §3(c) | 合成第 `AUTOSDD_RELAY_MAX_SPAWNS+1` 窗 | 必不排；`relay_stopped {why=cap}` 落痕跡 |
| V-d1 | §3(d) | 重演 fire→resume→收窗後（mac）`launchctl list \| grep AutoSDD_Sentinel_`；`python tools/session_resume_planner.py --pace` | 前者 rc=0（**mac 憑證是 rc 不是時間值**）；後者 liveness 警語為空字串 |
| V-d2 | §3(d) | 注入「stamp 在、排程不在」後跑 patrol tick | `_heal_armed_drift` 重掛痕跡；重掛失敗注入 ⇒ stamp 被清＋loud |
| V-e2e | 全部 | 端到端演練腳本 `tools/probe/replay_r113_lastmile.sh`（草案名）：合成撞線事件→哨兵 arm→模擬 reset（注入固定時刻）→假 spawn（`--pace` band 注入）→驗 handback＋重掛＋relay 上限 | 單腳本 rc=0＝重演今晚事件且四缺口全閉合；全程零真實額度消耗、零真 spawn `claude`（探針與 spawn 皆注入 fake）；刻意不進 CI（CI 從不執行 Claude Code hook 判例同型），開發機出聲層 |

## §5 落地拆包（映射帳本三列；相依順序＝(a)→(b)→(c)，(d) 可並行）

| 帳本列 | 承接本案節 | 併同承接（R112） | Windows 輪可執行？ |
|---|---|---|---|
| DEF-200-234（無主統籌） | §3(c) 受統籌自循環（統籌權移交接力窗口那一半） | §3-1 A-4 orphan_scan | ✅ 狀態機純函式＋常數平台中性 |
| DEF-200-235（等待到期無人接手） | §3(c) 接力鏈＋§3(d) fire 後重掛 | §5-2 復活語意、§3-3 | 設計/純函式 ✅；mac launchd 重掛**驗收**需 mac 窗口 |
| DEF-200-236（通知不重投） | §3(b) handback 可見性（可見面）＋SessionStart 偵測 | §3-4 補投佇列（投遞面） | ✅ handback 路徑用 `Path.home()` 平台中性 |
| （前置，無獨立列） | §3(a) 權限姿態——無它則 (b)(c) 寫檔全被擋，**必須最先落地** | 批2（R113-a）原樣 | ✅ argv/settings 平台中性；憑證各平台一條 |

鎖持有面預檢（鐵律七）：§3(a) 動 planner＋新 settings 檔、§3(b) 動 planner＋escalation＋SessionStart 臂、§3(c)(d) 動 planner resume 分支——**同檔多包必撞**，實作批需依上表順序串行或由單人窗口收尾；planner loc 餘裕 0，胖身體一律下 lib（R112 批0 判例）。

## §6 誠實劃界

1. **睡著的 Mac 不會醒**：`pmset repeat` 需 sudo，本專案維持不碰；交付的仍是「失效可偵測」（`endurance_env.py` 姿態出聲），本案不改此界。
2. **launchd 不報 NextRunTime**：mac 憑證＝`launchctl` rc＋plist 回讀（`schedule_backend.py` 檔頭三憑證），本案全部 mac 驗收照此，不得寫成時間值斷言。
3. **修憲未過前零實作**：本檔是 R113 設計包唯一產出；§3 全部行號＝2026-08-31 快照，實作批動工前現查。
4. **acceptEdits＋allowlist 解的是權限牆，不解「模型不寫 handback」**——那一半由 §3(b) 判準 4 的 planner 後檢承重（不依賴模型合作）。
5. **SessionStart 出聲依賴人真的再開一個互動 session**：人整夜不開機 ⇒ 可見性只剩推播（R112 §3-4 佇列＋TTL 承接），本案不宣稱能叫醒不開終端的人。
6. **自循環判準②在無頭行程內量不到 band 時＝不續排**：保守向收斂（量不到 ≠ free），代價是可能少燒一窗——方向刻意，與 §4.1.5 fail-safe 判例同向。
7. **§3(d) 判準2（patrol 自檢）蓋不到「工作消失型」漂移**：已明標，由判準1＋R112 §3-5 補齊；三判準持有面各異＝刻意冗餘，不是重複建設。
