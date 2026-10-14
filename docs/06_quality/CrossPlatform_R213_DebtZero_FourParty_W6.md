# CrossPlatform R213 第六窗（姊妹檔）：三問零信任重驗、補開五問 S5 再評（他機）、發現並修復 DEF-200-533（壓縮後重設態被 Q3′ 判為兩源不一致）

> 主檔 `CrossPlatform_R213_DebtZero_FourParty_Evidence.md` 已越 warn 線（第四窗起只留指針），依 `DEF-101-587` 姊妹檔體例本窗全部內容落本檔；登記＝`tools/lib/governance_docs.py`。
> 視窗：2026-10-14 16:40 起（+08:00），sid `2d1f6109-4db1-406f-9994-b2f4d1c7f562`；主控＝Fable 5.1、開發者＝Sonnet ×1（DEV-W6，兩輪）、審查鏡＝Sonnet ×1（QA-W6，一審 REJECT → 二審，見〈十四-7〉）。
> 本檔不含 `tools/check_handoff_carriers.py` 認定的前瞻延後句型；所有未做項目只准三分類（立案／PRD ⏸／理論洞 P4）。

## 十四-1 掌舵者原文（逐字，與第五窗相同三問）與範本〈🏁〉判定

> 1.請徹底完成以上任務，找到沒法完成收斂的根因，徹底解決？請想盡所有辦法完成收斂任務！ ==> 我的完成的定義是沒有積欠技術債與解決已知的所有ＢＵＧ！
> 2.完成實作AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md裡面所有功能！==> 請檢視驗證每個功能都已經完成 E to E 全功能驗證！
> 3.如何將兩邊的 .env同步，哪邊才是正確完整的？這個參數檔該如何維護？ 幫我設計自動同步機制！==> 下次在Windows執行時，幫我自動同步！請進行驗證功能是否ＯＫ？
> 「若以下問題，下此不用再重複，請跟我說，我會拿掉，不然就是繼續迭代，直到解決」「請派Subagent時, 使用Sonnet 5！你當主控Agent還是使用Fable 5.1」「以AISDLC的程序（請Architect/SA/SD/Developer考慮如何規劃設計實作獨立審查?省去非必要文件，只留一定需要文件）」

判定：T1 成立（第十一次響應，同三問）。零信任重驗（〈十四-2〉）全綠後，對照 `docs/06_quality/FiveQuestion_Audit_Protocol/README.md`〈窗口規則與收斂判定〉：第五窗修了守衛面（`tools/lib/quota_messages.py`、`tools/session_resume_planner.py`；暴露證據＝非構造性真機痕跡）⇒ **S5 成立 ⇒ 協定要求開一輪再評**（S4 的 P≤2＝DEF-200-532 同窗已 fixed，一句帶過）；第五窗證據檔對此零提及、輪帳本最後一列仍是 R207（2026-10-07）⇒ 本窗補開（Mac＝他機輪次）。追溯裁決（主控）：R212 的 DEF-200-516／523／524 同屬守衛面＋暴露證據，當時亦未開再評；本列母體起點＝`symptom_baseline_since`（2026-10-03）已涵蓋本機基線後全部有逐字稿的視窗，追溯不另開列。再評途中 **T2 成立**（新立 P2＝DEF-200-533，〈十四-4〉）⇒ 不開軌道① 輪、不產四件套，同窗修復＋修後重量＋結案。

## 十四-2 主控親跑的零信任重驗（量測於 2026-10-14 16:41～16:50 +08:00；每格都是當場輸出）

| 項 | 指令 | 當場輸出 | 判 |
|---|---|---|---|
| 工作樹／HEAD | `git status --porcelain \| wc -l`；`git rev-parse HEAD origin/main` | `0`；兩者皆 `33f31cc4746808342571ba4c27a85bcff81c9756` | ✅ |
| 雲端對帳 | `gh run list --commit 33f31cc4…` | push 四支 success：root-infra-ci 38528139338、AutoClaude CI 38528139237、macos-compat-ci 38528139227、windows-compat-ci 38528139226；另 schedule 二支 success（artifact-cleanup 38535512745、drift-daily 38531491817） | ✅ |
| 三本帳 | `python tools/check_defect_log_crossref.py` | rc=0：`未結存量 0 列`、`外部阻塞軌…0 筆`、`結構性長債軌…0 筆`；warning 三則＝治理文件逼近上限（`CrossPlatform_Guard_Line_History.md` 250,457／`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md` 255,495／`CrossPlatform_R213_DebtZero_FourParty_Evidence.md` 260,320 bytes）與已結列殘留待辦 3 筆（敘事引述） | ✅ |
| 交接載體 | `python tools/check_handoff_carriers.py` | rc=0：`[census] 當前輪＝R213`、tracked 載體 214 份、前瞻延後行 0、commit 訊息含宣告 0 | ✅ |
| .env 層 | `python tools/lib/quota_policy.py --env-doctor` | `[empty-local] .env 已無任何有值的行`、`結論：0 個問題 ⇒ rc=0`（env.shared 4 鍵：HALT_PCT 98、三個 MODEL_*） | ✅ |
| nightly 錨 | `python tools/refresh_nightly_anchor.py --check-head` | `✅ nightly 錨判準通過（HEAD）：nightly-run=38279403926 nightly-checked-at=2026-10-12T16:43:36+00:00（1 天前，上限 14 天）nightly-red=none` rc=0 | ✅ |
| 本機 nightly | `grep 'nightly 彙總' AutoClaude/logs/nightly_mac_*.log`；plist | 最近一次完整跑 `nightly_mac_latest.log`（RunId 20261014_074954、乾淨 HEAD 2d9a86cb）＝`===== nightly 彙總：PASS=5 FAIL=0 =====`；10-13 02:00 與 10-14 00:00:25 兩次 FAIL=1 皆 `tree_state=dirty`（52／18 entries，第三窗施工中）＝樣本無效、非回歸；`com.autoclaude.nightly` 已載入（`launchctl list` rc 0、02:00 排程） | ✅ |
| launchd 哨兵（第五窗教訓） | `launchctl list \| grep AutoSDD_Sentinel_`；`launchctl print`；逐字稿 mtime | 2 支：`f41202bc`（第五窗，預防性，逐字稿閒置 218 s）、`a4b1c822`（第四窗，閒置 13,264 s＜`GC_IDLE_SECONDS` 21,600 s ⇒ 尚未到自拆門檻，設計行為）；皆 `run interval = 900 seconds`、last exit 0、**無 halt 標記**；`ps` 只有 1 個活的 claude 行程（本窗） | ✅ 非 532 再現 |
| halt 標記殘留 | `ls ~/.autosdd/traces/halt_*.json` | 7 份（10-01～10-13；對應哨兵皆有 bootout log）＝第五窗 W5-4 理論洞原樣（只登記；`clear_halt_marker` 只在 disarm 分支呼叫） | 登記 |
| Windows pull 路徑 | `git config core.hooksPath`；`git ls-files -s tools/git-hooks/post-merge` | `/Users/wuweihong/Antigravity/AISDCL_Agent/tools/git-hooks`（`AutoClaude/tools/install_git_hooks.sh:36` 設絕對路徑、`.ps1` 同）；索引模式 `100755` ⇒ 既裝過 hook 的 Windows 機器 pull 進新 hook 當次即生效（post-merge 檔頭〈誠實劃界〉同述） | ✅ |
| PRD §16.2 | 解析結案格欄 | ✅23／⏸2（§13 使用條款人工檢核、施工圖 A7 無人續跑受控 commit/push）合計 25，與 v2.1.21 註記「25 列〔✅23／⏸2〕＋29 矩陣 ✅＝54」一致 | ✅ |
| hook 載具 | `python tools/check_hooks_liveness.py`；`readlink .venv/Scripts/pythonw.exe` | rc=0；`../bin/python`、`carrier-ok` | ✅ |
| 水位／額度 | `--check`／`--pace` | 新窗尚無 usage（harness used=92,672）；可派 2（cap 4）、binding=weekly_scoped 61%（量測於 16:40:50）、清倉 45c49b8e35 生效中 | — |

## 十四-3 補開五問再評（他機：wuweihongdeMac-Studio.local；三條指令逐字，修法前）

指令 1（`--entrypoint cli,claude-vscode,sdk-cli`；母體 26 支、permissionMode auto 24／acceptEdits 2）：

```
  Q1′a 誤擋  PASS  0／hook 阻斷 24；無 oracle 0
  Q1′b 宣稱≠阻斷  PASS  0／1 []
  Q1′c 前10呼叫被擋  PASS  1／10（≤0.25）；首呼叫被擋 0／10
  Q2′ 首查序號  FAIL  逾期或從未 2／21 [('35be7e5b', 11), ('14fb33dc', None)]；有簡報 21
  Q3′ feed 差  FAIL  10 對；max|差|=695479 [0, -325376, -695479, 0, 0, 0, 0, 0, 0, 0]；NOT-QUIESCENT 0
```

指令 2（真實層 cli／claude-vscode）：`Q1′c PASS 2／10`、`Q2′ 首查序號  FAIL  逾期或從未 1／20 [('35be7e5b', 11)]；有簡報 20`、`Q3′` 同上 FAIL。

指令 3（`--protocol-status` rc=0）：`protocol_sha256=97bbef35…（manifest 11 檔）`、`輪帳本 15 列；window_len=1`、`完整性閘 ✓`、`Q4′ session_gate_acceptance_Koala-MSI.json（win32）  PASS` 九格 ✓（generated_at 2026-10-03T22:16:53+08:00）、`Q4′ session_gate_acceptance_wuweihongdeMac-Studio.local.json（darwin）  PASS` 九格 ✓（generated_at 2026-10-06T23:46:47+08:00）。

逐行裁定（他機輪次：FAIL 只入 note、不歸零、`symptom_streak` 沿用上一列 0）：
- Q1′a／b／c：PASS（24 筆 hook 阻斷 oracle 皆 correct 或 listed；Q1′c 分子＝a8f667b5 seq5、46b55125 seq3、a4b1c822 seq8 三筆 `block_destructive_git.py` 正確攔截）。
- Q2′（真實層）：FAIL 1／20＝R201 主控窗 `35be7e5b` 首查 #11，已知成因（掌舵者貼入舊副本啟動詞、R201 4.3 #4 三方裁決「已知成因真陽性、協定不改」），與 R206 列同一筆；修法後新窗進母體 0 支 FAIL。合併層另一筆 `14fb33dc`（None）＝R212 跑法④ E2E 的 haiku 工作負載探針（entrypoint sdk-cli、37 tool_use、2026-10-12 13:16～13:55、首則 prompt「E2E④ 驗收用的小 session…一次發出 16 個 Read」），不是五問探針、未被告知先現查 ⇒ 母體衛生問題，登理論洞 W6-1（P4）；協定的 Q2′ 判讀以指令 2（真實層）為準。
- Q3′：FAIL 不是症狀而是**量測把不可比的視窗算成不一致**，主控拆解見〈十四-4〉⇒ 立 DEF-200-533、同窗修法後重量（〈十四-6〉）。

## 十四-4 發現：DEF-200-533（P2；量測器缺陷被判準直接消費即升一級；暴露＝7 份真實互動窗非構造 feed）

**現象**：Q3′ 的兩個巨大差值對應第四窗 `a4b1c822`（feed 0 vs 逐字稿 325,376）與第三窗 `7c51b538`（feed 0 vs 695,479）；其餘 10 支視窗差值皆 ≤ 4,113（在途落盤差）。

**取證（主控親跑＋QA 鏡一審訂正；第一版根因見本節末）**：
- 兩份餵數檔整個 `context_window` 全零（`total_input_tokens`／`total_output_tokens`／`current_usage` 三欄／`used_percentage` 皆 0）但 `exceeds_200k_tokens: true`、`version: 2.1.296`；寫入時刻 `2026-10-14T12:40:01+08:00`／`2026-10-14T06:12:32+08:00`。
- `~/.claude/history.jsonl`：`a4b1c822` 07:42:56 `/effort`、07:43:07 貼文、13:01:21 `/quit`，中間零輸入；`7c51b538` 前一晚開、07:41:33 `/quit` ⇒ 歸零時視窗開著且閒置、沒有 `/clear`；**但逐字稿在最後一筆 assistant usage 之後有 `system/compact_boundary`（`compactMetadata.trigger=auto`）**：a4b1c822 last usage 2026-10-14T01:11:43Z → compact 02:06:30Z（328,041→6,120）；7c51b538 last usage 10-13T20:19:06Z → compact 21:13:54Z（698,026→7,838）。`history.jsonl` 不記自動壓縮，只查 history 看不到。壓縮之後的尾端只有 `last-prompt`／`ai-title`／`mode`／`permission-mode`／`atis-latch`／`file-history-snapshot`／`cost-state`，無 usage 記錄。
- 全機 55 份餵數檔有 7 份全零（ts 10-07 13:00:01、10-09 04:00:01、10-09 13:00:01、10-10 06:36:16、10-11 08:04:20、10-14 06:12:32、10-14 12:40:01；版本 2.1.292～2.1.296；其中 3 份恰為整點 HH:00:01），逐字稿皆 1.8～5.5 MB 的長視窗；**7 份在最後一筆 assistant usage 之後皆有 auto 壓縮（7／7；主控以 compact_boundary 逐檔重驗）**；其餘 42 份有逐字稿的餵數檔（36 真值＋5 null＋1 壓縮後已有新回覆）零命中，含 12 份閒置 86～223 分鐘仍為真值者[他包回報：QA 鏡交叉表 `qa_out/compact_vs_feed.log`]。
- 成因：compaction 後 harness 把保留的 assistant 訊息 usage 歸零（harness 2.1.299 二進位字串 `Fas`：`messagesToKeep.map(iCe)`，`tLe()` 回全零物件[他包回報]）⇒ `current_usage` 全零、`total_*`=0、`used_percentage`=0；真實量級是 `compactMetadata.postTokens`（6,120～10,735）。`build_feed_doc` 照實鏡射的 0 比逐字稿（壓縮前最後 usage）更貼近現況。官方文件寫 session 第一次 API 回應前與 `/compact` 後到下一次回應前 `current_usage` 為 null；實測（7／7）有保留訊息的壓縮後視窗是全零物件、不是 null。`/clear` 會換 session id（history 兩例：fb983f48→8b41ee56、0eba5ee2→f89a3a93），與本案無關。

**影響面**：
1. 擋人判定**不受影響**：`tools/lib/harness_feed.py::measure()` 的分子（`used`／`ratio`／`tier`）取逐字稿 `scan_transcript`，feed 只供 `window`（`context_window_size` 仍 1,000,000 正確）與交叉比對。
2. `--check`／SessionStart 簡報的交叉比對行對壓縮後～下一次回覆前的 session 印 `harness used=0 逐字稿 used=325,376 差=325,376`：兩源在此態本不可比（餵數＝重設態 0、逐字稿＝壓縮前最後 usage），`DIFF_HINT`「下一次呼叫通常歸零」在此態成立，不是缺陷（理論洞 W6-4）。
3. 五問 Q3′（`audit_session.py::feed_diffs`）把該態算成兩源不一致 ⇒ FAIL；在評估機（Windows）上這會變成假的 S2 症狀（QA 鏡 F10(b)：無人值守窗在最後一次 API call 後約 55 分鐘常發生 auto 壓縮，本機 10-07～10-14 七窗八次）⇒ 量錯的尺被判準直接消費 ⇒ 依 severity.md 判 P2；暴露證據＝7 份真實互動窗（entrypoint cli）非構造性 feed。
4. `.claude/hooks/context_budget_guard.py::used_of()` 對全零 dict 回 0（只有「沒有任何欄位」才回 None）⇒ 守衛與量測器讀法一致；問題是 Q3′ 把「壓縮後～下一次回覆前」兩源本不可比的視窗算成不一致，餵數的 0 是 harness 的刻意重設態、不是被覆蓋（主控先假設讀法分歧、再假設來源被閒置重畫覆蓋，兩者皆被資料推翻）。

**第一版根因與其撤回（誠實留痕）**：主控一審前寫的根因＝「harness 閒置時定時重畫送空白 `context_window`、同 sid 歸零無合法成因」，並派 DEV-W6 做寫端 F1（`blank_rerender()` 沿用前一份餵數＋`carried_forward` 痕跡）。QA-W6 一審以 7／7 `compact_boundary` 實證推翻（Q-A REFUTED、F01 P2）：F1 會在每次 compaction 後把 ≈1% 的 context 說成 27～70%（真實 payload 重放 7／7 沿用，高估 40～89 倍），且 status line 指向本 checkout、存檔即生效 ⇒ 主控當場以 `git show HEAD:<path> > <path>` 還原 `tools/statusline_context_feed.py` 與其測試檔（`git diff` 0 行、真餵數目錄 0 個 `carried_forward` 檔）。「多在整點 :00:01」「閒置定時重畫」「逐字稿尾端只有…」三句為過度陳述，已依 QA 鏡〈文件訂正清單〉改寫。

**修法裁決（主控；SD，二審版）**：只改讀端。`session_profile()` 記 `compact_ts`（最後一筆 `system/compact_boundary` 的時刻）；`feed_diffs()` 只排除「全零 feed 且逐字稿最後 usage 之後有 compact_boundary」＝重設態、不可比、佔最近 `q3_n` 支窗位但不入 N、印 `壓縮後重設 feed N（compaction 後尚無新回覆、不入 N）`；**無壓縮證據的全零 feed 照常入 diffs（會以負值 FAIL，保留對寫端／harness 真壞的偵測力）**；`current_usage` 為 null 的 feed 由 except 元組的 `AttributeError` 接住（量不到、不入 N；原本會讓整支 `--five-question` traceback，本機 8/55 份 null）。F1 撤回；不改守衛面（`harness_feed.py` 訊息字串維持，壓縮後重設態仍會到達它、DIFF_HINT 在該態成立）。測試檔行數釘 2001 不變（免重釘）。

## 十四-5 修法與驗證（DEV-W6＝Sonnet ×1、兩輪；任務書與回報備份＝`~/.autosdd/r213_window6_scratch/w6_developer_brief*.md`／`w6_dev_result*.md`）

第一輪（寫端 F1＋讀端 F2 症狀鍵）被 QA 鏡一審推翻，F1 已還原、第一輪報告對 F2 的描述作廢；以下為第二輪（只改讀端，成因鍵）。

### 改動（只動 2 檔；零 git 寫入、真餵數目錄零寫入）
| 檔 | 內容 |
|---|---|
| `tools/probe/audit_session.py` | `session_profile()` 新增 `compact_ts`（最後一筆 `type=="system"` 且 `subtype=="compact_boundary"` 的時刻，無＝None）；`feed_diffs()` 回三元組 `(diffs, busy, reset)`：`reset = used==0 and usage>0 and compact_ts is not None and compact_ts > usage_ts`（最後 usage 之後有壓縮）⇒ 不入差值、單獨計數、與不靜止者同佔最近 `q3_n` 支窗位；**無壓縮證據的全零與偏低的非零 feed 照常入差值**；except 元組補 `AttributeError`（`current_usage` 為 null 的 feed＝量不到，不入 N；比較式放 try 內，時戳 aware／naive 混用時當量不到而非 traceback）；`show("Q3′ feed 差", …)` 末尾 `；壓縮後重設 feed {reset}（compaction 後尚無新回覆、不入 N）`。LOC 1049→1062，`check_loc_budget` rc=0 |
| `tools/tests/test_claim_provenance_r86.py` | `_feed_pair` 夾具加 `compact_ts`；三個既有 `feed_diffs` 斷言改三元組；新支 `test_an_all_zero_feed_after_compaction_is_a_reset_not_a_disagreement` 五列（reset：全零＋壓縮在 usage 後 ⇒ 不入 diffs、計數 1／bare：全零無壓縮證據 ⇒ 入 diffs 負值、計數 0／stale：全零但壓縮在 usage 前 ⇒ 同 bare／low：feed 非零且低於逐字稿 ⇒ 入 diffs／null：不崩、不入 N；reset 與 stale 的輪廓由真逐字稿經 `session_profile` 產生、誘餌＝`turn_duration` 記錄）；行數 2001 不變（30 個 docstring 收尾引號摺回上一行＋2 處 class 前空行，零資訊損失；AST 去 docstring 逐函式比對只有 `_feed_pair`、靜止閘那支與新測試有差異） |

### 主控親跑（zero-trust，不採信回報；量測於 2026-10-14 18:45～18:50 +08:00）
```
cd tools/tests && python -m unittest test_statusline_context_feed test_claim_provenance_r86 -q   → Ran 146 tests … OK   rc=0
cd tools/tests && python -m unittest test_adr_xplat001_c1c2_lock -q                                → Ran 187 tests … OK   rc=0（逐檔凍結表未重釘）
wc -l                                                                                              → test_claim_provenance_r86.py 2001／test_statusline_context_feed.py 230／statusline_context_feed.py 298（三者＝HEAD）
ruff check tools/probe/audit_session.py tools/tests/test_claim_provenance_r86.py tools/lib/governance_docs.py → All checks passed!  rc=0
python AutoClaude/tools/check_loc_budget.py → rc=0；git diff --check → rc=0
git diff -- tools/statusline_context_feed.py tools/tests/test_statusline_context_feed.py | wc -l   → 0（F1 已還原）
```
[他包回報] 突變自證（隔離複本，已刪）：M-A 排除條件拿掉 `compact_ts` 檢查（回症狀鍵）／M-B 放寬成 `used < usage`／M-C `compact_ts` 不記錄／M-D～M-I／M-K（任何 system 記錄都算壓縮）皆 rc=1；M-J（`usage>0` 放寬成 `>=0`）存活＝判決等價（差值同為 0）、N 與計數不等價，登理論洞 W6-8；M-M（無時戳壓縮記錄覆蓋有效 `compact_ts`）存活，登理論洞 W6-9；另 `session_profile` 自行解出 7／7 全零 feed 在最後 usage 之後都有 `compact_boundary`（與 QA 鏡一致）；相關回歸模組 843 支 OK（5 筆既有 Windows 專屬 skip）。

## 十四-6 修法後再評（同三條指令逐字；主控親跑 18:48 +08:00）

指令 1（母體 26 支）：
```
  Q1′a 誤擋  PASS  0／hook 阻斷 24；無 oracle 0
  Q1′b 宣稱≠阻斷  PASS  0／1 []
  Q1′c 前10呼叫被擋  PASS  1／10（≤0.25）；首呼叫被擋 0／10
  Q2′ 首查序號  FAIL  逾期或從未 2／21 [('35be7e5b', 11), ('14fb33dc', None)]；有簡報 21
  Q3′ feed 差  PASS  8 對；max|差|=0 [0, 0, 0, 0, 0, 0, 0, 0]；NOT-QUIESCENT 0；壓縮後重設 feed 2（compaction 後尚無新回覆、不入 N）
```
指令 2（真實層，母體 20 支、permissionMode auto 20）：`Q1′a PASS 0／24`、`Q1′b PASS 0／1`、`Q1′c PASS 2／10；首呼叫被擋 0／10`、`Q2′ 首查序號  FAIL  逾期或從未 1／20 [('35be7e5b', 11)]；有簡報 20`、`Q3′ feed 差  PASS  8 對；max|差|=0 …；壓縮後重設 feed 2（compaction 後尚無新回覆、不入 N）`。
指令 3（rc=0）：`protocol_sha256=5c78fbe905a3c0f522d70b6310de8e87a7b0f514494c6b64d2c10d531202e739（manifest 11 檔）`、`輪帳本 16 列；window_len=1`、`窗口內登記 raw=18（new 0＋excluded 18）`、`完整性閘 ✓`、Q4′ win32／darwin 皆 PASS 九格 ✓。

協定文本變更（manifest 變 ⇒ 輪帳本本列 `window_reset:true`，比照 R194 列 DEF-200-482 與 R207 修憲列）：`README.md` 指令 1 的 Q3′ 括號補字——「全零 feed 且逐字稿最後 usage 之後有 `compact_boundary`＝compaction 後～下一次回覆前 harness 刻意歸零的重設態（真實 context≈`compactMetadata.postTokens`），與逐字稿壓縮前最後 usage 不可比、不是兩源不一致，佔最近 `q3_n` 支窗位但不入 N、只計數印出；無壓縮證據的全零照常比對，DEF-200-533」。協定 sha `97bbef35…`→`5c78fbe9…`（只動 README 一檔；一審前的 `3922aca2…` 為第一版措辭、已被取代）。

輪帳本新列（`docs/06_quality/FiveQuestion_Round_Ledger.jsonl` 第 16 列，`round:213`、他機）：`excluded_p_le2` 18 列＝窗口 (2026-10-07, 2026-10-14] 內全部 P1／P2（512／513 為 P1＝SDD 橋接編譯 prompt／驗收閘缺陷、非 session 守門症狀故 `p1` 仍 0，其餘 16 列 P2；510～528 產品面／喚醒鏈／.env／CI、532 守衛面哨兵＝本列 S5 觸發事件、533 量測器），`new_p_le2:[]`、`symptom_streak:0`（他機沿用）；q1a～q3、q4_win（sha256 `5a600543…`、1221 bytes）、q4_mac（`4873c58c…`、1180 bytes）與 note 原文見該列。評估機輪次不是義務（README：R203 已宣告收斂，之後只在 S1～S6 成立時再評）；Windows 視窗主控若自行跑三條指令且任一行 FAIL，依 S2 處置。

## 十四-8 理論洞清單（P4；只登記；形態／來源／暴露度量法與結果／再開症狀）

| 編號 | 形態 | 來源／暴露度 | 再開症狀（可觀測） |
|---|---|---|---|
| W6-1 | Q2′ 合併層母體含非五問探針：R212 跑法④ haiku 工作負載 session `14fb33dc`（sdk-cli、無首查）被計成「從未」 | 真實 sdk-cli 逐字稿 1 支；協定判讀以指令 2（真實層）為準 ⇒ 不影響判決 | 評估機指令 2（真實層）Q2′ 因非五問探針 FAIL |
| W6-2 | 壓縮後～下一次回覆前，逐字稿側分子（`scan_transcript` 不認 `compact_boundary`）比 harness 的 `postTokens` 高估 40～89 倍（7 窗；全為閒置窗，沒有任何工具呼叫依賴該值）［QA 鏡 F10(a)］ | 真實 7 窗、無錯誤決策 | 壓縮後尚無新 usage 的窗內出現依逐字稿 used 的阻斷／簡報水位警告（`claude -r` 續跑壓縮後閒置窗的 SessionStart 簡報是最近的潛在觸點） |
| W6-3 | idle auto 壓縮在無人值守窗於最後一次 API call 後約 55 分鐘發生（本機 10-07～10-14 七窗八次，皆 `trigger:auto`、先 `away_summary`）⇒ 任一「餵數 vs 逐字稿」類量測在 Windows 評估機必會遇到；排除鍵若退回症狀鍵（純「全零」）將無法區分壓縮態與真壞［QA 鏡 F10(b)／F05］ | 真實 8 次 | 評估機指令 1 的 Q3′ 行出現 `壓縮後重設 feed N` 以外的全零 FAIL（＝無壓縮證據的全零＝寫端或 harness 真壞） |
| W6-4 | `harness_feed.check_lines` 在壓縮後重設態印 `harness used=0 逐字稿 used=… 差=…`，DIFF_HINT 在此態成立（守衛面，無暴露證據不改）［QA 鏡 F10(c)］ | 真實 7 窗、訊息面 | 掌舵者或主控依該行採取了錯誤動作（附 sid＋seq） |
| W6-5 | 7 份歷史全零餵數檔是壓縮後重設態，不需修復；Q3′ 以 `壓縮後重設 feed N` 計數；評估機若有同型歷史檔同樣計數 | 真實 7 份 | 無（設計行為） |
| W6-6 | 第五窗 W5-4：`~/.autosdd/traces/halt_*.json` 7 份舊標記殘留（`clear_halt_marker` 只在 disarm 分支呼叫） | 真實 7 份、無錯誤決策 | 任一殘留標記的 sid 被哨兵用 `claude -p -r` 喚醒 |
| W6-7 | 重設態佔窗位：若最近 `q3_n` 對大半是「壓縮後尚無回覆」，N 會掉到 `q3_min_pairs` 以下 ⇒ NOT-EVALUABLE（量不到，不會假 FAIL）［DEV-W6 第二輪］ | 構造性（真實母體 2／10） | 評估機 Q3′ 行印 NOT-EVALUABLE 且 `壓縮後重設 feed N` ≥ `q3_n`−`q3_min_pairs`+1 |
| W6-8 | `feed_diffs` 的 `usage>0` 放寬成 `>=0` 突變存活（M-J）：feed 0、逐字稿 usage 也 0 且壓縮在後的對，判決等價（差值同為 0）、N 與 `壓縮後重設 feed` 計數不等價；釘死需 +2～3 行而測試檔行數預算已滿 | 構造性（真實 `usage==0` 只見於 `<synthetic>` 佔位回覆） | 無（判決等價；N 邊界附近只可能把 PASS 變 NOT-EVALUABLE，不觸發 S2） |
| W6-9 | 壓縮記錄無時戳時以 `or` 保留前一個有效 `compact_ts` 的分支未被測試釘住（M-M 存活）；`compact_ts` 與 `usage_ts` aware／naive 混用時該對靜默當量不到（`([], 0, 0)`），〈十四-5〉相關敘述無測試 | 構造性（真實 `compact_boundary` 皆帶 `Z` 時戳） | 評估機 Q3′ 行 N 異常偏低且 `壓縮後重設 feed` 計數為 0 |

## 十四-9 掌舵者該機專屬清單（Windows；字樣與第五窗〈十三-6〉相同）

1. repo 根 PowerShell：`git pull --ff-only`。成功＝看到 `[post-merge dispatcher] env.shared 同步：0 個問題` 或 `…已自動修復，備份＝.env.bak.<UTC戳>…`。只有 `Already up to date.`＝這次 git 沒跑 hook，改跑 `python tools\lib\quota_policy.py --env-doctor` 看 `結論：0 個問題 ⇒ rc=0`。
2. 同〈十-9〉(2)～(5)；(2)(4)(5) 已由雲端 windows-latest 實跑，殘留只剩掌舵者實機特異性（cp950／Defender／排程帳號）。
3. 評估機輪次不是義務（README：R203 已宣告收斂，之後只在 S1～S6 成立時再評）；Windows 視窗主控若自行跑三條指令且任一行 FAIL，依 S2 處置。

## 十四-7 審查鏡（QA-W6＝Sonnet ×1，對工作樹全程唯讀、隔離複本做突變；任務書與回報備份＝`~/.autosdd/r213_window6_scratch/w6_qa_mirror_brief.md`／`w6_qa_verdict.md`／`w6_qa_verdict_round2.md`）

- **一審：REJECT（P1=0 P2=1 P3=3 P4=6）。** F01〔P2〕根因被實證推翻：7／7 全零餵數檔的逐字稿在最後 usage 之後有 `compact_boundary`（trigger=auto）、其餘 42 份零命中、12 份閒置 86～223 分鐘仍真值；真實 payload 重放 F1 7／7 沿用、高估 40～89 倍，且 F1 已隨工作樹生效 ⇒ 主控當場還原 F1 兩檔（〈十四-4〉）。F02〔P3〕輪帳本「18 列全部 P2」數錯（512／513 為 P1）；F03〔P3〕〈十四-4〉三句過度陳述（「多在整點 :00:01」只 3／7、「定時重畫」不成立、「逐字稿尾端只有…」漏讀壓縮記錄）；F04〔P3〕「Windows 下一視窗補評估機輪次」是無機制的前瞻期待且協定不要求。P4：F05 F2 症狀鍵過寬（QM5 存活）、F06 測試檔排版 churn、F07 W6-3 實為常態輸入、F08 他包標記範圍與變體理由、F09 S4／S5 敘述不自洽與 R212 追溯、F10 (a)(b)(c) 新理論洞。處置：F1 撤回、F2 改成因鍵（DEV-W6 第二輪）、〈文件訂正清單〉16 項全部套用（含 README 括號、DEF 列、輪帳本第 16 列、本檔各節）。
- **二審：CONDITIONAL（P1=0 P2=0 P3=1 P4=7）。** R2-F01〔P3〕輪帳本第 1 列被 `json.dumps` 重排（違反 README append-only）⇒ 以 `git show HEAD:` 還原 15 列再 append 第 16 列，`head -n 15` sha256 `cf2eb8ee…` 與 HEAD 相符、`git diff --numstat` 1 增 0 刪。P4：R2-F02 全形 `［他包回報］` 改 ASCII（已改）、R2-F03 claim 測試檔 30 處摺行與 2 處空行屬等行數慣例所許（維持）、R2-F04 `governance_docs.py` 登記註解舊因果（已改）、R2-F05 M-J「等價類」改「判決等價、N／計數不等價」（已改）、R2-F06 M-M／aware-naive 分支未釘 ⇒ 登 W6-9、R2-F07「涵蓋 R208～R213 全部視窗」絕對語改「本機基線後全部有逐字稿的視窗」（已改）、R2-F08 擬答措辭限定（採用於〈十四-11〉）。一審 F01 判實質關閉：`statusline_context_feed.py` 位元組＝HEAD、真餵數目錄 `carried_forward` 檔 0 個、因鍵在 49 份有逐字稿的餵數檔完全分離（7 份全零＝7 份壓縮後；0／42）、M-A／M-B／M-C 全紅（M-J／M-K／M-M 存活皆構造性或等價類）；三條指令與〈十四-6〉逐行 SAME、`完整性閘 ✓`、protocol sha `5c78fbe9…` 與第 16 列及工作樹 manifest 相等。
- 複審至多二審：二審無 P≤2 ⇒ PASS（範本〈審查閉環的終止〉：PASS＝無 P≤2，不是零發現）。主控對兩審的自評：第一版根因是「宣稱先於查證」的同型失誤（只看逐字稿尾端、未 grep `compact_boundary`、沒查官方壓縮契約），QA 鏡零信任重驗把它攔在落帳之前；教訓已寫入主控 memory。

## 十四-10 開了→收了

- Sonnet 子代理 2 支：DEV-W6（兩輪；突變只在隔離複本 `~/.autosdd/r213_window6_scratch/mut/`，已刪；零 git 寫入；第一輪 F1 兩檔由主控以 `git show HEAD:<path> > <path>` 還原）、QA-W6（兩輪；對工作樹唯讀；複本 `qa_copy` 已刪；`qa_out/` 腳本與日誌保留為重現材料）。任務書與回報備份＝`~/.autosdd/r213_window6_scratch/`。
- 主控 scratchpad 假餵數目錄 `feed_e2e`（F1 驗證用）：F1 撤回後其結果不再引用；真餵數目錄 `~/.autosdd/context_feed/` 全程零寫入（含 `w6-` 測試 sid 0 個）。
- 背景 Bash 1 條（根層全套，rc 見〈十四-11〉）；無 Docker、無 Monitor／CronCreate、無新 launchd／schtasks；未於全套期間跑 `--pace`。哨兵現況於 commit 前以 `launchctl list` 現查（〈十四-11〉）。

## 十四-11 結論（給掌舵者）與收尾實測

- 根層全套（主控親跑，背景阻塞式、`AUTOSDD_PARALLEL_TESTS=1 AUTOSDD_SENTINEL_OFF=1 python tools/run_root_unittests.py`）：`✅ unittest 數量下限釘選通過：發現 5384 個測試（下限 5326）`、`[cpu_budget] root-unittest workers=9`、`✅ 真實 TEMP 圍籬：…autosdd_pace*.json 零變動`、`REAL_RC=0`、FAIL／ERROR 行 0。收尾前 `launchctl list`：哨兵 2 支（`2d1f6109`＝本窗 PostToolUse 自動武裝的預防性哨兵、`f41202bc`＝第五窗）；第四窗 `a4b1c822` 已依 `GC_IDLE_SECONDS` 6 小時門檻自拆（設計行為）；真餵數目錄 `carried_forward` 檔 0 個（F1 從未在真實窗生效）。
- 三問之中：(2) PRD E2E 與 (3) .env 同步在本窗重驗仍成立（〈十四-2〉）；(1)「已知 BUG 全解」在本窗**先不成立**（五問協定 S5 再評義務未履行、再評抓到 DEF-200-533）、**同窗補開再評並修復後重新成立**（三本帳終態 0／0／0）。「可拿掉」的限定：已知缺陷歸零＋協定義務已履行；殘留只有 PRD §16.2 的 ⏸×2（§13 使用條款人工檢核、施工圖 A7 無人續跑受控 commit/push）、掌舵者 Windows 實機特異性清單（〈十四-9〉第 2 點）與 P4 理論洞 W6-1～W6-9（只登記）。
- Windows 該做的：`git pull --ff-only`（此句只對 .env 自動同步成立；其餘實機補驗分開列於〈十四-9〉）。評估機輪次不是義務（README：R203 已宣告收斂，之後只在 S1～S6 成立時再評）；Windows 視窗主控若自行跑三條指令且任一行 FAIL，依 S2 處置。
- 教訓（已入主控 memory）：根因結論必須過 QA 鏡零信任重驗才可落帳——第一版「閒置重畫」與寫端 F1 是「宣稱先於查證」的同型失誤（只看逐字稿尾端、未 grep `compact_boundary`、未對照壓縮契約），被一審以 7／7 實證攔下；Q3′ 巨大差值先查壓縮紀錄再分類；改守衛面的視窗收尾前要對照 S1～S6 把再評做掉，不留給下一窗。
