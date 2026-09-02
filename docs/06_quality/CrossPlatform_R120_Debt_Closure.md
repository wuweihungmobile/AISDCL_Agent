# CrossPlatform R120 技術債清償證據檔

> 輪籤：R120（技術債總清償循環令第三投；收尾單人窗口）
> 範圍：P1-7（SD-4／SD-8）落地 ＋ SA-4 實彈取證 ＋ P1-5/DEF-200-212 結案批（D8 裁決）
> ＋ P1-8 案檔盤點注與 R110 另案立列 ＋ 守衛線重釘。

## §1 P1-7：SD-4＋SD-8（tools/lib/relay_machine.py）

- **SD-4**：`settle_window()` 的 RELAY_NEXT 分支，`_register_and_record` rc≠0 時不再裸
  `return rc`＋記 `relay_spawned`（含 credential 的假成功痕跡），改記 `relay_spawn_failed`
  ＋loud alert＋拆自己的 -Once＋`_rearm_after_stop`（自帶清閂＋loud）＋`relay_rearmed`／
  `relay_rearm_failed` 痕跡＋回傳排程 rc（rearm rc 不覆蓋）。`relay_seq` 不回退（fail-safe）。
- **SD-8**：settle_window 主體自 `now = ...` 起包 try/except；`planner = _planner()` 留
  try 外。災難 handler 結構＝兩個 disposal（`_schtasks_remove`／`_rearm_after_stop`）
  **裸放在 handler 最前**，alert／append_log 殿後各包窄 try。此結構由結構鎖
  `test_the_settle_window_delegate_really_disposes`（test_context_budget_guard.py:7954-）
  的 dominator 演算法強制：把 disposal 包窄 try 時支配集合退化為 `['_planner']` 而真的紅
  （實測）。誠實劃界：disposal 自身拋例外仍會炸穿——結構鎖與二次防護的顯式取捨。

驗證（實作棒實跑）：新測試三案＋既有 relay 家族＝12 passed；結構鎖家族 7 passed；
六個突變逐一驗紅後還原；整支 test_context_budget_guard.py＝533 passed（+207 subtests）。

## §2 SA-4 實彈取證（headless 窗口，production 同形 argv）

argv 形狀對齊 `resume_route.fresh_argv`（`--permission-mode acceptEdits --settings
.claude/settings.unattended.json --add-dir <task> <handback>`）。

| 面 | 指令 | 結果（逐字取證） |
|---|---|---|
| allow 正面 | 無頭窗口以 PowerShell 工具跑 `git status` | 無權限阻擋，直接執行；輸出前三行＝`On branch main`／`Your branch is ahead of 'origin/main' by 2 commits.`／`(use "git push"...)` |
| allow 正面 | `Get-Date` | 無阻擋，輸出 `2026年9月2日 上午 09:10:24` |
| deny 面 | 無頭窗口以 Write 工具改寫 `.claude/settings.unattended.json` | 被拒（`File is in a directory that is denied by your permission settings.`）；`git status` 對該檔零輸出＝檔案零改動 |

**取證副產物＝DEF-200-245**：每次 spawn 的 stderr 噴 6 行
`Permission deny rule (...): Write(...) is not matched by file permission checks —
only Edit(path) rules are.`——證實 settings.unattended.json 的 6 條 Write/NotebookEdit
deny 是死規則（harness 檔案權限只比對 `Edit(path)`，且 Edit 規則涵蓋所有檔案編修工具）。
既有「deny 已實彈驗證」引據（R115）實為此警告被 err[:300] 截斷的前綴，引據錯；保護當時
仍由 Edit 規則成立。修法＝移除 6 條死規則、va3 鎖改 `Edit(path)` 承重＋死規則歸零斷言。

## §3 P1-5／DEF-200-212 結案批（D8 裁決）

死結＝兩條各自正確的紀律相乘：帳本「發現情境」欄零輪號紀律使 `current_round()` 凍結在
R100（自動祖父化永不觸發）× 具名豁免面 shrink-only 禁增長 ⇒ 歷史前瞻行只能逐筆進豁免
表、表又不准長。且 212 自身結案動作再生同型假陽性（212 轉 fixed 後判準② 新增 4 行、
判準① 因 commit `0398226` 承接載體消失新增 1 行）。

D8 裁決（存證 AutoSDD_Adjudication_Record_R120.md）：
- `_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES` 3→5，登記 2 筆豁免鍵
  （R113_HANDOFF.md／CrossPlatform_R113_Ledger_Closure.md × DEF-200-212）；
- DEF-200-212 → `fixed@R120`；
- 結構根因另立 **DEF-200-241**（承接輪次 R121，狀態欄具名輪次 ≥ R118 以補 commit
  `0398226` 判準① 承接載體——不然 pre-push 快層擋下）。

驗證：`check_handoff_carriers.py` rc=0＋`--self-test` rc=0（27 行）；帶
`AUTOSDD_NET_RATCHET_OFF=1` 的 `check_defect_log_crossref.py` rc=0；帳本六列 byte
（212＝692／241＝623／242＝507／243＝382／244＝462／245＝631，皆 ≤700）。

## §4 P1-8 盤點（案檔注＋R110 另案立列）

- Pacing／BurnDown 兩案檔各補【2026-09-02 P1-8 盤點注】：僅 Pacing §9 W2.5 標「已由實作
  超越」（`_REPIN_NET_CAP_DUE_ROUND=109` 到期義務已在常態棘輪兌現），其餘實作條款誠實標
  「Adopted 待落地」（座標表零行號漂移）；兩張待裁決表標「已由裁決超越」（R110）。
- Playbook :250/:259「(a) 可先行」依 R110 Q3 同步為「補證據門檻後獨立 gated」。
- R110 §3 另案清單三筆立列（P1-8「未覆蓋的立列」）：DEF-200-242（free 帶 cap 恆 None，
  Q6 (i)）／DEF-200-243（windows() 鄰軸繼承，Q9 (ii)）／DEF-200-244（gate 聚合面第三通道，
  Q9 末項）。

## §5 守衛線重釘

- 護欄層淨額三元組：**91646 → 91793（+147）**（本輪 repin log 三列：+130 P1-7／va3、
  +9 本表首輪編修、+8 sha 鏈列與收斂）。`test_context_budget_guard.py` 9645→9775、
  `test_adr_xplat001_c1c2_lock.py` 7178→7195；`_REPIN_LOG_FROZEN_PREFIX_LEN` 107→110、
  `_FROZEN_PREFIX_REWRITE_LEDGER` 追加 R120 鏈列（`4554dbed`→`31861e`）、
  `_REPIN_LOG_HISTORY_SHA256` 重釘 `31861e...`。`--print-guard-lines` 淨額對帳 +0、
  逐檔漂移 0 支。
- 🔴 款(11)：R118 淨額 -6 已終止 streak、R119 +399＝第 1 連升、R120 +147＝第 2 連升（合規，
  `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`）⇒ **下一輪（`R121`）淨額必須 ≤0**。

## §6 淨額棘輪逃生口說明

本輪 crossref 淨額棘輪＝新增未結 4（241/242/243/244）＞ 結案 1（212）＝淨增 3，觸發。
本輪本質＝P1 落地輪＋P1-8 盤點發現（循環令 D6 明文「落地輪 P0~P1 計解鎖件落地數、不計
淨減」）：241＝212 治本根因、242/243/244＝R110 §3 明文要求另立的另案清單。故本機驗證以
`AUTOSDD_NET_RATCHET_OFF=1` 單獨給 crossref 放行；push 無需帶該 env——淨額棘輪比
`git show HEAD` vs 工作樹，commit 後 HEAD 含新列、差集自然歸零（`ledger_closing_guards.py`
`net_new_vs_closed_problems()` 比較基準）。
