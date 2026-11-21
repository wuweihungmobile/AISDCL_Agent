# R217 工作推進軸 期 A 收尾證據（A9 單人窗口，2026-11-21）

> 範圍：R217 期 A（A1～A8、修復棒 F1～F7）的收尾連動——棘輪重釘、CI 接線、模組落點、帳本、基線、全套。
> 上游：`docs/02_architecture/WorkProgress_Axis_Design.md`、`docs/03_testing/contracts/TCS-WorkProgress-20261119.md`。
> 期 B（無人舵手 helm）、期 C（PRD 其餘修憲落款）、期 E1（`realverify coverage`）尚未動工，見〈未完成〉。

## 一、缺陷明細（帳本列只留索引，細節在此）

### DEF-200-631（舊視窗不自動關閉、又列一次待決）
掌舵者 2026-11-21 真機原話：「為何還有另一個視窗, 問同樣的問題? 是否沒有執行自動關閉機制? 這也會導致混淆或多頭馬車!」。
證據：`traces/oldwin/events.jsonl` 2026-11-21 09:35:47～09:53:03 四筆 `oldwin_not_eligible` 加 `retry_abandoned`。
成因：
1. `oldwin` 判「背景 shell 在跑」不認 TaskStop。計時 shell 已於 2026-11-20T20:48:15Z 被 TaskStop（舊逐字稿 tool_result `Successfully stopped task: b53oeig8w`，harness 不寫 task-notification），名冊永久判在跑，條件 2 三次重試後放棄。
2. `procstop` 以精確映像名比對，擋掉自動更新改名的 `claude.exe.old.<數字>.<pid>`（QuotaWall D-I）。
3. 放棄後無聲，只在 `oldwin --status` 印「請手動關閉」。
4. 舊視窗收尾又把「待掌舵者決定」列一次，掌舵者看到兩個視窗問同一件事。
修法：`oldwin.bg_shells` 以啟動 tool_result 對回 task_id 並認 TaskStop；`procstop.image_allowed` 家族判準與可降級原因；`oldwin.pending_manual_close` 於 UserPromptSubmit／Stop 每回合出聲直到舊窗關掉；`handoff.HANDOVER_CLOSING_RULE`（交棒後舊窗收尾只寫「請到新視窗回答」）；`check_pending_handoff` 對已交棒 session 不判。
回歸：`tools/tests/test_sessionctl_oldwin.py`（TaskStop／映像家族／放棄不無聲／交棒收尾規則四組）、真機 RV-OW1（替身 `claude.exe.old.*` 被關、真在跑 shell 的替身不被關）。

### DEF-200-632（真機驗證載具外洩）
掌舵者 2026-11-20 回報幽靈 session `57d0ccad`。RV-PR3 沙盒案例 `park --at` 登記正式前綴 `AutoSDD_HandoffSpawn_*` 排程，代理撞額度未清理，到點真開視窗 `claude -r` 於沙盒。自 11/18 起 17 筆沙盒 park 排程進正式前綴、11 筆真觸發含 2 次 spawn（`60d60c34` 08:03、`57d0ccad` 10:47）；交接包漏進真實 `~/.autosdd/handoff`。
止血：驗身分後砍行程樹、刪沙盒、八檔移入 `~/.autosdd/handoff/_quarantine/`（保留證據）。根治走 R218-B（PRD v2.1.25 §11.9 R-VER-1～6）。
RV-SK2（OI-20261120-005，24 小時、4 次以上 reset 的 soak）排程由主控停用，重開條件＝R218-B 哨兵前綴隔離落地。

### DEF-200-633（22:42 park 到點未續跑）
2026-11-20 22:42 park RESUME 先關舊窗（pid 41752＝仍開著的本視窗）被拒 `image_not_allowed` ⇒ spawn 未呼叫 ⇒ `spawn_rc=1`、排程撤銷、無備援。映像家族部分由 DEF-200-631 修；其餘（失敗不得無聲、視窗開著時以 session 內背景等待為主載具）屬 QuotaWall。

### DEF-200-636（期 E1／B 缺口）
- `realverify run-driver` 第 7 步呼叫不存在的 `realverify coverage --write`，結果恆標 `coverage=failed`（DES §15、D-18；DES 允許降級）。
- 全部案例模組都沒有宣告 `SOURCES` ⇒ `openitems scan --stale-pass` 在真 repo 永遠開 0 列（REQ-WP-17 實質空轉）。
- `scan --stale-pass --dry-run` 只出現在 TCS E2E-WP-23，DES §8-4 與 verbs 都沒有。
- 期 B 的 `helm-check`／`helm-status`／playbook 生成器整個 repo 零實作（A6g 查證）。

## 二、A9 收尾決策（有文件依據、他機可重現）

1. **`immutable_records`（`docs/06_quality/OpenItems_Protocol/params.json`，`tools/lib/openitems/scan.py`）**。A8 種子曾在 SI 觀察帳本 OBS-SI-372／397 與四問答案檔 `RUN-SI-010.md` 內插入 OI id，`si check` 因此判 `ROW-MUTATED` 與 `FOURQ-SHA-MISMATCH`（逐字封存紀錄被改一個字就破壞雜湊）。已還原三處，並讓掃描器對 `immutable_records` 命中的檔不判。這是對 TCS 「不留豁免名單」的偏離，唯一理由是封存紀錄的雜湊完整性；清單只有兩條（SI 觀察帳本、`_fourq/**`），新增須同樣寫 WHY。
2. **A7 測試併檔**：`test_waste_census_wake_pace_r217.py` 併入 `test_waste_census_metrics.py`（AT-QP-56～63 原指定落點），`-p "test_waste_census*.py"` 前後同為 Ran 70 OK。
3. **`--grace-sec` 移除**：全 repo 呼叫端 0 處（TCS／R216 證據檔內的兩處為凍結史料，不改）。
4. **OI-20261121-003**：新立一筆 human 項（帳本承接列＝DEF-200-636、DEF-200-632、DEF-200-633、DEF-200-637），承接 R217 期 B／E1 與 R218（QuotaWall＋副作用隔離）的實作與驗收，讓 PRD 兩列與 QuotaWall 設計附錄的「實作與驗收尚未完成」字樣有 OI id。原先分立的 001／002 因人工清單上限 7（`human_cap`）會讓完成閘每個 session 多出一行「人工清單已滿」而合併，兩筆已 `retire`（帳本只增不刪）。
5. **PRD 修訂表 v2.1.23 列**：依 DES 附錄 A-1 逐字落款（RV-WP40 逐字比對），兩處占位依實況改寫：R217 QA 審查尚未執行、R216 QA 紀錄座標＝`CrossPlatform_R216_SessionSwitch_CostModel_Closure_Evidence.md`。A-2～A-11（名詞表、就地註記、§4.5.x 新節、§16.6 新列）屬期 C，未落款。
6. **輪號標籤**：F5／F7 在程式註解自稱 R218，與帳本當前輪不符（`current_round()` 取 R 系列證據檔名最大號＝本檔 R217）；六處註解改回 R217（類別名 `R218F7*` 為識別字，保留）。
7. **AutoClaude 全套寫真 `checkpoints/`（DEF-200-634）**：`tests/conftest.py` 新增 autouse `_hermetic_default_checkpoint_dir`，出廠預設改指 tmp；全套前後檔數 2273→2273。
8. **`test_escalated_family_reopens_only_after_a_newer_commit` 時間炸彈**：測試用寫死的 `T0`（2026-11-20）當升級戳，而 `drive` 事件取牆鐘，牆鐘超過 T0 後 fold 把升級排到 drive 之前、列回到 driven。升級戳改為「該列最晚事件加 1 秒」，與牆鐘無關。

## 三、理論洞清單（守衛面准入 P4，不修）

| # | 形態 | 來源 | 暴露度量法與結果 |
|---|---|---|---|
| 1 | `tools/session_resume_planner.py:504-509` `probe_quota` 逾時不殺孫行程 | RV-PX33 以 ping shim 構造，牆鐘 151 秒對預期 90 秒 | 構造性（shim），無真機回報、真逐字稿零命中 ⇒ P4，不立輪、不修；任一暴露證據出現再升 P2 |

## 四、驗證輸出（當回合真跑；數字見下，來源為本棒 tool_result）

- 根層全套（`AUTOSDD_PARALLEL_TESTS=1 python tools/run_root_unittests.py`，含 selfimproving）：發現 7528 個測試，收尾時剩 5 項只能在 commit 後轉綠（4 項「追蹤檔 import 未追蹤檔」須 `git add`，1 項為 `.claude/hooks` 兩處註解的輪號標籤，須套用 diff）。
- AutoClaude 全套 `--dist loadgroup`：5935 passed、7 skipped；`ruff check` 全過；`lint-imports` 8 kept／0 broken；LOC 預算違規 0。
- `python tools/selfimproving.py check`：overall=PASS；`openitems scan` unmapped=0、`list` undriven=0。
- 缺陷帳本 `check_defect_log_crossref.py`：僅「淨額棘輪」一項（本輪新增未結 4 筆、結案 0 筆）要在 commit 時以發現輪逃生口 `AUTOSDD_NET_RATCHET_OFF=1` 通過。

## 五、未完成
- 期 B（無人舵手）、期 C 其餘修憲落款、期 E1（`realverify coverage`／`ASSERTS`）。
- ONBOARDING §7 表②（Windows 欄 AutoClaude 等四格）指紋 presumed stale：`--write --with-slow` 需乾淨 venv 實跑（本機 venv 含 PG 額外套件會使 passed 虛高，工具預設拒絕）。
