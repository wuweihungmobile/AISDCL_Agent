# CrossPlatform R213 第五窗（姊妹檔）：三問零信任重驗再做一次、發現並修復 DEF-200-532（halt 等待期不看他 session 接手）

> 主檔 `CrossPlatform_R213_DebtZero_FourParty_Evidence.md` 已越 warn 線（第四窗起只留指針），依 `DEF-101-587` 姊妹檔體例本窗全部內容落本檔；登記＝`tools/lib/governance_docs.py`。
> 視窗：2026-10-14 13:00 起（+08:00），sid `f41202bc-815a-4a95-97be-d4560ea180da`；主控＝Fable 5.1、開發者＝Sonnet ×1（DEV-W5）、審查鏡＝Sonnet（見〈十三-5〉）。

## 十三-1 掌舵者原文（逐字，與第四窗相同三問）與範本〈🏁〉判定

> 1.請徹底完成以上任務，找到沒法完成收斂的根因，徹底解決？請想盡所有辦法完成收斂任務！ ==> 我的完成的定義是沒有積欠技術債與解決已知的所有ＢＵＧ！
> 2.完成實作AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md裡面所有功能！==> 請檢視驗證每個功能都已經完成 E to E 全功能驗證！
> 3.如何將兩邊的 .env同步，哪邊才是正確完整的？這個參數檔該如何維護？ 幫我設計自動同步機制！==> 下次在Windows執行時，幫我自動同步！請進行驗證功能是否ＯＫ？
> 「若以下問題，下此不用再重複，請跟我說，我會拿掉，不然就是繼續迭代，直到解決」「請派Subagent時, 使用Sonnet 5！你當主控Agent還是使用Fable 5.1」

判定：T1 成立（第十次響應，同三問）；本窗零信任重驗途中**T2 成立**（新立 P2＝DEF-200-532，暴露證據＝非構造性真機痕跡，見〈十三-3〉）⇒ 不開軌道① 輪、不產四件套（T2 的載體是帳本未結列，本窗同窗修復），只做修復＋驗證＋結案。

## 十三-2 主控親跑的零信任重驗（量測於 2026-10-14 13:03～13:12 +08:00；每格都是當場輸出）

| 項 | 指令 | 輸出（逐字） | 判定 |
|---|---|---|---|
| 工作樹 | `git status --porcelain`、`git fetch origin main`、`git rev-parse HEAD origin/main` | 0 行；兩者皆 `2d9a86cb472e163c40f3ed00ccd9e1f893dd6b23` | 乾淨、與遠端一致 |
| 三本帳 | `python tools/check_defect_log_crossref.py` | rc=0；`未結存量 0 列`；`外部阻塞軌…：0 筆`；`結構性長債軌…：0 筆`（帳本 232 筆、175 份治理文件皆登記） | 0／0／0（本窗入帳 DEF-200-532 後變 1／0／0，修復後回 0） |
| 交接載體 | `python tools/check_handoff_carriers.py` | rc=0；`[census] 當前輪＝R213`；tracked 載體 213 份、commit 訊息 768 則皆無前瞻延後宣告 | 無延後宣稱 |
| HEAD CI | `gh run list --commit 2d9a86cb…` | AutoClaude CI `38492815122`／root-infra-ci `38492815087`／macos-compat-ci `38492815306`／windows-compat-ci `38492815060` 皆 `completed success`（push，2026-10-14T00:54:50Z） | 全綠 |
| .env（mac） | `python tools/lib/quota_policy.py --env-doctor` | `[empty-local] .env 已無任何有值的行（只剩註解／空白鍵）⇒ 可直接刪除該檔`；`結論：0 個問題 ⇒ rc=0`；`env.shared` 4 鍵（HALT_PCT／三個 MODEL） | 乾淨 |
| nightly 錨 | `python tools/refresh_nightly_anchor.py --check-head` | rc=0 `✅ nightly 錨判準通過（HEAD）：nightly-run=38279403926 …（1 天前，上限 14 天）nightly-red=none` | 新鮮 |
| 本機 nightly | `AutoClaude/logs/nightly_mac_latest.log` | `===== nightly 彙總：PASS=5 FAIL=0 =====`（RunId 20261014_074954，第四窗 `--force` 乾淨樹真跑；本窗之後無新排程 nightly） | 無新紅 |
| 額度 | `python tools/session_resume_planner.py --pace` | `現在可派 2 個 agent（硬上限 cap=4）｜band=notice｜最緊的一條＝weekly_scoped 55%`；量測於 2026-10-14T13:03:27+08:00 | 可派工 |
| launchd 哨兵現查 | `launchctl list \| grep AutoSDD_Sentinel_` | 3 支：`d364151e…`（runs=109）、`7c51b538…`（runs=48）、`a4b1c822…`（runs=20），皆 `run interval = 900 seconds`、last exit 0；本機只有 1 個活的 `claude` 行程（本窗） | ⚠ 三支都屬已關閉的視窗 ⇒ 追查（〈十三-3〉） |

## 十三-3 發現：DEF-200-532（P2；暴露證據＝非構造性真機痕跡）

- **現象**：`~/.autosdd/traces/halt_d364151e-….json`＝`{"band":"halt","binding":"seven_day","reset_at":"2026-10-17T17:59:59.749567+00:00","at":"2026-10-13T09:54:55.776700+08:00"}`；該 session 逐字稿最後寫入 2026-10-13 10:01（`ls -la`），之後無任何活動。哨兵 launchd log：`哨兵判定 arm_reset：偵測到自願 halt 標記；觀測 reset=2026-10-17 17:59:59.749567+00:00 尚未到 ⇒ 要求排程器改在那個時刻醒（本次零 token）` ×109（13:03:04 tick 時的快照；該 log 終值＝`哨兵判定` 151 筆：arm_reset 112／patrol 38／disarm 1，主控 `grep -c` 親數）；resume log 末筆 `controller_idle_seconds: 97403`（27 小時）；任務書狀態塊 `state=waiting, allow_resume=true, attempts=0, max_attempts=5, reset_source=halt-marker`。
- **額度實況**（`quota_burn.jsonl` 去重時間線，seven_day）：10-13 00:05 89% → 00:43 93% → 00:49 93% →（09:54 halt）→ 10:11 **0%** → 12:42 13% → 15:02 19% → 21:49 36% → 10-14 13:03 63%（10-14 的中間列略）；`resets_at` 全程維持 2026-10-17T18:00Z。即額度在標記後 17 分鐘已回到 0%（視窗被提供者重置，reset 時刻未變），哨兵無從得知、也不需要知道——真正的判準是下一點。
- **人已接手**：同專案逐字稿目錄在標記之後有 4 支新 session 大量活動（`db16e13f` 10-13 21:48／8.2MB、`7c51b538` 10-14 07:41／5.5MB、`a4b1c822` 10-14 13:01／2.2MB、`f41202bc` 本窗）。掌舵者早已在新視窗把 R213 第三、四窗做完。
- **後果（若不修）**：2026-10-17 18:01:59Z 哨兵轉 `probe`，`allow_resume=true` ⇒ 無頭 `claude -p -r d364151e…`（無人視窗主控模型＝fable）喚醒一個 context 484,502（任務書骨架於 09:54:55 的量測）、已被取代的 session，最多 5 次嘗試；燒的是掌舵者最在意的 Fable 額度，且與人正在用的視窗構成雙窗。
- **根因**：`tools/lib/quota_messages.py::halt_verdict(halt_marker, idle_seconds, now)` 的「標記失效」只看**本 session 自己**的逐字稿活動（兌現時刻後有活動才算已續跑）；`reap_verdict` ⑥ 又刻意保護 `waiting` 狀態不被 6 小時閒置 GC 收掉（等週 reset 本來就會閒置 7 天）。兩條規則各自正確，合起來對「同專案別的 session 已接手」整格失明。既有「防雙窗」（到點仍在動 ⇒ 不叫醒）也只看同一 session。
- **前身**：R212 E2E Run4 證據檔〈理論洞〉#55（跨 session 並行寫者：哨兵的靜止守門只看本 session 逐字稿）即本缺陷的 P4 形態；本窗取得非構造性暴露證據 ⇒ 升 P2（審查鏡 F7 指出的互引）。
- **對照（同族、設計正確）**：`7c51b538` 的 five_hour halt 標記 00:44:58 已存在（00:49:41 被重寫；reset=10-13 16:59:59.933611Z＝10-14 00:59:59+08:00），哨兵 00:44:58／01:00:00 `arm_reset`（plist 帶 `StartCalendarInterval Day=14 Hour=1 Minute=2`）、01:02:05 醒來讀到逐字稿 1s 前仍在寫 ⇒ `patrol`（session 自己續跑了，不叫醒）——同 session 的防雙窗是活的。

## 十三-4 修法與驗證（DEV-W5＝Sonnet，兩輪；任務書與回報＝`~/.autosdd/r213_window5_scratch/w5_developer_brief.md`／`w5_dev_result.md`）

### 修法（守衛面；暴露證據＝〈十三-3〉非構造性真機痕跡，符合根 CLAUDE.md〈守衛面准入〉）

| 檔 | 改動 | LOC（count_loc／上限；主控親跑 `check_loc_budget` rc=0） |
|---|---|---|
| `tools/lib/sentinel_lifecycle_arm.py` | `session_evidence(transcript, since=None)` 加 `since`（只計 `timestamp > since` 的記錄；`None` 與舊行為逐位元組相同）；新 `superseding_session(project_dir, own_sid, halt_marker)`（只看目錄直下 `*.jsonl`、`stem != own_sid`、`st_mtime > since` 成本閘、第一支過武裝門檻 `should_arm`（24 回合且 600s）者即回；標記缺席／`at` 解不出／任何 `OSError` ⇒ `None`＝量不到不算接手）；新 `clear_halt_marker(sid)`（路徑唯一的家＝`quota_gate.halt_marker_path`，lazy import） | 112→142／400 |
| `tools/lib/quota_messages.py` | `halt_verdict(..., superseded_by=None)`：**第二輪定稿的優先序**＝先算本 session 自己的失效（兌現時刻後仍有活動 ⇒ `None` 走 idle 判定），標記仍有效才看 `superseded_by` ⇒ `disarm`＋`clear_halt`，再往下才是 `arm_reset`／`patrol`／`probe`；沒有 `reset_at` 的標記維持舊判準（escalate／None，不看 superseded）；預設 `None` 時五個既有分支逐位元組同行為 | 392→398／400 |
| `tools/lib/sentinel_lifecycle.py` | 再匯出 `superseding_session`／`clear_halt_marker` | 361→363／400 |
| `tools/session_resume_planner.py` | `sentinel_decide(..., superseded_by=None)` 透傳；`_sentinel_tick` 以 `transcript.parent if transcript.is_file() else project_transcript_dir(_REPO_ROOT)` 為同專案範圍（逐字稿父目錄天生同專案；子專案 cwd／他 slug 的 session 自動隔離，退路才 slug 推導）；disarm／escalate 分支在註銷前 `clear_halt_marker`，痕跡 `sentinel_disarm`／`sentinel_escalate` 多帶 `cleared_halt` | 749→750／750（餘裕 0） |

第一輪把 `superseded_by` 放在所有分支之前，真機 13:47:37 把 `7c51b538`（標記 reset=10-13 16:59:59Z、它自己 07:41:33 還在寫＝標記早已失效；判定用 idle（逐字稿最新 mtime 起算）13:32:37＝21,063 s ⇒ patrol、13:47:37≈21,963 s ≥ 21,600 ⇒ idle 規則同 tick 也會自拆、僅超線約 363 s；resume log 的 `controller_idle_seconds` 34111 是另一把尺（最後一筆 assistant 記錄起算），不是判定用 idle）也用「接手」理由拆了：結果相同、理由是假的；活體變體＝視窗 A reset 後自己續跑中＋B 在工作 ⇒ A 正活著時被拆＋清標記（relatch 15 分內自癒，但是無意義拆裝＋誤導痕跡）⇒ 第二輪重排為上表語意，並以新測試 `test_a_marker_the_session_itself_outlived_is_not_a_takeover` 釘住（突變「移回原位」只紅這一支）。

### 測試（`tools/tests` 兩檔行數與 HEAD 相同：1079／408，主控親量 `wc -l`；逐檔凍結表／分桶棘輪／guard-line 皆免重釘）

- 新測試 8 支（`test_wake_chain_halt_r278.py`：`HaltVerdictTest` 3 支〔arming／probing／outlived〕、`SupersedingSessionEvidenceTest` 3 支〔含 subTest 11 列〕、`HaltMarkerRoundTripTest.test_clearing_removes_only_the_named_marker`；`test_sentinel_tick_e2e_r145.py`：`test_a_superseding_session_disarms_the_real_tick_and_clears_the_marker`＝真 `_sentinel_tick`，`_register_and_record`／`_resume_tick` 零次、`_schtasks_remove` 一次、標記消失、log 恰一筆 `sentinel_disarm` 且 `cleared_halt` 為真）。行數持平的代價：同檔樣板併行（`_cbg._tmpdir`／`enterContext`）、docstring 壓縮；arming 測試末行「無標記＋`superseded_by` ⇒ None」的斷言被拿掉（該性質仍由 `halt_verdict` 首句 `if not halt_marker: return None` 保證，登〈十三-5〉W5-5）。
- 主控親跑：`(cd tools/tests && python -m unittest test_wake_chain_halt_r278 test_sentinel_tick_e2e_r145 -q)` ⇒ rc=0、`Ran 78 tests`、`OK`；`ruff check` 六檔 rc=0 `All checks passed!`；`git diff --check` rc=0。
- [他包回報]（DEV-W5 在 scratchpad 隔離複本做、做完已刪；第二輪以 `PYTHONDONTWRITEBYTECODE=1`＋清 `__pycache__` 重跑，因第一次搬移型突變留下同大小 pyc 被誤吃）：突變 M1 停用 superseded 分支 ⇒ 4 支新測試紅；「移回原位」⇒ 只 outlived 一支紅；B 改回 slug 推導 ⇒ e2e 紅；M2 不排除自己 sid／M2b 遞迴掃子目錄／M3 不帶 since／M4 不清標記／M5 門檻拿掉／M6 mtime 閘拿掉／M7 不真的刪檔／M8 標記非 dict／M9 planner 不傳 superseded ⇒ 各自對應測試紅（紅單逐字見回報檔）；`test_context_budget_guard` 824 支綠（skipped=11）、相鄰鎖 c1c2／encoding_hygiene／platform_neutral_paths／platform_utils_dedup／doc_loc_baseline_freshness_r60 全綠。

### 真機證據（非構造；哨兵 tick 跑的是工作樹，修法落地的下一個 tick 即正式生效；全部主控親讀）

- `$TMPDIR/autosdd_resume_log_autosdd_resume_plan_d364151e-….jsonl` 末三筆：`sentinel_woken 2026-10-14T13:48:05+08:00` → `sentinel_decided action=disarm reason="halt 標記存在，但同專案另一 session f41202bc 於標記後已累積 109 回合／1575s 活動 ⇒ 人已接手（或已有續跑），本 session 不自動喚醒（防雙窗）；清 halt 標記、靜默解除" controller_idle_seconds=100104` → `sentinel_disarm unregister_rc=0 cleared_halt=true gc_plans=1`。接手者 `f41202bc`＝本窗主控自己。
- `~/.autosdd/traces/autosdd_sentinel_bootout_AutoSDD_Sentinel_d364151e-….log` 末兩行：`parent-gone waited=1s at 2026-10-14T05:48:06Z`／`bootout rc=0`；`launchctl print gui/501/AutoSDD_Sentinel_d364151e-…` rc=113（不存在）；`~/.autosdd/traces/halt_d364151e-….json` 與 `$TMPDIR/autosdd_resume_plan_d364151e-….md` 皆已不存在；`launchctl list` 只剩 `f41202bc`（本窗，預防性）與 `a4b1c822`（第四窗，閒置中，將於 6 小時門檻自拆）。
- `7c51b538`（第一輪優先序下的同窗事件）：13:47:37 `disarm`（同上理由）、`cleared_halt=true`、`unregister_rc=0`、`launchctl print` rc=113；其標記本已失效（它自己 07:41:33 仍在寫）、判定用 idle≈21,963 s ≥ 21,600 s ⇒ idle 規則同 tick 也會自拆 ⇒ 結果相同、理由不準，已由第二輪重排修正（見上）。
- 兩支仍活的哨兵在修法落地後各 tick 皆 `patrol`；主控哨兵 launchd log `Traceback|Error` 命中 0。

### 設計裁決（主控；供〈十三-5〉審查鏡挑戰）

- 選 `disarm`＋清標記，不選「額度提早回來就提早喚醒」（無人時只能靠每 tick 打 usage 端點才知道，違反 PRD R-4.5.10-2「巡邏只讀逐字稿＋一次 stat、零 token」；有人時提早喚醒＝雙窗）也不選 `escalate`（人就在，叫人是噪音）。
- 門檻沿用武裝門檻（24 回合且 600s）：同一把「這算不算一段真的工作」的尺；1 回合的 `claude -p "ok"` 無頭跑不算接手。
- 已知取捨 R1：同專案兩視窗同時被同軸 halt、B 在 A 標記後又做了 ≥24 回合且 ≥600s 才停 ⇒ A 的哨兵判接手而拆（B 的哨兵仍在、人在場）；與「防雙窗」一致，接受（登〈十三-5〉W5-1）。
- 根層全套（主控親跑，修法與文件落地後）：`python tools/run_root_unittests.py` ⇒ `REAL_RC=0`；`✅ unittest 數量下限釘選通過：發現 5383 個測試（下限 5326）`、`root-unittest workers=9`、`✅ 真實 TEMP 圍籬…零變動`。`ruff check tools/`：審查鏡 F1 指出主控的 governance_docs.py 登記註解 106 欄（E501，pre-push 會擋）⇒ 縮短後 rc=0 `All checks passed!`。

## 十三-5 審查鏡與理論洞

- **審查鏡 QA-W5（Sonnet，兼 Architect 帽；對工作樹唯讀、隔離複本實驗；判決檔 `~/.autosdd/r213_window5_scratch/w5_qa_verdict.md`）：CONDITIONAL，P1=0 P2=0 P3=3 P4=7；條件 C1～C4 全部為一行／文字修改，本窗已套用（本節與〈十三-3〉〈十三-4〉的訂正、PRD §16.6 措辭、governance_docs 註解寬度）。** [他包回報] 成立項：Q1 四個指定突變（停用 superseded／移回原位／改回 slug／不排除自己 sid）各自在隔離複本紅、原樣 78 支綠，另 17 項自選突變只有 X4／X8／X13 存活（登下表）；Q2 真實語料（合成標記 dict、不落檔）對 d364151e 回 `f41202bc`（150 回合／6100 s，0.015 s）、本窗 own／無標記回 None，強制全掃 58 檔／110 MB 最壞 0.696 s ≪ 5 s；9 份真實標記逐 tick 回放 0 筆誤拆、1 筆真接手（d364151e 於 10-13 10:24 即會被 db16e13f 接手）；本機 40 支互動視窗兩兩比對 10 分鐘桶，兩窗同時活動 0 對；Q3 門檻邊界（24 回合且 600 s，含等號）、子代理目錄不遞迴、壞標記全部 fail-closed；Q5 與 PRD 無硬衝突，兩處軟張力（§4.5.6 全稱字面的例外、R-4.5.10-4「僅」）屬措辭、以 §16.6 該列為例外說明；Q6 文件訂正 12 項（本窗全部套用或註明）。主控親驗其三項事實：`ruff check tools/` rc=1（E501 106 欄）、d364151e launchd log 判定 151＝112／38／1、Run4 證據檔 #55 存在。

| # | 洞 | 暴露度（三取一） | 一句可觀測再開症狀 |
|---|---|---|---|
| W5-1 | 同專案兩視窗同波次被同軸 halt、各自在標記後收斂 ≥24 回合且 ≥600s ⇒ 判準對稱、**雙向互拆**，兩窗都沒有自動喚醒（審查鏡 F4 合成複現；單窗收斂達標率在 7 份真標記中 4/7）。最便宜的硬化＝「peer 自己有未過期 halt 標記者不算接手」（約 4 行，住 arm 模組） | 構造性（本機 40 支互動視窗兩窗同時活動 0 對＝循序換窗型態） | 同一分鐘兩支哨兵痕跡皆 `sentinel_disarm` 且 `why` 互指對方 sid 前 8 碼 |
| W5-2 | `tools/probe/wakechain_e2e.py --run` 的 S3 用真專案目錄：若探針等待的 17 分鐘內主控在同專案再做 ≥24 回合且 ≥600s，探針哨兵會 `disarm`，而 `BAD` 集合含 `sentinel_disarm` ⇒ 探針紅且不指因 | 理論（只讀碼推得、未實跑） | 跑法④ 報 BAD 且 `sentinel_disarm` 的 reason 含「接手」 |
| W5-3 | 沒有 `reset_at` 的 halt 標記不看 `superseded_by`（維持 escalate／None 舊判準） | 理論 | `sentinel_escalate` 痕跡出現在同專案他視窗正工作期間 |
| W5-4 | 已無哨兵的舊 session 殘留 7 份過期 halt 標記（`2b759c13`…`e1a2d13c`，reset_at 全在過去，`halted_band_line` 對過期標記回 None），沒有任何 tick 會清它們 | 理論（檔案無害） | 某舊 sid 的標記 reset 在未來而該 sid 已無哨兵（現存 7 份都不會觸發） |
| W5-5 | （已撤）「無標記＋`superseded_by` ⇒ None」的直接斷言被拿掉——審查鏡突變 X16／X17（整段移到 `if not halt_marker` 之前／之前再複製一份）皆 rc=1、紅在 outlived 測試 ⇒ 該性質已被連帶守住，不是洞 | — | — |
| W5-6 | 清標記發生在註銷排程之前：註銷失敗（rc≠0）時標記已清，該哨兵退回 idle 判定（≥6 小時自拆），沒有「留標記讓下次 tick 重試註銷」的路 | 理論 | `sentinel_disarm` 痕跡 `cleared_halt=true` 且 `unregister_rc≠0`，之後同 job 仍每 15 分 `patrol` |
| W5-7 | `sentinel_decide` 的未處理撞線事件分支先於 halt 標記：真 429 路徑不看「接手」（審查鏡 F6；真實 resume log 43 份 2,400 筆判定中事件觸發的 `arm_reset` 8 筆全屬 db16e13f、當時同專案無他窗） | 理論（暴露 0） | 事件觸發的 `arm_reset` 與同專案他窗 ≥24 回合活動並存 |
| W5-8 | 既有鎖的咬合缺口（審查鏡 F5 存活突變）：X4 `session_evidence` 把「時間戳缺席也計入」仍綠；X8 無 `reset_at` 的標記也看 superseded 仍綠（＝W5-3 的契約無測試）；X13 planner 對每個 disarm／escalate 都清標記（不看 `clear_halt`）仍綠 | 構造性 | 任一行為改變且兩模組測試仍綠（補測試時要付 tools/tests 行數棘輪） |
| W5-9 | 排除自己只靠 `p.stem != own_sid`（審查鏡 F9）：狀態塊 `session_id` 與逐字稿檔名不等時，自己的收斂活動會被當他 session（本機三份 live 狀態塊皆相等） | 構造性（暴露 0） | `sentinel_disarm` 的 `why` 指向的 sid 等於該 job 自己的逐字稿檔名 |

## 十三-6 掌舵者該機專屬清單（Windows；同第四窗〈十二-6〉，字樣不變）

1. repo 根 PowerShell：`git pull --ff-only`。成功＝看到 `[post-merge dispatcher] env.shared 同步：0 個問題` 或 `…已自動修復，備份＝.env.bak.<UTC戳>…`。只有 `Already up to date.`＝這次 git 沒跑 hook，改跑 `python tools\lib\quota_policy.py --env-doctor` 看 `結論：0 個問題 ⇒ rc=0`。
2. 同〈十-9〉(2)～(5)；(2)(4)(5) 已由雲端 windows-latest 實跑，殘留只剩掌舵者實機特異性（cp950／Defender／排程帳號）。

## 十三-7 開了→收了

- Sonnet 子代理 2 支：DEV-W5（兩輪；隔離複本做突變、做完已刪；對 repo 只動 4 支正式碼＋2 支測試檔，零 git 寫入）、QA-W5（對工作樹唯讀；複本 `scratchpad/qa_w5_copy` 已刪、主樹 `.venv` 完好；未對任何真 sid 寫／清標記；收尾 `git status`／`numstat` 與審查前 cmp rc=0）。任務書與回報備份＝`~/.autosdd/r213_window5_scratch/`。
- 背景 Bash 1 條（根層全套）已結束 `REAL_RC=0`。無 Docker、無 Monitor／CronCreate、無新 launchd／schtasks（哨兵數由 4 支變 2 支＝兩支被真 tick 依新規則拆掉，本窗主控哨兵 `f41202bc` 為 PostToolUse 自動武裝的預防性哨兵）。
- 未跑 `--pace` 於全套期間（TEMP 圍籬 ✅ 零變動）。

## 十三-8 結論（給掌舵者）

三問之中：(2) PRD E2E 與 (3) .env 同步在本窗重驗仍成立；(1)「已知 BUG 全解」在本窗**先不成立**（launchctl 現查抓到 DEF-200-532）、**同窗修復並以真機 tick 自拆驗證後重新成立**（三本帳終態 0／0／0）。殘留＝該機專屬清單（〈十三-6〉；非再開事件）與 P4 理論洞（〈十三-5〉；只登記）。教訓已入 memory：零信任重驗要含排程器現查；哨兵 tick 跑的是工作樹，守衛面編修即時生效。
