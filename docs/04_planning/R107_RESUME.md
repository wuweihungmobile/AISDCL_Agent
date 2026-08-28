# R107 任務書（token reset 暫停點）— 技術債結案輪

> ✅ **本輪已收尾（2026-08-28），權威交接＝`R107_HANDOFF.md`**；本檔以下內容為過程史料。

> 寫於 2026-08-28 00:30（+08）。session `e7013c46-23a6-412b-841f-7ce608e707c0` 於 91% 額度
> （five_hour/session 軸，band=prepare）主動收斂暫停。reset 時刻＝2026-08-28 04:00（+08，
> 實測 `2026-08-27T20:00:00+00:00`）。
> 🔴 重啟後第一件事＝重驗，不採信本檔任何「已通過」宣稱（zero-trust 對自己亦然）。

## 0. 本輪定調（已由開場量測拍板）

- 輪型＝**A. 結案輪**（開場未結列 84，warn 線 86 差 2）。帳本主檔 154,307/262,144 bytes 安全。
- 掌舵者本輪三訴求：①技術債解方＋可重複使用計畫入 `docs/04_planning/`；②回答「先慢後快」
  配速是否適宜；③（新功能暫停）不碰 PRD 開發。
- 輪號紀律：檔名系列用 R107；帳本時鐘 `current_round()`＝100（讀「發現情境」欄最大 R 值）
  ⇒ **不新增帳本列、不動任何列的發現情境欄**，狀態欄可寫 `fixed@R107`。

## 1. 已驗證什麼（附實測）

- 分類艦隊（Workflow `wf_e70c6d70-3a7`）84/84 筆全分類、0 漏：needs-dev 35、quick-fix 19、
  needs-arch-decision 18、already-fixed-verify-only 8、needs-user 2、duplicate 1、
  external-candidate 1。完整 JSON＝session 暫存（已蒸發防洩漏；快照固化於
  Playbook 附錄 A／`CrossPlatform_R107_Review.md`）。
- Playbook 已交付：`docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md`（42,428 bytes、
  431 行含空行，本人抽驗章節結構完整；**內容尚未經四方複審**）。
- 開場 `python tools/check_defect_log_crossref.py --unresolved-count`＝84／158，rc 正常。
- 開場工作樹已有 2 支機器重生髒檔（非本輪產出、今日 14:48 本機 perf/nightly 所留）：
  `AutoClaude/.perf_baseline.toml`（基線重釘，sha→e3b0b38，合法）、
  `AutoClaude/tests/fixtures/pgvector_real_ground_truth.json`（seed_kb 重播種）。處置＝收尾
  以 chore 併入 commit 或由複審裁決。
- 配速/哨兵取證：91% 時 `--pace` cap=1；哨兵 `AutoSDD_Sentinel_e7013c46-…` NextRunTime
  2026/8/28 00:30:16（已武裝）。

> **狀態更新 2026-08-28 00:45**：§2 步驟 1 已完成——結案包 #1 十筆全結，主控親驗
> `--unresolved-count`＝**75／158**（count-rc=0）、完整 crossref full-rc=0、外部軌 8 筆、
> 抽查 DEF-101-739／DEF-200-075 兩列狀態欄形態合法。工作樹已保全：
> `git stash create`＝`0daf76cc22b7d2ca8e09019f0b28d4224f42d41d`、tag `r107-wip-preserved`。
> 自動續跑排程憑證：`AutoSDD_SessionResume_e7013c46-…` NextRunTime＝**2026/8/28 04:05:00**
> （relay 塊 allow_resume 已改 true）；哨兵每 15 分巡邏中。🔴 無人看管續跑硬禁
> commit/push（AUTOSDD_UNATTENDED＋PreToolUse 守衛）：§2 步驟 8 的 commit/push 只能由
> 掌舵者在場的 session 執行，續跑做到閘門全綠即停等。

> **狀態更新 2026-08-28 11:50（第二窗，session `b13f4527-525f-4128-9eed-a80207d4d3f6`，
> session 軸 99% halt 收斂暫停；five_hour reset＝2026-08-28T06:00Z＝14:00 +08）**
>
> - §2 步驟 2、3 **已完成**＋needs-user 兩筆已由掌舵者在場裁決並落地：DEF-101-338 核准
>   git rm（4 列 D 實測）；DEF-101-559 查證落「會被複製使用」分支＝hub-push.yml 8 站點升版。
>   四包完整回報（含逐筆結案敘述素材 notesForScribe）＝session 暫存（已蒸發防洩漏；
>   快照固化於 Playbook 附錄 A／`CrossPlatform_R107_Review.md`，落列處置對照見
>   `CrossPlatform_R107_Ledger_Closure.md`）
> - 主控親驗（不採信包宣稱）：未結列仍 75（帳本零觸碰）、PRD「待四方複審」剩 :10（v2.1.5
>   合法）、三支新測試在（lock:3666／quota:1392／platform:3606）、模板新節 :220-233 在、
>   git status 改動面與四包回報逐檔吻合。needsUser 包全套 run2 rc=0（Ran 3699）[他包回報]。
> - §2 步驟 4 收尾複審：**Architect／SA 兩鏡完成＝各 APPROVE_WITH_CONDITIONS**（完整報告
>   ＝同目錄 `tasks\a2049085d14ddcfd1.output`／`tasks\a9f527d37e0a2623a.output`）；SD 鏡
>   暫停時仍在背景跑（結果落 `tasks\a697adfb95d3b764f.output`，重啟後先驗它有沒有跑完，
>   撞額度死掉就重派）；QA 鏡因額度守衛 cap=0 **未派**。
> - 🔴 blocking 3 筆待修（全屬單人窗口型，勿並行派）：
>   **B1** 複審紀錄落檔：上輪 PRD v2.1.4 四方複審＋本次收尾複審四鏡，固化為
>   `docs/06_quality/CrossPlatform_R107_Review.md`（或併入 Ledger_Closure 一節），帳本
>   DEF-200-141/142/157 結案列指向之（Architect F1＝SA F1 雙鏡命中）。
>   **B2** 「原文一字不漏」宣稱不實（指稱詞被系統性改寫）：9 處措辭訂正（Guard_Line_History
>   八節標頭 :777/:802/:826/:844/:873/:893/:918/:939＋lock:1192 稽核列）改「原文全文保全、
>   知識零刪除；僅指稱詞隨載體必要調整」＋`_REPIN_LOG_HISTORY_SHA256` 同窗重釘——🔴 必須
>   在 commit 前（commit 後封進凍結前綴，改字代價劇增）。
>   **B3** 「§21~§28」指針指向不存在的節錨（目的檔無 §NN 體系；序數也是 22~29 對不上）：
>   三處修正（R106_HANDOFF.md:5／CrossPlatform_R106_Scan_Findings.md:5／lock:1191）改具名
>   節標題起訖——與 B2 同窗（同一稽核列字串、同一次 SHA 重釘）。
> - minor 5 筆（順手修）：①書記落 DEF-200-125 列時標明 :79/:1372/:1529 為立案時行號＋補
>   現行座標 :2436；②cap=4 殘留交代補 :14（v2.1.9 史料合法保留）；③本檔內的使用者
>   暫存絕對路徑一律改寫為「session 暫存（已蒸發防洩漏；快照固化於 Playbook 附錄 A）」句式；
>   ④Playbook :239 policy_version 補全字面 `v3-assertion-only+sd08-special`；⑤Playbook
>   §4.4 加一行指向模板 :220 派工紀律節。
> - 剩餘佇列（依序，單線）：①驗 SD 鏡結果→補派 QA 鏡 ②blocking B1~B3＋minor 修復
>   ③書記落列 14 筆（DEF-200-215/216/125/141/142/157/166/171/225/201/106＋
>   DEF-101-950/338/559，素材＝四包回報 notesForScribe）——🔴 訂正（QA-F2 實測）：
>   `current_round()` 只讀「發現情境」欄（狀態欄寫 fixed@R107 不翻鐘）；本輪甲路線新增列
>   「發現情境」欄一律不寫輪號，時鐘留 100 ⇒ SC-10 不要求 ADR-XPLAT-002 §6 補新列＋寫
>   R107_HANDOFF.md（紅線 1 單站點回歸鎖交棒 R108：落點 test_quota_policy.py＋重釘稅）
>   ④最後全套（run_root_unittests＋AutoClaude pytest＋lint-imports＋crossref）**必須在
>   最後一次寫文件之後** ⑤commit/push（掌舵者在場；含 2 支機器重生檔 chore 併入；push 後
>   等雲端五支 completed，windows/macos-compat-ci 長期紅不歸本輪）⑥🔴 資源釋放
>   （**成功或失敗皆必須執行**，掌舵者 2026-08-28 14:44 指示）：a) 移除
>   `AutoSDD_SessionResume_b13f4527-…` 排程；b) 哨兵視收尾狀態決定（全收尾＝移除；
>   仍有續跑需求＝保留）；c) 清 `%TEMP%\autosdd_resume_plan_*.md` 暫存任務書；
>   d) `Get-ScheduledTask AutoSDD_*` 確認清單符合預期（e7013c46 遺留排程已於
>   2026-08-28 14:57 實測清除）。
> - 工作樹保全：`git stash create`＝`ef4c5b5a18ad6e13e5cc4f4ac456bfd77639a97b`、
>   tag `r107-wip-preserved-w2`（第一窗 tag `r107-wip-preserved` 保留不動）。
> - 續跑排程憑證：`AutoSDD_SessionResume_b13f4527-…` NextRunTime＝2026/8/28 16:42:25
>   （已實測；掌舵者亦可於 14:00 reset 後手動 `claude -r b13f4527-525f-4128-9eed-a80207d4d3f6`）。
> - 額度紀錄：session/five_hour 軸 99% halt；weekly_all 38%／weekly_scoped(Fable) 62%
>   ——掌舵者指示「週額度 reset 前 21hr 全力用完」，reset 後可放開派工，但結案單線紀律不變。
>
> **🔴 掌舵者 2026-08-28 11:55 質疑「Token 用盡為何沒自動續跑」——根因取證（本窗實測）與
> 改善任務（R108 承接，本輪結案輪不新增帳本列）**：
> 1. 上一窗排程**有**自動跑：`AutoSDD_SessionResume_e7013c46` LastRunTime＝2026/8/28
>    04:05:00、LastTaskResult=0。喚醒機制本身啟動了。
> 2. 真根因＝**喚醒後的 headless 窗口許可層連 Edit/Write 都未授權**（上一窗備忘錄實測記
>    載）⇒ 續跑窗口只能唯讀，結案包零落地 ⇒ 體感「任務沒繼續」。改善＝續跑 action 的
>    `claude -p -r` 帶受控授權（如 `--permission-mode acceptEdits`；防線仍在：
>    AUTOSDD_UNATTENDED 治理面唯讀、破壞性 git 阻斷、commit/push 硬禁）——安全 vs 自動化
>    的設計裁決，R108 架構議題。
> 3. 第二根因＝planner `--register-schtasks` 觸發時刻退回 fallback（實測兩次：16:42＝
>    now+5h、19:56），**沒用 quota cache 實測 resets_at（14:00）**——工具違反 CLAUDE.md
>    「不准退回假設 5 小時」自家紀律。改善＝planner 時刻解析改讀實測 resets_at＋buffer。
> 4. 附帶發現＝`schtasks /change`（空密碼）與 `Set-ScheduledTask -Trigger` 都會把
>    Interactive principal 的 NextRunTime 弄空（實測三次）；修排程時刻唯一安全路徑＝
>    unregister→planner 重註冊。此教訓入 HANDOFF。
> 5. 本窗最終保底：`AutoSDD_SessionResume_b13f4527` NextRunTime＝**2026/8/28 19:56:02**
>    （憑證）；更早喚醒靠哨兵 15 分巡邏轉排（SD 鏡 429 已落逐字稿，哨兵應可偵測——此句
>    未驗證，重啟後從 `~/.autosdd/traces` 取證）或掌舵者 14:00 後手動
>    `claude -r b13f4527-525f-4128-9eed-a80207d4d3f6`。
> 6. **根因第 4 層（14:59 實測坐實）**：哨兵 `AutoSDD_Sentinel_b13f4527` 在 11:51~14:57
>    之間**死亡**——armed stamp 說已武裝、`Get-ScheduledTask` 查無此工作（planner 自診斷
>    「哨兵已死、喚醒鏈斷線（2026-08-16 事故形狀）」）⇒ 12:00~14:00 之間沒有任何一層
>    自動轉排，第 5 點的「哨兵應可偵測」推測**證偽**。已於 14:59 重武裝（NextRunTime＝
>    2026/8/28 15:14:39 憑證）。改善任務（R108）：哨兵死因取證（排程器日誌／
>    autosdd_resume_log jsonl）＋「哨兵活性自檢」接入 --pace 已有（本次就是它報的），
>    但**武裝後的存活監測**（哨兵死了誰來發現）仍缺機械物。

## 2. 還沒做什麼（依序執行）

1. ~~結案包 #1 驗收~~（**已完成**，見上方狀態更新）：標的 10 筆＝
   DEF-101-739/769/876、DEF-200-053/190/157/128/023/075（遷外部軌）。驗法：讀
   `docs/06_quality/CrossPlatform_R107_Ledger_Closure.md`（它的證據檔）＋
   `python tools/check_defect_log_crossref.py`（完整，rc 必須 0）＋ `--unresolved-count`
   看淨變化；抽 2 筆對源碼複核（防「宣稱複驗過其實還原錯」前例）。
2. **結案包 #2**（單線、文件級）：DEF-200-215＋216（同檔
   `docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 派工紀律節補「驗收指令派工前親跑」
   「外部端點輪詢間隔下限≥快取 TTL」「自造事件不得計為活體驗證」三條，兩筆同批結案）、
   DEF-200-125（真打一次 fetch_usage 取樣 limits[] 鍵集合，有 status 類鍵→補帶出，無→劃界
   結案；配方見分類 JSON）。
3. **結案包 #3**（單線、代碼級，觸護欄棘輪，同一窗口共用一次重釘）：
   DEF-200-166＋171（同檔 `tools/tests/test_adr_xplat001_c1c2_lock.py`：guard-total 改判相異
   檔數＋SC-10 補內容禁詞判準，各附紅綠自證）、DEF-200-225（CACHE_DIR_ENV 字面兩家加逐字
   assertEqual 測試）、DEF-101-950（TestWorktreeEolMatchesPolicy 改讀 .gitattributes 現查）、
   DEF-200-201（quota_pace explain() 相反符號顯示行修正）。配方細節見分類 JSON／Playbook 附錄 A。
4. **四方複審**（Architect/SA/SD/QA 各一，判本輪全部改動＋Playbook 內容），複審章程須明文
   包含：對 PRD v2.1.4 三站點＋§6 TELEMETRY_ALLOW_UNDOCUMENTED_ENDPOINT 的批准裁決
   （這是 DEF-200-141/142/157 的結案前置；PRD 檔內 :241/:248「待四方複審」字樣複審通過後
   改生效落款）。
5. 修復複審 blocking → 全修完才算完成。
6. **收尾書記**（單人窗口）：DEF-200-106 結案（憑證＝本輪逐列處置對照）；DEF-200-141/142/157
   依複審結論落款＋結案；寫 `R107_HANDOFF.md`；更新本檔狀態。
7. **最後一次全套必須在最後一次寫文件之後**（R96/DEF-200-163 教訓）：
   `python tools/run_root_unittests.py`＋AutoClaude `python -m pytest tests/ -q`＋
   `$env:PYTHONUTF8='1'; lint-imports`（在 AutoClaude/ 下）＋`python tools/check_defect_log_crossref.py`。
8. commit（含 2 支機器重生檔的 chore 處置）→ push（背景跑，timeout 480~570s；push 後等雲端
   五支 completed，windows/macos-compat-ci 長期紅不歸本輪）。
9. 結尾備忘錄必含：PRD v2.1 未完成清單（沿用前輪＋配速三改動路線）、帳本起訖數、
   配速疑問的正式回答（見 §4）、needs-user 兩筆裁決請求（見 §5）。

## 3. 下一步的確切指令

```powershell
# reset 後（自動排程已掛，手動亦可）：
claude -r e7013c46-23a6-412b-841f-7ce608e707c0
# 重啟第一組驗證指令：
python tools/check_defect_log_crossref.py --unresolved-count
git -C d:\CursorProject\AISDCL_Agent status --short
python tools/session_resume_planner.py --pace
```

## 4. 配速疑問的答案骨架（Architect 已分析完，收尾備忘錄照此展開）

判定＝**「先慢後快」不適宜**：錯不在「晚段回收剩餘額度」目標（use-it-or-lose-it 下成立），
錯在用「時刻」當代理變數而不用「燃燒證據」（lead_pp）當主控訊號——系統已有 lead_pp 卻只做
單向煞車；早段 throttle 砍到的是額度最充裕時的主力工作、晚段 ×2 落在 commit/push 等
must-finish 高風險動作上，方向正好相反。建議三改動：(a) thrifty floor（節儉證據成立時 far
乘數至少回 1.0，S 級可先行）；(b) bursting_ok() 接線＋pace_near 改條件制（修憲級，與
DEF-200-197/198/199 同批四方複審）；(c) must-finish 收尾保留段。詳見分類 JSON `architect` 節
與 Playbook §6。

## 5. 待掌舵者裁決（兩筆 needs-user，各一句話即可解鎖 S 級結案）

1. **DEF-101-338**：核准 Copy-on-Evolve 例外（先例 R44/45/46），`git rm` 凍結版 v0.01 內
   4 支測試假 SHA drift 殘留檔（現行測試已全用 tmp_path，該 4 檔是歷史 artifact）。
2. **DEF-101-559**：裁決 LATEST hub-push.yml sample 升不升 action 版（該 sample 在 GitHub
   永不觸發；裁「不升」代價近零，理由寫進檔頭即結案）。

## 6. 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准繞過或關閉任何 hook。
- 不准平行 agent wave 攻未結列；結案一律單線。
- 不准新增帳本列、不准動「發現情境」欄（帳本時鐘陷阱）；狀態首詞只用合法值。
- 不准 `git stash`（裸）/`checkout --`/`reset --hard`（hook 會擋；保全一律 `git stash create`＋tag）。
- 不採信任何 agent（含結案包 #1）的「已完成」宣稱，一律親驗後才改狀態。
- push 前本機閘門未全綠不准 push；最後全套必須在最後一次寫文件之後。
