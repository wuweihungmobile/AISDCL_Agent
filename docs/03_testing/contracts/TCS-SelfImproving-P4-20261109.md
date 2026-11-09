# Test Contract Specification — SelfImproving P4（自動演化排程：日曆格到期模型、`sched`／`patrol` 動詞、`sched.set`／`sched.skip` 事件、`status.schedule`、`check` 兩新項、run-scoped 無人值守授權、無人運轉執行器、待入帳自動入帳與核准後機械步驟推進、OS 任務與包裝腳本）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層半，Console 半另有 `TCS-SelfImprovingSchedule-20261109.md`）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（PRD v0.13 於 Stage-1 重凍）的單一 Feature（P4 階段，根層半）；單一 FSM 功能鍵 `monorepo-si-p4-schedule`（`spec-frozen --doc` 指向本檔）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P4-20261109.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-005 |
| **Feature 名稱** | SelfImproving P4：自動演化排程（根層半）——日曆格到期模型與七種跳過、`sched`（`show`／`set`／`arm`／`disarm`）與 `patrol` 兩個動詞、`run-open` 增補（`--trigger f`、Console `run-request` 載體）、`sched.set`／`sched.skip` 兩種事件、`status.schedule`、`check` 兩新項、`params.json` 九個新鍵、run-scoped 無人值守授權（`unattended`）、無人運轉執行器（`patrolrun`、`patrolbrief`）、待入帳自動入帳與核准後機械步驟推進（含本機 commit、不 push）、OS 任務 `AutoSDD_SI_Patrol` 與包裝腳本 `tools/si_patrol_tick.ps1`、`runner.run_argv`、能力登記增八鍵、Operations SOP 兩節與〈啟動條件〉〈P2 動詞〉增補 |
| **User Story** | US-401～US-406 |
| **建立日期** | 2026-11-09 |
| **QA 負責人** | SelfImproving P4 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SD 棒，實作者＝Developer 棒加主控〔收尾、真機驗收、重釘儀式〕，三方不同） |
| **FSM 功能鍵** | `monorepo-si-p4-schedule`（PRD §9.6 P4 列；開工先做 BRIDGE §8.4 基線採納；Console 半鍵 `agentconsole-si-schedule` 依賴本鍵 RELEASE） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（上位文件＝`docs/01_requirements/SelfImproving_PRD.md`〔v0.13〕與 `docs/05_development/SelfImproving_Operations_SOP.md`）的單一 Feature。未列入追溯表視為未滿足；引用不得指向未凍結文件。**凍結檔不得再改**：PRD 需修訂處一律寫在 §7 的 ⚖ 清單與〈PRD 修訂建議〉；PRD 未定而本檔為使其可測補定義者標「本檔類推」並列入 §7.1。**體例沿 P3 TCS**（`docs/03_testing/contracts/TCS-SelfImproving-P3-20261024.md`）：AT 格式、斷言簡寫（`M`、`MJ`、`snap`）、驗收字樣、判定指令與 `-k` 錨定規則、hermetic 環境、零殘留的定義，一律「沿 P3 TCS §2 開頭與 P2 TCS §2 開頭」，本檔不複寫。

### FRD-lite

**現況與變更（Before／After；brownfield；現況數字皆撰寫時現查）**

- Before：(1) `tools/selfimproving.py` 有 24 個動詞（`_HELP` 24 鍵，含議題中心的 `issues`），`check` 33 項（`CHECK_RULES_REV` 4），`params.json` 32 鍵，能力登記 `CAPABILITY` 51 鍵（39 `ro`／8 `rw`／2 `net`／2 `exec`），`events.KINDS` 21 個、`run.open` 的 `trigger` 寫死 `abcde`；(2) `decwrite.refuse_unattended` 已被 `decide`、`card --issue`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`obs-add`、`obs-close` 呼叫、`measure` 自檢，**P1 動詞**（`run-open`、`run-close`、`attr*`、`prop-*`、`research`）無檢查；(3) 不存在：任何排程狀態、`sched`／`patrol` 動詞、`sched.*` 事件、巡邏包裝腳本、`AutoSDD_SI_Patrol` 任務、`runner.run_argv`、`status.schedule`；`status` 物件 15 鍵（末鍵 `measure`）；`consoleaudit.KINDS` 只有 `decide`、`obs-add`、`obs-close`；(4) `scheduled_task_expectations.json` 與 `install_windows_nightly.ps1` 只管兩支任務（nightly、smoke），`test_install_windows_nightly.py::TestScheduledTaskExpectationsSsot` 三層鎖綁「任務集合逐字相等」與「全任務同一小時數、同一套用手段表」。
- After：新增 8 支套件模組（`ro`：`sched`、`unattended`、`patrolbrief`、`schedcheck`；`rw`：`schedwrite`；`exec`：`patrol`、`patrolrun`、`schedarm`）、2 個動詞（`sched`、`patrol`，共 26 個）、`run-open` 的 `--trigger f`／`--due-at`／`--carrier console --audit-ref`、`runner.run_argv`（明示環境入口）、`consoleaudit` 增 `sched-set`／`run-request` 兩個 `kind` 與其 `body` 判準；`events.KINDS` 23 個；`check` 35 項（`CHECK_RULES_REV` 5）；`params.json` 41 鍵（加九個 `sched_*`）；`status` 16 鍵（末鍵 `schedule`）；能力登記 59 鍵（43／9／2／5；若實作輪因 `events.py` 逼近 400 而拆 `evspec`〔`ro`〕則為 60 鍵、44 `ro`，兩態擇一，R160）；安裝器整組三支任務、`si_patrol_tick.ps1`、期望表加一筆；SOP〈巡邏與無人運轉（P4）〉〈無人運轉任務書範本〉兩節（PRD 提交時已落檔）與〈啟動條件〉〈P2 動詞〉增補的機器可判化；PRD §8.1 P4 出口 (a)～(f) 的真實運轉列為實跑檢核 V30～V35。
- **本檔不含**：AgentConsole 三層（Bridge 兩個 POST、backend 兩個 POST 與 Flyway CHECK 改版、frontend 面板；見 `TCS-SelfImprovingSchedule-20261109.md`）、P4 出口 (a)～(f) 的真機運轉（V30～V35，不入 AT，AT 不碰真帳本與外網）、`sched_auto_push` 為 true 的語意（PRD §9.7 #88：只准 false）、macOS 實跑（標「未驗」）。

**AC 編號規則**：PRD `AC-SI-NN-Y`（NN＝36～39）在 AT 的 ID 以 `AT-4NN-Y-…` 表示（百位 `4`＝P4，沿 P3 的 `AC-SI-22-1`→`AC-322-1` 體例；本檔 §1、§6 一律寫 PRD 全名 `AC-SI-NN-Y`，AT ID 內的 `4NN` 即其縮寫）；本檔自增 AC 帶階段前綴 `AC-P4-040-1`～`AC-P4-040-8`，其 AT 以 `AT-440-Y-…` 表示（第 Y 個自增 AC）；AT 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，負控／邊界 `AT-<NNN>-<Y>-E-<n>`；判定指令的 `-k` 一律為錨定名（AT 底線形接結尾底線）。**AC 數**：PRD 24 個（FR-SI-36 六、37 五、38 八、39 五）加自增 8 個合計 32 個；其中 `AC-SI-37-4`（Console UI 控件）**在本檔無 AT**（由 Console TCS 判定，根層半的契約面以 `AT-437-3-1`、`AT-437-3-2` 釘住），其餘 31 個皆有至少一個 AT；§1 共 105 個 AT（正控 56、負控 49）。

**P4 交付物**（D1～D12）

| 編號 | 交付物 | 路徑（相對 monorepo 根） | 製作者 | 主要驗證 |
|------|--------|--------------------------|--------|----------|
| D1 | 排程模型與狀態折疊、`schedule` 形狀、七種跳過的純判準、黑窗解析（`sched`）；`check` 兩新項（`schedcheck`）；run-scoped 授權閘（`unattended`） | `tools/lib/selfimproving/{sched,schedcheck,unattended}.py`（新，`ro`） | Developer | AC-SI-36-1、36-2、37-3、37-5、38-3 |
| D2 | `sched set`／Console 入帳、`run-open` 增補、`sched.skip` 寫入（`schedwrite`）；`consoleaudit` 兩新 `kind`；`events.py` 的 `KINDS`／`_SPEC`；`decwrite.refuse_unattended` 與各 P2 動詞改呼叫 `unattended.gate`（單一實作） | `schedwrite.py`（新，`rw`）；`consoleaudit.py`、`events.py`、`decwrite.py`、`writeverbs.py`（改，`writeverbs` 現 382、上限 400）；入口 | Developer | AC-SI-37-1、37-2、38-3 |
| D3 | 巡邏心跳編排、運轉執行器、任務書生成、OS 任務封裝（`patrol`、`patrolrun`、`patrolbrief`、`schedarm`）；`runner.run_argv` | `patrol.py`、`patrolrun.py`、`schedarm.py`（新，`exec`）、`patrolbrief.py`（新，`ro`）；`runner.py`（改） | Developer | AC-SI-36-3～36-6、38-1、38-2、38-4～38-8、39-1～39-5 |
| D4 | `status.schedule`、`export` 同函式、`console_pending[]` 兩新 kind、`params` 九鍵與界驗證 | `status.py`、`export.py`、`params.py`（改）；`docs/06_quality/SelfImproving_Protocol/params.json`（加九鍵，與 `PARAM_SPECS` 同 commit） | Developer | AC-SI-37-3、37-5；AC-P4-040-2 |
| D5 | 安裝器整組三支、期望表加一筆、包裝腳本 | `tools/install_windows_nightly.ps1`、`tools/scheduled_task_expectations.json`（改）；`tools/si_patrol_tick.ps1`（新，CRLF） | Developer | AC-SI-36-4 |
| D6 | 入口新動詞與登記 | `tools/selfimproving.py`；`tools/tests/test_selfimproving_capability.py` 的 `CAPABILITY`（+8 鍵） | Developer | AC-P4-040-3、040-7 |
| D7 | Operations SOP 條文的機器可判化（SOP 本文已於規格 commit 落檔，實作輪只在判準與 SOP 不符時回報⚖，不就地改 SOP） | `docs/05_development/SelfImproving_Operations_SOP.md`（唯讀） | Developer（判準作者） | AC-P4-040-4 |
| D8 | P4 夾具與既有測試的同步站點（零退化） | `tools/tests/_selfimproving_p4_fixtures.py`（新）；既有 P0～P3 與議題中心測試的 R163 站點（改） | Developer | AC-P4-040-5 |
| D9 | AT 錨定可重跑檢查與範圍守衛 | 併入 `test_selfimproving_schedule_gate.py` | Developer | AC-P4-040-6、040-8 |
| D10 | 基線文件同步（`SelfImproving_LedgerDb_P0_Baseline.md` 的 `params.json` 雜湊與位元組數、判準指紋、`CHECK_RULES_REV` 三列） | `docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md` | Developer | AC-P4-040-5 |
| D11 | 真機運轉（P4 出口 (a)～(f)） | 真帳本、真 OS 任務、真 Console（唯主控與掌舵者） | 主控；掌舵者 | V30～V35（不入 AT） |
| D12 | Console 半連動（主控處理）：Console 側黃金檔 G6～G9 與 `consoleaudit` 簽章對象一致（AT-437-1-3）；Flyway 版本**現查最大版本＋1**（本檔不寫死版號） | `AgentConsole/**`（本棒不碰） | 主控；Console 棒 | AT-437-1-3；Console TCS |

**提交順序與責任**

- 依賴序：D8（夾具與同步站點先行，否則既有測試的項數、鍵數、動詞數斷言轉紅）→ D4 的 `PARAM_SPECS` 與 `params.json`（`sched`、`status`、`check` 讀它們）與 D10 基線三列（同 commit）→ D2 的 `events.py`／`consoleaudit.py`（欄位表與稽核 `kind`）→ D1 → D2 的 `schedwrite`、`unattended` 接線 → D3 的 `runner.run_argv` → `patrolbrief` → `patrol`／`patrolrun`／`schedarm` → D5 → D6 入口與登記 → D7。每支程式完成立即跑該區 AT，不累積（根 `CLAUDE.md` 共通紀律第 2 條）。
- **鎖的持有面不得拆給並行包**（鐵律七）：PKG-ROOT-SCHED（`sched.py`、`schedcheck.py`、`unattended.py`、`schedwrite.py`、`consoleaudit.py`、`events.py`、`fold.py`〔本包不得改〕、`status.py`、`export.py`、`params.py`、`params.json`、`decwrite.py`、`writeverbs.py`、入口 `sched` 與 `run-open` 增補、`check` 兩新項、基線文件、同步站點測試）與 PKG-ROOT-PATROL（`patrol.py`、`patrolrun.py`、`patrolbrief.py`、`schedarm.py`、`runner.py`、`install_windows_nightly.ps1`、`scheduled_task_expectations.json`、`si_patrol_tick.ps1`、入口 `patrol`）。**兩包持有面不重疊**：共用檔 `events.py`、`status.py`、`params.py`、`consoleaudit.py`、`unattended.py` 歸 SCHED 包，PATROL 包只讀（`patrol.py` 只呼叫其公開函式）；`tools/selfimproving.py` 入口與 `CAPABILITY` 表兩包都要動，故**入口檔與登記表的合併由收尾單人窗口做**（PATROL 包交 handback 片段、不直接改入口）。結論：**可並行，但 PATROL 包的整合測試（`test_selfimproving_schedule_patrol.py`）須等 SCHED 包的 `events`／`sched`／`unattended` 落地後才能全綠**，故建議 SCHED 先行（約半棒）、PATROL 後接；若要並行，PATROL 棒須先以 §5.6 的函式簽章建議自備替身，合併時主控親驗。
- 真帳本與真事件帳本只由主控寫（PRD C1）：Developer 棒不得碰真 OBS 帳本、真事件帳本、真 `SelfImproving_Proposals/`，**也不得註冊真的 OS 任務、不得 spawn 真的 `claude`、不得讀真的 `AgentConsole/.env`**；AT 一律在 tmp 的合成 repo 內進行（`AUTOSDD_SI_DIR`、`CLAUDE_CONFIG_DIR` 指向 tmp）。重釘儀式（護欄層行數棘輪、`tools/tests` 檔數下限與 E501 棘輪、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE`、compat-ci `paths` 覆蓋）由主控單人窗口於同一個 commit 收齊，**屬實作輪收尾步驟，不是設計缺口**，實作者不碰鎖檔（NFR-P4-8）。

**〈P4 行為規則〉**（R137～R167；各 AT 以 R 編號引用；P0～P3 的 R1～R136 在其範圍內不變，P4 的重定與擴充見 R139〔`events`〕、R140〔`check`〕、R153〔run-scoped 授權取代 P2 R70 的「一律拒收」與 P1 動詞的「照常」〕、R158〔`status`〕、R159〔`params`〕、R160〔能力登記〕、R163〔既有測試同步站點〕）

*A. 介面、rc 與輸出（PRD §9.3；旗標細部為本檔類推，§7.1 ⚖ 7）*

- **R137 動詞與旗標**：P0～P3 與議題中心的 24 個動詞語意不變，唯 R153 的授權規則、`run-open` 的增補；新增 `sched`、`patrol` 共 **26 個**，頂層 usage 列出 26 個動詞；未列動詞名一律 rc 3、stdout 空、stderr 至少一行。共通旗標 `--repo DIR`、`--json` 沿 P1 R27。

| 動詞 | 旗標（＊必備） | 讀寫與事件 | rc |
|------|----------------|------------|-----|
| `sched show` | `--json`、`--now <ISO，須帶 offset>` | 唯讀；`armed` 在主機現查 OS 任務 | 0＝已輸出、3＝用法（含 `--now` 缺 offset） |
| `sched set` | `--enabled {true｜false}`＊、`--period-minutes N`、`--reason <一行>`、`--by <角色>`＊、載體三擇一：停用方向免引言（`carrier=host`）／`--sid <UUID> --line <N>`（`carrier=transcript`）／`--carrier console --audit-ref <uuid>` | 只寫 `sched.set` | 0＝已寫、1＝拒收、3＝用法 |
| `sched arm`／`sched disarm` | `--json` | 改 OS 任務（經 `runner.run_argv`）；不寫事件 | 0＝已執行且憑證已驗、1＝拒收（無憑證、`AUTOSDD_UNATTENDED` 有設、elevation 不足）、3＝用法 |
| `patrol` | `--now <ISO，須帶 offset>`、`--dry-run`、`--json`；**不收 `--run`** | 寫事件、OBS 帳本、主工作樹（promote／commit）、家目錄 | 0＝心跳已跑完（含「無事可做」「有跳過」「已有巡邏在跑」「`AUTOSDD_SI_PATROL_OFF` no-op」）、1＝拒收或未預期例外（`AUTOSDD_UNATTENDED` 有設＝`UNATTENDED-REFUSED`）、3＝用法（`--now` 缺 offset、`--repo` 非目錄、`HOME-UNWRITABLE`） |
| `run-open`（增補） | `--trigger {a｜b｜c｜d｜e｜f}`＊、`--coord`＊、`--by`＊、`--due-at <ISO>`（`f` 必帶）、`--carrier console --audit-ref <uuid>`（限 `--trigger a`） | 寫 `run.open`（或 Console 載體遇未關運轉時改寫 `sched.skip`） | 沿 P1 R27；P4 追加碼見拒收碼表 |

  rc 通則沿 P1 R27／P2 R68：用法錯誤（rc 3）先於一切；`sched show`、`status`、`export` 唯讀；`sched set`、`sched arm`／`disarm`、`patrol` 於 `AUTOSDD_UNATTENDED` 有設時一律 rc 1、零寫入（R153）。成功輸出形態：`sched show` 文字首行 `schedule: enabled=<true|false> period=<N> cell=<cell_start>/<cell_end> overdue=<true|false|null>`，其後 `last_set:`、`last_skip:`、`armed:` 各一行；`--json`＝R158 的 `schedule` 物件。`sched set` 成功行沿 `decwrite.ok_out` 形（`ok sched.set seq=<N> enabled=<…> period=<…> carrier=<…>`）。`patrol` 成功輸出為逐步驟一行 `step=<巡視|入帳|到期|運轉|推進> result=<…>`；`--json` 為鍵序 `ok`、`kind`（字面 `patrol`）、`dry_run`、`steps`（`[{"step","result","detail"}…]`）、`events`（本次追加事件的 `seq` 清單）。
- **R138 `sched set` 的載體與界**：(a) **停用方向**（`--enabled false`）免引言：`carrier=host`、`by` 為 `--by`（值域 P1 R27）；`--period-minutes` 缺＝沿用目前生效週期（無則 `sched_period_minutes_default`）；(b) **啟用或改週期**（`--enabled true`，或 `--period-minutes` 與現值不同）須人的引言：`--sid`＋`--line`（`carrier=transcript`，經 `decverify.verify_human_ref` 只驗載體與出處、不驗卡面）或 Console 載體（R146）；缺引言＝rc 1、碼 `SCHED-QUOTE-REQUIRED`；(c) `period_minutes` 須為整數（非布林）且在 `[sched_period_minutes_min, sched_period_minutes_max]`（取當下 `params.json`），否則 rc 1、碼 `PERIOD-OUT-OF-RANGE`；(d) `--reason` 沿 R141 的字串規則；(e) 零殘留沿 P2 R71（rc 1 時事件帳本位元組不變）；(f) `sched arm`／`disarm` 不需引言、不寫事件、憑證現查（R161）。

*B. 事件欄位表與 `check`（PRD §9.2〈P4 增補〉、§9.3 `check` 列）*

- **R139 `events` 的 P4 增量**：`KINDS` 21→**23**（加 `sched.set`、`sched.skip`；「不在 N 個詞彙內」訊息隨改為 23）；兩者**不入** PROP／RUN 折疊（`fold._apply` 對其不處理；`fold.py` 本棒不改）。欄位表（共通鍵 `seq`、`t`、`kind`、`by` 之外；表外鍵＝`EVENT-KEY-UNKNOWN`、缺必備鍵＝`EVENT-KEY-MISSING`、型別或值域不合＝`EVENT-TYPE`）：

| kind | 必備鍵與型別 | 條件 |
|------|--------------|------|
| `sched.set` | `enabled`（布林）、`period_minutes`（整數 ≥1，非布林）、`carrier`（`console`｜`transcript`｜`host`） | 選填 `reason`（單行、≤120 code point）；`carrier=console` 另必備 `audit_ref`（UUID）、`audit_sha256`、`key_id`（8 碼 hex）、`decider`（`^[A-Za-z0-9_.-]{1,64}$`）；`carrier=transcript` 另必備 `sid`（UUID）、`line`（整數 ≥1）；`carrier=host` 僅 `enabled=false`（`enabled=true` 配 `host`＝`EVENT-TYPE`）；其他載體不得帶他載體的鍵（`EVENT-KEY-UNKNOWN`）；界檢查不在事件形態判準（歸 `sched.events`，R140） |
| `sched.skip` | `due_at`（帶 offset 的秒精度 ISO 8601）、`reason`（七值：`disabled`、`blackout`、`quota-band`、`other-driver`、`dirty-tree`、`run-open`、`spawn-failed`）、`detail`（單行、≤120 code point） | 選填 `carrier`（字面 `console`）與 `audit_ref`（UUID；兩者成對，只在 Console `run-request` 被消耗而當下已有未關運轉時帶，R146） |

  `run.open` 增量：`trigger` 值域 `a`～`f`；選填鍵 `due_at`（`trigger=f` 必備，且 `trigger≠f` 時不得有）、`carrier`（字面 `console`，只限 `trigger=a`）、`audit_ref`／`audit_sha256`／`key_id`／`decider`（`carrier=console` 時四者必備、否則不得有）；P4 之前的 `run.open`（缺選填鍵）判準不變。事件行仍受 `event_max_bytes` 限制（最壞行：`sched.set` 約 520、`sched.skip` 約 330 bytes，遠小於上限）。
- **R140 `check` 的 P4 追加項與判準版本**：`check` 共 **35 項**（P0～P3 的 33 項 id、順序、語意、碼原樣，其後依序追加）：第 34 項 `sched.events`、第 35 項 `run.trigger_f_has_patrol_by`；兩項只讀事件帳本與 `params.json`（不讀 OBS／DEF 帳本、不呼叫 git、不讀家目錄）；事件帳本不在場＝nonblocking NE `CARRIER-NOT-ESTABLISHED`；無任何 `sched.*` 與 `trigger=f` 事件＝PASS。**`CHECK_RULES_REV` 由 4 增為 5**（本檔預設，⚖ 4）。判準：
  - `sched.events`（FAIL 碼）：`SCHED-PERIOD-RANGE`（`sched.set.period_minutes` 不在界內；界取當下 `params.json`）、`SCHED-RUN-DUP`（同一格內 `run.open(trigger=f)` 超過一筆；格以該筆 `run.open` 之前最近一次重置事件（R142 (b)） 的 `t` 為 origin、`period` 取該筆的 `period_minutes`）、`SCHED-SKIP-DUP`（同一格同一 `reason` 的非 Console `sched.skip` 超過一筆；Console 載體的 skip 以 `audit_ref` 判，同一 `audit_ref` 超過一筆即此碼）、`SCHED-SKIP-DUE`（非 Console 載體的 `sched.skip.due_at` 不是其 `t` 所在格的起點）。
  - `run.trigger_f_has_patrol_by`（FAIL 碼）：`TRIGGER-F-BY`（`trigger=f` 的 `by` 不是 `patrol`）、`TRIGGER-F-DUE-AT`（`due_at` 缺，或 `(due_at − origin) mod period ≠ 0`，origin 取該 `run.open` 之前最近一次重置事件（R142 (b)））、`TRIGGER-F-NO-ORIGIN`（該 `run.open` 之前沒有任何重置事件（R142 (b)））。
- **R141 Console 稽核檔兩個新 `kind` 與字串規則**（承 Console 側 `API_Contract_SelfImproving_P2c`，本條是 CLI 端的唯一判準；`consoleaudit.KINDS` 由 3 增為 5：`sched-set`、`run-request`）：(a) 外層七鍵與驗證步驟沿 P2 R94，外層 `subject` 一律 null（非 null＝`AUDIT-SUBJECT-MISMATCH`）；(b) `sched-set` 的 `body`：`enabled`（布林）與 `period_minutes`（整數，非布林）**兩鍵皆必備**（停用時也要帶界內週期）、`reason` 選填；`run-request` 的 `body`：`note` 選填；表外鍵一律 `AUDIT-BODY-INVALID`（含 `digest`、`card_seq` 等卡面鍵：這兩種寫入**不帶卡面 digest、不走 dedupe 重送閘**）；(c) **字串規則**（`reason`、`note` 共用）：選填、單行（不含 CR／LF）、≤120 code point（以 Unicode code point 計，不以位元組或 UTF-16 單元計）、拒 U+0000～U+001F 與 U+007F 控制字元（碼 `CTRL-CHAR`，CR／LF 亦屬之）、超長＝`FIELD-TOO-LONG`、有值時不得全空白（含空字串；碼 `FIELD-BLANK`）、**允許 `|`**（事件 JSON 不進 Markdown 表）；(d) 界：`period_minutes` 不在 `[sched_period_minutes_min, sched_period_minutes_max]`＝`PERIOD-OUT-OF-RANGE`；(e) **位元組權威與鍵序**：簽章對象的位元組權威＝根層 `consoleaudit.py`（`body` 字串逐位元組取自稽核檔；鍵序＝共通鍵之後依書寫序接專屬鍵——即 `sched-set` 為 `enabled`、`period_minutes`、`reason`，`run-request` 為 `note`，各專屬鍵位於 P2 R94 的共通鍵之後），Console 與 CLI 兩端對同一份位元組驗同一個 HMAC，CLI 不重新序列化；(f) 判準住 `consoleaudit.body_guard(kind, body)` 的純函式（沿 P3 R136 的同源原則：寫入端與 `check` 共用同一組述詞，單一實作）；碼（`CTRL-CHAR`、`FIELD-TOO-LONG`、`FIELD-BLANK`、`PERIOD-OUT-OF-RANGE`、`AUDIT-BODY-INVALID`）一併收集、rc 1、零寫入、輸出末尾印 `obs-draft:`。**與 P3 R136 的差別**：R136 對 `decide.reason` 的「只含空白者放行」不變；本條的新 `kind` 對空白一律拒收（Console 契約定案；主控裁決 D-RT-6，與 R136 並存、不回頭改 R136）。

*C. 日曆格到期模型與跳過（`sched.py`；AC-SI-36-1、36-2；時間一律注入 `now`、不讀系統時鐘）*

- **R142 排程狀態折疊**：輸入＝事件序列與注入的 `now`（aware）。(a) `enabled`＝最近一筆 `sched.set` 的 `enabled`（無＝false）；`period`＝其 `period_minutes`（無＝`sched_period_minutes_default`）；(b) `origin`＝最近一次**重置事件**的 `t`；重置事件＝`enabled` 由 false（或尚無設定）轉為 true 的 `sched.set`，或 `enabled` 為 true 而 `period_minutes` 與前一筆生效值不同的 `sched.set`（D-QA-6）；**值不變的 `sched.set`（含值不變的重送）照記事件但不重置 origin**；`enabled=false` 的 `sched.set` 使 `enabled` 為 false 而不改 origin 的歷史值，其後再啟用的那筆（false→true）成為新的重置事件；(c) 格 k＝`[origin＋k·period, origin＋(k＋1)·period)`（起點含、終點不含）；`k＝floor((now−origin)/period)`；`cell_start`、`cell_end`＝`now` 所在格兩端；(d) `now` 早於 origin（時鐘倒退）＝`cell_start`、`cell_end`、`ran_this_cell`、`overdue` 皆為 null（不猜）；(e) `enabled=false` 時 `cell_*`、`ran_this_cell`、`overdue`＝null／false 依 R158 表；(f) `ran_this_cell`＝該格內（`t` 落在 `[cell_start, cell_end)`）有 `run.open(trigger=f)`；`trigger` 為 a～e 的運轉不算；前一格的 `run.open(f)` 不延續到下一格；(g) 時區：以 aware 值比較，同一瞬間不論 offset 寫法結果相同（鐵律三）；`now` 缺 offset＝`ValueError`（CLI 為 rc 3）；(h) **版本號、覆蓋度、「每 N 輪」不是啟動事件**：`status.events_detected` 在排程啟用且本格未執行時不增項、不出現 `trigger` 為 `f` 的偵測項（(f) 運轉由巡邏器的 `run-open(f)` 開，不是偵測項）。
- **R143 七種跳過的判序與判準**（純函式 `sched.decide_skip(inputs)`→`reason` 或 None；輸入全由呼叫端注入）：判序固定 `disabled`→`blackout`→`quota-band`→`other-driver`→`dirty-tree`→`run-open`→`spawn-failed`，第一個成立者即 `reason`；(a) `disabled`＝`enabled` 為 false（只供判序進行中被翻的競態，正常流程下 `enabled=false` 不嘗試、不寫事件）；(b) `blackout`＝本機 wall clock 時分（`sched.local_hm(now)`＝`now.astimezone()` 的時分）落在 `sched_blackout_local` 任一區間：區間 `HH:MM-HH:MM`、**起點含、終點不含**、起＞迄＝跨午夜、多區間聯集、空清單＝無黑窗；(c) `quota-band`＝`quota_gate.read_quota(now)` 的 `band` 為 `prepare`、`halt` 或 `unmeasured` ⇒ 跳過（fail-closed）；`free`、`notice`、`converge` ⇒ 照跑，其中 `notice`、`converge` 的任務書必帶降載聲明（R152；`converge` 為主控裁決 D-RT-3 (a)）；(d) `other-driver`＝本 repo 逐字稿目錄（`events.transcript_dir(repo)`）最近 `sched_driver_quiet_minutes` 內有**對話記錄**（`transcript_activity.newest_conversation_at`，判記錄時間戳、不是檔案 mtime）：`now − newest < quiet`（嚴格小於）才成立，恰等於＝不成立；只有 `away_summary`、`cost-state` 之類非對話記錄使 mtime 更新＝不成立；(e) `dirty-tree`＝`git status --porcelain`（含未追蹤）除 **SI 自有路徑**（事件帳本、OBS 帳本、`SelfImproving_Proposals/**`）外非空；改名條目兩端皆判；(f) `run-open`＝折疊出**本運轉以外**的任何未關運轉（任何 trigger；Console (a) 運轉自己不算，與 R166 同字；D-QA-16）；(g) `spawn-failed`＝`resume_route.preflight_problem()` 非空、`claude` 不在 PATH（`shutil.which`）、或 SOP 任務書範本的結構判準不過（`patrolbrief.template_problems`，detail 以 `sop-template:` 起頭）。
- **R144 同格同因一筆與 `due_at`**：嘗試時任一原因成立＝追加 `sched.skip{due_at＝本格起點, reason, detail}`；**同一格同一 `reason` 只寫一筆**（去重鍵＝(格, reason)）；同格內 `reason` 改變才再寫一筆（每格事件 ≤7 筆）；進入新格重新計；skip 不推進任何格線、不影響 `ran_this_cell`，下一心跳仍再試；有 skip＝巡邏活著，`overdue` 為 false（R145）；`detail` 為單行、≤120 code point（超長截斷、換行改空白）；寫入前 `events.validate` 過、`check` 的 `sched.events` 綠。**黑窗不造成永久跳過**：origin 落在黑窗內時，黑窗期間各心跳只記一筆 `blackout`，黑窗過後同格的下一心跳即可嘗試並開運轉。
- **R145 `overdue`**：`overdue＝enabled ∧ 本格內既無 run.open(f) 也無 sched.skip ∧ now − cell_start > 2×sched_heartbeat_minutes`（嚴格大於；`cell_start` 起算整 2×心跳時 false，多一秒 true）；`enabled=false` ⇒ false；無事件帳本 ⇒ null；`now` 早於 origin ⇒ null；任何一個 skip（含 Console 載體消耗者，只要 `t` 落在本格內）使其 false。
- **R146 Console 載體入帳**：(a) `sched set --carrier console --audit-ref <UUID>`：驗簽（金鑰缺＝`AUDIT-KEY-MISSING`，不降為 NE）、驗 R141 的 `body_guard`、同一 `audit_ref` 不得二次入帳（`AUDIT-REF-REUSED`）、於事件帳本寫入鎖內追加 `sched.set{enabled, period_minutes, by, carrier:"console", audit_ref, audit_sha256, key_id, decider}`（`reason` 有則帶）；`by` 取 `--by`（Console 入帳者：巡邏器＝`patrol`、主控手動＝`main`）；(b) `run-open --trigger a --carrier console --audit-ref <UUID> --coord console_audit/<UUID>.json --by console`：稽核檔 `kind=run-request`、驗簽與 `body_guard`；當下**無未關運轉**⇒ 追加 `run.open{trigger:"a", carrier:"console", audit_ref, audit_sha256, key_id, decider}`；**有未關運轉**⇒ 改追加 `sched.skip{reason:"run-open", carrier:"console", audit_ref, due_at, detail}`（請求被消耗、不卡在待入帳）；`due_at`＝排程啟用時為本格起點、停用時為稽核 `body` 外層 `time`（主控裁決 D-RT-3 (b)）；去重鍵＝`audit_ref`（同格內不同 `audit_ref` 各記一筆，與 R144 的 (格, reason) 去重互不取代）；(c) 兩動詞於 `AUTOSDD_UNATTENDED` 有設時一律 rc 1（R153 ③，不因 `AUTOSDD_SI_PATROL_RUN` 有設而放行，主控裁決 D-RT-1）；(d) 無金鑰的環境下兩動詞一律 rc 1 `AUDIT-KEY-MISSING`。
- **R147 `run-open --trigger f`**：(a) `--by` 必為 `patrol`（否則 rc 1、`TRIGGER-F-BY`）；(b) `--due-at` 必帶（缺＝rc 3 用法）；`--trigger` 非 `f` 而帶 `--due-at`＝rc 3；(c) `--due-at` 須等於當下本格起點（`DUE-AT-NOT-CELL-START`）；(d) 排程須為 `enabled`（否則 `SCHED-NOT-ENABLED`）；(e) 本格已有 `run.open(f)`＝`CELL-ALREADY-RUN`（每格至多一個 (f) 運轉）；(f) `--coord` 沿 `rows.has_coord`（P0 九式不擴）：`trigger=f` 的座標為 `docs/06_quality/SelfImproving_Event_Ledger.jsonl:<origin 那筆 sched.set 的 1 起算實體行號>`；(g) 以上碼與 `HEAD`、座標等既有碼一併收集，rc 1、零殘留。

*D. 巡邏、無人運轉與授權（`patrol`、`patrolrun`、`patrolbrief`、`unattended`；AC-SI-36-3～36-6、38、39）*

- **R148 一次性心跳**：`patrol` 單次執行依序 **巡視進行中的無人運轉（步 0′，R167）→入帳（R149）→到期判定（R143、R144）→運轉（R150、R151；含本心跳新入帳的 Console (a) 運轉，R166）→推進（R155）** 後退出；心跳本身只做短動作（spawn 為脫離式、不等待無人主控），`patrol.lock` 於數分鐘內釋放；套件不含 `while True`、`time.sleep`、`os.fork`、`signal.alarm`（沿 §9.4 全套件禁字樣，新檔照樣適用）；等待只用 `communicate(timeout)`／`subprocess.run(timeout=…)`；行程以 `apply_lock` 取 `<si>/locks/patrol.lock`（立即放棄、不等待）：取不到＝rc 0 並印「已有巡邏在跑」、零寫入；`AUTOSDD_SI_PATROL_OFF` 有設且非空（含字面 `0`）＝整次 no-op（rc 0、日誌一行、連入帳也不做、不取鎖）；`AUTOSDD_UNATTENDED` 有設＝rc 1 `UNATTENDED-REFUSED`、零寫入（先於一切，含 OFF 判斷之前）；未預期例外＝寫日誌並 rc 1、**不重試**；`--dry-run`＝零寫入（不寫事件、OBS 帳本、日誌以外的任何檔，不取鎖、不建任何家目錄子目錄、不 spawn、不入帳、不 commit）、印「此心跳會做什麼」；`--now` 缺 offset＝rc 3。
- **R149 入帳**：心跳第一步，對 `status.console_pending[]` 逐檔依稽核檔 `time` 升冪（同時刻依 `audit_ref` 位元組序；`sched-set` 先於 `run-request` 以 `time` 序自然成立）呼叫對應入帳路徑：`decide`→`decide --carrier console`、`obs-add`、`obs-close`、`sched-set`→`sched set --carrier console`、`run-request`→`run-open --trigger a --carrier console`；金鑰 `AUTOSDD_SI_AUDIT_KEY` 由包裝腳本自 `AgentConsole/.env` 的 `CONSOLE_SI_AUDIT_KEY` **第一把**讀入巡邏行程環境（只取該鍵、不 `source` 整檔）；入帳 rc 1＝保留稽核檔、日誌記一列 `obs-draft` 與拒收碼、不重試、不刪檔，同一 `audit_ref` 連續被拒不重複寫日誌（日誌行帶拒收碼，以 `audit_ref` 去重）；金鑰值不得出現在任何輸出、日誌、任務書、事件與 handback 目錄（以植入唯一字串的掃描判）。與互動視窗手動入帳互斥靠既有寫入鎖與「同一 `audit_ref` 不得二次入帳」。
- **R150 運轉前置序**：(f) 到期判定全不成立後，或本心跳於步 1 入帳了 Console (a) 運轉（R166）後：(f) 先 `run-open --trigger f --coord <事件帳本路徑>:<origin 行號> --due-at <本格起點> --by patrol`（R147；(a) 已有 `run.open`）→先自跑 `research --fetch --run <RUN>`（rc 1＝改跑 `research --skip --reason offline --note <一行>`；rc 2 照常繼續；有網路例外時同 rc 1 處置）→`scan`（候選只落巡邏日誌，**不入 OBS 帳本**）→生成任務目錄 `<si>/patrol/<RUN>/` 並寫 `brief.md`→spawn（R151）。`spawn-failed` 的預檢（R143 (g)）在 (f) 的 `run-open` **之前**，故預檢不過時不留下 `run.open`、只記一筆 `sched.skip(spawn-failed)`；(a) 運轉的預檢不過只寫日誌（R166）。
- **R151 spawn 形態（脫離式）**：argv＝`resume_route.fresh_argv(claude, prompt, add_dir)` 逐元素相同（`claude -p <prompt> --permission-mode acceptEdits --settings <姿態檔> [<主控模型旗標>] --add-dir <任務目錄> <handback 目錄>`；姿態檔 `.claude/settings.unattended.json` 本 PRD 不改）；經 `runner.spawn_detached(argv, *, env, cwd) -> pid`（R160、R167：新 session 或新 process group、不等待）；**環境＝明示建構、不繼承**：必含 `AUTOSDD_UNATTENDED=1`、`AUTOSDD_SI_PATROL_RUN=<RUN>`、`CLAUDE_CODE_SUBAGENT_MODEL`（取 `resume_route.spawn_env()`）、harness 背景等待上限（`unattended_authz.HARNESS_BG_WAIT_ENV`，值＝`RESUME_BG_WAIT_CEILING_SECONDS×1000`）；其餘只准下列白名單（主控裁決 D-RT-4）：`runner` 探針白名單 `PATH`、`SYSTEMROOT`、`TEMP`、`TMP`、`HOME`、`USERPROFILE`、`LANG`、`LC_ALL`，加 `APPDATA`、`LOCALAPPDATA`、`CLAUDE_CONFIG_DIR`、`AUTOSDD_SI_DIR`（若父環境有設）；**絕不含** `AUTOSDD_SI_AUDIT_KEY`、任何名稱含 `KEY`、`TOKEN`、`SECRET`、`PASSWORD` 的變數、其他 `AUTOSDD_*`（含 `AUTOSDD_SI_PATROL_OFF`）；牆鐘不由 spawn 的 timeout 管：巡邏器把 `{pid, started_at, wall_due_at}` 寫進 `spawn.json`（`wall_due_at＝started_at＋unattended_authz.RESUME_HARD_WALL_SECONDS`），逾牆由後續心跳的步 0′ 終止（R167）；`cwd`＝repo 根；任務目錄與 handback 目錄於 spawn 前存在。
- **R152 任務書**：`patrolbrief` 自 SOP〈無人運轉任務書範本〉的程式碼圍欄取骨架（讀 `--repo` 內的 SOP 檔），把全部大寫占位符（`<RUN>`、`<HEAD_SHA>`、`<NOW_ISO>`、`<DUE_AT>`、`<BAND>`、`<DEGRADE_NOTE>`、`<BUDGET_MINUTES>`、`<EVENTS>`、`<RESEARCH_RESULT>`、`<SOURCE_FILES>`、`<SCAN_CANDIDATES>`、`<MAX_PROPOSALS>`、`<HANDBACK_PATH>`）填入現查值；小寫或中文占位符（`<來源 id>`、`<PROP>`、`<held-out 目錄>`、`<凍結者>`）原樣保留（是給無人主控的現場指令）；必含項：RUN、`trigger=f` 與到期時刻、偵測到的事件、研究結果與來源檔路徑、`scan` 候選、預算 `sched_run_budget_minutes`、角色序（8 步；步 2 為無人主控**手寫入 OBS 帳本**〔D-QA-12〕，手寫列不產生 `obs.add` 事件〔那是 Console 載體專用〕，`check` 以帳本列為準〔D-QA-13〕）、禁止事項、handback 四節標題逐字等於 `resume_route.HANDBACK_MARKERS`；額度帶為 `notice` 或 `converge` 時 `<DEGRADE_NOTE>` 為降載聲明、`free` 時不得有降載聲明；`template_problems(sop_text)` 回問題碼清單（空＝可用），缺必含項或圍欄不存在＝非空。
- **R153 run-scoped 無人值守授權**（取代 P2 R70 的「一律拒收」與 P1 R27 動詞的「照常」；單一實作 `unattended.gate(verb, run, env)`，`decwrite.refuse_unattended` 與各動詞改呼叫它，套件內不再有第二處讀 `AUTOSDD_UNATTENDED`）：「`AUTOSDD_UNATTENDED` 有設」＝存在且值非空（含字面 `0`；空字串＝未設）。① **A 類**（`research`、`attr`、`attr-confirm`、`attr-reject`、`prop-new`、`prop-revise`、`heldout-freeze`、`card --issue`）：有設時須同時有 `AUTOSDD_SI_PATROL_RUN` 且其 `--run`（無 `--run` 的動詞取其所屬 PROP 的 `run`）等於它，否則 rc 1、碼 `UNATTENDED-REFUSED`、零寫入；② `decide` 有設時**只准** `--carrier console`（逐字稿載體一律 rc 1，不因 `PATROL_RUN` 放行；註（D-QA-9）：無人主控不持金鑰，此分支在無人主控實際上必為 `AUDIT-KEY-MISSING`，保留是為了讓規則對「巡邏器本體若誤設 `AUTOSDD_UNATTENDED`」仍 fail-closed）；③ **C 類**（`run-open`、`run-close`、`obs-add`、`obs-close`、`sched set`、`sched arm`、`sched disarm`、`sandbox`、`verify`、`promote`、`rollback`、`measure`、`patrol`）有設時一律 rc 1、零寫入（只由不帶 `AUTOSDD_UNATTENDED` 的巡邏器本體執行；`PATROL_RUN` 有設也不放行）；④ 未設 `AUTOSDD_UNATTENDED`＝所有動詞行為不變（`AUTOSDD_SI_PATROL_RUN` 單獨存在不改變任何動詞行為，含 `--run` 與其不相等者）；⑤ 唯讀動詞（`check`、`status`、`scan`、`card` 無 `--issue`、`export`、`capacity`、`issues`、`sched show`、`obs-add --dry-run`）不受此限。**行為放寬的負控**：A 類中 `heldout-freeze`、`card --issue` 原為一律拒收，放寬後仍須拒絕跨運轉（`--run`／所屬 PROP 的 `run` 不等於 `PATROL_RUN`）。誠實劃界：環境變數是行程自述，持有者可自設，偵測靠 `check` 的 `run.trigger_f_has_patrol_by` 與 git 歷史對 DEC 對帳，不是被擋。
- **R154 DEC 只認 Console 載體與巡邏器的權限列**：巡邏器能做：到期判定、入帳 Console 稽核檔、`run-open(f)`、`research`、`scan`、spawn、`sandbox`／`verify`／`promote`／`measure`／`run-close`、本機 commit；不能做：任何 `decide`（入帳 Console 決定不是代決）、push、改 `non_evolvable_globs`、撰寫提案內容。靜態判準：`patrol*`、`schedarm`、`sched*` 原始碼對 CLI 動詞的呼叫集合 ⊆ 上述可做集合，不含 `decide --carrier transcript`、`git push`、`--no-verify`、`git add -A`／`git add .`。
- **R155 核准後機械步驟與 commit**：(a) 前置恆為「已有人的 DEC」：本心跳入帳了 `dec(approve)`⇒`sandbox`→`verify`→`card --issue`（`verdict` 與 `reasons` 原樣進卡面，**巡邏器不改判**；`FAIL`／`NE` 的退回與否決是人的決定）；入帳了 `dec(promote)`⇒`promote`→commit→`measure`；入帳了 `dec(rollback)`⇒`rollback`→commit；非 approve 的 `dec`（`reject`、`return`、`decline-promote`、`ack-handoff` 等）不觸發 `sandbox`；無 DEC 的 PROP 零動作；`promote`／`rollback` 另受既有 `decverify` 回查（fail-closed，偽造的 DEC 被拒）；(b) **推進路徑**（`sandbox`／`verify`／`promote`／`rollback`／`measure`／`run-close`）遇前置不成立（例如缺 `heldout.freeze`）或工作樹髒⇒**只寫巡邏日誌、不寫任何 `sched.skip`**（`sched.skip` 只在 (f) 到期嘗試寫，D-QA-3；下一心跳再試）；(c) 本運轉各提案皆已離開待人工決定態（`rejected`／`handed-off`／`returned`／`promoted` 以後）⇒`run-close`（`outcomes` 記各提案狀態）；(d) **自動 commit**：`sched_auto_commit`（預設 true）且 promote 前工作樹除 SI 自有路徑外乾淨 ⇒ 只 `git add` 該 `app.promote` 的 `touched` 路徑與 SI 自有路徑、`git commit`（訊息含 PROP ID、DEC ID、APP ID）；**不 push**、不 `--no-verify`、不 `git add -A`；promote 前工作樹不乾淨⇒不 promote、只寫日誌（排程啟用或停用皆然，無格線也不寫事件）；commit 失敗（含 git hook 拒絕）⇒日誌＋OBS 草稿列、不重試、不繞過 hook；`sched_auto_commit=false`⇒promote 照做、不 commit。
- **R156 收尾與 handback**：收尾發生在**後續心跳的步 0′**（R167），不在 spawn 返回時（spawn 為脫離式）：以**事件帳本**為憑：該運轉無任何 `prop` 事件⇒巡邏器 `run-close`（`no_event:true`）；有 `prop`⇒運轉保持開啟、由 R155 於後續心跳推進；handback 缺四節標題任一⇒日誌記「handback 不完整」、不重 spawn；`resume_route.harness_bg_kill(stderr)` 為真⇒日誌記錄；子行程逾 `wall_due_at` 仍存活⇒殺行程樹後同樣以事件帳本為憑；同日連續兩個 `no_event` 運轉不構成成效（`status.no_event` 仍只依偵測事件，AC-SI-03-1 不變）。
- **R157 日誌**：`<si>/patrol/patrol.log` 一行一筆，格式 `<ISO 帶 offset>␠step=<步驟>␠rc=<N>␠code=<碼或->␠<一行說明>`；任一步驟失敗只寫日誌、不中斷後續互不相依的步驟（入帳失敗不阻止到期判定）；日誌丟失不影響帳本；`status.schedule.overdue` 是「巡邏根本沒跑」的偵測面，日誌是「跑了但某步失敗」的偵測面。

*E. `status`／`export`、參數、能力登記、OS 載具、SOP 與零退化*

- **R158 `status.schedule`**：`status` 物件前 15 鍵次序與語意不變，其後附加末鍵 `schedule`（共 **16 鍵**；文字形態加一行 `schedule: enabled=… period=… cell=…/… overdue=…`）。`schedule`＝鍵序 `enabled`、`period_minutes`、`period_min`、`period_max`、`heartbeat_minutes`、`last_set`、`cell_start`、`cell_end`、`ran_this_cell`、`last_skip`、`overdue`、`armed`；`last_set`＝`{"at","by","carrier"}` 或 null（最近一筆 `sched.set`）；`last_skip`＝`{"at","reason","detail"}`（**本格**最近一筆 `sched.skip`，無＝null）；`period_min`、`period_max`、`heartbeat_minutes` 取自 `params.json`；停用（`enabled=false`）時 `cell_start`、`cell_end`＝null、`ran_this_cell`＝null、`overdue`＝false；無事件帳本時 `overdue`＝null；`armed`：`export` 與讀不到家目錄時恆為字串 `NOT-EVALUABLE：export-reads-no-home`（全形冒號，逐字），`si status` 在主機現查 OS 任務後為 `{"task":"AutoSDD_SI_Patrol","present":<布林>,"credential":"<NextRunTime 值或 launchctl 回讀摘要>"}`，查詢失敗為 `{"task":"AutoSDD_SI_Patrol","present":null,"credential":"NOT-EVALUABLE：<碼>"}`。`export --kind status` 的 `items[0]` 同 `status` 的 16 鍵（與 `status --json` 同一函式；差異只有 `capacity` 與 `armed` 的 export 固定 NE 值）；無事件帳本時 `ne` 另列 `{"field":"schedule.overdue","reason":"carrier-not-established"}`；`schema_rev` 維持 1。`status.console_pending[].kind` 值域加 `sched-set`、`run-request`（稽核檔存在而事件帳本尚無帶該 `audit_ref` 的 `sched.set`／`run.open`／`sched.skip`）。兩者唯讀、零寫入。
- **R159 `params.json` 九個新鍵**（不可進化面；`PARAM_SPECS` 與 `params.json` 同 commit 由 Developer 加入；共 **41 鍵**）：`sched_heartbeat_minutes`＝15（正整數）、`sched_period_minutes_default`＝1440、`sched_period_minutes_min`＝60、`sched_period_minutes_max`＝10080（整數；`min ≤ default ≤ max`；`heartbeat ≤ min`）、`sched_run_budget_minutes`＝90（正整數；`≤ unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS／60`，現值上限 240）、`sched_blackout_local`＝`["21:00-01:30"]`（D-QA-8；字串陣列，每項 `HH:MM-HH:MM`，起＝迄為違規，空陣列合法；須涵蓋 `scheduled_task_expectations.json` 每一個 `expected_trigger_time`；初值 WHY：涵蓋 smoke 21:30 與 nightly 22:30 的觸發時刻加常態歷時（5～8 分鐘）的十倍餘裕，`PT4H` 是砍掉凍住實例的上限、不是歷時；黑窗只約束巡邏的**嘗試時刻**，不保證與長跑任務零重疊，後段重疊由額度帶與 `dirty-tree` 兜）、`sched_driver_quiet_minutes`＝30（正整數）、`sched_auto_commit`＝true（布林）、`sched_auto_push`＝false（布林；**只准 false**，true＝`PARAM-RANGE`，PRD §9.7 #88）；缺、型別或範圍不符＝`PARAM-MISSING`／`PARAM-TYPE`／`PARAM-RANGE`（`params.keys` FAIL；布林當整數、整數當布林皆 `PARAM-TYPE`）；跨鍵違規（`min>default`、`default>max`、`heartbeat>min`、預算超界）＝`PARAM-RANGE` 並點名鍵；改鍵使指紋 manifest 部分改變（`metrics.md` 與 `metrics_rev` 不改）；`docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md` 的 `params.json` 雜湊與位元組數、指紋、`CHECK_RULES_REV` 三列須同 commit 更新（D10）。
- **R160 能力登記、LOC 與 `runner.run_argv`**：`CAPABILITY` 由 51 鍵增為 **59 鍵（43 `ro`／9 `rw`／2 `net`／5 `exec`）**：新增 `sched`、`unattended`、`patrolbrief`、`schedcheck`（`ro`）、`schedwrite`（`rw`）、`patrol`、`patrolrun`、`schedarm`（`exec`）；**可選 `evspec.py`**（`ro`；僅當 `events.py` 斷言行將超過 380 時，Developer 把 `_SPEC` 整段拆出，擇一、不得並存）⇒60 鍵（44／9／2／5）；判準沿 P2 R105：`check`／`status`／`scan`／`export`／`card` 的相對 import 閉包 ⊆ `ro`（故 `sched`、`schedcheck`、`unattended` 必為 `ro` 且不 import `runner`、`schedwrite`）；任何相對 import `runner` 的檔須登記 `exec`；整個套件除 `git.py` 與 `runner.py` 外不得出現 `subprocess` 字樣；`runner.py` 新增 `run_argv(argv, *, env, timeout, cwd)`：`shell=False`、`communicate(timeout)`、逾時殺行程樹（平台守衛不變）、環境**只用呼叫端明示的 `env`**（不讀 `os.environ`、不 `dict(os.environ)`、不 `os.environ.copy()`），`spawn_detached(argv, *, env, cwd) -> int`（脫離式啟動：新 session 或新 process group、`shell=False`、不等待、回 pid；D-QA-10）同守這些不變量（環境只用明示 `env`）；探針入口 `run_probe` 的環境白名單與行為不變；全套件禁字樣（`time.sleep`、`while True`、`os.fork`、`signal.alarm`）；`capability_problems` 的 `FORBIDDEN` 清單**不動**（其中 `schtasks`、`launchctl`、`crontab`、`Register-ScheduledTask`、`ScheduleWakeup`、`CronCreate`、`apscheduler`、`threading.Timer`、`sched.scheduler`、`daemon=True` 仍是 P0 設計鎖），另加逐檔豁免表 `FORBIDDEN_EXEMPT = {"schedarm.py": ("schtasks", "launchctl", "Register-ScheduledTask")}`（D-QA-1：只豁免 OS 排程器字面、不豁免 `time.sleep`、`while True`、`os.fork`、`signal.alarm` 等其餘條；同字樣出現在 `schedarm.py` 以外任一檔仍紅；WHY：ADR-SI-14 的 OS 載具封裝須住在 `schedarm.py`，其餘守衛不削弱）；`.claude/**`、`tools/lib/schedule_backend.py`、`tools/lib/resume_route.py`、`tools/lib/unattended_authz.py`、`tools/lib/model_roles.py`、`.claude/settings.unattended.json` 本棒不改（只消費）；每檔斷言行 ≤400（`writeverbs.py` 現 382、`events.py` 現 357、`decwrite.py` 現約 348；`fold.py` 不得再加）、入口 `tools/selfimproving.py` ≤750。
- **R161 OS 任務、包裝腳本與 `schedarm`**：(a) **任務設定集**（Windows）：名稱 `AutoSDD_SI_Patrol`；觸發＝每日 00:00 起每 `sched_heartbeat_minutes` 分鐘重複、持續一天；`StartWhenAvailable=true`、`WakeToRun=false`（D-QA-7：心跳不喚醒睡眠機器，醒來由 `StartWhenAvailable` 補跑一次；睡著的機器不巡邏為已知邊界、與 macOS 一致；nightly、smoke 維持 `WakeToRun=true`）、`DisallowStartIfOnBatteries=false`、`StopIfGoingOnBatteries=false`、`ExecutionTimeLimit=PT1H`（D-QA-10：心跳自身的上限；無人運轉的牆鐘由 `spawn.json` 管，R167）、`MultipleInstancesPolicy=IgnoreNew`、`LogonType=S4U`；Action＝`powershell.exe -NoProfile -ExecutionPolicy Bypass -File <repo>\tools\si_patrol_tick.ps1`；安裝器整組三支（`install`／`-Uninstall`／`-Status`／`-WhatIf` 骨架不變，`-Uninstall` 仍移除整組）；(b) **三層鎖的連動**（`TestScheduledTaskExpectationsSsot`）：任務集合逐字相等（其解析任務名的判準須改為認得第三支的變數名）、每項期望值↔套用手段（**逐任務、逐值**：`WakeToRun` 為 true 者↔`-WakeToRun`（nightly、smoke）、為 false 者↔不帶該參數（patrol）；`StopExisting`↔COM fixup `MultipleInstances = 3`〔僅 nightly、smoke〕，`IgnoreNew`↔模組參數 `-MultipleInstances IgnoreNew`〔僅 patrol〕；不再只對「全檔存在某字面」）、`PT<N>H` 與 `New-TimeSpan -Hours N` 逐任務對齊（nightly、smoke＝4、patrol＝1）；期望表對 `AutoSDD_SI_Patrol` 的 `expected` 七鍵與其他任務同鍵集、`expected_trigger_time` **省略**（`check_scheduled_task_drift.load_trigger_expectations` 已容忍缺鍵，不改該檔）、`why_each` 的 `MultipleInstancesPolicy` 與 `ExecutionTimeLimit` 補「逐任務」說明；既有 `Show-TaskDetail` 的「expected PT4H」「expected StopExisting」字樣改為逐任務期望；(c) **包裝腳本** `tools/si_patrol_tick.ps1`：行尾 CRLF、PS 5.1 語意（無 PS 6+ 專屬變數）、只自 `AgentConsole/.env` 取 `CONSOLE_SI_AUDIT_KEY` 的第一把（逐行解析，不 `source`／點號載入／`Invoke-Expression` 整檔）、只設進行程作用域環境變數 `AUTOSDD_SI_AUDIT_KEY`、值不出現在任何輸出或日誌、呼叫 `.venv\Scripts\python.exe tools\selfimproving.py patrol`、日誌輪替；(d) **`schedarm`**：`sched arm` 經 `runner.run_argv`：Windows＝呼叫安裝器（`powershell.exe -NoProfile -ExecutionPolicy Bypass -File <installer>`；elevation 不足＝印指令並 rc 1）、macOS＝自寫 launchd plist（`plistlib`；`Label` 為 `AutoSDD_SI_Patrol`、`StartInterval`＝心跳分鐘×60、`RunAtLoad=false`、`StandardOutPath`／`StandardErrorPath` 指向家目錄痕跡目錄）並 `launchctl`；**憑證是值**：Windows 為 `NextRunTime` 非空字串、macOS 為 `launchctl` rc 與 plist 回讀；取不到憑證＝rc 1、輸出不得含「已排程」「armed」字樣；`sched disarm` 移除後須驗證任務真的不見（Windows 查無、macOS `launchctl` rc 113）才 rc 0；`schedarm` 原始碼對單平台外部執行檔 `powershell.exe`、`schtasks`、`launchctl` 的 argv 字面須住在 `sys.platform` 守衛分支內（根 `CLAUDE.md` 鐵律三 `TestForeignExecutableArgvIsGuarded` 五種罩法之一；D-QA-1），`launchctl`、`schtasks`、`Register-ScheduledTask` 字面僅 `schedarm.py` 可有（`FORBIDDEN_EXEMPT`，R160）（不新增 `_FOREIGN_EXE_ARGV_DEBT` 與 `_FOREIGN_API_SCOPE_DEBT` 的 selfimproving 條目）；(e) OS 任務與啟用旗標**相互獨立**：`sched set` 不呼叫 OS、`sched arm`／`disarm` 不寫事件、`overdue` 只由事件折出。
- **R162 SOP 條文**：SOP 已含〈巡邏與無人運轉（P4）〉（子節〈安裝與憑證〉〈每心跳做什麼〉〈停用與逃生口〉〈日誌與逾期處置〉）、〈無人運轉任務書範本〉、〈啟動條件〉第六類、〈P2 動詞〉序列條文的 run-scoped 改寫；`sop_p4_problems(text)`（§5.6）判其必含項（逐項刪去、注入、移入程式碼圍欄的自證沿 P3 R133）：〈啟動條件〉含第六類「排程巡邏到期」與字面 `日曆格`；〈P2 動詞〉序列條文**不得再含**「無人值守：有設時寫入動詞一律 rc 1」類的過度概括、須含 `run-scoped`（或等價字面 `AUTOSDD_SI_PATROL_RUN`）；〈每心跳做什麼〉的表含「入帳」「到期判定」「運轉」「推進」四列與七種跳過的全部字面；〈停用與逃生口〉含 `sched set --enabled false`、`sched disarm`、`AUTOSDD_SI_PATROL_OFF`；〈日誌與逾期處置〉含 `overdue` 與「不得手補 `sched.skip`」；〈無人運轉任務書範本〉的圍欄含 R152 的全部大寫占位符與四節 handback 標題；〈擷取者〉〈歸因者〉〈提案者〉〈研究者〉四節仍不得含 P3 R133 (e) 的禁出現片段。
- **R163 零退化與既有測試的同步站點**：P4 夾具不改任何 P0～P3 或議題中心夾具的既有呼叫形態；既有 AT 全綠，其斷言值或預設值**只准在 §2.5 的同步表所列站點改**（每項標「檔、函式名」；行號僅供參考，以函式名為準）；本表外若有既有函式因鍵數、項數、動詞數、預設欄位表變動而紅，Developer 以 ⚖ 回報、不就地改斷言（由主控裁決後補入本表）。
- **R164 AT 錨定與範圍**：本檔 AT 的 `-k` 一律為錨定名；檢查函式 `parse_at_headers`、`anchor_problems`、`collect_nodes` 沿用 `test_selfimproving_p2_meta.py` 的同名函式（匯入、不複製）。Developer 棒只新增或修改 §5.7 的集合；不改 `.claude/**`、凍結檔（PRD、SOP、P0～P3 TCS）、`autoclaude/` 引擎原始碼、`AgentConsole/**`、`tools/lib/{schedule_backend,resume_route,unattended_authz,model_roles}.py`、`.github/**`。
- **R165 測試 seam（建議名）**：見 §5.6；全部時間、額度、對話時刻、git、`claude`、OS 任務一律注入或以替身取代，測試不讀系統時鐘、不連網、不註冊真 OS 任務。
- **R166 Console 載體 (a) 運轉的執行與收尾**（D-QA-2；AC-SI-38-8）：巡邏心跳於步 1 入帳 `run-request` 得到 `run.open{trigger:"a", carrier:"console"}` 後，於**同一心跳**對該運轉走與 (f) 相同的運轉前置序（R150：`research --fetch`→`scan`→任務書→spawn；R151、R152 同形，任務書的 trigger 行寫 `trigger=a（Console 立即啟動）`）；跳過判準沿 R143 的 ②～⑦（`blackout`、`quota-band`、`other-driver`、`dirty-tree`、`run-open`〔另一未關運轉，不含本運轉自己〕、`spawn-failed`），**不看啟用旗標、不受格線限制**；被擋時**只寫巡邏日誌、不寫 `sched.skip`**，運轉保持開啟，下一心跳再試（不重新入帳，運轉已存在）；spawn 後的收尾同 R156（無 `prop`⇒`run-close(no_event)`）；既有未關 (a) 運轉（任何來源）使 (f) 到期記 `sched.skip(run-open)` 的規則不變（R143 (f)；Console 看得到 `open_runs` 與 `last_skip.reason`，不是靜默）。
- **R167 脫離式 spawn 與步 0′ 巡視**（D-QA-10）：(a) spawn 經 `runner.spawn_detached`（不等待；`shell=False`；環境只用明示 `env`）；旗標（D-QA-14）：Windows 的 `creationflags`＝`CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`（三者各以 `getattr(subprocess, ..., 0)` 兜底），使子行程脫離排程任務的 job（任務實例結束不連帶終止它）；POSIX 為 `start_new_session=True`；**fail-closed**：breakaway 被拒（`OSError`／`PermissionError`，例如任務 job 不允許）⇒不 spawn、視同預檢失敗——(f) 記一筆 `sched.skip(spawn-failed)`（`detail` 以 `breakaway-denied` 起頭，沿 R144 去重）、(a) 只寫巡邏日誌不寫事件，兩者皆保持運轉開啟之外不留半套狀態（無 `spawn.json`），下一心跳再試；巡邏器於 spawn 後把 `{pid, started_at, wall_due_at}`（皆帶 offset 的 ISO）寫入 `<si>/patrol/<RUN>/spawn.json`（UTF-8、LF）後**立即返回**，`patrol.lock` 隨即釋放；(b) 每心跳**步 0′「巡視進行中的無人運轉」**（取鎖之後、入帳之前）：對每個 `spawn.json` 尚未結案的運轉：子行程存活（以 pid 與啟動時刻核對，pid 被重用者視為已結束）且未超 `wall_due_at`⇒不動；超過 `wall_due_at`⇒殺行程樹（`runner` 既有殺樹）後依事件收尾；已結束⇒依事件收尾（R156）；收尾後 `spawn.json` 補寫 `closed_at`；(c) **同一時間至多一個進行中的無人運轉**：存在存活且未超牆的 `spawn.json` 時，其他運轉的 spawn 延後（只寫日誌，不 spawn；(f) 到期仍依 R143 (f) 因該運轉未關而記 `run-open` skip）；(d) `ExecutionTimeLimit` 為心跳自身上限（R161），無人運轉的牆鐘只由 `spawn.json` 管。

**〈P4 判定碼表（`check` 的 P4 追加；P0～P3 的 33 項及其碼不變）〉**

| 項目 ID | 碼 | 狀態 | 觸發 |
|---------|-----|------|------|
| `sched.events` | `SCHED-PERIOD-RANGE`、`SCHED-RUN-DUP`、`SCHED-SKIP-DUP`、`SCHED-SKIP-DUE` | FAIL | R140 |
| `sched.events`、`run.trigger_f_has_patrol_by` | `CARRIER-NOT-ESTABLISHED` | NE nonblocking | 事件帳本不在場 |
| `run.trigger_f_has_patrol_by` | `TRIGGER-F-BY`、`TRIGGER-F-DUE-AT`、`TRIGGER-F-NO-ORIGIN` | FAIL | R140 |
| `events.structure` | `EVENT-KEY-MISSING`、`EVENT-KEY-UNKNOWN`、`EVENT-TYPE`、`EVENT-KIND`（`sched.*` 與 `run.open` 增量） | FAIL | R139 |
| `params.keys` | `PARAM-MISSING`、`PARAM-TYPE`、`PARAM-RANGE` | FAIL | 必備鍵由 32 增為 41（R159） |

**〈P4 拒收碼表（rc 1；零殘留沿 P2 R71）〉**

| 動詞 | 碼 |
|------|-----|
| `sched set` | `SCHED-QUOTE-REQUIRED`、`PERIOD-OUT-OF-RANGE`、`UNATTENDED-REFUSED`、`LOCK-BUSY`、`EVENT-BYTES-OVER`；Console 載體另有 `AUDIT-FILE-MISSING`、`AUDIT-KEY-MISSING`、`AUDIT-KEY-UNKNOWN`、`AUDIT-MAC-MISMATCH`、`AUDIT-REF-REUSED`、`AUDIT-KIND-MISMATCH`、`AUDIT-SUBJECT-MISMATCH`、`AUDIT-BODY-INVALID`、`CTRL-CHAR`、`FIELD-TOO-LONG`、`FIELD-BLANK`（rc 3：用法、`HOME-UNWRITABLE`、`params.json` 鍵無效） |
| `sched arm`／`sched disarm` | `UNATTENDED-REFUSED`、`SCHED-NO-CREDENTIAL`、`SCHED-ELEVATION-REQUIRED` |
| `run-open`（P4 追加） | `TRIGGER-F-BY`、`DUE-AT-NOT-CELL-START`、`SCHED-NOT-ENABLED`、`CELL-ALREADY-RUN`、`UNATTENDED-REFUSED`；Console 載體同 `sched set` 的稽核碼 |
| `patrol` | `UNATTENDED-REFUSED`、未預期例外（日誌碼 `PATROL-EXCEPTION`）（rc 3：用法、`HOME-UNWRITABLE`） |
| A／C 類動詞（R153） | `UNATTENDED-REFUSED`（跨運轉、缺 `PATROL_RUN`、C 類一律） |

| US ID | User Story | AC ID | AC（Given／When／Then；括號內為 PRD 全名與規則） |
|-------|------------|-------|---------------------------------------------------|
| US-401 | 作為掌舵者，我要讓系統依我設定的週期定期自動演化，且我隨時看得出排程有沒有在跑、為什麼沒跑，使「忘了啟動」與「靜默壞掉」都可偵測 | AC-SI-36-1 | （PRD AC-SI-36-1；R142、R147）Given 事件帳本與注入的 `now` When 折疊排程 Then `origin`、日曆格、`ran_this_cell` 依 R142；改週期與再啟用重置格線；`run-open(f)` 的 `due_at`、`--by patrol`、每格至多一個 |
| US-401 | 同上 | AC-SI-36-2 | （PRD AC-SI-36-2；R143、R144）Given 啟用且本格未執行 When 嘗試 Then 七種跳過依序判、同格同因只記一筆、skip 不推進格線、黑窗過後同格下一心跳即跑 |
| US-401 | 同上 | AC-SI-36-5 | （PRD AC-SI-36-5；R138、R148、R161）Given 任何時刻 When 停用、`disarm` 或 `AUTOSDD_SI_PATROL_OFF` Then 只停 (f) 運轉／只移 OS 任務／整次 no-op，且互相獨立 |
| US-401 | 同上 | AC-SI-36-6 | （PRD AC-SI-36-6；R155、R156、R159）Given 一個到期 When 開運轉 Then 至多一個 (f) 運轉、預算不超 harness 上限、額度帶準備以上不 spawn、no_event 不構成成效 |
| US-401 | 同上 | AC-SI-37-3 | （PRD AC-SI-37-3；R145、R158）Given `status`／`export` When 讀 `schedule` Then 12 鍵形狀、`overdue` 判準、`armed` 的現查與 export NE |
| US-401 | 同上 | AC-SI-37-5 | （PRD AC-SI-37-5；R140、R158）Given 事件帳本 When `check` Then 35 項、`sched.events` 與 `run.trigger_f_has_patrol_by` 的碼；`console_pending[]` 含兩新 kind |
| US-402 | 作為維護者，我要巡邏是 OS 排程器每心跳叫醒一次的一次性行程，不是常駐程式，且安裝後憑證可查、可獨立停用 | AC-SI-36-3 | （PRD AC-SI-36-3；R148）Given `si patrol` When 執行 Then 入帳→到期→運轉→推進後退出；`--dry-run` 零寫入；鎖、OFF、`UNATTENDED`、例外不重試；無禁字樣 |
| US-402 | 同上 | AC-SI-36-4 | （PRD AC-SI-36-4；R161）Given 安裝 When 安裝器或 `sched arm` Then 任務 `AutoSDD_SI_Patrol` 的設定集、期望表與安裝器三層鎖、包裝腳本、憑證為值 |
| US-403 | 作為掌舵者，我要在 Console 啟停排程、改週期、立即啟動一次演化，根層負責驗簽入帳 | AC-SI-37-1 | （PRD AC-SI-37-1；R141）Given 稽核檔 `sched-set`／`run-request` When CLI 驗證 Then 形狀、界、字串規則、不帶卡面 digest、Console 黃金檔 G6～G9 |
| US-403 | 同上 | AC-SI-37-2 | （PRD AC-SI-37-2；R146）Given 稽核檔 When `sched set --carrier console`／`run-open --trigger a --carrier console` Then 驗簽、驗界、鎖內追加、不得二次入帳；已有未關運轉改記 `sched.skip` |
| US-403 | 同上 | AC-SI-37-4 | （PRD AC-SI-37-4；Console UI 控件，**本檔無 AT**，由 Console TCS 判；根層半契約由 AC-SI-37-3 的 AT 釘住）Given `/self-improving` When ADMIN 開啟 Then 具名欄位、三個動作、確認對話框與收據 |
| US-404 | 作為掌舵者，我要無人運轉的每一條寫入都被授權邊界限住，核准與晉升的決定永遠只有我能做 | AC-SI-38-1 | （PRD AC-SI-38-1；R150、R151）Given 到期的 (f) 或本心跳入帳的 Console (a) 運轉且全不跳過 When 脫離式 spawn Then argv、明示環境、`spawn.json` 牆鐘、任務目錄、`research`／`scan` 前置 |
| US-404 | 同上 | AC-SI-38-2 | （PRD AC-SI-38-2；R152）Given 任務書生成 When 檢視 Then 自 SOP 骨架填占位符，必含項齊全 |
| US-404 | 同上 | AC-SI-38-3 | （PRD AC-SI-38-3；R153）Given `AUTOSDD_UNATTENDED` 有設 When 寫入動詞 Then A／B／C 類真值表、跨運轉拒收、未設時不變 |
| US-404 | 同上 | AC-SI-38-4 | （PRD AC-SI-38-4；R154、R155）Given 無人運轉 When 出現核准需求 Then 只到 `card --issue` 與 handback，巡邏器不執行逐字稿載體的 `decide` |
| US-404 | 同上 | AC-SI-38-5 | （PRD AC-SI-38-5；R155 (d)）Given promote 成功 When `sched_auto_commit` Then 只 add 白名單、不 push、不繞 hook；髒樹不 promote |
| US-404 | 同上 | AC-SI-38-6 | （PRD AC-SI-38-6；R156）Given 後續心跳的步 0′ 巡視到運轉結束或逾牆 When 收尾 Then 以事件帳本為憑：零提案 `run-close`、有提案保持開啟、handback 不完整只記日誌 |
| US-404 | 同上 | AC-SI-38-7 | （PRD AC-SI-38-7；R154）Given 巡邏器權限列 When 檢視 Then 能做與不能做的拒收路徑 |
| US-404 | 同上 | AC-SI-38-8 | （PRD AC-SI-38-8；R166，D-QA-2）Given 巡邏心跳入帳了 Console `run-request` 得到的 `run.open(a)` When 同一心跳 Then 走與 (f) 相同的運轉前置序與 spawn，跳過判準沿 ②～⑦、不看啟用旗標、被擋只寫日誌不記 skip，收尾同 AC-SI-38-6 |
| US-405 | 作為掌舵者，我要我在 Console 做的決定被自動入帳並推進到下一個機械步驟，不必守在主機前 | AC-SI-39-1 | （PRD AC-SI-39-1；R149）Given `console_pending[]` 非空 When 心跳開始 Then 逐檔依 kind 入帳、依 `time` 升冪、金鑰不洩漏 |
| US-405 | 同上 | AC-SI-39-2 | （PRD AC-SI-39-2；R149）Given 入帳 rc 1 When 處理 Then 保留稽核檔、日誌一列 `obs-draft`、不重試、以 `audit_ref` 去重 |
| US-405 | 同上 | AC-SI-39-3 | （PRD AC-SI-39-3；R155）Given 入帳了 approve／promote／rollback When 同心跳 Then `sandbox`→`verify`→`card --issue`、`promote`→commit→`measure`、`rollback`、`run-close` |
| US-405 | 同上 | AC-SI-39-4 | （PRD AC-SI-39-4；R155 (a)）Given 任一心跳 When 欲推進 Then 前置恆為已有人的 DEC，無 DEC 零動作，偽造 DEC 被 `decverify` 擋 |
| US-405 | 同上 | AC-SI-39-5 | （PRD AC-SI-39-5；R157）Given 任一步驟失敗 When 收尾 Then 日誌一行帶步驟、rc、碼，互不相依的後續步驟照跑 |
| US-406 | 作為維護者，我要 P4 的事件、參數、能力登記、SOP、既有測試同步與範圍各有可重跑檢查 | AC-P4-040-1 | （本檔自增；PRD §9.2〈P4 增補〉；R139）Given 事件帳本 When 驗形態 Then 詞彙 23、`sched.*` 欄位表、`run.open` 選填鍵 |
| US-406 | 同上 | AC-P4-040-2 | （本檔自增；PRD §9.2；R159）Given `params.json` When 驗證 Then 41 鍵、九鍵的型別與界、跨鍵關係、黑窗涵蓋期望觸發時刻、指紋與基線文件連動 |
| US-406 | 同上 | AC-P4-040-3 | （本檔自增；PRD §9.4〈P4 增補〉；R160）Given 套件原始碼 When 掃描 Then 能力登記 59 鍵（或 60）、閉包、`runner.run_argv` 的靜態不變量、禁字樣 |
| US-406 | 同上 | AC-P4-040-4 | （本檔自增；PRD §8.1 P4 與 SOP；R162）Given Operations SOP When 判準 Then 條文必含項齊全，刪去與注入自證 |
| US-406 | 同上 | AC-P4-040-5 | （本檔自增；R163）Given P4 變更落地 When 全套 Then P0～P3 與議題中心既有 AT 全綠、基線文件同步 |
| US-406 | 同上 | AC-P4-040-6 | （本檔自增；R164）Given 本檔 AT 清單 When 解析與收集 Then 每個 AT 的錨定 `-k` 恰收一個測試函式 |
| US-406 | 同上 | AC-P4-040-7 | （本檔自增；R137）Given 入口 When 呼叫 Then 26 個動詞、`sched`／`patrol`／`run-open` 的旗標與 rc 契約、用法錯誤 rc 3 |
| US-406 | 同上 | AC-P4-040-8 | （本檔自增；R164）Given 變更集合 When `git diff --name-only` Then 落在 §5.7 的允許集合、守衛面與消費檔零改動 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID；本檔除 §1 外沒有任何第一欄以 AC 起頭的表格，AT ID 於 §1 與 §2 的宣告位置之外只出現在說明性文字與表格的非第一欄。**本檔任何一行不寫出測試摘要字樣與數字同行的敘述**（`tools/check_pytest_baseline_sites.py` 的發現面），計數只放表格欄位或寫中文；測試向量與範例不含金鑰形字面，範例識別碼用 `pid(n)`、`oid(n)` 等執行期組出的形（不寫字面的 `OBS-SI-` 或 `PROP-SI-` 接數字）。

**INVEST 自檢**：獨立（只依賴既有 `tools/lib/selfimproving/` 的 P0～P3 套件、`lib.apply_lock`、`lib.quota_gate`、`lib.transcript_activity`、`lib.resume_route`、`lib.unattended_authz`、git）、可協商（旗標細部、碼名、日誌格式、`run-open(f)` 的座標形態由本檔定義並列 §7.1）、有價值（PRD §8.1 P4 出口 (a)～(f) 的機制面全可由 AT 判定，真實面由 V30～V35 如實標記）、可估計（8 支新套件模組＋`runner.run_argv`＋入口 2 動詞＋既有檔小幅增量＋4 個新測試檔＋1 個新夾具模組＋既有測試的 R163 同步站點）、小（P4 根層半；Console 半與真機運轉不在本檔）、可測（AT 數見 §1；全部用 tmp 合成 repo、注入 `now`、替身 `claude`、替身 OS 後端，不碰真帳本、不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P4-1 | 時間確定性：`sched` 純函式與心跳的判準只用注入的 `now`，不讀系統時鐘；全部時刻為 aware（`now` 缺 offset＝錯誤）；格邊界起點含、終點不含；黑窗比對本機 wall clock 時分、不做 naive 相減 | AT-436-1-1、AT-436-1-E-1、AT-436-2-2 |
| NFR-P4-2 | 無常駐：巡邏為一次性行程，套件無 `while True`、`time.sleep`、`os.fork`、`signal.alarm`；等待只用帶 timeout 的 `communicate`／`subprocess.run` | AT-436-3-1、AT-440-3-2 |
| NFR-P4-3 | 授權邊界：無人值守下的寫入面依 R153 真值表；巡邏器不 `decide`、不 push、不 `--no-verify`、不 `git add -A`；金鑰不洩漏（輸出、日誌、任務書、事件、handback 目錄的植入字串掃描為零命中） | AT-438-3-1～E-2、AT-438-4-1、AT-438-7-1、AT-439-1-E-1 |
| NFR-P4-4 | 失效可偵測（NFR-SI-09）：量不到＝NOT-EVALUABLE／null 並帶理由（`overdue`、`armed`）；OS 任務憑證是值不是 rc；skip 事件使「被擋」可見；日誌記每步 rc 與碼 | AT-437-3-1、AT-437-3-E-1、AT-436-4-E-1、AT-439-5-1 |
| NFR-P4-5 | 跨平台（根 `CLAUDE.md` 鐵律三）：`.ps1` CRLF、`schedarm` 的外部執行檔字面在平台守衛內、路徑一律 `posixpath`／`Path`、時區不依本機實施 DST、macOS 未實跑項標「未驗」；`claude` 以 `shutil.which` 現查 | AT-436-4-3、AT-436-4-E-1、AT-440-3-2 |
| NFR-P4-6 | 根層護欄相容：沿 P3 NFR-P3-4（不新增 skip／xfail、`encoding="utf-8"`、子行程與執行緒夾具必回收）；每個新測試檔不超過 35 個 AT | 根層 unittest 閘門；SCG-4 |
| NFR-P4-7 | 測試 hermetic：tmp 合成 repo；`AUTOSDD_SI_DIR`、`CLAUDE_CONFIG_DIR`、`HOME` 指向 tmp；替身 `claude`（記錄 argv 與 env 的假腳本）、替身 `runner.run_argv`、注入的額度與對話時刻；不註冊真 OS 任務、不讀真 `AgentConsole/.env`、不連外網；合成編號於執行期組出 | V20 的字面 ID 掃描與既有鎖 |
| NFR-P4-8 | 範圍守衛：實作者只動 §5.7 的集合；重釘根層棘輪、compat-ci `paths` 由主控收尾（**實作輪收尾步驟、不是設計缺口**）；`schedule_backend.py`、`resume_route.py`、`unattended_authz.py`、`.claude/**` 零改動 | AT-440-8-1 |
| NFR-P4-9 | CI 與棘輪：新增 4 個測試檔與 1 個夾具模組，估新增 `tools/` 斷言行超過護欄層單輪淨額上限，須由主控以具名一次性例外重釘；compat-ci `paths` 現有 `tools/tests/**`、`tools/lib/selfimproving/**` 與 `docs/03_testing/contracts/TCS-SelfImproving-*.md` 等 glob 預期已涵蓋，實作輪現查；每個新測試檔在 CI 上小於 300 秒；全套件 xdist 多 CPU 模式不變（序列例外不新增） | V20；根層全套 unittest |
| NFR-P4-10 | **Developer 交卷前閘門清單**（缺一即不得交卷；輸出逐字貼入）：(1) 本檔 AT 與 P0～P3、議題中心全部 AT 全綠（P4 四個新測試檔、`test_selfimproving_capability.py`、`test_install_windows_nightly.py`、`test_selfimproving_p3_meta.py`、`test_selfimproving_p2_meta.py` 及其餘既有 SI 測試檔，`-q -p no:xdist -o addopts=`）；(2) `python tools/selfimproving.py check` 對真 repo rc 0（35 項）；(3) `ruff check`；(4) `check_loc_budget.py --json` rc 0；(5) `python tools/sync_onboarding_baselines.py --check-snapshot` rc 0；(6) 官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）rc 0；(7) 護欄層重釘做到 `--print-guard-lines` 淨差額 0（主控）；(8) 文件引用子專案檔案一律寫 monorepo 根起算路徑；(9) 交卷含〈流程摩擦〉節；(10) 新增 `tools/tests/` 檔逐項過根層鎖（檔數下限、E501 東亞寬度、腳本入口在檔尾、docstring 指名受測模組）；(11) AT-440-6-1 綠；(12) `git grep` 本檔、測試與程式碼無不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>` | SCG-4 實跑檢核 V17～V21 |

**追溯矩陣**：F-005 ← PRD FG-M（FR-SI-36～39）、AC-SI-03-1 (f)、AC-SI-10-3、§2.1.1 巡邏器列、§2.2 SC-SI-6（對映 AC-SI-38-8）、§3.2、§9.1 C22／C23／C24 的根層半與〈C4 套件檔案表（P4）〉、§9.2（事件欄位表 `sched.set`／`sched.skip`、`run.open` 增補、〈P4 增補〉）、§9.3（`sched`、`patrol`、`run-open` 增補、rc 通則）、§9.4〈P4 增補〉、§9.5 ADR-SI-14／15、§9.6 P4 列、§8.1 P4 出口 (a)～(f)、附錄 C.2 #21、#22、§9.7 #82～#90；US-401～US-406 → AC-SI-36-1～AC-P4-040-8（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；單一 FSM 鍵 `monorepo-si-p4-schedule`）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v0.13 全文（FG-M、§8.1 P4、§9.6 P4）；Stage-1 重凍依常態規則由主控執行（`--approver` 引 sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；T1 立案＝sid f1522ddb-bdcf-4104-bb81-614c1118fa9d line 14） | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-005（本檔 FRD-lite）；FR-SI-36～39 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-0／NFR 已量化定義 | NFR-P4-1～10（本檔）；最近依據 PRD NFR-SI-01、02-3、07-5、09-5 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-0／User Story 已完成 INVEST 檢查 | US-401～US-406（本檔 INVEST 自檢） | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-0／利害關係人已確認簽核 | PRD 附錄 C.2 #21、#22（授權代決；sid f1522ddb-bdcf-4104-bb81-614c1118fa9d line 14；掌舵者可隨時以 T1 推翻） | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6；根層 RTM 檔由主控依落點 SSOT 落 `docs/06_quality/RTM-SelfImproving-P4-<日期>.md` | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review | 不適用（功能級增量；設計載於 PRD §9）；最近依據 PRD §9.0～§9.6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-1／API Spec 草稿完成 | 不適用（無 HTTP 端點；Console 端點屬 Console 半）；命令列介面即契約：R137、R138、R147、R158 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-1／資料模型設計完成 | PRD §9.2（事件欄位表 `sched.*`、`run.open` 增補、〈P4 增補〉）；本檔 R139、R142、R158 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-1／NFR 設計對應完成 | NFR-P4-1～10 對應 R142（注入 now）、R148（一次性）、R153（run-scoped 授權）、R160（能力登記）、R161（OS 憑證） | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-1／整合架構說明完整 | 依賴 git（只經 `Git`）、`lib.apply_lock`、`lib.quota_gate`、`lib.transcript_activity`、`lib.resume_route`、`lib.unattended_authz`（皆只消費不修改）、OS 排程器（Windows schtasks／macOS launchd）、`claude` CLI（無人主控，替身判） | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-2／C4 Context 圖完成 | PRD §9.1 C22、C23、C24 的根層半；P4 新增系統邊界＝OS 排程器與無人 `claude` 行程 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-2／C4 Container 圖完成 | 落點：`tools/lib/selfimproving/`（59 檔；可選 `evspec.py` 時 60 檔）、`tools/selfimproving.py`、`tools/si_patrol_tick.ps1`、`tools/install_windows_nightly.ps1`、`tools/scheduled_task_expectations.json`、`tools/tests/`、`docs/06_quality/`、`docs/05_development/` | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-2／所有架構決策有對應 ADR | PRD §9.5：ADR-SI-14（排程與巡邏）、ADR-SI-15（run-scoped 授權）；本增量無新增架構決策，ADR 不新開 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-2／Trust Boundary Map 完成 | PRD §9.4〈P4 增補〉：金鑰面、run-scoped 授權的信任邊界與誠實劃界；要點：巡邏器只推進人已決定的步驟、環境變數是行程自述 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-2／Before／After 架構對比 | 本檔 FRD-lite〈現況與變更〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／OpenAPI 3.1 規格完整 | 不適用（無 HTTP API）；介面為命令列 | docs/05_development/SelfImproving_Operations_SOP.md | sha256:12ae6b65f242d448f3719ec71c49c7f6290fba76ea20fcfda4ed10b59d0ae374（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／Request／Response Schema 定義完整 | 輸出形態：R137、R139、R141、R158 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／錯誤碼定義 | rc 表 0、1、3（R137）、〈P4 判定碼表〉與〈P4 拒收碼表〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／Consumer Contract 完成 | 消費者＝掌舵者（`sched show`、巡邏日誌）、主控（`status`、`check`、SOP 序列）、AgentConsole（`export --kind status` 的 `schedule`、稽核檔兩新 `kind`，Console 半另有 TCS）、無人主控（任務書） | docs/05_development/SelfImproving_Operations_SOP.md | sha256:12ae6b65f242d448f3719ec71c49c7f6290fba76ea20fcfda4ed10b59d0ae374（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1466e0359c76f15274dfdf1909a4e5d1aefd9eab281b9e13f7fc6ca615068de0（主控現算 2026-11-09 13:43 +08:00） |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查 | docs/05_development/SelfImproving_Operations_SOP.md | sha256:12ae6b65f242d448f3719ec71c49c7f6290fba76ea20fcfda4ed10b59d0ae374（主控現算 2026-11-09 13:43 +08:00） |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 與 SOP 的值是本檔作者於 2026-11-09 以 `Get-FileHash -Algorithm SHA256` 對工作樹現況（HEAD `5199e5600a01b5627c2ae8b1d0aa80e6debdf6a4`，含規格 commit `3f34eefa`；兩檔皆 LF）重算的值；Stage-1 重凍後的實際 digest 以該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 為準，與本表不符時以 `show` 為準並更正本表（PRD 若於本檔撰寫後又經 T1 修訂，亦同）。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（`4NN`＝PRD `AC-SI-NN-Y` 的 NN；`440`＝本檔自增 `AC-P4-040-Y`）；負控與邊界以 `AT-<NNN>-<Y>-E-<n>` 命名。測試檔縮寫（全部在 `tools/tests/`）：**SM**＝`test_selfimproving_schedule_model.py`、**SP**＝`test_selfimproving_schedule_patrol.py`、**SA**＝`test_selfimproving_schedule_advance.py`（入帳之後的推進、commit、收尾與 Console (a) 運轉；SP 於 D-QA 增補後逾 35 個 AT，故自 SP 分出）、**SG**＝`test_selfimproving_schedule_gate.py`（以上四檔為本檔新增；SM、SP、SA、SG 各不超過 35 個 AT）。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-SI-36-1 | 日曆格與到期（SM） | AT-436-1-1 | （SM）origin、period、格邊界起點含終點不含、`cell_start`／`cell_end` | ✅ | Unit | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-2 | （SM）`ran_this_cell`：格內 `run.open(f)` 算、他 trigger 不算、不延續到下一格 | ✅ | Unit | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-3 | （SM）改週期與再啟用（false 轉 true）重置 origin；值不變的重送不重置；停用後 `cell_*` 為 null | ✅ | Unit | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-4 | （SM）`run-open --trigger f` 正控：座標、`due_at`、`by patrol`、寫入的事件鍵 | ✅ | Integration | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-E-1 | （SM）`now` 缺 offset 為錯誤、早於 origin 為 null、不同 offset 同瞬間同結果 | ✅ | Unit | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-E-2 | （SM）事件帳本不在場與在場但無 `sched.set` 的區別 | ✅ | Unit | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-E-3 | （SM）`run-open f` 負控：by 非 patrol、缺或多帶 due-at、非格起點、未啟用、同格已有 | ✅ | Integration | □ |
| AC-SI-36-1 | 日曆格與到期 | AT-436-1-E-4 | （SM）版本號、覆蓋度、每 N 輪不是啟動事件：`events_detected` 不增項 | ✅ | Integration | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-1 | （SM）判序：七種各自單獨成立得其 `reason`、兩兩並存取先者、皆不成立得 None | ✅ | Unit | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-2 | （SM）`blackout`：區間起點含終點不含、跨午夜、多區間、空清單、本機時分 seam | ✅ | Unit | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-3 | （SM）`quota-band`：free／notice／converge 照跑（後二者降載旗標）、prepare／halt／unmeasured 跳過 | ✅ | Unit | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-4 | （SM）`other-driver`：對話記錄在靜默窗內、恰等於窗、僅非對話記錄使 mtime 更新 | ✅ | Integration | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-5 | （SM）`dirty-tree`：SI 自有路徑除外、其他路徑與未追蹤、改名兩端 | ✅ | Integration | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-6 | （SM）`run-open`（任何 trigger 的未關運轉）與 `spawn-failed`（預檢非空、claude 缺、SOP 範本不合） | ✅ | Integration | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-7 | （SM）去重：同格同因一筆、同格改因再一筆、新格重計、`due_at` 為格起點、`detail` 單行 ≤120 | ✅ | Unit | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-E-1 | （SP）黑窗跨格：origin 在黑窗內、黑窗期間只記一筆、過後同格下一心跳即開運轉 | ✅ | Integration | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-E-2 | （SM）停用時不嘗試、不寫事件；`disabled` 只由判序函式在競態輸入下產生 | ✅ | Unit | □ |
| AC-SI-36-2 | 七種跳過與同格同因一筆 | AT-436-2-E-3 | （SM）skip 不推進格線：`ran_this_cell` 仍 false、`overdue` 因 skip 為 false、`check` 綠 | ✅ | Integration | □ |
| AC-SI-36-3 | 巡邏為一次性行程 | AT-436-3-1 | （SP）單次心跳依序巡視、入帳、到期、運轉、推進後退出，spawn 後立即返回、鎖已釋放，輸出五行步驟 | ✅ | Integration | □ |
| AC-SI-36-3 | 巡邏為一次性行程 | AT-436-3-2 | （SP）`--dry-run` 零寫入、不取鎖、不 spawn，印此心跳會做什麼 | ✅ | Integration | □ |
| AC-SI-36-3 | 巡邏為一次性行程 | AT-436-3-E-1 | （SP）用法：`--now` 缺 offset、未知旗標、`--repo` 非目錄、家目錄不可寫 | ✅ | Integration | □ |
| AC-SI-36-3 | 巡邏為一次性行程 | AT-436-3-E-2 | （SP）鎖已被持有、`AUTOSDD_UNATTENDED` 有設、未預期例外不重試 | ✅ | Integration | □ |
| AC-SI-36-4 | OS 任務與憑證 | AT-436-4-1 | （SG）安裝器整組三支、期望表第三筆、三層鎖逐任務逐值對齊 | ✅ | Unit | □ |
| AC-SI-36-4 | OS 任務與憑證 | AT-436-4-2 | （SG）任務設定集與觸發形態：重複間隔取心跳參數、Action argv、`-WhatIf` 預覽 | ✅ | Integration | □ |
| AC-SI-36-4 | OS 任務與憑證 | AT-436-4-3 | （SG）包裝腳本：CRLF、5.1 語意、只取第一把金鑰、不洩漏、呼叫 patrol、日誌輪替 | ✅ | Unit | □ |
| AC-SI-36-4 | OS 任務與憑證 | AT-436-4-E-1 | （SG）`sched arm`：憑證為空 rc 1 且不含已排程字樣；Windows argv 與 macOS plist 內容 | ✅ | Integration | □ |
| AC-SI-36-4 | OS 任務與憑證 | AT-436-4-E-2 | （SG）OS 任務與啟用旗標相互獨立：set 不呼叫 OS、arm／disarm 不寫事件、overdue 只由事件折出 | ✅ | Integration | □ |
| AC-SI-36-5 | 停用與逃生口 | AT-436-5-1 | （SM）`sched set --enabled false` 免引言、`carrier host`、沿用週期；入帳仍照常 | ✅ | Integration | □ |
| AC-SI-36-5 | 停用與逃生口 | AT-436-5-2 | （SG）`sched disarm` 移除後驗證任務不見才 rc 0；仍在則 rc 1 | ✅ | Integration | □ |
| AC-SI-36-5 | 停用與逃生口 | AT-436-5-E-1 | （SP）`AUTOSDD_SI_PATROL_OFF` 非空（含字面 0）整次 no-op、空字串視為未設 | ✅ | Integration | □ |
| AC-SI-36-5 | 停用與逃生口 | AT-436-5-E-2 | （SM）啟用或改週期缺引言 rc 1；`sched set`、`arm`、`disarm` 於無人值守下 rc 1 | ✅ | Integration | □ |
| AC-SI-36-6 | 有界與預算 | AT-436-6-1 | （SP）一格至多一個 (f) 運轉；未關的 Console 運轉使到期記 `run-open` skip | ✅ | Integration | □ |
| AC-SI-36-6 | 有界與預算 | AT-436-6-E-1 | （SP）額度帶準備以上不 spawn、不留 `run.open`；兩個 no_event 運轉不構成成效 | ✅ | Integration | □ |
| AC-SI-37-1 | 兩種新寫入的形狀與資格 | AT-437-1-1 | （SM）`sched-set` 稽核檔形狀、界的兩端值收下、界外與型別錯拒收 | ✅ | Integration | □ |
| AC-SI-37-1 | 兩種新寫入的形狀與資格 | AT-437-1-2 | （SM）`run-request` 稽核檔形狀、`note` 選填、外層 `subject` 須 null | ✅ | Integration | □ |
| AC-SI-37-1 | 兩種新寫入的形狀與資格 | AT-437-1-3 | （SM）真 CLI 收下 Console 黃金檔 G6～G9：同一位元組驗同一 HMAC | ✅ | Integration | □ |
| AC-SI-37-1 | 兩種新寫入的形狀與資格 | AT-437-1-E-1 | （SM）不帶卡面 digest、不走 dedupe：表外鍵 `digest`、`card_seq` 拒收 | ✅ | Integration | □ |
| AC-SI-37-1 | 兩種新寫入的形狀與資格 | AT-437-1-E-2 | （SM）字串規則負控表：控制字元、CR／LF、超長、全空白、`\|` 放行、code point 計數 | ✅ | Unit | □ |
| AC-SI-37-2 | 入帳動詞 | AT-437-2-1 | （SM）`sched set --carrier console` 的事件鍵、鎖內追加、重複 `audit_ref` 與金鑰與 MAC 負控 | ✅ | Integration | □ |
| AC-SI-37-2 | 入帳動詞 | AT-437-2-2 | （SM）`run-open --trigger a --carrier console`：`run.open` 事件鍵與座標、`by console` | ✅ | Integration | □ |
| AC-SI-37-2 | 入帳動詞 | AT-437-2-3 | （SM）已有未關運轉時改記 `sched.skip`：`audit_ref` 去重、不受 (格, reason) 去重限制 | ✅ | Integration | □ |
| AC-SI-37-2 | 入帳動詞 | AT-437-2-E-1 | （SM）`AUTOSDD_UNATTENDED` 有設：兩動詞 rc 1，`PATROL_RUN` 有設也不放行 | ✅ | Integration | □ |
| AC-SI-37-2 | 入帳動詞 | AT-437-2-E-2 | （SM）稽核檔 kind 與動詞不符、無金鑰環境、稽核檔不存在 | ✅ | Integration | □ |
| AC-SI-37-3 | `status.schedule` | AT-437-3-1 | （SM）鍵序與型別、`last_set`／`last_skip` 形狀、`status` 與 `export` 同一函式差分 | ✅ | Integration | □ |
| AC-SI-37-3 | `status.schedule` | AT-437-3-2 | （SM）`armed`：present 為真或假且憑證為值、查詢失敗為 NE、export 為固定字串 | ✅ | Integration | □ |
| AC-SI-37-3 | `status.schedule` | AT-437-3-E-1 | （SM）無事件帳本 `overdue` 為 null 並入 `ne`；`overdue` 嚴格大於 2×心跳的邊界 | ✅ | Unit | □ |
| AC-SI-37-5 | `check` 兩新項與對帳 | AT-437-5-1 | （SG）`console_pending[]` 含兩新 kind，入帳後消失 | ✅ | Integration | □ |
| AC-SI-37-5 | `check` 兩新項與對帳 | AT-437-5-2 | （SG）`check` 35 項、id 與順序、`CHECK_RULES_REV` 為 5、合法帳本兩項 PASS | ✅ | Integration | □ |
| AC-SI-37-5 | `check` 兩新項與對帳 | AT-437-5-E-1 | （SG）`sched.events` 四碼各恰一碼 | ✅ | Integration | □ |
| AC-SI-37-5 | `check` 兩新項與對帳 | AT-437-5-E-2 | （SG）`run.trigger_f_has_patrol_by` 三碼與 origin 取法、k 為 0 的邊界 | ✅ | Integration | □ |
| AC-SI-37-5 | `check` 兩新項與對帳 | AT-437-5-E-3 | （SG）載體缺席為 NE nonblocking、無 `sched.*` 事件為 PASS | ✅ | Integration | □ |
| AC-SI-38-1 | spawn 形態 | AT-438-1-1 | （SP）脫離式 spawn：替身記錄 argv 與 env（到期 (f) 與 Console (a) 兩種運轉）、四個必含環境鍵、`spawn.json` 的牆鐘、任務目錄 | ✅ | Integration | □ |
| AC-SI-38-1 | spawn 形態 | AT-438-1-2 | （SP）前置序：`run-open f` 事件鍵、`research` rc 0／2／1 三分支、`scan` 候選只落日誌 | ✅ | Integration | □ |
| AC-SI-38-1 | spawn 形態 | AT-438-1-E-1 | （SP）`claude` 不在 PATH：記 `spawn-failed` skip、不留 `run.open`、不寫任務目錄 | ✅ | Integration | □ |
| AC-SI-38-1 | spawn 形態 | AT-438-1-E-2 | （SP）環境不洩漏：金鑰與機密類名稱與其他 `AUTOSDD_*` 不傳給子行程，白名單鍵照傳 | ✅ | Integration | □ |
| AC-SI-38-1 | spawn 形態 | AT-438-1-E-3 | （SP）脫離旗標（breakaway）被拒時 fail-closed：(f) 記 `spawn-failed` skip、(a) 只寫日誌，皆不留 `spawn.json`、下一心跳再試 | ✅ | Integration | □ |
| AC-SI-38-2 | 任務書必含 | AT-438-2-1 | （SP）自 SOP 骨架生成：大寫占位符全替換、小寫與中文占位符保留、必含項齊、降載聲明依額度帶 | ✅ | Unit | □ |
| AC-SI-38-2 | 任務書必含 | AT-438-2-E-1 | （SP）SOP 範本缺必含項或圍欄：`template_problems` 非空，心跳記 `spawn-failed` skip 不 spawn | ✅ | Integration | □ |
| AC-SI-38-3 | run-scoped 授權 | AT-438-3-1 | （SP）A 類八個動詞×環境真值表 | ✅ | Integration | □ |
| AC-SI-38-3 | run-scoped 授權 | AT-438-3-2 | （SP）`decide` 僅准 console 載體；C 類十三個動詞一律拒；唯讀動詞不受限 | ✅ | Integration | □ |
| AC-SI-38-3 | run-scoped 授權 | AT-438-3-E-1 | （SP）跨運轉寫入：`--run` 與所屬 PROP 的 `run` 兩路都拒；`heldout-freeze`、`card --issue` 放寬後仍拒跨運轉 | ✅ | Integration | □ |
| AC-SI-38-3 | run-scoped 授權 | AT-438-3-E-2 | （SP）環境值邊界：字面 0 算有設、空字串算未設、`PATROL_RUN` 單獨存在不改行為；單一實作的靜態鎖 | ✅ | Integration | □ |
| AC-SI-38-4 | DEC 只認 Console 載體 | AT-438-4-1 | （SP）無人值守逐字稿載體 `decide` rc 1；console 載體通過授權閘而止於金鑰缺 | ✅ | Integration | □ |
| AC-SI-38-4 | DEC 只認 Console 載體 | AT-438-4-E-1 | （SP）心跳期間無任何逐字稿載體 `decide`；無 DEC 的核准需求只到 `card --issue` | ✅ | Integration | □ |
| AC-SI-38-5 | 核准後自動 commit | AT-438-5-1 | （SA）乾淨樹 promote 後只 add 白名單並 commit：訊息含 PROP、DEC、APP，不 push、不繞 hook | ✅ | Integration | □ |
| AC-SI-38-5 | 核准後自動 commit | AT-438-5-E-1 | （SA）promote 前樹不乾淨：不 promote、只寫日誌不記 skip（排程啟用與停用兩子情境）、無 commit | ✅ | Integration | □ |
| AC-SI-38-5 | 核准後自動 commit | AT-438-5-E-2 | （SA）白名單之外的髒檔不被 add | ✅ | Integration | □ |
| AC-SI-38-5 | 核准後自動 commit | AT-438-5-E-3 | （SA）commit 被 hook 拒：日誌加 OBS 草稿列、不重試、不 `--no-verify`；`sched_auto_commit` 為 false 不 commit | ✅ | Integration | □ |
| AC-SI-38-6 | 硬牆、handback 與零提案收尾 | AT-438-6-1 | （SA）以事件帳本為憑：後續心跳步 0′ 對無 `prop` 的運轉 `run-close`（`no_event`）、有 `prop` 保持開啟 | ✅ | Integration | □ |
| AC-SI-38-6 | 硬牆、handback 與零提案收尾 | AT-438-6-2 | （SA）同一時間至多一個進行中的無人運轉：存活且未超牆時其他運轉的 spawn 延後 | ✅ | Integration | □ |
| AC-SI-38-6 | 硬牆、handback 與零提案收尾 | AT-438-6-E-1 | （SA）handback 缺節、harness 殺行程標記、逾牆：只記日誌或終止行程、不重 spawn | ✅ | Integration | □ |
| AC-SI-38-7 | 巡邏器的權限列 | AT-438-7-1 | （SG）靜態：巡邏相關原始碼呼叫的動詞集合 ⊆ 可做集合，無 `git push`、`--no-verify`、`git add -A`、逐字稿 `decide` | ✅ | Unit | □ |
| AC-SI-38-7 | 巡邏器的權限列 | AT-438-7-E-1 | （SA）不能做的拒收路徑：觸及不可進化面的 PROP 不被 promote、日誌記因、無 commit | ✅ | Integration | □ |
| AC-SI-38-8 | Console 載體 (a) 運轉的執行與收尾 | AT-438-8-1 | （SA）排程停用下入帳 `run-request` 後同心跳 spawn，無 `prop` 則 `run-close`，無 `sched.skip` | ✅ | Integration | □ |
| AC-SI-38-8 | Console 載體 (a) 運轉的執行與收尾 | AT-438-8-E-1 | （SA）額度帶準備、有人在開車、黑窗、預檢不過：只寫日誌、運轉仍開、不記 skip，解除後下一心跳 spawn | ✅ | Integration | □ |
| AC-SI-39-1 | 心跳第一步入帳 | AT-439-1-1 | （SA）五種 kind 逐檔入帳、依 `time` 升冪、金鑰取自環境 | ✅ | Integration | □ |
| AC-SI-39-1 | 心跳第一步入帳 | AT-439-1-E-1 | （SA）植入的金鑰字串不出現在輸出、日誌、任務書、事件與 handback 目錄；同心跳改週期加立即啟動依操作序 | ✅ | Integration | □ |
| AC-SI-39-2 | 拒收處置 | AT-439-2-1 | （SA）入帳 rc 1：保留稽核檔、日誌一列 `obs-draft`、不重試不刪檔、以 `audit_ref` 去重；互動視窗手動入帳互斥 | ✅ | Integration | □ |
| AC-SI-39-2 | 拒收處置 | AT-439-2-E-1 | （SA）四種拒收碼逐一保留稽核檔、各一行日誌與 obs-draft、不重試 | ✅ | Integration | □ |
| AC-SI-39-3 | 核准後機械步驟 | AT-439-3-1 | （SA）`approve`→`sandbox`→`verify`→`card --issue`；FAIL 不自動否決；缺 `heldout.freeze` 跳過且不記 skip | ✅ | Integration | □ |
| AC-SI-39-3 | 核准後機械步驟 | AT-439-3-2 | （SA）`promote`→commit→`measure`；`rollback`；全部離開待人工決定態則 `run-close` 並記 `outcomes` | ✅ | Integration | □ |
| AC-SI-39-3 | 核准後機械步驟 | AT-439-3-E-1 | （SA）reject、return、decline-promote、ack-handoff 不觸發 sandbox；缺凍結者跳過且無 skip | ✅ | Integration | □ |
| AC-SI-39-4 | 只推進人已決定的步驟 | AT-439-4-1 | （SA）無 DEC 零動作；偽造的 DEC 被 `decverify` 回查擋下（fail-closed） | ✅ | Integration | □ |
| AC-SI-39-4 | 只推進人已決定的步驟 | AT-439-4-E-1 | （SA）promote 前置缺 `heldout.freeze` 跳過、不記 skip，補上後下一心跳推進 | ✅ | Integration | □ |
| AC-SI-39-5 | 失敗可偵測 | AT-439-5-1 | （SA）日誌行格式；某步失敗不中斷互不相依的後續步驟；日誌丟失不影響帳本 | ✅ | Integration | □ |
| AC-SI-39-5 | 失敗可偵測 | AT-439-5-E-1 | （SA）日誌行格式逐欄、成功與失敗步驟的 rc 與碼、說明單行、不含金鑰 | ✅ | Integration | □ |
| AC-P4-040-1 | 事件詞彙與欄位表 | AT-440-1-1 | （SG）`KINDS` 為 23 個、`sched.set`／`sched.skip` 欄位表正控、`run.open` 選填鍵 | ✅ | Unit | □ |
| AC-P4-040-1 | 事件詞彙與欄位表 | AT-440-1-E-1 | （SG）欄位表負控表：缺鍵、表外鍵、型別、載體組合、`due_at` 與 trigger 的配對 | ✅ | Unit | □ |
| AC-P4-040-1 | 事件詞彙與欄位表 | AT-440-1-E-2 | （SG）舊事件不變：P4 之前的 `run.open` 照過；訊息為 23 個詞彙；`trigger` g 拒收 | ✅ | Unit | □ |
| AC-P4-040-2 | 參數九鍵 | AT-440-2-1 | （SG）41 鍵、九鍵預設值、`PARAM_SPECS` 與 `params.json` 鍵集合相等、真 repo `check` 綠 | ✅ | Unit | □ |
| AC-P4-040-2 | 參數九鍵 | AT-440-2-E-1 | （SG）型別與界負控、跨鍵關係、預算超界、`sched_auto_push` 為 true 紅 | ✅ | Unit | □ |
| AC-P4-040-2 | 參數九鍵 | AT-440-2-E-2 | （SG）黑窗涵蓋期望表每個觸發時刻、指紋隨九鍵改變、基線文件三列與活值相等 | ✅ | Unit | □ |
| AC-P4-040-3 | 能力登記與 runner | AT-440-3-1 | （SG）登記 59 或 60 鍵、類別計數、閉包全 `ro`、`runner` 匯入者恰為四個 exec 檔 | ✅ | Unit | □ |
| AC-P4-040-3 | 能力登記與 runner | AT-440-3-2 | （SG）`run_argv` 靜態不變量、禁字樣、外部執行檔字面守衛、`subprocess` 字樣只在兩檔 | ✅ | Unit | □ |
| AC-P4-040-3 | 能力登記與 runner | AT-440-3-E-1 | （SG）注入副本自證：新檔未登記、`sched` 匯入 `runner`、`patrol` 登記為 `ro`、`run_argv` 讀 `os.environ`、`schedarm.py` 以外出現 `launchctl`（戊）、`schedarm.py` 內出現核心禁字樣 `time.sleep`（己；豁免表不豁免）各被抓到 | ✅ | Unit | □ |
| AC-P4-040-3 | 能力登記與 runner | AT-440-3-3 | （SG）`schedarm.py` 的 `powershell.exe`、`schtasks`、`launchctl` argv 住在 `sys.platform` 守衛分支內，注入副本被判出 | ✅ | Unit | □ |
| AC-P4-040-4 | SOP 條文 | AT-440-4-1 | （SG）`sop_p4_problems` 對真 SOP 為空、四節標題與範本占位符齊全 | ✅ | Unit | □ |
| AC-P4-040-4 | SOP 條文 | AT-440-4-E-1 | （SG）逐項刪去、注入過度概括句、移入圍欄各被判出 | ✅ | Unit | □ |
| AC-P4-040-5 | 零退化與同步 | AT-440-5-1 | （SG）P1 與 P2 與 P3 情境表在升級後夾具上重放：結構 PASS、折疊狀態不變 | ✅ | Integration | □ |
| AC-P4-040-5 | 零退化與同步 | AT-440-5-E-1 | （SG）同步表所列站點的斷言值逐項為新值；表外既有 SI 測試檔的函式集合未被改動 | ✅ | Unit | □ |
| AC-P4-040-6 | AT 錨定 | AT-440-6-1 | （SG）本檔每個 AT 的 `-k` 恰收一個測試函式、檔名與底線形相符 | ✅ | Unit | □ |
| AC-P4-040-6 | AT 錨定 | AT-440-6-E-1 | （SG）錨定檢查有牙：非錨定、零命中、多命中的注入各被判出 | ✅ | Unit | □ |
| AC-P4-040-7 | 入口與 rc 契約 | AT-440-7-1 | （SG）頂層 usage 26 個動詞、`sched` 子命令、`patrol` 與 `run-open` 旗標、成功輸出形態 | ✅ | Integration | □ |
| AC-P4-040-7 | 入口與 rc 契約 | AT-440-7-E-1 | （SG）用法錯誤一律 rc 3、stdout 空；未知動詞 rc 3 | ✅ | Integration | □ |
| AC-P4-040-8 | 範圍守衛 | AT-440-8-1 | （SG）變更檔案集合 ⊆ §5.7、守衛面與消費檔 `git diff` 為空、無新增 skip 與 xfail | ✅ | Unit | □ |

## 2. 可自動化 AT 格式規範

> **格式、驗收字樣與判定指令沿 P3 TCS §2 開頭**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_436_1_1]`；E 類為 `[AT_OK_436_1_E_1]`），Then、And 行只有驗收字樣一組引號，其餘字面值一律用反引號；判定指令一律為 `python -m pytest tools/tests/<檔名> -k <AT 底線形>_ -q -p no:xdist -o addopts=`（`-k` 為錨定名，R164）；測試函式名為 `test_<AT 底線形>_<slug>`。Given 描述佈置、When 描述被測動作、Then／And 描述斷言；子情境以 `subTest` 實作並保留 AT ID 對映；AT 內不引用其他 AT 的 ID；不得 skip（NFR-P4-6）。
>
> **P4 斷言簡寫**（其餘沿 P2、P3 §2）：`R4`＝`make_p4_repo(...)` 回傳的 tmp git repo（§5.1）；`O`＝`2026-11-02T08:00:00+00:00`（預設 origin）；`D1`＝1440 分鐘（預設週期）；格 k＝`[O＋k·D1, O＋(k＋1)·D1)`；`SCH(events, now)`＝`sched.schedule_obj` 的 `schedule` 物件（§5.6）；`HB`＝`sched_heartbeat_minutes`（15）；`ledger(R4)`＝事件帳本事件清單（依 `seq`）；`snap(R4)`＝事件帳本、OBS 帳本、`SelfImproving_Proposals/` 與家目錄樹的位元組快照；`CLI(R4, …)`＝以真入口 `tools/selfimproving.py` 子行程呼叫（`AUTOSDD_SI_DIR`、`CLAUDE_CONFIG_DIR` 指向 tmp）；`STUB`＝替身 `claude`（記錄 argv 與 env 到 tmp 的假腳本，回傳可設的 rc 並可寫 handback 檔）。S-…（情境）與 `ev`、`sched_set`、`run_open_f`、`skip_ev`、`audit_file`、`golden` 等建構器一律定義於 §5。

**A. 排程模型、跳過判準、Console 載體與 `status.schedule`（SM）**

```gherkin
# AT-436-1-1
# 對應 AC: AC-SI-36-1（R142 (a)(b)(c)）origin、period、格邊界與 cell_start／cell_end
# 測試類型: Unit
# 自動化工具: unittest（純函式、注入 now）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_1_ -q -p no:xdist -o addopts=

Feature: 日曆格折疊
Scenario: 格 k 起點含、終點不含
  Given 事件帳本只有一筆 `sched.set`（`enabled` 為 `true`、`period_minutes` 為 `1440`、`t` 為 `O`）
  When 以 `now` 分別為 `O`、`O＋1440 分－1 秒`、`O＋1440 分`、`O＋3 天＋5 分` 呼叫 `SCH`
  Then 四次的 `cell_start` 依序為 `O`、`O`、`O＋1 天`、`O＋3 天`，`cell_end` 為其後一天；`enabled` 為 `true`、`period_minutes` 為 `1440`；`last_set` 的 `at` 為 `O`、`carrier` 為寫入值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_1]"
```
```gherkin
# AT-436-1-2
# 對應 AC: AC-SI-36-1（R142 (f)）ran_this_cell 的格內判定
# 測試類型: Unit
# 自動化工具: unittest（純函式、注入 now）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_2_ -q -p no:xdist -o addopts=

Feature: 本格已執行
Scenario: 只認格內的 trigger 為 f 的 run.open
  Given S-CELL：origin 為 `O`；`run.open`（trigger `f`）於 `O＋1 小時`；另有 trigger 為 `a` 與 `e` 的 `run.open` 於 `O＋2 小時`
  When 以 `now` 為 `O＋3 小時`、`O＋1 天＋3 小時` 呼叫 `SCH`
  Then 第一次 `ran_this_cell` 為 `true`；刪去 trigger 為 `f` 的那筆後重算為 `false`（trigger a、e 不算）；第二次（下一格）`ran_this_cell` 為 `false`（不延續）；`run.open(f)` 的 `t` 恰為 `cell_end` 時屬下一格
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_2]"
```
```gherkin
# AT-436-1-3
# 對應 AC: AC-SI-36-1（R142 (b)(e)；D-QA-6）改週期與再啟用重置 origin；值不變的重送不重置；停用後格欄位為 null
# 測試類型: Unit
# 自動化工具: unittest（純函式、注入 now）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_3_ -q -p no:xdist -o addopts=

Feature: origin 重置
Scenario: 只有 false 轉 true 或週期改變才重置格線
  Given 事件依序：`sched.set`（啟用、週期 1440、`t`＝`O`）、`run.open(f)`（`O＋1 小時`）、`sched.set`（啟用、週期 720、`t`＝`O＋20 小時`）、`sched.set`（停用、週期 720、`t`＝`O＋30 小時`）、`sched.set`（啟用、週期 720、`t`＝`O＋40 小時`）、`sched.set`（啟用、週期 720、`t`＝`O＋45 小時`，值與前一筆生效值完全相同）
  When 以 `now` 為 `O＋21 小時`、`O＋35 小時`、`O＋41 小時`、`O＋46 小時` 呼叫 `SCH`
  Then 第一次 `cell_start` 為 `O＋20 小時`、`cell_end` 為 `O＋32 小時`、`period_minutes` 為 `720`、`ran_this_cell` 為 `false`（改週期前那筆 `run.open(f)` 不算）；第二次 `enabled` 為 `false`、`cell_start`／`cell_end`／`ran_this_cell` 為 `null`、`overdue` 為 `false`；第三次 `cell_start` 為 `O＋40 小時`（false 轉 true 重置）；第四次 `cell_start` 仍為 `O＋40 小時`（值不變的重送照記事件、`last_set.at` 為 `O＋45 小時`，但不重置 origin）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_3]"
```
```gherkin
# AT-436-1-4
# 對應 AC: AC-SI-36-1（R147）run-open --trigger f 正控
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_4_ -q -p no:xdist -o addopts=

Feature: run-open 的 trigger f
Scenario: 巡邏器身分、格起點與座標
  Given `R4` 已有啟用的 `sched.set`（`t` 為 `O`，行號 `L`）；以注入 `now` 使本格起點為 `O`
  When `CLI(R4, run-open, --trigger, f, --by, patrol, --due-at, <O 的 ISO>, --coord, <事件帳本相對路徑>:<L>)`
  Then rc 為 `0`；新增恰一筆 `run.open`：`trigger` 為 `f`、`by` 為 `patrol`、`due_at` 為 `O` 的秒精度 ISO、`coords` 為該座標、`head_sha` 為 40 碼；其後 `SCH` 的 `ran_this_cell` 為 `true`；`check` 的 `events.structure` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_4]"
```
```gherkin
# AT-436-1-E-1
# 對應 AC: AC-SI-36-1（R142 (d)(g)、NFR-P4-1）時間的邊界與時區
# 測試類型: Unit
# 自動化工具: unittest（純函式、注入 now）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_E_1_ -q -p no:xdist -o addopts=

Feature: now 的合法性
Scenario: naive、時鐘倒退與同瞬間異 offset
  Given S-CELL 的單一啟用事件（`t` 為 `O`）
  When 呼叫 `SCH` 並分別傳入 naive 的 `now`、`O－1 秒`、`O＋2 小時` 以 `+00:00` 與 `+08:00`（同瞬間）兩種寫法
  Then naive 拋 `ValueError`；`O－1 秒` 時 `cell_start`、`cell_end`、`ran_this_cell`、`overdue` 皆為 `null`；兩種 offset 寫法的整個 `schedule` 物件逐鍵相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_E_1]"
```
```gherkin
# AT-436-1-E-2
# 對應 AC: AC-SI-36-1（R142 (a)、R158）事件帳本不在場與無 sched.set 的區別
# 測試類型: Unit
# 自動化工具: unittest（純函式、tmp 目錄）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_E_2_ -q -p no:xdist -o addopts=

Feature: 量不到不是停用
Scenario: 載體缺席為 null，載體在場而無設定為 false
  Given 一個事件帳本檔不存在的 repo，與一個只有 `run.open`（trigger a）的 repo
  When 各以 `now` 為 `O` 取 `schedule` 物件
  Then 前者 `enabled` 為 `false`、`last_set` 為 `null`、`overdue` 為 `null`；後者 `enabled` 為 `false`、`overdue` 為 `false`、`period_minutes` 為 `1440`（預設）；兩者 `cell_start` 皆 `null`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_E_2]"
```
```gherkin
# AT-436-1-E-3
# 對應 AC: AC-SI-36-1（R147 (a)～(g)）run-open f 的負控
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_E_3_ -q -p no:xdist -o addopts=

Feature: run-open f 的拒收
Scenario: 每個違規恰一個碼、零殘留
  Given `R4` 啟用且 `snap(R4)` 已取
  When 逐一呼叫：`--by main`；缺 `--due-at`；`--trigger a` 而帶 `--due-at`；`--due-at` 為本格起點＋1 分鐘；排程停用時；同格已有一筆 `run.open(f)` 時再開
  Then 依序 rc 為 `1`（`TRIGGER-F-BY`）、`3`、`3`、`1`（`DUE-AT-NOT-CELL-START`）、`1`（`SCHED-NOT-ENABLED`）、`1`（`CELL-ALREADY-RUN`）；rc 為 1 者輸出末尾有 `obs-draft:`；每次之後 `snap(R4)` 與呼叫前逐位元相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_E_3]"
```
```gherkin
# AT-436-1-E-4
# 對應 AC: AC-SI-36-1（R142 (h)）版本號、覆蓋度、每 N 輪不是啟動事件
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_1_E_4_ -q -p no:xdist -o addopts=

Feature: 偵測事件集合不因排程而增
Scenario: 啟用且本格未執行時 status 無 f 類偵測項
  Given `R4` 啟用、本格未執行；另造版本目錄新增與已關運轉數達十的情境
  When `CLI(R4, status, --json)`
  Then `events_detected` 中沒有任何 `trigger` 為 `f` 的項；與排程停用時的 `events_detected` 逐項相等；`no_event` 的值相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_1_E_4]"
```
```gherkin
# AT-436-2-1
# 對應 AC: AC-SI-36-2（R143）七種跳過的判序
# 測試類型: Unit
# 自動化工具: unittest（純函式 decide_skip）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_1_ -q -p no:xdist -o addopts=

Feature: 判序
Scenario: 單一成立、兩兩並存、皆不成立
  Given 輸入夾具 `inputs(**kw)`，預設七項皆不成立
  When 對七個原因各單獨成立呼叫 `decide_skip`；再對 21 個兩兩組合呼叫；最後全不成立呼叫
  Then 單一成立各得 `disabled`、`blackout`、`quota-band`、`other-driver`、`dirty-tree`、`run-open`、`spawn-failed`；兩兩並存者得判序較前的那個；全不成立得 `None`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_1]"
```
```gherkin
# AT-436-2-2
# 對應 AC: AC-SI-36-2（R143 (b)、NFR-P4-1）黑窗判準
# 測試類型: Unit
# 自動化工具: unittest（純函式、替身 local_hm）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_2_ -q -p no:xdist -o addopts=

Feature: 黑窗
Scenario: 起點含終點不含、跨午夜、多區間、空清單
  Given `sched.local_hm` 以 `mock.patch.object` 換成回傳指定時分的替身；區間 `["21:00-00:30"]`
  When 時分依序為 `20:59`、`21:00`、`23:59`、`00:00`、`00:29`、`00:30`；再以 `["09:00-10:00","22:00-23:00"]` 取 `09:59`、`10:00`、`22:30`；再以 `[]` 取 `22:30`；再取 `now` 為 `+08:00` 的 aware 值並還原替身
  Then 第一組依序為 假、真、真、真、真、假；第二組為 真、假、真；空清單為 假；還原替身後的呼叫經 `now.astimezone()` 取時分（以對原始碼的 AST 或 `mock` 呼叫紀錄判，不依本機時區）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_2]"
```
```gherkin
# AT-436-2-3
# 對應 AC: AC-SI-36-2（R143 (c)）額度帶
# 測試類型: Unit
# 自動化工具: unittest（替身 read_quota）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_3_ -q -p no:xdist -o addopts=

Feature: quota-band
Scenario: 準備以上與量不到跳過，其餘照跑
  Given `quota_gate.read_quota` 以替身回傳 `band` 為 `free`、`notice`、`converge`、`prepare`、`halt`、`unmeasured` 的狀態
  When 各呼叫 `sched.quota_verdict(state)`
  Then 前三者 `skip` 為 `false`，其中 `notice`、`converge` 的 `degrade` 為 `true`、`free` 為 `false`；後三者 `skip` 為 `true`；替身拋例外時也是 `skip` 為 `true`（fail-closed）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_3]"
```
```gherkin
# AT-436-2-4
# 對應 AC: AC-SI-36-2（R143 (d)）other-driver
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_4_ -q -p no:xdist -o addopts=

Feature: 有人在開車
Scenario: 以對話記錄時間戳判、不以 mtime 判
  Given `sched_driver_quiet_minutes` 為 30；合成逐字稿目錄（`transcript_dir(R4)`）內一個檔：最後一筆對話記錄（`assistant` 或人類 `user`）於 `now－29 分`，另含一筆 `away_summary` 於 `now－1 分`且檔案 mtime 設為 `now`
  When 呼叫 `sched.other_driver(repo, now, params)`；再把對話記錄改為 `now－30 分`、`now－31 分`；再刪去對話記錄只留 `away_summary` 與 `cost-state`
  Then 依序為 真、假（恰等於窗，嚴格小於才成立）、假、假；逐字稿目錄不存在也為 假（不丟例外）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_4]"
```
```gherkin
# AT-436-2-5
# 對應 AC: AC-SI-36-2（R143 (e)）dirty-tree
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_5_ -q -p no:xdist -o addopts=

Feature: 髒樹的界
Scenario: SI 自有路徑不算、其他路徑與未追蹤算
  Given `R4` 乾淨；依序改動：事件帳本、OBS 帳本、`SelfImproving_Proposals/` 下新檔；再新增未追蹤的 `notes/x.txt`；再把一個被追蹤檔改名
  When 每步後呼叫 `sched.dirty_paths(repo)`（回「SI 自有路徑以外」的條目）
  Then 前三步為空清單；加 `notes/x.txt` 後恰含它；改名後清單含改名的新舊兩端路徑；`git status --porcelain` 本身在前三步非空（證明排除的是路徑界、不是樹乾淨）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_5]"
```
```gherkin
# AT-436-2-6
# 對應 AC: AC-SI-36-2（R143 (f)(g)）run-open 與 spawn-failed
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_6_ -q -p no:xdist -o addopts=

Feature: 運轉互斥與 spawn 預檢
Scenario: 任何未關運轉與三種預檢失敗
  Given `R4` 有一個 trigger 為 `a` 的未關運轉；另備三種預檢失敗：`resume_route.preflight_problem` 替身回非空字串、`shutil.which("claude")` 替身回 `None`、SOP 範本圍欄被刪的副本
  When 各呼叫 `sched.spawn_problem(repo, which=…, preflight=…)` 與折疊未關運轉判斷
  Then 未關運轉存在時 `run-open` 條件為真，`run.close` 後為假；預檢三種各回非空碼：`preflight:<字串>`、`claude-not-found`、`sop-template:<碼>`；全正常回 `None`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_6]"
```
```gherkin
# AT-436-2-7
# 對應 AC: AC-SI-36-2（R144）同格同因一筆與 due_at
# 測試類型: Unit
# 自動化工具: unittest（純函式 skip_plan）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_7_ -q -p no:xdist -o addopts=

Feature: 去重鍵 (格, reason)
Scenario: 連續心跳的寫入計畫
  Given 已啟用、格 0；`skip_plan(events, now, reason, detail)` 回「要追加的事件 dict 或 None」
  When 依序在 `O＋1h`、`O＋1h15m`、`O＋1h30m` 以 `blackout` 呼叫並把回傳事件（若有）追加；再以 `quota-band` 呼叫；再回到 `blackout`；再 `now` 為 `O＋1 天＋1h`（格 1）以 `blackout` 呼叫；`detail` 另用含換行與 200 字元者
  Then 前三次只有第一次回事件（`due_at` 為 `O`、`reason` 為 `blackout`）；`quota-band` 回事件（改因再一筆）；回到 `blackout` 回 `None`；格 1 回事件（`due_at` 為 `O＋1 天`）；`detail` 無換行且 ≤120 code point；每個回傳事件過 `events.validate`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_7]"
```
```gherkin
# AT-436-2-E-2
# 對應 AC: AC-SI-36-2（R143 (a)、R142 (e)）停用時不嘗試
# 測試類型: Unit
# 自動化工具: unittest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_E_2_ -q -p no:xdist -o addopts=

Feature: disabled
Scenario: 停用不寫事件，disabled 只出現在判序競態
  Given 停用的事件帳本（最近一筆 `sched.set` 為停用）
  When 呼叫 `sched.attempt_plan(events, now, inputs)`；再以 `inputs(enabled=False)` 直接呼叫 `decide_skip`
  Then `attempt_plan` 回 `None`（不嘗試、不產事件）；`decide_skip` 回 `disabled`；`ledger(R4)` 無任何 `sched.skip`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_E_2]"
```
```gherkin
# AT-436-2-E-3
# 對應 AC: AC-SI-36-2（R144、R145）skip 不推進格線
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_2_E_3_ -q -p no:xdist -o addopts=

Feature: skip 後仍可再試
Scenario: 有 skip 不算逾期、不算已執行
  Given `R4` 啟用，格 0 內有一筆 `blackout` 的 `sched.skip`（經 `schedwrite` 寫入）
  When 以 `now` 為 `O＋3 小時`（遠超 2×心跳）取 `SCH`，再跑 `check`
  Then `ran_this_cell` 為 `false`、`overdue` 為 `false`、`last_skip` 的 `reason` 為 `blackout`；`check` 的 `sched.events` 為 `PASS`；同一格再以 `quota-band` 寫第二筆仍 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_E_3]"
```
```gherkin
# AT-436-5-1
# 對應 AC: AC-SI-36-5（R138 (a)）停用方向免引言
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_5_1_ -q -p no:xdist -o addopts=

Feature: sched set 停用
Scenario: 不需 sid、line，沿用週期
  Given `R4` 啟用且生效週期為 `720`
  When `CLI(R4, sched, set, --enabled, false, --by, main)`
  Then rc 為 `0`；新增恰一筆 `sched.set`：`enabled` 為 `false`、`period_minutes` 為 `720`、`carrier` 為 `host`、`by` 為 `main`、無 `sid`／`line`／`audit_ref`；其後 `SCH` 的 `enabled` 為 `false`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_5_1]"
```
```gherkin
# AT-436-5-E-2
# 對應 AC: AC-SI-36-5（R138 (b)、R153 ③）缺引言與無人值守
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_436_5_E_2_ -q -p no:xdist -o addopts=

Feature: 啟用須人的引言
Scenario: 缺引言與無人值守拒收
  Given `R4` 停用；`snap(R4)` 已取
  When 呼叫 `sched set --enabled true --period-minutes 120 --by main`（無 sid、line、console）；再呼叫 `sched set --enabled false --by main`、`sched arm`、`sched disarm` 並於環境設 `AUTOSDD_UNATTENDED` 為 `1` 與 `AUTOSDD_SI_PATROL_RUN` 為任一 RUN 號
  Then 第一個 rc 為 `1`、碼 `SCHED-QUOTE-REQUIRED`；後三個 rc 皆 `1`、碼 `UNATTENDED-REFUSED`（`PATROL_RUN` 不放行）；每次之後 `snap(R4)` 逐位元不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_5_E_2]"
```
```gherkin
# AT-437-1-1
# 對應 AC: AC-SI-37-1（R141 (b)(d)、R138 (c)）sched-set 稽核檔形狀與界
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_1_1_ -q -p no:xdist -o addopts=

Feature: sched-set 的 body 判準
Scenario: 界的兩端收下、界外與型別錯拒收
  Given `audit_file(kind="sched-set", body=…)` 以測試金鑰簽章並落在 tmp 家目錄的 `console_audit/`
  When `period_minutes` 依序為 `60`、`10080`、`59`、`10081`、`True`（布林）、字串 `"120"`、`120.0`；另一份缺 `enabled`；另一份缺 `period_minutes` 而 `enabled` 為 `false`
  Then 前兩者經 `sched set --carrier console` rc 為 `0`；其餘皆 rc 為 `1`，碼依序 `PERIOD-OUT-OF-RANGE`、`PERIOD-OUT-OF-RANGE`、`AUDIT-BODY-INVALID`、`AUDIT-BODY-INVALID`、`AUDIT-BODY-INVALID`、`AUDIT-BODY-INVALID`、`AUDIT-BODY-INVALID`（停用時也必帶界內週期）；拒收者 `snap(R4)` 不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_1_1]"
```
```gherkin
# AT-437-1-2
# 對應 AC: AC-SI-37-1（R141 (a)(b)）run-request 稽核檔形狀與外層 subject
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_1_2_ -q -p no:xdist -o addopts=

Feature: run-request 的 body 判準
Scenario: note 選填、subject 須 null
  Given `audit_file(kind="run-request", body=…)`
  When `body` 為 `{}`、`{"note":"手動啟動"}`；另一份外層 `subject` 為 `"PROP"` 形字串；另一份 `body` 帶表外鍵 `extra`
  Then 前兩者經 `run-open --trigger a --carrier console` rc 為 `0`；第三份 rc 為 `1`、碼 `AUDIT-SUBJECT-MISMATCH`；第四份 rc 為 `1`、碼 `AUDIT-BODY-INVALID`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_1_2]"
```
```gherkin
# AT-437-1-3
# 對應 AC: AC-SI-37-1（R141 (e)；D12）真 CLI 收下 Console 黃金檔 G6～G9
# 測試類型: Integration
# 自動化工具: pytest + 黃金檔 + 真 CLI（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_1_3_ -q -p no:xdist -o addopts=

Feature: 跨語言位元組權威
Scenario: 同一份位元組、同一個 HMAC
  Given Console 側黃金檔 G6、G7、G8、G9（路徑與檔名由 Console TCS 定，Developer 現查；本 AT 讀檔、不預填數值；每檔含外層七鍵與簽章用的測試金鑰 id）；金鑰以測試金鑰環境變數餵入；`R4` 啟用並已有可開運轉的狀態
  When 依各檔 `kind` 與 `body` 把原始位元組不經重新序列化地落到 tmp 家目錄的 `console_audit/<audit_ref>.json`，再呼叫真 CLI 對應入帳動詞（`sched-set` 檔用 `sched set --carrier console`、`run-request` 檔用 `run-open --trigger a --carrier console`）
  Then 四檔 rc 皆為 `0`（金鑰 id 對得上、`audit_sha256` 對得上、MAC 對得上）；事件的 `audit_sha256` 等於該檔位元組的雜湊；對其中一檔改動任一位元組（例如鍵序對調）重驗 rc 為 `1`、碼 `AUDIT-MAC-MISMATCH`；黃金檔缺失時 AT 為紅（不 skip）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_1_3]"
```
```gherkin
# AT-437-1-E-1
# 對應 AC: AC-SI-37-1（R141 (b)）不帶卡面 digest、不走 dedupe
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_1_E_1_ -q -p no:xdist -o addopts=

Feature: 兩種新寫入不走卡面閘
Scenario: 表外的卡面鍵一律拒收
  Given 兩份稽核檔：`sched-set` 的 `body` 加 `digest`、`run-request` 的 `body` 加 `card_seq`
  When 各自入帳
  Then 皆 rc 為 `1`、碼 `AUDIT-BODY-INVALID`；兩次後事件帳本無新增；同一 `audit_ref` 的重送閘（`AUDIT-REF-REUSED`）只在先前已入帳者才命中，未入帳者不受 dedupe 影響
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_1_E_1]"
```
```gherkin
# AT-437-1-E-2
# 對應 AC: AC-SI-37-1（R141 (c)(f)）reason／note 字串規則
# 測試類型: Unit
# 自動化工具: unittest（純函式 body_guard）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_1_E_2_ -q -p no:xdist -o addopts=

Feature: 單行字串規則
Scenario: 以 code point 計、控制字元、全空白、豎線放行
  Given `consoleaudit.body_guard(kind, body)` 回（碼, 說明）清單
  When 對 `sched-set.reason` 與 `run-request.note` 各代入：`"a|b"`、120 個 U+4E2D、121 個 U+4E2D、120 個 U+1F600（補充平面）、`"x\ny"`、`"x\ry"`、`"x\u0000y"`、`"x\u001fy"`、`"x\u007fy"`、`""`、`"   "`、`"\t"`；另一次完全不帶該鍵
  Then 放行者（回空清單）：`"a|b"`、120 個 U+4E2D、120 個 U+1F600、不帶該鍵；`121` 個＝`FIELD-TOO-LONG`；換行、CR、U+0000、U+001F、U+007F、`"\t"`＝`CTRL-CHAR`；`""` 與 `"   "`＝`FIELD-BLANK`；`reason` 與 `note` 兩鍵的結果逐項相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_1_E_2]"
```
```gherkin
# AT-437-2-1
# 對應 AC: AC-SI-37-2（R146 (a)）sched set 的 Console 入帳
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_2_1_ -q -p no:xdist -o addopts=

Feature: sched-set 入帳
Scenario: 事件鍵、重複、金鑰、MAC
  Given 一份合法 `sched-set` 稽核檔（`enabled` 為 `true`、`period_minutes` 為 `120`、`reason` 為一行）與測試金鑰
  When 入帳兩次；另以金鑰缺席、金鑰 id 不認得、MAC 被改動各入帳一份新檔
  Then 第一次 rc `0`，新增 `sched.set`：`enabled` 真、`period_minutes` 為 `120`、`carrier` 為 `console`、`by` 為 `--by` 值、`audit_ref`、`audit_sha256`、`key_id`（8 碼）、`decider`、`reason` 皆在；第二次 rc `1`、碼 `AUDIT-REF-REUSED`、零寫入；其餘三者 rc `1`，碼依序 `AUDIT-KEY-MISSING`、`AUDIT-KEY-UNKNOWN`、`AUDIT-MAC-MISMATCH`；入帳後 `SCH` 的 `last_set.carrier` 為 `console`、新 origin 為該筆的 `t`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_2_1]"
```
```gherkin
# AT-437-2-2
# 對應 AC: AC-SI-37-2（R146 (b)）run-request 入帳為 run.open
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_2_2_ -q -p no:xdist -o addopts=

Feature: 立即啟動一次
Scenario: 無未關運轉時開 trigger a 的運轉
  Given 無未關運轉；一份合法 `run-request` 稽核檔
  When `CLI(R4, run-open, --trigger, a, --carrier, console, --audit-ref, <U>, --coord, console_audit/<U>.json, --by, console)`
  Then rc `0`；新增 `run.open`：`trigger` 為 `a`、`by` 為 `console`、`carrier` 為 `console`、`audit_ref`、`audit_sha256`、`key_id`、`decider` 在、`coords` 為 `["console_audit/<U>.json"]`；`status.console_pending[]` 不再含 `<U>`；`check` 的 `events.structure` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_2_2]"
```
```gherkin
# AT-437-2-3
# 對應 AC: AC-SI-37-2（R146 (b)、R144）已有未關運轉時改記 skip
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_2_3_ -q -p no:xdist -o addopts=

Feature: 請求被消耗而不卡住
Scenario: audit_ref 去重，不受 (格, reason) 限制
  Given 一個未關運轉；排程啟用；三份 `run-request` 稽核檔 `U1`、`U2`（不同 `audit_ref`）與重送 `U1`
  When 依序入帳 `U1`、`U2`、`U1`
  Then 前兩次 rc `0` 且各新增一筆 `sched.skip`：`reason` 為 `run-open`、`carrier` 為 `console`、`audit_ref` 為各自值、`due_at` 為本格起點、無新的 `run.open`；第三次 rc `1`、碼 `AUDIT-REF-REUSED`；`check` 的 `sched.events` 為 `PASS`（同格同 reason 兩筆 Console skip 因 `audit_ref` 不同而不違反 SCHED-SKIP-DUP）；排程停用時改以稽核 `time` 為 `due_at`，`check` 仍 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_2_3]"
```
```gherkin
# AT-437-2-E-1
# 對應 AC: AC-SI-37-2（R146 (c)、R153 ③）無人值守
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_2_E_1_ -q -p no:xdist -o addopts=

Feature: 入帳動詞不被無人行程呼叫
Scenario: UNATTENDED 有設一律拒收
  Given 兩份合法稽核檔；環境 `AUTOSDD_UNATTENDED` 為 `1`
  When 各自入帳，一次不設 `AUTOSDD_SI_PATROL_RUN`、一次設為任一 RUN 號
  Then 四次皆 rc `1`、碼 `UNATTENDED-REFUSED`、`snap(R4)` 逐位元不變、稽核檔仍在
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_2_E_1]"
```
```gherkin
# AT-437-2-E-2
# 對應 AC: AC-SI-37-2（R146、R141）kind 不符、無金鑰環境、稽核檔缺
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_2_E_2_ -q -p no:xdist -o addopts=

Feature: 前置碼
Scenario: 每個違規一個碼
  Given 一份 `run-request` 稽核檔與一份 `sched-set` 稽核檔
  When 把 `run-request` 檔餵給 `sched set --carrier console`、把 `sched-set` 檔餵給 `run-open --carrier console`、對不存在的 `audit_ref` 入帳、環境完全無金鑰變數時入帳合法檔
  Then 碼依序 `AUDIT-KIND-MISMATCH`、`AUDIT-KIND-MISMATCH`、`AUDIT-FILE-MISSING`、`AUDIT-KEY-MISSING`，rc 皆 `1`，零寫入
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_2_E_2]"
```
```gherkin
# AT-437-3-1
# 對應 AC: AC-SI-37-3（R158）status.schedule 形狀與同一函式差分
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_3_1_ -q -p no:xdist -o addopts=

Feature: schedule 物件
Scenario: 12 鍵、型別、差分
  Given S-STATUS：`R4` 啟用（週期 1440）、本格有一筆 `blackout` 的 `sched.skip`、一筆 Console 載體的 `sched.set` 為最近一筆
  When `CLI(R4, status, --json)` 與 `CLI(R4, export, --json, --kind, status)`
  Then `status` 物件共 16 鍵、末鍵為 `schedule`、前 15 鍵順序與 P3 相同；`schedule` 鍵序為 `enabled`、`period_minutes`、`period_min`、`period_max`、`heartbeat_minutes`、`last_set`、`cell_start`、`cell_end`、`ran_this_cell`、`last_skip`、`overdue`、`armed`；`period_min`／`period_max`／`heartbeat_minutes` 等於 `params.json` 的值；`last_set` 鍵為 `at`、`by`、`carrier`；`last_skip` 鍵為 `at`、`reason`、`detail`；`export` 的 `items[0].schedule` 除 `armed` 外與 `status` 的逐鍵相等，且 `items[0]` 同為 16 鍵
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_3_1]"
```
```gherkin
# AT-437-3-2
# 對應 AC: AC-SI-37-3（R158、R161 (d)）armed 的現查與 export 的固定值
# 測試類型: Integration
# 自動化工具: pytest + 替身 runner.run_argv（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_3_2_ -q -p no:xdist -o addopts=

Feature: armed
Scenario: 憑證是值
  Given `runner.run_argv` 以 `mock.patch.object` 換成回傳可設輸出的替身：(甲)輸出含一個非空的 NextRunTime 值、(乙)輸出表示任務不存在、(丙)拋例外
  When 各呼叫 `sched.armed_value(...)`，並取 `export --kind status` 的 `schedule.armed`
  Then (甲)`present` 為 `true`、`credential` 為該值逐字；(乙)`present` 為 `false`；(丙)`present` 為 `null`、`credential` 以 `NOT-EVALUABLE：` 起頭；`export` 的 `armed` 恆為字串 `NOT-EVALUABLE：export-reads-no-home` 且測試期間替身未被呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_3_2]"
```
```gherkin
# AT-437-3-E-1
# 對應 AC: AC-SI-37-3（R145、R158）overdue 的邊界與 null
# 測試類型: Unit
# 自動化工具: unittest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_model.py -k AT_437_3_E_1_ -q -p no:xdist -o addopts=

Feature: overdue
Scenario: 嚴格大於 2×心跳；載體缺席為 null；export 的 ne 列
  Given S-CELL 啟用、本格無 `run.open(f)` 也無 `sched.skip`、`HB` 為 15
  When 以 `now` 為 `cell_start＋30 分`、`＋30 分 1 秒`、`＋10 天` 取 `SCH`；加入一筆格內 `sched.skip` 後重取 `＋30 分 1 秒`；加入一筆格內 `run.open(f)` 後重取；對事件帳本不存在的 repo 取 `export --kind status`
  Then 依序 `overdue` 為 `false`、`true`、`true`；有 skip 後 `false`；有 `run.open(f)` 後 `false`；載體缺席時 `schedule.overdue` 為 `null` 且 `ne` 含 `{"field":"schedule.overdue","reason":"carrier-not-established"}`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_3_E_1]"
```

**B. 巡邏心跳、無人運轉與授權（SP；入帳之後的推進、commit、收尾與 Console (a) 運轉一族在 SA）**

> SP 的共通佈置：`HEARTBEAT(R4, now, **deps)`＝呼叫 `patrol.main(["--now", now, "--repo", R4], deps=Deps(...))` 並回 `(rc, out, err)`；`Deps` 可注入 `quota`（回 `QuotaState` 替身）、`driver_quiet`（回布林）、`which`、`preflight`、`run_argv`（預設換成呼叫 `STUB` 的包裝）、`verbs`（記錄巡邏器對 CLI 動詞的呼叫，預設走真入口）；環境變數 `AUTOSDD_SI_AUDIT_KEY` 以測試金鑰設於測試行程；全部家目錄在 tmp。

```gherkin
# AT-436-2-E-1
# 對應 AC: AC-SI-36-2（R144 黑窗不造成永久跳過）origin 落在黑窗內的跨格情境
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_2_E_1_ -q -p no:xdist -o addopts=

Feature: 黑窗過後同格即跑
Scenario: 22:00 啟用、黑窗 21:00-00:30
  Given `R4` 的 `sched.set` 於本機時間 22:00（以替身 `local_hm` 驅動）、週期 1440；其餘六種跳過皆不成立；`STUB` rc 為 0 且不產提案
  When 依序在 22:15、22:30、23:00（皆黑窗內）與次日 00:40（黑窗外、同格）呼叫 `HEARTBEAT`
  Then 前三次各 rc 為 `0`，合計恰一筆 `sched.skip`（`reason` 為 `blackout`、`due_at` 為格 0 起點）；00:40 該次新增 `run.open`（trigger `f`、`due_at` 為格 0 起點）且 `STUB` 被呼叫一次；其後 `SCH` 的 `ran_this_cell` 為 `true`；`check` 的 `sched.events` 與 `run.trigger_f_has_patrol_by` 皆 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_2_E_1]"
```
```gherkin
# AT-436-3-1
# 對應 AC: AC-SI-36-3（R148、R167）一次性心跳的步驟序，spawn 後立即返回
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_3_1_ -q -p no:xdist -o addopts=

Feature: 單次心跳
Scenario: 巡視、入帳、到期、運轉、推進後退出，不等待無人主控
  Given `R4` 啟用且本格到期；`console_pending[]` 有一份合法 `sched-set` 稽核檔；`Deps.verbs` 記錄呼叫序；`Deps.spawn_detached` 替身記錄呼叫並回假 pid
  When `HEARTBEAT` 一次
  Then rc 為 `0`；輸出含五行 `step=` 依序 `巡視`、`入帳`、`到期`、`運轉`、`推進`；`verbs` 記錄中 `sched set --carrier console` 先於 `run-open`、`run-open` 先於 `research`、`research` 先於 `scan`；`spawn_detached` 恰被呼叫一次、其後函式立即返回（沒有對子行程的等待呼叫），返回時 `<si>/locks/patrol.lock` 已釋放、`spawn.json` 已寫；`--json` 的 `steps` 長度為 5
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_3_1]"
```
```gherkin
# AT-436-3-2
# 對應 AC: AC-SI-36-3（R148）--dry-run 零寫入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_3_2_ -q -p no:xdist -o addopts=

Feature: dry-run
Scenario: 印計畫、不動任何東西
  Given 與 AT-436-3-1 同一情境；`snap(R4)` 與整個家目錄樹快照已取
  When `HEARTBEAT` 帶 `--dry-run`
  Then rc 為 `0`；輸出含「此心跳會做什麼」的逐步驟說明（含將入帳的 `audit_ref` 與將 spawn 的決定）；事件帳本、OBS 帳本、`SelfImproving_Proposals/`、家目錄樹（含 `locks/`、`patrol/`）與工作樹的快照皆逐位元相同；`STUB` 與 `verbs` 的寫入類呼叫次數為 0
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_3_2]"
```
```gherkin
# AT-436-3-E-1
# 對應 AC: AC-SI-36-3（R137、R148）用法錯誤
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_3_E_1_ -q -p no:xdist -o addopts=

Feature: patrol 用法
Scenario: rc 3 先於一切
  Given `R4`
  When 呼叫 `patrol --now 2026-11-02T08:00:00`（無 offset）、`patrol --bogus`、`patrol --repo <不存在目錄>`、`patrol --run RUN-X`、以及 `AUTOSDD_SI_DIR` 指向唯讀目錄時 `patrol`
  Then 皆 rc 為 `3`、stdout 空、stderr 至少一行；第五者 stderr 含 `HOME-UNWRITABLE`；`snap(R4)` 不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_3_E_1]"
```
```gherkin
# AT-436-3-E-2
# 對應 AC: AC-SI-36-3（R148）鎖、無人值守、例外不重試
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_3_E_2_ -q -p no:xdist -o addopts=

Feature: 第二道防線
Scenario: patrol.lock、UNATTENDED、例外
  Given `R4` 啟用且到期；先以 `apply_lock` 取走 `<si>/locks/patrol.lock`
  When 呼叫 `HEARTBEAT`；釋放鎖後於環境設 `AUTOSDD_UNATTENDED` 為 `1` 呼叫；移除該變數後把 `verbs` 的第一次呼叫換成拋 `RuntimeError` 的替身呼叫
  Then 第一次 rc `0`、輸出含「已有巡邏在跑」、`snap(R4)` 不變；第二次 rc `1`、碼 `UNATTENDED-REFUSED`、`snap(R4)` 不變（先於 OFF 判斷與入帳）；第三次 rc `1`、日誌含 `PATROL-EXCEPTION`、替身恰被呼叫一次（不重試）、鎖已釋放
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_3_E_2]"
```
```gherkin
# AT-436-5-E-1
# 對應 AC: AC-SI-36-5（R148）AUTOSDD_SI_PATROL_OFF 整次 no-op
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_5_E_1_ -q -p no:xdist -o addopts=

Feature: 逃生口
Scenario: 非空含字面 0 即 no-op、空字串視為未設
  Given `R4` 啟用且到期、`console_pending[]` 非空
  When 於環境分別設 `AUTOSDD_SI_PATROL_OFF` 為 `1`、`0`、空字串後呼叫 `HEARTBEAT`
  Then 前兩者 rc `0`、`snap(R4)` 不變、不入帳、不取鎖（`locks/patrol.lock` 不存在）、`patrol.log` 增恰一行；空字串者視為未設、正常入帳並開運轉
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_5_E_1]"
```
```gherkin
# AT-436-6-1
# 對應 AC: AC-SI-36-6（R142 (f)、R143 (f)）至多一個運轉
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_6_1_ -q -p no:xdist -o addopts=

Feature: 每格至多一個 (f) 運轉
Scenario: 已執行的格不再嘗試；未關的 Console 運轉使到期記 skip
  Given `R4` 啟用；第一次心跳成功開 (f) 運轉；另一個 repo 副本先有一個 trigger 為 `a` 的未關運轉
  When 第一個 repo 在同格再跑兩次心跳；副本跑一次心跳
  Then 第一個 repo 後兩次心跳 `run.open(f)` 總數仍為 `1`、`STUB` 總呼叫為 `1`、新增 `sched.skip` 為 0（本格已執行不嘗試）；副本新增恰一筆 `sched.skip`（`reason` 為 `run-open`）、無 `run.open(f)`、`STUB` 未被呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_6_1]"
```
```gherkin
# AT-436-6-E-1
# 對應 AC: AC-SI-36-6（R143 (c)）額度帶準備以上不 spawn；no_event 不構成成效
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_436_6_E_1_ -q -p no:xdist -o addopts=

Feature: 額度帶與成效
Scenario: prepare 帶跳過、兩個 no_event 不算成效
  Given `R4` 啟用；`Deps.quota` 回 `prepare` 帶
  When 跑一次心跳；之後改回 `free` 帶並連續完成兩個格的 (f) 運轉（`STUB` 零提案、巡邏器 `run-close`）
  Then 第一次新增恰一筆 `sched.skip`（`reason` 為 `quota-band`）、無 `run.open`、`STUB` 未被呼叫；兩個運轉的 `run.close` 皆 `no_event` 為 `true`；其後 `status` 的 `no_event` 為 `true`、`events_detected` 為空（不因兩個無事件運轉而出現任何成效類欄位）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_6_E_1]"
```
```gherkin
# AT-438-1-1
# 對應 AC: AC-SI-38-1（R151、R167）spawn 的 argv、環境、spawn.json（脫離式）
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_1_1_ -q -p no:xdist -o addopts=

Feature: spawn 形態
Scenario: argv 逐元素等於 fresh_argv，環境含四個必含鍵，牆鐘寫進 spawn.json
  Given 兩種運轉各一次：到期的 (f) 運轉，與本心跳入帳的 Console (a) 運轉；`Deps.spawn_detached` 替身把收到的 argv、env 鍵值、cwd 寫到 tmp 記錄檔並回執行期組出的假 pid
  When 各 `HEARTBEAT` 一次
  Then 記錄的 argv 逐元素等於 `resume_route.fresh_argv(<claude 路徑>, <prompt>, <任務目錄>)`（以同參數重算比較）；env 含 `AUTOSDD_UNATTENDED` 為 `1`、`AUTOSDD_SI_PATROL_RUN` 為本次 RUN 號、`CLAUDE_CODE_SUBAGENT_MODEL` 與 `resume_route.spawn_env()` 的值相同、`unattended_authz.HARNESS_BG_WAIT_ENV` 為 `RESUME_BG_WAIT_CEILING_SECONDS×1000` 的字串；`spawn_detached` 的簽章不含 timeout；替身記錄的旗標：以替身平臺為 Windows 時 `creationflags` 為 `CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` 的聯集（三個常數取自 `subprocess` 或 `getattr` 兜底值），以替身平臺為 POSIX 時 `start_new_session` 為 True 且無 `creationflags`（兩種平臺各跑一次）；`<si>/patrol/<RUN>/spawn.json` 含 `pid`（等於假 pid）、`started_at`、`wall_due_at`，且 `wall_due_at` 減 `started_at` 恰為 `unattended_authz.RESUME_HARD_WALL_SECONDS` 秒；cwd 的 `realpath` 等於 `R4` 的 `realpath`；任務目錄內有 `brief.md`；`brief.md` 的位元組等於傳入 prompt 所指檔案
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_1_1]"
```
```gherkin
# AT-438-1-2
# 對應 AC: AC-SI-38-1（R150）spawn 前置序與 research 三分支
# 測試類型: Integration
# 自動化工具: pytest + 替身 + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_1_2_ -q -p no:xdist -o addopts=

Feature: run-open f、research、scan
Scenario: rc 0／2 繼續、rc 1 改 offline 免掃、scan 只落日誌
  Given `R4` 啟用到期；`research --fetch` 的替身依次回 rc `0`、`2`、`1`；`scan` 替身回兩列候選
  When 各用一個新格（`now` 前進一天）跑一次心跳
  Then 三次皆先有 `run.open(f)`（`by` 為 `patrol`、`due_at` 為該格起點、座標為事件帳本路徑加 origin 行號）、再有 `research` 事件（rc 0／2＝`research.scan`；rc 1＝`research.skip` 的 `reason` 為 `offline`）、最後才 `STUB` 被呼叫；`scan` 的兩列候選出現在 `patrol.log` 與 `brief.md`，OBS 帳本位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_1_2]"
```
```gherkin
# AT-438-1-E-1
# 對應 AC: AC-SI-38-1（R143 (g)、R150）claude 不在 PATH
# 測試類型: Integration
# 自動化工具: pytest + 替身 + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_1_E_1_ -q -p no:xdist -o addopts=

Feature: 預檢先於開運轉
Scenario: spawn-failed 不留 run.open
  Given `R4` 啟用到期；`Deps.which` 對 `claude` 回 `None`
  When `HEARTBEAT` 兩次（同格）
  Then 新增恰一筆 `sched.skip`（`reason` 為 `spawn-failed`、`detail` 含 `claude-not-found`）；無 `run.open`、無 `research` 事件、`<si>/patrol/` 下無任務目錄；第二次不再新增事件（同格同因）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_1_E_1]"
```
```gherkin
# AT-438-1-E-2
# 對應 AC: AC-SI-38-1（R151、NFR-P4-3）子行程環境不洩漏
# 測試類型: Integration
# 自動化工具: pytest + 替身 claude + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_1_E_2_ -q -p no:xdist -o addopts=

Feature: 環境白名單
Scenario: 機密與其他 AUTOSDD 變數不傳
  Given 測試行程環境含：`AUTOSDD_SI_AUDIT_KEY`、`ANTHROPIC_API_KEY`、`MY_SERVICE_TOKEN`、`DB_PASSWORD`、`AUTOSDD_SI_PATROL_OFF` 為空字串、`AUTOSDD_QUOTA_HALT_PCT`、`AUTOSDD_SI_DIR`、`CLAUDE_CONFIG_DIR`、`PATH`、`APPDATA`（值皆為執行期組出的唯一字串）
  When `HEARTBEAT` 一次，`STUB` 記錄 env 的鍵與值
  Then 記錄的鍵集合 ⊆ `runner` 探針白名單 ∪ {`APPDATA`、`LOCALAPPDATA`、`CLAUDE_CONFIG_DIR`、`AUTOSDD_SI_DIR`} ∪ 四個必含鍵；不含 `AUTOSDD_SI_AUDIT_KEY`、`ANTHROPIC_API_KEY`、`MY_SERVICE_TOKEN`、`DB_PASSWORD`、`AUTOSDD_QUOTA_HALT_PCT`、`AUTOSDD_SI_PATROL_OFF`；各唯一值字串不出現在記錄檔的任何位置（含 argv 與 prompt）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_1_E_2]"
```
```gherkin
# AT-438-1-E-3
# 對應 AC: AC-SI-38-1（R167 (a)；D-QA-14）breakaway 被拒時 fail-closed
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_1_E_3_ -q -p no:xdist -o addopts=

Feature: 脫離旗標被拒
Scenario: 不 spawn、不留 spawn.json，(f) 記 spawn-failed，(a) 只寫日誌，下一心跳再試
  Given 兩種運轉各一個 repo：到期的 (f)，與本心跳入帳的 Console (a)；`Deps.spawn_detached` 替身對第一次呼叫拋 `PermissionError`（模擬 breakaway 被拒）、其後正常
  When 各 `HEARTBEAT` 兩次
  Then (f)：第一次新增恰一筆 `sched.skip`（`reason` 為 `spawn-failed`、`detail` 以 `breakaway-denied` 起頭）、無 `spawn.json`、`STUB` 與 research 以外的後續步驟未進行；第二次（同格）不重複記 skip，`spawn_detached` 被呼叫並成功；(a)：第一次只在 `patrol.log` 寫一行（`step=運轉`、碼含 `breakaway-denied`）、**無任何新增 `sched.skip`**、`run.open` 保持為一筆、無 `spawn.json`；第二次 `spawn_detached` 成功、`run.open` 總數仍為一
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_1_E_3]"
```
```gherkin
# AT-438-2-1
# 對應 AC: AC-SI-38-2（R152）任務書生成
# 測試類型: Unit
# 自動化工具: unittest + 真 SOP 檔（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_2_1_ -q -p no:xdist -o addopts=

Feature: patrolbrief
Scenario: 占位符替換、必含項、降載聲明
  Given 真 SOP 的〈無人運轉任務書範本〉圍欄；`patrolbrief.render(template, fields)` 的 `fields` 含全部大寫占位符值
  When 以額度帶 `free`、`notice`、`converge` 各渲染一次
  Then 輸出不含任何 `<大寫底線>` 占位符；仍含小寫與中文占位符（`<來源 id>`、`<PROP>`、`<held-out 目錄>`、`<凍結者>`）；含 RUN 號、`trigger=f`、到期時刻、事件文字、研究結果、來源檔路徑、`scan` 候選、預算分鐘數、角色序八步、禁止事項各行、四節 handback 標題逐字等於 `resume_route.HANDBACK_MARKERS`；`notice`、`converge` 版含降載聲明、`free` 版不含；`template_problems(真 SOP)` 為空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_2_1]"
```
```gherkin
# AT-438-2-E-1
# 對應 AC: AC-SI-38-2（R152、R143 (g)）範本缺必含項即拒絕 spawn
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_2_E_1_ -q -p no:xdist -o addopts=

Feature: 範本結構判準
Scenario: 逐項刪去
  Given 真 SOP 的副本放在 `R4`；依序刪去：`## 做了什麼` 標題、`禁止事項` 節、角色序第 6 步、`<RUN>` 占位符、整個程式碼圍欄
  When 對每份副本呼叫 `template_problems` 並跑一次心跳（每份換一個新格）
  Then 每份 `template_problems` 回非空且各含不同的碼；心跳新增恰一筆 `sched.skip`（`reason` 為 `spawn-failed`、`detail` 以 `sop-template:` 起頭）、無 `run.open`、`STUB` 未被呼叫；對照組（未刪的真 SOP）可 spawn
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_2_E_1]"
```
```gherkin
# AT-438-3-1
# 對應 AC: AC-SI-38-3（R153 ①、④）A 類八個動詞的真值表
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_3_1_ -q -p no:xdist -o addopts=

Feature: run-scoped 放行
Scenario: research、attr、attr-confirm、attr-reject、prop-new、prop-revise、heldout-freeze、card --issue
  Given 每個動詞備一個合法的呼叫（由 §5.2 的 `a_class_calls(R4, run=RUN_A)` 建構；`attr-confirm`／`attr-reject` 的 `--by` 與提出者不同；PROP 所屬運轉為 `RUN_A`）
  When 對每個動詞在四種環境各呼叫一次：(甲)兩變數皆未設；(乙)`AUTOSDD_UNATTENDED` 為 `1`、`PATROL_RUN` 未設；(丙)`AUTOSDD_UNATTENDED` 為 `1`、`PATROL_RUN` 為 `RUN_A`、呼叫指向 `RUN_A`；(丁)`AUTOSDD_UNATTENDED` 為 `1`、`PATROL_RUN` 為 `RUN_B`、呼叫指向 `RUN_A`
  Then (甲)(丙)rc 為 `0`（該動詞的既有成功路徑）；(乙)(丁)rc 為 `1`、碼 `UNATTENDED-REFUSED`、呼叫前後 `snap(R4)` 逐位元相同；八個動詞 × 四環境共 32 格逐格斷言（subTest 名含動詞與環境代號）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_3_1]"
```
```gherkin
# AT-438-3-2
# 對應 AC: AC-SI-38-3（R153 ②③⑤）decide 只准 console、C 類一律拒、唯讀不受限
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_3_2_ -q -p no:xdist -o addopts=

Feature: B 類與 C 類
Scenario: 十三個 C 類動詞即使 PATROL_RUN 有設也拒
  Given 環境 `AUTOSDD_UNATTENDED` 為 `1`、`AUTOSDD_SI_PATROL_RUN` 為 `RUN_A`；C 類清單 `run-open`、`run-close`、`obs-add`、`obs-close`、`sched set`、`sched arm`、`sched disarm`、`sandbox`、`verify`、`promote`、`rollback`、`measure`、`patrol` 各備合法呼叫；唯讀清單 `check`、`status`、`scan`、`card`（無 `--issue`）、`export`、`capacity`、`issues`、`sched show`、`obs-add --dry-run`
  When 逐一呼叫
  Then C 類十三個 rc 皆 `1`、碼 `UNATTENDED-REFUSED`、零寫入；`decide --carrier transcript` rc 為 `1`、碼 `UNATTENDED-REFUSED`；`decide --carrier console` 通過授權閘（其 rc 可為 `1`，但碼不是 `UNATTENDED-REFUSED`，例如 `AUDIT-KEY-MISSING`）；唯讀九項 rc 皆 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_3_2]"
```
```gherkin
# AT-438-3-E-1
# 對應 AC: AC-SI-38-3（R153 ①「行為放寬的負控」）跨運轉寫入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_3_E_1_ -q -p no:xdist -o addopts=

Feature: 放寬後仍拒跨運轉
Scenario: --run 不符與所屬 PROP 的 run 不符兩路
  Given 兩個運轉 `RUN_A`、`RUN_B`；`RUN_A` 下有一個 PROP（`prop_a`）；環境 `AUTOSDD_UNATTENDED` 為 `1`、`PATROL_RUN` 為 `RUN_B`
  When 呼叫 `research --skip --run RUN_A …`、`prop-new --run RUN_A …`、`prop-revise <prop_a> …`、`heldout-freeze <prop_a> …`、`card <prop_a> --issue`、`attr-confirm --att <屬 RUN_A 的 ATT> …`
  Then 六個 rc 皆 `1`、碼 `UNATTENDED-REFUSED`、`snap(R4)` 不變；把 `PATROL_RUN` 改為 `RUN_A` 後同樣六個呼叫的授權閘通過（其後的 rc 依各動詞前置，但碼不是 `UNATTENDED-REFUSED`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_3_E_1]"
```
```gherkin
# AT-438-3-E-2
# 對應 AC: AC-SI-38-3（R153、R160）環境值邊界與單一實作
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 靜態掃描（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_3_E_2_ -q -p no:xdist -o addopts=

Feature: 環境語意
Scenario: 字面 0、空字串、PATROL_RUN 單獨存在、單一實作
  Given 一個 A 類呼叫（`research --skip`）與一個 C 類呼叫（`run-close`）
  When 設 `AUTOSDD_UNATTENDED` 為 `0`、空字串；另只設 `AUTOSDD_SI_PATROL_RUN`（不等於呼叫的 `--run`）；並靜態掃描套件原始碼中讀取 `AUTOSDD_UNATTENDED` 的站點
  Then `0` 時兩者 rc `1`（字面 `0` 算有設）；空字串與「只設 PATROL_RUN」時兩者行為與兩變數皆未設逐位元相同；套件內讀 `AUTOSDD_UNATTENDED` 或 `UNATTENDED_ENV` 的站點只有 `unattended.py`（`decwrite.refuse_unattended` 與各動詞皆改呼叫 `unattended.gate`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_3_E_2]"
```
```gherkin
# AT-438-4-1
# 對應 AC: AC-SI-38-4（R153 ②、R154）逐字稿載體一律拒、console 載體通過授權閘
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_4_1_ -q -p no:xdist -o addopts=

Feature: DEC 只認 Console
Scenario: 無人行程的 decide
  Given 一個 `proposed` 的 PROP 與一份合成逐字稿中的真人核准引言；環境 `AUTOSDD_UNATTENDED` 為 `1`、`PATROL_RUN` 為該 PROP 的運轉；測試行程**不設**金鑰變數
  When `decide <PROP> --kind approve --sid <S> --line <N>`；`decide <PROP> --carrier console --audit-ref <U>`（稽核檔存在）
  Then 第一個 rc `1`、碼 `UNATTENDED-REFUSED`、無 `dec` 事件；第二個 rc `1`、碼 `AUDIT-KEY-MISSING`（證明授權閘已放行、止於金鑰面）、無 `dec` 事件
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_4_1]"
```
```gherkin
# AT-438-4-E-1
# 對應 AC: AC-SI-38-4（R154、R155 (a)）心跳不代決
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_patrol.py -k AT_438_4_E_1_ -q -p no:xdist -o addopts=

Feature: 巡邏器不下決定
Scenario: 無 DEC 的待決 PROP 只到 card --issue
  Given 無人運轉已產出一個 `proposed` 的 PROP、尚無 `dec`；`Deps.verbs` 記錄全部對 CLI 的呼叫
  When 跑三次心跳（跨一個格以上）
  Then `verbs` 記錄中沒有任何 `decide`（含 `--kind` 與 `--carrier transcript` 形）；PROP 狀態仍為 `proposed`；沒有 `sandbox`、`verify`、`promote` 呼叫；`card --issue` 至多被記一次 `card` 事件（卡面送達），重跑不重複追加相同 digest 的 `card`（沿 P2 既有冪等規則）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_4_E_1]"
```
```gherkin
# AT-438-5-1
# 對應 AC: AC-SI-38-5（R155 (d)）核准晉升後的自動 commit
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_5_1_ -q -p no:xdist -o addopts=

Feature: 本機 commit
Scenario: 白名單、訊息、不 push、不繞 hook
  Given 夾具 repo 的工作樹乾淨（SI 自有路徑除外）；一個 `verified` 的 PROP 與已入帳的 `dec(promote)`（Console 載體稽核檔）；repo 的 `pre-commit` hook 為會記錄「被呼叫」的腳本（rc 0）；無任何 remote；`sched_auto_commit` 為 `true`
  When `HEARTBEAT` 一次
  Then `promote` 成功；恰新增一個 commit，其變更路徑集合 ⊆ `app.promote.touched` ∪ SI 自有路徑 且包含 `touched` 全部；commit 訊息含 PROP ID、DEC ID 與 APP ID；hook 被呼叫一次；`verbs` 記錄與 git 呼叫記錄中無 `push`、無 `--no-verify`、無 `add -A`／`add .`；其後 `measure` 被呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_5_1]"
```
```gherkin
# AT-438-5-E-1
# 對應 AC: AC-SI-38-5（R155 (b)(d)；D-QA-3）promote 前樹不乾淨：只寫日誌，不寫 sched.skip
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_5_E_1_ -q -p no:xdist -o addopts=

Feature: 髒樹不 promote
Scenario: SI 自有路徑以外有改動，排程啟用與停用兩個子情境皆然
  Given 同 AT-438-5-1，但工作樹另有未提交的 `notes/dirty.txt`；兩個子情境：(甲)排程啟用且本格有 (f) 到期；(乙)排程停用（無格線，只有人的 DEC 待推進）
  When 各 `HEARTBEAT` 兩次
  Then 兩子情境皆無 `app.promote` 事件、`verbs` 無 `promote` 呼叫、無新 commit；兩子情境皆**零新增 `sched.skip`**（推進路徑只寫日誌；(甲)若有 (f) 到期被其他原因擋下才有 skip，與本情境無關，夾具使其他六種跳過皆不成立）；乙情境事件帳本在兩次心跳後與前逐位元組相同；`patrol.log` 每次心跳各一行帶 `step=推進` 與原因 `dirty-tree`；`notes/dirty.txt` 內容不變；清乾淨後下一心跳可 promote
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_5_E_1]"
```
```gherkin
# AT-438-5-E-2
# 對應 AC: AC-SI-38-5（R155 (d)）touched 之外的髒檔不被 add
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 替身 promote（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_5_E_2_ -q -p no:xdist -o addopts=

Feature: 提交白名單
Scenario: promote 期間冒出的多餘檔
  Given 同 AT-438-5-1；`promote` 以 `mock.patch.object` 包一層：除原本套用外另寫入 `stray/extra.txt`（模擬套用器多寫）
  When `HEARTBEAT` 一次
  Then 新 commit 的變更路徑不含 `stray/extra.txt`；`stray/extra.txt` 仍為未追蹤；commit 路徑集合 ⊆ `touched` ∪ SI 自有路徑
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_5_E_2]"
```
```gherkin
# AT-438-5-E-3
# 對應 AC: AC-SI-38-5（R155 (d)、R157）commit 失敗與 auto_commit 為 false
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_5_E_3_ -q -p no:xdist -o addopts=

Feature: commit 的失敗處置
Scenario: hook 拒絕不重試、不繞過；關閉自動 commit
  Given 同 AT-438-5-1，但 `pre-commit` hook 計數並以 rc `1` 結束；另一個副本把 `sched_auto_commit` 設為 `false`
  When 兩者各跑 `HEARTBEAT` 一次
  Then 前者 `promote` 已成功、無新 commit、hook 恰被呼叫一次（不重試）、`patrol.log` 有一行帶 `step=commit` 與非零 rc、輸出含一列 `obs-draft`、未出現 `--no-verify`；後者 `promote` 成功、hook 與 `git commit` 皆未被呼叫、工作樹保留改動、`measure` 仍被呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_5_E_3]"
```
```gherkin
# AT-438-6-1
# 對應 AC: AC-SI-38-6（R156、R167）以事件帳本為憑的收尾，發生在後續心跳的步 0′
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_6_1_ -q -p no:xdist -o addopts=

Feature: 零提案與有提案
Scenario: 替身行程的自述不算數
  Given 兩個運轉：甲運轉 spawn 後其 handback 寫已完成但事件帳本無 `prop`；乙運轉 spawn 後替身經真 CLI 寫出一個 `prop`（帶 `--run`）；`Deps.pid_alive` 先回存活、再回已結束
  When 各跑兩次心跳：第一次使其 spawn（返回後立即結束），第二次（`pid_alive` 已回已結束）
  Then 第一次心跳 rc 為 `0`、`spawn.json` 含 `pid`、`started_at`、`wall_due_at`、`patrol.lock` 已釋放、尚無 `run.close`；第二次心跳步 0′ 後：甲 `run-close` 被巡邏器呼叫、`run.close` 的 `no_event` 為 `true`；乙運轉保持開啟（無 `run.close`）、`status.open_runs` 含該運轉；兩者 `spawn.json` 補寫 `closed_at`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_6_1]"
```
```gherkin
# AT-438-6-2
# 對應 AC: AC-SI-38-6（R167 (c)；D-QA-10）同一時間至多一個進行中的無人運轉
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_6_2_ -q -p no:xdist -o addopts=

Feature: 單一進行中運轉
Scenario: spawn.json 存活且未超牆時其他運轉的 spawn 延後
  Given 運轉 `RUN_A` 已 spawn，`Deps.pid_alive` 回存活、`now` 早於 `wall_due_at`；另有一份本心跳入帳的 Console `run-request` 與下一格的 (f) 到期
  When 在 `RUN_A` 進行中跑兩次心跳（第二次跨到下一格）
  Then 兩次心跳的步 0′ 皆不動 `RUN_A`；`spawn_detached` 總呼叫仍為 `1`（不為新運轉 spawn）；`patrol.log` 各有一行延後原因（已有進行中的無人運轉）；Console 的 `run-request` 仍被入帳為 `run.open` 或依 R146 記 `sched.skip(run-open)`；(f) 到期因 `RUN_A` 未關而至多記一筆 `sched.skip(run-open)`；`RUN_A` 結束後的下一心跳才為延後的運轉 spawn
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_6_2]"
```
```gherkin
# AT-438-6-E-1
# 對應 AC: AC-SI-38-6（R156、R167 (b)）handback 缺節、harness 殺行程、逾牆
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_6_E_1_ -q -p no:xdist -o addopts=

Feature: 只記日誌與終止的三種收尾
Scenario: 不重 spawn，逾牆才殺行程樹
  Given 三個運轉 spawn 後：(甲)行程已結束、handback 缺 `## 卡在哪`；(乙)行程已結束、stderr 檔含 `unattended_authz.HARNESS_BG_KILL_MARK`；(丙)行程仍存活而 `now` 晚於 `wall_due_at`（`Deps.kill_tree` 替身記錄呼叫）
  When 各跑一次步 0′ 所在的心跳
  Then 三運轉各只 spawn 過一次；`patrol.log` 依序有「handback 不完整」「harness 背景殺行程」「逾牆終止」各一行；(丙)的 `kill_tree` 恰被呼叫一次、其後依事件帳本收尾；三運轉零提案者皆 `run-close`；無重新 spawn
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_6_E_1]"
```
```gherkin
# AT-438-7-E-1
# 對應 AC: AC-SI-38-7（R154）巡邏器不能做的拒收路徑
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_7_E_1_ -q -p no:xdist -o addopts=

Feature: 守衛面不經巡邏器修改
Scenario: 觸及不可進化面的 PROP
  Given 一個已入帳 `dec(promote)` 的 PROP，其 patch 觸及 `non_evolvable_globs` 的路徑（以夾具把該路徑納入 `touched`）
  When `HEARTBEAT` 一次
  Then `promote` 被既有前置檢查拒絕（rc 1）、無 `app.promote`、無新 commit、`patrol.log` 記拒收碼；巡邏器不改 `params.json`、不重試；工作樹其他檔位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_7_E_1]"
```
```gherkin
# AT-438-8-1
# 對應 AC: AC-SI-38-8（R166；D-QA-2）Console 載體 (a) 運轉在同一心跳執行並收尾
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_8_1_ -q -p no:xdist -o addopts=

Feature: 立即啟動一次演化的執行者
Scenario: 入帳 run-request 後同心跳 spawn，無 prop 則 run-close
  Given `R4` 的排程為**停用**（證明不看啟用旗標、不受格線限制）；`console_pending[]` 有一份合法 `run-request` 稽核檔；七種跳過皆不成立；`Deps.spawn_detached` 替身
  When 先 `HEARTBEAT` 一次，再於替身行程已結束後 `HEARTBEAT` 一次
  Then 第一次：事件序含 `run.open`（`trigger` 為 `a`、`carrier` 為 `console`、帶該 `audit_ref`），其後有 `research` 事件，`spawn_detached` 恰被呼叫一次（任務書 trigger 行含 `trigger=a`）、`spawn.json` 已寫；第二次：該運轉 `run-close` 的 `no_event` 為 `true`；兩次心跳皆無任何新增 `sched.skip`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_8_1]"
```
```gherkin
# AT-438-8-E-1
# 對應 AC: AC-SI-38-8（R166、R143 ②～⑦）被擋時只寫日誌、運轉保持開啟、下一心跳再試
# 測試類型: Integration
# 自動化工具: pytest + 替身 spawn_detached + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_438_8_E_1_ -q -p no:xdist -o addopts=

Feature: (a) 運轉被擋
Scenario: 額度帶準備等原因擋下不寫 sched.skip
  Given 與 AT-438-8-1 同一情境，但 `Deps.quota` 回 `prepare` 帶；另三個子情境：`driver_quiet` 為假（有人在開車）、黑窗內、`which` 回 `None`（spawn-failed 預檢）
  When 各 `HEARTBEAT` 一次，再把阻擋原因解除後 `HEARTBEAT` 一次
  Then 第一次：`run.open`（`a`）已寫入、`spawn_detached` 未被呼叫、`patrol.log` 有一行帶 `step=運轉` 與對應原因碼（`quota-band`、`other-driver`、`blackout`、`spawn-failed`）、**無任何新增 `sched.skip`**、運轉仍開；第二次：`spawn_detached` 恰被呼叫一次、`run.open` 總數仍為 `1`（不重新入帳、不重開運轉）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_8_E_1]"
```
```gherkin
# AT-439-2-E-1
# 對應 AC: AC-SI-39-2（R149；D-QA-11）入帳拒收碼逐一保留稽核檔
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_2_E_1_ -q -p no:xdist -o addopts=

Feature: 拒收碼
Scenario: 每種拒收保留稽核檔、一行日誌、不重試
  Given 四份稽核檔：已入帳過的重複 `audit_ref`（其事件已存在，不在 `console_pending`——巡邏器不會再碰它，`AUDIT-REF-REUSED` 由 CLI 面的 AT-437-1-E-x 覆蓋；D-IMP-6 (4)）、金鑰變數缺席下的合法檔（`AUDIT-KEY-MISSING`）、外層 `kind` 與入帳路徑不符（`AUDIT-KIND-MISMATCH`）、外層 `audit_ref` 與檔名不符（`AUDIT-REF-MISMATCH`）
  When `HEARTBEAT` 連續兩次
  Then 四份檔皆仍在、`status.console_pending` 仍含後三份（重複者不在其中，斷言它不再被重試）；`patrol.log` 對後三份每份各一行帶各自拒收碼與一列 `obs-draft`，第二次不重複；每份每心跳入帳呼叫至多一次；事件帳本與 OBS 帳本無由這些檔造成的新增
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_2_E_1]"
```
```gherkin
# AT-439-3-E-1
# 對應 AC: AC-SI-39-3（R155 (a)；D-QA-11）非 approve 的 dec 不觸發 sandbox
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_3_E_1_ -q -p no:xdist -o addopts=

Feature: 只有 approve 推進 sandbox
Scenario: reject、return、decline-promote、ack-handoff 不被推進
  Given 四個 PROP 各有一個已入帳的 `dec`：`reject`、`return`、`decline-promote`（針對 `verified` 者）、`ack-handoff`；另一個 `approve` 但缺 `heldout.freeze` 的 PROP
  When `HEARTBEAT` 兩次
  Then 四個非 approve 的 PROP 無任何 `app.sandbox`、`app.verify`、`app.promote` 事件、無 `card` 新事件；巡邏器未寫任何 `dec`；缺 `heldout.freeze` 的 PROP 被跳過、日誌記原因、無 `sched.skip`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_3_E_1]"
```
```gherkin
# AT-439-4-E-1
# 對應 AC: AC-SI-39-4（R155 (a)(b)；D-QA-11）promote 前置缺 heldout.freeze 跳過且不記 skip
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_4_E_1_ -q -p no:xdist -o addopts=

Feature: 前置缺件跳過
Scenario: 缺 heldout.freeze 的 PROP 不 promote，補上後下一心跳可推進
  Given 一個 `verified` 的 PROP 有已入帳的 `dec(promote)`，但夾具刪去其 `heldout.freeze` 事件；排程啟用且本格另有 (f) 到期的其他六種跳過皆不成立
  When `HEARTBEAT` 兩次；補回 `heldout.freeze` 後再 `HEARTBEAT` 一次
  Then 前兩次無 `app.promote`、無 commit、無新增 `sched.skip`、日誌各一行記缺 `heldout.freeze`；補回後的心跳 `promote` 成功並 commit
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_4_E_1]"
```
```gherkin
# AT-439-5-E-1
# 對應 AC: AC-SI-39-5（R157；D-QA-11）日誌行格式負控
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_5_E_1_ -q -p no:xdist -o addopts=

Feature: 日誌格式
Scenario: 成功與失敗步驟的欄位、單行、不含金鑰
  Given 一個必拒的稽核檔（入帳步驟失敗，說明文字含換行）、其餘步驟成功；測試金鑰為執行期組出的唯一字串 `K`
  When `HEARTBEAT` 一次並逐行解析 `patrol.log`
  Then 每行符合 `<ISO 帶 offset> step=<巡視|入帳|到期|運轉|推進|commit> rc=<整數> code=<非空字串> <說明>` 的單行形；成功步驟為 `rc=0` 且 `code=-`；失敗的入帳步驟 `rc` 非 0 且 `code` 為拒收碼（不為 `-`）；說明中的換行被改為空白；全檔不含 `K`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_5_E_1]"
``````gherkin
# AT-439-1-1
# 對應 AC: AC-SI-39-1（R149）五種 kind 的入帳與排序
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_1_1_ -q -p no:xdist -o addopts=

Feature: 逐檔入帳
Scenario: decide、obs-add、obs-close、sched-set、run-request 依 time 升冪
  Given 五份合法稽核檔，`time` 依序為 `run-request`（最早）、`obs-add`、`sched-set`、`decide`、`obs-close`（最晚）；另一組 `sched-set` 與 `run-request` 的 `time` 相同
  When `HEARTBEAT` 一次
  Then `Deps.verbs` 記錄的入帳呼叫序等於 `time` 升冪；每份對應事件或 OBS 列都在；`status.console_pending` 清空；相同 `time` 者依 `audit_ref` 位元組序；金鑰取自環境變數 `AUTOSDD_SI_AUDIT_KEY`（無此變數時入帳 rc 為 `1`、碼 `AUDIT-KEY-MISSING`，稽核檔保留）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_1_1]"
```
```gherkin
# AT-439-1-E-1
# 對應 AC: AC-SI-39-1（R149、NFR-P4-3）金鑰不洩漏；同心跳改週期加立即啟動
# 測試類型: Integration
# 自動化工具: pytest + 替身 claude + 全樹掃描（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_1_E_1_ -q -p no:xdist -o addopts=

Feature: 金鑰面
Scenario: 植入唯一字串後全樹掃描為零
  Given 測試金鑰為執行期組出的唯一字串 `K`，設為 `AUTOSDD_SI_AUDIT_KEY`；一份 `sched-set`（改週期為 120）與一份 `run-request`（`time` 較晚）；排程已啟用
  When `HEARTBEAT` 一次（含 spawn）
  Then 掃描 `patrol.log`、全部 stdout／stderr、`brief.md`、handback 目錄、事件帳本、OBS 帳本、`STUB` 記錄檔與 `--json` 輸出，`K` 命中數為 0；事件序為 `sched.set`（週期 120）先於 `run.open(a)`（依操作序）；新 origin 使本格起點為該 `sched.set` 的 `t`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_1_E_1]"
```
```gherkin
# AT-439-2-1
# 對應 AC: AC-SI-39-2（R149）入帳被拒的處置
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_2_1_ -q -p no:xdist -o addopts=

Feature: 拒收處置
Scenario: 保留稽核檔、一列 obs-draft、不重試、去重、與手動入帳互斥
  Given 一份 MAC 被改動的稽核檔 `UX`；一份合法稽核檔 `UY` 且鎖被另一執行緒持有（`evwrite.PAUSE_HOOK`）
  When `HEARTBEAT` 連續三次（鎖在第二次釋放）；其間互動視窗（同行程另一呼叫）手動入帳 `UY`
  Then `UX` 檔仍在、`status.console_pending` 仍含它；`patrol.log` 對 `UX` 只有一行（含 `AUDIT-MAC-MISMATCH` 與一列 `obs-draft`），第二、三次不重複；`UX` 的入帳呼叫次數每心跳至多一次（不在同心跳內重試）；`UY` 在鎖忙時該心跳跳過、下一心跳或手動路徑入帳，事件帳本中 `audit_ref` 為 `UY` 的 `sched.set`／`dec` 恰一筆
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_2_1]"
```
```gherkin
# AT-439-3-1
# 對應 AC: AC-SI-39-3（R155 (a)(b)）approve 後的推進
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_3_1_ -q -p no:xdist -o addopts=

Feature: sandbox、verify、card --issue
Scenario: 原樣進卡面；缺凍結者就跳過
  Given PROP `P1`（有 `heldout.freeze`）與 `P2`（無 `heldout.freeze`）各有已入帳的 `dec(approve)`；另有 `P3` 的 `app.verify` 將為 `FAIL`（夾具使其驗證不過）
  When `HEARTBEAT` 一次，再跑一次
  Then `P1` 依序有 `app.sandbox`、`app.verify`、`card` 事件，卡面中的 `verdict` 與 `reasons` 與 `app.verify` 事件逐字一致；`P3` 的 verdict 為 `FAIL` 仍原樣進卡面、沒有任何 `dec(reject)`／`dec(return)` 被巡邏器寫入；`P2` 無 `app.sandbox`、日誌記「缺 heldout.freeze」、**無** `sched.skip` 新增；第二次心跳不對 `P1` 重複 `sandbox`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_3_1]"
```
```gherkin
# AT-439-3-2
# 對應 AC: AC-SI-39-3（R155 (a)(c)）promote、rollback 與 run-close
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_3_2_ -q -p no:xdist -o addopts=

Feature: 晉升、回滾與收尾
Scenario: 依序推進，皆離開待人工決定態後 run-close
  Given 運轉 `RUN_A` 下兩個 PROP：`Pa`（`verified`、已入帳 `dec(promote)`）、`Pb`（已晉升、已入帳 `dec(rollback)`）；乾淨工作樹
  When `HEARTBEAT` 一次，再跑一次
  Then 事件序含 `Pa` 的 `app.promote`、其後 `Pa` 的 `mea.*`（`measure` 的輸出，至少 `mea.report` 或 `mea.open`）、`Pb` 的 `app.rollback`；各自一個本機 commit（訊息含各自 PROP 與 DEC）；兩個 PROP 皆離開待人工決定態後 `run-close` 被呼叫一次，`run.close.outcomes` 記兩個 PROP 的狀態；第二次心跳不再 `promote`、不再 `rollback`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_3_2]"
```
```gherkin
# AT-439-4-1
# 對應 AC: AC-SI-39-4（R155 (a)）無 DEC 零動作、偽造 DEC 被擋
# 測試類型: Integration
# 自動化工具: pytest + 真 git + 夾具 repo（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_4_1_ -q -p no:xdist -o addopts=

Feature: 前置恆為人的決定
Scenario: 缺 DEC 與偽造 DEC
  Given `Pc`（`approved` 之前、無 `dec`）、`Pd`（事件帳本中被手寫了一筆 `dec(promote)`，但無對應稽核檔與逐字稿，`decverify` 回查會失敗）
  When `HEARTBEAT` 兩次
  Then `Pc` 無任何 `app.*` 事件；`Pd` 的 `promote` 被拒（rc 1、`decverify` 的失敗碼）、無 `app.promote`、無 commit、日誌記碼；`check` 的 `events.dec_console` **非 PASS**（手寫 Console 載體 `dec` 無稽核檔時該項為非阻塞 NE `CONSOLE-AUDIT-MISSING`；偵測面仍在——D-IMP-6 (5)）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_4_1]"
```
```gherkin
# AT-439-5-1
# 對應 AC: AC-SI-39-5（R157）日誌格式與步驟獨立
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 替身（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_5_1_ -q -p no:xdist -o addopts=

Feature: 失敗可偵測
Scenario: 入帳失敗不阻止到期判定；日誌丟失不影響帳本
  Given 一份必拒的稽核檔；排程啟用到期、其餘六種跳過不成立
  When `HEARTBEAT` 一次；刪除 `patrol.log` 後 `check` 與 `status`
  Then 入帳步驟 `rc=1` 的日誌行符合 `<ISO 帶 offset> step=入帳 rc=1 code=<碼> <說明>`；之後仍有 `step=到期` 與 `step=運轉` 行且運轉被開；刪日誌後 `check` 的結果與刪前逐項相同、`status` 的 `schedule` 不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_439_5_1]"
```

**C. 閘門與靜態判準：OS 任務、`check`、事件欄位表、參數、能力登記、SOP、同步、錨定與範圍（SG）**

```gherkin
# AT-436-4-1
# 對應 AC: AC-SI-36-4（R161 (a)(b)）安裝器三支任務與三層鎖逐任務對齊
# 測試類型: Unit
# 自動化工具: unittest + 文字掃描（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_436_4_1_ -q -p no:xdist -o addopts=

Feature: 期望表與安裝器
Scenario: 任務集合、逐任務逐值、小時數
  Given `tools/install_windows_nightly.ps1` 與 `tools/scheduled_task_expectations.json` 的現況；`test_install_windows_nightly.py` 的三層鎖已依 R163 同步
  When 解析安裝器註冊的任務名（含第三支）、期望表、套用手段；對安裝器副本逐項改動（刪去 `IgnoreNew` 的套用、把 patrol 的小時數改成 4、把 patrol 的 `MultipleInstancesPolicy` 期望改成 `StopExisting`、任務集合少一支）
  Then 期望表任務集合等於安裝器註冊集合且恰含 `AutoClaude_Nightly`、`AutoClaude_WindowsSmoke`、`AutoSDD_SI_Patrol`；三支的 `expected` 鍵集合相同（七鍵）；patrol 的期望值為 `Settings/ExecutionTimeLimit` 是 `PT1H`、`Settings/WakeToRun` 是 `false`（nightly、smoke 為 `true`）、`Settings/MultipleInstancesPolicy` 是 `IgnoreNew`、`Principals/Principal/LogonType` 是 `S4U`，且 `expected_trigger_time` 缺省；nightly 與 smoke 的 `StopExisting` 對應 COM fixup（`MultipleInstances = 3`）、patrol 的 `IgnoreNew` 對應模組參數 `-MultipleInstances IgnoreNew`，兩種套用手段各只出現在其任務上；`Register-ScheduledTask` 恰三處且各帶 `-Principal $principal`；四個副本改動各使對應鎖轉紅（逐項 `assertFalse` 於鎖函式回傳）；`schedule_backend.py` 與 `check_scheduled_task_drift.py` 的位元組與 HEAD 相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_4_1]"
```
```gherkin
# AT-436-4-2
# 對應 AC: AC-SI-36-4（R161 (a)）觸發形態與 -WhatIf 預覽
# 測試類型: Integration
# 自動化工具: pytest + powershell.exe -WhatIf（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_436_4_2_ -q -p no:xdist -o addopts=

Feature: 觸發與 Action
Scenario: 重複間隔取自心跳參數，WhatIf 不動排程器
  Given 安裝器文字；`params.json` 的 `sched_heartbeat_minutes`；有 Windows PowerShell 引擎的平台另跑 `-WhatIf`（無引擎的平台以 `_ps_engine()` 為 `None` 判並改走靜態判準，不 skip）
  When 掃描安裝器的 patrol 區段；跑 `-WhatIf`
  Then 重複間隔等於心跳參數分鐘數（安裝器自 `params.json` 讀、不寫死第二份）、持續一天、每日 00:00 起；巡邏 Action 的 `-Argument` 字串**逐旗標**含 `-NoProfile`、`-WindowStyle Hidden`、`-ExecutionPolicy Bypass`、`-File`（不釘旗標相鄰——D-IMP-7，與 R84 對 `test_install_windows_nightly.py` 的同型修法一致）且安裝器含 `tools\si_patrol_tick.ps1`；`-WhatIf` 預覽逐項列出三支任務與 `AutoSDD_SI_Patrol` 的設定集、rc 為 `0`、`Get-ScheduledTask` 前後的任務清單相同（不動排程器）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_4_2]"
```
```gherkin
# AT-436-4-3
# 對應 AC: AC-SI-36-4（R161 (c)、NFR-P4-5）包裝腳本
# 測試類型: Unit
# 自動化工具: unittest + 文字掃描與 PowerShell 語法解析（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_436_4_3_ -q -p no:xdist -o addopts=

Feature: si_patrol_tick.ps1
Scenario: 金鑰讀取面、行尾、語意
  Given `tools/si_patrol_tick.ps1` 的位元組
  When 掃描與（有引擎時）以 `[System.Management.Automation.Language.Parser]::ParseFile` 解析
  Then 行尾全為 CRLF；解析零錯誤；不含 PS 6+ 專屬變數（`$IsWindows` 等）；只提及 `CONSOLE_SI_AUDIT_KEY` 與 `AUTOSDD_SI_AUDIT_KEY` 兩個金鑰名；取金鑰用逐行比對而非 `source`、`. <檔>`、`Invoke-Expression`、`iex`、`Get-Content` 整檔後 `Invoke-`；以第一個命中為準（有 `break` 或等價）；無 `Write-Output`／`Write-Host`／`Out-File`／`Add-Content`／`Tee-Object` 作用於金鑰值的變數；呼叫 `.venv\Scripts\python.exe` 與 `tools\selfimproving.py` 與 `patrol`；含日誌輪替字樣；對一個含兩把金鑰的假 `.env` 以替身執行（有引擎時）：行程環境只得第一把
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_4_3]"
```
```gherkin
# AT-436-4-E-1
# 對應 AC: AC-SI-36-4（R161 (d)）憑證是值；兩平台載具內容
# 測試類型: Integration
# 自動化工具: pytest + 替身 runner.run_argv + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_436_4_E_1_ -q -p no:xdist -o addopts=

Feature: sched arm
Scenario: 無憑證不得宣稱已排程
  Given `runner.run_argv` 替身：(甲)回傳 NextRunTime 非空、(乙)任務建立成功但 NextRunTime 為空字串、(丙)elevation 不足的失敗輸出；平台以替身 `sys.platform` 分別為 Windows 與 macOS
  When 各呼叫 `sched arm`
  Then (甲)rc `0`、輸出含該 NextRunTime 值；(乙)rc `1`、碼 `SCHED-NO-CREDENTIAL`、輸出不含「已排程」「armed」字樣；(丙)rc `1`、碼 `SCHED-ELEVATION-REQUIRED`、輸出含可貼用的指令；Windows 的 argv 為 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <installer>` 的形；macOS 路徑寫出的 plist（`plistlib` 回讀）`Label` 為 `AutoSDD_SI_Patrol`、`StartInterval` 等於心跳分鐘×60、`RunAtLoad` 為 `false`、含 `StandardOutPath`，且 `launchctl` argv 位於平台守衛內
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_4_E_1]"
```
```gherkin
# AT-436-4-E-2
# 對應 AC: AC-SI-36-4（R161 (e)）OS 任務與啟用旗標相互獨立
# 測試類型: Integration
# 自動化工具: pytest + 替身 runner.run_argv + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_436_4_E_2_ -q -p no:xdist -o addopts=

Feature: 兩個獨立的旋鈕
Scenario: 互不呼叫、互不寫事件
  Given `R4` 啟用；`runner.run_argv` 替身記錄呼叫
  When 呼叫 `sched set --enabled false`；呼叫 `sched arm` 與 `sched disarm`；各自前後取 `schedule` 與事件帳本
  Then `sched set` 期間替身呼叫次數為 `0`；`arm`／`disarm` 前後事件帳本位元組逐位元相同；`SCH` 的 `overdue` 在 OS 任務存在與不存在兩種替身下，以相同事件與 `now` 算出的值相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_4_E_2]"
```
```gherkin
# AT-436-5-2
# 對應 AC: AC-SI-36-5（R161 (d)）disarm 須驗證任務真的不見
# 測試類型: Integration
# 自動化工具: pytest + 替身 runner.run_argv（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_436_5_2_ -q -p no:xdist -o addopts=

Feature: sched disarm
Scenario: 移除後驗證
  Given 替身：移除指令回 rc 0 後，(甲)現查回「任務不存在」（Windows 查無、macOS `launchctl` rc 113）、(乙)現查仍回任務存在
  When `sched disarm`
  Then (甲)rc `0`；(乙)rc `1`、輸出指出任務仍在；兩者皆未寫任何事件；只移除 `AutoSDD_SI_Patrol` 一支（替身記錄的 argv 不含 `AutoClaude_Nightly`、`AutoClaude_WindowsSmoke`，且不是安裝器的 `-Uninstall`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_436_5_2]"
```
```gherkin
# AT-437-5-1
# 對應 AC: AC-SI-37-5（R158）console_pending 的兩新 kind
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_437_5_1_ -q -p no:xdist -o addopts=

Feature: 待入帳
Scenario: sched-set 與 run-request 出現又消失
  Given 家目錄 `console_audit/` 內兩份合法稽核檔（`kind` 為 `sched-set`、`run-request`）
  When `status --json`；入帳兩者；再取 `status --json`
  Then 入帳前 `console_pending` 含兩筆 `{"audit_ref","kind"}`，`kind` 值為 `sched-set` 與 `run-request`；入帳後（事件帳本有帶該 `audit_ref` 的 `sched.set`、`run.open` 或 `sched.skip`）兩筆消失；`export --kind status` 的 `console_pending` 仍為 `export-reads-no-home` 的 NE 形（沿 P2 R99）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_5_1]"
```
```gherkin
# AT-437-5-2
# 對應 AC: AC-SI-37-5（R140）check 35 項與判準版本
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_437_5_2_ -q -p no:xdist -o addopts=

Feature: 兩個新 check 項
Scenario: id、順序、版本、合法帳本
  Given S-CHECK-OK：啟用、一筆 `run.open(f)`（`by` 為 `patrol`、`due_at` 為格起點）、一筆 `blackout` skip、一筆 Console 載體 skip
  When `check --json`；讀 `CHECK_RULES_REV`
  Then `items` 共 35 個，前 33 個 id 與順序與 P3 相同，第 34、35 個 id 為 `sched.events`、`run.trigger_f_has_patrol_by`；兩項皆 `PASS`；`CHECK_RULES_REV` 為 `5`；整體 rc 為 `0`；對真 repo `check` rc 為 `0`（35 項）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_5_2]"
```
```gherkin
# AT-437-5-E-1
# 對應 AC: AC-SI-37-5（R140）sched.events 四碼
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 手寫事件（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_437_5_E_1_ -q -p no:xdist -o addopts=

Feature: sched.events 負控
Scenario: 每個違規恰一個碼
  Given 以合法帳本為對照組（四碼皆無）；逐一手寫違規：`sched.set` 的 `period_minutes` 為 `59`；同一格兩筆 `run.open(f)`；同一格兩筆同 `reason` 的非 Console `sched.skip`；`sched.skip` 的 `due_at` 為格起點＋1 分；同一 `audit_ref` 兩筆 Console `sched.skip`
  When 各跑 `check --json`
  Then 依序 `sched.events` 的 FAIL 碼恰為 `SCHED-PERIOD-RANGE`、`SCHED-RUN-DUP`、`SCHED-SKIP-DUP`、`SCHED-SKIP-DUE`、`SCHED-SKIP-DUP`；每次 `events.structure` 仍為 `PASS`；對照組 `PASS`；兩筆同格同 `reason` 但 `audit_ref` 不同的 Console skip 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_5_E_1]"
```
```gherkin
# AT-437-5-E-2
# 對應 AC: AC-SI-37-5（R140）run.trigger_f_has_patrol_by 三碼與 origin 取法
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 手寫事件（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_437_5_E_2_ -q -p no:xdist -o addopts=

Feature: trigger f 的守衛
Scenario: by、due_at、origin
  Given 對照組：啟用於 `O`、`run.open(f)` 的 `due_at` 為 `O`（k 為 0）與 `O＋1 天`（k 為 1），`by` 皆 `patrol`；違規：(甲)`by` 為 `main`；(乙)缺 `due_at`；(丙)`due_at` 為 `O＋1 天＋1 分`；(丁)`run.open(f)` 之前無任何 `sched.set(enabled=true)`；(戊)週期改為 720 後的 `run.open(f)` 其 `due_at` 為舊週期的格起點而非新 origin 的整數倍
  When 各跑 `check --json`
  Then 對照組 `PASS`（含 k 為 0 的邊界）；違規依序為 `TRIGGER-F-BY`、`TRIGGER-F-DUE-AT`、`TRIGGER-F-DUE-AT`、`TRIGGER-F-NO-ORIGIN`、`TRIGGER-F-DUE-AT`；origin 取該 `run.open` 之前最近一次重置事件（R142 (b)）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_5_E_2]"
```
```gherkin
# AT-437-5-E-3
# 對應 AC: AC-SI-37-5（R140）載體缺席與空集合
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_437_5_E_3_ -q -p no:xdist -o addopts=

Feature: NE 與 PASS
Scenario: 事件帳本不在場與無 sched 事件
  Given 一個事件帳本不存在的 repo；一個只有 P0～P3 事件的 repo
  When `check --json`
  Then 前者兩項皆為 nonblocking NE、碼 `CARRIER-NOT-ESTABLISHED`、整體 rc 與 P3 時相同；後者兩項皆 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_437_5_E_3]"
```
```gherkin
# AT-438-7-1
# 對應 AC: AC-SI-38-7（R154）巡邏相關原始碼的動詞呼叫集合
# 測試類型: Unit
# 自動化工具: unittest + AST 掃描（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_438_7_1_ -q -p no:xdist -o addopts=

Feature: 權限列的靜態面
Scenario: 能做 ⊆ 可做集合
  Given `patrol.py`、`patrolrun.py`、`patrolbrief.py`、`schedarm.py`、`sched.py`、`schedwrite.py` 的原始碼；`patrol_verb_calls(src)` 自 AST 抽出對 CLI 動詞字面與 git 子命令字面的呼叫集合
  When 掃描真檔並對注入副本（加入 `git push`、`--no-verify`、`git add -A`、`decide` 加 `--sid`、`rm -rf`、`decide --carrier transcript` 字樣各一）掃描
  Then 真檔的動詞集合 ⊆ {`research`、`scan`、`run-open`、`run-close`、`sandbox`、`verify`、`promote`、`rollback`、`measure`、`card`、`sched set`、`decide --carrier console`（僅入帳）、`obs-add`、`obs-close`、`status`、`check`}；git 子命令 ⊆ {`status`、`add`、`commit`、`rev-parse`、`diff`、`log`、`show`}；無 `push`、`--no-verify`、`add -A`、`add .`、逐字稿載體的 `decide`；各注入副本被判出對應問題碼
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_438_7_1]"
```
```gherkin
# AT-440-1-1
# 對應 AC: AC-P4-040-1（R139）事件詞彙與欄位表正控
# 測試類型: Unit
# 自動化工具: unittest（events.validate）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_1_1_ -q -p no:xdist -o addopts=

Feature: sched.* 欄位表
Scenario: 詞彙 23 與合法事件
  Given `events.KINDS` 與一組合法事件：`sched.set` 的三種載體（console、transcript、host）、`sched.skip`（含與不含 Console 選填鍵）、`run.open` 的 trigger f 與 Console 的 a
  When `events.validate` 逐一驗；讀 `len(KINDS)`；檢查 `fold` 對兩種新 kind 的處理
  Then 皆無問題；`len(KINDS)` 為 `23` 且含 `sched.set`、`sched.skip`；兩種新 kind 加入任一事件序列後 `fold` 的 PROP 與 RUN 結果不變（不入折疊）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_1_1]"
```
```gherkin
# AT-440-1-E-1
# 對應 AC: AC-P4-040-1（R139）欄位表負控
# 測試類型: Unit
# 自動化工具: unittest（events.validate）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_1_E_1_ -q -p no:xdist -o addopts=

Feature: sched.* 負控
Scenario: 一次只壞一處
  Given 對照組合法事件；變形：缺 `enabled`、缺 `carrier`、`enabled` 為字串、`period_minutes` 為布林、`carrier` 為 `console` 而缺 `audit_ref`、`carrier` 為 `host` 而 `enabled` 為真、`carrier` 為 `transcript` 而帶 `audit_ref`、`sched.skip` 的 `reason` 為第八值、`detail` 121 code point、`due_at` 缺 offset、只帶 `audit_ref` 而無 `carrier`、`run.open` 的 trigger 為 `f` 而缺 `due_at`、trigger 為 `a` 而帶 `due_at`、`carrier` 為 `console` 的 `run.open` 缺 `decider`
  When 各 `events.validate`
  Then 每個變形恰得一個碼（`EVENT-KEY-MISSING`、`EVENT-KEY-UNKNOWN` 或 `EVENT-TYPE` 依性質）；對照組為空；表外鍵永遠是 `EVENT-KEY-UNKNOWN`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_1_E_1]"
```
```gherkin
# AT-440-1-E-2
# 對應 AC: AC-P4-040-1（R139）舊事件不變與詞彙訊息
# 測試類型: Unit
# 自動化工具: unittest（events.validate）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_1_E_2_ -q -p no:xdist -o addopts=

Feature: 向後相容
Scenario: P4 之前的 run.open 照過
  Given 一個不帶任何 P4 選填鍵的舊式 `run.open`（trigger `a`～`e`）；trigger 為 `g` 的事件；kind 為 `sched.bogus` 的事件
  When `events.validate`
  Then 舊式事件無問題；trigger `g` 得 `EVENT-TYPE`；未知 kind 得 `EVENT-KIND` 且訊息含 `23 個詞彙`；真 repo 的整份事件帳本 `check` 的 `events.structure` 仍 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_1_E_2]"
```
```gherkin
# AT-440-2-1
# 對應 AC: AC-P4-040-2（R159）41 鍵與九鍵預設值
# 測試類型: Unit
# 自動化工具: unittest（params）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_2_1_ -q -p no:xdist -o addopts=

Feature: 參數九鍵
Scenario: 鍵集合與預設值
  Given 真 `params.json` 與 `params.PARAM_SPECS`
  When 比對
  Then 兩者鍵集合相等且共 41 個；頂層鍵依位元組序；九鍵值為 `sched_heartbeat_minutes` 15、`sched_period_minutes_default` 1440、`sched_period_minutes_min` 60、`sched_period_minutes_max` 10080、`sched_run_budget_minutes` 90、`sched_blackout_local` 為 `["21:00-01:30"]`、`sched_driver_quiet_minutes` 30、`sched_auto_commit` 為 `true`、`sched_auto_push` 為 `false`；`param_findings(真值)` 為空；對真 repo `check` 的 `params.keys` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_2_1]"
```
```gherkin
# AT-440-2-E-1
# 對應 AC: AC-P4-040-2（R159；兼 AC-SI-36-6 預算方向）型別、界與跨鍵關係
# 測試類型: Unit
# 自動化工具: unittest（param_findings）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_2_E_1_ -q -p no:xdist -o addopts=

Feature: 參數負控
Scenario: 一次改一處
  Given 對照組為真值；變形：缺各鍵（九次）、`sched_auto_commit` 為整數 `1`、`sched_heartbeat_minutes` 為布林、`sched_blackout_local` 含 `"21:00-21:00"`、含 `"9:00-10:00"`、含非字串、`sched_auto_push` 為 `true`、`min>default`、`default>max`、`heartbeat>min`（`sched_heartbeat_minutes` 為 61）、`sched_run_budget_minutes` 為 `RESUME_BG_WAIT_CEILING_SECONDS／60＋1`；另以恰等於上限者為對照
  When `param_findings`
  Then 缺鍵為 `PARAM-MISSING`；型別錯為 `PARAM-TYPE`；其餘為 `PARAM-RANGE` 並點名鍵；預算恰等於上限者無問題、多 1 者 `PARAM-RANGE`；空的 `sched_blackout_local` 列表無問題；`sched_auto_push` 為 `false` 以外一律 `PARAM-RANGE`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_2_E_1]"
```
```gherkin
# AT-440-2-E-2
# 對應 AC: AC-P4-040-2（R159 (blackout 涵蓋)、D10）黑窗涵蓋、指紋與基線文件
# 測試類型: Unit
# 自動化工具: unittest（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_2_E_2_ -q -p no:xdist -o addopts=

Feature: 連動
Scenario: 黑窗涵蓋每個期望觸發時刻；指紋與基線三列
  Given `check_scheduled_task_drift.load_trigger_expectations` 回傳的每個 `HH:mm`；`params.json` 的黑窗；`params.fingerprint`；`SelfImproving_LedgerDb_P0_Baseline.md`
  When 對每個觸發時刻以 `sched.blackout_hit` 判；把黑窗改成不涵蓋 21:30 的副本重判；把九鍵之一改值後重算指紋；比對基線文件三列
  Then 每個期望觸發時刻（現為 21:30 與 22:30）皆在黑窗內，且各觸發時刻加 80 分鐘（十倍常態歷時的下限）仍在黑窗內；副本判出未涵蓋；改任一 `sched_*` 值使指紋改變、`metrics.md` 與 `metrics_rev` 不改；基線文件的 `params.json` 雜湊與位元組數、指紋、`CHECK_RULES_REV` 三列與活值相等（沿既有鎖 `test_AT_LD_02_6_1`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_2_E_2]"
```
```gherkin
# AT-440-3-1
# 對應 AC: AC-P4-040-3（R160）能力登記與閉包
# 測試類型: Unit
# 自動化工具: unittest + AST（沿 test_selfimproving_capability.py 的判準函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_3_1_ -q -p no:xdist -o addopts=

Feature: 59 鍵登記
Scenario: 計數、類別、閉包、runner 匯入者
  Given `test_selfimproving_capability.py` 的 `CAPABILITY` 與 `capability_problems`（匯入、不複製）；真套件目錄
  When 對真樹執行
  Then `capability_problems` 為空；鍵數屬 {59、60}（60 者須含 `evspec.py` 且為 `ro`，計數為 44／9／2／5；否則 43／9／2／5）；登記鍵集合等於實際檔案集合；`sched`、`unattended`、`patrolbrief`、`schedcheck` 為 `ro`、`schedwrite` 為 `rw`、`patrol`、`patrolrun`、`schedarm` 為 `exec`；`exec` 類恰為 `runner`、`verify`、`patrol`、`patrolrun`、`schedarm`；相對 import `runner` 的檔恰為 `verify.py`、`patrol.py`、`patrolrun.py`、`schedarm.py`；`check`、`status`、`scan`、`export`、`card` 的 import 閉包不含 `schedwrite`、`patrol*`、`schedarm`、`runner`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_3_1]"
```
```gherkin
# AT-440-3-2
# 對應 AC: AC-P4-040-3（R160、R148、NFR-P4-2、NFR-P4-5）run_argv 與禁字樣
# 測試類型: Unit
# 自動化工具: unittest + AST（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_3_2_ -q -p no:xdist -o addopts=

Feature: runner.run_argv
Scenario: 靜態不變量
  Given `runner.py` 與全套件原始碼
  When 掃描
  Then 出現 `subprocess` 字樣的檔恰為 `git.py`、`runner.py`；`run_argv` 的 `Popen` 或 `run` 呼叫 `shell` 為 `False`（或缺省）、`communicate` 帶 `timeout`；`run_argv` 函式本體不含 `os.environ`；`run_probe` 的環境白名單與 `_ENV_KEYS` 不變；`forbidden_hits` 對全部新檔為空（經 `FORBIDDEN_EXEMPT` 豁免後：`schedarm.py` 的 `schtasks`、`launchctl`、`Register-ScheduledTask` 不算命中，其餘 `FORBIDDEN` 條目照判，含 `time.sleep`、`while True`、`os.fork`、`signal.alarm`）；`run_argv` 與 `spawn_detached` 兩函式本體皆不含 `os.environ`、`shell` 皆為 False；`schedarm.py` 內 `launchctl` 與 `powershell.exe` 的 argv 字面位於平台守衛作用域內，`test_platform_neutral_paths.py` 的 `TestForeignExecutableArgvIsGuarded`、`TestForeignPlatformApiIsGuarded`、`TestForeignApiVocabularyOnlyGrows` 仍綠，兩張債表無 selfimproving 條目
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_3_2]"
```
```gherkin
# AT-440-3-E-1
# 對應 AC: AC-P4-040-3（R160）注入副本自證
# 測試類型: Unit
# 自動化工具: unittest（合成套件副本）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_3_E_1_ -q -p no:xdist -o addopts=

Feature: 判準有牙
Scenario: 四個注入各被抓到、對照組綠
  Given 真套件的副本；對照組不改；注入：(甲)新增未登記檔；(乙)`sched.py` 加 `from . import runner`；(丙)登記表把 `patrol.py` 標為 `ro`；(丁)`runner.run_argv` 加讀 `os.environ`；(戊)`sched.py` 加 `launchctl` 字面（`schedarm.py` 以外仍被抓）；(己)`schedarm.py` 加 `time.sleep`（豁免表不豁免核心禁字樣）
  When 各跑 `capability_problems` 與 AT-440-3-2 的靜態掃描函式
  Then 對照組為空；(甲)含「未登記」；(乙)含 `②′` 或「import 閉包」；(丙)含 `②′`；(丁)被靜態掃描判出 `os.environ`；(戊)(己)各被 `capability_problems` 判出（戊含 `launchctl`、己含 `time.sleep`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_3_E_1]"
```
```gherkin
# AT-440-3-3
# 對應 AC: AC-P4-040-3（R161 (d)；D-QA-1）schedarm 的平台專屬 argv 住在 sys.platform 守衛內
# 測試類型: Unit
# 自動化工具: unittest + AST（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_3_3_ -q -p no:xdist -o addopts=

Feature: 平台守衛
Scenario: powershell.exe、schtasks、launchctl 字面只出現在守衛分支
  Given `schedarm.py` 原始碼與 `test_platform_neutral_paths.py` 的 `TestForeignExecutableArgvIsGuarded` 判準（五種罩法）；注入副本：把 `launchctl` argv 搬到無守衛的模組層、把 `powershell.exe` argv 搬到 `if sys.platform` 以外的分支
  When 對真檔與注入副本各以 AST 判定每個單平台 argv 字面的所在作用域，並執行 `TestForeignExecutableArgvIsGuarded`
  Then 真檔每個 `powershell.exe`、`schtasks`、`launchctl` 字面都位於 `sys.platform`（或等價守衛函式）分支內；`TestForeignExecutableArgvIsGuarded` 仍綠且 `_FOREIGN_EXE_ARGV_DEBT` 沒有 selfimproving 條目；兩個注入副本各被判出
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_3_3]"
``````gherkin
# AT-440-4-1
# 對應 AC: AC-P4-040-4（R162）SOP 條文必含項
# 測試類型: Unit
# 自動化工具: unittest + 文字判準（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_4_1_ -q -p no:xdist -o addopts=

Feature: SOP P4 條文
Scenario: 真檔通過
  Given 真 SOP 與測試自有的 `sop_p4_problems(text)`
  When 判
  Then 回空清單；〈巡邏與無人運轉（P4）〉含四個子節標題〈安裝與憑證〉〈每心跳做什麼〉〈停用與逃生口〉〈日誌與逾期處置〉；〈每心跳做什麼〉含「入帳」「到期判定」「運轉」「推進」與七種跳過字面；〈無人運轉任務書範本〉圍欄含 R152 的全部大寫占位符與 `resume_route.HANDBACK_MARKERS` 四個標題；〈啟動條件〉含 `日曆格` 與第六類；〈P2 動詞〉序列條文含 `run-scoped` 或 `AUTOSDD_SI_PATROL_RUN` 且不含「無人值守：有設時寫入動詞一律 rc 1」；〈擷取者〉〈歸因者〉〈提案者〉〈研究者〉四節不含 P3 的禁出現片段
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_4_1]"
```
```gherkin
# AT-440-4-E-1
# 對應 AC: AC-P4-040-4（R162）刪去與注入自證
# 測試類型: Unit
# 自動化工具: unittest（合成 SOP 副本）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_4_E_1_ -q -p no:xdist -o addopts=

Feature: 判準有牙
Scenario: 逐項刪去、移入圍欄、注入過度概括句
  Given 真 SOP 副本
  When 依序：逐一刪去 R162 列的每個必含字面；把〈停用與逃生口〉的 `sched disarm` 行包進程式碼圍欄；在〈P2 動詞〉序列條文加回「無人值守：有設時寫入動詞一律 rc 1」；在〈提案者〉節加入 `params.json`；把〈無人運轉任務書範本〉圍欄的 `<RUN>` 換成 `<run>`
  Then 每個副本 `sop_p4_problems` 皆非空且各含對應項的碼；未動的真檔為空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_4_E_1]"
```
```gherkin
# AT-440-5-1
# 對應 AC: AC-P4-040-5（R163）零退化：舊情境表在新夾具上重放
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_5_1_ -q -p no:xdist -o addopts=

Feature: 夾具升級不改舊行為
Scenario: P1、P2、P3 的情境表在 make_p4_repo 上重放
  Given `make_p4_repo` 包裝 `make_p3_repo`；P1 的 `sc_close`、`sc_seq`、`sc_legal`、`sc_rev`、`sc_susp`、P2 的 `sc_p2_legal`、P3 的 S-BASE、S-ADOPT、S-SUSP 情境
  When 於升級後的夾具上重放，並以 `events.structure`、`fold` 取結果
  Then `events.structure` 為 `PASS`；`fold` 狀態與 problems 與預期相同；`params.json` 為 41 鍵；P0～P3 夾具的呼叫形態未被改（以夾具簽章比對）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_5_1]"
```
```gherkin
# AT-440-5-E-1
# 對應 AC: AC-P4-040-5（R163）同步站點逐項為新值、站點外不動
# 測試類型: Unit
# 自動化工具: unittest + AST（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_5_E_1_ -q -p no:xdist -o addopts=

Feature: 同步表
Scenario: 每個站點的斷言值正確、其餘函式不變
  Given §2.5 同步表；對每個站點自測試檔 AST 取其斷言常數
  When 逐站點比對
  Then 每站點的值等於新值（動詞數 26、`check` 35 項、`params` 41 鍵、`status` 16 鍵、能力登記 59 或 60 鍵與計數、`CHECK_RULES_REV` 為 5、`KINDS` 23、安裝器任務 3 支）；被修改的既有 SI 測試檔集合 ⊆ §2.5 允許檔集合（檔級；函式級對帳由實作輪交卷的站點清單與 §2.5 表人讀核對——D-IMP-6 (10)）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_5_E_1]"
```
```gherkin
# AT-440-6-1
# 對應 AC: AC-P4-040-6（R164）AT 錨定可重跑
# 測試類型: Unit
# 自動化工具: unittest（匯入 test_selfimproving_p2_meta 的檢查函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_6_1_ -q -p no:xdist -o addopts=

Feature: 錨定
Scenario: 每個 AT 恰一個測試函式
  Given 本檔文字（以 `real_tcs("P4")` 取，glob 恰命中一檔）；`parse_at_headers`、`anchor_problems`、`collect_nodes`（匯入）
  When 解析 §2 全部 AT 標頭並於四個新測試檔收集節點
  Then 解析出 105 個 AT；`anchor_problems` 為空；每個 AT 的 `-k` 為錨定名、恰收一個節點；四個檔各不超過 35 個 AT；AT 清單的 ID 集合等於 §1 映射表的 ID 集合
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_6_1]"
```
```gherkin
# AT-440-6-E-1
# 對應 AC: AC-P4-040-6（R164）錨定檢查有牙
# 測試類型: Unit
# 自動化工具: unittest（合成清單）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_6_E_1_ -q -p no:xdist -o addopts=

Feature: 檢查函式的負控
Scenario: 注入各被判出
  Given 合成的 AT 清單與收集結果
  When 注入：`-k` 無結尾底線、`-k` 去底線後不等於 AT 底線形、零命中、兩個函式同前綴（多命中）
  Then `anchor_problems` 分別判出「非錨定」「不等於 AT 底線形」「零命中」「命中 2 個」；對照組為空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_6_E_1]"
```
```gherkin
# AT-440-7-1
# 對應 AC: AC-P4-040-7（R137）入口與 rc 契約
# 測試類型: Integration
# 自動化工具: pytest + 真入口子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_7_1_ -q -p no:xdist -o addopts=

Feature: 入口
Scenario: 26 個動詞與新旗標
  Given 真入口 `tools/selfimproving.py`
  When 呼叫頂層 usage、`sched --help`、`patrol --help`、`run-open --help`、`sched show --json`、`sched show`
  Then usage 列出 26 個動詞（含 `sched`、`patrol`），`_HELP` 為 26 鍵；`sched` 有 `show`／`set`／`arm`／`disarm` 四個子命令；`patrol` 有 `--now`、`--dry-run`、`--json`、`--repo` 且無 `--run`；`run-open` 的 `--trigger` 選項為 `a`～`f` 且有 `--due-at`、`--carrier`、`--audit-ref`；`sched show --json` 為 R158 的 `schedule` 物件、rc `0`；文字首行以 `schedule: enabled=` 起頭；入口斷言行 ≤750
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_7_1]"
```
```gherkin
# AT-440-7-E-1
# 對應 AC: AC-P4-040-7（R137）用法錯誤
# 測試類型: Integration
# 自動化工具: pytest + 真入口子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_7_E_1_ -q -p no:xdist -o addopts=

Feature: rc 3
Scenario: 先於一切
  Given 真入口
  When 呼叫 `sched`（無子命令）、`sched set`（缺 `--enabled`）、`sched set --enabled maybe`、`sched show --now 2026-11-02T08:00:00`（無 offset）、`run-open --trigger g …`、`patrol --run X`、`sched bogus`、未知動詞 `schedule`
  Then 全部 rc 為 `3`、stdout 空、stderr 至少一行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_7_E_1]"
```
```gherkin
# AT-440-8-1
# 對應 AC: AC-P4-040-8（R164、NFR-P4-8）範圍守衛
# 測試類型: Unit
# 自動化工具: unittest + git（hermetic；於 SCG-4 的實作樹上跑）
# 判定指令: python -m pytest tools/tests/test_selfimproving_schedule_gate.py -k AT_440_8_1_ -q -p no:xdist -o addopts=

Feature: 變更面
Scenario: 只動允許集合
  Given 實作輪起點的基準 commit（以環境變數 `SI_P4_BASE_SHA` 提供；未設時以 `HEAD` 的父 commit 為界並於輸出註明；父 commit 不可得〔淺層 clone〕＝只看未追蹤檔並註明；D-IMP-5）
  When `git diff --name-only <基準>` 與 `git ls-files --others --exclude-standard`
  Then 差異**觸及 §5.7 允許集合**時：每個路徑 ⊆ §5.7 的允許集合；`.claude/**`、`tools/lib/schedule_backend.py`、`tools/lib/resume_route.py`、`tools/lib/unattended_authz.py`、`tools/lib/model_roles.py`、`tools/check_scheduled_task_drift.py`、PRD、SOP、P0～P3 TCS、`AgentConsole/**`、`.github/**` 的差異為空（本檔的主控勘誤追加不計）；差異未觸及允許集合＝輸出「範圍守衛未觸發」並通過（常駐於 CI 不得把無關 commit 判紅）；本檔四個新測試檔與夾具不含 `skip`、`skipTest`、`xfail` 字樣（恆查）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_440_8_1]"
```

### 2.5 既有測試的同步站點（R163；檔、函式名；行號僅供參考）

| 站點 | 既有檔與函式 | 變更 |
|------|--------------|------|
| 動詞數 24→26 | `test_selfimproving_issues.py` 的動詞數斷言（現約 1830 行）；`test_selfimproving_p3_meta.py` 的 `len(selfimproving._HELP)`（現約 293 行）；`test_selfimproving_console_obs.py::test_AT_235_3_1_no_delete_or_renumber`（現約 921 行） | 24 改 26 |
| `check` 33→35 項 | `test_selfimproving_events.py`：`test_AT_001_1_1_baseline_is_green` 相關的 `items=33` 字面（約 1490）與 `len(res["items"])` 的兩處（約 1907、2273）；`test_selfimproving_measure_verb.py`（約 80）；`test_selfimproving_capability.py::test_AT_143_1_E_2_dynamic_purity_and_forbidden_words`（約 624）；`test_selfimproving_events_p2.py::test_AT_240_3_1_check_has_32_items` | 33 改 35 |
| `CHECK_RULES_REV` 4→5 | `test_selfimproving_p3_meta.py`（約 292）；`SelfImproving_LedgerDb_P0_Baseline.md` 的 `CHECK_RULES_REV` 列（`test_selfimproving_ledgerdb_p0.py::test_AT_LD_02_6_1_baseline_rows_equal_live_values` 判） | 4 改 5；基線文件同 commit |
| `params` 32→41 鍵 | `test_selfimproving_events_p2.py` 的 `params` 鍵數斷言；`_selfimproving_fixtures.py` 的 `params_dict`；`test_selfimproving_check.py` 本地 `params_dict`；`_selfimproving_p2_fixtures.py::make_p2_repo` 的 `params.json`；`test_selfimproving_p2_meta.py` 的 `PARAM_SPECS` 鍵集合斷言；`SelfImproving_LedgerDb_P0_Baseline.md` 的 `params.json` 雜湊與位元組數與指紋兩列 | 加九鍵（預設值見 R159） |
| `status` 15→16 鍵 | `test_selfimproving_export_status.py` 的 `STATUS_KEYS`；`test_selfimproving_events.py` 的 `WEIRD_STATUS_KEYS` 與 `test_AT_140_1_E_2_verbs_survive_weird_events`；`test_selfimproving_console_obs.py::test_AT_240_12_1_buckets_and_pending` 的末鍵斷言；`test_selfimproving_export_status.py::test_AT_132_5_E_2_differential_and_isolation` 的 `same()` 排除集合 | 末鍵 `measure` 之後加 `schedule`；差分排除集合加 `schedule.armed` 的 export 固定值 |
| `KINDS` 21→23 | `test_selfimproving_events.py` 內「不在 21 個詞彙內」訊息的斷言；任何斷言 `len(events.KINDS)` 為 21 的站點（現查） | 21 改 23 |
| 能力登記 51→59（或 60） | `test_selfimproving_capability.py` 的 `CAPABILITY` 表、檔頭計數註解、`test_AT_143_1_1_real_tree_matches_registry`（計數 39／8／2／2→43／9／2／5）、`test_AT_240_5_1_exec_registry`（鍵數 51→59；`exec` 集合 `runner`、`verify`→加 `patrol`、`patrolrun`、`schedarm`；「`runner` 匯入者恰 `verify.py`」→四個檔）、`test_AT_340_4_2_p3_registry_closure_and_load_surface`（現約 650 行的鍵數與計數） | 依 R160 兩態 |
| 安裝器三層鎖 | `test_install_windows_nightly.py`：`TestScheduledTaskExpectationsSsot::test_ssot_covers_exactly_the_tasks_the_installer_registers`（任務名解析 regex 須認得第三支）、`::test_every_expected_value_is_actually_applied_by_the_installer`（改逐任務逐值）、`::test_execution_time_limit_expectation_matches_installer_hours`（改逐任務）、`TestUnattendedExecutionHardening` 的 `test_principal_is_s4u_and_applied_to_both_tasks`（`Register-ScheduledTask` 兩處→三處）、`test_stop_existing_applied_via_com_because_module_enum_cannot_express_it`（呼叫名單仍為 nightly、smoke，不含 patrol）、`test_execution_time_limit_is_bounded`（取值改逐任務並維持 ≤8）、`test_status_surfaces_the_three_regression_prone_fields`、`TestStatusExitCodeRuntime`／`test_whatif_previews_every_task_without_touching_scheduler`（預覽三支） | 見 R161 (b)；期望表 `why_each` 補逐任務說明 |
| SOP 相關 | `test_selfimproving_events.py::TestSopArticles`、`test_selfimproving_p3_meta.py` 的 `sop_p3_problems` 相關、`test_selfimproving_p2_meta.py` 的 `sop_p2_problems` 相關：以標題切段者須對 SOP 新增的兩個 `##` 節（位於檔尾）仍成立 | 預期零改；若紅以 ⚖ 回報 |
| Console 稽核 `kind` | `test_selfimproving_console_obs.py` 內斷言 `consoleaudit.KINDS` 為三值或列舉 `kind` 的站點（現查） | 3 改 5 |
| Console `decide` 無人值守（D-IMP-4 追認） | `test_selfimproving_console_obs.py::test_AT_233_1_E_2` 子案 (e) | `UNATTENDED-REFUSED` 改 `AUDIT-KEY-MISSING`（R153 ②／D-QA-9：過授權閘、止於金鑰缺） |
| 常駐機制禁字樣豁免（D-IMP-6 追認） | `test_selfimproving_check.py::test_AT_003_1_1_no_resident_mechanism` | 加 `schedarm.py` 對 `schtasks`／`launchctl`／`Register-ScheduledTask` 三字樣的豁免（與 R160 `FORBIDDEN_EXEMPT` 同源） |
| 安裝器任務名與漂移檢查器（D-IMP-6 追認） | `test_install_windows_nightly.py::_declared_task_names`（regex 加 Patrol）；同檔 `test_all_settings_matching_is_ok`、`test_missing_execution_time_limit_is_drift_not_ok`、`test_interactive_logon_type_is_drift`（改用 `_parsed_per_task()` 逐任務解析） | 三支任務逐任務逐值 |
| 議題中心事件標籤（D-IMP-3） | `tools/lib/selfimproving/issuemap.py::EVENT_LABELS`（`test_selfimproving_issuemap.py` 的 AT-IC-01-1-1／01-1-E-1／01-1-E-2 閉包對帳）；`test_selfimproving_issuemap.py::test_AT_IC_01_7_2_channel_event_and_decision_dictionaries` 的 `len(EVENT_LABELS)` | 加 `sched.set`＝排程設定、`sched.skip`＝排程跳過；計數 21 改 23（TCS-IssueCenter 勘誤同步） |
| 能力登記禁字樣（D-QA-1） | `test_selfimproving_capability.py`：`FORBIDDEN`（現約 91～106 行，內容**不動**）旁新增常數 `FORBIDDEN_EXEMPT = {"schedarm.py": ("schtasks", "launchctl", "Register-ScheduledTask")}`，`capability_problems` 對每檔的 `forbidden_hits` 先扣除該檔豁免項；`FORBIDDEN_SAMPLES`（現約 108 行起）與負控加「同字樣出現在 `schedarm.py` 以外仍紅」「`schedarm.py` 內 `time.sleep` 仍紅」兩例 | 加豁免表與兩個負控；既有 14 條禁字樣與其樣本逐位不變 |
| 單平台外部執行檔 argv 守衛（D-QA-1） | `test_platform_neutral_paths.py::TestForeignExecutableArgvIsGuarded`（及 `TestForeignPlatformApiIsGuarded`、`TestForeignApiVocabularyOnlyGrows`）：`schedarm.py` 的 `powershell.exe`、`schtasks`、`launchctl` 字面須住在 `sys.platform` 守衛內，`_FOREIGN_EXE_ARGV_DEBT`、`_FOREIGN_API_SCOPE_DEBT` 不新增 selfimproving 條目 | 預期零改（以 AT-440-3-3 與 `test_selfimproving_capability.py::test_AT_240_5_E_2_runner_static_invariants` 守）；若該測試因新檔而紅，以 ⚖ 回報 |
| `runner` 靜態不變量 | `test_selfimproving_capability.py::test_AT_240_5_1_exec_registry`、`test_AT_240_5_E_2_runner_static_invariants`：`runner.py` 新增 `run_argv` 與 `spawn_detached` 後，`Popen` 的 `shell` 與 `communicate` 的 timeout 斷言涵蓋新函式（`spawn_detached` 不等待、不呼叫 `communicate`，以其為豁免並釘「不等待」）、`CREATE_BREAKAWAY_FROM_JOB`、`CREATE_NEW_PROCESS_GROUP`、`DETACHED_PROCESS` 的 `getattr` 兜底字面 | 預期值增列 |
| 護欄層與棘輪 | `tools/tests` 檔數下限、E501 棘輪、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE`、compat-ci `paths` | **主控收尾重釘（實作輪收尾步驟，不是設計缺口）** |
| `test_context_budget_guard.py::PrintModeBgCeilingTest` | 本棒不改 `unattended_authz` 常數 | 預期零改；`SG` 以 AT-440-8-1 守 |

## 3. AT 完整清單

> 依測試檔的閱讀索引（權威清單是 §1；各 AT 的測試類型見 §1 與 §2 標頭）；測試函式名樣式 `test_<AT 底線形>_<slug>`（R164）。本節表格第一欄是測試檔、不是 AC ID。

### 3.1 新增測試檔（`tools/tests/`；四檔，各不超過 35 個 AT）

| 測試檔 | AT 數 | AT ID |
|--------|-------|-------|
| test_selfimproving_schedule_model.py（SM） | 32 | AT-436-1-1、AT-436-1-2、AT-436-1-3、AT-436-1-4、AT-436-1-E-1～AT-436-1-E-4、AT-436-2-1～AT-436-2-7、AT-436-2-E-2、AT-436-2-E-3、AT-436-5-1、AT-436-5-E-2、AT-437-1-1、AT-437-1-2、AT-437-1-3、AT-437-1-E-1、AT-437-1-E-2、AT-437-2-1、AT-437-2-2、AT-437-2-3、AT-437-2-E-1、AT-437-2-E-2、AT-437-3-1、AT-437-3-2、AT-437-3-E-1 |
| test_selfimproving_schedule_patrol.py（SP） | 21 | AT-436-2-E-1、AT-436-3-1、AT-436-3-2、AT-436-3-E-1、AT-436-3-E-2、AT-436-5-E-1、AT-436-6-1、AT-436-6-E-1、AT-438-1-1、AT-438-1-2、AT-438-1-E-1、AT-438-1-E-2、AT-438-1-E-3、AT-438-2-1、AT-438-2-E-1、AT-438-3-1、AT-438-3-2、AT-438-3-E-1、AT-438-3-E-2、AT-438-4-1、AT-438-4-E-1 |
| test_selfimproving_schedule_advance.py（SA） | 21 | AT-438-5-1、AT-438-5-E-1、AT-438-5-E-2、AT-438-5-E-3、AT-438-6-1、AT-438-6-2、AT-438-6-E-1、AT-438-7-E-1、AT-438-8-1、AT-438-8-E-1、AT-439-1-1、AT-439-1-E-1、AT-439-2-1、AT-439-2-E-1、AT-439-3-1、AT-439-3-2、AT-439-3-E-1、AT-439-4-1、AT-439-4-E-1、AT-439-5-1、AT-439-5-E-1 |
| test_selfimproving_schedule_gate.py（SG） | 31 | AT-436-4-1、AT-436-4-2、AT-436-4-3、AT-436-4-E-1、AT-436-4-E-2、AT-436-5-2、AT-437-5-1、AT-437-5-2、AT-437-5-E-1～AT-437-5-E-3、AT-438-7-1、AT-440-1-1、AT-440-1-E-1、AT-440-1-E-2、AT-440-2-1、AT-440-2-E-1、AT-440-2-E-2、AT-440-3-1、AT-440-3-2、AT-440-3-3、AT-440-3-E-1、AT-440-4-1、AT-440-4-E-1、AT-440-5-1、AT-440-5-E-1、AT-440-6-1、AT-440-6-E-1、AT-440-7-1、AT-440-7-E-1、AT-440-8-1 |

> SA 為 D-QA 增補後新增：SP 原 34 個，增補 AC-SI-38-8、38-6 的新 AT 與 AC-SI-39-2～39-5 的獨立負控後逾 35，故把入帳之後的推進、commit、收尾與 Console (a) 運轉一族分出（主控裁決 D-QA-2、D-QA-10、D-QA-11；§5.7 已登記新檔，SG 31 個仍未逾上限，不需拆分）。

**3.3 Contract Tests 與 3.4 E2E Tests**：（均無：P4 根層半沒有鍵 B 的 AutoClaude 契約測試；出口 (a)～(f) 的真機運轉屬實跑檢核 V30～V35，不入 AT，因為 AT 不碰真帳本、真 OS 任務、真 `claude` 與外網。Console 側的 Docker 全棧 V 系列在 Console TCS。）

## 4. 邊界與錯誤測試規格

邊界與錯誤情境以 `AT-<NNN>-<Y>-E-<n>` 命名並已列入 §1；下表是依場景類型的索引（第一欄為場景類型、不是 AC ID）。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|----------|
| 時間邊界（格、黑窗、逾期、靜默窗） | AT-436-1-1、AT-436-1-E-1、AT-436-2-2、AT-436-2-4、AT-437-3-E-1 | 起點含終點不含、`now` 缺 offset、早於 origin、`HH:MM` 區間、恰等於靜默窗、嚴格大於 2×心跳 | 注入的 `now`、替身 `local_hm`、合成逐字稿 | 逐邊界斷言；不讀系統時鐘 |
| 用法錯誤（rc 3） | AT-436-3-E-1、AT-440-7-E-1、AT-436-1-E-3 | 缺 offset、未知旗標、`--run`、缺必備旗標、`--due-at` 搭配不當 | 旗標複本 | rc 3、stdout 空、stderr 點名 |
| 狀態類拒收（rc 1） | AT-436-1-E-3、AT-437-1-1、AT-437-2-E-2、AT-436-5-E-2 | 非 patrol、非格起點、未啟用、同格已有、界外週期、kind 不符、缺引言 | 手寫帳本與稽核檔 | rc 1、碼、`obs-draft:`、零殘留 |
| 無人值守與授權 | AT-438-3-1、AT-438-3-2、AT-438-3-E-1、AT-438-3-E-2、AT-437-2-E-1、AT-436-5-E-2、AT-436-3-E-2 | A／B／C 類真值表、跨運轉、字面 0、空字串、PATROL_RUN 單獨存在 | 環境變數組合 | `UNATTENDED-REFUSED` 或不變；零寫入 |
| 稽核檔變形（位元組與字串） | AT-437-1-E-1、AT-437-1-E-2、AT-437-1-3、AT-437-2-1、AT-439-2-1 | 表外鍵、控制字元、CR／LF、超長、全空白、MAC 被改、重複 `audit_ref`、金鑰缺 | 變形稽核檔、黃金檔 | 各一碼、保留稽核檔、不重試 |
| 載體缺席與量不到 | AT-436-1-E-2、AT-437-3-E-1、AT-437-3-2、AT-437-5-E-3、AT-436-4-E-1 | 無事件帳本、憑證為空、查詢失敗、export 不讀家目錄 | 檔案不存在或替身 | null／NOT-EVALUABLE 與理由；不是零、不是綠 |
| 偽造與不合法事件 | AT-440-1-E-1、AT-437-5-E-1、AT-437-5-E-2、AT-439-4-1 | `sched.*` 欄位違規、同格重複、`due_at` 不在格起點、偽造 DEC | 手寫事件 | 各恰一碼；偽造 DEC 被 `decverify` 擋 |
| 併發與冪等 | AT-436-3-E-2、AT-436-2-7、AT-439-2-1、AT-436-6-1 | 巡邏鎖、同格同因一筆、手動與自動入帳互斥、每格至多一個運轉 | `apply_lock`、`evwrite.PAUSE_HOOK`、連續心跳 | 不重複事件、`seq` 連續 |
| 外部行程與環境 | AT-438-1-1、AT-438-1-E-1、AT-438-1-E-2、AT-438-6-E-1 | argv、環境白名單、硬牆、claude 缺、handback 缺節、harness 殺行程、逾時 | 替身 `claude`、替身 `run_argv` | 逐元素相等、機密零洩漏、只記日誌 |
| 提交與 git | AT-438-5-1、AT-438-5-E-1、AT-438-5-E-2、AT-438-5-E-3 | 白名單、髒樹、多寫檔、hook 拒絕、`sched_auto_commit` 關閉 | 夾具 repo 與 hook | 不 push、不繞 hook、不重試 |
| OS 載具與跨平台 | AT-436-4-1、AT-436-4-3、AT-436-4-E-1、AT-440-3-2 | 三層鎖逐任務、包裝腳本行尾與金鑰讀取面、plist、外部執行檔字面守衛 | 文字掃描、替身 | 逐項注入副本自證 |
| 差分（單一實作） | AT-437-3-1、AT-438-1-1、AT-438-3-E-2 | `status` 與 `export` 同函式、argv 對 `fresh_argv`、授權閘單一站點 | 獨立重算 | 逐項相同 |
| 刻意不做 | （無 AT） | 真機運轉 V30～V35、macOS 與 Linux 實跑、`sched_auto_push` 為 true、Console 半、真 OS 任務註冊 | — | 實跑檢核或 §7.2 登記，不以構造資料充當 |

## 5. 測試資料規格

共用夾具住 `tools/tests/_selfimproving_p4_fixtures.py`（新增；底線開頭、不被收集；§5.7）與既有 P1～P3 夾具（呼叫形態不變，R163）。夾具模組自行定義判準函式與建構器，不 import 被測模組的內部私有符號（被測的公開函式級入口見 §5.6）；**函式名皆為建議**，Developer 改名須於勘誤登記對照。合成編號（PROP、RUN、ATT、DEC、OBS）一律於執行期以字串相加組出（`pid()`、`rid()`、`obs_id()`）；本檔與測試原始碼不寫不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>`（NFR-P4-7）。**金鑰與稽核檔**：測試金鑰於執行期以 `secrets.token_hex` 組出、只經環境變數餵入、不寫入任何檔案字面；稽核檔建構沿 P2 §5.5 的 `write_audit`、`body_decide`（新增 `body_sched_set`、`body_run_request`），每份用新的 UUID `audit_ref`，簽章對象取 `consoleaudit` 的位元組權威（R141 (e)）。

### 5.1 基線 repo（`make_p4_repo`）、環境與常數

`make_p4_repo(dest, *, events=None, prm=None, commit=True) -> Path`：包裝 `make_p3_repo`——P1、P2、P3 §5.1 的全部內容逐字不變，再於其上：(1) `params.json` 為 **41 鍵**（P3 的 32 鍵逐值沿用，加 R159 的九鍵預設值；以 `set_params(R, …)` 覆寫者，AT 明文寫出）；(2) 把真 SOP 的位元組複製為 `docs/05_development/SelfImproving_Operations_SOP.md`（巡邏器自 `--repo` 讀範本）；(3) 家目錄 `AUTOSDD_SI_DIR` 與 `CLAUDE_CONFIG_DIR` 指向 tmp；(4) 預設事件帳本只有 `BASE-EV`（P3 同名）。**常數**：`O`＝`2026-11-02T08:00:00+00:00`（預設 origin）；`D1`＝1440 分鐘；`HB`＝15；`H`＝小時、`MIN`＝分鐘（`timedelta` 縮寫）；`TEST_KEY`＝執行期組出的金鑰字串。**環境（hermetic）**：沿 P3 §5.1 (a)～(q)，另 (r) 替身 `claude`（`STUB`）是 tmp 內的 Python 腳本，記錄 `sys.argv`、`os.environ` 鍵值、`os.getcwd()` 到 JSON 記錄檔並依旗標寫 handback、回傳指定 rc；(s) 測試行程的 `AUTOSDD_UNATTENDED`、`AUTOSDD_SI_PATROL_RUN`、`AUTOSDD_SI_PATROL_OFF`、`AUTOSDD_SI_AUDIT_KEY` 只在明文要求的 AT 內以 `mock.patch.dict(os.environ, …)` 設定、用畢即還原，其餘子行程不傳 `AUTOSDD_*`；(t) 凡比較路徑者兩側先 `realpath`（雲端 runner 的 TEMP 為 8.3 短檔名或 symlink）；(u) 不讀真 `AgentConsole/.env`、不註冊真 OS 任務、不 spawn 真 `claude`、不連網；(v) 需要 PowerShell 引擎的子項以 `_ps_engine()` 為 `None` 時走靜態判準（不 skip）。

### 5.2 建構器與情境表

**建構器**（`_selfimproving_p4_fixtures.py`；事件與流程建構器沿 P1～P3：`ev`、`write_events`、`append_events`、`rewrite_event`、`set_params`、`snap`、`M`、`MJ`、`promoted`、`new_prop`）：

- `sched_set(R, t, *, enabled=True, period=1440, carrier="host", **kw)`、`run_open_f(R, t, *, due_at=None, by="patrol")`、`skip_ev(R, t, reason, *, due_at=None, detail="x", audit_ref=None)`：手寫對應事件並回其 `seq`；`due_at` 缺省取 `t` 所在格起點。
- `audit_file(R, kind, body, *, key=TEST_KEY, subject=None, time=None, audit_ref=None, tamper=None)`：依 `kind`（五值）建構外層七鍵稽核檔並以 `consoleaudit` 的簽章對象簽章後落到 tmp 家目錄的 `console_audit/`，回 `audit_ref`；`tamper` 指名「對位元組做一處改動」（鍵序對調、改一字元）供 MAC 負控；`golden(name)`：讀 Console 側黃金檔 G6～G9（路徑由 Console TCS 定、Developer 現查），缺檔＝`AssertionError`。
- `a_class_calls(R, *, run)`：回八個 A 類動詞各一個合法呼叫（argv 清單）的字典（含 PROP 與 ATT 的前置佈置）；`c_class_calls(R)`：回十三個 C 類動詞的合法呼叫；`readonly_calls(R)`：回九個唯讀呼叫。
- `Deps(**kw)`：`patrol.main` 的依賴注入包（`quota`、`driver_quiet`、`which`、`preflight`、`run_argv`、`verbs`）；`make_stub(R, *, rc=0, writes_prop=False, handback="ok")`：建 `STUB` 並回其路徑與記錄檔路徑。
- `git_repo_with_hook(dest, *, hook_rc=0)`：夾具 repo 加可計數的 `pre-commit` hook；`dirty(R, rel)`：寫一個未追蹤檔。

**情境表**（時刻皆 UTC；`O` 起算）：

- **S-CELL**：`sched.set`（啟用、週期 1440、`t`＝`O`）；格 0＝`[O, O＋1 天)`，格 1＝`[O＋1 天, O＋2 天)`。
- **S-STATUS**：S-CELL 加 `sched.skip`（`blackout`、`due_at`＝`O`、`t`＝`O＋1 H`）與一筆 Console 載體的 `sched.set`（週期 1440、`t`＝`O＋30 MIN` 之前的啟用重置，取其為最近一筆）。
- **S-CHECK-OK**：S-CELL 加 `run.open(f)`（`by` 為 `patrol`、`due_at`＝`O`）、`blackout` skip、Console 載體 skip（`audit_ref` 唯一）。
- **S-PATROL**：S-CELL 加乾淨工作樹、`STUB`（rc 0、零提案）、`Deps.quota` 為 `free`、`driver_quiet` 為假、`which` 回 STUB 路徑、`preflight` 回 `None`；本機時分替身落在黑窗之外；單一心跳 `now`＝`O＋1 H`（本格已過 2×心跳）。
- **S-APPROVE／S-PROMOTE**：`promoted`／`new_prop` 手寫的 PROP 鏈加 Console 載體 `dec`（approve、promote、rollback 各一，稽核檔存在、金鑰環境已設）；`heldout.freeze` 由夾具附上。
- **S-ENV**：A 類真值表的四種環境（甲乙丙丁，AT-438-3-1）。

### 5.6 測試 seam、函式級入口、判準函式與逐字清單

- **被測函式級入口**（建議名）：`sched.schedule_obj(events, params, now, *, armed)`（回 R158 的 `schedule` 物件）；`sched.decide_skip(inputs) -> str | None`（R143）；`sched.attempt_plan(events, now, inputs)`、`sched.skip_plan(events, now, reason, detail)`（回要追加的事件 dict 或 `None`）；`sched.local_hm(now)`（R143 (b) 的唯一本機時分來源，供替身）；`sched.blackout_hit(hm, ranges)`；`sched.quota_verdict(state)`（回 `skip`、`degrade`）；`sched.other_driver(repo, now, params)`；`sched.dirty_paths(repo)`；`sched.spawn_problem(repo, *, which, preflight)`；`sched.armed_value(runner)`；`unattended.gate(verb, run, env)`；`consoleaudit.body_guard(kind, body)`；`patrolbrief.render(template, fields)`、`patrolbrief.template_problems(sop_text)`；`patrol.main(argv, deps=None) -> int`（CLI 與測試共用；`deps` 缺省取真依賴）；`runner.run_argv(argv, *, env, timeout, cwd)`、`runner.spawn_detached(argv, *, env, cwd) -> int`；`patrol.main` 的 `deps` 另含 `spawn_detached`（替身記錄 argv、env、cwd 並回假 pid）、`pid_alive(pid, started_at)`、`kill_tree(pid)`；`schedarm.arm(...)`、`schedarm.disarm(...)`（以注入的 `run_argv` 取代 `runner.run_argv`）；既有 seam `evwrite.PAUSE_HOOK`、`evwrite.LOCK_TIMEOUT_SECONDS`、`resume_route.fresh_argv`、`resume_route.preflight_problem`、`quota_gate.read_quota`、`transcript_activity.newest_conversation_at`。
- **測試自有判準函式**：`sop_p4_problems(text)`（碼 `SOP-P4-REQ-MISSING`、`SOP-P4-STALE-WORDING`、`SOP-P4-FENCE`、`SOP-P4-FORBIDDEN`、`SOP-P4-PLACEHOLDER`）；`patrol_verb_calls(src)`（AST；碼 `V-PUSH`、`V-NOVERIFY`、`V-ADD-ALL`、`V-DECIDE-TRANSCRIPT`、`V-UNKNOWN-VERB`）；`secret_scan(root, needle)`（全樹位元組掃描）。沿用既有：`capability_problems`、`forbidden_hits`（`test_selfimproving_capability.py`）；`parse_at_headers`、`anchor_problems`、`collect_nodes`（`test_selfimproving_p2_meta.py`，匯入不複製）；`_ps_engine`（`test_install_windows_nightly.py`）。
- **SOP-P4-REQ**（〈巡邏與無人運轉（P4）〉與相關節須含；字面須位於程式碼圍欄之外，除另註）：1 四個子節標題；2 〈每心跳做什麼〉表的四個步驟列與七種跳過字面 `disabled`、`blackout`、`quota-band`、`other-driver`、`dirty-tree`、`run-open`、`spawn-failed`；3 〈停用與逃生口〉的 `sched set --enabled false`、`sched disarm`、`AUTOSDD_SI_PATROL_OFF`；4 〈日誌與逾期處置〉的 `overdue` 與「不得手補 `sched.skip`」；5 〈無人運轉任務書範本〉圍欄（位於圍欄內）含 R152 的全部大寫占位符與四個 handback 標題；6 〈啟動條件〉含第六類與 `日曆格`；7 〈P2 動詞〉序列條文含 `run-scoped`（或 `AUTOSDD_SI_PATROL_RUN`）。另：〈P2 動詞〉不含「無人值守：有設時寫入動詞一律 rc 1」；〈擷取者〉〈歸因者〉〈提案者〉〈研究者〉四節不含 P3 `SOP-P3-FORBID` 清單的片段。

### 5.7 允許變更的檔案集合（新檔名為本檔類推——PRD 建議檔名依現查校準；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md`；Developer 棒只動此集合）

| 類別 | 路徑 |
|------|------|
| 新增（程式） | `tools/lib/selfimproving/{sched,unattended,schedcheck,schedwrite,patrolbrief,patrol,patrolrun,schedarm}.py`，可選 `evspec.py`（R160 兩態擇一）；`tools/si_patrol_tick.ps1` |
| 新增（測試） | `tools/tests/{_selfimproving_p4_fixtures,test_selfimproving_schedule_model,test_selfimproving_schedule_patrol,test_selfimproving_schedule_advance,test_selfimproving_schedule_gate}.py` |
| 修改（程式） | `tools/lib/selfimproving/{events,status,export,params,check,evcheck,decwrite,writeverbs,consoleaudit,runner}.py`（增量上限依 PRD §9.1〈C4 套件檔案表（P4）〉與 R160：`writeverbs.py` 總數 ≤400、`events.py` 總數 ≤400 否則拆 `evspec`；`fold.py` 不得改）；`tools/selfimproving.py`（入口，合併由收尾單人窗口做）；其他 P2 動詞檔（`sandbox.py`、`verify.py`、`promote.py`、`obswrite.py` 等）僅限把 `refuse_unattended` 呼叫改為 `unattended.gate` 的站點；`tools/lib/selfimproving/issuemap.py` 僅限 `EVENT_LABELS` 加 `sched.set`／`sched.skip` 兩列（D-IMP-3；主控落地） |
| 修改（OS 載具與資料） | `tools/install_windows_nightly.ps1`、`tools/scheduled_task_expectations.json`；`docs/06_quality/SelfImproving_Protocol/params.json`（加九鍵，與 `PARAM_SPECS` 同 commit）；`docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md`（三列，同 commit） |
| 修改（測試） | R163／§2.5 同步表所列既有測試檔的指名函式與常數；`test_selfimproving_capability.py` 的 `CAPABILITY` 表與計數 |
| 主控專屬 | 真帳本與真事件帳本；真 OS 任務註冊；護欄層重釘、compat-ci `paths`、`tools/tests` 棘輪（**實作輪收尾步驟**）；RTM 檔 `docs/06_quality/RTM-SelfImproving-P4-<日期>.md`；SCG-4 報告 |
| 不得變更 | `.claude/**`（含 `settings.unattended.json`）、PRD、SOP、P0～P3 TCS、`autoclaude/` 引擎原始碼、`AgentConsole/**`、`.github/**`、`tools/lib/{schedule_backend,resume_route,unattended_authz,model_roles}.py`、`tools/check_scheduled_task_drift.py` |

---

## 6. RTM 連結確認

追溯鏈（US→AC→AT→測試檔→規則→NFR）已在 §1（AC→AT）、FRD-lite（US→AC、NFR）與下表閉合；根層 RTM 檔由主控於 SCG-4 依落點 SSOT 落 `docs/06_quality/RTM-SelfImproving-P4-<日期>.md`（本檔不代寫）。**覆蓋核對**：PRD AC 24 個中 23 個有至少一個 AT，`AC-SI-37-4` 在本檔無 AT（委 Console TCS）；自增 AC 8 個皆有至少一個正控與一個負控；全檔 AT 105 個（正控 56、負控 49），分佈於四個測試檔（SM 32、SP 21、SA 21、SG 31），每個新檔不超過 35 個 AT（NFR-P4-6）。

### 6.1 US → AC → AT

| US ID | AC ID | AT 數 | 測試檔 | 主要規則與 NFR |
|-------|-------|-------|--------|----------------|
| US-401 | AC-SI-36-1（8）、36-2（10）、36-5（4）、36-6（2）、37-3（3）、37-5（5） | 32 | SM、SP、SG | R138、R140～R145、R158；NFR-P4-1、4 |
| US-402 | AC-SI-36-3（4）、36-4（5） | 9 | SP、SG | R148、R161；NFR-P4-2、5 |
| US-403 | AC-SI-37-1（5）、37-2（5）、37-4（0） | 10 | SM | R141、R146 |
| US-404 | AC-SI-38-1（5）、38-2（2）、38-3（4）、38-4（2）、38-5（4）、38-6（3）、38-7（2）、38-8（2） | 24 | SP、SA、SG | R150～R156、R166、R167；NFR-P4-3 |
| US-405 | AC-SI-39-1（2）、39-2（2）、39-3（3）、39-4（2）、39-5（2） | 11 | SA | R149、R155、R157；NFR-P4-3、4 |
| US-406 | AC-P4-040-1（3）、040-2（3）、040-3（4）、040-4（2）、040-5（2）、040-6（2）、040-7（2）、040-8（1） | 19 | SG | R137、R139、R159、R160、R162～R164；NFR-P4-6～10 |

### 6.2 行為規則 → AT（R137～R167 每條至少一個 AT）

| 規則 | 主題 | AT |
|------|------|----|
| R137、R138 | 動詞、旗標、rc、`sched set` 的載體與界 | AT-440-7-1、AT-440-7-E-1、AT-436-5-1、AT-436-5-E-2、AT-437-1-1 |
| R139 | 事件詞彙與欄位表 | AT-440-1-1、AT-440-1-E-1、AT-440-1-E-2 |
| R140 | `check` 35 項與判準版本 | AT-437-5-2、AT-437-5-E-1、AT-437-5-E-2、AT-437-5-E-3 |
| R141 | Console 稽核檔兩新 kind 與字串規則、位元組權威 | AT-437-1-1、AT-437-1-2、AT-437-1-3、AT-437-1-E-1、AT-437-1-E-2 |
| R142 | 排程狀態折疊 | AT-436-1-1、AT-436-1-2、AT-436-1-3、AT-436-1-E-1、AT-436-1-E-2、AT-436-1-E-4 |
| R143 | 七種跳過判序與判準 | AT-436-2-1～AT-436-2-6、AT-436-2-E-2、AT-436-6-E-1 |
| R144 | 同格同因一筆、`due_at`、黑窗跨格 | AT-436-2-7、AT-436-2-E-1、AT-436-2-E-3 |
| R145 | `overdue` | AT-437-3-E-1、AT-436-2-E-3 |
| R146 | Console 載體入帳 | AT-437-2-1、AT-437-2-2、AT-437-2-3、AT-437-2-E-1、AT-437-2-E-2 |
| R147 | `run-open --trigger f` | AT-436-1-4、AT-436-1-E-3 |
| R148 | 一次性心跳 | AT-436-3-1、AT-436-3-2、AT-436-3-E-1、AT-436-3-E-2、AT-436-5-E-1、AT-436-6-1、AT-438-6-2 |
| R149 | 入帳 | AT-439-1-1、AT-439-1-E-1、AT-439-2-1、AT-439-2-E-1 |
| R150 | 運轉前置序 | AT-438-1-2、AT-438-1-E-1、AT-438-8-1 |
| R151 | spawn 形態 | AT-438-1-1、AT-438-1-E-2 |
| R152 | 任務書 | AT-438-2-1、AT-438-2-E-1 |
| R153 | run-scoped 授權 | AT-438-3-1、AT-438-3-2、AT-438-3-E-1、AT-438-3-E-2、AT-438-4-1 |
| R154 | DEC 只認 Console、權限列 | AT-438-4-E-1、AT-438-7-1、AT-438-7-E-1 |
| R155 | 機械步驟與 commit | AT-438-5-1、AT-438-5-E-1、AT-438-5-E-2、AT-438-5-E-3、AT-439-3-1、AT-439-3-2、AT-439-3-E-1、AT-439-4-1、AT-439-4-E-1 |
| R156 | 收尾與 handback | AT-438-6-1、AT-438-6-2、AT-438-6-E-1 |
| R157 | 日誌 | AT-439-5-1、AT-439-5-E-1 |
| R158 | `status.schedule`、`export`、`console_pending` | AT-437-3-1、AT-437-3-2、AT-437-5-1 |
| R159 | `params` 九鍵 | AT-440-2-1、AT-440-2-E-1、AT-440-2-E-2 |
| R160 | 能力登記、LOC、`runner.run_argv`、`spawn_detached`、`FORBIDDEN_EXEMPT` | AT-440-3-1、AT-440-3-2、AT-440-3-3、AT-440-3-E-1 |
| R161 | OS 任務、包裝腳本、`schedarm` | AT-436-4-1、AT-436-4-2、AT-436-4-3、AT-436-4-E-1、AT-436-4-E-2、AT-436-5-2 |
| R162 | SOP 條文 | AT-440-4-1、AT-440-4-E-1 |
| R163 | 零退化與同步站點 | AT-440-5-1、AT-440-5-E-1 |
| R164 | AT 錨定與範圍 | AT-440-6-1、AT-440-6-E-1、AT-440-8-1 |
| R165 | 測試 seam | AT-436-2-2、AT-437-3-2（seam 注入的代表 AT） |
| R166 | Console 載體 (a) 運轉的執行與收尾 | AT-438-8-1、AT-438-8-E-1 |
| R167 | 脫離式 spawn 與步 0′ 巡視 | AT-438-1-1、AT-438-1-E-3、AT-438-6-1、AT-438-6-2、AT-438-6-E-1 |

### 6.3 實跑檢核 V30～V35（**不是 AT**；主控與掌舵者於真機做，結果寫進 SCG-4 報告；未驗者如實標「未驗」，構造情境不得充當）

| 編號 | 實查項 | 步驟與通過判準 |
|------|--------|----------------|
| V30 | 真機 spawn：`claude -p` 能起且心跳結束後仍存活（D-QA-14；兼驗 D-RT-4 的環境白名單） | 於真 OS 任務下觸發一次到期心跳；心跳行程結束後 `<si>/patrol/<RUN>/spawn.json` 的 pid 仍可查（Windows `Get-Process -Id`、macOS `ps -p`）且**心跳結束後存活至少 1 分鐘**；`claude` 因缺環境變數而起不來、或因 breakaway 被拒而記 `spawn-failed` 皆為不通過 |
| V31 | 出口 (a)：真實到期巡邏開 `run.open(f)` 並 `run-close` | 事件帳本有 `run.open(trigger=f, by=patrol)` 與對應 `run.close`；日誌有各步驟行 |
| V32 | 出口 (b)：Console `sched-set`／`run-request` 真機走完入帳 | 兩種稽核檔經巡邏器或手動入帳；`status.schedule.last_set.carrier` 為 console；(a) 運轉依 AC-SI-38-8 被執行 |
| V33 | 出口 (c)：Console `approve` 被自動入帳並推進到 `verify` | `dec(approve)` 之後有 `app.sandbox`、`app.verify` 與 `card` 事件，verdict 原樣進卡面 |
| V34 | 出口 (d)(f)：停用 OS 任務後 `overdue` 翻 true；`unmeasured` 額度帶確實跳過 | `sched show` 的 `overdue` 為 true 且指令與憑證輸出貼入；`unmeasured` 時有一筆 `sched.skip(quota-band)`、無 `run.open` |
| V35 | 出口 (e)：git 歷史對 DEC 對帳（含巡邏器 commit） | 每個 `app.promote` 皆有對應人的 DEC；巡邏器 commit 只含 `touched` 與 SI 自有路徑、無 push |

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 裁決與預設（D-RT-1～D-RT-6 為主控對本檔六個再決點的裁決，取代原預設；⚖ 4、⚖ 7 為本檔預設）

| 編號 | 問題 | 本檔預設 | 替代與再開症狀 |
|------|------|----------|----------------|
| D-RT-1（原 ⚖ 1） | PRD AC-SI-37-2 寫「兩動詞於 `AUTOSDD_UNATTENDED` 有設且**無** `AUTOSDD_SI_PATROL_RUN` 時 rc 1」，而 AC-SI-38-3 ③ 與 §9.3 把 `run-open`、`sched set` 列為無人值守下**一律** rc 1 | **主控裁決：採 AC-SI-38-3 ③，`AUTOSDD_UNATTENDED` 有設時一律 rc 1**（PRD AC-SI-37-2 的矛盾句主控已原地訂正）；AT-437-2-E-1、AT-438-3-2 釘此（無「有設且無 PATROL_RUN 才拒」的格） | 替代：`PATROL_RUN` 有設時放行 Console 入帳（會讓無人主控可自開運轉，與 D-SCH-13 衝突）。再開：掌舵者要求無人主控入帳稽核檔 |
| D-RT-2（原 ⚖ 2） | 任務書要求以 `schedule_backend` 替身後端判 OS 任務；PRD §9.7 #85 決定 `schedarm` **不 import、不改** `schedule_backend.py`（macOS 自寫 plist；Windows 呼叫安裝器） | **主控裁決：**以 `runner.run_argv` 為替身縫（R161 (d)）；`schedule_backend.py` 零改動（AT-440-8-1 守） | 替代：改走 `schedule_backend`（守衛面、綁續航 planner，需暴露證據）。再開：macOS 載具的 plist 行為需與續航哨兵共用 |
| D-RT-3（原 ⚖ 3） | PRD 未明文兩處：(a) 額度帶 `converge`（收斂）是否跳過（只明列準備、停止、量不到跳過；注意帶降載）；(b) 排程停用時 Console `run-request` 被消耗成 `sched.skip` 的 `due_at`（「本格起點」不存在） | **主控裁決：**(a) `converge` 同「注意」：照跑加降載聲明（只有準備、停止、量不到跳過）；(b) 停用時 `due_at` 取稽核外層 `time`，Console 載體的 skip 不受「`due_at` 為格起點」限制（R140 `SCHED-SKIP-DUE` 只判非 Console） | (a) 替代：`converge` 也跳過（更保守）。(b) 替代：停用時 `run-request` 不寫 skip 而 rc 1。再開：真機出現 `converge` 帶的無人運轉擠壓額度 |
| ⚖ 4 | `CHECK_RULES_REV` 是否因新增兩項而 bump | 由 4 增為 5（主控已採；沿 P3 先例；基線文件三列同 commit） | 替代：不 bump（改判準版本語意需另證）。再開：量測指紋與 `check` 項數的對應被質疑 |
| D-RT-4（原 ⚖ 5） | 子行程環境「須帶 `AUTOSDD_*` 與機密以外的子集」的實際白名單 | **主控裁決：**`runner` 探針白名單＋`APPDATA`、`LOCALAPPDATA`、`CLAUDE_CONFIG_DIR`、`AUTOSDD_SI_DIR`＋四個必含鍵；不含任何 `KEY`／`TOKEN`／`SECRET`／`PASSWORD` 名稱與其他 `AUTOSDD_*`（AT-438-1-E-2 釘） | 替代：再加 `ProgramData` 等。再開：真機 `claude` 因缺環境變數啟動失敗（留 V30 驗） |
| D-RT-5（原 ⚖ 6） | `tools/si_patrol_tick.ps1` 讀金鑰，但不在 PRD NFR-SI-02-1 的 `non_evolvable_globs` 與守衛面清單 | **主控裁決：**不列入 `non_evolvable_globs`（不擴守衛面，沿〈守衛面准入〉須暴露證據）；包裝腳本以 AT-436-4-3 靜態釘金鑰讀取面 | 替代：PRD 修訂把它列入不可進化面。再開：提案者的 PROP 觸及該腳本 |
| ⚖ 7 | 旗標細部與碼名（PRD 只定動詞與行為）：`sched`／`patrol` 的旗標、`SCHED-QUOTE-REQUIRED` 等新碼、`sched show` 文字首行、`patrol` 輸出形態、`patrol.log` 行格式 | 本檔 R137、R138、R147、R157 與兩張碼表（本檔類推） | 再開：掌舵者看過真輸出後要求改版面 |
| D-RT-6（原 ⚖ 8） | Console 契約規定 `reason`／`note` 有值時不得全空白，而 P3 R136 對 `decide.reason` 「只含空白者放行」 | **主控裁決：**新 kind 拒收全空白（`FIELD-BLANK`）、`decide` 維持放行；兩者並存，AT-437-1-E-2 釘新 kind | 替代：統一為拒收（需改 R136 與其 AT）。再開：Console 與 CLI 對同一份空白字串結論不一致 |
| D-QA-1 | 能力登記 `FORBIDDEN` 的 OS 排程器字面與 `schedarm.py` 互斥 | **主控裁決（乙）**：`FORBIDDEN` 清單不動，加逐檔豁免表 `FORBIDDEN_EXEMPT = {"schedarm.py": ("schtasks", "launchctl", "Register-ScheduledTask")}`（只豁免這三條）與負控（`schedarm.py` 以外仍紅、`schedarm.py` 內核心禁字樣仍紅）；`schedarm.py` 的平台專屬 argv 須在 `sys.platform` 守衛內。落點 R160、R161 (d)、AT-440-3-2、AT-440-3-3、AT-440-3-E-1、§2.5 | 替代甲（全域移除三條）不採：削弱整個套件的守衛 |
| D-QA-2 | Console (a) 運轉無人執行 | **主控裁決**：新增 AC-SI-38-8；巡邏心跳於同一心跳執行入帳的 Console (a) 運轉，不看啟用旗標、被擋只寫日誌不記 `sched.skip`。落點 R166、AT-438-8-1、AT-438-8-E-1、AT-438-1-1（Given 兩種運轉）；SC-SI-6 對映見追溯矩陣 | 替代（只由互動主控接手）不採：無人時按鈕等於失效 |
| D-QA-3 | 推進路徑髒樹記 `sched.skip` | **主控裁決**：推進路徑只寫日誌、不寫任何 `sched.skip`；刪原 R155 (d) 的 skip 字樣。落點 R155、AT-438-5-E-1（加排程停用子情境）、AT-439-4-E-1 | 替代（專屬 reason、`due_at` 可為 null）不採 |
| D-QA-4 | 無人值守 rc 1 清單三處不一致 | 以 AC-SI-38-3 ③ 為唯一真值表，補 `patrol`、`sched arm`、`sched disarm`；本檔 R153 與 AT-438-3-2 原本即含，不需改 | — |
| D-QA-5 | (a)～(e) 殘字 | PRD 側修正，本檔無落點 | — |
| D-QA-6 | 值不變的重送重置格線 | **主控裁決**：origin 只在 false 轉 true 或 `period_minutes` 改變時重置。落點 R142 (b)、R140、AT-436-1-3（加值不變重送子情境）、AT-437-5-E-2 | — |
| D-QA-7 | `WakeToRun` 每日喚醒 | **主控裁決**：`AutoSDD_SI_Patrol` 的 `WakeToRun=false`，nightly、smoke 維持 true。落點 R161 (a)(b)、AT-436-4-1 | 再開：睡著的機器長期不巡邏（已知邊界，`overdue` 偵測） |
| D-QA-8 | 黑窗只涵蓋觸發時刻 | **主控裁決**：`sched_blackout_local` 初值 `["21:00-01:30"]`，WHY 與「只約束嘗試時刻」寫入 R159。落點 R159、AT-440-2-1、AT-440-2-E-2 | — |
| D-QA-9 | 無人值守 `decide --carrier console` 為實質死許可 | **主控裁決**：維持字面並加註（無人主控不持金鑰、實際為 `AUDIT-KEY-MISSING`、保留以 fail-closed）。落點 R153 ② | — |
| D-QA-10 | 巡邏長跑擋入帳 | **主控裁決**：脫離式 spawn、`spawn.json`、步 0′ 巡視、同時至多一個進行中運轉、`ExecutionTimeLimit` 改 `PT1H`、`runner.spawn_detached`。落點 R148、R151、R156、R160、R161、R167、AT-436-3-1、AT-438-1-1、AT-438-6-1、AT-438-6-2、AT-438-6-E-1 | — |
| D-QA-11 | AC-SI-39-2～39-5 缺獨立負控 AT | **主控裁決**：各補一個 `-E-` AT。落點 AT-439-2-E-1、AT-439-3-E-1、AT-439-4-E-1、AT-439-5-E-1 | — |
| D-QA-12 | AC-SI-38-2 的 `obs` 入帳用詞 | 改「手寫入 OBS 帳本」。落點 R152 | — |
| D-QA-13 | 手寫列無 `obs.add` 的說明 | SOP 範本步 2 補一句；本檔 R152 同註 | — |
| D-QA-14 | 脫離式 spawn 在 Windows 的存活性（SD 提出） | **主控裁決**：旗標 `CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`、POSIX `start_new_session=True`；breakaway 被拒 fail-closed（(f) 記 `sched.skip(spawn-failed)`、(a) 只寫日誌，下一心跳再試）。落點 R167 (a)、AT-438-1-1（替身記錄旗標）、AT-438-1-E-3、§6.3 V30 | 再開：真機任務 job 不允許 breakaway 而永遠 spawn-failed（V30 現形） |
| D-QA-15 | 黑窗內 Console 立即啟動被擋（SD 提出） | **主控裁決**：Console TCS 已加註，不另增 AT | — |
| D-QA-16 | `run-open` 跳過判準應排除運轉自己 | **主控裁決**：R143 (f) 改為「本運轉以外的任何未關運轉」，與 R166 同字 | — |
| D-IMP-1（實作輪 2026-11-09 14:3x） | AT-437-1-3 的黃金檔 G6～G9 由 Console PKG-BE 產出，而 Console TCS 原寫「根層鍵 RELEASE（前置）→ PKG-BE」⇒ 根層 RELEASE ← AT-437-1-3 ← PKG-BE ← 根層 RELEASE 的循環；且 pre-push 跑根層全套，該 AT 紅會擋住根層任何 push（SCHED 棒回報） | **主控裁決（依授權代決）**：黃金檔只依賴凍結契約（API_Contract_P2c §3、PRD §9.2）與根層 `consoleaudit` 兩新 kind 的驗簽（SCHED 棒已落地），不依賴根層 RELEASE ⇒ PKG-BE 於 SCHED 棒 commit 後即開工並先產黃金檔；主控以根層 CLI 驗簽（AT-437-1-3 轉綠）、複製到 Bridge fixtures 後才 push 根層 commit；「根層鍵 RELEASE」只維持為 Console 鍵 RELEASE 的前置。產出者仍為 BE（沿 P2b G1～G5 先例）。§SCG-4 通過標準末列同步改寫 | 再開：BE 黃金檔無法被根層 CLI 收下（契約兩端解讀分歧）⇒ 回 SD 對齊 §3 字面後重產 |
| D-IMP-2（實作輪） | `events.py` 斷言行到 400（R160 寫「將超過 380 即拆 `evspec.py`」）；SCHED 棒回報 `_SPEC` 與 `events.py` 的謂詞互相依賴，拆出會循環匯入且要動熱檔 | **主控裁決**：本輪接受 400（LOC 絕對上限 ≤400 成立、`check_loc_budget` rc 0）；PATROL 棒不得再往 `events.py` 加一行，任何後續增量先拆 `evspec.py`（R160 兩態擇一） | 再開：`check_loc_budget` 對 `events.py` 轉紅 |
| D-IMP-3（實作輪） | `issuemap.py` 的 `EVENT_LABELS` 缺兩新 kind，`test_selfimproving_issuemap.py` 四個 AT（AT-IC-01-1-1／01-1-E-1／01-1-E-2／01-7-2）以閉包對帳轉紅；該檔不在 §5.7 | **主控裁決**：§5.7 修改（程式）加 `issuemap.py`（僅 `EVENT_LABELS` 兩列：`sched.set`＝排程設定、`sched.skip`＝排程跳過），§2.5 加站點；由主控落地 | — |
| D-IMP-4（實作輪） | `test_selfimproving_console_obs.py::test_AT_233_1_E_2` 子案 (e) 為 §2.5 表外站點（R153 ②／D-QA-9：無人值守下 `decide --carrier console` 過授權閘、止於 `AUDIT-KEY-MISSING`），Developer 已就地改 | **主控裁決**：追認並補進 §2.5（R163：表外改動由主控裁決後補表） | — |
| D-IMP-6（實作輪 PATROL 棒交卷 2026-11-09） | PATROL 棒對 TCS 字面的十二點偏離／再決 | **主控裁決（全部接受，字面同步）**：(1) `patrol.Deps` 無 `run_argv` 欄（spawn 走 `spawn_detached`、OS 任務走 `schedarm` 注入；欄位＝`quota`、`driver_quiet`、`which`、`preflight`、`verbs`、`spawn_detached`、`pid_alive`、`kill_tree`）；(2) `runner.spawn_detached` 多選填 `out_dir`（stdout／stderr 接到任務目錄供步 0′ 判 harness 殺行程），另增 `runner.kill_pid_tree`、`runner.pid_started_at`；(3) 預設 `verbs`＝行程內 `importlib.import_module("selfimproving")` 呼叫入口、不另起行程；(4) AT-439-2-E-1 的 `AUDIT-REF-REUSED` 子案改斷言「已入帳的 ref 不在 `console_pending`、不再被重試」（該碼由 CLI 面 AT 覆蓋）；(5) AT-439-4-1 的 `events.dec_console`「為紅」改「非 PASS」（手寫 Console 載體 `dec` 為非阻塞 NE `CONSOLE-AUDIT-MISSING`）；(6) 已有進行中無人運轉時每心跳寫一行 `code=BUSY`，Console `run-request` 依 R146 消耗成 `sched.skip(run-open)`、不留待延後的 (a) 運轉；(7) M 類 PROP 巡邏器不帶 `--memory-dir`，只寫日誌 `MEMORY-DIR`、人工推進；(8) `sandbox`／`verify` 在樹外沙盒不受髒樹阻擋，只有 `promote`／`rollback` 遇髒樹只寫日誌；(9) AT-436-4-2 安裝器 `-WhatIf` 於本機真跑；(10) AT-440-5-E-1 改檔級對帳（函式級由交卷站點清單人讀）；(11) 每心跳日誌格式 `step=<步> rc=<N> code=<碼|-> <說明>`、入帳拒收以 (audit_ref, 碼) 去重；(12) AT-440-8-1 本機並行紅屬 D-IMP-5 預期。另：主控把 `patrol.py` 的 `sys.path.insert` 迴圈變數形態改成兩句可靜態解析形態（SDD `test_ci_paths_cover_root_consumers` R67 鎖）；表外站點追認見 §2.5 新列 | 再開：(3) 若入口模組狀態殘留跨心跳污染 ⇒ 改子行程 |
| D-IMP-5（實作輪） | AT-440-8-1 以 `HEAD~1` 為基準常駐於 CI，後續任何無關 commit（Console、`.github/`、護欄層重釘）都會被判紅；淺層 clone 無父 commit | **主控裁決**：常駐形態＝差異（基準→工作樹＋未追蹤）**觸及 §5.7 允許集合**時才強制「⊆ 允許集合」與守衛面為空，未觸及＝輸出註明並通過；父 commit 不可得＝只看未追蹤檔；`skip`／`xfail` 字樣掃描恆跑；本檔（P4 TCS）的主控勘誤追加不屬守衛面。AT-440-8-1 的 Given／Then 同步改寫；護欄層重釘、compat-ci `paths` 等主控專屬變更一律另開 commit | 再開：P4 面的 commit 混入守衛面檔仍會紅（這是設計，不是誤報） |
| D-IMP-7（實作輪收尾 2026-11-09 根層全套實跑） | 全套 11 紅中六條屬 P4 新增面撞既有護欄鎖：(a) `test_check_hooks_liveness.TestNightlyTaskActionsAreWindowless` 釘「恰兩支 Action」、其去旗標注入以前帶空白的 ` -WindowStyle Hidden` 為準，而 PATROL 棒為滿足本檔 AT-436-4-2 原字面「引數含 `-NoProfile -ExecutionPolicy Bypass -File`」把第三支 Action 排成 `-WindowStyle Hidden -NoProfile …`（旗標緊貼引號）⇒ 兩鎖互斥；(b) `schedarm.py` 的 `repo/.venv/bin/python` 路徑片段命中零 guard 裸 python 站點鎖（`_ZERO_GUARD_BARE_PY_SITES` 等值）；(c) `tools/si_patrol_tick.ps1` 無 `.sh` 對等、未登記 `check_script_parity._SINGLE_SIDED_EXEMPT`（三支 parity 測試＋`macos-compat-ci` 觸發對稱）；(d) SP 測試以 `/stub/claude` 字面比對 argv（POSIX 絕對路徑字面鎖）；(e) 兩處整檔 `assertNotIn`（`patrol.py` 原始碼的 `communicate`、`patrol.log` 的金鑰）命中整檔缺席斷言鎖；(f) compat-ci `paths` 條目帶行內註解，macos 側抽取器只認整行 `- "…"` | **主控裁決（依授權代決）**：(a) 第三支 Action 旗標序改與前兩支一致 `-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File`；AT-436-4-2 的 Then 改「巡邏 Action 的 `-Argument` 字串逐旗標含四旗標」（R84 對姊妹鎖的同型修法：慣例釘的是用哪些旗標、不是相鄰）；liveness 鎖改認三支（nightly／smoke／巡邏）。(b) 登記 `_ZERO_GUARD_BARE_PY_SITES`（非呼叫，與 `platform_utils.py` 同型）。(c) 登記 `_SINGLE_SIDED_EXEMPT`（tier3；reason 以 launchd 為硬理由、刻意不含 ONBOARDING 第 8 節字樣與 Windows 排程器名——mac 對等機制＝`schedarm.py` 寫出的 launchd plist 直呼 venv python，本檔不是該節 Windows-only 缺口清單成員）＋`_TIER_BASELINE`、`_TIER34_FLOOR` 10→11、Scan-H 凍結對 AC 47→48（ADR-XPLAT-002 §4.2 規則 2：不計收斂成果、非禁止）。(d) 夾具 `_selfimproving_p4_fixtures.py` 新增 `STUB` 常數（檔頭 docstring 原已預告）、`Rig` 預設與三處引用改常數。(e) 改逐行判定（原始碼放行註解行）。(f) 註解移至條目上一行。P4 面檔（安裝器、SG／SP／SA 測試、夾具、本檔）與鎖檔（liveness、裸 python 名冊、parity 與其測試、c1c2 凍結對與護欄層重釘、workflows）依 D-IMP-5 分兩個 commit | 再開：`test_install_windows_nightly` 的 live detector 鎖（本機未註冊 `AutoSDD_SI_Patrol`，偵測器回 `task_missing`）屬 V30 真機步驟（掌舵者以系統管理員跑 `python tools\selfimproving.py sched arm`），不在本勘誤射程 |
| D-IMP-8（SCG-4 一審 2026-11-09，QA 鏡 Sonnet 報告 `docs/06_quality/SCG4-REVIEW-SelfImproving-P4-20261109.md`） | 判定 FAIL：P2 一項 B-1——AT-439-1-1 的夾具五份稽核檔 `time` 與 `audit_ref` 同向遞增（`new_uuid` 單調），入帳排序鍵改成只看 `audit_ref`、完全不看 `time` 的突變（M09b）通過全部 AT ⇒ 「依 audit time 升冪入帳」的斷言無牙；P4 三項：B-2 逐字稿載體在 CLI 實作為 `carrier=None`（判準記錄）、B-3 `tools/si_patrol_tick.ps1` 在 `$ErrorActionPreference='Stop'` 下 `2>&1` 接原生指令，PowerShell 5.1 遇 python 寫 stderr 會當成終止錯誤、該心跳 `tick.log` 不落、B-4 `AUTOSDD_SI_PATROL_RUN` 為行程自述（檔頭已劃界） | **主控裁決（依授權代決）**：B-1 只改測試——五份稽核檔 `audit_ref` 取遞減、`time` 取遞增，斷言入帳序仍依 `time`（同 `time` 子案例既有：先寫 `high` 後寫 `low`、斷言依 `audit_ref` 位元組序升冪）；B-3 同輪一併修：原生呼叫段暫設 `$ErrorActionPreference='Continue'`（取 rc 後還原），其餘段維持 Stop；B-2／B-4 只記錄不動碼。突變 M01～M07 在共用樹上與主控並行（QA 已註記）、其後改在 repo 外 worktree 跑，共用樹結案時只剩主控修改 | 再開：二審由同一 QA 鏡以新 HEAD 的 worktree 只重跑 B-1（M09b 須被殺、AT-439-1-1 綠）與 AT-436-4-3 |
| D-IMP-9（OS 任務真機首跳 2026-11-09：掌舵者以系統管理員 `sched arm` 回 `credential=2026-11-09T20:30:00+08:00` 之後；V30～V32 的前置） | (a) 首跳 `patrol.log` 記「入帳 rc=1 PATROL-EXCEPTION 未預期例外 AttributeError：module 'selfimproving' has no attribute 'main'」——入口以腳本執行時 `patrol.py` 把 tools/lib 插到 sys.path 最前，`_real_verbs` 以名字 import 入口卻解析到同名套件 `tools/lib/selfimproving/`；105 AT 全綠仍漏，因為測試一律注入 `verbs` 替身或在 tools 先於 tools/lib 的行程裡跑。(b) `tools/check_scheduled_task_drift.py` 對剛註冊的任務兩處誤判：匯出 XML 省略等於結構預設的 `<WakeToRun>`（巡邏任務為 false）被讀成 `<missing>` 而判 drift；未執行過任務的 LastRunTime 是 1999-11-30 哨兵值，被讀成九千多天沒跑而判 stale_run（該函式 docstring 早已寫明「沒跑過不算 stale」）——兩者讓 `test_install_windows_nightly` 的 live detector 鎖紅、擋 push。(c) Console V1 真機棒留下兩筆真寫入（啟用、每 120 分鐘；立即啟動），巡邏器修好後下一心跳就會入帳，並在無人時開無人運轉。(d) 修好後的首個心跳（21:00）對已晉升、量測中、無待回滾的 M 類 PROP（PROP-SI-004／006／007）記「須人工給 --memory-dir」，其實無事可做，且每心跳重複（D-IMP-6 (7) 的判準把 promoted／measuring／closed 全算進去）。(e) `tick.log` 裡 python 的輸出是亂碼：載具以 PowerShell 原生指令管線收輸出，該管線以排程任務主控台的字碼頁（繁中 CP950）解碼 python 寫的 UTF-8；互動殼常是 UTF-8，故開發機看不出 | **主控裁決**（(c) 依掌舵者互動選項「每天一次（建議）」）：(a) 入口改以檔案路徑載入（`patrol._entry()`），與 sys.path 順序無關；回歸測試 `tools/tests/test_selfimproving_schedule_patrol.py::test_D_IMP_9_real_verbs_find_the_entry_whatever_the_path_order` 以 tools/lib 在前的路徑序重現（修前即 AttributeError、修後綠）。(b) `parse_task_xml` 對省略的選填元素補結構預設值（`_XML_SCHEMA_DEFAULTS`），`stale_run_days` 對 never_ran 回 None；回歸測試 `tools/tests/test_install_windows_nightly.py::test_fresh_install_reads_as_neither_drift_nor_stale`（同一時間戳改回成功碼仍算 stale，證明判準看 LastTaskResult、不看日期）；漂移檢查器屬 §5.7「不得變更」面、P4 實作棒零改動仍成立，本修法由主控另開 commit（D-IMP-5 分 commit），AT-436-4-1 的「位元組與 HEAD 相同」判的是未提交差異、照字面成立。(c) 主控經 Console 真棧代送「啟用、1440 分鐘」（audit_ref `c289a25a-fee0-43f9-afe2-1b4ba15eca48`），三筆待入帳由修好後的巡邏心跳依時間序入帳（終態每天一次）；測試的立即啟動所開的運轉由主控 `run-close --by main` 關閉、不 spawn；Console DB 列依 PRD §9.2 保留為證據、不刪。(d) `patrolrun._advance_prop` 的 M 類判準改為「approved／verified，或已晉升類且有待回滾」；回歸測試 `tools/tests/test_selfimproving_schedule_advance.py::test_D_IMP_9_m_class_asks_for_memory_dir_only_when_a_step_is_pending`（舊判準三格紅、修後綠）。(e) 載具改以 .NET `Process` 直接收 stdout／stderr 並指定 UTF-8 解碼，不經原生指令管線；這也消除了 B-3 的成因，D-IMP-8 加的 ErrorActionPreference 放寬隨之移除。AT-436-4-3 加「假 python 印中文、tick.log 原樣保留」的斷言，並把載具複本的主控台字碼頁設成 437 模擬排程環境（舊載具即亂碼而紅、新載具綠） | 再開：任何以名字 import 入口的寫法再出現（同名套件陷阱）；真機驗證的寫入未在收尾作廢或取代（Console TCS D-CS-26） |
| D-IMP-10（雲端 CI 2026-11-09，P4 首次 push `5fc77b03`） | root-infra-ci（ubuntu）與 macos-compat-ci 皆只紅 AT-436-4-2：`_ps_engine()` 在非 Windows 回 `pwsh`，測試據以對 Windows 專屬的安裝器真跑 `-WhatIf`，安裝器的系統管理員檢查呼叫 `WindowsIdentity.GetCurrent()` 而「Windows Principal functionality is not supported on this platform」⇒ rc 1；windows-compat-ci 與本機皆綠，故收卷前看不到 | **主控裁決**：真跑條件改為 `sys.platform == "win32"` 且有引擎——本條 Given 原文即「有 **Windows PowerShell** 引擎的平台另跑 `-WhatIf`」，實作漏判平台；非 Windows 只走靜態判準、不 skip（字面不動）。以 `sys.platform` 模擬 linux 實跑該格綠、Windows 實跑仍含 `-WhatIf` | 再開：任何「有 pwsh 就真跑 Windows 專屬腳本」的測試再出現 |

### 7.2 P3 TCS 承接項與刻意不做

- 承接：P3 R136 的「寫入端與 `check` 共用同一組述詞」原則延伸到 `body_guard` 的兩個新 kind（R141 (f)）；P3 勘誤的「重釘儀式是收尾單人窗口步驟、不是設計缺口」沿用；`measure` 於無人值守下一律 rc 1（P3 R111）在 R153 ③ 中維持。
- 刻意不做：`sched_auto_push` 為 true 的語意（PRD §9.7 #88，只准 false）；`obs-add --carrier patrol`（PRD §9.7 #82，無人主控手寫 OBS 列）；真機 spawn、真 OS 任務與睡眠機器行為（V30～V35，屬 **P**）；Console UI、Bridge 與 backend（Console TCS）；macOS 實跑（標「未驗」）。

### 7.3 PRD 修訂建議（凍結檔不改；供 T1 或 PRD 修訂）

1. AC-SI-37-2 的「且無 `AUTOSDD_SI_PATROL_RUN`」一句與 AC-SI-38-3 ③ 對齊（主控裁決 D-RT-1）。2. §9.1 C23 與 PRD 其他處提到 Flyway 版本號者改為「現查最大版本＋1」（現況 Flyway 已有 V22，PRD 寫稿快照為 V19）。3. PRD §9.3 的「24 個動詞」類計數字樣（若有）以現查為準（議題中心已把動詞數推到 24，P4 後 26）。4. 子行程環境白名單（D-RT-4）寫進 §9.4〈P4 增補〉。5. `converge` 帶與停用時的 Console skip `due_at`（D-RT-3）寫進 AC-SI-36-2、AC-SI-37-2。

---

## 📋 SCG-4 通過標準

- [ ] 本檔 105 個 AT 全綠（SM 32、SP 21、SA 21、SG 31；`-q -p no:xdist -o addopts=`），且 P0～P3、議題中心既有 AT 全綠（斷言值只在 §2.5 站點改）。
- [ ] `python tools/selfimproving.py check` 對真 repo rc 為 0（35 項，`CHECK_RULES_REV` 為 5）；`params.json` 41 鍵；`status` 16 鍵；動詞 26 個；能力登記 59（或 60）鍵且分類計數與 R160 一致。
- [ ] NFR-P4-10 閘門清單 (1)～(12) 逐項輸出貼入（ruff、LOC 分級、onboarding 基線快照、官方根層全套 unittest 多 CPU 模式、字面 ID 掃描）。
- [ ] QA 獨立審查：突變驗證（對 `sched` 的格邊界、`decide_skip` 判序、`unattended.gate` 真值表、commit 白名單、金鑰面各做至少一個突變並確認對應 AT 轉紅）；斷言強度審查（不接受「rc 為 0」單獨作為判準的 AT）。
- [ ] 範圍守衛：AT-440-8-1 綠；`schedule_backend.py`、`resume_route.py`、`unattended_authz.py`、`.claude/**` 零差異。
- [ ] 實跑檢核 V30～V35 由主控與掌舵者於真機完成並如實標記（出口 (a) 真實到期巡邏、(b) Console 兩種寫入真機入帳、(c) Console `approve` 被自動入帳並推進到 `verify`、(d) 停用 OS 任務後 `overdue` 翻 true、(e) git 歷史對 DEC 對帳含巡邏器 commit、(f) `unmeasured` 額度帶確實跳過）；未達成者標「未達成（前置未成立）」，不以構造資料充當。
- [ ] 重釘儀式（護欄層行數棘輪、`tools/tests` 檔數下限與 E501 棘輪、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE`、compat-ci `paths`）由主控單人窗口於同一 commit 收齊。
- [ ] Console 半鍵 `agentconsole-si-schedule` 的 **RELEASE** 以本鍵 RELEASE 為前置；其 PKG-BE 於根層 SCHED 棒 commit 後即開工並先交付黃金檔 G6～G9（D-IMP-1），AT-437-1-3 於主控以根層 CLI 收下黃金檔後全綠——本鍵 RELEASE 前 105 AT 必須全綠（不得以 Console 未交付為由留紅）。

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（留空）
