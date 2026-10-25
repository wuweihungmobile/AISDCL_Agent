# Test Contract Specification — SelfImproving P3（採納量測窗與回滾偵測、劣化暫停、退役欄位與抖動防護、容量事件、量測腳本與判準指紋、`measure` 與 `capacity` 動詞、`mea.*` 欄位表）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（PRD v0.10 與研究方法 SOP 於 Stage-1 凍結）的單一 Feature（P3 階段）；單一 FSM 功能鍵 `monorepo-si-p3-measure-retire`（`spec-frozen --doc` 指向本檔）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P3-20261024.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-004 |
| **Feature 名稱** | SelfImproving P3：採納後量測窗（機會列、基線窗、再現歸屬、`pending`、`mea.amend`）與回滾偵測、SUSPENDED 劣化暫停的重釘、`measure` 與 `capacity` 兩個動詞、量測腳本（M1～M5、資訊欄、判準指紋）、退役欄位與抖動防護、容量事件與截斷風險、`mea.*` 事件欄位表與 `check` 追加項、`status`／`export` 增量、Operations SOP〈P3 動詞〉定稿、承接 DEF-200-568 的 Console 載體三動詞寫入前判準 |
| **User Story** | US-301～US-307 |
| **建立日期** | 2026-10-24 |
| **QA 負責人** | SelfImproving P3 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝Developer 棒加主控〔收尾、真實運轉、重釘儀式〕，三方不同） |
| **FSM 功能鍵** | `monorepo-si-p3-measure-retire`（PRD §9.6 P3 列；開工先做 BRIDGE §8.4 基線採納） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（上位文件＝`docs/01_requirements/SelfImproving_PRD.md`〔v0.10〕與 `docs/05_development/SelfImproving_Research_Methodology_SOP.md`）的單一 Feature。未列入追溯表視為未滿足；引用不得指向未凍結文件。**凍結檔不得再改**：PRD 需修訂處一律寫在 §7 的 ⚖ 清單與〈PRD 修訂建議〉；PRD 未定而本檔為使其可測補定義者標「本檔類推」並列入 §7.1。**體例沿 P2 TCS**（`docs/03_testing/contracts/TCS-SelfImproving-P2-20261021.md`）：AT 格式、斷言簡寫（`M`、`MJ`、`snap`、`surface`、`codes`、`draft_ok`、`S`、`F`）、驗收字樣、判定指令與 `-k` 錨定規則、hermetic 環境、零殘留的定義一律「沿 P2 TCS §2 開頭」，本檔不複寫。

### FRD-lite

**現況與變更（Before／After；brownfield）**

- Before：(1) P0～P2 已 RELEASE：`tools/selfimproving.py` 21 個動詞，`check` 32 項（`CHECK_RULES_REV` 3），`params.json` 30 鍵，能力登記 `CAPABILITY` 40 鍵（29 `ro`／7 `rw`／2 `net`／2 `exec`）；(2) `events.KINDS` 已含四種 `mea.*`，但只有被消費鍵的型別檢查（`events._CONSUMED`）；`fold` 已折疊 `mea.open`→`measuring`、`mea.close`→`closed`（`pending` 維持 `measuring`）、`mea.amend` 記入生效結果、SUSPENDED（連續 `stop_after_bad` 個壞窗、其後無 `dec(resume)`），但 `mea.amend` 不校驗、`pending` 經 amend 落定後 PROP 仍停在 `measuring`、`mea.report` 一律要求 `prop`；(3) 不存在：任何 `mea.*` 的寫入者、機會列／基線窗／再現歸屬的實作、`measure`、`capacity`、量測腳本、退役欄位判準、抖動判準；`status.capacity` 恆印 `capacity-verb-not-established`；PROP 本文欄位表的 `retire_when`、`reopen_symptom` 兩鍵（P1 digest 已綁定）無人判其形態，也無人要求非 M 類帶它們（P1 只對 M 類判 `retire_when` 非空）；(4) 真帳本只有一筆 PROP（PROP-SI-004，`proposed`），無任何 promoted PROP、`mea.*` 為零（`python tools/selfimproving.py status` 現查）。
- After：新增 7 支套件模組（`ro`：`mea`、`meastat`、`meacheck`、`capacity`、`retire`、`churn`；`rw`：`meawrite`；另可選 `meaplan`〔`ro`，D1〕）、2 個動詞（`measure`、`capacity`，共 23 個）、任何 action 的 `prop-new`／`prop-revise` 之本文退役欄位判準（無新 CLI 旗標，R127）、`attr-confirm`／`attr-reject` 於落定後同鎖追加 `mea.amend`（R121 (e)）、探針 `tools/probe/selfimproving_measure.py`；`check` 追加 `events.mea` 共 33 項（`CHECK_RULES_REV` 4）；`params.json` 加 `memory_index_max_lines`（200）與 `memory_index_max_bytes`（25600）共 32 鍵；能力登記 47 鍵（35／8／2／2；可選 `meaplan` 存在時為 48 鍵 36／8／2／2，R132）；`fold`、`status`、`export`、`card`、`props`、`defs`、`evwrite`、`writeverbs` 的小幅增量；SOP〈P3 動詞〉；D12（承接 DEF-200-568）：`consoleaudit.py` 的新純函式 `body_guard`，由 `decwrite.py`、`obswrite.py`、`obsrows.py` 於既有本文判準呼叫（Console 載體三動詞的寫入前判準，R136；Before 的缺口＝P2 碼收下壞稽核檔、事後 `check` 才紅）；PRD §8.1 P3 出口 (a)～(d) 的真實運轉列為實跑檢核 V22～V26。
- **本檔不含**：AgentConsole 三層（P1b、P2b）、P2 的真實運轉 V8／V9／V15（P3 出口 (b) 以其真實晉升為前置，§7.2）、KB 與偏好的退役提案（PRD §9.7 #23：MVP 只印報告）、對 SDD `set_maturity` 的實呼叫（只在卡面與 SOP 提示）。

**AC 編號規則**（沿 P2 TCS〈AC 編號規則〉1、4，百位改 `3`）：PRD `AC-SI-NN-Y`＝本檔 `AC-3NN-Y`（`AC-SI-22-1`→`AC-322-1` … `AC-SI-27-2`→`AC-327-2`）；本檔自增 AC 自 `AC-340-1` 起（PRD 階段前綴形 `AC-P3-040-1`），與 P2 的 `AC-240-x` 不衝突；AT 文法 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，負控／邊界 `AT-<NNN>-<Y>-E-<n>`，同一 AC 的 AT 序號超過 9 改兩位序號（`E-10` 起），判定指令的 `-k` 一律為錨定名（AT 底線形接結尾底線）。**AC 數**：PRD 13 個（FR-SI-22 三、23 二、24 二、25 二、26 二、27 二）加自增 10 個（`AC-340-1`～`AC-340-10`，後者承接 DEF-200-568）合計 23 個；§1 共 78 個 AT（正控 35、負控 43）。

**P3 交付物**（D1～D14；D12 為主控追加項，承接 DEF-200-568）

| 編號 | 交付物 | 路徑（相對 monorepo 根） | 製作者 | 主要驗證 |
|------|--------|--------------------------|--------|----------|
| D1 | 列宇宙、機會列、再現歸屬、基線窗、採納窗、規劃（`mea`）；M1～M5 與反證條件的聚合（`meastat`）；`defs.py` 的 `DefRow` 增唯讀欄 `status_text`（狀態欄原文，供 M2、M3 取 `fixed@<sha>`；`classify_status`、`load_ledger_status` 回傳不變；斷言行 ≤+8） | `tools/lib/selfimproving/{mea,meastat}.py`（新，ro）、`defs.py`（改）；可選 `meaplan.py`（新，ro；僅當 `mea.py` 斷言行將超過 380 時，Developer 把 `plan` 與 amend 校驗整段拆出，**擇一、不得並存**，R132） | Developer | AC-323-1、AC-322-1 |
| D2 | `meawrite` 與動詞 `measure`（含 `--record-check`、回滾提案卡）；`meawrite.plan_amends` 供 `attr-confirm`／`attr-reject` 同鎖呼叫（R121 (e)）；`evwrite.append_event` 的 `build` 可回事件清單（R122 (g)） | `tools/lib/selfimproving/meawrite.py`（新，rw）、入口；`evwrite.py`（改，≤+12 斷言行，現 92）、`writeverbs.py`（改，≤+15 斷言行且總數 ≤400，現 377） | Developer | AC-323-1、AC-323-2、AC-340-2 |
| D3 | `capacity` 與動詞 `capacity` | `tools/lib/selfimproving/capacity.py`（新，ro）、入口 | Developer | AC-327-1、AC-327-2、AC-340-3 |
| D4 | 退役欄位判準（任何 action 的 `prop-new`／`prop-revise` 本文兩欄非空且過形態；`action=retire` 的目標須為已採納工件）、`card` 的 `set_maturity` 提示；**無新 CLI 旗標**（避免同一資訊兩個來源） | `retire.py`（新，ro）；`props.py`、`card.py`（改） | Developer | AC-325-1、AC-325-2 |
| D5 | 抖動防護與 capability-delta | `churn.py`（新，ro）；`props.py`（改；與 D4 合計 ≤+20 斷言行，現 258） | Developer | AC-326-1、AC-326-2 |
| D6 | 量測探針 | `tools/probe/selfimproving_measure.py`（新） | Developer | AC-322-1、AC-322-2、AC-340-6 |
| D7 | `events.mea` 與 `check` 接線、`CHECK_RULES_REV` | `meacheck.py`（新，ro）；`evcheck.py`、`check.py`、`params.py`（改） | Developer | AC-340-1 |
| D8 | `fold`／`status`／`export` 增量；`fold.py` 增量須使其 ≤400（現 363），**預排後備**：逼近時照 R114 (f) 把 amend 校驗整段搬進 `mea.py`（或可選的 `meaplan.py`） | `fold.py`、`status.py`、`export.py`（改） | Developer | AC-324-1、AC-324-2、AC-340-5 |
| D9 | 入口與登記：`measure`／`capacity` 子命令、`CAPABILITY` 47 鍵（可選 `meaplan` 時 48 鍵）、`PARAM_SPECS` 加兩鍵、`params.json` 兩鍵（**由 Developer 同棒與 `PARAM_SPECS` 同 commit 加入**，先例＝P2 Developer 同棒加 `probe_timeout_seconds`、`verify_runs_max`；`docs/06_quality/` 不在 hooks 保護面） | `tools/selfimproving.py`、`tools/tests/test_selfimproving_capability.py`、`params.py`；`docs/06_quality/SelfImproving_Protocol/params.json` | Developer | AC-340-4 |
| D10 | Operations SOP〈P3 動詞〉與提案者隔離條文 | `docs/05_development/SelfImproving_Operations_SOP.md` | Developer（文件作者） | AC-322-3、AC-340-7 |
| D11 | 出口 (a)～(d) 的真實運轉 | 真帳本（唯主控寫） | 主控；掌舵者 | V22～V26（不入 AT） |
| D12 | Console 載體三動詞的寫入前判準（承接 DEF-200-568：收下壞稽核檔、事後 `check` 才紅）：R136 的四個拒收碼；判準不改 `check`。**交付連動（主控處理）**：P2b TCS（W12）Console 側同判準的兩端防線，其碼表與 R136 的四碼逐一一致；根層收緊後 P2b 的 ⚖3 再開症狀「規則漂移」關閉 | `consoleaudit.py`（`body_guard`）、`decwrite.py`、`obswrite.py`、`obsrows.py`（改）；`tools/tests/test_selfimproving_console_obs.py`（既有檔，新增 AT 函式；既有函式僅限 R134 所列站點） | Developer；主控（連動） | AC-340-10 |
| D13 | P3 夾具與既有測試的同步站點（零退化；含 P1 夾具 `body_md` 預設加退役兩欄，R134 (f)） | `tools/tests/_selfimproving_p3_fixtures.py`（新）；既有 P0～P2 測試與夾具的 R134 站點（改） | Developer | AC-340-8 |
| D14 | AT 錨定可重跑檢查 | `tools/tests/test_selfimproving_p3_meta.py`（新） | Developer | AC-340-9 |

**提交順序與責任**

- 依賴序：D13（夾具與同步站點先行，否則既有測試的項數與鍵數斷言轉紅）→ D9 的 `PARAM_SPECS` 與 `params.json` 兩鍵（`capacity` 與 `status` 讀它們，故前移到 D3 之前）→ D8 的 `fold` 增量與 D7（欄位表與折疊同一把「事件重放」鎖，同一棒）→ D1 → D2 → D4、D5 → D3 → D8 的 `status`／`export` → D6 → D9 的入口與能力登記 → D10；D12 只動四個 Console 載體檔、與其餘各項無持有面重疊，可與上列任一段並行（同一棒內做亦可）。每支程式完成立即跑該區 AT，不累積（根 `CLAUDE.md` 共通紀律第 2 條）。
- **鎖的持有面不得拆給並行包**（鐵律七）：`fold.py` 的 amend 校驗、`meacheck.py` 的欄位表、`mea.py` 的窗規則是同一把「窗重放」鎖；探針與 `measure` 共用 `mea`／`meastat`（單一窗規則實作，R126 (d)），故 D1、D2、D6 的窗相關部分由同一棒做；`meawrite.plan_amends`、`evwrite` 的多事件追加與 `writeverbs.attr_settle` 的呼叫是同一把「同鎖追加」鎖（R121 (e)、R122 (g)），同樣由 D2 的同一棒做。
- 真帳本與真事件帳本只由主控寫（PRD C1）：Developer 棒不得碰真 OBS 帳本、真事件帳本與真 `SelfImproving_Proposals/`；AT 一律在 tmp 的合成 repo 內進行（`AUTOSDD_SI_DIR`、`CLAUDE_CONFIG_DIR` 指向 tmp），不讀真逐字稿與真 Claude 家目錄（唯一例外：AT-327-1-2 與 AT-340-6-E-2 唯讀引擎原始碼與真缺陷帳本）。重釘儀式（護欄層行數棘輪、`tools/tests` 檔數下限與 E501 棘輪、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE`、compat-ci `paths` 覆蓋）由主控單人窗口於同一個 commit 收齊，實作者不碰鎖檔（NFR-P3-8）。

**〈P3 行為規則〉**（R111～R136；各 AT 以 R 編號引用；P0 的 R1～R26、P1 的 R27～R67、P2 的 R68～R110 在其範圍內不變，P3 的重定與擴充見 R114〔`fold`〕、R115〔`check` 項數與判準版本〕、R121 (e)〔`attr-confirm`、`attr-reject` 的同鎖追加〕、R130〔`status`、`export`〕、R131〔`params`〕、R132〔能力登記〕、R134〔既有測試同步站點〕、R136〔Console 載體寫入前判準，補強 P2 R94～R97〕）

*A. 介面、rc 與輸出（PRD §9.3；旗標細部為本檔類推，§7.1 ⚖ 14）*

- **R111 兩個新動詞與其旗標**：P2 的 21 個動詞語意不變（唯 `attr-confirm`、`attr-reject` 於 `link` 型 `attr` 落定後多一次同鎖追加 `mea.amend`，R121 (e)）；加 `measure`、`capacity` 共 **23 個**，頂層 usage 列出 23 個動詞；凡未列動詞名一律 rc 3、stdout 空、stderr 至少一行。共通旗標 `--repo DIR`、`--json` 沿 P1 R27。

| 動詞 | 旗標（＊必備） | 讀寫與事件 | rc |
|------|----------------|------------|-----|
| `measure` | `--by <標籤>`（預設 `main`）、`--record-check` | 寫事件：只准 `mea.report`、`mea.open`、`mea.close`、`mea.amend` 四種 | 0＝已重算（有無新事件皆 0）、1＝拒收（未寫）、3＝用法或輸入錯誤 |
| `capacity` | `--memory-index <路徑>`、`--kb-metrics <路徑>`、`--prefs <路徑>` | 唯讀，不寫事件、不寫 OBS 帳本、不建立家目錄 | 0＝已執行（含 NE 與觸發）、3＝無法執行 |

  rc 通則沿 P1 R27／P2 R68：用法錯誤（rc 3）先於一切；`measure` 於 `AUTOSDD_UNATTENDED` 存在且值非空（含字面 `0`）時一律 rc 1、碼 `UNATTENDED-REFUSED`、**零寫入**、先於其他 rc 1 前置檢查（沿 P2 R70；`capacity`、探針、`status`、`export` 唯讀、不受限）；`measure` 需要家目錄可寫（鎖檔；沿 P1 R29，不可寫＝rc 3 `HOME-UNWRITABLE`、不退回暫存），`capacity` 與探針不建立、不要求家目錄。
- **R112 `measure` 的輸出**：成功文字＝首行 `ok measure events=<N> props=<M>`（N＝本次追加事件數、M＝本次檢視的 promoted PROP 數；PROP＝有 `app.promote` 者），其後每個有 `mea.open` 的 PROP 一行 `window <PROP> state=<measuring|pending|closed> result=<生效結果或 -> n_opp=<n>/<w_opp> baseline=<events>/<opp 筆數>`（依 PROP 號升冪），再後（有才印）每個需回滾卡的 PROP 一個區塊（R123）；帶 `--record-check` 另印一行 `check-report appended=<true|false>`。`--json`＝單一物件，鍵序 `ok`、`kind`（字面 `measure`）、`events`、`props`、`appended`（`[{"seq","kind","prop"}…]` 依 `seq`）、`windows`（鍵 `prop`、`state`、`result`、`n_opp`、`w_opp`、`baseline`〔`{"events","opp_n","pending"}` 或 null〕、`unsettled`）、`rollback_cards`（`[{"prop","text"}…]`）、`check_report`（`{"appended": 布林}`；未帶旗標為 null）。拒收（rc 1）與用法錯誤（rc 3）的輸出文法沿 P1 R28 (b)(c)(d)，含 `obs-draft:` 與一行草稿列。

*B. 事件欄位表、折疊與 `check`（PRD §9.2、§5.1.2、§9.3）*

- **R113 `mea.*` 欄位表**（共通鍵 `seq`、`t`、`kind`、`by` 之外；判準住 `meacheck`，**不改** `events.validate`：P2 的 `_CONSUMED` 型別檢查與 `sound()` 語意原樣；表外鍵＝`MEA-KEY-UNKNOWN`、缺必備鍵＝`MEA-KEY-MISSING`、型別或值域不合＝`MEA-TYPE`、列舉外＝`MEA-ENUM`）：

| kind | 必備鍵與型別 | 條件與值域 |
|------|--------------|------------|
| `mea.open` | `prop`（PROP ID）、`w_opp`（整數 ≥1）、`promote_seq`（整數 ≥1） | `w_opp`＝開窗當下 `params.json` 的值（窗內不隨參數改動）；`promote_seq` 須等於該 PROP 的 `app.promote` 的 `seq`（`MEA-PROMOTE-SEQ`） |
| `mea.report`（`report`＝`baseline`） | `prop`、`report`、`promote_seq`、`opp`（OBS 或 DEF ID 清單，長度 ≤ `w_opp`，依窗序）、`events`（整數 ≥0）、`pending`（整數 ≥0）、`w_opp`、`w_evt`、`w_min`（整數 ≥1）、`anchor`（帶 offset 的秒精度 ISO 8601 或 null） | 每 PROP 至多一筆（`MEA-BASELINE-DUP`）；其 `seq` 介於該 PROP 的 `app.promote` 與 `mea.open` 之間（`MEA-BASELINE-ORDER`） |
| `mea.report`（`report`＝`check`） | `report`、`fingerprint`（`sha256:` 接 64 位 hex）、`metrics_rev`（整數）、`windows`（整數 ≥0，可評估採納窗數）、`m1_n`（整數 ≥0）、`m1`（數值 0～1 或 null）、`m4`（整數 ≥0 或 null）、`m5_main`、`m5_all`（數值 0～1 或 null）、`m5_n`（整數 ≥0）、`falsified`（布林或 null）、`missing`（字串清單，每項 ≤60 字元、至多 20 項、排序去重） | **不得有 `prop`**（全域紀錄） |
| `mea.close` | `prop`、`result`（`clean`、`recurred`、`rolled-back`、`pending`）、`n_opp`（整數 ≥0）、`at`（帶 offset 的秒精度 ISO 8601＝關閉時點，R120） | `n_opp` ≤ 該窗 `mea.open.w_opp`；`result` 為 `clean` ⇒ `n_opp` 等於 `w_opp`（`MEA-CLOSE-N`） |
| `mea.amend` | `prop`、`window`（整數 ≥1，該窗 `mea.close` 的 `seq`）、`from`、`to`（皆屬四值）、`cause`（整數 ≥1，觸發落定的 `attr.confirm` 或 `attr.reject` 事件的 `seq`） | 合法 `(from,to)` 僅 `pending→clean`、`pending→recurred`、`clean→recurred`、`rolled-back→recurred`；指向與轉移合法性由 `fold` 判（R114） |

  除 `report` 為 `check` 者外，任一 `mea.*` 的 `prop` 須在該事件之前已有 `app.promote`（`MEA-NOT-PROMOTED`；無 `app.promote` 者只報此碼、不另報 `MEA-PROMOTE-SEQ`）。`MEA-CLOSE-N` 以該 PROP 的 `mea.open.w_opp` 為比較值；該值缺或型別錯時不另報此碼（只報 `MEA-KEY-MISSING`／`MEA-TYPE`）。事件行仍受 `event_max_bytes` 限制。
- **R114 `fold` 的 P3 增量**（`fold.py` 現 363 斷言行，增量須使其 ≤400）：(a) `mea.report` 的 `report` 為 `check` 者不綁 PROP（不判 `TRANSITION-ORPHAN`、不改任何 PROP）；`baseline` 者沿 P1（PROP 須存在）。(b) `mea.amend` 校驗：`window` 須是**同一 PROP** 的 `mea.close` 的 `seq`、`from` 須等於該窗當時的生效結果、`(from,to)` 須屬 R113 的四個合法對；任一不合 ⇒ 該筆 amend **不生效**（生效結果不變）並記 `TRANSITION-ILLEGAL`（subject 為 PROP，經 `events.transitions` 呈現）。(c) 合法的 `pending→clean`、`pending→recurred` amend 使該 PROP 態由 `measuring` 轉 `closed`；其餘合法 amend 不改 PROP 態。(d) `Prop` 增 `promote_seq`、`promote_t`（`app.promote` 的 `seq` 與 `t`）、`ack`（其 `unverified_ack`）；`Folded.windows` 的元素增 `n_opp`、`at`（取自 `mea.close`）。(e) **SUSPENDED 折疊不改**（沿 P1 R35 (b)(c)：生效結果≠`pending` 的窗依 `mea.close` 的 `seq` 排序，最近連續 `stop_after_bad` 個皆 `recurred` 或 `rolled-back`，且其後〔`seq` 大於其中最後一個窗的 `mea.close`〕無 `dec(resume)`；所在運轉＝`seq` 小於該最後壞窗 `mea.close` 的最近一筆 `run.open`）；`prop-new`、`prop-revise` 於 SUSPENDED 拒收（P2 R93）；P3 以 AC-324-1、AC-324-2 重釘。(f) **後備（D8 預排，不走勘誤）**：`fold.py` 逼近 400 時，把 (b) 的校驗整段搬進 `mea.py`（Developer 依 R132 拆出 `meaplan.py` 時則搬進後者）的純函式並由 `fold` 呼叫（單一實作）。
- **R115 `events.mea`（`check` 第 33 項）與判準版本**：項目 ID `events.mea`，接在 `obs.console_audit` 之後；只讀事件（不讀 OBS／DEF 帳本、不呼叫 git）；FAIL 碼＝`MEA-KEY-MISSING`、`MEA-KEY-UNKNOWN`、`MEA-TYPE`、`MEA-ENUM`、`MEA-NOT-PROMOTED`、`MEA-PROMOTE-SEQ`、`MEA-BASELINE-DUP`、`MEA-BASELINE-ORDER`、`MEA-CLOSE-N`；事件帳本不在場＝nonblocking NE `CARRIER-NOT-ESTABLISHED`；無任何 `mea.*`＝PASS。`check` 共 **33 項**（P0 21＋P1 7＋P2 4＋本項），前 32 項的 id、順序、語意、碼原樣；**`CHECK_RULES_REV` 由 3 增為 4**。`mea.amend` 的指向與轉移合法、重複 `mea.open` 由 `fold` 以 `TRANSITION-ILLEGAL` 於 `events.transitions` 呈現，本項不重報（§7.1 ⚖ 13）。

*C. 量測窗語意（`mea.py`；AC-SI-23-1；PRD §1.3〈M1 判定細則〉；本檔類推的細節見 §7.1 ⚖ 4～7）*

- **R116 列宇宙與時刻**：(a) 列宇宙＝OBS 帳本主檔與 `…_archive*.md` 的合法九欄列，加缺陷帳本家族（`AutoSDD_Defect_Log*.md` 與兩個姊妹帳本）的 DEF 列；DEF 一律經 `defs.load_rows` 解析（不新增第二份解析器，ADR-SI-05）。(b) **instant**：OBS 列＝`時間` 欄起點（缺 offset 者取該帳本檔頭 `tz=`；檔頭缺＝該列不計入任何窗，計資訊欄 `unplaced_rows`）；DEF 列＝發現日期當天 `23:59:59+00:00`（日精度的保守化，等同 PRD「日精度的 DEF 列以日期對錨的 UTC 日期比較、同日者納入」）；DEC＝`decided_at`；`app.promote`＝其 `t`；**錨**＝`params.json` 的 `migration_base_sha` 的 committer 時間（`Git.commit_time`；sha 缺、非 commit 或 git 不可用＝錨不可用）。(c) 對某 instant `X`，列 `r`「之後」＝`instant(r) > X`、「之前」＝`instant(r) < X`，**同刻者兩側皆不屬**；DEF 因此對同日的晉升恆屬「之後」（入採納窗、不入基線窗）。(d) **窗序**＝（列上顯示的日期字面〔OBS 取 `時間` 欄的日期部分、DEF 取發現日期〕, ID 末段數字, ID 全文位元組序）升冪；「最近 `W_OPP` 筆」＝窗序最後 `W_OPP` 筆。(e) 列的證據路徑集合＝`rows.path_set(證據座標格)`（OBS 第 5 欄；DEF 的「現象與證據」欄；casefold、`/` 分隔）。
- **R117 機會列規則**（採納窗與基線窗共用）：對 promoted PROP `P`、列 `r`：(a) **非 M 類**：`P.target` 各路徑取 `posixpath.dirname` 後的最近公共目錄 `D`（casefold；單一檔＝其所在目錄；公共目錄為 repo 根＝空字串，此時任何有路徑的列皆在其下）；`r` 的證據路徑**任一**路徑 `p` 滿足 `p == D` 或 `p` 以 `D` 加 `/` 起頭 ⇒ 屬機會列（目錄名須整段相符：`docs/p3/areax/…` 不在 `docs/p3/area` 之下）；無路徑的列不計。(b) **M 類**：`r` 的已確認根因鍵集合（R118 (c)）與 `P` 的有交集，或 `r` 的證據格含 `P.target` 任一路徑的檔名（`posixpath.basename`，casefold 子字串）⇒ 屬機會列（條目標題的引用不判，⚖ 6）。(c) **再現優先**（PRD §1.3 (d)，本檔推廣到全部類別）：屬再現候選（R118）的列——經確認並歸屬於 `P` 者＝再現、**不算**機會列；經 `attr.reject` 駁回者回頭算機會列；歸屬於 `P` 而未決者暫不算；候選但歸屬於他 PROP 或不可歸屬者，對 `P` 視為一般列（依 (a)(b) 判）。(d) 窗重疊允許、各窗各自累計（同一機會列可同時算在兩個 PROP 的窗內）；再現只歸一個 PROP（R118 (d)）。
- **R118 再現候選、確認態與歸屬**：(a) **候選**＝帶再現標記的列（OBS 列的標記鍵 `reopens`，值為被再開列的 ID），或為某 `attr`（`type`＝`link`）事件之 `from` 的 OBS 列（P1 的 `attr link` 只要求 `from` 在帳本、不要求該列帶標記）；DEF 列的「現象與證據」欄含 `reopens:DEF-<號>` 字樣者亦為候選。(b) **確認態**以事件帳本 `attr`（`type`＝`link`，`from`＝該 OBS 列）的落定為準：有任一筆 `attr.confirm`＝**已確認再現**；其 link 全為 `attr.reject`＝**已駁回**；其餘（含沒有 link 事件）＝**未決**。DEF 列不能是 link 的 `from`（只收 OBS），故 DEF 側候選恆無確認態、也無根因鍵可歸屬，**不屬任何 PROP 的窗**（不造成 `pending`），只計資訊欄 `unattributable_candidates`（§7.1 ⚖ 5）。(c) **根因鍵**：列 `x` 的鍵集合＝所有 `type=root` 且 `obs` 含 `x`、並已被 `attr.confirm` 確認的 `attr` 的 `root_cause`——**基線計算（R119）時該 `attr.confirm` 的 `seq` 亦須小於 `SP`**（晉升之後才確認的根因鍵不回補基線，否則同一份基線隨執行時機而變）；`P` 的鍵集合＝其 `sources` 各列鍵集合的聯集（只認已確認者；與 `fold.prop_root_causes` 的差別）；候選 `N` 的鍵集合＝`N` 自身的鍵集合與被再開列〔有 link 取其 `reopens`，否則取標記值〕的鍵集合之聯集。(d) **歸屬**：候選 `N` 歸屬於 `P` ⇔ `N` 的鍵集合與 `P` 的有交集 ∧ `N` 在 `P` 的 R117 (a)(b) 涵蓋範圍內（不計 (c)）∧ `instant(N)` 在 `P` 的 `app.promote.t` 之後；符合者有多個 PROP 時**只歸 `app.promote` 的 `seq` 最大者**（最近晉升者）。暫判（未決）與定案（已確認）用同一個歸屬函式。
- **R119 基線窗與基線報告**（ADR-SI-05）：對 promoted PROP `P`（`app.promote` 的 `t`＝`TP`、`seq`＝`SP`）：(a) **`opp`**＝機會列（R117；再現優先於基線期改判為：候選的鍵集合與 `P` 的有交集且涵蓋者，截至 `SP` 已確認＝再現、未落定＝未決、已駁回＝一般列）中 `錨 ≤ instant < TP` 者的窗序最後 `W_OPP` 筆；錨不可用＝基線不可算（R122 (d)）。(b) **`events`**＝上述候選中截至 `SP` 已確認（`attr.confirm` 的 `seq` < `SP`）、且 `instant` 落在基線時間範圍者的筆數；基線時間範圍＝自 `opp` 窗序最前一筆的 instant（`opp` 不足 `W_OPP` 筆時自錨）起、止於 `TP`（不含）。(c) **`pending`**＝同範圍內截至 `SP` 尚無落定事件（無 `seq` < `SP` 的 `attr.confirm`／`attr.reject`）而鍵相交的 OBS 候選數（不計入 `events`）。(d) **確定性**：全部只由帳本內容、事件序與 `SP` 決定、不讀現在時刻；`measure` 晚於晉升執行得同一基線——晉升之後才到的落定事件不回補 `events` 與 `pending`（只會使基線偏低、偏向 NE，保守）。(e) `mea.report`（baseline）記 `promote_seq`＝`SP`、`opp`（ID，窗序）、`events`、`pending`、`w_opp`／`w_evt`／`w_min`（寫入當下的 `params.json`）、`anchor`（錨的 instant，秒精度）。
- **R120 採納窗的關閉**：(a) `mea.open` 之後，窗依下列「先到者」關閉（由 `measure` 寫 `mea.close`）：**再現**＝窗內（`instant > TP`）窗序最前的「已確認並歸屬於 `P`」的候選，時點＝其 instant；**回滾**＝該 PROP 最早的 `dec(rollback)`（`decided_at` > `TP`），時點＝其 `decided_at`；**滿窗**＝窗序第 `w_opp`（取 `mea.open.w_opp`）筆機會列，時點＝其 instant。取時點最早者；同刻優先序 再現 > 回滾 > 滿窗；三者皆無＝窗仍 `measuring`。(b) `result`：再現先到＝`recurred`；回滾先到＝`rolled-back`；滿窗先到＝此刻窗內（`TP < instant ≤ 時點`）仍有歸屬於 `P` 的未決候選 ⇒ `pending`，否則 `clean`。(c) `n_opp`＝時點之前（`recurred`、`rolled-back` 不含時點本身）的機會列筆數；`clean`、`pending` 恆為 `w_opp`。(d) `at`＝時點（秒精度、帶 offset；DEF 為日末 instant）。(e) 寫入後 PROP 態 `closed`（`pending` 維持 `measuring`，R114）；`mea.close` 不改寫、只追加 `mea.amend`。(f) 窗未關閉的 PROP 不計入 M5 分母、M1 維持 NE（不以暫值宣稱）。
- **R121 `pending` 落定、晚到確認與生效結果**：(a) **生效結果**＝以該 `mea.close` 的 `seq` 為 `window` 的最後一筆**生效** `mea.amend` 的 `to`，無則 `mea.close.result`。(b) **落定**：窗為 `pending`，且以當下事件帳本重判所得、歸屬於 `P` 並滿足 `TP < instant ≤ at` 的候選**集合非空且全數落定**（`attr.confirm` 或 `attr.reject`；零候選的 `pending` 窗不產出 amend）⇒ 追加 `mea.amend(from=pending, to=…)`：任一候選已確認 ⇒ `recurred`、全數駁回 ⇒ `clean`；`cause`＝使候選集合達全數落定的那一筆（`seq` 最大者）事件的 `seq`。(c) **晚到確認**：生效結果為 `clean` 或 `rolled-back`，且存在已確認再現 `N` 歸屬於 `P`、`instant(N) < at`、其最先的 `attr.confirm` 的 `seq` 大於該窗 `mea.close` 的 `seq` ⇒ 追加 `mea.amend(from=<生效結果>, to=recurred, cause=<該 attr.confirm 的 seq>)`；`instant(N) ≥ at`（再現在關閉之後）者不改該窗（「先到」一律比立案時刻、不比確認時間）。(d) 生效結果為 `recurred` 者不再 amend。(e) **寫入者**（PRD §9.3 attr 列與 AC-SI-23-1「同一把寫入鎖內追加」；主控裁決，⚖ 2）：`attr-confirm`、`attr-reject` 於**同一把寫入鎖內**、寫完 `attr.confirm`／`attr.reject` 之後，**僅當所落定的 `attr` 為 `link` 型**，呼叫 `meawrite.plan_amends(repo, events)`（`events`＝含該新事件的事件序列；OBS 帳本由 `meawrite` 自 `repo` 讀取，重算本條 (b)(c)；判準＝`mea.plan` 的 amend 分支，單一窗規則實作）並與該事件**同一次追加**所得的 `mea.amend`（R122 (g)）；**`root` 型 `attr` 的落定不產生 amend**（它只改根因鍵集合，R118 (c)，故 attr 動詞不在 `root` 落定時追加；若該落定使既有候選才歸屬於 `P` 而令本條 (b)(c) 條件成立，由下次 `measure` 補記，`status.measure.due` 先為 1——預期行為）；`plan_amends` 讀不到 OBS 帳本（於 `meawrite` 內處理）或無任何窗時回空清單、**不使 attr 動詞拒收**；P0～P2 無 `mea.*` 的情境恆回空清單（零退化）。`measure` 仍為**冪等補記者**：`mea.plan` 見到尚未追加的 amend（attr 路徑因輸入不可用、手寫的確認事件或替身而未追加）照追加；兩路徑所得的 `mea.amend` 除 `seq`、`t`、`by`（attr 路徑取該動詞的 `--by`）外逐鍵相同（確定性）。
- **R122 `measure` 的規劃與冪等**（ADR-SI-10）：(a) **規劃函式** `mea.plan(ctx)`（純函式；`measure`、`status.measure.due`、`measure --record-check` 與探針共用，不得有第二份窗規則）：依 PROP 號升冪、對每個 promoted PROP 產出下一個應追加的事件——無 baseline ⇒ `mea.report(baseline)`；無 `mea.open` ⇒ `mea.open`；窗 `measuring` 且 R120 條件成立 ⇒ `mea.close`；窗 `pending` 或已關閉且 R121 條件成立 ⇒ `mea.amend`。(b) **逐事件鎖內重算**：反覆「取寫入鎖 → 以鎖內最新事件帳本與當下 OBS／DEF 帳本重算 plan → 追加 plan 的第一個事件（單次完整行追加）→ 放鎖」直到 plan 為空；追加數超過 `5×(promoted PROP 數)` ＝rc 1 `MEASURE-NOT-CONVERGING`（零額外追加）。(c) **冪等**：第二次呼叫 plan 為空、不寫任何位元組（rc 0、`events=0`），輸出仍列各窗狀態。(d) **輸入不可用 fail-loud**（不寫出不可恢復的 NE 基線）：plan 含 baseline 事件而錨不可用 ⇒ rc 1 `ANCHOR-UNAVAILABLE`；plan 含任何事件而 OBS 帳本不存在或不可解析 ⇒ `OBS-LEDGER-UNAVAILABLE`；缺陷帳本家族無任何檔 ⇒ `DEFECT-LEDGER-UNAVAILABLE`；皆零寫入並印草稿列；無 promoted PROP 或 plan 為空時不需任何輸入、rc 0。(e) **`--record-check`**：收斂後以 `meastat.metrics` 算 M1～M5 與反證（同探針）；與最近一筆 `mea.report(check)` 的內容（除 `seq`、`t`、`by`）逐鍵相同 ⇒ 不追加；否則追加一筆（`fingerprint`＝R126 (c)、`missing` 列各 NE 的缺什麼碼）；無任何 promoted PROP 時仍追加（NE 也留紀錄並寫缺什麼，出口 (d)）。(f) `measure` 不寫非 `mea.*` 事件、不改 OBS／DEF 帳本與工作樹（`git status --porcelain` 的差異只有事件帳本）、不 commit、不接任何閘門。(g) **多事件追加**（R121 (e) 的承載）：`evwrite.append_event` 的 `build(state)` 除回單一事件 dict（P1 行為與回傳值不變）外，可回事件 dict 清單——依序配連續 `seq`、`event_max_bytes` 逐行判（任一行超限＝整批拒收、零寫入）、同一把鎖內以單次 `os.write` 追加（全有或全無）、回傳首筆事件的 dict；`evwrite.py` 增量 ≤+12 斷言行（現 92）。
- **R123 回滾提案卡**（AC-SI-23-2；本檔類推，⚖ 3）：(a) 每次 `measure` 為**每個**「生效結果為 `recurred` 且尚無 `dec(rollback)`」的 promoted PROP 印一個區塊（狀態導出：重跑重印，直到掌舵者以 `回滾` 決定；僅有未決候選的窗＝`pending`，只在 `status` 印候選數、不印卡）。(b) 區塊第一行 `[<PROP>] 回滾提案｜窗：recurred｜digest：<8 碼>`；核心區（至分界線 `--- 以下不計入核心區 ---` 之前）≤12 行、每行顯示寬度 ≤ `card_line_max`（沿 `card` 的寬度函式）：一、再現（再現列 ID 與其證據座標、對應 `ATT-SI-N` 與確認者）；二、已採納（`touched` 檔數、`app.promote` 的 `seq`）；三、回滾配方（`rN.md` 欄位 `rollback` 的原句；`rN.md` 讀不到＝印 `量不到` 與碼，不編造）；分界線之下一行 `決定：回滾 <PROP> <一句理由>`（取 `決定：` 之後、以一句理由代入，須被 `decgrammar.parse` 解析為動詞 `回滾`）。(c) **絕不自動回滾**：`measure` 不寫 `dec`、`app.rollback`，不改工作樹；回滾只在掌舵者打字 `回滾 PROP-SI-NNN <一句理由>` 後經 P2 的 `decide --kind rollback` 與 `rollback` 執行。

*D. 量測腳本與指標（`meastat.py`、`tools/probe/selfimproving_measure.py`；AC-SI-22）*

- **R124 M1 與反證條件**：(a) **可評估窗**＝同時成立：窗已關閉且生效結果∈{`clean`,`recurred`}；該 PROP 有 `mea.report(baseline)`；其 `events` ≥ `W_EVT` 且 `opp` 筆數 ≥ `W_MIN`（取當下 `params.json`；`events` 為 0 一律不可評估，不得算「未低於」或「已改善」）。因再現提早關閉的窗（`recurred`）照樣可評估（不另設採納窗最小列數）。(b) **M1**（成功指標區）＝可評估窗中生效結果為 `recurred` 者的窗數 ÷ 可評估窗數，附 `n`（可評估窗數）與每 PROP 一列（`prop`、`result`、`events`、`opp_n`、`evaluable`、`reason`）；`n` 為 0 ⇒ NOT-EVALUABLE（不印 0、不印 0/0）。每 PROP 的 NE 理由碼（依序判、先中者）：`NO-BASELINE`、`WINDOW-OPEN`、`WINDOW-PENDING`、`ROLLED-BACK-NO-RECURRENCE`（生效結果仍為 `rolled-back`：M1 不評估、仍計 M5）、`BASELINE-EVENTS-BELOW-W-EVT`、`BASELINE-ROWS-BELOW-W-MIN`；M1 只讀已記的基線報告，錨不可用只影響全域窗（`info.global_m1` 的 `reason` 為 `anchor-unavailable`），不影響 M1。(c) **反證條件**（§1.1）：對每個根因鍵 `k`，取鍵集合含 `k` 的 PROP 的可評估窗，依 `mea.close` 的 `seq` 排序（NE 窗與 `pending` 窗不計入也不打斷）；存在相鄰兩個皆 `recurred` ⇒ `k` 列入 `falsified_keys`；`falsified`＝有任一鍵為真則 true、無可評估窗則 null（`missing` 寫缺什麼）、其餘 false；**只印、不自動下線**（T1 決策項）。(d) **全域窗**（資訊欄）＝窗序最後 `W_N` 筆「處置或狀態首詞為 `fixed`」之列（OBS 處置首詞 `fixed@…`、DEF 狀態分類 `fixed`；僅錨之後）中已確認再現者（某已確認 link 的 `reopens` 指向該列）的比例，附 n；n < `W_MIN` ⇒ NE（`sample-below-w-min`）；不得單獨宣稱成效。
- **R125 M4、M5 與資訊欄**：(a) **M4**（成功指標區）＝`fold` 的 `COOLDOWN-BYPASS-SUSPECT` 筆數（冷卻中又出現同型 PROP；離線不判 (b-2) 新證據，故為上界，⚖ 8）；事件帳本不在場 ⇒ NE `carrier-not-established`；每筆附一列 OBS 草稿列（只印、不寫）。(b) **M5**（成功指標區）＝兩值**並列**、各附 n：分母＝窗已關閉（生效結果≠`pending`）的 promoted PROP；分子＝其中有 `dec(rollback)` 且 `decided_at` ≤ 該窗 `mea.close.at` 者（窗內被回滾）；窗後的回滾不計分子、另列資訊欄 `late_rollbacks`；`m5_main`＝只含 `unverified_ack` 為假的 PROP、`m5_all`＝含全部；各自 n < `W_MIN` ⇒ NE（不印 0；理由碼 `sample-below-w-min`，事件帳本不在場為 `carrier-not-established`，與 M2、M3、全域窗同一碼族）；分子取 `dec(rollback)` 的事實，不隨窗結果標籤改判而變；不機械判趨勢（`m5` 物件只含 `main`、`all` 兩值，鍵見 R126 (b)，無趨勢、門檻或判定鍵）。(c) **資訊欄**（與成功指標分區）：提案數（不同 PROP ID 數）、決定分佈（各 `dkind` 的 `dec` 筆數）、OBS 列數、`closed-by-decision` 數（DEF 狀態分類）、未驗採納數、`late_rollbacks`、`unplaced_rows`、`unattributable_candidates`、**M2**（DEF 列〔狀態欄原文取 `DefRow.status_text`〕`fixed@<sha>` 的 commit 時間〔UTC 日〕減發現日期的整日差中位數；sha 經 `Git.commit_time` 解析，無法解析者排除並計 `excluded`；n < `W_MIN` ⇒ NE；`closed-by-decision` 另計數）、**M3**（已確認再現列的修復時間：其處置為 `fixed@<sha>`，或為 `DEF-<id>` 而該 DEF 列的 `status_text` 含 `fixed@<sha>`；修復 commit 時間減該列發現日期的整日差中位數；無法解析者排除並計數；n < `W_MIN` ⇒ NE）、全域窗 M1（R124 (d)）。
- **R126 探針形態與判準指紋**（C11）：(a) `python tools/probe/selfimproving_measure.py [--repo DIR] [--json]`（不帶 `--repo`＝本檔所在 repo；任何 cwd 皆可執行）；rc 0＝已輸出（NE 不是錯誤，rc 不隨指標值或反證結果改變）、3＝無法執行（未知旗標；`--repo` 不是目錄；`params.json` 的 `w_opp`、`w_min`、`w_evt`、`w_n`、`metrics_rev` 缺或無效，stderr 點名、不以預設值頂替）。(b) 輸出（零 token、不連網、不呼叫模型、不寫任何檔、位元組直寫 UTF-8 LF；同一 HEAD 與工作樹重跑逐位元相同）：JSON 單一物件，鍵序 `schema_rev`（1）、`fingerprint`、`fingerprint_parts`（`manifest`、`metrics_rev`）、`head_sha`、`params`（`w_opp`、`w_min`、`w_evt`、`w_n`）、`success`（`m1`、`m4`、`m5`）、`info`（鍵見下）、`falsification`（`falsified`、`falsified_keys`、`missing`）、`ne`（`[{"field","reason"}…]`）；**各物件鍵表**（AT 用到的鍵皆在此；量值物件恆帶 `status`，可評估者為 `read`，量不到者為 `NOT-EVALUABLE` 且帶 `reason`、不帶 `value`）：`m1`＝`status`、`n`（可評估窗數）、`recurred`（其中生效結果為 `recurred` 的窗數）、`value`（`recurred` 除以 `n`）、`per_prop`（R124 (b) 每 PROP 一列：`prop`、`result`、`events`、`opp_n`、`evaluable`、`reason`），NE 的 `reason` 為 `no-evaluable-window`（事件帳本不在場為 `carrier-not-established`）；`m4`＝`status`、`value`、`drafts`（OBS 草稿列字串清單，每筆一列）；`m5`＝只有 `main`、`all` 兩個物件，各為 `status`、`value`、`n`（NE 時為 `status`、`reason`、`n`，`reason` 見 R125 (b)）；`info`＝`proposals`（提案數）、`decisions`（`dkind` 到筆數的物件）、`obs_rows`、`closed_by_decision`、`unverified_ack`（未驗採納數）、`late_rollbacks`、`unplaced_rows`、`unattributable_candidates`、`m2`（`status`、`value`、`n`、`excluded`）、`m3`（同 `m2`）、`global_m1`（`status`、`value`、`n`；NE 時 `reason` 為 `sample-below-w-min` 或 `anchor-unavailable`）；文字形態以標題行分區：`== 成功指標 ==` 之下只有 M1、M4、M5（M5 兩值並列），`== 資訊欄 ==` 之下其餘，末行 `fingerprint=<值>`；量不到的欄位一律印 `NOT-EVALUABLE（<碼>）`，絕不印成 0 或綠。(c) **判準指紋**＝`sha256:` 接 `{"manifest","metrics_rev"}` 兩鍵（鍵序排序、`separators=(",",":")`）JSON 的雜湊；manifest 取 `params.fingerprint` 的同一份實作（協定目錄各檔 CRLF→LF 後雜湊，排除 `research_sources.json`）；**不含** `check_rules_rev`；改 `params.json`、`metrics.md` 任一位元組或 `metrics_rev` 皆改指紋；不同指紋的數字不得並列於同一份輸出。(d) **單一窗規則實作**：探針只經 `lib.selfimproving.{mea,meastat,defs,params,events,fold,refs,git,rows,ledger}` 取得窗與指標，不自寫窗、歸屬或指標邏輯（以 import 關係與對 `measure` 的差分 AT 釘住）；DEF 解析只經 `defs`，並以差分測試對 `tools/check_defect_log_crossref.py` 的 `_load_ledger_status` 釘「同批列給同組（ID, 結案類）」。(e) **純度**：探針原始碼不含 `subprocess`、網路模組、模型客戶端字樣、寫入形原語；git 只經 `Git`；不讀 `AUTOSDD_*` 與金鑰環境變數。(f) **不接閘門**（AC-SI-22-2）：`.github/workflows/`、`tools/git-hooks/`、`.claude/settings.json` 不含字面 `selfimproving_measure`。

*E. 退役、抖動與容量（AC-SI-25～27）*

- **R127 退役欄位與目標**（`retire.py`；PRD AC-SI-25-1「任一已採納工件」；主控裁決：沿 P1 本文欄位、不增 CLI 旗標，故原 ⚖ 11 取消）：(a) **範圍**：**任何 `action`** 的 `prop-new` 與 `prop-revise`，其本文欄位表（P1：標題含「欄位」之節的第一個表）都須有 `retire_when`、`reopen_symptom` 兩鍵且值非空（去前後空白後非空；缺或空 ⇒ rc 1、碼 `RETIRE-FIELD-MISSING`，detail 點名鍵；兩鍵已綁進 digest，P1 R55 (a)）；M 類的 `retire_when` 缺或空仍由 P1 的 `M-FIELD-MISSING` 判、本條不重報，其餘情形（M 類的 `reopen_symptom`、非 M 類的兩鍵）一律由本條判。**不新增 CLI 旗標**（避免同一資訊兩個來源）：舊形態 `--retire-when`、`--reopen-symptom` 為未知旗標 ⇒ rc 3。(b) **形態**（純函式 `retire.form_problems(text)`，對兩鍵的值各判一次；**只判非空值**——去前後空白後為空者由 (a) 的 `RETIRE-FIELD-MISSING` 判，`form_problems` 對其回空清單，不雙報）：「一句」＝不含換行；不得含輪號（`(?<![A-Za-z0-9])R\d+` 或 `improving_\d+`）、日期（`\d{4}-\d{2}-\d{2}`）、字面「待排程」，任一 ⇒ rc 1、碼 `RETIRE-FIELD-FORM`（detail 點名鍵與成因；`PR123`、`ROW-MUTATED` 這類非輪號字樣不誤殺）；判準住 `retire.py`，由 `props` 的階段一前置檢查（與 `BODY-FIELD-*` 一併收集）呼叫。(c) **已採納工件**（階段二政策碼）：`action=retire` 的 `prop-new`／`prop-revise`，其 `target`（casefold 的路徑集合）的**每個路徑**都須「在役」——存在 promoted 的 PROP（`app.promote` 已記、且無針對它的 `app.rollback`）其 `target` 含該路徑，且在這些 PROP 中**最近晉升者（`app.promote` 的 `seq` 最大）的 `action` 不是 `retire` 也不是 `delete`**（最近晉升者為 `delete` 者視為不在役；WHY：已刪除的工件不再是採納中的工件，退役對象不存在）；否則 rc 1、碼 `RETIRE-TARGET-NOT-ADOPTED`（detail 列未採納的路徑；patch 能否套用由 `verify` 判）；從未採納、已退役或已刪除而未再新增、或其採納已被回滾的路徑皆不在役（退役被回滾則回到在役；`A1 R1 A2` 之後 `A2` 為最近晉升者，故路徑再度在役）。(d) 非 `retire` 的 PROP 只受 (a)(b)。(e) 退役走同一 K=1 閘：`action=retire` 的 PROP 由 `prop-new` 產生、態 `proposed`，只能經 P2 的 `decide`、`sandbox`、`verify`、`promote` 推進；本迴圈任何動詞不自動建立、核准或套用退役（只提議）。(f) **SDD 規則面提示**：`cls` 為 `R` 且 `action` 為 `retire` 的 PROP，`card` 於分界線之後加一行 `SDD 規則退役須經 set_maturity(reviewed_by=<人>)；本迴圈不呼叫 SDD 碼`（SOP 同句，R133）；套件原始碼不得有對 `set_maturity` 的呼叫，不得 import `rule_loader` 與 `fsm_runtime`。
- **R128 抖動防護與 capability-delta**（`churn.py`；`churn.codes(ctx)` 由 `props.evaluate` 呼叫，`props.py` 增量與 R127 合計 ≤+20 斷言行〔現 258〕；`writeverbs.py` 增量 ≤+15 斷言行、總數 ≤400〔現 377；R121 (e) 的 attr 同鎖呼叫〕）：(a) **群**＝promoted PROP 中 `target` 路徑集合相同、且根因鍵集合（R118 (c)）有交集或皆為空者；群內依 `app.promote` 的 `seq` 排序。(b) **循環數**＝群內「晉升的 `add`，其之前群內已有晉升的 `retire` 且該 `retire` 之後尚無其他 `add`」的筆數。(c) **`CHURN-EXCEEDED`**：`prop-new` 的新提案（`action=add`）落入某群、且該群最後一個晉升者為 `retire` 時，其將使循環數加 1；加 1 之後 > `churn_max` ⇒ rc 1、碼 `CHURN-EXCEEDED`（升級人工＝照常印 OBS 草稿列；與 `COOLDOWN` 等同屬階段二政策碼、與其他碼一併收集）。群的歸屬以新提案的 `target`（排序去重）與其 `sources` 的鍵集合判。(d) **`CAPABILITY-DELTA-MISSING`**：同一情形（再提已退役工件）下，新提案的 `sources` 須至少含一列「新證據」——instant 在該群最近一筆晉升 `retire` 的 `app.promote.t` 之後（R116 (c)），且其證據座標集合（`rows.coord_set`；DEF 取「現象與證據」欄）與該群全部既有 PROP 之 `sources` 各列座標集合的聯集**不相交**；無 ⇒ rc 1。(e) 兩判準只在 `prop-new`（rev 1）判，與 `cooldown`、`DUPLICATE-TYPE` 互不取代、可同時命中。
- **R129 容量**（`capacity.py`）：(a) 輸入全由旗標與 `params.json` 給：`--memory-index`（預設 `transcript_dir(repo)` 之下的 `memory/MEMORY.md`，即 `claude_home()/projects/<slug>/memory/MEMORY.md`）、`--kb-metrics`、`--prefs`；沒給旗標而預設路徑不存在，或給了而讀不到、不合形態 ⇒ 該軸 NOT-EVALUABLE（碼 `memory-index-missing`、`kb-not-supplied`、`kb-metrics-unparseable`、`prefs-not-supplied`、`prefs-unparseable`），不是 rc 3、不是零。(b) **記憶索引軸**：`bytes`＝檔位元組數、`lines`＝以 LF 切分的實體行數（末行無 LF 者亦計一行）；上限取 `memory_index_max_bytes`、`memory_index_max_lines`；用量比＝`max(bytes÷上限bytes, lines÷上限lines)`；≥ `cap_frac`（含等號）⇒ `over_cap`。(c) **KB 軸**：`--kb-metrics` 為 UTF-8 JSON 物件、鍵 `kb_cache_eviction_count`（整數 ≥0）；值 ≥1 ⇒ `over_cap`。**偏好軸**：`--prefs` 為 UTF-8 JSON 物件，鍵數＝用量，上限常數 `PREFS_MAX_KEYS`＝10，用量比 ≥ `cap_frac` ⇒ `over_cap`。常數 `KB_MAX_ENTRIES`＝1000 與 `PREFS_MAX_KEYS` 須等於 `AutoClaude/autoclaude/utils/knowledge_base.py` 的 `_MAX_ENTRIES` 與 `AutoClaude/autoclaude/plugins/preference_memory_plugin.py` 的 `_MAX_KEYS`（唯讀漂移鎖 AT）。(d) **退役／合併候選**（只記憶索引軸、只提議）：`over_cap` 時，**條目行**＝以 `- ` 起頭（行首無縮排）的行；自檔尾向前逐條取，至最小的 `j` 使 `lines − j + 1 < cap_frac × 上限lines` 且 `bytes − Σ被移除行位元組 + P < cap_frac × 上限bytes`（`P`＝被移除行中最長一行的位元組數，保守估一行歸檔指標）；全部取完仍不足 ⇒ 列全部並標 `insufficient: true`。候選依原序、**逐字**（含行尾空白與原行尾字元）、每 `max_archive_entries_per_card` 條切一張卡；不寫任何檔（歸檔走 M 類歸檔型 PROP，ADR-SI-06）。KB 與偏好 `over_cap` 時**只印容量報告與 OBS 草稿列**，不產候選、不產提案（PRD §9.7 #23）。(e) **OBS 草稿列**（`rows.draft_row`；只印、`check` 零 finding、≤ `row_max_bytes`）：記憶索引 `over_cap` ⇒ `process`／`P3`／`open`；KB 或偏好 `over_cap` ⇒ 各一列 `process`／`P4`／`open`。(f) **截斷風險**（AC-SI-27-2）：索引 `bytes` 或 `lines` 大於上限時，計「落在載入範圍之外的條目」＝條目行滿足「行號 > 上限lines」或「行的結束位元組偏移（含其 LF）> 上限bytes」者（被位元組上限攔腰截斷的條目亦計）；≥1 ⇒ 輸出 `truncation_risk`（條目數與首個行號）並印一列 `bug`／`P2`／`open`、症狀以「截斷風險：」起頭的草稿列（不得當成 harness 已處理而略過）；大於上限而其後只有非條目行＝無風險；恰等於上限＝無風險。(g) **輸出**：`--json` 單一物件，鍵序 `schema_rev`（1）、`cap_frac`、`memory_index`、`kb`、`prefs`、`retire_candidates`（`[{"card","lines","first_line","last_line"}…]`）、`truncation_risk`（物件或 null）、`obs_drafts`、`events_detected`（`[{"trigger":"e","subject","detail"}…]`）；各軸物件為 `{"status":"read","used","limit","frac","over_cap"}` 或 `{"status":"NOT-EVALUABLE","reason"}`；文字形態逐軸一行、末接候選卡與 `obs-draft:`。(h) rc 3 僅限：未知旗標、`params.json` 的 `cap_frac`、`memory_index_max_lines`、`memory_index_max_bytes`、`max_archive_entries_per_card` 缺或無效（stderr 點名、不以預設值頂替）、`--repo` 不是目錄。

*F. `status`／`export`、參數、能力登記、SOP 與零退化*

- **R130 `status` 與 `export` 增量**：(a) `status` 物件前 14 鍵的次序與語意不變（`capacity` 的值依 (b)），其後附加末鍵 `measure`（共 15 鍵）；文字形態加 `measure: due=<n> measuring=<k> candidates_unsettled=<m>`。(b) `capacity`＝`capacity.evaluate` 對**預設輸入**（只有預設路徑的記憶索引；KB 與偏好未供）的彙總：三軸皆 NE ⇒ `{"status":"NOT-EVALUABLE","reason":"no-axis-evaluable"}`；否則 `{"status":"read","axes":{"memory_index":…,"kb":…,"prefs":…},"over_cap":[軸名…]}`；任一軸 `over_cap` ⇒ `events_detected` 增一筆 `{"trigger":"e","subject":<軸名>,"detail":…}`（AC-SI-03-1 (e)）；文字形態維持 `capacity NOT-EVALUABLE（<reason>）` 前綴。(c) `measure`＝`{"status":"read","due":<n>,"windows":[{"prop","state","result","n_opp"}…],"candidates_unsettled":<m>,"rollback_pending":[<PROP>…]}`：`due`＝`mea.plan` 此刻的事件數；`windows` 為有 `mea.open` 的 PROP（依 PROP 號升冪），`n_opp` 於 `measuring` 為窗內目前機會列數、其餘為 `mea.close.n_opp`；`candidates_unsettled`＝歸屬於某 promoted PROP 的未決 OBS 候選數；`rollback_pending`＝生效結果為 `recurred` 且尚無 `dec(rollback)` 者；量不到 ⇒ `{"status":"NOT-EVALUABLE","reason":<carrier-not-established｜anchor-unavailable｜obs-ledger-unavailable｜defect-ledger-unavailable>}`（有 promoted PROP 需要而不可用者；無 promoted PROP 時為 `read`、`due` 為 0）。(d) `pending_windows`、`root_cause_changes`、`reopen_candidates`（`unsettled`＝未落定的 link `attr` 數）的鍵與值語意不變（P1 R60）。(e) `export --kind proposals` 的每個 PROP 物件於末鍵 `card` 之後加 `window`：無 `mea.open` ⇒ null；否則 `{"state","opened_seq","closed_seq","result","n_opp","baseline"}`（`baseline` 為 `{"events","opp_n","pending"}` 或 null）；`schema_rev` 維持 1。(f) `export --kind status` 的 `items[0]` 同 `status` 的 15 鍵，但 `capacity` 恆為 `{"status":"NOT-EVALUABLE","reason":"export-reads-no-home"}`（`export` 不讀家目錄與 Claude 家目錄；沿 P2 R99 (b)）。(g) 兩者唯讀、零寫入。
- **R131 `params.json` 與判準版本**：`PARAM_SPECS` 加 `memory_index_max_lines`（`int1`，初值 200）與 `memory_index_max_bytes`（`int1`，初值 25600；兩值皆「初值（未校準）」，S-08 的「前 200 行或 25KB」，25KB 換算未查證）共 **32 鍵**，頂層鍵依位元組序；缺、型別或範圍不符＝`PARAM-MISSING`／`PARAM-TYPE`／`PARAM-RANGE`（`params.keys` FAIL）；`capacity`、`status` 只讀所需鍵，無效＝rc 3 點名、不以預設值頂替。`params.json` 屬不可進化面（對迴圈提案者；`docs/06_quality/` 不在 hooks 保護面），由 Developer 同棒與 `PARAM_SPECS` 同 commit 加入（先例＝P2 Developer 同棒加 `probe_timeout_seconds`、`verify_runs_max`）；兩新鍵使指紋 manifest 部分改變（P3 之前無任何量測數字，故無歷史數字被拆散）；`metrics.md` 與 `metrics_rev` 不改；`CHECK_RULES_REV` 為 4（R115）。`non_evolvable_globs` 與 `spec_body_globs` 不變。
- **R132 能力登記與 LOC**：`CAPABILITY` 由 40 鍵增為 **47 鍵（35 `ro`／8 `rw`／2 `net`／2 `exec`）**（可選 `meaplan` 存在時為 48 鍵、36 `ro`，見末句）：新增 `mea`、`meastat`、`meacheck`、`capacity`、`retire`、`churn`（`ro`）與 `meawrite`（`rw`）；P2 R105 的判準 ①～④ 原樣適用：`check`、`status`、`scan`、`export`、`card` 的相對 import 閉包 ⊆ `ro`（故新增六檔必須是 `ro`）；`meawrite` 只在 handler 內延遲 import（入口的 `measure` handler 與 `writeverbs.attr_settle`；後者本身為 `rw`，R121 (e)）；`exec` 仍恰為 `runner.py` 與 `verify.py`；套件原始碼無 `set_maturity` 呼叫與 `rule_loader`／`fsm_runtime` 字樣。每個 `tools/lib/selfimproving/*.py` 斷言行 ≤400（`guardrail_lib`）、入口 `tools/selfimproving.py` ≤750；**可選 `meaplan.py`**（D 表的可選檔，不走勘誤；⚖ 15）：`mea.py` 斷言行將超過 380 時，Developer 得把 `plan` 與 amend 校驗整段拆出為 `meaplan.py`（`ro`），**擇一、不得並存**——不拆＝47 鍵（35／8／2／2），拆＝48 鍵（36／8／2／2）；AT-340-4-2 斷言鍵數屬 {47, 48}、登記鍵集合等於實際檔案集合、`ro` 數＝35＋（`meaplan.py` 存在則 1、否則 0）。
- **R133 Operations SOP〈P3 動詞〉與提案者隔離**（SOP-P3-REQ，§5.6）：SOP 加〈P3 動詞〉節（接在〈P2 動詞〉之後）：(a) rc 契約表補 `measure`、`capacity` 兩列（`measure` 列寫明 `AUTOSDD_UNATTENDED` 有設＝rc 1；`capacity` 列寫明量不到＝NOT-EVALUABLE 不是 rc 3）；(b) 序列：`promote`→主控 commit→`measure`；`run-close` 前跑一次 `measure` 作補記（`attr-confirm`／`attr-reject` 已同鎖追加 `mea.amend`，`measure` 補未追加者與開窗、關窗）；`measure` 印回滾提案卡 ⇒ 卡面逐字貼給掌舵者 ⇒ 掌舵者打字回滾 ⇒ `decide --kind rollback` ⇒ `rollback`（PowerShell 與 bash 兩形態）；(c) 退役提案配方：**容量候選（記憶索引軸）走 M 類歸檔型 PROP**（`--cls M`，R129 (d)、ADR-SI-06），**不用** `--action retire`；`--action retire` 只用於已被 promoted PROP 採納的工件（R127 (c)），`scan` 候選須先確認其目標在役；`prop-new --action retire`（本文欄位表填 `retire_when`、`reopen_symptom`）⇒ 沿 P2 的人工閘序列；R 類退役句 `set_maturity(reviewed_by=`；(d) 讀值紀律：量測腳本的 NE 不得改寫為達標、M1 不得單獨宣稱成效、反證條件成立只列為 T1 決策項；(e) **提案者隔離條文**（AC-SI-22-3；流程型 P）：提案者任務書不含指標目標值、計算細節與 `params.json` 路徑，偵測沿 AC-SI-20-4 ②（P2 的暴露掃描針已含 `params.json` 與量測腳本路徑，P3 不新增針）；〈擷取者〉〈歸因者〉〈提案者〉〈研究者〉四節不得含 §5.6 列的禁出現片段；(f) 〈啟動條件〉內兩處「P0 尚無該動詞」字樣（(e) 的 `capacity`；事件偵測段的 `status`——後者自 P1 起已存在而措辭過期）一併刪除，該節不得再含字面 `尚無該動詞`。`sop_p3_problems(text)` 與逐項刪去、注入的自證沿 P2 R108 的手法。
- **R134 零退化與既有測試的同步站點**：P3 夾具不改任何 P0／P1／P2 夾具的既有呼叫形態；**P0 的 42、P1 的 163、P2 的 137 個 AT 全綠**，其斷言值或預設值只准在下列站點改（站點含 R127 (c) 的目標在役判準所造成者），**既有函式僅限這些站點**、其餘一字不動（每項標「檔:行、函式名」；行號為撰寫時現況，以函式名為準）：(a) `check` 項數 32 改 33：`test_selfimproving_check.py` 的 `test_AT_001_1_1_baseline_is_green`；`test_selfimproving_events.py` 的 `test_AT_142_1_1_p1_items_on_p0_baseline_and_after_a_round`、`test_AT_142_2_E_1_p0_negatives_unchanged`、`test_AT_108_4_E_3_weird_events_are_event_type_only`、`TestDecFlagsAndConsumedKeys.check_case`；`test_selfimproving_capability.py` 的 `test_AT_143_1_E_2_dynamic_purity_and_forbidden_words`；`test_selfimproving_events_p2.py` 的 `test_AT_240_3_1_check_has_32_items`（並 `CHECK_RULES_REV` 3 改 4）。(b) `params` 30 鍵改 32 鍵：`test_selfimproving_events_p2.py` 的 `test_AT_240_4_1_params_30_keys`；`_selfimproving_fixtures.py:319` 的 `params_dict`；`test_selfimproving_check.py:275-322` 的本地 `params_dict`；`_selfimproving_p2_fixtures.py:43` 的 `make_p2_repo`（其 `params.json`）；`test_selfimproving_p2_meta.py:477-478` 的 `test_AT_240_14_1_p1_scenarios_replay_and_at_coverage`（`PARAM_SPECS` 鍵集合加兩鍵）。(c) `capacity` 不再是未實作動詞、動詞數 21 改 23：`test_selfimproving_events.py:1633` 的 `test_AT_140_1_E_1_unimplemented_verbs_and_reject_grammar`（calls 去掉 `capacity`，只留非動詞字串）；`test_selfimproving_console_obs.py:920` 的 `test_AT_235_3_1_no_delete_or_renumber`（動詞數 21 改 23）。(d) `status` 14 鍵改 15 鍵（末鍵 `measure`）、`capacity` 值改 `{"status":"NOT-EVALUABLE","reason":"no-axis-evaluable"}`：`test_selfimproving_events.py:1874-1878` 的 `WEIRD_STATUS_KEYS` 與 `:1924` 的 `test_AT_140_1_E_2_verbs_survive_weird_events`；`test_selfimproving_console_obs.py:1165、1168` 的 `test_AT_240_12_1_buckets_and_pending`（末鍵 `console_pending` 改 `measure`）；`test_selfimproving_export_status.py:27` 的 `STATUS_KEYS` 與其 `capacity` 斷言、`:453-475` 的 `test_AT_132_5_1_five_kinds`（proposals 18 鍵清單加末鍵 `window`）、`:573-574` 的 `test_AT_132_5_E_2_differential_and_isolation`（`same()` 的排除集合由 `console_pending` 加 `capacity`）。(e) `CAPABILITY` 登記表與計數：`test_selfimproving_capability.py` 的 `CAPABILITY` 表、`test_AT_143_1_1_real_tree_matches_registry`、`test_AT_240_5_1_exec_registry`（40 改 47，29／7／2／2 改 35／8／2／2；R132 兩態）。(f) 退役欄位與目標（R127）：`_selfimproving_fixtures.py:1042` 的 `body_md`（預設欄位表加 `retire_when`、`reopen_symptom` 兩列的合規值；M 類已有 `retire_when`，只加 `reopen_symptom`）；`test_selfimproving_props.py:1480-1481` 的 `test_AT_144_1_1_files_and_digest`（digest 核心的兩鍵由 null 改為夾具預設值）；`test_selfimproving_props.py:1146` 的 `test_AT_111_1_1_classes_and_group_marks`：其 `action=retire` 的 `prop-new` 目標 `docs/notes/tiny.md` 在該 run repo 內無 promoted PROP，依 R127 (c) 將 rc 1——Developer 於該呼叫之前以 P3 夾具 `promoted()` 手寫一個 `target="docs/notes/tiny.md"` 的 promoted PROP 使目標在役（`target` 為字串、與 §5.2 的 `promoted(…, target=T1)` 同形；不用 P2 夾具 `promoted_chain`：它的 `target` 固定為 `docs/notes/n<N>.md`、不可指定；該檔頂端加 P3 夾具模組的 import，非函式站點），斷言值（rc 為 0、`(cls, action, route)` 為 `("D","retire","loop")`）不變，`:1147` 的 `props_of(repo)[0]` 改 `props_of(repo)[-1]`；該檔其餘以 `body_md` 明示值的函式（`test_AT_109_1_1_body_shapes_accepted`、`test_AT_109_3_E_1_m_field_rejections`、`test_AT_144_1_E_1_digest_sensitivity_and_failures`）依 R127 (a) 不需改。本表外若有既有函式因預設欄位表或鍵數變動而紅，Developer 以 ⚖ 回報、不就地改斷言（由主控裁決後補入本表）。**P3 夾具自測**＝AT-340-8-1：以升級後夾具重放 P1 情境表（`sc_close`、`sc_seq`、`sc_legal`、`sc_rev`、`sc_susp`）與 P2 的 `sc_p2_legal`，`events.structure` 為 PASS、`fold` 狀態與 problems 與預期相同。
- **R135 AT 錨定與範圍**：本檔 AT 的 `-k` 一律為錨定名（P2 R102）；檢查函式 `parse_at_headers`、`anchor_problems`、`collect_nodes` 沿用 `test_selfimproving_p2_meta.py` 的同名函式（匯入、不複製；AT-340-9-1、AT-340-9-E-1）。Developer 棒只新增或修改 §5.7 的集合；不改 `.claude/**`、凍結檔（PRD、研究方法 SOP、P0／P1／P2 TCS）、`autoclaude/` 引擎原始碼、`AgentConsole/**`。

*G. Console 載體三動詞的寫入前判準（承接 DEF-200-568；P2 R94～R97 的補強，PRD AC-SI-33-1、35-1、35-2 把合法性判準歸 CLI）*

- **R136 寫入前判準**：實測（並行 SA 以真 CLI 餵稽核檔變形）顯示 P2 碼對 Console 載體三動詞「收下再變紅」——`decide --carrier console` 收下帶 `reason`、`flags` 的核准與空或含換行 `reason` 的否決，`obs-add` 收下含換行的字串欄，`obs-close` 收下含換行的 `disposition`；皆 rc 0 入帳，事後 `check` 才紅（`EVENT-KEY-UNKNOWN`、`EVENT-TYPE`、`ROW-ARITY`、`ROW-MUTATED`），OBS 帳本列被毀。**不變量**：任一 Console 動詞 rc 0 入帳之後，`check` 的 `events.structure`、`obs.console_audit`、`ledger.structure`、`history.row_mutated` 與各 `row.*` 項不得因該筆而 FAIL。**判準**（在 R94 的稽核檔驗證與既有前置碼〔`AUDIT-REF-REUSED`、`AUDIT-KIND-MISMATCH`、`AUDIT-SUBJECT-MISMATCH`〕之後、取寫入鎖之前，與其他本文碼一併收集；不符一律 rc 1、零寫入〔R71〕、輸出末尾印 `obs-draft:`）：(a) **`CTRL-CHAR`**（沿用 P0 `row.control_chars` 與 P2 AT-235-1-E-1 的既有碼名，不新增 `FIELD-CONTROL-CHAR`，⚖ 19）：自由文字欄含 C0 控制字元（`\x00`～`\x1f`，含 `\t`、`\n`、`\r`；以稽核檔 `body` 的原值判、不先 trim）——`decide` 的 `reason`；`obs-add` 的 `context`、`symptom`、`evidence`、`exposure` 與 `marks_extra` 各值（`obs-add` 對 `\n` 以外的 C0 與 DEL 本來就以 `CTRL-CHAR` 拒收，缺口只有 `\n`：列經 `parse_ledger` 被切成兩行，組列後自驗看不見）；列舉欄與 ID 欄（`category`、`severity`、`face`、`reason_class`、`digest`、`prop`、`run`、`obs_id`、`corrects`）本來就以各自既有碼拒收，不重複判；(b) **`EVENT-KEY-UNKNOWN`**（與 `events.validate` 對 `dec` 同碼）：`decide` 的 `body` 帶該 `dkind` 不收的鍵——`reason` 出現於 `approve`、`promote`、`unblock`、`ack-handoff`；非空 `flags` 出現於 `promote` 以外（空陣列放行，R94）；`promote` 的 `flags` 含不等於 `unverified_ack` 的元素者，同樣以 `events.validate` 的碼 `EVENT-TYPE` 拒收；(c) **`REASON-EMPTY`**：`reject`、`decline-promote`、`return`、`rollback`、`resume` 的 `reason` 為空字串（缺鍵仍為 `AUDIT-BODY-INVALID`；只含空白者與 `check` 同判而放行，⚖ 19）；(d) **`DISPOSITION-INVALID`**：`obs-close` 的 `disposition` 含 `\n`（新增；含 `\r\n` 與結尾換行），或首詞不屬 R97 的終值枚舉（既有行為）；`\n` 以外的 C0 控制字元仍為既有碼 `CTRL-CHAR`（R97 組列後自驗，不變）。**同源**：寫入端判準與 `check` 對同一事件或列的判準共用 `events.py` 的同一組述詞與欄位表（單一實作，不得各寫一份；必要時於 `events.py` 增公開入口）；判準函式住 `consoleaudit.py`（`ro`）的純函式 `body_guard(kind, body)`（回（碼, 說明）清單），`decwrite._console_body_codes`、`obsrows.body_problems`、`obswrite._close_codes` 各於既有本文判準呼叫點呼叫它；斷言行增量上限：`decwrite.py`（現 345）≤40、`obswrite.py` 與 `obsrows.py` 各 ≤20、`events.py`（現 350）≤10。**不變**：`check` 的判準本身、其餘既有碼與其先後、動詞、旗標與事件鍵集合；P2 的 AT-233、AT-235 各函式斷言不改（作者抽查 `test_selfimproving_console_obs.py` 的 decide、obs-add、obs-close 各表，輸入皆不含上列禁止形態；Developer 以該檔全檔重跑為準，發現例外以 ⚖ 回報、不就地改斷言）。

**〈P3 判定碼表（`check` 的 P3 追加；P0～P2 的 32 項及其碼不變）〉**

| 項目 ID | 碼 | 狀態 | 觸發 |
|---------|-----|------|------|
| `events.mea` | `MEA-KEY-MISSING`、`MEA-KEY-UNKNOWN`、`MEA-TYPE`、`MEA-ENUM`、`MEA-NOT-PROMOTED`、`MEA-PROMOTE-SEQ`、`MEA-BASELINE-DUP`、`MEA-BASELINE-ORDER`、`MEA-CLOSE-N` | FAIL | R113、R115 |
| `events.mea` | `CARRIER-NOT-ESTABLISHED` | NE nonblocking | 事件帳本不在場 |
| `events.transitions` | `TRANSITION-ILLEGAL`（`mea.amend` 指向或轉移不合法、第二個 `mea.open`、態不合）、`TRANSITION-ORPHAN` | FAIL | R114 |
| `params.keys` | `PARAM-MISSING`、`PARAM-TYPE`、`PARAM-RANGE` | FAIL | 必備鍵由 30 增為 32（R131） |

**〈P3 拒收碼表（rc 1；零殘留沿 P2 R71）〉**

| 動詞 | 碼 |
|------|-----|
| `measure` | `UNATTENDED-REFUSED`、`LOCK-BUSY`、`LEDGER-TORN`、`EVENT-BYTES-OVER`、`ANCHOR-UNAVAILABLE`、`OBS-LEDGER-UNAVAILABLE`、`DEFECT-LEDGER-UNAVAILABLE`、`MEASURE-NOT-CONVERGING`（rc 3：用法、`HOME-UNWRITABLE`、`params.json` 鍵無效） |
| `prop-new`、`prop-revise`（P3 追加；與既有碼一併收集） | `RETIRE-FIELD-MISSING`、`RETIRE-FIELD-FORM`（本文判準，兩動詞）、`RETIRE-TARGET-NOT-ADOPTED`（`action=retire`，兩動詞）；階段二政策碼 `CHURN-EXCEEDED`、`CAPABILITY-DELTA-MISSING`（僅 `prop-new`）（rc 3：舊旗標 `--retire-when`、`--reopen-symptom` 為未知旗標） |
| `capacity` | 無（唯讀；rc 3：用法、`params.json` 鍵無效、`--repo` 不是目錄） |
| `decide --carrier console`、`obs-add`、`obs-close`（P3 追加；R136；與既有本文碼一併收集） | `CTRL-CHAR`（既有碼名；`decide` 的 `reason` 與 `obs-add` 的自由文字欄含 C0 控制字元，`obs-add` 的 `\n` 為新增）、`EVENT-KEY-UNKNOWN`（`decide`）、`REASON-EMPTY`（`decide`）、`DISPOSITION-INVALID`（`obs-close`；含 `\n` 者為新增，首詞不在終值枚舉者沿 P2 R97） |

| US ID | User Story | AC ID | AC（Given／When／Then；括號內為 PRD 全名與規則） |
|-------|------------|-------|---------------------------------------------------|
| US-301 | 作為掌舵者，我要每個已晉升的改進在其後的量測窗內被確定性地檢視有沒有讓同一症狀復發，復發時拿到一張待我決定的回滾卡而不是被自動回滾，使損失有界 | AC-323-1 | （PRD AC-SI-23-1、§1.3〈M1 判定細則〉(a)～(e)；(f) 的 `W_OPP ≥ W_MIN` 耦合由 P0 AT-031-1-E-3 守、P3 不重複；R116～R122）Given 一筆 promoted PROP When `measure` Then 先記基線報告再開窗，依機會列規則累計，以再現／回滾／滿窗先到者關閉並記 `clean`／`recurred`／`rolled-back`／`pending`；`pending` 落定與晚到確認以 `mea.amend` 更正（`attr-confirm`／`attr-reject` 於同一把鎖內追加、`measure` 補記）、`mea.close` 不改寫；基線以晉升時刻為界、確定性重算 |
| US-301 | 同上 | AC-323-2 | （PRD AC-SI-23-2；R123）Given 窗內有經審查者確認的再現 When `measure` Then 出聲並印回滾提案卡、不自動回滾、不寫 DEC；僅有未決候選只在 `status` 印候選數與 `pending` 的窗 |
| US-301 | 同上 | AC-340-1 | （本檔自增；PRD §9.2 `mea.*` 列；R113～R115）Given 事件帳本 When `check` Then 四種 `mea.*` 有欄位表與 `events.mea`（共 33 項、`CHECK_RULES_REV` 為 4），載體缺席 NE |
| US-301 | 同上 | AC-340-2 | （本檔自增；PRD §9.2、§9.3 `attr` 列的承接，§7.1 ⚖ 2；R111、R112、R122）Given `measure` When 呼叫 Then 冪等、逐事件鎖內重算、無人值守 rc 1、輸入不可用 fail-loud、`--record-check` 留反證條件紀錄 |
| US-302 | 作為掌舵者，我要連續兩次採納都壞時迴圈自動暫停、只有我能恢復，且暫停期間觀察照常，使迴圈不在邊際報酬遞減時空轉 | AC-324-1 | （PRD AC-SI-24-1；R114 (e)）Given 連續 `stop_after_bad` 個窗的生效結果為 `recurred` 或 `rolled-back` When 重放 Then SUSPENDED（`pending` 不計入也不打斷、含 amend 更正），僅 `dec(resume)` 恢復 |
| US-302 | 同上 | AC-324-2 | （PRD AC-SI-24-2；R114 (e)、⚖ 9）Given SUSPENDED When 觀察 Then 觀察擷取照常，`prop-new`／`prop-revise` 拒收 |
| US-303 | 作為維護者與掌舵者，我要用一支零 token、只讀、可重跑的量測腳本看 M1～M5 與判準指紋，樣本不足時如實說量不到，且提案者看不到指標 | AC-322-1 | （PRD AC-SI-22-1；R124～R126）Given 帳本與 git 歷史 When 跑量測腳本 Then 輸出 M1～M5 的值、n、窗定義與判準指紋，NE 規則逐條，不呼叫模型 |
| US-303 | 同上 | AC-322-2 | （PRD AC-SI-22-2；R126）Given 輸出 When 呈現 Then 資訊欄與成功指標分區、M5 兩值並列、指標定義變更必改指紋、不接任何閘門 |
| US-303 | 同上 | AC-322-3 | （PRD AC-SI-22-3；R133 (e)；流程型 P，以 SOP 條文代位）Given 提案者 When 運作 Then 任務書不含指標目標值、計算細節與 `params.json` 路徑 |
| US-303 | 同上 | AC-340-6 | （本檔自增；PRD §9.3 量測腳本列、ADR-SI-05；R126）Given 探針 When 於任意 cwd 執行 Then 確定性、零寫入、窗規則與 `measure` 單一實作、DEF 解析與既有解析逐筆差分一致、純度 |
| US-304 | 作為掌舵者，我要每個要退役的工件帶得出可觀測的退役條件與再開症狀，並以同一道人工閘退役，且新增與退役不抖動 | AC-325-1 | （PRD AC-SI-25-1；R127）Given 任何 action 的 `prop-new`／`prop-revise` When 受理 Then 本文欄位表帶 `retire_when` 與 `reopen_symptom`（一句、不含輪號、日期、待排程字樣），缺一或形態不合 rc 1；`action=retire` 另須目標為已採納工件，否則 rc 1 |
| US-304 | 同上 | AC-325-2 | （PRD AC-SI-25-2；R127 (e)(f)）Given 退役 When 執行 Then 是 `action=retire` 的 PROP、走同一 K=1 閘；R 類卡面提示 `set_maturity(reviewed_by=`；系統只提議、不自動退役 |
| US-304 | 同上 | AC-326-1 | （PRD AC-SI-26-1；R128 (a)～(c)）Given 同一（`target`, 根因鍵）的 add→retire→re-add 循環 When 次數超過 `churn_max` Then `prop-new` 拒收 `CHURN-EXCEEDED` 並升級人工 |
| US-304 | 同上 | AC-326-2 | （PRD AC-SI-26-2；R128 (d)）Given 已退役工件被再提 When 受理 Then 須附 capability-delta 證據（退役後新出現、與原證據集不相交），否則 `CAPABILITY-DELTA-MISSING` |
| US-305 | 作為掌舵者，我要記憶索引等有上限的載入面逼近上限時自動列出可歸檔條目（只提議、不自動刪），且被截斷的條目被當成缺陷入帳 | AC-327-1 | （PRD AC-SI-27-1；R129 (a)～(e)）Given 有上限的載入面 When 用量達 `cap_frac` Then 記憶索引產生逐字歸檔的候選清單與 OBS 草稿列；KB 與偏好只印容量報告 |
| US-305 | 同上 | AC-327-2 | （PRD AC-SI-27-2；R129 (f)）Given 索引實際大小超過載入上限而仍有條目排在上限之後 When 檢查 Then 視為截斷風險缺陷、印草稿列 |
| US-305 | 同上 | AC-340-3 | （本檔自增；PRD §9.3 `capacity` 列；R129 (a)(g)(h)）Given `capacity` When 呼叫 Then 旗標與輸出契約、量不到＝NE、唯讀、rc 0／3 |
| US-306 | 作為維護者，我要 P3 的參數、能力登記、`status`／`export` 增量、SOP 與零退化各有可重跑檢查 | AC-340-4 | （本檔自增；PRD §9.1 C5、§9.4〈能力登記與純度判準〉；R131、R132）Given `params.json` 與套件原始碼 When 掃描 Then 32 鍵與新鍵驗證；能力登記 47 鍵（35／8／2／2；可選 `meaplan` 時 48 鍵 36／8／2／2）、閉包全 `ro`、無 SDD 碼呼叫 |
| US-306 | 同上 | AC-340-5 | （本檔自增；PRD §9.3 `status` 列、AC-SI-03-1 (e)；R130）Given `status` 與 `export` When 輸出 Then `capacity` 可評估、`events_detected` 增容量事件、新末鍵 `measure`、`export` 的 `window` 與 NE 值、全唯讀 |
| US-306 | 同上 | AC-340-7 | （本檔自增；PRD §8.1 P3 出口與 SOP；R133；流程型 P，以 SOP 條文代位）Given Operations SOP When 定稿 Then 〈P3 動詞〉節補齊 rc 契約、序列、退役配方、讀值紀律與隔離條文 |
| US-306 | 同上 | AC-340-8 | （本檔自增；R134）Given P3 變更落地 When 全套 Then P0／P1／P2 的 AT 全綠，斷言值只於同步站點改 |
| US-306 | 同上 | AC-340-9 | （本檔自增；R135）Given 本檔 AT 清單 When 解析與收集 Then 每個 AT 的錨定 `-k` 恰收一個測試函式 |
| US-307 | 作為維護者與 Console 操作者，我要 Console 載體的三個寫入動詞在寫入前就拒收壞稽核檔，使帳本與事件帳本不被收下再變紅的資料毀損 | AC-340-10 | （本檔自增；承接 DEF-200-568；P2 R94～R97；R136）Given 變形的稽核檔（自由文字欄含換行或控制字元、`decide` 帶該 dkind 不收的鍵、需理由者的 `reason` 為空、`obs-close` 的 `disposition` 不合法）When 呼叫 `decide --carrier console`、`obs-add`、`obs-close` Then rc 1、零寫入、輸出 `obs-draft:`，`check` 仍綠；合法稽核檔照常入帳 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID（沿 P2 TCS）；本檔除 §1 外沒有任何第一欄以 AC 起頭的表格，AT ID 於 §1 與 §2 的宣告位置之外只出現在說明性文字與表格的非第一欄。**本檔任何一行不寫出測試摘要字樣與數字同行的敘述**（`tools/check_pytest_baseline_sites.py` 的發現面），計數只放表格欄位；測試向量與範例不含金鑰形字面。

**INVEST 自檢**：獨立（只依賴 git、PRD、既有 `tools/lib/selfimproving/` 的 P0～P2 套件與 `lib.apply_lock`、`lib.platform_utils`）、可協商（旗標細部、窗時刻與邊界、歸屬細節、容量候選規則、卡面格式由本檔定義並列 §7.1，掌舵者可裁決）、有價值（PRD §8.1 P3 出口 (a)～(d) 的機制面全可由 AT 判定，真實面由 V22～V26 如實標記）、可估計（7 支新套件模組＋1 支探針＋入口 2 動詞＋`evwrite`、`writeverbs`、`defs` 的小幅增量＋5 個新測試檔＋1 個新夾具模組＋既有測試的 R134 同步站點＋SOP＋D12 對四個既有 Console 載體檔的小幅增量）、小（P3 範圍由 PRD §9.6 劃定；AgentConsole 與 P2 真實運轉不在本檔）、可測（AT 數見 §1；絕大多數用 tmp 目錄的合成 repo 與手寫事件，不碰真帳本、不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P3-1 | 純度與能力登記：R132；`status`、`export`、`check`、`card`、`scan` 與 `capacity`、探針的行程**不載入** `meawrite` 與其他寫入類、`exec`、`net` 模組；`measure` 只寫 `mea.*` 四種事件（R122 (f)） | AT-340-4-2、AT-340-4-E-2、AT-340-6-E-1、AT-323-2-E-2 |
| NFR-P3-2 | 效能（寬鬆不等式）：合成 repo（200 列 OBS、50 列 DEF、10 個 promoted PROP）上單次 `measure`、`status`、`capacity`、探針各小於 10 秒；真 repo 上探針與 `status` 各小於 30 秒（3 次取最大值，V22、V23，不列 AT） | AT 內牆鐘上界；V22、V23 |
| NFR-P3-3 | 跨平台（根 `CLAUDE.md` 鐵律三）：全部時刻為 aware（DEF 以日末 UTC instant 比較，不用本機時區）；路徑一律 `posixpath`／`rows.path_set` 的 casefold 與 `/` 形、不用 `os.path` 的平台語意；git 只經 `Git`；CRLF 與 BOM 容忍（記憶索引、KB／偏好 JSON、帳本）；輸出位元組直寫 UTF-8 LF；macOS 未實跑項在報告標「未驗」 | AT-323-1-E-2、AT-327-1-E-2、AT-340-6-1；V28 |
| NFR-P3-4 | 根層護欄相容：沿 P2 NFR-P2-4（不新增 skip／skipTest／xfail、`encoding="utf-8"`、可被兩種方式收集、不另寫 stdout 重設站點、子行程與執行緒夾具必回收） | 根層 unittest 閘門；SCG-4 |
| NFR-P3-5 | LOC 分級：`tools/lib/selfimproving/*.py` 每檔 ≤400 斷言行（現 `fold.py` 363、`events.py` 350、`writeverbs.py` 377、`props.py` 258、`evwrite.py` 92、`defs.py` 75，增量上限依 D 表與 R114 (f)、R121 (e)、R122 (g)、R127、R128、R132；可選 `meaplan.py` 同守 400）；入口 ≤750；現查 `python AutoClaude/tools/check_loc_budget.py --json` rc 0 | SCG-4 實跑（V20） |
| NFR-P3-6 | 靜態檢查：`ruff check` 對新增與改動的每個 `.py` 為 0 錯 | SCG-4 實跑（V20） |
| NFR-P3-7 | 測試 hermetic：沿 P2 NFR-P2-7（tmp 合成 repo、`AUTOSDD_SI_DIR` 與 `CLAUDE_CONFIG_DIR` 指向 tmp、不讀真逐字稿與真 Claude 家目錄、不連外網、合成編號於執行期組出、不寫不存在於真帳本的字面 ID）；P3 的唯讀例外只有 AT-327-1-2（引擎常數）與 AT-340-6-E-2（真缺陷帳本差分） | V20 的字面 ID 掃描與既有鎖 |
| NFR-P3-8 | 範圍守衛：實作者只新增或修改 §5.7 的集合；不改 `.claude/**`、凍結檔、`autoclaude/` 引擎原始碼、`AgentConsole/**`；重釘根層棘輪與 compat-ci `paths`（新探針與新測試檔的覆蓋）由主控收尾 | V16、V20 |
| NFR-P3-9 | CI 與棘輪：新增 5 個測試檔與 1 個夾具模組，估新增 `tools/` 斷言行遠超護欄層單輪淨額上限，須由主控以具名一次性例外重釘（`_REPIN_APPROVED_ROUND_OVERAGE`，名冊上限上修須可見）；compat-ci 兩支的 `paths`（OBS-SI-215 的結構條件）現有 `tools/probe/**` 與 `docs/03_testing/contracts/TCS-SelfImproving-*.md` 等 glob 已涵蓋探針、新測試與本檔，**不得新增含 `selfimproving_measure` 字面的 `paths` 項**（探針不接任何閘門，R126 (f)）；新測試另讀的文件由主控於收尾現查覆蓋；每個新測試檔在 CI 上小於 300 秒、每檔不超過 35 個 AT | V20；根層全套 unittest |
| NFR-P3-10 | **Developer 交卷前閘門清單**（缺一即不得交卷；輸出逐字貼入）：(1) 本檔 AT 與 P0～P2 全部 AT 全綠（P3 五個新測試檔、既有的 `test_selfimproving_capability.py` 與 `test_selfimproving_console_obs.py`，加其餘既有 SI 測試檔，`-q -p no:xdist -o addopts=`）；(2) `python tools/selfimproving.py check` 對真 repo rc 0（33 項）；(3) `ruff check`；(4) `check_loc_budget.py --json` rc 0；(5) `python tools/sync_onboarding_baselines.py --check-snapshot` rc 0；(6) 官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）rc 0；(7) 護欄層重釘做到 `--print-guard-lines` 淨差額 +0（主控）；(8) 文件引用子專案檔案一律寫 monorepo 根起算路徑；(9) 交卷含〈流程摩擦〉節（收尾前由主控入帳）；(10) 新增 `tools/tests/` 檔逐項過根層鎖（沿 P2 NFR-P2-10 (11)～(14)：檔數下限、E501 東亞寬度、腳本入口在檔尾、docstring 指名受測模組）；(11) AT-340-9-1 綠；(12) `git grep` 本檔、測試與程式碼無不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>` | SCG-4 實跑檢核 V17～V21 |
| NFR-P3-11 | 失效可偵測（NFR-SI-09）：量不到＝NOT-EVALUABLE、不得印成 0 或綠——`measure` 輸入不可用（rc 1）、`status.measure`／`status.capacity` 的 NE、探針各欄 NE、`capacity` 各軸 NE、M1 的 NE 理由碼、反證條件的 `falsified: null` 與 `missing` | 各 AT 的 NE 斷言 |
| NFR-P3-12 | 寫入面最小：`measure` 之外的 P3 入口（`capacity`、探針、`status`、`export`、`events.mea`）零寫入；`measure` 的 `git status --porcelain` 差異只有事件帳本一個檔；不 commit、不自動回滾、不自動退役 | AT-323-2-E-2、AT-325-2-E-1、AT-340-3-1、AT-340-6-1 |

**追溯矩陣**：F-004 ← PRD FR-SI-22～27（§5.2 FG-G、FG-H）、§1.3 與〈M1 判定細則〉、§9.1 的 C11、C12、C15、§9.2（Measurement 列、事件欄位表的 `mea.*`、詞彙 21）、§9.3（`status`、`capacity`、量測腳本列）、§9.4（SUSPENDED、抖動、能力登記）、§9.5 的 ADR-SI-05、06、10、§9.6 P3 列、§8.1 P3 出口 (a)～(d)、§9.7 #23、附錄 C.2 #3、#8；DEF-200-568 ← P2 R94～R97、PRD AC-SI-33-1／35-1／35-2（D12）；US-301～US-307 → AC-322-1～AC-340-10（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；單一 FSM 鍵 `monorepo-si-p3-measure-retire`）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v0.10 全文（§8.1 P3、§9.6 P3）；Stage-1 凍結依常態規則由主控執行（`--approver` 引 sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-004（本檔 FRD-lite）；FR-SI-22～27 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／NFR 已量化定義 | NFR-P3-1～12（本檔）；最近依據 PRD NFR-SI-01、02、03、05、06、09 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-301～US-307（本檔 INVEST 自檢） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／利害關係人已確認簽核 | PRD 附錄 C.2（授權代決；sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13）；本輪立案 T1＝sid af29fe90-d902-4763-9d33-eb4d4b98214b line 13 與 line 94（凍結依常態規則由主控執行、掌舵者可隨時以 T1 推翻） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6；根層 RTM 檔另依 SSOT §2 落 `docs/06_quality/RTM-SelfImproving-P3-<日期>.md` | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review | 不適用（功能級增量；設計載於 PRD §9）；最近依據 PRD §9.0～§9.6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／API Spec 草稿完成 | 不適用（無 HTTP 端點）；命令列介面即契約：R111、R112、R129、R130 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／資料模型設計完成 | PRD §9.2（Measurement 列、事件欄位表）；本檔 R113、R116～R121 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／NFR 設計對應完成 | NFR-P3-1～12 對應 R122（逐事件鎖內重算）、R126（純度與單一窗規則）、R132（能力登記）、R116 (b)（aware 時刻） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／整合架構說明完整 | 無第三方服務；依賴 git（只經 `Git`）、標準庫、`lib.apply_lock`、`lib.platform_utils`；引擎常數（KB 1000、偏好 10）以唯讀漂移鎖對映 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／C4 Context 圖完成 | PRD §9.1 載體對映表（C11、C12、C14 的容量事件、C15）；P3 不新增系統邊界 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／C4 Container 圖完成 | 落點：`tools/lib/selfimproving/`（47 檔；可選 `meaplan.py` 時 48 檔）、`tools/selfimproving.py`、`tools/probe/selfimproving_measure.py`、`tools/tests/`、`docs/06_quality/`、`docs/05_development/` | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／所有架構決策有對應 ADR | PRD §9.5：ADR-SI-05、ADR-SI-06、ADR-SI-10；本增量無新架構決策，ADR 不新開 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／Trust Boundary Map 完成 | 不適用（brownfield）；要點：量測只讀帳本與 git、`measure` 只寫 `mea.*`、`capacity` 只讀、提案者隔離為流程型（P）加暴露掃描（D） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／Before／After 架構對比 | 本檔 FRD-lite〈現況與變更〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／OpenAPI 3.1 規格完整 | 不適用（無 HTTP API）；介面為命令列 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／Request／Response Schema 定義完整 | 輸出形態：R112、R113、R126 (b)、R129 (g)、R130 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／錯誤碼定義 | rc 表 0、1、3（R111）、〈P3 判定碼表〉與〈P3 拒收碼表〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／Consumer Contract 完成 | 消費者＝主控與 QA（`measure`、`status`、`capacity`、探針輸出）、掌舵者（回滾提案卡）、AgentConsole 的 `export` 消費者（`window` 與 `measure` 新鍵，P1b／P2b 側另有 TCS）；SOP 是各角色任務書的上位（研究方法 SOP，本增量不改它） | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 與研究方法 SOP 的值是 Stage-1 凍結的 digest；本檔作者於 2026-10-24 以 `Get-FileHash -Algorithm SHA256` 對工作樹現況重算一致（PRD `1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406`、SOP `deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2`；兩檔皆 LF，故原檔雜湊與換行正規化後相同），HEAD `23b1afb1b6d1afe63fdd1687462f106db44544af`。凍結後的實際 digest 以該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 為準，與本表不符時以 `show` 為準並更正本表。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；負控與邊界以 `AT-<NNN>-<Y>-E-<n>` 命名。標「流程型」者＝以 SOP 條文（加刪去自證）判定的 AC，其機器守的一半另有 AT。AT 的判定指令與測試檔見 §2 各 AT 標頭；測試檔縮寫見 §2 開頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-322-1 | 量測腳本輸出與 NE 規則（PRD AC-SI-22-1） | AT-322-1-1 | （PB）M1 per-PROP：S-PROBE-A 的可評估窗、值與 n、每 PROP 的基線事件數與機會列數；JSON 與文字兩形態 | ✅ | Integration | □ |
| AC-322-1 | 量測腳本輸出與 NE 規則（PRD AC-SI-22-1） | AT-322-1-2 | （PB）M4、M5 兩值與 m5 鍵集合、資訊欄各計數、M2 與 M3 的中位數與排除計數、全域窗 | ✅ | Integration | □ |
| AC-322-1 | 量測腳本輸出與 NE 規則（PRD AC-SI-22-1） | AT-322-1-E-1 | （PB）M1 的 NE 規則逐條：基線事件數 0 與 1、基線列數不足、未關閉、pending、rolled-back 無再現、無 baseline、n 為 0；錨不可用只使全域窗為 NE | ✅ | Integration | □ |
| AC-322-1 | 量測腳本輸出與 NE 規則（PRD AC-SI-22-1） | AT-322-1-E-2 | （PB）M5 的 NE 與分區：n 不足為 NE（理由碼 sample-below-w-min）、兩值並列、ack 分區、amend 改判不改分子、窗後回滾列 late_rollbacks | ✅ | Integration | □ |
| AC-322-1 | 量測腳本輸出與 NE 規則（PRD AC-SI-22-1） | AT-322-1-E-3 | （PB）反證條件：同鍵相鄰可評估窗皆 recurred 才成立、NE 與 pending 不計不打斷、不同鍵不合併、無可評估窗為 null | ✅ | Integration | □ |
| AC-322-2 | 分區、M5 兩值、指紋、不接閘門（PRD AC-SI-22-2） | AT-322-2-1 | （PB）成功指標區與資訊欄分區、M5 兩值並列、指紋為 manifest 與 metrics_rev 的雜湊、鍵序固定 | ✅ | Integration | □ |
| AC-322-2 | 分區、M5 兩值、指紋、不接閘門（PRD AC-SI-22-2） | AT-322-2-E-1 | （PB）指紋敏感度：params、metrics.md、metrics_rev 改變即變；來源表、CRLF 版、CHECK_RULES_REV 不改 | ✅ | Integration | □ |
| AC-322-2 | 分區、M5 兩值、指紋、不接閘門（PRD AC-SI-22-2） | AT-322-2-E-2 | （PB）不接閘門與零寫入：最壞資料仍 rc 0；工作流程、git hooks、settings 不含探針字面；帳本與工作樹位元組不變 | ✅ | Integration | □ |
| AC-322-3 | 提案者隔離（PRD AC-SI-22-3；流程型） | AT-322-3-1 | （M3）SOP 提案者面向四節不含禁出現片段，〈P3 動詞〉含隔離條文 | ✅ | Unit | □ |
| AC-322-3 | 提案者隔離（PRD AC-SI-22-3；流程型） | AT-322-3-E-1 | （M3）隔離判準有牙：對 SOP 副本逐項注入禁出現片段與刪除隔離條文，各點名該項 | ✅ | Unit | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-1 | （MW）基線與開窗：S-BASE 的基線報告欄位（opp、events、pending、anchor）與 mea.open；第二次零事件 | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-2 | （MW）滿窗關閉 clean：S-ADOPT 五列、n_opp、at；第六列不計；PROP 態 closed | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-3 | （MW）M 類機會列：檔名引用與已確認根因鍵、無關列不計；再現優先（確認得 recurred、駁回算列、未決得 pending） | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-4 | （MW）再現只歸最近晉升者：兩 PROP 共用鍵時只有後者 recurred、前者不受影響；窗重疊各自累計 | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-5 | （MW）回滾先到關閉 rolled-back：n_opp 與 at 取 DEC 時刻，其後的列不計 | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-6 | （MW）pending 與落定：未決候選使滿窗記 pending、PROP 維持 measuring；`attr-confirm` 得 recurred、`attr-reject` 得 clean，amend 於同一把鎖內緊接落定事件、cause 為其 seq、`measure` 之前 due 已為 0、PROP 轉 closed | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-7 | （MW）晚到確認：clean 窗關閉之後以 `attr-confirm` 確認先於關閉立案的再現，同鎖追加 amend 由 clean 到 recurred；關閉之後立案者不改 | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-E-1 | （MW）基線確定性：晚於晉升才跑 measure、晉升後才到的落定事件與根因確認不回補 events 與 pending | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-E-2 | （MW）列邊界與規則負控：錨前後、同刻、同日 DEF、缺 offset、目錄名前綴相似、大小寫、無路徑 | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-E-3 | （MW）輸入不可用 fail-loud：錨缺、錨非 commit、OBS 帳本缺、缺陷帳本家族缺皆 rc 1 零寫入；無 promoted PROP 時 rc 0 | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-E-4 | （MW）偽造事件不生效：指向他 PROP 的 amend、from 不符、非法轉移、非 close 的 seq、第二個 mea.open；生效結果與 PROP 態不變、TRANSITION-ILLEGAL | ✅ | Integration | □ |
| AC-323-1 | 採納窗與基線窗（PRD AC-SI-23-1） | AT-323-1-E-5 | （MW）attr 動詞的同鎖追加被替身略過：due 為 1、measure 補記後為 0，補記的 amend 與同鎖路徑逐鍵相同 | ✅ | Integration | □ |
| AC-323-2 | 回滾提案卡（PRD AC-SI-23-2） | AT-323-2-1 | （MW）recurred 窗印回滾提案卡：首行、核心區行數與寬度、再現與 ATT 與配方內容、決定樣板可被 decgrammar 解析；重跑重印、DEC 後不再印 | ✅ | Integration | □ |
| AC-323-2 | 回滾提案卡（PRD AC-SI-23-2） | AT-323-2-E-1 | （MW）無已確認再現不印卡：未決候選、pending、clean、rolled-back、已記回滾決定；status 印候選數 | ✅ | Integration | □ |
| AC-323-2 | 回滾提案卡（PRD AC-SI-23-2） | AT-323-2-E-2 | （MW）measure 從不下決定：只追加四種 mea 事件、不寫 dec 與 app.rollback、工作樹不變；無人值守 rc 1 | ✅ | Integration | □ |
| AC-324-1 | SUSPENDED 導出（PRD AC-SI-24-1） | AT-324-1-1 | （MW）連續兩個壞窗 SUSPENDED、所在運轉、prop-new 拒收、decide resume 解除、解除後 prop-new 受理 | ✅ | Integration | □ |
| AC-324-1 | SUSPENDED 導出（PRD AC-SI-24-1） | AT-324-1-2 | （MW）pending 不計入也不打斷：壞、pending、壞成立；pending 經 amend 到 clean 後不成立、到 recurred 後成立 | ✅ | Integration | □ |
| AC-324-1 | SUSPENDED 導出（PRD AC-SI-24-1） | AT-324-1-E-1 | （MW）不成立情形：單一壞窗、壞 clean 壞、stop_after_bad 為 3 時兩個壞窗；三個壞窗成立 | ✅ | Integration | □ |
| AC-324-1 | SUSPENDED 導出（PRD AC-SI-24-1） | AT-324-1-E-2 | （MW）恢復的綁定與邊界：RUN 不符、未暫停時恢復、恢復後相鄰壞窗再度暫停（不歸零）、恢復後 pending 窗經 amend 轉壞再度暫停 | ✅ | Integration | □ |
| AC-324-2 | SUSPENDED 期間觀察照常（PRD AC-SI-24-2） | AT-324-2-1 | （MW）SUSPENDED 期間觀察擷取與唯讀動詞照常：與未暫停的 repo 逐一同 rc | ✅ | Integration | □ |
| AC-324-2 | SUSPENDED 期間觀察照常（PRD AC-SI-24-2） | AT-324-2-E-1 | （MW）prop-new 與 prop-revise 拒收 SUSPENDED 且零殘留；在途 PROP 的 card --issue 與 heldout-freeze 不受影響 | ✅ | Integration | □ |
| AC-325-1 | 退役欄位（PRD AC-SI-25-1） | AT-325-1-1 | （CR）retire 提案的本文兩欄合形態、目標為已採納工件：受理、digest 綁定兩值（任一改動 digest 即變）、事件無新鍵；add 提案的兩欄同樣受理 | ✅ | Integration | □ |
| AC-325-1 | 退役欄位（PRD AC-SI-25-1） | AT-325-1-E-1 | （CR）缺欄、空值、含日期或輪號、revise 缺欄、舊旗標 rc 3、retire 目標未採納（最近晉升者為 retire 或 delete 被擋、回滾後回到在役、退役後再 add 放行）：碼與 rc、零殘留 | ✅ | Integration | □ |
| AC-325-1 | 退役欄位（PRD AC-SI-25-1） | AT-325-1-E-2 | （CR）形態負控：輪號、日期、待排程、換行各 RETIRE-FIELD-FORM；空值回空清單不雙報；PR123、ROW-MUTATED 不誤殺 | ✅ | Unit | □ |
| AC-325-2 | 退役走同一人工閘（PRD AC-SI-25-2） | AT-325-2-1 | （CR）退役走同一人工閘：目標已採納、proposed 態、經 decide 與 P2 動詞推進（態序逐步斷言）；R 類卡面有 set_maturity 提示、其他類無 | ✅ | Integration | □ |
| AC-325-2 | 退役走同一人工閘（PRD AC-SI-25-2） | AT-325-2-E-1 | （CR）只提議不套用：capacity、measure、scan 不建立 PROP 或 DEC、不改工作樹；套件無 set_maturity 呼叫與 SDD 碼 import | ✅ | Integration | □ |
| AC-326-1 | 抖動防護（PRD AC-SI-26-1） | AT-326-1-1 | （CR）第二個循環放行：A1 R1 A2 R2 之後的新 add 受理 | ✅ | Integration | □ |
| AC-326-1 | 抖動防護（PRD AC-SI-26-1） | AT-326-1-E-1 | （CR）超過 churn_max 拒收：A1 R1 A2 R2 A3 R3 之後的新 add 得 CHURN-EXCEEDED 與草稿列；churn_max 為 3 放行；不同 target 或根因鍵不計；與 CAPABILITY-DELTA-MISSING 同時命中時兩碼並列 | ✅ | Integration | □ |
| AC-326-2 | capability-delta（PRD AC-SI-26-2） | AT-326-2-1 | （CR）capability-delta 放行：退役後新立且座標與既有證據不相交的來源 | ✅ | Integration | □ |
| AC-326-2 | capability-delta（PRD AC-SI-26-2） | AT-326-2-E-1 | （CR）缺 capability-delta：來源全為舊證據、座標相交、退役前立案、同日 DEF 邊界 | ✅ | Integration | □ |
| AC-327-1 | 容量事件與歸檔候選（PRD AC-SI-27-1） | AT-327-1-1 | （CR）記憶索引逼近上限：位元組軸與行數軸、候選自尾逐字、單卡、events_detected e、草稿列過 check | ✅ | Integration | □ |
| AC-327-1 | 容量事件與歸檔候選（PRD AC-SI-27-1） | AT-327-1-2 | （CR）KB 與偏好只印容量報告與草稿列、不產候選；常數 10 與 1000 對映引擎原始碼 | ✅ | Integration | □ |
| AC-327-1 | 容量事件與歸檔候選（PRD AC-SI-27-1） | AT-327-1-E-1 | （CR）門檻邊界與量不到：恰等於 cap_frac 觸發、少一位元組不觸發；缺輸入與不可解析為 NE 而非零、非 rc 3；唯讀零寫入 | ✅ | Integration | □ |
| AC-327-1 | 容量事件與歸檔候選（PRD AC-SI-27-1） | AT-327-1-E-2 | （CR）分卡與逐字：需移除的條目數超過卡上限時切卡、逐字含行尾空白與 CRLF、原序、max_archive 參數隨動 | ✅ | Unit | □ |
| AC-327-2 | 截斷風險（PRD AC-SI-27-2） | AT-327-2-1 | （CR）截斷風險：行數軸與位元組軸（含攔腰截斷的條目）、草稿列 bug P2 以截斷風險起頭 | ✅ | Integration | □ |
| AC-327-2 | 截斷風險（PRD AC-SI-27-2） | AT-327-2-E-1 | （CR）無風險：恰等於上限、大於上限但其後只有非條目行 | ✅ | Unit | □ |
| AC-340-1 | mea.* 欄位表與 events.mea（本檔自增） | AT-340-1-1 | （MV）measure 寫出的事件通過欄位表與 check：33 項、events.mea PASS、鍵集合恰為 R113 | ✅ | Integration | □ |
| AC-340-1 | mea.* 欄位表與 events.mea（本檔自增） | AT-340-1-E-1 | （MV）欄位表負控：缺鍵、表外鍵、型別、列舉、n_opp 上限與 clean 的 n_opp、promote_seq、未晉升、基線重複與次序、check 報告帶 prop 與 missing 過長，各恰一碼 | ✅ | Integration | □ |
| AC-340-1 | mea.* 欄位表與 events.mea（本檔自增） | AT-340-1-E-2 | （MV）判準版本與載體缺席：CHECK_RULES_REV 為 4、前 32 項 id 與次序不變、無事件帳本時 NE 非阻塞、P0 基線 repo 的 rc 不變 | ✅ | Integration | □ |
| AC-340-2 | measure 動詞（本檔自增） | AT-340-2-1 | （MV）measure 的 CLI 契約：成功文字與 JSON 鍵序、事件次序 report open close、--by 標籤、第二次零事件、鎖釋放 | ✅ | Integration | □ |
| AC-340-2 | measure 動詞（本檔自增） | AT-340-2-2 | （MV）--record-check：追加一筆全域報告、相同內容不重複、內容變則再追加、NE 也記並寫缺什麼、指紋等於探針的指紋 | ✅ | Integration | □ |
| AC-340-2 | measure 動詞（本檔自增） | AT-340-2-E-1 | （MV）拒收與用法：無人值守（值 0 與 1）rc 1 零寫入、未知旗標 rc 3、--by 不合 rc 3、params 鍵無效 rc 3、家目錄不可寫 rc 3、鎖被占 rc 1 | ✅ | Integration | □ |
| AC-340-2 | measure 動詞（本檔自增） | AT-340-2-E-2 | （MV）並行 measure 不重複：兩執行緒交錯後每 PROP 恰一筆 baseline 與一筆 open、seq 連續 | ✅ | Integration | □ |
| AC-340-3 | capacity 動詞（本檔自增） | AT-340-3-1 | （CR）capacity 的 CLI 契約：旗標、JSON 鍵序與文字形態、唯讀零寫入、無人值守不受限 | ✅ | Integration | □ |
| AC-340-3 | capacity 動詞（本檔自增） | AT-340-3-E-1 | （CR）用法與參數：未知旗標 rc 3、params 鍵無效 rc 3 點名、旗標路徑讀不到為 NE 而非 rc 3 | ✅ | Integration | □ |
| AC-340-4 | 參數與能力登記（本檔自增） | AT-340-4-1 | （M3）params.json 為 32 鍵且兩新鍵值為 200 與 25600、PARAM_SPECS 含之、check 的 params.keys 與 coupling 通過 | ✅ | Integration | □ |
| AC-340-4 | 參數與能力登記（本檔自增） | AT-340-4-2 | （CP）能力登記兩態（47 鍵 35／8／2／2；可選 meaplan 時 48 鍵 36／8／2／2）、新增的 ro 檔為 ro 與 meawrite 為 rw、閉包全 ro、無 SDD 碼呼叫 | ✅ | Unit | □ |
| AC-340-4 | 參數與能力登記（本檔自增） | AT-340-4-E-1 | （M3）新鍵缺、型別或範圍不符：check 紅、capacity 與 status 對應軸 rc 3 點名、不以預設值頂替 | ✅ | Integration | □ |
| AC-340-4 | 參數與能力登記（本檔自增） | AT-340-4-E-2 | （CP）能力登記判準有牙：對套件 tmp 副本逐項注入違規（ro 檔 import meawrite、探針之外的 subprocess、SDD 碼呼叫），各回對應問題 | ✅ | Unit | □ |
| AC-340-5 | status 與 export 增量（本檔自增） | AT-340-5-1 | （MV）status 的 15 鍵與 measure 物件、capacity 對預設路徑記憶索引的可評估值與 events_detected 的 e；前 14 鍵語意不變 | ✅ | Integration | □ |
| AC-340-5 | status 與 export 增量（本檔自增） | AT-340-5-2 | （MV）export proposals 的 window 末鍵（無窗 null、有窗各狀態）與 export status 的 capacity 恆 NE；export 不讀家目錄 | ✅ | Integration | □ |
| AC-340-5 | status 與 export 增量（本檔自增） | AT-340-5-E-1 | （MV）量不到與零寫入：無事件帳本、錨不可用、缺陷帳本缺各自的 NE 理由；status 與 export 前後位元組不變 | ✅ | Integration | □ |
| AC-340-6 | 探針形態與純度（本檔自增） | AT-340-6-1 | （PB）任意 cwd 子行程執行、兩次輸出逐位元相同、零寫入、窗欄位與 measure 的基線與生效結果逐項相同 | ✅ | Integration | □ |
| AC-340-6 | 探針形態與純度（本檔自增） | AT-340-6-E-1 | （PB）純度：原始碼無 subprocess、網路、模型客戶端、寫入原語；import 只經 ro 模組；不讀 AUTOSDD 與金鑰環境變數 | ✅ | Unit | □ |
| AC-340-6 | 探針形態與純度（本檔自增） | AT-340-6-E-2 | （PB）DEF 解析差分：合成邊界列與真缺陷帳本家族，（ID, 結案類）與 check_defect_log_crossref 逐筆相同 | ✅ | Integration | □ |
| AC-340-6 | 探針形態與純度（本檔自增） | AT-340-6-E-3 | （PB）用法與載體缺席：--repo 不是目錄與 params 鍵無效 rc 3；無事件帳本時 M1、M4、M5 為 NE 而 rc 0 | ✅ | Integration | □ |
| AC-340-7 | SOP〈P3 動詞〉（本檔自增；流程型） | AT-340-7-1 | （M3）SOP〈P3 動詞〉定稿：rc 契約兩列、序列、回滾序列、兩形態、退役配方、讀值紀律、隔離條文、啟動條件字樣已刪 | ✅ | Unit | □ |
| AC-340-7 | SOP〈P3 動詞〉（本檔自增；流程型） | AT-340-7-E-1 | （M3）SOP 判準有牙：逐項刪去必備片段、條文移入圍欄、序列對調、待補復現，各被判不合格 | ✅ | Unit | □ |
| AC-340-8 | 零退化（本檔自增） | AT-340-8-1 | （M3）零退化：升級夾具重放 P1 與 P2 情境表皆合規；P0、P1、P2 的全部 AT 在測試檔各有對應函式；同步站點的斷言值如 R134 | ✅ | Integration | □ |
| AC-340-8 | 零退化（本檔自增） | AT-340-8-E-1 | （M3）夾具升級不吞掉違規：明示的錯誤值不被預設值覆蓋，P0 至 P2 的負控事件仍被同一碼擋下 | ✅ | Unit | □ |
| AC-340-9 | AT 錨定檢查（本檔自增） | AT-340-9-1 | （M3）本檔每個 AT 的錨定 -k 以節點 id 子字串比對恰命中一個測試函式 | ✅ | Integration | □ |
| AC-340-9 | AT 錨定檢查（本檔自增） | AT-340-9-E-1 | （M3）錨定檢查有牙：無結尾底線、值與 AT id 不符、零命中、重複命中、缺 slug、同一函式被兩個 AT 命中，各被判紅 | ✅ | Integration | □ |
| AC-340-10 | Console 載體寫入前判準（本檔自增；承接 DEF-200-568） | AT-340-10-1 | （CN）合法稽核檔照常入帳：核准、單字元理由的否決、obs-add、obs-close 各一份，事件與帳本逐項合規、check 仍綠 | ✅ | Integration | □ |
| AC-340-10 | Console 載體寫入前判準（本檔自增；承接 DEF-200-568） | AT-340-10-E-1 | （CN）自由文字欄含換行或控制字元（十種）：既有碼 CTRL-CHAR、rc 1、零殘留、check 仍綠、換成一般字元後放行 | ✅ | Integration | □ |
| AC-340-10 | Console 載體寫入前判準（本檔自增；承接 DEF-200-568） | AT-340-10-E-2 | （CN）decide 的 body 帶該 dkind 不收的鍵（七種）：EVENT-KEY-UNKNOWN；flags 元素不合（一種）：EVENT-TYPE；與 check 對手寫事件同碼的差分 | ✅ | Integration | □ |
| AC-340-10 | Console 載體寫入前判準（本檔自增；承接 DEF-200-568） | AT-340-10-E-3 | （CN）需理由的五種 dkind 帶空 reason：REASON-EMPTY；單字元 reason 放行；缺鍵仍 AUDIT-BODY-INVALID | ✅ | Integration | □ |
| AC-340-10 | Console 載體寫入前判準（本檔自增；承接 DEF-200-568） | AT-340-10-E-4 | （CN）obs-close 的 disposition 含換行（四種）或首詞不在終值枚舉（兩種）：DISPOSITION-INVALID；其他控制字元維持既有 CTRL-CHAR | ✅ | Integration | □ |
| AC-340-10 | Console 載體寫入前判準（本檔自增；承接 DEF-200-568） | AT-340-10-E-5 | （CN）回歸：被拒的含換行 disposition 與 obs-add 不留痕，OBS 帳本位元組不變、該列仍 open，其後同一列可正常關閉 | ✅ | Integration | □ |

**覆蓋率統計**:
- 總 AC 數: 23（PRD 的 13 個加本檔自增的 10 個）
- 已映射 AT 數: 78（正控 35 個、負控〔E 類〕43 個；每個 AC 至少一個正控與一個負控；負控數不少於正控數）
- 各測試檔的 AT 數: MW 21；MV 10；PB 12；CR 17；M3 10；CP 2；CN 6（既有檔 `test_selfimproving_console_obs.py`，D12）
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **格式、驗收字樣與判定指令沿 P2 TCS §2 開頭**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_323_1_1]`；E 類為 `[AT_OK_323_1_E_1]`），Then、And 行只有驗收字樣一組引號，其餘字面值一律用反引號；判定指令一律為 `python -m pytest tools/tests/<檔名> -k <AT 底線形>_ -q -p no:xdist -o addopts=`（`-k` 為錨定名，R135）；測試函式名為 `test_<AT 底線形>_<slug>`。Given 描述佈置、When 描述被測動作、Then／And 描述斷言；子情境以 `subTest` 實作並保留 AT ID 對映；AT 內不引用其他 AT 的 ID；不得 skip（NFR-P3-4）。
>
> **測試檔縮寫**（全部在 `tools/tests/`）：**MW**＝`test_selfimproving_measure.py`、**MV**＝`test_selfimproving_measure_verb.py`、**PB**＝`test_selfimproving_measure_probe.py`、**CR**＝`test_selfimproving_capacity_retire.py`、**M3**＝`test_selfimproving_p3_meta.py`（以上五檔為本檔新增）；**CP**＝`test_selfimproving_capability.py`（既有檔，新增 AT 函式並依 R134 同步站點）；**CN**＝`test_selfimproving_console_obs.py`（既有檔，新增 AT 函式；D12，沿用 P2 §5.5 的 `write_audit`、`body_decide`、`body_obs_add`、`body_obs_close`）。共用夾具住 `_selfimproving_p3_fixtures.py`（新增；底線開頭、不被收集；§5）。
>
> **P3 斷言簡寫**（其餘沿 P2 §2）：`R3`＝`make_p3_repo(...)` 回傳的 tmp git repo（§5.1），`TA`、`TP`、`D3`、`T1` 為其時間與路徑常數；`s1`＝基底 OBS 第 2 列的 ID（其根因鍵 `docs/stale-note` 已確認）；`P`、`P1`…＝PROP 號，執行期取自 `pid(n)` 或 CLI 輸出（本檔與測試不寫死不存在於真帳本的編號字面）；`win(R)`＝事件帳本中 `mea.*` 事件（依 `seq`）；`E0`、`G0`＝事件帳本位元組與 `git status --porcelain` 輸出的前置快照；S-…（情境）與 `promoted`、`root_attr`、`link_attr`、`mea_chain`、`obs_at`、`def_at`、`cap_index` 等建構器與向量表一律定義於 §5。

**A. 採納量測窗、回滾偵測與劣化暫停（MW）**

```gherkin
# AT-323-1-1
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R116～R119、R122）基線與開窗：S-BASE 的基線報告欄位與 mea.open 的次序；第二次呼叫零事件
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_1_ -q -p no:xdist -o addopts=

Feature: measure 的基線報告與開窗
Scenario: 晉升後第一次 measure 先寫基線報告再開窗，重跑不再寫
  Given `R3` 依 S-BASE 備妥（`P` 於 `TP` 晉升；b1～b9 列；b3、b5 的 link 已確認且 `seq` 小於晉升的 `seq`；b9 的 link 未落定）；`E0` 為事件帳本位元組
  When 呼叫 `M(R3, measure)` 兩次，兩次之間取 `win(R3)`
  Then 第一次 rc 為 `0`、輸出首行 `ok measure events=2 props=1`；`win(R3)` 恰兩行：依序 `mea.report`（`report` 為 `baseline`、`prop` 為 `P`、`promote_seq` 等於晉升事件的 `seq`、`opp` 依序為 b2、b4、b6、b7、b8 的 ID、`events` 為 `2`、`pending` 為 `1`、`w_opp`／`w_evt`／`w_min` 為 `5`／`2`／`5`、`anchor` 為 `2026-10-10T00:00:00+00:00`）與 `mea.open`（`w_opp` 為 `5`、`promote_seq` 同上）
  And 第二次 rc 為 `0`、首行 `ok measure events=0 props=1`、事件帳本位元組與第一次之後逐位元相同；`fold` 顯示 `P` 為 `measuring`；`MJ(R3, check)` 的 `events.mea` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_1]"
```
```gherkin
# AT-323-1-2
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R120）滿窗關閉 clean：第 w_opp 筆機會列為 DEF 列時以日末 instant 為 at；其後的列不計
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_2_ -q -p no:xdist -o addopts=

Feature: 採納窗滿窗關閉
Scenario: 第五筆機會列到達時窗關為 clean
  Given `R3` 依 S-BASE 與 S-ADOPT 的 a1～a6 備妥；尚未跑過 `measure`
  When 呼叫 `M(R3, measure)` 一次，再呼叫一次
  Then 第一次 rc 為 `0`、`events=3`；`win(R3)` 依序為 `mea.report`、`mea.open`、`mea.close`；`mea.close` 的 `result` 為 `clean`、`n_opp` 為 `5`、`at` 為 `2026-10-25T23:59:59+00:00`（a5 是 DEF 列，取日末 instant）
  And a6 不計入（`n_opp` 仍為 `5`）；`fold` 顯示 `P` 為 `closed`；第二次得 `events=0`；`MJ(R3, status)` 的 `measure.windows` 為一個元素，`state` 為 `closed`、`result` 為 `clean`、`n_opp` 為 `5`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_2]"
```
```gherkin
# AT-323-1-3
# 對應 AC: AC-323-1（PRD AC-SI-23-1、§1.3 (d)；R117 (b)(c)、R118、R120）M 類機會列以檔名引用或已確認根因鍵判；再現優先（確認得 recurred、駁回回頭算列、未決得 pending）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_3_ -q -p no:xdist -o addopts=

Feature: M 類機會列與再現優先
Scenario: 同一組列在候選 n1 的三種落定下各得不同窗結果
  Given 依 S-M 備三份 `R3` 複本（`Pm` 為 M 類、`target` 為記憶檔 `memory/feedback_demo.md`），只差候選 n1 的 link：(a) 已確認、(b) 已駁回、(c) 未落定
  When 對各複本呼叫 `M(R3, measure)`
  Then (a) `mea.close` 的 `result` 為 `recurred`、`n_opp` 為 `2`、`at` 為 `2026-10-22T12:00:00+00:00`（m1、m2 之後 n1 先到，n1 不算機會列）；(b) `result` 為 `clean`、`n_opp` 為 `5`、`at` 為 `2026-10-25T09:00:00+00:00`（機會列依序 m1、m2、n1、q1、q2；n1 被駁回而回頭計列）；(c) `result` 為 `pending`、`n_opp` 為 `5`、`at` 為 `2026-10-26T09:00:00+00:00`（機會列 m1、m2、q1、q2、q3；n1 歸屬而未決故暫不計）
  And 三份中 m3（證據路徑不在涵蓋範圍、無根因鍵）皆不計入；(c) 的 `fold` 顯示 `Pm` 為 `measuring`、(a)(b) 為 `closed`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_3]"
```
```gherkin
# AT-323-1-4
# 對應 AC: AC-323-1（PRD AC-SI-23-1、§1.3 (a)(b)；R117 (d)、R118 (d)）同一筆確認的再現只歸最近晉升的 PROP；窗重疊時各自累計同一筆機會列
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_4_ -q -p no:xdist -o addopts=

Feature: 再現歸屬與窗重疊
Scenario: 兩個 PROP 共用根因鍵時，再現只使後晉升者的窗 recurred；同一列可計入兩窗
  Given `R3` 內 `P1` 於 `2026-10-20T10:00:00+00:00`、`P2` 於 `2026-10-22T10:00:00+00:00` 晉升，兩者 `target` 皆在 `D3` 之下、`sources` 皆為 `s1`；子情境 (a)：列 a1（2026-10-21 09:00 +00:00）與 r1（2026-10-23 09:00 +00:00，標記 `reopens`＝`s1`，link 已確認）；(b)：列 a1（2026-10-22 11:00 +00:00）而無 r1
  When 對 (a)(b) 各呼叫 `M(R3, measure)` 並取 `MJ(R3, status)`
  Then (a) `P2` 的 `mea.close` 為 `recurred`、`n_opp` 為 `0`、`at` 為 `2026-10-23T09:00:00+00:00`；`P1` 沒有 `mea.close`（`fold` 為 `measuring`），其 `status.measure.windows` 的 `n_opp` 為 `2`（a1 與 r1；r1 對 `P1` 是歸屬於他 PROP 的一般列）
  And (b) `P1` 與 `P2` 皆為 `measuring` 且 `n_opp` 皆為 `1`（同一列 a1 同時計入兩窗）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_4]"
```
```gherkin
# AT-323-1-5
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R120 (a)(b)）回滾決定先於第 w_opp 筆機會列時關窗為 rolled-back；時點取 DEC 的 decided_at
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_5_ -q -p no:xdist -o addopts=

Feature: 回滾先到的窗
Scenario: 回滾決定使窗以 rolled-back 關閉，其後的列不計
  Given `R3` 依 S-BASE 與 S-ROLL 備妥（a1 在 2026-10-21 09:00 +00:00、a2 在 2026-10-22 09:00 +00:00；`P` 的 `dec(rollback)` 的 `decided_at` 為 2026-10-22T12:00:00+00:00；a3 在 2026-10-22 15:00 +00:00）
  When 呼叫 `M(R3, measure)` 兩次
  Then 第一次 `mea.close` 的 `result` 為 `rolled-back`、`n_opp` 為 `2`、`at` 為 `2026-10-22T12:00:00+00:00`；`fold` 顯示 `P` 為 `closed`
  And `win(R3)` 內沒有 `mea.amend`；第二次得 `events=0`；輸出沒有回滾提案卡區塊（已有 `dec(rollback)`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_5]"
```
```gherkin
# AT-323-1-6
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R120 (b)、R121 (a)(b)(e)）未決候選使滿窗記 pending，落定動詞於同一把鎖內追加 mea.amend 更正；mea.close 不改寫
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_6_ -q -p no:xdist -o addopts=

Feature: pending 的落定
Scenario: 候選全數落定時，落定動詞緊接追加 mea.amend，PROP 由 measuring 轉 closed
  Given `R3` 依 S-BASE 與 S-PEND 備妥（a1～a5 與候選 c1：2026-10-22 12:00 +00:00、標記 `reopens`＝`s1`、link 未落定，其 ATT 編號為 `T`）；兩份複本 (a)(b)，皆已呼叫一次 `M(R3, measure)`（得 `pending`）
  When 各取 `MJ(R3, status)`；(a) 以 CLI 呼叫 `attr-confirm --att <T> --by QA`（事件 `seq` 為 `k`）、(b) 呼叫 `attr-reject --att <T> --by QA --note <一句理由>`；各於其後立即取 `win(R3)` 與 `MJ(R3, status)`，再呼叫 `M(R3, measure)` 兩次
  Then 落定之前 `mea.close` 的 `result` 為 `pending`、`n_opp` 為 `5`、`at` 為 `2026-10-25T23:59:59+00:00`，`fold` 顯示 `P` 為 `measuring`，`status.measure.candidates_unsettled` 為 `1`、`pending_windows` 含 `P` 一筆；兩個落定動詞 rc 皆為 `0`
  And 事件帳本於落定事件之後緊接恰一筆 `mea.amend`（`seq` 為落定事件的 `seq` 加 `1`）：(a) `from` 為 `pending`、`to` 為 `recurred`、`cause` 為 `k`；(b) `to` 為 `clean`、`cause` 為該 `attr.reject` 的 `seq`；`window` 皆等於 `mea.close` 的 `seq`；此時（`measure` 之前）`status.measure.due` 為 `0`、`pending_windows` 為空、`fold` 顯示 `P` 為 `closed`；其後兩次 `measure` 皆 `events=0`、`mea.close` 位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_6]"
```
```gherkin
# AT-323-1-7
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R121 (c)(e)）晚到確認：關閉之前立案的再現列於關閉之後才被確認，落定動詞同鎖追加 amend 使 clean 窗成 recurred；關閉之後立案者不屬該窗
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_7_ -q -p no:xdist -o addopts=

Feature: 晚到確認
Scenario: 以立案時刻、不以確認時間判斷再現屬不屬於已關閉的窗
  Given `R3` 依 S-BASE 與 S-LATE：機會列 a1、a2、l1（2026-10-23 08:00 +00:00，無再現標記）、a4、a5 使窗於 `2026-10-25T23:59:59+00:00` 關為 `clean`（先跑一次 `measure`）；兩份複本：(a) 追加 l1 的 link（`reopens`＝`s1`，未落定）；(b) 追加列 l2（2026-10-27 09:00 +00:00）的 link（未落定）
  When 對各份以 CLI 呼叫 `attr-confirm --att <該 link 的 ATT> --by QA`（事件 `seq` 為 `k`），其後取 `MJ(R3, status)`，再呼叫 `M(R3, measure)` 兩次
  Then (a) 落定事件之後緊接恰一筆 `mea.amend`（`seq` 為 `k` 加 `1`、`from` 為 `clean`、`to` 為 `recurred`、`cause` 等於 `k`、`window` 等於 `mea.close` 的 `seq`），生效結果為 `recurred`；其後 `status.measure.due` 為 `0`、`rollback_pending` 含 `P`
  And (b) 落定事件之後沒有 `mea.amend`（l2 立案晚於關閉時點）、`due` 為 `0`；兩份其後的兩次 `measure` 皆得 `events=0`；兩份的 `mea.close` 位元組皆不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_7]"
```
```gherkin
# AT-323-1-E-1
# 對應 AC: AC-323-1（PRD AC-SI-23-1、§1.3〈M1 判定細則〉；R118 (c)、R119 (d)）基線確定性：晚於晉升才跑 measure、晉升之後才到的落定事件與根因確認不回補 events 與 pending
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_E_1_ -q -p no:xdist -o addopts=

Feature: 基線不回補
Scenario: 兩份只差執行時機的複本得到同一份基線報告
  Given 複本 `Ra`、`Rb` 皆依 S-BASE 備妥（b9 的 link 於晉升時未落定），但 `P` 的 `sources` 為 `s1` 與 `s2`（基底 OBS 第 3 列），並多一個候選 b10（2026-10-11 15:00 +00:00、座標在 `D3` 之下、`reopens` 為 `s3`〔基底 OBS 第 4 列〕；b10 的 link 與 `s3` 的根因鍵 `k/late` 的 root `attr` 皆於晉升之前已確認）；`Rb` 另追加（皆在晉升之後）：b9 的 link 的 `attr.confirm`、`s2` 的 root `attr`（鍵 `k/late`）與其 `attr.confirm`、S-ADOPT 的 a1、a2
  When 對 `Ra` 立即、對 `Rb` 於追加之後各呼叫 `M(R3, measure)`
  Then 兩者的 `mea.report`（baseline）除 `seq`、`t` 外逐鍵相同：`opp` 為 b10、b4、b6、b7、b8（b10 的鍵集合與 `P` 的不相交，視為一般列而把 b2 擠出窗），`events` 為 `2`，`pending` 為 `1`
  And `Rb` 的 b9 之確認既不增加 `events`（仍為 `2`）也不減少 `pending`（仍為 `1`）；`Rb` 於晉升之後才確認的 `s2` 根因鍵 `k/late` 不使 b10 轉為歸屬於 `P` 的再現（`events` 不變、b10 仍在 `opp`）；`Rb` 的 a1、a2 不出現在 `opp`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_E_1]"
```
```gherkin
# AT-323-1-E-2
# 對應 AC: AC-323-1（PRD AC-SI-23-1、§1.3〈M1 判定細則〉；R116 (b)(c)(e)、R117 (a)）錨與晉升邊界、日精度、缺 offset、目錄整段相符與大小寫
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_E_2_ -q -p no:xdist -o addopts=

Feature: 列的邊界與機會列規則負控
Scenario: 依 S-BOUND 逐列判屬基線、採納窗或不屬任何窗
  Given `R3` 依 S-BOUND 備妥（`P` 於 `TP` 晉升；x1～x3、y1～y5、z1～z3 各列；OBS 帳本檔頭 tz 為 `+08:00`）
  When 呼叫 `M(R3, measure)` 後取 `win(R3)` 與 `MJ(R3, status)`
  Then 基線報告的 `opp` 恰為 x3、y1（x1 早於錨、x2 為錨前一日的 DEF 而日末 instant 早於錨，皆排除；x3 為錨同日的 DEF 而納入；y1 在晉升前一分鐘）、`anchor` 為 `2026-10-10T00:00:00+00:00`
  And `status.measure.windows[0].n_opp` 為 `4`（y3、y4〔與晉升同日的 DEF〕、y5〔無 offset，取檔頭 tz 得 10:30Z〕、z2〔證據路徑大小寫不同〕）；y2（與晉升同刻）、z1（目錄名只是前綴相似）、z3（證據無路徑）皆不計入任何窗
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_E_2]"
```
```gherkin
# AT-323-1-E-3
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R122 (d)、R130 (c)）錨或帳本不可用時 fail-loud，不寫出不可恢復的基線；不需輸入時不要求
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_E_3_ -q -p no:xdist -o addopts=

Feature: 輸入不可用
Scenario: 五份複本各缺一種輸入
  Given 五份 `R3` 複本，前四份皆含一個尚無 baseline 的 promoted PROP：(a) `migration_base_sha` 為 null；(b) 其值為不是 commit 的 40 位 hex；(c) OBS 帳本檔被移除；(d) 缺陷帳本家族全部移除；(e) 對照組：與 (a) 同但沒有任何 promoted PROP
  When 對各份呼叫 `M(R3, measure)` 與 `MJ(R3, status)`
  Then (a)(b) rc 為 `1`、碼 `ANCHOR-UNAVAILABLE`；(c) 碼 `OBS-LEDGER-UNAVAILABLE`；(d) 碼 `DEFECT-LEDGER-UNAVAILABLE`；皆於輸出末尾印 `obs-draft:` 與一行草稿列（`draft_ok`）、事件帳本位元組逐位元不變
  And (e) rc 為 `0`、`events=0`、`status.measure.status` 為 `read`；(a)～(d) 的 `status.measure` 為 `NOT-EVALUABLE`，理由依序為 `anchor-unavailable`、`anchor-unavailable`、`obs-ledger-unavailable`、`defect-ledger-unavailable`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_E_3]"
```
```gherkin
# AT-323-1-E-4
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R114 (b)(c)、R115）不合法的 mea.amend 與第二個 mea.open 不生效並記 TRANSITION-ILLEGAL；欄位合法者 events.mea 不重報
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_E_4_ -q -p no:xdist -o addopts=

Feature: 偽造 amend 的處置
Scenario: 四種不合法的 amend 與第二個 mea.open 都被忽略
  Given `R3` 內 `P1`、`P2` 各有 baseline、open、close（`P1` 為 `clean`、`P2` 為 `recurred`；以 `mea_chain` 手寫）；五份複本各追加一筆手寫事件：(a) `prop` 為 `P1` 而 `window` 指向 `P2` 的 `mea.close` 的 amend；(b) `P1` 的 amend 其 `from` 為 `pending`；(c) `P2` 的 amend `from` 為 `recurred`、`to` 為 `clean`；(d) `P1` 的 amend 其 `window` 指向 `P1` 的 `mea.open` 的 `seq`；(e) `P1` 的第二個 `mea.open`
  When 對各份取 `fold` 與 `MJ(R3, check)`
  Then 五份的 `P1`、`P2` 生效結果不變（`clean`、`recurred`）、PROP 態仍為 `closed`；`events.transitions` 為 `FAIL`，findings 含 `TRANSITION-ILLEGAL`（subject 為該事件的 PROP）
  And `events.mea` 對這五筆事件為 `PASS`（欄位本身合法，不重報）；`MJ(R3, status)` 的 `measure.windows` 的 `result` 仍為 `clean` 與 `recurred`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_E_4]"
```
```gherkin
# AT-323-1-E-5
# 對應 AC: AC-323-1（PRD AC-SI-23-1；R121 (e)、R122 (a)(c)）attr 動詞的同鎖追加被替身略過：status.measure.due 為 1、measure 補記後為 0，補記的 amend 與同鎖路徑逐鍵相同
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + mock.patch.object（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_1_E_5_ -q -p no:xdist -o addopts=

Feature: measure 補記未被 attr 動詞追加的 amend
Scenario: attr 動詞的追加被替身略過時，due 為 1，measure 補上同一筆 amend
  Given 兩份複本 `Rx`、`Ry` 皆依 S-BASE 與 S-PEND 備妥並各已呼叫一次 `M(Rx, measure)`、`M(Ry, measure)`（窗為 `pending`）；`Rx` 於 `mock.patch.object` 把 `meawrite.plan_amends` 換成回空清單的替身之下、`Ry` 不替身，各以行程內入口呼叫 `attr-confirm --att <c1 的 link 的 ATT> --by QA`
  When 對 `Rx` 先取 `win(Rx)` 與 `MJ(Rx, status)`，再呼叫 `M(Rx, measure)` 兩次並再取 `win(Rx)`；對 `Ry` 取 `win(Ry)`
  Then `Rx` 於 attr 動詞之後、`measure` 之前沒有 `mea.amend`、`status.measure.due` 為 `1`；第一次 `measure` 輸出首行為 `ok measure events=1 props=1`、追加恰一筆 `mea.amend`，其後 `due` 為 `0`；第二次得 `events=0`
  And `Rx` 補記的 `mea.amend` 與 `Ry` 同鎖追加者除 `seq`、`t`、`by` 外逐鍵相同（`from` 為 `pending`、`to` 為 `recurred`、`cause`、`window` 相同）；兩份 `fold` 皆顯示 `P` 為 `closed`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_1_E_5]"
```
```gherkin
# AT-323-2-1
# 對應 AC: AC-323-2（PRD AC-SI-23-2；R123）窗以 recurred 關閉後 measure 印回滾提案卡；狀態導出（重跑重印）、記下回滾決定後不再印；樣板行可被決定語法解析
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_2_1_ -q -p no:xdist -o addopts=

Feature: 回滾提案卡
Scenario: 已確認的再現使 measure 印出卡面，且不下任何決定
  Given `R3` 以 `drive_to(R3, promoted)` 取得 `P`（`prop-new` 本文欄位表的 `rollback` 為字面 `還原該行`）；`s1` 的根因鍵已確認且列為 `P` 的 `sources`；晉升事件 `t` 加 1 日的列 a1、加 2 日的列 r1（標記 `reopens`＝`s1`，link 與 `attr.confirm` 已寫）補入 OBS 帳本；`E0`、`G0` 為前置快照
  When 呼叫 `M(R3, measure)` 與 `MJ(R3, measure)`，其後追加 `P` 的 `dec(rollback)`（`decide_say`）並再呼叫 `M(R3, measure)`
  Then 輸出含一個區塊，首行符合 `^\[<P>\] 回滾提案｜窗：recurred｜digest：[0-9a-f]{8}$`；核心區（分界線之前）至多 12 行、每行顯示寬度至多 `card_line_max`；含 r1 的 ID 與證據座標、link 的 `ATT-SI-` 編號與確認者標籤、`app.promote` 的 `seq`、字面 `還原該行`；分界線之下的樣板行把一句理由代入後，`decgrammar.parse` 得動詞 `回滾`、`id` 為 `P`
  And `--json` 的 `rollback_cards` 為單一元素；第二次呼叫（未記決定）輸出同一區塊且 `events=0`；`git status --porcelain` 相對 `G0` 只多事件帳本一個路徑；記下 `dec(rollback)` 之後的呼叫不再印該區塊
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_2_1]"
```
```gherkin
# AT-323-2-E-1
# 對應 AC: AC-323-2（PRD AC-SI-23-2；R123 (a)、R130 (c)）沒有已確認再現的窗不印卡；僅有未決候選時只在 status 印候選數與 pending 的窗
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_2_E_1_ -q -p no:xdist -o addopts=

Feature: 不印卡的情形
Scenario: 五種窗狀態皆不產生回滾提案卡
  Given 五份 `R3` 複本：(a) 窗 `measuring` 且有一個未決候選；(b) 窗 `pending`（S-PEND）；(c) 窗 `clean`（S-ADOPT）；(d) 窗 `rolled-back`（S-ROLL）；(e) 窗 `recurred` 但 `P` 已有 `dec(rollback)`
  When 對各份呼叫 `M(R3, measure)` 與 `MJ(R3, status)`
  Then 五份的輸出皆不含 `回滾提案` 字樣、`rollback_cards` 皆為空清單、`status.measure.rollback_pending` 皆為空清單；(a) 的 `status.measure.candidates_unsettled` 為 `1`、(b) 的 `status.measure.windows` 含 `state` 為 `pending` 的元素
  And 再於 (c) 追加一個已確認的 link（再現列立案早於關閉時點）後呼叫 `measure`：追加 `mea.amend`（`clean` 到 `recurred`），該次輸出含 `回滾提案` 區塊、`rollback_pending` 含 `P`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_2_E_1]"
```
```gherkin
# AT-323-2-E-2
# 對應 AC: AC-323-2（PRD AC-SI-23-2；R111、R122 (f)、R123 (c)）measure 只追加四種 mea 事件、絕不下決定、不改工作樹；無人值守一律拒收
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_323_2_E_2_ -q -p no:xdist -o addopts=

Feature: measure 不下決定
Scenario: 事件種類與工作樹的不變量，及 AUTOSDD_UNATTENDED 的拒收
  Given 四份 `R3` 複本依 S-ADOPT（clean）、S-REC、S-ROLL、S-PEND 備妥；`G0` 為各份的 `git status --porcelain` 輸出與 HEAD；另一份備妥複本供無人值守案例
  When 對四份各呼叫 `M(R3, measure)`；對另一份在 `AUTOSDD_UNATTENDED` 為 `0` 與為 `1` 時各呼叫一次
  Then 各份追加的事件 kind 集合是 `mea.report`、`mea.open`、`mea.close`、`mea.amend` 的子集（沒有 `dec`、`app.*`、`attr*`）；`git status --porcelain` 相對 `G0` 只多事件帳本一個路徑、HEAD 不變
  And 兩次無人值守呼叫皆 rc 為 `1`、碼 `UNATTENDED-REFUSED`、事件帳本與家目錄位元組不變、輸出末尾有 `obs-draft:`；移除環境變數後同一呼叫 rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_323_2_E_2]"
```
```gherkin
# AT-324-1-1
# 對應 AC: AC-324-1（PRD AC-SI-24-1；R114 (e)）連續兩個壞窗使迴圈 SUSPENDED、其所在運轉由重放導出；唯有 dec(resume) 解除
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_324_1_1_ -q -p no:xdist -o addopts=

Feature: SUSPENDED 與恢復
Scenario: 兩個壞窗暫停迴圈，恢復後 prop-new 重新受理
  Given `R3` 依 S-SUSP：運轉 1 與其研究事件、`mea_chain` 得 `A`（`recurred`）、運轉 2 與其研究事件、`mea_chain` 得 `B`（`rolled-back`）；`stop_after_bad` 為 `2`；備妥一個對運轉 2 的 `prop-new` 呼叫（`try_prop`）
  When 取 `MJ(R3, status)`；呼叫 `prop-new`；以 `decide_say` 受理 `恢復 <運轉 2> 已人工檢視` 後再取 `status` 並重送 `prop-new`
  Then 第一次 `status.suspended.run` 等於運轉 2 的 ID（最後一個壞窗 `mea.close` 之前最近一筆 `run.open`）；`prop-new` rc 為 `1`、碼含 `SUSPENDED`、`snap(R3)` 不變
  And `decide` rc 為 `0` 之後 `status.suspended` 為 null、重送的 `prop-new` rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_324_1_1]"
```
```gherkin
# AT-324-1-2
# 對應 AC: AC-324-1（PRD AC-SI-24-1；R114 (e)、R121 (a)）pending 的窗既不計入也不打斷連續；經 amend 落定後依生效結果重判
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_324_1_2_ -q -p no:xdist -o addopts=

Feature: pending 與連續壞窗
Scenario: 壞、pending、壞成立；pending 落定為 clean 後不成立、落定為 recurred 後成立
  Given `R3` 內三個 `mea_chain` 窗依 `mea.close` 序為 `A`（`recurred`）、`B`（`pending`）、`C`（`recurred`），其間各有 `run.open`；兩份複本另各追加 `B` 的 `mea.amend`（`cause` 為合法落定事件的 `seq`）：(a) `pending` 到 `clean`、(b) `pending` 到 `recurred`；`stop_after_bad` 為 `2`
  When 對原始、(a)、(b) 取 `MJ(R3, status)`
  Then 原始 `status.suspended` 非 null（忽略 `pending` 後 `A` 與 `C` 相鄰皆壞）；(a) 為 null（有效序列為壞、clean、壞）；(b) 非 null（壞、壞、壞）
  And 三者的 `status.pending_windows` 依序含 `B` 一筆、空、空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_324_1_2]"
```
```gherkin
# AT-324-1-E-1
# 對應 AC: AC-324-1（PRD AC-SI-24-1；R114 (e)）不成立的序列與 stop_after_bad 的門檻邊界；參數隨動
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_324_1_E_1_ -q -p no:xdist -o addopts=

Feature: SUSPENDED 不成立的情形
Scenario: 五種序列與門檻的邊界
  Given 以 `mea_chain` 組成的序列，皆無 `dec(resume)`：(a) 單一 `recurred`；(b) `recurred`、`clean`、`recurred`；(c) `recurred`、`rolled-back`，`stop_after_bad` 為 `3`；(d) `recurred`、`rolled-back`、`recurred`，`stop_after_bad` 為 `3`；(e) `clean`、`recurred`、`rolled-back`，`stop_after_bad` 為 `2`
  When 對各情境取 `status.suspended`；另對 (d) 以 `set_params` 把 `stop_after_bad` 改為 `4` 後再取
  Then (a)(b)(c) 為 null；(d)(e) 非 null（(e) 取最近連續兩個）
  And (d) 改為 `4` 之後為 null
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_324_1_E_1]"
```
```gherkin
# AT-324-1-E-2
# 對應 AC: AC-324-1（PRD AC-SI-24-1；R114 (e)、P2 R93、§7.1 ⚖ 9）恢復綁定折疊出的運轉、不歸零連續計數；恢復後 pending 窗轉壞會再度暫停
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_324_1_E_2_ -q -p no:xdist -o addopts=

Feature: 恢復的綁定與邊界
Scenario: 錯誤的恢復被拒，合法恢復後新的壞窗與落定的 pending 窗各自重判
  Given `R3` 為 S-SUSP 的 SUSPENDED 狀態（`A`、`B` 皆壞，所在運轉 `U`）；`stop_after_bad` 為 `2`
  When (a) 以 `decide_say` 受理 `恢復 <另一個運轉> …`；(b) 對未暫停的複本受理 `恢復 <U> …`；(c) 受理 `恢復 <U> …` 後手寫追加 `C`（`mea_chain`，`recurred`）；(d) 受理後追加 `D`（`pending`）再追加其 `mea.amend`（`pending` 到 `recurred`）
  Then (a) rc 為 `1`、碼 `RUN-MISMATCH`；(b) rc 為 `1`、碼 `NOT-SUSPENDED`；皆零殘留
  And (c) `status.suspended` 非 null（`B` 與 `C` 相鄰皆壞，恢復不歸零）；(d) 追加 `D` 的 `pending` 時為 null、amend 之後非 null
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_324_1_E_2]"
```
```gherkin
# AT-324-2-1
# 對應 AC: AC-324-2（PRD AC-SI-24-2；R114 (e)）SUSPENDED 期間觀察擷取與唯讀動詞照常，與未暫停時行為逐一相同
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_324_2_1_ -q -p no:xdist -o addopts=

Feature: 暫停期間的觀察
Scenario: 同一組動詞在兩份只差暫停與否的複本上得同樣的結果
  Given `Rs`（依 S-SUSP 為 SUSPENDED）與 `Rn`（相同事件但最後一個壞窗改為 `clean`，故未暫停）；兩份各有一個 open 運轉
  When 對兩份各依序呼叫：`run-open`、`research --skip`、`attr --type root` 加 `attr-confirm`、`scan`、`status`、`check`、`export --kind events`、`measure`、`capacity`、`obs-add --dry-run`
  Then 兩份對每個動詞的 rc 與拒收碼集合逐一相同；`Rs` 的 `status.suspended` 非 null、`Rn` 為 null
  And `Rs` 在這些呼叫之後 `status.suspended` 仍非 null
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_324_2_1]"
```
```gherkin
# AT-324-2-E-1
# 對應 AC: AC-324-2（PRD AC-SI-24-2；R114 (e)、P2 R93、§7.1 ⚖ 9）prop-new 與 prop-revise 於 SUSPENDED 拒收；在途提案的人工閘不被 SUSPENDED 擋
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure.py -k AT_324_2_E_1_ -q -p no:xdist -o addopts=

Feature: 暫停期間的提案
Scenario: 新提案被擋，在途提案照常走人工閘
  Given `Rs` 為 SUSPENDED；另有一個在途 PROP `Q`（態 `proposed`，於暫停之前建立）與一個被退回的 PROP `Z`（態 `returned`）
  When 呼叫 `prop-new`、`prop-revise Z`；呼叫 `card --issue Q` 與 `decide_say` 受理 `核准 Q`
  Then `prop-new` 與 `prop-revise` 皆 rc 為 `1`、碼含 `SUSPENDED`、`snap(Rs)` 不變
  And `card --issue Q` rc 為 `0`、`decide` rc 為 `0` 且 `Q` 轉 `approved`（兩者輸出都不出現 `SUSPENDED`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_324_2_E_1]"
```

**B. `mea.*` 欄位表、`measure` 動詞、`status`／`export` 增量（MV）**

```gherkin
# AT-340-1-1
# 對應 AC: AC-340-1（本檔自增；PRD §9.2 `mea.*` 列；R113、R115）measure 寫出的四種事件鍵集合恰為欄位表，check 為 33 項且綠
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_1_1_ -q -p no:xdist -o addopts=

Feature: mea.* 欄位表與 events.mea
Scenario: 三份複本 measure 之後 check 全綠
  Given 三份 `R3` 複本：(a) 依 S-BASE 與 S-ADOPT（窗 `clean`）；(b) 依 S-REC（`recurred`）；(c) 依 S-PEND 並追加 `attr.confirm`（先 `pending`、後 `mea.amend`）
  When 對各份呼叫 `M(R3, measure)`，再取 `MJ(R3, check)`
  Then 各份 `check` 的 `items` 為 33 項、第 33 項 id 為 `events.mea` 且為 `PASS`、`events.transitions` 為 `PASS`、`overall` 為 `PASS`、rc 為 `0`
  And 被寫出的各事件鍵集合恰為 R113 的欄位表加共通鍵（baseline 十鍵、`mea.open` 三鍵、`mea.close` 四鍵、`mea.amend` 五鍵）、`t` 為帶 offset 的秒精度、`by` 為 `main`、行長不超過 `event_max_bytes`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_1_1]"
```
```gherkin
# AT-340-1-E-1
# 對應 AC: AC-340-1（本檔自增；R113、R115）欄位表負控：十四種變體各使 events.mea 恰報預期碼，對照組為 PASS
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_1_E_1_ -q -p no:xdist -o addopts=

Feature: mea.* 欄位表負控
Scenario: 每個變體只改一處，只觸發規定的碼
  Given 一份依 S-ADOPT 跑過 `measure` 的合規 `R3` 帳本（對照組）；§5.4 的 MEA-NEG 表十四列，每列為對該帳本複本的一處改寫或一筆手寫追加事件
  When 對對照組與每個變體取 `MJ(R3, check)`
  Then 對照組的 `events.mea` 為 `PASS`；每個變體的 `events.mea` 為 `FAIL`，其 findings 的碼集合恰等於該列的預期碼集合
  And 每個變體的其他 P0～P2 項目狀態與對照組相同（除 MEA-NEG 表註明會連帶出現的 `events.transitions` 者）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_1_E_1]"
```
```gherkin
# AT-340-1-E-2
# 對應 AC: AC-340-1（本檔自增；R115、P2 R98）判準版本、項目次序與載體缺席
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_1_E_2_ -q -p no:xdist -o addopts=

Feature: check 的判準版本與載體缺席
Scenario: 33 項、判準版本 4、無事件帳本時 NE 非阻塞
  Given P0 基線 repo（無事件帳本）、有事件帳本而無任何 `mea.*` 的 repo、依 S-ADOPT 跑過 `measure` 的 repo
  When 對三者取 `MJ(R3, check)`
  Then 三者的 `fingerprint_parts.check_rules_rev` 皆為 `4`；前 32 項的 id 與次序等於 P2 的 32 項常數表（`p1_items` 的 28 項加 P2 四項）、第 33 項為 `events.mea`
  And 無事件帳本者的 `events.mea` 為 `NE` 且 `blocking` 為 `false`、碼 `CARRIER-NOT-ESTABLISHED`，其 `overall` 與 rc 相同於升級前的 P0 基線值；其餘兩者的 `events.mea` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_1_E_2]"
```
```gherkin
# AT-340-2-1
# 對應 AC: AC-340-2（本檔自增；R111、R112、R122）measure 的 CLI 契約：成功文字與 JSON 鍵序、事件次序、--by 標籤、第二次零事件、鎖釋放
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_2_1_ -q -p no:xdist -o addopts=

Feature: measure 的輸出契約
Scenario: 成功文字、JSON 鍵序與事件次序
  Given `R3` 依 S-BASE 與 S-ADOPT 備妥；`HOME` 為 tmp 家目錄
  When 呼叫 `M(R3, measure, --by, ops1)`，再呼叫 `MJ(R3, measure)`
  Then 首次輸出首行 `ok measure events=3 props=1`、次行符合 `^window <P> state=closed result=clean n_opp=5/5 baseline=2/5$`；三筆新事件的 `by` 皆為 `ops1`、`kind` 依序為 `mea.report`、`mea.open`、`mea.close`
  And 第二次 `--json` 輸出為單一物件，鍵序恰為 `ok`、`kind`、`events`、`props`、`appended`、`windows`、`rollback_cards`、`check_report`，其中 `events` 為 `0`、`appended` 為空清單、`check_report` 為 null；`HOME` 內除已釋放的鎖檔外無新檔
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_2_1]"
```
```gherkin
# AT-340-2-2
# 對應 AC: AC-340-2（本檔自增；PRD §8.1 P3 出口 (d)；R122 (e)）--record-check 留反證條件紀錄：內容相同不重複、內容變則再追加、NE 也記並寫缺什麼
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_2_2_ -q -p no:xdist -o addopts=

Feature: measure 的全域檢查報告
Scenario: 兩份複本各記一筆全域報告
  Given 兩份 `R3`：(a) 依 S-PROBE-A 備妥（八個 PROP 的 `mea.*` 已手寫）；(b) 沒有任何 promoted PROP
  When 對 (a)(b) 各呼叫 `M(R3, measure, --record-check)` 兩次；再於 (a) 追加一個 `clean` 的可評估窗後呼叫一次
  Then (a) 首次追加一筆 `mea.report`（`report` 為 `check`、無 `prop` 鍵、`windows` 為 `3`、`m1_n` 為 `3`、`m4` 為 `0`、`m5_n` 為 `6`、`falsified` 為 `false`、`metrics_rev` 為 `1`、`fingerprint` 等於探針對同 repo 輸出的 `fingerprint`）；第二次不追加且輸出 `check-report appended=false`；新增窗後內容改變而再追加一筆
  And (b) 仍追加一筆（`windows` 為 `0`、`m1` 為 null、`falsified` 為 null、`missing` 非空且含 `no-evaluable-window`）；兩筆報告的行長皆不超過 `event_max_bytes`，`check` 的 `events.mea` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_2_2]"
```
```gherkin
# AT-340-2-E-1
# 對應 AC: AC-340-2（本檔自增；R111、R122 (d)、P2 R70）拒收與用法錯誤的碼、rc 與零殘留
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_2_E_1_ -q -p no:xdist -o addopts=

Feature: measure 的拒收與用法錯誤
Scenario: 七種成因各得規定的 rc 與碼
  Given 一份依 S-ADOPT 備妥而有待寫事件的 `R3`，與其 `E0`、家目錄快照 `H0`
  When 依序：(a) `AUTOSDD_UNATTENDED` 為 `0`；(b) 為 `1`；(c) 未知旗標 `--force`；(d) `--by` 為含空白的字串；(e) `params.json` 缺 `w_opp`；(f) `AUTOSDD_SI_DIR` 指向不可寫路徑；(g) 另一行程持有寫入鎖（以 `evwrite.LOCK_TIMEOUT_SECONDS` 改小）
  Then (a)(b) rc 為 `1`、碼 `UNATTENDED-REFUSED`；(c)(d)(e) rc 為 `3`、stderr 以 `selfimproving:` 起頭（(e) 點名 `w_opp`，不以預設值頂替）；(f) rc 為 `3`、碼 `HOME-UNWRITABLE`；(g) rc 為 `1`、碼 `LOCK-BUSY`
  And 全部情境事件帳本位元組皆等於 `E0`、rc 為 `1` 者輸出末尾有 `obs-draft:`；各情境移除成因後同一呼叫 rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_2_E_1]"
```
```gherkin
# AT-340-2-E-2
# 對應 AC: AC-340-2（本檔自增；R122 (b)(c)、ADR-SI-10）兩個執行緒同時 measure 不產生重複的 baseline、open 或 close
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_2_E_2_ -q -p no:xdist -o addopts=

Feature: measure 的並行
Scenario: 交錯的兩個 measure 只產生一組事件
  Given `R3` 依 S-BASE 與 S-ADOPT 備妥；以 `evwrite.PAUSE_HOOK` 令兩個執行緒在讀末行並配號之後、追加之前交錯
  When 以 `ThreadPoolExecutor` 同時呼叫 `meawrite.measure(R3, …)` 兩次並以 `future.result()` 取回
  Then 兩次回傳 rc 皆為 `0`；事件帳本中該 PROP 恰一筆 baseline、一筆 `mea.open`、一筆 `mea.close`，`seq` 連續無重複、每行為完整 JSON
  And 兩次回傳的 `events` 之和等於實際新增的事件行數
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_2_E_2]"
```
```gherkin
# AT-340-5-1
# 對應 AC: AC-340-5（本檔自增；PRD AC-SI-03-1 (e)；R130 (a)(b)(c)）status 共 15 鍵、capacity 對預設路徑記憶索引可評估並列入容量事件、measure 物件
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_5_1_ -q -p no:xdist -o addopts=

Feature: status 的 P3 增量
Scenario: capacity 與 measure 由占位轉為可評估
  Given `R3` 依 S-ADOPT 備妥（窗 `closed`）；`CLAUDE_CONFIG_DIR` 的 `projects/<slug>/memory/MEMORY.md` 依 `cap_index` 組成 18 行，`set_params` 把 `memory_index_max_lines` 設為 `20`（用量比恰 0.9）；對照複本沒有該檔
  When 取 `MJ(R3, status)` 與 `M(R3, status)`
  Then 鍵序為 P2 的前 14 鍵（`events_detected` 至 `console_pending`）接 `measure` 共 15 鍵；`measure` 物件的 `status` 為 `read`、`due` 為 `0`、`windows` 為含一個 closed 窗的清單、`candidates_unsettled` 為 `0`、`rollback_pending` 為空清單
  And 有該檔的複本：`capacity.status` 為 `read`、`capacity.over_cap` 恰含 `memory_index` 一項、`events_detected` 含一筆 `trigger` 為 `e` 的元素；對照複本 `capacity` 的 `status` 為 `NOT-EVALUABLE`、`reason` 為 `no-axis-evaluable`、文字形態含 `capacity NOT-EVALUABLE`；`pending_windows`、`root_cause_changes`、`reopen_candidates` 的值語意與 P1 相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_5_1]"
```
```gherkin
# AT-340-5-2
# 對應 AC: AC-340-5（本檔自增；R130 (e)(f)(g)）export 的 proposals 項帶 window 末鍵、status 的 capacity 恆 NE，且不讀家目錄
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_5_2_ -q -p no:xdist -o addopts=

Feature: export 的 P3 增量
Scenario: window 末鍵與 capacity 的 NE 值
  Given `R3` 內三個 PROP：無 `mea.open` 者、`measuring` 者、`closed`（`clean`）者；家目錄放一個哨兵檔（內容含獨特字串）；`CLAUDE_CONFIG_DIR` 內放一個記憶索引檔
  When 呼叫 `MJ(R3, export, --kind, proposals)` 與 `MJ(R3, export, --kind, status)`
  Then proposals 的每個 PROP 物件在 `card` 之後多末鍵 `window`：無窗者為 null、其餘為含 `state`、`opened_seq`、`closed_seq`、`result`、`n_opp`、`baseline` 六個子鍵的物件（`measuring` 者 `closed_seq` 與 `result` 為 null；`closed` 者 `result` 為 `clean`）；`schema_rev` 仍為 `1`
  And status 的 `items[0].capacity` 恆為 `status` 等於 `NOT-EVALUABLE` 且 `reason` 等於 `export-reads-no-home` 的物件、`items[0]` 為 15 鍵；兩個輸出皆不含哨兵字串與記憶索引內容；`snap(R3)` 與家目錄位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_5_2]"
```
```gherkin
# AT-340-5-E-1
# 對應 AC: AC-340-5（本檔自增；R130 (c)、NFR-P3-11）量不到時印 NE 與理由、唯讀零寫入；status 與 export 的 measure 值逐位元相同
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_verb.py -k AT_340_5_E_1_ -q -p no:xdist -o addopts=

Feature: status 的量不到
Scenario: 四份複本各缺一種載體或輸入
  Given 四份複本：(a) 無事件帳本；(b) 有 promoted PROP 而 `migration_base_sha` 為 null；(c) 有 promoted PROP 而缺陷帳本家族不存在；(d) 事件帳本只有運轉事件（無 promoted PROP）
  When 對各份取 `MJ(R3, status)` 與 `MJ(R3, export, --kind, status)`
  Then (a) `measure` 的 `status` 為 `NOT-EVALUABLE`、`reason` 為 `carrier-not-established`；(b) 理由 `anchor-unavailable`；(c) 理由 `defect-ledger-unavailable`；(d) 為 `read`、`due` 為 `0`、`windows` 為空清單
  And 各份 `snap(R3)` 與家目錄位元組在呼叫前後相同；`status` 與 `export` 兩者的 `measure` 值逐位元相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_5_E_1]"
```

**C. 量測腳本（PB）**

```gherkin
# AT-322-1-1
# 對應 AC: AC-322-1（PRD AC-SI-22-1；R124 (a)(b)、R126 (b)）M1 per-PROP：S-PROBE-A 的可評估窗、值與 n、每 PROP 的基線事件數與機會列數、NE 理由碼；JSON 與文字兩形態
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_1_1_ -q -p no:xdist -o addopts=

Feature: 量測腳本的 M1
Scenario: 八個 PROP 中三個可評估，M1 為三分之一
  Given `R3` 依 S-PROBE-A 備妥（八個 PROP 的 `mea.*` 與根因鍵手寫；§5.2 表）
  When 以子行程執行 `python tools/probe/selfimproving_measure.py --repo <R3> --json`，再以文字形態執行一次
  Then rc 為 `0`；`success.m1` 的 `n` 為 `3`、`recurred` 為 `1`、`value` 與三分之一相差小於 1e-9；`per_prop` 為八列，`evaluable` 為真者恰 P1、P2、P7；P3、P4、P5、P6、P8 的 `reason` 依序為 `BASELINE-EVENTS-BELOW-W-EVT`、`BASELINE-ROWS-BELOW-W-MIN`、`WINDOW-PENDING`、`ROLLED-BACK-NO-RECURRENCE`、`WINDOW-OPEN`；每列帶 `events` 與 `opp_n`（P1 為 `2` 與 `5`）
  And 文字形態的 `== 成功指標 ==` 之下列出 M1 的值與 `n=3` 及各 NE 理由碼；`falsification.falsified` 為 `false`、`falsified_keys` 為空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_1_1]"
```
```gherkin
# AT-322-1-2
# 對應 AC: AC-322-1（PRD AC-SI-22-1、§1.3；R125、R126 (b)）M4、M5 兩值與 m5 鍵集合、資訊欄各計數與 M2、M3、全域窗
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_1_2_ -q -p no:xdist -o addopts=

Feature: 量測腳本的 M4、M5 與資訊欄
Scenario: 成功指標與資訊欄各欄的值
  Given `R3` 依 S-PROBE-A 並追加：S-M23 的五個 `fixed@` DEF 列與一個 `closed-by-decision` 列（基底缺陷帳本原有的一列 `fixed@` 其 sha 在 tmp repo 不存在，無法解析）；一組冷卻繞過情境（被否決的 PROP `Q1` 與其後同型的 `Q2`，`fold` 產生一筆 `COOLDOWN-BYPASS-SUSPECT`）
  When 執行探針（`--json`）
  Then `success.m4` 的 `value` 為 `1` 且 `drafts` 含一列 OBS 草稿（`draft_ok`）；`success.m5` 的鍵恰為 `main`、`all`，各只含 `status`、`value`、`n`（無趨勢、門檻或判定鍵）：`main` 的 `value` 為 `0.0`、`n` 為 `5`，`all` 的 `value` 與六分之一相差小於 1e-9、`n` 為 `6`（分母為窗已關閉的 P1、P2、P3、P4、P6、P7；分子只有 P6 的窗內回滾）
  And `info`：`proposals` 為 `10`、`decisions` 中 `approve` 為 `8`、`promote` 為 `8`、`rollback` 為 `1`、`reject` 為 `1`、`obs_rows` 等於獨立解析所得的合法列數、`closed_by_decision` 為 `1`、`unverified_ack` 為 `1`、`m2` 的 `value` 為 `5`、`n` 為 `5`、`excluded` 為 `1`、`m3` 與 `global_m1` 為 NE（`reason` 為 `sample-below-w-min`）；`success` 區不含任何資訊欄鍵
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_1_2]"
```
```gherkin
# AT-322-1-E-1
# 對應 AC: AC-322-1（PRD AC-SI-22-1；R124 (a)(b)、NFR-P3-11）M1 的每一條 NE 規則獨立成立，NE 不被印成 0
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_1_E_1_ -q -p no:xdist -o addopts=

Feature: M1 的 NOT-EVALUABLE
Scenario: 基線不足、無基線、錨缺席與無可評估窗
  Given (a) S-PROBE-A 加 P9（基線 `events` 為 `0`、`opp` 為 5 筆、窗 `clean`）與 P10（promoted 而沒有任何 `mea.*`）；(b) 同 (a) 但 `migration_base_sha` 為 null；(c) 唯一的 promoted PROP 為 S-PROBE-A 的 P3（基線事件數 `1`）
  When 對三份各執行探針（`--json` 與文字形態）
  Then (a) P9 的 `reason` 為 `BASELINE-EVENTS-BELOW-W-EVT`（0 不算未低於也不算已改善）、P10 為 `NO-BASELINE`；(b) 的 `success.m1` 與 (a) 相同（M1 不讀錨），`info.global_m1` 的 `reason` 為 `anchor-unavailable`
  And (c) 的 `success.m1` 的 `status` 為 `NOT-EVALUABLE`、`reason` 為 `no-evaluable-window` 且 `n` 為 `0`、不含 `value` 鍵；文字形態印 `NOT-EVALUABLE（no-evaluable-window）`、不印 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_1_E_1]"
```
```gherkin
# AT-322-1-E-2
# 對應 AC: AC-322-1（PRD AC-SI-22-1、AC-SI-22-2；R125 (b)）M5 的 NE、兩值分區與標籤改判、窗後回滾的處理
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_1_E_2_ -q -p no:xdist -o addopts=

Feature: M5 的 NE 與分區
Scenario: n 不足為 NE，窗後回滾只入資訊欄，改判不改分子
  Given 三份複本：(a) S-PROBE-A 只留 P1～P4（已關閉窗 4 個）；(b) S-PROBE-A 加 P9（`clean` 的窗，`dec(rollback)` 的 `decided_at` 晚於其 `mea.close.at`）；(c) S-PROBE-A 的 P6 另追加合法的 `mea.amend`（`rolled-back` 到 `recurred`）
  When 對各份執行探針（`--json`）
  Then (a) `success.m5.main` 與 `all` 皆為 `NOT-EVALUABLE`、`reason` 皆為 `sample-below-w-min`（`n` 各為 `4`，小於 `W_MIN`）；(b) `info.late_rollbacks` 為 `1`，`m5.all` 的 `value` 與七分之一相差小於 1e-9、`n` 為 `7`，`m5.main` 的 `value` 為 `0.0`、`n` 為 `6`（P9 計入分母、其窗後回滾不入分子）
  And (c) `m5.all` 與 S-PROBE-A 相同（分子取回滾決定的事實，不隨標籤改判而變），但 M1 對 P6 的 `evaluable` 轉為真、`success.m1.n` 為 `4`、`recurred` 為 `2`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_1_E_2]"
```
```gherkin
# AT-322-1-E-3
# 對應 AC: AC-322-1（PRD AC-SI-22-1、§1.1、§1.3〈M1 判定細則〉(c)；R124 (c)）反證條件：同鍵相鄰可評估窗皆 recurred 才成立
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_1_E_3_ -q -p no:xdist -o addopts=

Feature: 反證條件
Scenario: 只有同一根因鍵下相鄰的兩個可評估窗皆 recurred 才成立
  Given `R3` 依 S-FALS（八個窗 W1～W8；根因鍵 `k/x`、`k/y`、`k/z`，§5.2）；對照複本 (b) 只含 W7（基線事件數不足，不可評估）、(c) 只含 W5（可評估的 `clean`）
  When 對三份執行探針（`--json`）
  Then 第一份 `falsification.falsified` 為 `true`、`falsified_keys` 恰為只含 `k/x` 的清單（W2 的 `pending` 不計入也不打斷；`k/y` 的壞、clean、壞不相鄰；`k/z` 只有 W8 一個可評估窗；W3 與 W4 相鄰但鍵不同、不合併）；rc 為 `0`、探針沒有因反證成立而改變 rc
  And (b) `falsified` 為 null、`missing` 含 `no-evaluable-window`、`falsified_keys` 為空清單；(c) `falsified` 為 `false`（有可評估窗而無相鄰的兩個 `recurred`）、`missing` 不含 `no-evaluable-window`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_1_E_3]"
```
```gherkin
# AT-322-2-1
# 對應 AC: AC-322-2（PRD AC-SI-22-2；R126 (b)(c)）成功指標區與資訊欄分區、M5 兩值並列、指紋由兩個組成值決定、鍵序固定
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_2_1_ -q -p no:xdist -o addopts=

Feature: 探針輸出的分區與指紋
Scenario: 成功指標與資訊欄分區，指紋由 manifest 與 metrics_rev 兩值決定
  Given `R3` 依 S-PROBE-A 備妥；測試自備獨立函式 `fp_ref(parts)`：對 `parts` 的 JSON（鍵序排序、緊湊分隔、非 ASCII 不跳脫）取 `sha256:` 前綴的雜湊
  When 以子行程執行探針的 `--json` 形態與文字形態各一次
  Then JSON 頂層鍵序恰為 `schema_rev`、`fingerprint`、`fingerprint_parts`、`head_sha`、`params`、`success`、`info`、`falsification`、`ne`；`success` 鍵序恰為 `m1`、`m4`、`m5` 且 `m5` 含 `main` 與 `all` 兩值；`fingerprint_parts` 只有 `manifest` 與 `metrics_rev` 兩鍵，`fingerprint` 等於 `fp_ref(fingerprint_parts)`，其 `manifest` 等於 `params.fingerprint` 對 `R3` 回傳的 `manifest`；`head_sha` 等於 `git rev-parse HEAD`
  And 文字形態：標題行 `== 成功指標 ==` 與 `== 資訊欄 ==` 依序各出現一次，前者之下只有 M1、M4、M5 三個標籤（M5 兩值為並列的兩行），M2、M3 與提案數等標籤只在後者之下；末行為 `fingerprint=` 接同一個值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_2_1]"
```
```gherkin
# AT-322-2-E-1
# 對應 AC: AC-322-2（PRD AC-SI-22-2；R126 (c)）指紋敏感度：params、metrics.md、metrics_rev 改變即變；來源表、CRLF 版、CHECK_RULES_REV 不改
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_2_E_1_ -q -p no:xdist -o addopts=

Feature: 判準指紋的敏感度
Scenario: 該變的三種改動使指紋改變，不該變的三種改動不改
  Given `R3` 依 S-PROBE-A 備妥，`F0` 為探針函式級入口 `build_report(R3)` 回傳的 `fingerprint`；六份複本各做一處改動：(a) `params.json` 的 `w_opp` 由 `5` 改為 `6`；(b) `metrics.md` 末尾多一個字元；(c) `params.json` 的 `metrics_rev` 由 `1` 改為 `2`；(d) `research_sources.json` 的內容改動；(e) `metrics.md` 的 LF 全換成 CRLF（內容等價）；(f) 以 `mock.patch.object` 把 `params.CHECK_RULES_REV` 改為另一個整數
  When 對六份各取 `build_report` 的 `fingerprint`；(f) 另取 `params.fingerprint` 回傳的 `check_rules_rev` 部分
  Then (a)(b)(c) 的指紋互不相同且皆不等於 `F0`；(c) 的 `fingerprint_parts.metrics_rev` 為 `2`
  And (d)(e)(f) 的指紋皆等於 `F0`；(f) 中 `params.fingerprint` 自身的 `check_rules_rev` 部分確已改變（證明替身有效、探針指紋刻意不含它）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_2_E_1]"
```
```gherkin
# AT-322-2-E-2
# 對應 AC: AC-322-2（PRD AC-SI-22-2；R126 (a)(f)）不接閘門與零寫入：最壞資料仍 rc 0；工作流程、git hooks、settings 不含探針字面
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_322_2_E_2_ -q -p no:xdist -o addopts=

Feature: 探針不接任何閘門
Scenario: 反證成立與全 NE 兩種情形 rc 皆為 0，且探針沒有被任何閘門引用
  Given 兩份：(a) `R3` 依 S-FALS（反證成立）；(b) P0 基線的 `R3`（無事件帳本）；`snap`、`G0` 為前置快照；本 repo 的 `.github/workflows/` 下各檔、`tools/git-hooks/` 下各檔與 `.claude/settings.json`（唯讀）
  When 以子行程對 (a)(b) 各執行探針 `--json`
  Then 兩者 rc 皆為 `0`（rc 不隨反證結果或 NE 改變）；(a) 的 `falsification.falsified` 為 `true`；兩者的 `snap` 與 `G0` 在執行前後相同（零寫入）
  And 上述本 repo 路徑皆不含字面 `selfimproving_measure`（探針不接任何閘門）；對照：同一掃描函式對含該字面的副本回報命中
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_2_E_2]"
```
```gherkin
# AT-340-6-1
# 對應 AC: AC-340-6（本檔自增；R126 (a)(b)(d)）任意 cwd 子行程執行、兩次輸出逐位元相同、零寫入；窗欄位與 measure 的基線與生效結果逐項相同
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_340_6_1_ -q -p no:xdist -o addopts=

Feature: 探針的確定性與單一窗規則
Scenario: 同一份帳本在別的 cwd 重跑得同一份輸出，窗欄位與 measure 的結果相同
  Given `R3` 依 S-BASE 與 S-ADOPT 備妥並已呼叫 `M(R3, measure)`（窗為 `closed`、`clean`）；`X` 為另一個空的 tmp 目錄（非 git repo）；`E0`、`G0`、`H0` 為事件帳本位元組、`git status --porcelain` 輸出、家目錄內容的前置快照
  When 以 `cwd` 為 `X` 的子行程執行探針 `--repo <R3> --json` 兩次；另以 `MJ(R3, measure)` 取 `windows`
  Then 兩次 stdout 位元組逐位元相同、rc 皆為 `0`、stderr 為空、stdout 為 UTF-8 且不含 CR；`E0`、`G0`、`H0` 與 `snap(R3)`、`X` 的內容皆不變（零寫入）
  And `per_prop` 該列的 `evaluable` 為 `true`、`result` 為 `clean`、`events` 為 `2`、`opp_n` 為 `5`，逐項等於 `measure` 的 `windows` 與事件帳本內 `mea.report`（baseline）所記；`success.m1` 的 `n` 為 `1`、`value` 為 `0.0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_6_1]"
```
```gherkin
# AT-340-6-E-1
# 對應 AC: AC-340-6（本檔自增；R126 (d)(e)、NFR-P3-1）純度：原始碼無 subprocess、網路、模型客戶端、寫入原語；import 只經 ro 模組；不讀 AUTOSDD 與金鑰環境變數
# 測試類型: Unit
# 自動化工具: pytest（純函式；AST 掃描）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_340_6_E_1_ -q -p no:xdist -o addopts=

Feature: 探針純度的靜態判準
Scenario: 真原始碼合格，八種注入各被判出對應的問題
  Given 判準函式 `probe_purity_problems(src)`（測試自有，§5.6）與探針原始碼 `S0`；八份副本各注入一處：(i) import `subprocess`；(ii) import `socket`；(iii) import `urllib.request`；(iv) import `anthropic`；(v) 以寫入模式呼叫 `open`；(vi) 呼叫 `write_text`；(vii) 讀取名稱以 `AUTOSDD_` 起頭的環境變數；(viii) 相對 import 一個 `rw` 或 `exec` 類的套件模組
  When 對 `S0` 與八份副本各呼叫 `probe_purity_problems`
  Then `S0` 回空清單；(i)～(viii) 各恰回一筆問題，依序為 `P-SUBPROCESS`、`P-NET`、`P-NET`、`P-MODEL`、`P-WRITE`、`P-WRITE`、`P-ENV`、`P-NON-RO-IMPORT`
  And `S0` 的全部 import 目標皆為標準庫或 R126 (d) 列的十個 `ro` 模組；`S0` 不含名稱含 `KEY`、`TOKEN`、`SECRET` 的環境變數讀取
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_6_E_1]"
```
```gherkin
# AT-340-6-E-2
# 對應 AC: AC-340-6（本檔自增；R126 (d)、ADR-SI-05）DEF 解析差分：合成邊界列與真缺陷帳本家族，（ID, 結案類）與 check_defect_log_crossref 逐筆相同
# 測試類型: Integration
# 自動化工具: pytest + 真缺陷帳本（唯讀）+ tmp 目錄
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_340_6_E_2_ -q -p no:xdist -o addopts=

Feature: DEF 解析的單一來源
Scenario: 兩批輸入，兩個解析器對同一批列給同一組（ID, 結案類）
  Given 合成缺陷帳本主檔 `Gd`（§5.2 的 DEF-EDGE：表頭欄位換序、`fixed@` 起頭、`closed-by-decision`、`open`、`wontfix`、狀態欄為空、ID 欄含空白、無效列）；另一批為本 repo 的真缺陷帳本主檔（唯讀）
  When 對兩批各以 `defs.load_ledger_status` 取映射，並以 `mock.patch.object` 把 `check_defect_log_crossref` 的 `_DEFECT_LOG` 指向同一批後呼叫其 `_load_ledger_status`
  Then 兩批的兩個映射的鍵集合相等、每個 ID 的結案類相同（含 null）；合成批的結果與 §5.2 DEF-EDGE 表逐列相同
  And 探針經 `defs.load_rows` 取得的列的（ID, 結案類）對映射逐筆一致；對真帳本批只斷言兩邊一致、不斷言任何固定筆數；測試沒有寫入真帳本
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_6_E_2]"
```
```gherkin
# AT-340-6-E-3
# 對應 AC: AC-340-6（本檔自增；R126 (a)、NFR-P3-11）用法與載體缺席：rc 3 的成因與點名；無事件帳本時 M1、M4、M5 為 NE 而 rc 0
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 子行程（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_measure_probe.py -k AT_340_6_E_3_ -q -p no:xdist -o addopts=

Feature: 探針的用法與載體缺席
Scenario: 五種無法執行的成因 rc 為 3；載體缺席不是錯誤
  Given 五個呼叫：(a) 未知旗標 `--force`；(b) `--repo` 指向一個檔案；(c) `--repo` 指向不存在的路徑；(d) `R3` 的 `params.json` 缺 `w_n`；(e) `params.json` 的 `w_opp` 為字串；另有 P0 基線 `R3`（無事件帳本、無任何 promoted PROP）
  When 以子行程執行探針（(d)(e) 帶 `--repo <R3>`），再對 P0 基線執行 `--json` 與文字形態
  Then (a)～(e) rc 皆為 `3`、stdout 為空、stderr 至少一行，(d)(e) 的 stderr 分別點名 `w_n` 與 `w_opp`（不以預設值頂替）
  And P0 基線 rc 為 `0`；`success.m1`、`success.m4`、`success.m5.main`、`success.m5.all` 的 `status` 皆為 `NOT-EVALUABLE`、`reason` 皆為 `carrier-not-established`，`ne` 清單含這些欄位；文字形態印 `NOT-EVALUABLE（carrier-not-established）`、不印 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_6_E_3]"
```

**D. 退役、抖動、容量與 `capacity` 動詞（CR）**

```gherkin
# AT-325-1-1
# 對應 AC: AC-325-1（PRD AC-SI-25-1；R127 (a)(b)(c)）retire 提案的本文兩欄合形態、目標為已採納工件：受理、digest 綁定兩值、事件無新鍵；add 提案的兩欄同樣受理
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_325_1_1_ -q -p no:xdist -o addopts=

Feature: 退役提案的兩個欄位
Scenario: 本文兩欄合形態且目標在役即受理，digest 綁定兩值
  Given `R3` 內一個 open 運轉與一個以 `promoted(R3, target=T1)` 取得的 PROP `A0`（`T1` 在役）；`try_prop` 的退役配方：`action` 為 `retire`、`target` 為 `T1`、`sources` 為 `s1`，`retire_when` 為字面 `該段連續兩個運轉無人引用`、`reopen_symptom` 為字面 `同一條提示再度被研究者重寫`（經 `body_md` 寫入本文欄位表）
  When 呼叫 `try_prop` 得 `P`；另取三份複本各只改一處再呼叫：(a) `retire_when` 改為另一句；(b) `reopen_symptom` 改為另一句；(c) 對照：`action` 改為 `add`、`target` 改為 `T2`（兩欄沿用）
  Then `P` 的 rc 為 `0`、`prop` 事件的 `action` 為 `retire`、PROP 態為 `proposed`；`P`、(a)、(b) 的 `digest` 互不相同；(c) 的 rc 為 `0`，且 `P` 的事件鍵集合等於 (c) 的事件鍵集合（事件沒有新鍵）
  And `MJ(R3, check)` 的 `events.structure` 與 `events.mea` 皆為 `PASS`；各複本事件帳本只多一筆 `prop` 事件
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_325_1_1]"
```
```gherkin
# AT-325-1-E-1
# 對應 AC: AC-325-1（PRD AC-SI-25-1；R127 (a)(b)(c)）缺欄、空值、含日期或輪號、revise 缺欄、舊旗標、retire 目標未採納（含最近晉升者為 retire 或 delete、回滾後回到在役、退役後再 add）：碼與 rc、零殘留
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_325_1_E_1_ -q -p no:xdist -o addopts=

Feature: 退役欄位與目標的拒收
Scenario: 九類 rc 1 與一種 rc 3，目標在役的判定隨後續採納移動，移除成因後同一呼叫受理
  Given `R3` 內一個 open 運轉、一個以 `promoted(R3, target=T1)` 取得的 PROP `A0`（`T1` 在役）與一個態為 `returned` 的 PROP `Z`（供 `try_revise`），`E0` 與 `snap(R3)` 為前置快照；退役配方同上，每次只破壞一處；另自前置快照 `snap(R3)` 備妥四份獨立複本 `Rj`、`Rk`、`Rl`、`Rm`（複本不含 (i) 建出的 PROP）
  When 依序呼叫 `try_prop`：(a) 本文缺 `retire_when` 鍵；(b) `action` 為 `add` 而本文缺 `reopen_symptom` 鍵；(c) `retire_when` 為空字串；(d) `reopen_symptom` 含 `2026-10-24`；(e) `retire_when` 含 `R214`；(f) `target` 為在役之外的 `T2`；(g) 以 `try_revise` 修訂 `Z` 而新本文缺 `reopen_symptom` 鍵；(h) 呼叫行多帶舊旗標 `--retire-when`；(i) 恢復合規；再於各複本先以 `promoted` 手寫 `T1` 的後續採納 `B`，然後以退役配方呼叫 `try_prop`：(j) `Rj` 的 `B` 為 `action=retire`；(k) `Rk` 同 (j) 且另手寫 `B` 的 `dec`（rollback）與 `app.rollback`；(l) `Rl` 同 (j) 且其後再手寫一個 `action=add` 的 `promoted`；(m) `Rm` 的 `B` 為 `action=delete`
  Then (a)(b)(c)(g) rc 為 `1`、碼 `RETIRE-FIELD-MISSING`；(d)(e) rc 為 `1`、碼 `RETIRE-FIELD-FORM`；(f)(j)(m) rc 為 `1`、碼 `RETIRE-TARGET-NOT-ADOPTED`；(h) rc 為 `3`、stderr 以 `selfimproving:` 起頭；(i)(k)(l) rc 為 `0`（(k) 回滾使 `T1` 回到在役、(l) 最近晉升者為 add）
  And (a)～(g)(j)(m) 輸出末尾有 `obs-draft:` 與草稿列（`draft_ok`）；(a)～(h) 每次呼叫之後 `snap(R3)` 與 `E0` 皆與呼叫之前相同，(j)(m) 之後各該複本的 `snap` 與事件帳本亦與呼叫之前相同（零殘留）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_325_1_E_1]"
```
```gherkin
# AT-325-1-E-2
# 對應 AC: AC-325-1（PRD AC-SI-25-1；R127 (a)(b)）形態負控：輪號、日期、待排程、換行各 RETIRE-FIELD-FORM；空值不雙報（回空清單，由 RETIRE-FIELD-MISSING 判）；PR123、ROW-MUTATED 不誤殺
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_325_1_E_2_ -q -p no:xdist -o addopts=

Feature: 退役欄位的形態判準
Scenario: 六個違規向量各被判出，六個對照向量（含空值）不被判
  Given 向量 N1～N6：N1 含 `R123`；N2 含 `improving_117`；N3 含 `2026-10-24`；N4 含 `待排程`；N5 中間有換行；N6 句首為 `R7`；對照 C1 含 `PR123`、C2 含 `ROW-MUTATED`、C3 含 `CR2`、C4 為前後有空白的合規一句、C5 為空字串、C6 只有空白
  When 對每個向量呼叫 `retire.form_problems`
  Then N1～N6 各回恰一筆碼 `RETIRE-FIELD-FORM`，detail 點名的成因依序為輪號、輪號、日期、待排程、換行、輪號
  And C1～C6 皆回空清單（C4 的前後空白不構成成因；C5、C6 為空值，由 `RETIRE-FIELD-MISSING` 判而不雙報）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_325_1_E_2]"
```
```gherkin
# AT-325-2-1
# 對應 AC: AC-325-2（PRD AC-SI-25-2；R127 (e)(f)）退役走同一人工閘：proposed 態、經 decide 與 P2 動詞推進；R 類卡面有 set_maturity 提示、其他類無
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git + 合成逐字稿（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_325_2_1_ -q -p no:xdist -o addopts=

Feature: 退役與新增走同一道人工閘
Scenario: D 類退役推到 promoted，R 類退役的卡面多一行提示
  Given `R3` 內 open 運轉；兩個已採納工件各有一個 promoted PROP（`T1` 與規則檔 `AISDLC_SDD/<VNEW>/governance/rules/R-9.2.yaml`，後者 `maturity` 為 `proposed`，以 `promoted` 手寫）；`Pd`（`cls` 為 `D`、`action` 為 `retire`、`target` 為 `T1`）與 `Pr`（`cls` 為 `R`、`action` 為 `retire`、`target` 為該規則檔）皆以 `drive_to(R3, proposed, …)` 取得，本文兩欄由 `body_md` 預設寫入
  When 對 `Pd` 依序呼叫 `card --issue`、`decide_say` 受理 `核准`、`heldout-freeze`、`sandbox`、`verify`、`decide_say` 受理 `晉升`、`promote`，每步之後取 `fold` 態；對 `Pr` 呼叫 `card --issue`
  Then `Pd` 每步之後的 `fold` 態依序為 `proposed`（`card --issue`）、`approved`（核准）、`approved`（`heldout-freeze`）、`sandboxed`（`sandbox`）、`verified`（`verify`）、`verified`（晉升的 `dec`）、`promoted`（`promote`），每步只用 P2 既有動詞；兩者 `prop` 事件的 `route` 皆為 `loop`、`action` 皆為 `retire`
  And `Pr` 的卡面在分界線之後有一行 `SDD 規則退役須經 set_maturity(reviewed_by=<人>)；本迴圈不呼叫 SDD 碼`，核心區不含該行；`Pd` 的卡面沒有該行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_325_2_1]"
```
```gherkin
# AT-325-2-E-1
# 對應 AC: AC-325-2（PRD AC-SI-25-2；R127 (e)(f)、NFR-P3-12）只提議不套用：capacity、measure、scan 不建立 PROP 或 DEC、不改工作樹；套件無 set_maturity 呼叫與 SDD 碼 import
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_325_2_E_1_ -q -p no:xdist -o addopts=

Feature: 系統只提議、不自動退役
Scenario: 容量逼近上限也不產生任何提案或決定
  Given `R3` 依 S-CAP 備妥（記憶索引逼近上限），並依 S-ADOPT 備有一個 promoted PROP；`E0`、`G0` 為事件帳本位元組與 `git status --porcelain` 的前置快照
  When 依序呼叫 `capacity`、`scan`、`M(R3, measure)`、`status`
  Then 事件帳本相對 `E0` 只多出 `mea.*` 事件，沒有 `prop`、`dec`、`app.*` 或 `attr*`；`git status --porcelain` 相對 `G0` 只多事件帳本一個路徑
  And 對 `tools/lib/selfimproving/*.py` 與 `tools/selfimproving.py` 的 AST 掃描：沒有對名為 `set_maturity` 的呼叫、沒有 import `rule_loader` 或 `fsm_runtime`；同一掃描函式對注入這類呼叫的副本回報問題（對照）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_325_2_E_1]"
```
```gherkin
# AT-326-1-1
# 對應 AC: AC-326-1（PRD AC-SI-26-1；R128 (a)(b)(c)）第二個循環放行：A1 R1 A2 R2 之後的新 add 受理；門檻隨 churn_max 移動
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_326_1_1_ -q -p no:xdist -o addopts=

Feature: 抖動防護的放行
Scenario: 兩個完整循環之後的新增在 churn_max 為 2 時受理
  Given `R3` 依 S-CHURN 取得 `A1`、`R1`、`A2`、`R2`（皆 promoted、同 `target` 為 `T1`、`sources` 的根因鍵皆含 `k/c`；`churn_max` 為 `2`），並備有 capability-delta 證據列 `n1`（於 `R2` 晉升之後立案、證據座標與該群既有座標不相交）
  When 呼叫 `try_prop`（`action` 為 `add`、`target` 為 `T1`、`sources` 含 `n1` 與鍵為 `k/c` 的舊列 `c1`）；另取一份複本以 `set_params` 把 `churn_max` 改為 `1` 後同一呼叫
  Then 首次 rc 為 `0`、`prop` 事件的 `action` 為 `add`、PROP 態為 `proposed`（循環數 1 加 1 等於 2，不大於 2）
  And 複本 rc 為 `1`、碼含 `CHURN-EXCEEDED`（2 大於 1）且零殘留；兩者都不含 `CAPABILITY-DELTA-MISSING`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_326_1_1]"
```
```gherkin
# AT-326-1-E-1
# 對應 AC: AC-326-1（PRD AC-SI-26-1；R128 (a)～(e)）超過 churn_max 拒收：A1 R1 A2 R2 A3 R3 之後的新 add 得 CHURN-EXCEEDED 與草稿列；churn_max 為 3 放行；不同 target 或根因鍵不計；與 CAPABILITY-DELTA-MISSING 同時命中時兩碼並列
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_326_1_E_1_ -q -p no:xdist -o addopts=

Feature: 抖動防護的拒收與不計入
Scenario: 三個循環之後被擋；參數、target、根因鍵三種改變放行；缺證據時兩碼並列
  Given `R3` 依 S-CHURN 取得 `A1`、`R1`、`A2`、`R2`、`A3`、`R3p`（群同上、`churn_max` 為 `2`，循環數為 `2`）與 capability-delta 證據列 `n1`；`E0`、`snap(R3)` 為前置快照；以下每個呼叫都取各自獨立的複本
  When 呼叫 `try_prop`（`action` 為 `add`、`target` 為 `T1`、`sources` 含 `n1` 與 `c1`），再各只改一處：(a) `set_params` 把 `churn_max` 改為 `3`；(b) `target` 改為另一個檔 `T2`；(c) `sources` 的根因鍵改為與群不相交的 `k/other`；(d) `sources` 只含舊證據列、不含 `n1`
  Then 首次呼叫 rc 為 `1`、碼含 `CHURN-EXCEEDED`、輸出末尾有 `obs-draft:` 與草稿列（`draft_ok`）、`snap(R3)` 與 `E0` 不變；(a)(b)(c) 皆 rc 為 `0`
  And (d) rc 為 `1`、碼同時含 `CHURN-EXCEEDED` 與 `CAPABILITY-DELTA-MISSING`（兩碼並列收集、不互相取代）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_326_1_E_1]"
```
```gherkin
# AT-326-2-1
# 對應 AC: AC-326-2（PRD AC-SI-26-2；R128 (d)）capability-delta 放行：退役後新立且座標與既有證據不相交的來源
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_326_2_1_ -q -p no:xdist -o addopts=

Feature: 再提已退役工件的新證據
Scenario: 新證據的 OBS 列與同日 DEF 列各使再提放行，舊列單獨使其被擋
  Given `R3` 依 S-CHURN 取得 `A1`、`R1`（`R1` 於 `TR` 晉升；`churn_max` 為 `2`）與三列：`c1`（舊列，鍵 `k/c`）、`n1`（OBS，立案於 `TR` 之後、座標與 `A1`、`R1` 的 sources 座標集合不相交）、`n2`（DEF，發現日期與 `TR` 同日、座標不相交）
  When 對各自獨立的複本以 `sources` 為 (a) `c1` 加 `n1`、(b) `c1` 加 `n2`、(c) 只有 `c1` 呼叫 `try_prop`（`action` 為 `add`、`target` 為 `T1`）
  Then (a)(b) rc 為 `0`、`prop` 事件的 `sources` 含所給列（DEF 列以日末 instant 比較而晚於 `TR`，同日者算新證據）
  And (c) rc 為 `1`、碼 `CAPABILITY-DELTA-MISSING`、輸出末尾有 `obs-draft:`、零殘留
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_326_2_1]"
```
```gherkin
# AT-326-2-E-1
# 對應 AC: AC-326-2（PRD AC-SI-26-2；R116 (c)、R128 (d)）缺 capability-delta：來源全為舊證據、座標相交、退役前立案、同日 DEF 邊界
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_326_2_E_1_ -q -p no:xdist -o addopts=

Feature: capability-delta 的邊界
Scenario: 四種來源組合缺證據，同日 DEF 放行且邊界隨晉升時刻移動
  Given `R3` 依 S-CHURN 取得 `A1`、`R1`（`R1` 於 `TR` 晉升）與列：`c1`（舊證據，鍵 `k/c`）、`o1`（OBS，立案於 `TR` 之後但座標與群既有座標相交）、`o2`（OBS，立案早於 `TR`、座標新）、`d0`（DEF，發現日期為 `TR` 的前一日、座標新）、`d1`（DEF，發現日期與 `TR` 同日、座標新）
  When 對各自獨立的複本以 `sources` 為：(a) `c1`；(b) `c1` 加 `o1`；(c) `c1` 加 `o2`；(d) `c1` 加 `d0`；(e) `c1` 加 `d1` 呼叫 `try_prop`（`action` 為 `add`、`target` 為 `T1`）
  Then (a)～(d) rc 為 `1`、碼 `CAPABILITY-DELTA-MISSING`、輸出末尾有 `obs-draft:`、零殘留；(e) rc 為 `0`（同日 DEF 的日末 instant 晚於 `TR`）
  And 把 `R1` 的 `app.promote` 的 `t` 改為 `d1` 發現日期次日零時（重建複本）後，(e) 改為 rc `1`、碼 `CAPABILITY-DELTA-MISSING`（邊界隨晉升時刻移動）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_326_2_E_1]"
```
```gherkin
# AT-327-1-1
# 對應 AC: AC-327-1（PRD AC-SI-27-1；R129 (b)(d)(e)(g)）記憶索引逼近上限：行數軸與位元組軸、候選自尾逐字、單卡、events_detected e、草稿列過 check
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_327_1_1_ -q -p no:xdist -o addopts=

Feature: 記憶索引的容量事件與歸檔候選
Scenario: 兩軸各自觸發，候選自檔尾逐字取到剛好低於門檻，未逼近者無事件
  Given `cap_index` 組出三份索引檔：(a) 17 個條目（共 19 行），`memory_index_max_lines` 為 `20`；(b) 18 個條目（共 928 位元組），`memory_index_max_bytes` 為 `1000`；(c) 對照：15 個條目（共 17 行），`memory_index_max_lines` 為 `20`；`cap_frac` 為 `0.9`、每個條目行為 50 位元組加 LF、表頭 2 行共 10 位元組
  When 對三份各呼叫 `MJ(R3, capacity, --memory-index, <檔>)`
  Then (a) 的 `memory_index.over_cap` 為 true、`used` 為 `19`、`limit` 為 `20`；`retire_candidates` 為單張卡，內容為第 15、16、17 個條目行（依原序、位元組與檔內逐字相同）、`first_line` 為 `17`、`last_line` 為 `19`；(b) 的候選為第 17、18 個條目行、`first_line` 為 `19`、`last_line` 為 `20`
  And (a)(b) 的 `events_detected` 各含一筆 `trigger` 為 `e`、`subject` 為 `memory_index` 的元素；`obs_drafts` 各一列（`process`、`P3`、`open`，`draft_ok`）；(c) 的 `over_cap` 為 false、`retire_candidates`、`events_detected`、`obs_drafts` 皆為空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_327_1_1]"
```
```gherkin
# AT-327-1-2
# 對應 AC: AC-327-1（PRD AC-SI-27-1、§9.7 #23；R129 (c)(e)）KB 與偏好只印容量報告與草稿列、不產候選；常數 10 與 1000 對映引擎原始碼
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 唯讀引擎原始碼
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_327_1_2_ -q -p no:xdist -o addopts=

Feature: KB 與偏好的容量報告
Scenario: 觸發時只報告不提議；上限常數與引擎一致
  Given `R3`；`kb.json`（鍵 `kb_cache_eviction_count` 為整數 `1`）與 `prefs.json`（頂層物件含 9 個鍵）；對照 `kb0.json`（該鍵為 `0`）與 `prefs8.json`（8 個鍵）
  When 呼叫 `MJ(R3, capacity, --kb-metrics, kb.json, --prefs, prefs.json)` 與用對照檔的同一呼叫；另以 AST 讀 `AutoClaude/autoclaude/utils/knowledge_base.py` 的 `_MAX_ENTRIES` 與 `AutoClaude/autoclaude/plugins/preference_memory_plugin.py` 的 `_MAX_KEYS`
  Then 第一個輸出：`kb` 與 `prefs` 的 `over_cap` 皆為 true（偏好 9 除以 10 恰等於 `cap_frac`）、`retire_candidates` 為空清單、`obs_drafts` 兩列（皆 `process`、`P4`、`open`，各自 `draft_ok`）、`events_detected` 兩筆（`subject` 為 `kb` 與 `prefs`）
  And 對照輸出兩軸 `over_cap` 皆為 false、沒有草稿列；`capacity.KB_MAX_ENTRIES` 等於 `_MAX_ENTRIES`、`capacity.PREFS_MAX_KEYS` 等於 `_MAX_KEYS`（引擎端改值而此處未改即轉紅）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_327_1_2]"
```
```gherkin
# AT-327-1-E-1
# 對應 AC: AC-327-1（PRD AC-SI-27-1；R129 (a)(b)(h)、NFR-P3-11）門檻邊界與量不到：恰等於 cap_frac 觸發、少一單位不觸發；缺輸入與不可解析為 NE 而非零、非 rc 3；唯讀零寫入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_327_1_E_1_ -q -p no:xdist -o addopts=

Feature: 容量的邊界與量不到
Scenario: 邊界值各側的結果，與各種量不到的 NE 理由
  Given `memory_index_max_lines` 為 `20`、`memory_index_max_bytes` 為 `1000`、`cap_frac` 為 `0.9`；`cap_index` 組出 L18（共 18 行）、L17（共 17 行）、B900（位元組恰 900、行數遠低於門檻）、B899；另備 `kb_bad.json`（不是合法 JSON）與 `prefs_list.json`（頂層為陣列）
  When 依序呼叫 `MJ(R3, capacity, --memory-index, <檔>)`：L18、L17、B900、B899；不存在的檔；再呼叫 `--kb-metrics kb_bad.json`、`--prefs prefs_list.json`；最後不帶任何旗標且預設路徑無檔
  Then L18 與 B900 的 `over_cap` 為 true（恰等於 `cap_frac` 即觸發）、L17 與 B899 為 false；不存在的檔使 `memory_index` 為 NE、理由 `memory-index-missing`；`kb` 理由 `kb-metrics-unparseable`、`prefs` 理由 `prefs-unparseable`；不帶旗標時 `kb` 與 `prefs` 的理由為 `kb-not-supplied` 與 `prefs-not-supplied`
  And 以上每次 rc 皆為 `0`（NE 不是 rc 3、也不是 0 筆通過）；NE 的軸沒有 `obs_drafts` 與 `events_detected`；`snap(R3)`、事件帳本與家目錄位元組在全部呼叫前後相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_327_1_E_1]"
```
```gherkin
# AT-327-1-E-2
# 對應 AC: AC-327-1（PRD AC-SI-27-1；R129 (d)）分卡與逐字：需移除的條目數超過卡上限時切卡、逐字含行尾空白與 CRLF、原序、max_archive 參數隨動
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_327_1_E_2_ -q -p no:xdist -o addopts=

Feature: 歸檔候選的分卡與逐字
Scenario: 八條候選依卡上限切卡，位元組與原行逐字相同
  Given 索引位元組串 `Bx`：2 行表頭與 130 個條目行（共 132 行），第 126 至 130 個條目行行尾各有兩個空白；同內容的 CRLF 版 `Bc`；`memory_index_max_lines` 為 `140`、`cap_frac` 為 `0.9`、`max_archive_entries_per_card` 為 `3`
  When 對 `Bx` 與 `Bc` 各呼叫函式級入口 `capacity.evaluate`（§5.6）；再把 `max_archive_entries_per_card` 改為 `4` 後對 `Bx` 呼叫
  Then 候選共 8 條（行 125 至 132）：分 3 張卡，各 3、3、2 條、依原序，`first_line` 與 `last_line` 依序為 `125`／`127`、`128`／`130`、`131`／`132`；每張卡的文字位元組等於其所含原行位元組的串接（`Bx` 含行尾空白與 LF、`Bc` 含 CRLF）
  And 卡上限為 `4` 時分 2 張卡，各 4 條（行 125 至 128 與 129 至 132）；沒有任何一條候選的位元組與原行不同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_327_1_E_2]"
```
```gherkin
# AT-327-2-1
# 對應 AC: AC-327-2（PRD AC-SI-27-2；R129 (f)）截斷風險：行數軸與位元組軸（含攔腰截斷的條目）、草稿列 bug P2 以截斷風險起頭
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_327_2_1_ -q -p no:xdist -o addopts=

Feature: 載入面的截斷風險
Scenario: 排在上限之後的條目被當成缺陷入帳
  Given 兩份索引：(a) `memory_index_max_lines` 為 `20`、25 個條目（共 27 行）；(b) `memory_index_max_bytes` 為 `500`、12 個條目（共 622 位元組；每個條目行連 LF 為 51 位元組、表頭 10 位元組）
  When 對各份呼叫 `MJ(R3, capacity, --memory-index, <檔>)`，並取文字形態
  Then (a) 的 `truncation_risk` 條目數為 `7`、首個行號為 `21`；(b) 條目數為 `3`、首個行號為 `12`（第 10 個條目的結束偏移 520 大於 500，被攔腰截斷者亦計）
  And 兩者各多一列草稿列：類別 `bug`、嚴重度 `P2`、狀態 `open`、症狀以 `截斷風險：` 起頭且 `draft_ok`；文字形態含 `truncation_risk` 一行
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_327_2_1]"
```
```gherkin
# AT-327-2-E-1
# 對應 AC: AC-327-2（PRD AC-SI-27-2；R129 (f)）無風險：恰等於上限、大於上限但其後只有非條目行
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_327_2_E_1_ -q -p no:xdist -o addopts=

Feature: 截斷風險的無風險情形
Scenario: 四種無風險的索引與一個對照
  Given 五個索引位元組串：(a) 共 20 行、`memory_index_max_lines` 為 `20`；(b) 位元組恰 500、最後一個條目行的結束偏移（含 LF）恰 500、`memory_index_max_bytes` 為 `500`；(c) 共 22 行、`memory_index_max_lines` 為 `20`，第 21 行為空白行、第 22 行為不以 `- ` 起頭的註解行；(d) 同 (c) 但第 21 行為縮排的子項（行首有空白）；(e) 對照：同 (c) 但第 21 行為行首無縮排的條目行
  When 對各個呼叫函式級入口 `capacity.truncation_risk`（§5.6）
  Then (a)～(d) 的結果皆為 null（無風險、不產生草稿列）
  And (e) 的結果為條目數 `1`、首個行號 `21`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_327_2_E_1]"
```
```gherkin
# AT-340-3-1
# 對應 AC: AC-340-3（本檔自增；R129 (a)(g)、NFR-P3-12）capacity 的旗標、輸出鍵序與文字形態、唯讀零寫入、無人值守不受限
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_340_3_1_ -q -p no:xdist -o addopts=

Feature: capacity 的輸出契約
Scenario: 旗標與輸出形態，不寫任何檔，無人值守照常執行
  Given `R3` 依 S-CAP：`memory_index_max_lines` 為 `20`、預設路徑（`CLAUDE_CONFIG_DIR` 下 `projects/<slug>/memory/MEMORY.md`）放 17 個條目的索引；`kb.json`（驅逐計數 `0`）與 `prefs.json`（3 個鍵）；`E0`、`G0`、`H0` 為事件帳本位元組、`git status --porcelain` 輸出與家目錄內容的前置快照
  When 呼叫 `MJ(R3, capacity)`、`M(R3, capacity)`、帶三個旗標的 `MJ(R3, capacity, --memory-index, <預設檔>, --kb-metrics, kb.json, --prefs, prefs.json)`；在 `AUTOSDD_UNATTENDED` 為 `1` 時重複第一個呼叫
  Then 三個 `--json` 輸出皆為單一物件，鍵序恰為 `schema_rev`、`cap_frac`、`memory_index`、`kb`、`prefs`、`retire_candidates`、`truncation_risk`、`obs_drafts`、`events_detected`；`schema_rev` 為 `1`；不帶旗標時 `kb` 與 `prefs` 為 NE（`kb-not-supplied`、`prefs-not-supplied`）、帶旗標時為 `read` 且 `over_cap` 為 false
  And 文字形態逐軸一行並以候選卡與 `obs-draft:` 行收尾；四次呼叫 rc 皆為 `0`、無人值守的輸出與第一次逐位元相同；`E0`、`G0`、`H0`、`snap(R3)` 皆不變且沒有建立任何新目錄
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_3_1]"
```
```gherkin
# AT-340-3-E-1
# 對應 AC: AC-340-3（本檔自增；R129 (a)(h)）用法與參數：未知旗標 rc 3、params 鍵無效 rc 3 點名、旗標路徑讀不到為 NE 而非 rc 3
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capacity_retire.py -k AT_340_3_E_1_ -q -p no:xdist -o addopts=

Feature: capacity 的用法與參數
Scenario: 無法執行才是 rc 3，讀不到輸入是 NE
  Given `R3`；`params.json` 的 `cap_frac`、`memory_index_max_lines`、`memory_index_max_bytes`、`max_archive_entries_per_card` 四個鍵各一份缺鍵複本與各一份型別錯誤複本（共 8 份）；一個檔案路徑當 `--repo`；一個目錄當 `--kb-metrics`
  When 呼叫 `capacity`：(a) 未知旗標 `--force`；(b) 8 份複本各一次；(c) `--repo` 為檔案；(d) `--memory-index` 指向不存在的路徑；(e) `--kb-metrics` 指向目錄
  Then (a)(c) rc 為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭；(b) 每份 rc 為 `3` 且 stderr 點名該鍵、不以預設值頂替
  And (d) rc 為 `0`、`memory_index` 為 NE、理由 `memory-index-missing`；(e) rc 為 `0`、`kb` 為 NE、理由 `kb-metrics-unparseable`；各情境之後 `snap(R3)` 不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_3_E_1]"
```

**E. 流程型（SOP）、參數、能力登記、零退化與 AT 錨定（M3、CP）**

```gherkin
# AT-322-3-1
# 對應 AC: AC-322-3（PRD AC-SI-22-3；R133 (e)；流程型 P）SOP 提案者面向四節不含禁出現片段，〈P3 動詞〉含隔離條文
# 測試類型: Unit
# 自動化工具: pytest（純函式；讀 SOP 文字）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_322_3_1_ -q -p no:xdist -o addopts=

Feature: 提案者隔離條文
Scenario: 四節沒有禁出現片段，P3 動詞節有隔離條文
  Given 現行 `docs/05_development/SelfImproving_Operations_SOP.md` 全文 `T`；測試自有的判準函式 `sop_p3_problems(text)`（沿 P2 `sop_p2_problems` 的手法）與 §5.6 的 SOP-P3-FORBID、SOP-P3-REQ
  When 對 `T` 呼叫 `sop_p3_problems`，並取〈擷取者〉〈歸因者〉〈提案者〉〈研究者〉四節的文字與〈P3 動詞〉節
  Then `sop_p3_problems(T)` 回空清單；四節文字不含 SOP-P3-FORBID 的任何片段（逐片段逐節比對）
  And 〈P3 動詞〉節含 SOP-P3-REQ 隔離條文列所要求的字面，且該字面位於程式碼圍欄之外
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_3_1]"
```
```gherkin
# AT-322-3-E-1
# 對應 AC: AC-322-3（PRD AC-SI-22-3；R133 (e)）隔離判準有牙：對 SOP 副本逐項注入禁出現片段與刪除隔離條文，各點名該項
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_322_3_E_1_ -q -p no:xdist -o addopts=

Feature: 隔離判準的牙
Scenario: 每個片段在每一節的注入與條文的刪除各被判出
  Given 現行 SOP 全文 `T` 的副本；SOP-P3-FORBID 的每個片段與四節的每個組合各一份把該片段插入該節的副本；一份刪去隔離條文的副本；一份把隔離條文移入程式碼圍欄的副本
  When 對每份副本呼叫 `sop_p3_problems`
  Then 每份注入副本回恰一筆 `SOP-P3-FORBIDDEN`，detail 點名該節與該片段；刪除副本與移入圍欄副本各回恰一筆 `SOP-P3-REQ-MISSING`，點名隔離條文列
  And 未改動的 `T` 回空清單（對照）；任何一份副本都不使另一節的判定改變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_322_3_E_1]"
```
```gherkin
# AT-340-4-1
# 對應 AC: AC-340-4（本檔自增；R131）params.json 為 32 鍵且兩新鍵值為 200 與 25600、PARAM_SPECS 含之、check 的 params 三項通過
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_4_1_ -q -p no:xdist -o addopts=

Feature: P3 的兩個新參數
Scenario: 真 params.json 與 PARAM_SPECS 一致，合規參數使 check 的三個 params 項為 PASS
  Given 本 repo 的 `docs/06_quality/SelfImproving_Protocol/params.json`（唯讀）與 `params.PARAM_SPECS`；`R3` 的夾具 `params.json`
  When 讀真檔的鍵集合與值；對 `R3` 取 `MJ(R3, check)`
  Then 真檔恰 `32` 鍵、頂層鍵依位元組序遞增、`memory_index_max_lines` 為 `200`、`memory_index_max_bytes` 為 `25600`；`PARAM_SPECS` 含此兩鍵且型別規格皆為 `int1`；真檔的鍵集合等於 `PARAM_SPECS` 的鍵集合
  And `R3` 的 `check` 中 `params.keys`、`params.globs`、`params.coupling` 皆為 `PASS`、`overall` 為 `PASS`；真檔經 `params_file_problems` 無問題
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_4_1]"
```
```gherkin
# AT-340-4-E-1
# 對應 AC: AC-340-4（本檔自增；R131）新鍵缺、型別或範圍不符：check 紅、capacity 與 status 對應軸 rc 3 點名、不以預設值頂替
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_4_E_1_ -q -p no:xdist -o addopts=

Feature: 新參數的驗證
Scenario: 七種無效值各得規定的碼，兩個唯讀動詞拒絕以預設值頂替
  Given `R3` 的八份 `params.json` 複本，每份只改一處：(a) 缺 `memory_index_max_lines`；(b) 缺 `memory_index_max_bytes`；(c) `memory_index_max_lines` 為字串；(d) `memory_index_max_bytes` 為布林；(e) `memory_index_max_lines` 為 `0`；(f) `memory_index_max_bytes` 為負數；(g) `memory_index_max_lines` 為 `1.5`；(h) 對照：兩鍵皆合規；預設路徑記憶索引檔皆在場
  When 對各份取 `MJ(R3, check)`，並對 (a)～(h) 各呼叫 `capacity` 與 `status`
  Then (a)(b) 的 `params.keys` 為 `FAIL`、碼 `PARAM-MISSING`；(c)(d)(g) 碼 `PARAM-TYPE`；(e)(f) 碼 `PARAM-RANGE`；(h) 為 `PASS`
  And `capacity` 與 `status` 對 (a)～(g) 皆 rc 為 `3`、stderr 點名該鍵、不以預設值頂替；(h) 的 `capacity` 與 `status` rc 皆為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_4_E_1]"
```
```gherkin
# AT-340-4-2
# 對應 AC: AC-340-4（本檔自增；R132、NFR-P3-1）能力登記兩態（47 鍵 35／8／2／2；可選 meaplan 存在時 48 鍵 36／8／2／2）、新增的 ro 檔為 ro 與 meawrite 為 rw、閉包全 ro、無 SDD 碼呼叫
# 測試類型: Unit
# 自動化工具: pytest（靜態 AST 掃描加子行程 -X importtime）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_340_4_2_ -q -p no:xdist -o addopts=

Feature: P3 的能力登記
Scenario: 登記表、閉包與載入面
  Given 本檔 `CAPABILITY` 登記表與 `tools/lib/selfimproving/*.py` 的實際檔案集合
  When 取登記表鍵數與各類計數；對 `check`、`status`、`scan`、`export`、`card` 取相對 import 閉包；以子行程 `-X importtime` 分別載入 `status`、`export`、`check`、`card`、`scan`、`capacity` 與探針；對套件與入口做 AST 掃描
  Then 登記表鍵數屬 {`47`, `48`}：`meaplan.py` 不存在時恰 `47` 鍵、四類計數依序為 `35`（ro）、`8`（rw）、`2`（net）、`2`（exec）；存在時恰 `48` 鍵、依序為 `36`、`8`、`2`、`2`；`mea`、`meastat`、`meacheck`、`capacity`、`retire`、`churn`（及存在的 `meaplan`）皆為 `ro`、`meawrite` 為 `rw`；登記鍵集合等於實際檔案集合；`exec` 恰為 `runner` 與 `verify`
  And 五個動詞的閉包皆 ⊆ `ro`；七個載入面行程的載入模組清單皆不含 `meawrite`、`runner`、`verify`；`meawrite` 只在入口 handler 與 `writeverbs.attr_settle` 內延遲 import；套件與入口沒有對 `set_maturity` 的呼叫、沒有 `rule_loader` 與 `fsm_runtime` 的 import
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_4_2]"
```
```gherkin
# AT-340-4-E-2
# 對應 AC: AC-340-4（本檔自增；R132）能力登記判準有牙：對套件 tmp 副本逐項注入違規，各回對應問題
# 測試類型: Unit
# 自動化工具: pytest（純函式；tmp 副本）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_340_4_E_2_ -q -p no:xdist -o addopts=

Feature: 能力登記判準的牙
Scenario: 六種違規各被判出，合規副本不被誤殺
  Given 套件與入口的 tmp 副本 `Q0`（合規，對照），以既有的 `make_pkg` 與 `synth` 建構；六份注入副本：(i) `mea.py` 加相對 import `meawrite`；(ii) `capacity.py` 加 import `subprocess`；(iii) `retire.py` 加對 `set_maturity` 的呼叫；(iv) 新增未登記的檔 `extra.py`；(v) `status.py` 在模組層 import `meawrite`；(vi) `churn.py` 加 import `rule_loader`
  When 對 `Q0` 與六份注入副本各呼叫 `capability_problems`（沿 P2，§5.6）
  Then `Q0` 回空清單；(i) 回 `ro` 檔相對 import `rw` 檔；(ii) 回 `ro` 檔含 `subprocess`；(iii) 回 `set_maturity` 呼叫；(iv) 回檔案未登記；(v) 回 `status` 的閉包含 `meawrite`；(vi) 回 `rule_loader` import
  And 每份注入副本恰回一筆問題，且點名檔名與成因
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_4_E_2]"
```
```gherkin
# AT-340-7-1
# 對應 AC: AC-340-7（本檔自增；R133；流程型 P）SOP〈P3 動詞〉定稿：rc 契約兩列、序列、回滾序列、兩形態、退役配方、讀值紀律、隔離條文、啟動條件字樣已刪
# 測試類型: Unit
# 自動化工具: pytest（純函式；讀 SOP 文字）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_7_1_ -q -p no:xdist -o addopts=

Feature: Operations SOP 的 P3 動詞節
Scenario: 字面齊備、位置與次序正確
  Given 現行 SOP 全文 `T` 與 §5.6 的 SOP-P3-REQ（十列）
  When 切出〈P3 動詞〉節與〈啟動條件〉節；對 `T` 呼叫 `sop_p3_problems`
  Then 〈P3 動詞〉節位於〈P2 動詞〉節之後，且含 SOP-P3-REQ 各列要求的字面：rc 契約表的 `measure`、`capacity` 兩列、`promote` 到 `measure` 的序列、`run-close` 之前跑一次 `measure` 作補記、回滾序列（PowerShell 與 bash 兩種圍欄各一）、退役配方（M 類歸檔與在役工件的 retire 兩路）、讀值紀律三句、提案者隔離條文
  And 〈啟動條件〉節不含 `尚無該動詞`；〈P3 動詞〉節沒有 `待補` 與 `TODO`；`sop_p3_problems(T)` 回空清單
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_7_1]"
```
```gherkin
# AT-340-7-E-1
# 對應 AC: AC-340-7（本檔自增；R133）SOP 判準有牙：逐項刪去必備片段、條文移入圍欄、序列對調、待補復現，各被判不合格
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_7_E_1_ -q -p no:xdist -o addopts=

Feature: SOP 判準的牙
Scenario: 十四份破壞的副本各被判出恰一筆問題
  Given 現行 SOP 全文 `T` 的副本：SOP-P3-REQ 十列各一份刪去該列字面者；另四份：(a) 把回滾序列移入程式碼圍欄；(b) 把 `measure` 與 `promote` 的序列對調；(c) 在〈P3 動詞〉節加入 `待補` 字樣；(d) 在〈啟動條件〉節加回 `尚無該動詞`
  When 對各份呼叫 `sop_p3_problems`
  Then 刪列副本各回恰一筆 `SOP-P3-REQ-MISSING`、點名該列編號；(a) 回 `SOP-P3-REQ-MISSING`（圍欄內的字面不算）；(b) 回 `SOP-P3-ORDER`；(c) 回 `SOP-P3-PLACEHOLDER`；(d) 回 `SOP-P3-STALE-WORDING`
  And 未改動的 `T` 回空清單（對照）；每份副本回傳的問題數皆為一
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_7_E_1]"
```
```gherkin
# AT-340-8-1
# 對應 AC: AC-340-8（本檔自增；R134）零退化：升級夾具重放 P1 與 P2 情境表皆合規；P0、P1、P2 的全部 AT 在測試檔各有對應函式；同步站點的斷言值如 R134
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_8_1_ -q -p no:xdist -o addopts=

Feature: P0 至 P2 的零退化
Scenario: 夾具升級不改變既有情境的結論，既有 AT 與同步站點齊備
  Given 升級後的夾具；P1 情境表（`sc_close`、`sc_seq`、`sc_legal`、`sc_rev`、`sc_susp`）與 P2 的 `sc_p2_legal`；P0、P1、P2 三份 TCS 的 AT 標頭；R134 (a)～(f) 的各同步站點
  When 以夾具重放各情境取 `events.structure` 與 `fold`；以 `parse_at_headers` 與 `collect_nodes` 對三份 TCS 與全部 SI 測試檔收集；以 AST 讀各站點的斷言常數
  Then 各情境的 `events.structure` 為 `PASS`、`fold` 的狀態與問題與預期表逐項相同；三份 TCS 解析出的 AT 數依序為 `42`、`163`、`137`，且每個 AT 的錨定 `-k` 至少收到一個測試函式
  And 各站點的斷言值為新值：`check` 項數 `33`、`CHECK_RULES_REV` 為 `4`、`params` 為 `32` 鍵、動詞數為 `23`、`STATUS_KEYS` 為 `15` 鍵（`console_obs` 的末鍵為 `measure`）、`export` 的 proposals 鍵清單為 `19` 鍵、`same()` 的排除集合含 `capacity`、`CAPABILITY` 為 R132 兩態之一（`47` 鍵 `35`／`8`／`2`／`2`，或 `48` 鍵 `36`／`8`／`2`／`2`）；未實作動詞清單不再含 `capacity`；夾具 `body_md` 的預設欄位表含 `retire_when` 與 `reopen_symptom`、`digest` 核心的兩鍵為其預設值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_8_1]"
```
```gherkin
# AT-340-8-E-1
# 對應 AC: AC-340-8（本檔自增；R134）夾具升級不吞掉違規：明示的錯誤值不被預設值覆蓋，P0 至 P2 的負控事件仍被同一碼擋下
# 測試類型: Unit
# 自動化工具: pytest（純函式；tmp 目錄）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_8_E_1_ -q -p no:xdist -o addopts=

Feature: 夾具預設值不覆蓋明示值
Scenario: 九個明示錯誤的 mea 事件保持錯誤，P2 的負控事件仍被擋
  Given 升級後夾具的 `ev()`；九個明示錯誤的 `mea.*` 事件（每個置換於一份合規帳本中）：`mea.open` 的 `w_opp` 為 `0`；`mea.open` 以 `DROP` 哨兵明示刪除 `promote_seq`；`mea.close` 的 `result` 為表外值；`mea.close` 的 `n_opp` 為負數；`mea.amend` 的 `to` 為表外值；baseline 的 `events` 為負數；check 報告帶 `prop`；`mea.amend` 的 `cause` 為 `0`；`mea.report` 的 `report` 為表外值；另備 P2 事件欄位負控表各列（取自 `tools/tests/test_selfimproving_events_p2.py`）以升級後夾具重建
  When 對九個事件取 `events.mea`，對 P2 負控各列取 `events.structure`
  Then 九個事件的明示值逐位元保留，`events.mea` 依序得 `MEA-TYPE`、`MEA-KEY-MISSING`、`MEA-ENUM`、`MEA-TYPE`、`MEA-ENUM`、`MEA-TYPE`、`MEA-KEY-UNKNOWN`、`MEA-TYPE`、`MEA-ENUM`，沒有一個得 `PASS`
  And P2 負控各列得到與升級前相同的碼（以該測試檔的預期表為準）；未明示的 `mea.*` 欄位被補成合規值（對照），其 `events.mea` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_8_E_1]"
```
```gherkin
# AT-340-9-1
# 對應 AC: AC-340-9（本檔自增；R135）本檔每個 AT 的錨定 -k 以節點 id 子字串比對恰命中一個測試函式
# 測試類型: Integration
# 自動化工具: pytest + 子行程 pytest --collect-only
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_9_1_ -q -p no:xdist -o addopts=

Feature: P3 的 AT 錨定
Scenario: 每個 AT 的錨定 -k 恰收一個測試函式
  Given 本檔全文 `T3`；七個測試檔（五個新檔與既有的 `test_selfimproving_capability.py`、`test_selfimproving_console_obs.py`）；自 `test_selfimproving_p2_meta.py` 匯入的 `parse_at_headers`、`anchor_problems`、`collect_nodes`
  When 對 `T3` 呼叫 `parse_at_headers`；對七個測試檔呼叫 `collect_nodes`（子行程 `--collect-only`、cwd 為 repo 根）；呼叫 `anchor_problems`
  Then `parse_at_headers` 回 `78` 個 AT、AT id 無重複、每個 AT 的判定指令所指測試檔屬上述七個之一；`anchor_problems` 回空清單
  And 每個 AT 的錨定 `-k` 以節點 id 子字串比對恰命中一個測試函式；七個檔中函式名以 `test_AT_3` 起頭的收集節點都屬於本檔的某個 AT（沒有孤兒函式；既有檔內 P2 以前的函式不在此列）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_9_1]"
```
```gherkin
# AT-340-9-E-1
# 對應 AC: AC-340-9（本檔自增；R135）錨定檢查有牙：無結尾底線、值與 AT id 不符、零命中、重複命中、缺 slug、同一函式被兩個 AT 命中，各被判紅
# 測試類型: Integration
# 自動化工具: pytest（純函式；合成標頭與收集結果）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_9_E_1_ -q -p no:xdist -o addopts=

Feature: 錨定檢查的牙
Scenario: 六組合成輸入各被判出，合規組不被誤殺
  Given 合成的 AT 標頭與收集結果六組：(a) `-k` 缺結尾底線；(b) `-k` 去掉結尾底線後與 AT 底線形不符；(c) 對應測試檔收集不到任何節點；(d) 同一 `-k` 命中兩個測試函式；(e) 測試函式名缺 slug（只有 AT 底線形）；(f) 同一個測試函式同時被兩個 AT 的 `-k` 命中；另備一組合規者
  When 對六組與合規組各呼叫 `anchor_problems`
  Then 六組各回至少一筆問題且點名 AT id，成因依序為非錨定（無結尾底線）、不等於 AT 底線形、零命中、命中 2 個、函式名缺 slug、同時被兩個 AT 命中；合規組回空清單
  And 六組的問題字串都不含 AT id 以外的檔案內容；合規組的測試函式名各含 slug
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_9_E_1]"
```

**F. Console 載體三動詞的寫入前判準（CN；D12，承接 DEF-200-568）**

```gherkin
# AT-340-10-1
# 對應 AC: AC-340-10（本檔自增；承接 DEF-200-568；P2 R94～R97、R136）合法稽核檔照常入帳：核准、單字元理由的否決、obs-add、obs-close 各一份，事件與帳本逐項合規、check 仍綠
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_340_10_1_ -q -p no:xdist -o addopts=

Feature: Console 載體合法稽核檔
Scenario: 四份合法稽核檔各自入帳，邊界值也放行
  Given `R3`、測試金鑰（`AUTOSDD_SI_AUDIT_KEY`）與 `HOME`；以 P2 的 `write_audit`、`body_decide`、`body_obs_add`、`body_obs_close` 備四份稽核檔：(a) `decide` 核准（`DEC-STATES` 第 1 列的 PROP、`flags` 為空陣列、無 `reason`）；(b) `decide` 否決（第 2 列的 PROP、`reason` 為單一字元 `a`、`reason_class` 為 `證據不足`）；(c) `obs-add`（`face` 為 `守衛` 並附 `exposure`、`marks_extra` 的 `根因` 值為 `docs/x`、各字串欄不含控制字元）；(d) `obs-close`（取 `R3` 內一個處置為 `open` 的基底列、`disposition` 為 `decided：掌舵者裁決，已修復`）
  When 依序以 `--carrier console --audit-ref <ref>` 形態呼叫 `decide`、`obs-add`、`obs-close`
  Then 四次 rc 皆為 `0`；事件帳本依序新增 `dec`（核准）、`dec`（否決，`reason` 為 `a`）、`obs.add`、`obs.close`；OBS 帳本多一列新列（處置為 `open`、標記含 `carrier=console` 與該 `audit_ref`），被關的基底列只有第 8 欄由 `open` 改為所給終值
  And `MJ(R3, check)` 的 `overall` 為 `PASS`，`events.structure`、`events.dec_console`、`obs.console_audit` 皆為 `PASS`；核准的 `dec` 事件沒有 `reason` 與 `flags` 鍵
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_10_1]"
```
```gherkin
# AT-340-10-E-1
# 對應 AC: AC-340-10（本檔自增；承接 DEF-200-568；R136 (a)）自由文字欄含換行或控制字元：寫入前以既有碼 CTRL-CHAR 拒收，帳本與事件帳本位元組不變
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_340_10_E_1_ -q -p no:xdist -o addopts=

Feature: 控制字元的寫入前拒收
Scenario: 十份變形稽核檔各被拒收且零殘留
  Given `R3`、測試金鑰與 `HOME`；`E0`、`L0`、`H0` 為事件帳本位元組、OBS 帳本位元組與 `HOME` 內容的前置快照；十份稽核檔各只破壞一處：`decide` 否決（`DEC-STATES` 第 2 列）的 `reason` 含 `\n`、`\r`、`\x00`、`\x1f`、`\t` 各一份；`obs-add` 的 `context` 含 `\n`、`symptom` 含 `\r`、`evidence` 含 `\x00` 各一份；`face` 為 `守衛` 而 `exposure` 含 `\n`；`marks_extra` 的 `根因` 值含 `\n`
  When 對每份以 `--carrier console --audit-ref <ref>` 形態呼叫對應動詞，每次之後取 `MJ(R3, check)`
  Then 每次 rc 為 `1`、`codes(out)` 恰為只含 `CTRL-CHAR` 的集合、輸出末尾有 `obs-draft:` 與草稿列（`draft_ok`）；其中 `obs-add` 的 `\r`、`\x00` 兩份是既有行為的回歸對照（修復前後同碼），`decide` 五份與 `obs-add` 的三份 `\n` 為新增拒收
  And 每次之後事件帳本等於 `E0`、OBS 帳本等於 `L0`、`HOME` 除稽核檔外等於 `H0`（零殘留），`check` 的 `overall` 為 `PASS`；各以一般字元取代該控制字元並重簽的獨立複本 rc 為 `0`（對照）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_10_E_1]"
```
```gherkin
# AT-340-10-E-2
# 對應 AC: AC-340-10（本檔自增；承接 DEF-200-568；R136 (b)）decide 的 body 帶該 dkind 不收的鍵：EVENT-KEY-UNKNOWN；flags 元素不合：EVENT-TYPE；皆與 check 對手寫事件同碼
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_340_10_E_2_ -q -p no:xdist -o addopts=

Feature: 不收的鍵的寫入前拒收
Scenario: 八份帶多餘鍵或不合 flags 的 decide 稽核檔被拒收，且與 check 同碼
  Given `R3`、測試金鑰與 `HOME`；`E0`、`H0` 為前置快照；八份 `decide` 稽核檔（PROP 取 `DEC-STATES` 對應列的前提態）各只破壞一處：(a) 核准（第 1 列）帶 `reason`；(b) 核准帶 `flags`（元素 `unverified_ack`）；(c) 否決（第 2 列，附合法 `reason` 與 `reason_class`）帶 `flags`；(d) 退回（第 4 列）帶 `flags`；(e) 轉交（第 7 列）帶 `reason`；(f) 晉升前式（第 5 列）帶 `reason`；(g) 解除（第 10 列）帶 `reason`；(h) 晉升前式（第 5 列，獨立複本）的 `flags` 為元素 `x` 的陣列（不帶 `reason`）
  When 對每份呼叫 `decide <ID> --carrier console --audit-ref <ref>`；另取兩個合規 Console `dec` 事件的複本，各以 `rewrite_event` 加上 `reason` 鍵、把 `flags` 改成元素 `x` 的陣列，取 `MJ(R3, check)`
  Then (a)～(g) rc 為 `1`、`codes(out)` 恰為只含 `EVENT-KEY-UNKNOWN` 的集合；(h) rc 為 `1`、`codes(out)` 恰為只含 `EVENT-TYPE` 的集合；每次輸出末尾有 `obs-draft:`、事件帳本等於 `E0`、`HOME` 除稽核檔外等於 `H0`
  And 兩個手寫複本的 `check` 之 `events.structure` 為 `FAIL`，碼依序為 `EVENT-KEY-UNKNOWN` 與 `EVENT-TYPE`（寫入端與 check 同碼的差分）；對照：核准帶空陣列 `flags` 且無 `reason` 者 rc 為 `0`、之後 `check` 的 `overall` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_10_E_2]"
```
```gherkin
# AT-340-10-E-3
# 對應 AC: AC-340-10（本檔自增；承接 DEF-200-568；R136 (c)）需理由的五種 dkind 帶空 reason：REASON-EMPTY；單字元 reason 放行；缺鍵仍 AUDIT-BODY-INVALID
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_340_10_E_3_ -q -p no:xdist -o addopts=

Feature: 空理由的寫入前拒收
Scenario: 五種需理由的決定帶空 reason 被拒收，缺鍵維持既有碼
  Given `R3`、測試金鑰與 `HOME`；`E0`、`H0` 為前置快照；六份 `decide` 稽核檔（PROP 或 RUN 取 `DEC-STATES` 對應列）：(a) 否決（第 2 列）、(b) 否決晉升（第 3 列）、(c) 退回（第 4 列）、(d) 回滾（第 9 列）、(e) 恢復（第 11 列）的 `reason` 皆為空字串（需理由類者附合法 `reason_class`）；(f) 否決（第 2 列）完全不帶 `reason` 鍵
  When 對每份呼叫 `decide <ID> --carrier console --audit-ref <ref>`，每次之後取 `MJ(R3, check)`；另取 (a) 的獨立複本把 `reason` 改為單一字元 `a` 後重簽再呼叫
  Then (a)～(e) rc 皆為 `1`、`codes(out)` 恰為只含 `REASON-EMPTY` 的集合、輸出末尾有 `obs-draft:`、事件帳本等於 `E0`、`HOME` 除稽核檔外等於 `H0`、`check` 的 `overall` 為 `PASS`
  And (f) rc 為 `1`、`codes(out)` 恰為只含 `AUDIT-BODY-INVALID` 的集合（既有碼不變）；改為單一字元的 (a) rc 為 `0` 且新增的 `dec` 事件 `reason` 為 `a`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_10_E_3]"
```
```gherkin
# AT-340-10-E-4
# 對應 AC: AC-340-10（本檔自增；承接 DEF-200-568；R136 (d)）obs-close 的 disposition 含換行或首詞不在終值枚舉：DISPOSITION-INVALID；其他控制字元維持既有 CTRL-CHAR
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_340_10_E_4_ -q -p no:xdist -o addopts=

Feature: disposition 的寫入前拒收
Scenario: 含換行與首詞不合的 disposition 各被拒收且零殘留，其他控制字元的既有碼不變
  Given `R3`、測試金鑰與 `HOME`；`E0`、`L0`、`H0` 為前置快照；`Ox` 為 OBS 帳本中一個處置為 `open` 的基底列；七份 `obs-close` 稽核檔的 `obs_id` 皆為 `Ox`，`disposition` 依序為：(a) `decided：甲` 接 `\n` 與 `乙`；(b) `decided：甲` 接 `\r\n` 與 `乙`；(c) `decided：甲` 接結尾的 `\n`；(d) `fixed@` 接存在的 commit 前 12 碼、其後接 `\n` 與文字（首詞合法而帶換行）；(e) 首詞為 `bogus`；(f) 恰為 `open`；(g) `decided：甲` 接 `\t` 與 `乙`
  When 對每份以 `--carrier console --audit-ref <ref>` 形態呼叫 `obs-close`，每次之後取 `MJ(R3, check)`
  Then (a)～(f) rc 為 `1`、`codes(out)` 恰為只含 `DISPOSITION-INVALID` 的集合（(b) 含 `\r` 而不另報 `CTRL-CHAR`：`body_guard` 須在組列後自驗之前返回）；(g) rc 為 `1`、`codes(out)` 恰為只含既有碼 `CTRL-CHAR` 的集合（R97 組列後自驗，修復前後不變）；每次輸出末尾有 `obs-draft:` 與草稿列（`draft_ok`）
  And 每次之後事件帳本等於 `E0`、OBS 帳本等於 `L0`、`HOME` 除稽核檔外等於 `H0`，`check` 的 `overall` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_10_E_4]"
```
```gherkin
# AT-340-10-E-5
# 對應 AC: AC-340-10（本檔自增；承接 DEF-200-568；R136 (a)(d)）回歸：被拒的含換行 disposition 與 obs-add 不留痕，OBS 帳本位元組不變、該列仍 open，其後同一列可正常關閉
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_340_10_E_5_ -q -p no:xdist -o addopts=

Feature: 被拒收之後不留痕
Scenario: 壞稽核檔被拒後，帳本位元組不變，同一列之後仍可正常關閉
  Given `R3`、測試金鑰與 `HOME`；`Ox` 為處置為 `open` 的基底列；`L0`、`E0` 為 OBS 帳本與事件帳本的位元組快照；三份稽核檔：`A1`＝`obs-close`（`obs_id` 為 `Ox`、`disposition` 為 `decided：甲` 接 `\n` 與 `乙`）；`A2`＝同 `obs_id` 的合法 `obs-close`（`disposition` 為 `decided：掌舵者裁決，已修復`）；`A3`＝`obs-add`（`symptom` 含 `\n`）
  When 依序呼叫帶 `A1` 的 `obs-close`、帶 `A3` 的 `obs-add`，各取 OBS 帳本位元組與 `MJ(R3, check)`；其後呼叫帶 `A2` 的 `obs-close`
  Then 帶 `A1` 與帶 `A3` 的呼叫 rc 皆為 `1`；OBS 帳本位元組等於 `L0`（`Ox` 的第 8 欄仍恰為 `open`、列數不變、沒有多出的行）、事件帳本等於 `E0`；`A1`、`A3` 的 `audit_ref` 不在任何事件與 OBS 列標記中；`check` 的 `history.row_mutated`、`obs.console_audit` 與 `overall` 皆為 `PASS`
  And 帶 `A2` 的呼叫 rc 為 `0`；OBS 帳本相對 `L0` 只有 `Ox` 的第 8 欄改為所給終值（其餘位元組逐字不變）、事件帳本新增恰一筆 `obs.close`；`check` 的 `overall` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_340_10_E_5]"
```

---

## 3. AT 完整清單

> 依測試類型與測試檔的閱讀索引（權威清單是 §1）；測試函式名樣式 `test_<AT 底線形>_<slug>`（R135）。本節表格第一欄是測試檔、不是 AC ID。

### 3.1 Unit Tests

| 測試檔（tools/tests/） | AT ID |
|------------------------|-------|
| test_selfimproving_capacity_retire.py | AT-325-1-E-2、AT-327-1-E-2、AT-327-2-E-1 |
| test_selfimproving_measure_probe.py | AT-340-6-E-1 |
| test_selfimproving_p3_meta.py | AT-322-3-1、AT-322-3-E-1、AT-340-7-1、AT-340-7-E-1、AT-340-8-E-1 |
| test_selfimproving_capability.py（既有檔，新增函式） | AT-340-4-2、AT-340-4-E-2 |

### 3.2 Integration Tests

| 測試檔（tools/tests/） | AT ID |
|------------------------|-------|
| test_selfimproving_measure.py（21 個） | AT-323-1-1～AT-323-1-7、AT-323-1-E-1～AT-323-1-E-5、AT-323-2-1、AT-323-2-E-1、AT-323-2-E-2、AT-324-1-1、AT-324-1-2、AT-324-1-E-1、AT-324-1-E-2、AT-324-2-1、AT-324-2-E-1 |
| test_selfimproving_measure_verb.py（10 個） | AT-340-1-1、AT-340-1-E-1、AT-340-1-E-2、AT-340-2-1、AT-340-2-2、AT-340-2-E-1、AT-340-2-E-2、AT-340-5-1、AT-340-5-2、AT-340-5-E-1 |
| test_selfimproving_measure_probe.py（11 個） | AT-322-1-1、AT-322-1-2、AT-322-1-E-1～AT-322-1-E-3、AT-322-2-1、AT-322-2-E-1、AT-322-2-E-2、AT-340-6-1、AT-340-6-E-2、AT-340-6-E-3 |
| test_selfimproving_capacity_retire.py（14 個） | AT-325-1-1、AT-325-1-E-1、AT-325-2-1、AT-325-2-E-1、AT-326-1-1、AT-326-1-E-1、AT-326-2-1、AT-326-2-E-1、AT-327-1-1、AT-327-1-2、AT-327-1-E-1、AT-327-2-1、AT-340-3-1、AT-340-3-E-1 |
| test_selfimproving_p3_meta.py（5 個） | AT-340-4-1、AT-340-4-E-1、AT-340-8-1、AT-340-9-1、AT-340-9-E-1 |
| test_selfimproving_console_obs.py（既有檔，新增 6 個函式；D12） | AT-340-10-1、AT-340-10-E-1～AT-340-10-E-5 |

**3.3 Contract Tests 與 3.4 E2E Tests**：（均無：P3 沒有鍵 B 的 AutoClaude 契約測試；出口 (a)～(d) 的真實運轉屬實跑檢核 V22～V26，不入 AT，因為 AT 不碰真帳本與外網。）

## 4. 邊界與錯誤測試規格

邊界與錯誤情境以 `AT-<NNN>-<Y>-E-<n>` 命名並已列入 §1；下表是依場景類型的索引（第一欄為場景類型、不是 AC ID）。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|----------|
| 用法錯誤（rc 3） | AT-340-2-E-1、AT-340-3-E-1、AT-340-6-E-3、AT-325-1-E-1 | 未知旗標、`--by` 含空白、`params.json` 鍵缺或無效、`--repo` 非目錄、舊旗標 `--retire-when`（未知旗標） | 旗標與參數複本 | rc 3、stdout 空、stderr 點名；不以預設值頂替 |
| 狀態類拒收（rc 1） | AT-323-1-E-3、AT-325-1-E-1、AT-326-1-E-1、AT-326-2-E-1 | 錨缺、帳本缺、退役欄位缺或形態不合、退役目標未採納、抖動超限、缺 capability-delta | 手寫帳本與 CLI | rc 1、碼、`obs-draft:`、零殘留 |
| 稽核檔變形（收下再變紅） | AT-340-10-E-1～AT-340-10-E-5 | 自由文字欄含換行或控制字元、`decide` 帶該 dkind 不收的鍵、需理由者的空 `reason`、`obs-close` 的不合法 `disposition`；被拒後帳本位元組不變 | 變形稽核檔（`write_audit`，重簽使一次只有一個缺陷） | rc 1、四碼（既有碼名 `CTRL-CHAR`、`EVENT-KEY-UNKNOWN`、`REASON-EMPTY`、`DISPOSITION-INVALID`）、零殘留、`check` 仍綠；一般字元或單字元的對照放行 |
| 無人值守 | AT-323-2-E-2、AT-340-2-E-1 | `AUTOSDD_UNATTENDED` 設為 `0` 或 `1` | 環境變數 | `UNATTENDED-REFUSED`、零寫入；唯讀動詞不受限（AT-340-3-1） |
| 邊界值（時刻、日精度與機會列） | AT-323-1-E-2、AT-323-1-2、AT-326-2-E-1 | 錨前後、同刻、同日與前一日的 DEF（日末 instant）、缺 offset 取檔頭 tz、目錄名前綴相似、路徑大小寫、無路徑 | S-BOUND、DEF 列 | 逐列歸屬如 §5.2；同日 DEF 算新證據、前一日不算；日末 instant 為窗關閉時點 |
| 邊界值（門檻） | AT-324-1-E-1、AT-326-1-E-1、AT-327-1-E-1、AT-327-2-E-1 | `stop_after_bad` 2／3／4；`churn_max` 2／3；`cap_frac` 恰等於與少一單位；載入上限恰等於 | 參數與索引 | 容量等於即觸發、抖動大於才拒；恰等於載入上限無風險 |
| 載體缺席與量不到 | AT-340-1-E-2、AT-340-5-E-1、AT-322-1-E-1、AT-340-6-E-3、AT-327-1-E-1 | 無事件帳本、錨不可用、缺陷帳本缺、基線不足、容量輸入缺或不可解析 | 檔案不存在或損壞 | NOT-EVALUABLE 與理由碼；不是零、不是綠 |
| 偽造與不合法事件 | AT-323-1-E-4、AT-340-1-E-1、AT-340-8-E-1 | 指向他 PROP 的 amend、非法轉移、十四種欄位表違規、明示錯誤值 | 手寫事件 | 不生效並 `TRANSITION-ILLEGAL`；`events.mea` 恰一碼；夾具不補掉錯誤 |
| 併發與冪等 | AT-340-2-E-2、AT-323-1-1、AT-340-2-1 | 兩執行緒同時 `measure`；重跑 | `evwrite.PAUSE_HOOK` | 不重複事件、`seq` 連續、第二次零事件 |
| 確定性、不接閘門、純度與能力登記 | AT-340-6-1、AT-322-2-E-1、AT-322-2-E-2、AT-340-4-2、AT-340-4-E-2、AT-340-6-E-1、AT-325-2-E-1 | 任意 cwd、位元組直寫、指紋敏感度、工作流程與 hooks 不含探針字面；47（或 48）鍵四類、閉包、載入面、探針純度、無 `set_maturity` 呼叫 | 子行程、靜態掃描與 `-X importtime` | 輸出逐位元相同、零寫入、指紋依 params 與 metrics 改變；純度各項有注入副本自證 |
| 差分（獨立實作） | AT-340-6-E-2、AT-322-2-1、AT-327-1-2 | DEF 解析、指紋重算、引擎常數 | 測試自寫的獨立實作 | 逐筆相同 |
| 行尾與編碼 | AT-327-1-E-2、AT-322-2-E-1、AT-340-6-1 | CRLF 索引逐字、CRLF 的 `metrics.md`、輸出不含 CR | 位元組 | 逐字保留；指紋不變；輸出 LF |
| 刻意不做 | （無 AT） | 真實運轉（V22～V26）、macOS 與 Linux 實跑、AgentConsole 三層、KB 與偏好的退役提案、對 `set_maturity` 的實呼叫、M4 自動入 OBS | — | 實跑檢核或 §7.2 登記，不以構造資料充當 |

## 5. 測試資料規格

共用夾具住 `tools/tests/_selfimproving_p3_fixtures.py`（新增；底線開頭、不被收集；§5.7）與既有 P1／P2 夾具（呼叫形態不變，R134）。夾具模組自行定義判準函式與建構器，不 import 被測模組的內部私有符號（被測的公開函式級入口見 §5.6）；**函式名皆為建議**，Developer 改名須於勘誤登記對照。合成編號（PROP、RUN、ATT、DEC、OBS、DEF）一律於執行期以字串相加組出（`pid()`、`rid()`、`obs_id()`、`def_id()`）；本檔與測試原始碼不寫不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>`（NFR-P3-7；P1 R18 (a) 會掃整個 repo 的非忽略檔）。§5.3（逐字稿與決定語法）與 §5.5（Console 稽核檔、金鑰）沿 P2，P3 不新增；D12 的稽核檔變形沿用其 `write_audit`、`body_decide`、`body_obs_add`、`body_obs_close`（每份用新的 UUID `audit_ref`、重簽使一次只有一個缺陷；變形清單逐列寫在 AT-340-10 系各 AT 的 Given）。

### 5.1 基線 repo（`make_p3_repo`）、環境與常數

`make_p3_repo(dest, *, events=None, obs=(), defs=(), prm=None, commit=True) -> Path`：包裝 `make_p2_repo`——P1 與 P2 §5.1 的全部內容逐字不變（OBS 列 001～010、缺陷帳本家族〔其中一列的 `fixed@` sha 於 tmp repo 不存在，即 M2 的無法解析列〕、`<VOLD>`／`<VNEW>` 版本目錄與規則檔 `R-9.1`～`R-9.3`、`docs/notes/*.md` 等），再於其上：(1) 第一個 commit `C0` 以 `GIT_AUTHOR_DATE`、`GIT_COMMITTER_DATE` 設為 `TA`＝`2026-10-10T00:00:00+00:00`，其後 commit 把 `params.json` 的 `migration_base_sha` 寫為 `C0` 的 sha；(2) 工作樹新增 `docs/p3/area/t1.md`、`docs/p3/area/t2.md`（各 100 行 `line NNN`）、`docs/p3/area/f.md`、`docs/p3/areax/f.md`（各 20 行）；(3) `params.json` 為 **32 鍵**：P2 的 30 鍵逐值沿用（`w_opp` 5、`w_min` 5、`w_evt` 2、`w_n` 20、`stop_after_bad` 2、`churn_max` 2、`cap_frac` 0.9、`max_archive_entries_per_card` 50、`card_line_max` 100、`metrics_rev` 1、`event_max_bytes` 2000、`row_max_bytes` 700 等）加 `memory_index_max_lines` 200 與 `memory_index_max_bytes` 25600（以 `set_params(R, …)` 覆寫者，AT 明文寫出）；(4) 基底事件帳本 `BASE-EV`＝`run.open`、`research.skip`（offline）、`attr`（root，`obs` 為 `s1`、`root_cause` 為 `docs/stale-note`）與其 `attr.confirm`（`by` 為 `QA`）（沿 P2 `COOL-BASE` 的同名事件）。**常數**：`TA` 如上；`TP`＝`2026-10-20T10:00:00+00:00`（`P` 的 `app.promote.t`）；`D3`＝`docs/p3/area`；`T1`＝`docs/p3/area/t1.md`；`T2`＝`docs/p3/area/t2.md`；`s1`＝基底 OBS 第 2 列的 ID。**環境（hermetic）**：沿 P2 §5.1 (a)～(m)；另 (n) `CLAUDE_CONFIG_DIR` 指向 tmp，記憶索引預設路徑為 `<cfg>/projects/<slug>/memory/MEMORY.md`（`<slug>` 取 `transcript_dir(R)` 的末段）；(o) `GIT_AUTHOR_DATE`、`GIT_COMMITTER_DATE` 只在建構 commit 時以 `mock.patch.dict(os.environ, …)` 設定、用畢即還原；(p) 探針與 CLI 子行程不傳 `AUTOSDD_*`（`AUTOSDD_UNATTENDED` 只在明文要求的 AT 內設）；(q) 凡比較路徑者兩側先 `realpath`（雲端 runner 的 TEMP 為 8.3 短檔名或 symlink，OBS-SI-272）。

### 5.2 建構器與情境表

**建構器**（`_selfimproving_p3_fixtures.py`；事件與流程建構器沿 P1／P2：`ev`、`write_events`、`append_events`、`rewrite_event`、`drop_events`、`drive_to`、`decide_say`、`set_params`、`snap`、`M`、`MJ`）：

- `obs_at(R, n, when, path, *, reopens=None)`、`def_at(R, n, date, path, *, status="open")`：附加合法 OBS 或 DEF 列並回傳其 ID（`n` 為執行期組號的序數）；`when` 為 `YYYY-MM-DD HH:MM +00:00`（`時間` 欄原樣；省略 `+00:00` 者即無 offset 形）；證據座標一律 `<path>:<行號>`；`reopens` 寫入標記欄；`def_at` 的狀態欄逐字給。
- `root_attr(R, obs_ids, key, *, confirm=True)`、`link_attr(R, from_id, reopened_id, *, settle=None)`：手寫 `attr`（`by` 為 `SA`，即提出者）與其 `attr.confirm` 或 `attr.reject`（`by` 為 `QA`，避免 `CONFIRMER-IS-PROPOSER`；`settle` 為 `confirm`、`reject` 或 None＝未落定），回傳 `ATT` 編號；事件依呼叫順序入帳（S-BASE 的 link 先於晉升事件寫入）。
- `promoted(R, *, cls="D", action="modify", target=T1, sources=(s1,), t=TP, ack=False)`：手寫 `prop`、`card`、`dec`（approve）、`heldout.freeze`、`app.sandbox`、`app.verify`（PASS）、`dec`（promote）、`app.promote`（`t` 為所給）並回傳 PROP 號；`ack` 為真時 `dec` 的 `flags` 含 `unverified_ack` 且 `app.promote.unverified_ack` 為真；`rN.md` 的 `rollback` 欄為字面 `還原該行`。
- `mea_chain(R, prop, result, *, ev=2, opp=5, n_opp=5, at=None, amend=None, stop_at=None)`：為已晉升的 PROP 手寫 `mea.report`（baseline；`events`＝`ev`、`opp` 為 `opp` 個執行期組出的合法 ID，不要求存在於帳本）、`mea.open`、`mea.close`（`result`、`n_opp`、`at`）與選用的 `mea.amend`；`stop_at` 為 `open` 時只寫到 `mea.open`、為 `baseline` 時只寫 baseline；回傳 `mea.close` 的 `seq`。
- `try_prop(R, run, *, cls="D", action="add", target=T1, sources=(s1,), body_over=None, body_drop=(), extra_args=())`：以真 `prop-new` 建 PROP（P3 新增；**有別於 P2 夾具的 `new_prop`**——後者簽名與回傳不變〔回 PROP 號、斷言 rc 為 `0`〕，既有測試沿用）；patch 為 `add`＝新增檔、其餘 action＝於 `target` 第 1 行之後插入一行；本文由 `fx.body_md(cls, **body_over)` 組成（`body_drop` 指名的鍵不寫；R134 (f) 之後預設欄位表已含 `retire_when`、`reopen_symptom` 兩鍵的合規值），`extra_args` 附加於呼叫行；回傳 `(rc, stdout, stderr, PROP 號)`。`try_revise(R, prop, *, body_over=None, body_drop=())`：對態為 `returned` 的 PROP 呼叫 `prop-revise`（patch 沿原 rev），回傳 `(rc, stdout, stderr)`。
- `cap_index(entries, *, total_bytes=None, eol="\n", trail=0)`：2 行表頭（`# Memory` 與一個空行；LF 版共 10 位元組）加 `entries` 個條目行——第 i 行為 `- e` 接兩位數 i、一個空格、以 `x` 補到 50 位元組（不含行尾），每個條目連 LF 為 51 位元組（CRLF 版 52）；`total_bytes` 給了就調整最後一個條目的補字數使總位元組恰為該值；`trail` 為最後幾個條目行尾加的空白數。`fix_commit(R, date)`：以 `GIT_COMMITTER_DATE` 建空 commit 並回傳 sha。`DROP`：`ev()` 的哨兵，明示刪除該鍵。`win(R)`：事件帳本中 `mea.*` 事件（依 `seq`）。

**情境表**（時刻皆 UTC；證據座標皆在 `D3` 之下的 `f.md`，除非另述；OBS 列的 `時間` 為 `2026-10-DD HH:MM +00:00`，下以 `DD HH:MM` 簡記，DEF 列以發現日期的日末 instant 計）：

- **S-BASE**（單一 PROP `P`＝`promoted(R3)`，`target` 為 `T1`、`sources` 為 `s1`、`TP` 晉升）：b1＝09 12:00；b2＝11 09:00、b4＝13 09:00、b6＝15 09:00、b7＝16 09:00、b8＝17 09:00（機會列）；b3＝12 09:00、b5＝14 09:00（`reopens` 為 `s1`，link 已確認，`seq` 小於 `app.promote`）；b9＝18 09:00（`reopens` 為 `s1`，link 未落定，`seq` 小於 `app.promote`）。預期基線：`opp`＝b2、b4、b6、b7、b8；`events` 2；`pending` 1；`anchor`＝`TA`；b1 早於錨而不計。
- **S-ADOPT**（接在 S-BASE 後）：a1＝21 09:00、a2＝22 09:00、a3＝23 08:00、a4＝24 09:00（OBS）；a5＝DEF 列、發現日期 2026-10-25（instant 為 2026-10-25T23:59:59+00:00）；a6＝26 09:00（OBS）。a5 為第 5 筆機會列：`clean`、`n_opp` 5、`at` 同 a5 的 instant；a6 不計。
- **S-REC**＝S-BASE 加 a1（同上）與 r1＝23 09:00（`reopens` 為 `s1`，link 已確認）：`recurred`、`n_opp` 1、`at`＝2026-10-23T09:00:00+00:00。**S-PEND**＝S-BASE 加 a1～a5（同 S-ADOPT）與 c1＝22 12:00（`reopens` 為 `s1`，link 未落定）：`pending`、`n_opp` 5、`at`＝2026-10-25T23:59:59+00:00。**S-LATE**＝S-BASE 加 a1、a2、l1＝23 08:00（無標記、無 link）、a4、a5（同 S-ADOPT）：`clean`；晚到確認＝追加 l1 的 link（`reopens` 為 `s1`）與 `attr.confirm`；l2＝2026-10-27 09:00 的 link 與確認（關閉之後立案，不改窗）。**S-ROLL**＝S-BASE 加 a1＝21 09:00、a2＝22 09:00、手寫的 `dec`（`dkind` 為 `rollback`、`decided_at` 為 2026-10-22T12:00:00+00:00）、a3＝22 15:00：`rolled-back`、`n_opp` 2、`at`＝2026-10-22T12:00:00+00:00。
- **S-M**（`Pm`＝`promoted(R3, cls="M", target="memory/feedback_demo.md", sources=(s1,))`，`TP` 晉升；證據座標含檔名 `feedback_demo.md` 者為機會列）：m1＝21 09:00、m2＝22 09:00、q1＝24 09:00、q2＝25 09:00、q3＝26 09:00（機會列）；n1＝22 12:00（候選，`reopens` 為 `s1`；三份複本的 link 依序為已確認、已駁回、未落定）；m3＝23 10:00（座標 `docs/notes/other.md:3`、無鍵，不計）。預期：已確認＝`recurred`、`n_opp` 2、`at`＝2026-10-22T12:00:00+00:00；已駁回＝`clean`、5、2026-10-25T09:00:00+00:00；未落定＝`pending`、5、2026-10-26T09:00:00+00:00。
- **S-BOUND**（`P` 同 S-BASE、`TP` 晉升；OBS 帳本檔頭 `tz=+08:00`）：x1＝OBS 2026-10-09 12:00；x2＝DEF 發現日期 2026-10-09；x3＝DEF 發現日期 2026-10-10；y1＝20 09:59；y2＝20 10:00（與晉升同刻）；y3＝21 09:00；y4＝DEF 發現日期 2026-10-20（與晉升同日）；y5＝OBS 2026-10-21 18:30（無 offset，取檔頭 tz 得 10:30Z）；z1＝22 09:00、座標 `docs/p3/areax/f.md:1`；z2＝22 10:00、座標 `DOCS/P3/AREA/F.MD:2`；z3＝22 11:00、證據格無路徑。預期：基線 `opp`＝x3、y1；採納窗 `n_opp` 4＝y3、y4、y5、z2；y2、z1、z3 不屬任何窗。
- **S-SUSP**（`stop_after_bad` 為 2）：`run.open`（運轉 1）、`research.skip`、`run.close`；`promoted` 取 `A` 加 `mea_chain`（`recurred`）；`run.open`（運轉 2）、`research.skip`；`promoted` 取 `B` 加 `mea_chain`（`rolled-back`）；各 `promoted` 的 `target` 互異。折疊結果 `suspended` 為運轉 2。
- **S-PROBE-A**（八個 PROP，`target` 互異、根因鍵各自不同，以 `promoted` 加 `mea_chain` 手寫；`mea.close` 依 P1 至 P7 序入帳）：

| PROP | 窗（`mea.close`） | 基線 events／opp | 預期（M1） |
|------|------------------|------------------|-----------|
| P1 | `clean` | 2／5 | 可評估 |
| P2 | `recurred`（`n_opp` 2） | 3／5 | 可評估（唯一 `recurred`） |
| P3 | `clean` | 1／5 | `BASELINE-EVENTS-BELOW-W-EVT` |
| P4 | `clean` | 2／4 | `BASELINE-ROWS-BELOW-W-MIN` |
| P5 | `pending`（無 amend） | 2／5 | `WINDOW-PENDING`（不入 M5 分母） |
| P6 | `rolled-back`（`dec(rollback)` 的 `decided_at` 等於 `mea.close.at`；`ack` 為真） | 2／5 | `ROLLED-BACK-NO-RECURRENCE`（入 M5 分子） |
| P7 | `clean` | 2／5 | 可評估 |
| P8 | 只有 baseline 與 `mea.open` | 2／5 | `WINDOW-OPEN` |

  各 PROP 的 `dec` 為 approve 與 promote 各一（P6 另有 rollback）。冷卻繞過組（AT-322-1-2 追加）：`Q1`（`prop` 加 `dec` reject、`reason_class` 為 `證據不足`）與其後晚 1 日、同 `cls`、`action`、`target`、`sources` 的 `Q2`（`prop`），使 `fold` 得一筆 `COOLDOWN-BYPASS-SUSPECT`。P9＝`clean` 窗、opp 5（基線 events 依 AT 指明：AT-322-1-E-1 為 0、AT-322-1-E-2 為 2）；P10＝只有 `promoted`、無任何 `mea.*`。
- **S-FALS**（八個窗，依序入帳 `mea.close`，基線皆 2／5 除 W7）：W1＝A1、W2＝A2（`pending`）、W3＝A3，根因鍵皆 `k/x`；W4＝B1、W5＝B2（`clean`）、W6＝B3，鍵皆 `k/y`；W7＝C1（基線 1／5，不可評估）、W8＝C2，鍵皆 `k/z`；除 W2、W5 外窗結果皆 `recurred`。鍵經各 PROP 的 `sources` 列的 `root_attr`（已確認）取得。預期：`falsified` 為 true、`falsified_keys` 為只含 `k/x` 的清單。
- **S-M23**：DEF 列五個（發現日期 2026-09-20 至 2026-09-24，狀態 `fixed@<sha>`，各以 `fix_commit` 於發現日期之後 3、4、5、6、7 日建 commit，整日差中位數 5）；DEF 列一個（發現日期 2026-09-25、狀態 `closed-by-decision`）。發現日期皆早於錨，故不入全域窗。
- **S-CAP**：以 `cap_index` 建索引，參數與預期見 AT-327-1-1、AT-327-1-E-1、AT-327-1-E-2、AT-327-2-1、AT-327-2-E-1 的 Given（每個條目行 50 位元組加行尾；候選取數 `j` 依 R129 (d)，行位元組含行尾：17 個條目〔19 行〕於上限 20 行、`cap_frac` 0.9 得 `j` 為 3；18 個條目〔928 位元組〕於上限 1000 位元組得 `j` 為 2）；預設路徑索引放於 `<cfg>/projects/<slug>/memory/MEMORY.md`。
- **S-CHURN**（群：`target` 為 `T1`、根因鍵 `k/c`）：`c1`＝OBS 2026-10-11 09:00、座標 `docs/p3/area/f.md:3`、`root_attr` 鍵 `k/c`（已確認）；`c2`＝OBS 11 10:00、座標 `f.md:4`、鍵 `k/other`；以 `promoted` 依序手寫 `A1`（add，12 10:00）、`R1`（retire，13 10:00）、`A2`（add，14 10:00）、`R2`（retire，15 10:00）、`A3`（add，16 10:00）、`R3p`（retire，17 10:00），`sources` 皆為 `c1`；`n1`＝OBS 18 09:00、座標 `f.md:9`。capability-delta 的兩個 AT（AT-326-2-1、AT-326-2-E-1）：`TR`＝`R1` 的 `app.promote.t`（2026-10-13T10:00:00+00:00）；`n2`＝DEF 發現日期 2026-10-13（座標 `f.md:14`）；`o1`＝OBS 14 10:00（座標 `f.md:3`，與 `c1` 相交）；`o2`＝OBS 12 09:00（座標 `f.md:11`）；`d0`＝DEF 發現日期 2026-10-12（座標 `f.md:12`）；`d1`＝DEF 發現日期 2026-10-13（座標 `f.md:13`）。
- **DEF-EDGE**（AT-340-6-E-2；合成缺陷帳本主檔，表頭欄位順序換成 ID、狀態、發現日期等；預期結案類）：`fixed@abc1234`→`fixed`、`closed-by-decision`→`closed-by-decision`、`no_action_needed`→`closed-by-decision`、`open`→`open`、`wontfix`→`wontfix`、空白狀態→null；另有 ID 欄含空白的無效列（兩個解析器皆略過）。

### 5.4 事件欄位表負控（MEA-NEG）

**MEA-NEG**（AT-340-1-E-1；每列為對「S-ADOPT 跑過 `measure` 的合規帳本」的一處改寫，以 `rewrite_event`、`drop_events`、`append_events` 實作；`events.mea` 的碼集合恰為單一碼）：

| # | 改動 | 預期碼 |
|---|------|--------|
| N1 | `mea.open` 缺 `w_opp` | `MEA-KEY-MISSING`（`MEA-CLOSE-N` 無 `w_opp` 可比，不另報） |
| N2 | `mea.close` 多一個鍵 `note` | `MEA-KEY-UNKNOWN` |
| N3 | `mea.report`（check）帶 `prop` | `MEA-KEY-UNKNOWN` |
| N4 | `mea.open` 的 `w_opp` 為字串 | `MEA-TYPE`（同上，不另報 `MEA-CLOSE-N`） |
| N5 | baseline 的 `events` 為負數 | `MEA-TYPE` |
| N6 | `mea.report`（check）的 `missing` 有一項 61 字元 | `MEA-TYPE` |
| N7 | `mea.close` 的 `result` 為表外值 | `MEA-ENUM` |
| N8 | baseline 的 `report` 為表外值 | `MEA-ENUM` |
| N9 | `mea.close` 的 `n_opp` 大於 `w_opp` | `MEA-CLOSE-N` |
| N10 | `clean` 的 `n_opp` 小於 `w_opp` | `MEA-CLOSE-N` |
| N11 | `mea.open` 的 `promote_seq` 不等於晉升事件的 `seq` | `MEA-PROMOTE-SEQ` |
| N12 | `mea.open` 指向未晉升的 PROP（另有一個 `proposed` 的 PROP） | `MEA-NOT-PROMOTED`（連帶 `events.transitions` 為 `FAIL`、碼 `TRANSITION-ILLEGAL`） |
| N13 | 第二筆 baseline 置於首筆 baseline 與 `mea.open` 之間 | `MEA-BASELINE-DUP` |
| N14 | 唯一的 baseline 的 `seq` 在 `mea.open` 之後 | `MEA-BASELINE-ORDER` |

AT-340-8-E-1 的 P2 負控取自 `tools/tests/test_selfimproving_events_p2.py` 的事件欄位負控表（本檔不重列）。

### 5.6 測試 seam、函式級入口、判準函式與逐字清單

- **被測函式級入口**（建議名）：`mea.plan(ctx)`；`meastat.metrics(ctx)`；`meawrite.measure(repo, *, by="main", record_check=False)`（回傳 rc、文字與 JSON 物件；AT-340-2-E-2 以 `ThreadPoolExecutor` 並行呼叫、以 `future.result()` 取回，OBS-SI-275）；`meawrite.plan_amends(repo, events)`（`attr_settle` 於同鎖內呼叫；OBS 帳本由 `meawrite` 自 `repo` 讀取，讀不到回空清單；測試以 `mock.patch.object` 換成回空清單的替身）；探針 `build_report(repo) -> dict` 與 `main(argv) -> int`（以 `importlib` 依檔案路徑載入，`sys.path` 含 `tools`）；`retire.form_problems(text) -> list`；`capacity.evaluate(index_bytes, kb, prefs, params)`、`capacity.truncation_risk(index_bytes, params)`（無風險回 None）、常數 `capacity.KB_MAX_ENTRIES`（1000）與 `capacity.PREFS_MAX_KEYS`（10）；P2 既有 seam `evwrite.PAUSE_HOOK`、`evwrite.LOCK_TIMEOUT_SECONDS`。
- **測試自有判準函式**：`probe_purity_problems(src)`（AST；碼 `P-SUBPROCESS`、`P-NET`、`P-MODEL`、`P-WRITE`、`P-ENV`、`P-NON-RO-IMPORT`）；`sop_p3_problems(text)`（碼 `SOP-P3-FORBIDDEN`、`SOP-P3-REQ-MISSING`、`SOP-P3-ORDER`、`SOP-P3-PLACEHOLDER`、`SOP-P3-STALE-WORDING`）；`fp_ref(parts)`。沿用既有：`capability_problems`、`make_pkg`、`synth`（`test_selfimproving_capability.py`）；`parse_at_headers`、`anchor_problems`、`collect_nodes`（`test_selfimproving_p2_meta.py`，匯入不複製）。
- **SOP-P3-FORBID**（〈擷取者〉〈歸因者〉〈提案者〉〈研究者〉四節不得含；P3 開工時各片段於四節的命中數為零）：`params.json`、`selfimproving_measure`、`metrics.md`、`w_opp`、`w_evt`、`w_min`、`stop_after_bad`、`churn_max`、`M1`、`fingerprint`。
- **SOP-P3-REQ**（〈P3 動詞〉節〔位於〈P2 動詞〉之後〕須含；除第 6 列外，字面須位於程式碼圍欄之外）：1 rc 契約表的 `measure` 列，含 `AUTOSDD_UNATTENDED` 與 `rc 1`；2 rc 契約表的 `capacity` 列，含 `NOT-EVALUABLE` 與量不到不是 rc 3；3 序列句：`promote`、主控 `commit`、`measure` 依此次序；4 `run-close` 之前跑一次 `measure` 作補記；5 回滾序列散文：`measure` 印卡、卡面逐字貼給掌舵者、掌舵者打字回滾、`decide --kind rollback`、`rollback`；6 一個 `powershell` 與一個 `bash` 圍欄，各含 `decide` 與 `rollback` 指令；7 退役配方：`--cls M`（容量候選走 M 類歸檔型 PROP，不用 `--action retire`）、`--action retire`（只用於已被 promoted PROP 採納的工件）、本文欄位 `retire_when`、`reopen_symptom`、字面 `目標在役`（scan 候選須先確認）；8 R 類退役句：`set_maturity(reviewed_by=`；9 讀值紀律三句：`NOT-EVALUABLE 不得改寫為達標`、`M1 不得單獨宣稱成效`、`反證條件成立只列為 T1 決策項`；10 隔離條文：`提案者任務書不含指標目標值、計算細節與 params.json 路徑`。另：〈啟動條件〉節不含 `尚無該動詞`；〈P3 動詞〉節不含 `待補`、`TODO`。

### 5.7 允許變更的檔案集合（新檔名為本檔類推——PRD 無 P3 套件檔條目；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md`；Developer 棒只動此集合）

| 類別 | 路徑 |
|------|------|
| 新增（程式） | `tools/lib/selfimproving/{mea,meastat,meacheck,meawrite,capacity,retire,churn}.py`，可選 `meaplan.py`（R132 兩態擇一）；`tools/probe/selfimproving_measure.py` |
| 新增（測試） | `tools/tests/{_selfimproving_p3_fixtures,test_selfimproving_measure,test_selfimproving_measure_verb,test_selfimproving_measure_probe,test_selfimproving_capacity_retire,test_selfimproving_p3_meta}.py` |
| 修改（程式） | `tools/lib/selfimproving/{fold,status,export,card,props,evcheck,check,params,defs,evwrite,writeverbs}.py`（增量上限：`defs.py` ≤+8、`evwrite.py` ≤+12、`writeverbs.py` ≤+15 且總數 ≤400、`props.py` 與 R127 合計 ≤+20，依 D 表與 R121 (e)、R122 (g)、R127、R128）；`tools/selfimproving.py`；D12：`tools/lib/selfimproving/{consoleaudit,decwrite,obswrite,obsrows}.py`，必要時 `events.py` 增公開入口（≤10 斷言行，R136） |
| 修改（測試） | R134 同步站點（僅限該條所列函式與常數）：`test_selfimproving_check.py`、`test_selfimproving_events.py`、`test_selfimproving_events_p2.py`、`test_selfimproving_export_status.py`、`test_selfimproving_p2_meta.py`、`test_selfimproving_props.py`、`_selfimproving_fixtures.py`、`_selfimproving_p2_fixtures.py`、`test_selfimproving_capability.py`（含 AT-340-4-2、AT-340-4-E-2 新函式）；D12：`test_selfimproving_console_obs.py`（AT-340-10 系六個新函式；既有函式僅限 R134 所列站點） |
| 修改（文件與資料） | `docs/05_development/SelfImproving_Operations_SOP.md`（〈P3 動詞〉節、〈啟動條件〉措辭）；`docs/06_quality/SelfImproving_Protocol/params.json`（加兩鍵，與 `PARAM_SPECS` 同 commit，D9） |
| 主控專屬 | 真帳本與真事件帳本；護欄層重釘、compat-ci `paths`、`tools/tests` 棘輪；RTM 檔 `docs/06_quality/RTM-SelfImproving-P3-<日期>.md`；SCG-4 報告 |
| 不得變更 | `.claude/**`、PRD、研究方法 SOP、P0～P2 TCS、`autoclaude/` 引擎原始碼、`AgentConsole/**`、`.github/**` |

---

## 6. RTM 連結確認

追溯鏈（US→AC→AT→測試檔→規則→NFR）已在 §1（AC→AT）、FRD-lite（US→AC、NFR）與下表閉合；根層 RTM 檔由主控於 SCG-4 依落點 SSOT 落 `docs/06_quality/RTM-SelfImproving-P3-<日期>.md`（本檔不代寫）。**覆蓋核對**：AC 23 個皆有至少一個正控與一個負控 AT；全檔 AT 78 個（正控 35、負控 43），分佈於七個測試檔（MW 21、MV 10、PB 12、CR 17、M3 10、CP 2、CN 6），每個新檔不超過 35 個 AT（NFR-P3-9；CN 為既有檔，本檔只新增 6 個函式）。

### 6.1 US → AC → AT

| US ID | AC ID | AT 數 | 測試檔 | 主要規則與 NFR |
|-------|-------|-------|--------|----------------|
| US-301 | AC-323-1、AC-323-2、AC-340-1、AC-340-2 | 12＋3＋3＋4＝22 | MW、MV | R111～R123；NFR-P3-1、2、3、11、12 |
| US-302 | AC-324-1、AC-324-2 | 4＋2＝6 | MW | R114 (e)；P2 R93 |
| US-303 | AC-322-1、AC-322-2、AC-322-3、AC-340-6 | 5＋3＋2＋4＝14 | PB、M3 | R124～R126、R133 (e)；NFR-P3-1、3、11 |
| US-304 | AC-325-1、AC-325-2、AC-326-1、AC-326-2 | 3＋2＋2＋2＝9 | CR | R127、R128；NFR-P3-12 |
| US-305 | AC-327-1、AC-327-2、AC-340-3 | 4＋2＋2＝8 | CR | R129；NFR-P3-3、11、12 |
| US-306 | AC-340-4、AC-340-5、AC-340-7、AC-340-8、AC-340-9 | 4＋3＋2＋2＋2＝13 | MV、M3、CP | R130～R135；NFR-P3-4～10 |
| US-307 | AC-340-10 | 1＋5＝6 | CN | R136；NFR-P3-11、12 |

### 6.2 行為規則 → AT（R111～R136 每條至少一個 AT）

| 規則 | 主題 | AT |
|------|------|----|
| R111、R112 | 動詞、旗標、rc、`measure` 輸出 | AT-340-2-1、AT-340-2-E-1、AT-323-2-E-2、AT-340-3-1、AT-340-3-E-1 |
| R113、R115 | `mea.*` 欄位表、`events.mea`、33 項與判準版本 | AT-340-1-1、AT-340-1-E-1、AT-340-1-E-2、AT-340-8-E-1 |
| R114 | `fold` 增量與 SUSPENDED | AT-323-1-E-4、AT-324-1-1、AT-324-1-2、AT-324-1-E-1、AT-324-1-E-2、AT-324-2-1、AT-324-2-E-1 |
| R116～R119 | 列宇宙與時刻、機會列、再現歸屬、基線窗（PRD〈M1 判定細則〉(f) 的 `W_OPP ≥ W_MIN` 耦合→P0 AT-031-1-E-3） | AT-323-1-1、AT-323-1-3、AT-323-1-4、AT-323-1-E-1、AT-323-1-E-2 |
| R120、R121 | 採納窗關閉、pending 落定、晚到確認、attr 動詞同鎖追加與 measure 補記 | AT-323-1-2、AT-323-1-5、AT-323-1-6、AT-323-1-7、AT-323-1-E-5、AT-324-1-2 |
| R122 | 規劃、冪等、fail-loud、`--record-check`、多事件追加 | AT-323-1-E-3、AT-323-1-E-5、AT-340-2-1、AT-340-2-2、AT-340-2-E-2 |
| R123 | 回滾提案卡 | AT-323-2-1、AT-323-2-E-1、AT-323-2-E-2 |
| R124、R125 | M1、反證條件、M4、M5、資訊欄 | AT-322-1-1、AT-322-1-2、AT-322-1-E-1～AT-322-1-E-3 |
| R126 | 探針形態、指紋、純度、不接閘門 | AT-322-2-1、AT-322-2-E-1、AT-322-2-E-2、AT-340-6-1、AT-340-6-E-1～AT-340-6-E-3 |
| R127 | 退役欄位 | AT-325-1-1、AT-325-1-E-1、AT-325-1-E-2、AT-325-2-1、AT-325-2-E-1 |
| R128 | 抖動與 capability-delta | AT-326-1-1、AT-326-1-E-1、AT-326-2-1、AT-326-2-E-1 |
| R129 | 容量與截斷風險 | AT-327-1-1、AT-327-1-2、AT-327-1-E-1、AT-327-1-E-2、AT-327-2-1、AT-327-2-E-1、AT-340-3-1、AT-340-3-E-1 |
| R130 | `status` 與 `export` | AT-340-5-1、AT-340-5-2、AT-340-5-E-1 |
| R131、R132 | `params`、能力登記與 LOC | AT-340-4-1、AT-340-4-E-1、AT-340-4-2、AT-340-4-E-2 |
| R133 | SOP 與提案者隔離 | AT-322-3-1、AT-322-3-E-1、AT-340-7-1、AT-340-7-E-1 |
| R134、R135 | 零退化、AT 錨定與範圍 | AT-340-8-1、AT-340-8-E-1、AT-340-9-1、AT-340-9-E-1 |
| R136 | Console 載體三動詞的寫入前判準（承接 DEF-200-568） | AT-340-10-1、AT-340-10-E-1～AT-340-10-E-5 |

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（⚖ 1～⚖ 19；⚖ 11 已由主控裁決取消、編號保留不重排）

| 編號 | 問題 | 本檔預設 | 替代與再開症狀 |
|------|------|----------|----------------|
| ⚖ 1 | P3 出口 (b)(c) 需要真實 promoted PROP 與真實退役提案，而真帳本現無 | 本檔只定機制面（AT）；出口 (a)(d) 現況可達成（V22、V26）；(b)(c) 於 V24、V25 如實標「未達成（前置未成立）」，不以構造資料充當 | 替代：先以 P2 的真實運轉產生 promoted PROP 再驗收。再開：掌舵者要求在無真實採納下宣稱 P3 出口 |
| ⚖ 2 | PRD §9.3 把 `mea.amend` 寫成 `attr-confirm`、`attr-reject` 同鎖追加 | **照 PRD（主控裁決）**：兩個動詞於同一把寫入鎖內（`link` 型 `attr` 落定時；`root` 型不產生 amend，其使既有候選改歸屬者由下次 `measure` 補記）呼叫 `meawrite.plan_amends(repo, events)`（判準＝`mea.plan` 的 amend 分支，單一窗規則實作）追加；`measure` 為冪等補記者（輸入不可用、手寫確認事件或替身而未追加者）；為此 `evwrite.append_event` 的 `build` 可回事件清單（R122 (g)） | 替代：只由 `measure` 追加（需 PRD 修訂）。再開：`attr-confirm`、`attr-reject` 的延遲或鎖競爭因窗重放而可觀測地惡化 |
| ⚖ 3 | 回滾提案卡的版式（首行、核心區至多 12 行、樣板行）PRD 未定 | R123 的版式（本檔類推）；絕不自動回滾 | 再開：掌舵者看過真卡後要求增減行 |
| ⚖ 4 | 時刻比較：DEF 日精度、同刻兩側皆不屬 | R116 (b)(c)：DEF＝日末 instant；錨、晉升、關閉時點皆嚴格比較 | 再開：真帳本出現同日 DEF 使窗歸屬與人工判讀不一致 |
| ⚖ 5 | DEF 側再現候選無確認態（`attr` 只收 OBS） | R118 (b)：DEF 候選不屬任何窗、不造成 `pending`，只計資訊欄 `unattributable_candidates` | 替代：P4 讓 `attr` 收 DEF。再開：真帳本的 DEF 再現列常見且需歸屬 |
| ⚖ 6 | M 類機會列的認定（PRD 寫「檔名或條目標題」） | R117 (b)：已確認根因鍵或檔名子字串；條目標題引用不判（WHY：離線不讀記憶檔內容，條目標題不可解；PRD 修訂建議見 §7.3） | 再開：M 類窗在真運轉中機會列過少或過多 |
| ⚖ 7 | 窗序與「最近 `W_OPP` 筆」 | R116 (d)：（日期字面, ID 尾號, ID 全文）升冪 | 再開：同日多列的次序使窗結果與人工判讀不同 |
| ⚖ 8 | M4 離線無法判新證據例外 | R125 (a)：M4＝`COOLDOWN-BYPASS-SUSPECT` 筆數（上界），附草稿列只印不寫（P2 TCS 提到的自動入 OBS 不做） | 再開：假陽性使 M4 失真，或掌舵者要求自動入帳 |
| ⚖ 9 | SUSPENDED 的範圍與恢復 | 沿 P1 R35、P2 R93：只擋 `prop-new`、`prop-revise`；恢復綁折疊出的運轉、不歸零連續計數；`pending` 不計入也不打斷 | 替代：恢復後歸零。再開：恢復後同一壞序列立即再度暫停而被人工判為不合理 |
| ⚖ 10 | M5 的分子與兩值 | R125 (b)：分子取窗內 `dec(rollback)` 的事實，兩值並列（以 `unverified_ack` 分區）；窗後回滾列 `late_rollbacks` | 再開：掌舵者要求分子隨改判變動 |
| ⚖ 12 | `capacity` 預設輸入 | 只有預設路徑記憶索引；KB 與偏好須旗標；`status` 只用預設輸入、`export` 恆 NE | 再開：掌舵者要求 `status` 也讀 KB 與偏好 |
| ⚖ 13 | `events.mea` 是否重報 amend 指向與轉移 | 不重報，由 `fold` 以 `TRANSITION-ILLEGAL` 呈現（單一實作） | 再開：同一事件在兩項得兩種碼而造成誤讀 |
| ⚖ 14 | 旗標細部與 rc 細節 | R111：`--by`、`--record-check`、`--memory-index`、`--kb-metrics`、`--prefs`（PRD §9.3 只列動詞名） | 再開：PRD 修訂定其旗標 |
| ⚖ 15 | `mea.py` 逼近 400 斷言行 | D 表可選檔 `meaplan.py`（`ro`）：Developer 於 `mea.py` 將超過 380 時拆出，兩態擇一（R132）；**不走勘誤** | 再開：實作 LOC 超限而兩態皆不足 |
| ⚖ 16 | 記憶索引上限 | `memory_index_max_lines` 200、`memory_index_max_bytes` 25600，皆為「初值（未校準）」（S-08 的 25KB 換算未查證） | 再開：真索引觀測到被截斷的位元組門檻不同 |
| ⚖ 17 | 歸檔候選的位元組估算 | R129 (d)：行位元組含行尾終止字元；以被移除行中最長一行保守估一行歸檔指標 | 再開：歸檔後用量仍高於 `cap_frac` |
| ⚖ 18 | 探針指紋是否含 `CHECK_RULES_REV` | 不含（R126 (c)）：只改 `check` 判準版本不使量測數字斷代 | 再開：量測判準由程式碼改動而數字不可比時，須人工升 `metrics_rev` |
| ⚖ 19 | D12（DEF-200-568）的判準邊界：「與 `check` 同一判準」與主控指定的四碼之間的細節 | (1) **控制字元碼名**：主控指定 `FIELD-CONTROL-CHAR`，本檔改用既有碼 `CTRL-CHAR`（主控准許依既有碼表同族命名）——P0 `row.control_chars` 與 `check` 對 OBS 列已以 `CTRL-CHAR` 判 C0 與 DEL，P2 的 AT-235-1-E-1 對 `obs-add` 的 `\t` 斷言恰為 `CTRL-CHAR`；另立同義碼會使同一條件在兩動詞得兩種碼，並逼 P2 既有 AT 改斷言；`decide` 的 `reason` 沿同名（一概念一碼）；(2) C0（`\x00`～`\x1f`，含 `\t`、`\n`、`\r`）一律拒收，比 `check` 對 `reason` 的判準（只判 `\n`、`\r`）嚴；DEL 只由既有列規則判（OBS）；以 `body` 原值判、不先 trim（Console 側先 trim 再判，兩端相容）；(3) 只掃自由文字欄（`reason`；`context`、`symptom`、`evidence`、`exposure`、`marks_extra` 各值），列舉欄與 ID 欄已各有既有碼；(4) `disposition` 含 `\n` 只報 `DISPOSITION-INVALID`（新增），其他 C0 為既有 `CTRL-CHAR`；(5) `REASON-EMPTY` 只判空字串，只含空白者與 `check` 同判而放行；`flags` 空陣列對任何 dkind 放行（R94）；(6) 其餘碼名沿主控指定 | 替代：統一為 `FIELD-CONTROL-CHAR`（改名走勘誤，P2 AT-235-1-E-1 (l) 併入 R134 站點、同步 P2b）。再開：主控要求統一碼名；Console 輸入框需保留 tab；真實操作出現只含空白的 `reason` 被人工判為不合理；P2b 側規則與 R136 漂移（主控連動時對表） |

### 7.2 P2 TCS 承接項（P2 已 RELEASE；下列為其遺留、刻意不做與收尾教訓，P3 逐項處置）

| 來源 | 承接內容 | 本檔處置 |
|------|----------|----------|
| DEF-200-568（P2 R94～R97；缺陷帳本 open、承接輪次 R214、鍵 D12） | Console 載體三動詞收下壞稽核檔、事後 `check` 才紅（accept-then-red） | D12、R136、AC-340-10：四碼寫入前拒收、判準不改 `check`；**交付連動（主控處理）**：P2b TCS（W12）Console 側同判準的兩端防線，其碼表與 R136 的四碼逐一一致；根層收緊後 P2b 的 ⚖3 再開症狀「規則漂移」關閉 |
| P2 TCS §4〈刻意不做〉 | `capacity`、`mea.*` 的寫入、M1～M5、退役 | 全部承接：D1～D6（R111～R129） |
| P2 TCS §4、R98 | M4 的計數與自動入 OBS | 只計數並印草稿列（⚖ 8） |
| P2 TCS R72 | `mea.*` 只有被消費鍵的型別檢查 | R113、R115 欄位表與 `events.mea` |
| P2 TCS（`status.capacity` 恆 NE） | 容量事件偵測 | R130 (b)；P2 的 `status` 14 鍵斷言改為 15 鍵（R134） |
| P2 R93、P1 R35 | SUSPENDED 折疊 | 折疊不改，以 AC-324-1 與 AC-324-2 的各 AT 重釘；`prop-new` 拒收沿用 |
| OBS-SI-271（deferred） | 無人值守與用法預檢的先後逐動詞不一致 | `measure` 沿 P2 R68：用法先於拒收；其他動詞維持 deferred，不在本檔範圍 |
| OBS-SI-265 | AT 對帳要用錨定計數 | AT-340-9-1；NFR-P3-10 (11) |
| OBS-SI-266 | `__main__` 守衛須在檔尾 | NFR-P3-10 (10)；V19 腳本模式檢核 |
| OBS-SI-267 | PowerShell 不展開萬用字元給 pytest | 判定指令一律明確檔名；V18、V19 先展開成明確路徑 |
| OBS-SI-263、OBS-SI-264 | 交卷數字只當提示；全套期間不呼叫 `--pace` | NFR-P3-10 輸出逐字貼入；V20 期間不呼叫 `--pace`、不派 Agent |
| OBS-SI-268 | 任務書引用的修法須標預跑與否 | 審查回補時由主控標明（任務書紀律，不入 AT） |
| OBS-SI-272 | 雲端 runner 的 TEMP 為 8.3 短檔名或 symlink | §5.1 (q) 路徑比較兩側先 `realpath`；V28 |
| OBS-SI-275（deferred） | 執行緒競態子案須原樣拋出執行緒內例外 | AT-340-2-E-2 以 `ThreadPoolExecutor` 與 `future.result()` |
| OBS-SI-269、OBS-SI-270（deferred） | `obswrite` 還原雙重失敗靜默；`verify` 的 `rmtree` 以 traceback 穿出 | 不在 P3 範圍（`meawrite` 不用這兩個原語），維持 deferred |
| P2 SCG-4 報告 §F 的未驗項：V7、V8、V9、V10、V13、V14、V15；AgentConsole 對 `export` 新鍵的消費 | V8、V9、V15 的真實運轉（P3 出口 (b) 的前置：真實 promoted PROP）；其餘各項為 P2 自己的 RELEASE 後排程 | 前置見 ⚖ 1 與本檔 V24；P3 另列同型檢核 V20（全套）、V23（真 repo 煙霧）、V28（macOS 與 Linux 未驗）、V29（編譯計數）；`export` 新鍵（`window`、`measure`）的消費屬 P1b／P2b 側 TCS，本檔只保證 `schema_rev` 維持 1、只加鍵（R130） |

### 7.3 PRD 修訂建議（凍結檔不改；列此供 T1 或 PRD 修訂）

- §9.3 補 `measure`、`capacity` 的旗標與 rc（⚖ 14）；§9.3 `attr` 列已由本檔照辦（⚖ 2），無修訂建議。
- §9.2 `mea.*` 欄位表：補 R113 的欄位、值域與碼；§1.3〈M1 判定細則〉補 R116 的 instant 規則（DEF 日末 instant、同刻兩側皆不屬）、窗序與「再現優先」推廣到全部類別（⚖ 4、7）；AC-SI-23-1 與〈M1 判定細則〉(d) 的「或條目標題」改為只認檔名（離線不讀記憶檔內容，⚖ 6）。
- §9.4 補「探針指紋不含 `CHECK_RULES_REV`」（⚖ 18）；§9.1 C5 的 `params.json` 鍵數 30 改為 32（⚖ 16）。

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 23 個 AC 無未映射者（§1） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 有判定指令與驗收字樣；判定指令的 `-k` 字串等於 AT 底線形接結尾底線（錨定名，R135） | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（E 類；流程型 AC 的負向＝對 SOP 條文逐一刪去的副本須判不合格）；全檔負控數（43）不少於正控數（35） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試（§4 各列：錨與晉升的前後與同刻、日精度、`stop_after_bad` 2／3／4、`churn_max` 2／3、`cap_frac` 恰等於與少一單位、載入上限恰等於、DEF 同日與前一日、位元組 900 與 899） | □ |
| 併發負控 | 兩執行緒同時 `measure` 不重複事件（AT-340-2-E-2） | □ |
| 稽核檔變形的寫入前拒收（D12） | 四型各一條負控、一條合法正控、一條回歸（AT-340-10-1、AT-340-10-E-1～AT-340-10-E-5）；被拒後帳本與事件帳本位元組不變、`check` 仍綠；寫入端與 `check` 同源（AT-340-10-E-2 的差分） | □ |
| 純度與能力登記 | 47／48 鍵（R132 兩態）四類登記表與合成樹自證、載入面（`-X importtime`）、探針純度與注入自證（AT-340-4-2、AT-340-4-E-2、AT-340-6-E-1、AT-322-2-E-2、AT-325-2-E-1） | □ |
| 差分與獨立實作 | DEF 解析、指紋重算、引擎常數（AT-340-6-E-2、AT-322-2-1、AT-327-1-2） | □ |
| 測試資料規格完整 | 資料來源明確定義（§5：建構器、情境表、MEA-NEG、判準函式與清單、檔案集合） | □ |
| 實跑檢核 V16～V31 全部有逐字輸出證據 | 見下表；沒貼輸出＝未驗證；V24、V25 於前置未成立時必須如實標「未達成」 | □ |

**實跑檢核（非 AT；QA 於 SCG-4 親跑，輸出逐字貼入證據；AT 不碰真帳本與外網，真帳本的驗收全在這裡；讀 rc 先存變數再讀，不接管線）**

| 編號 | 檢核 | 指令與證據 | 判斷標準 |
|------|------|-----------|---------|
| V16 | 範圍守衛 | `git diff --name-only <Developer 棒起點>..HEAD`；`git diff --stat -- .claude`；`git status --porcelain` | 只含 §5.7 的集合與主控收尾檔；`.claude/**`、PRD、研究方法 SOP、P0～P2 TCS、`autoclaude/` 引擎原始碼、`AgentConsole/**` 無變動；真事件帳本、真 OBS 帳本與真 `SelfImproving_Proposals/` 不在 Developer 棒的 diff 內；`params.json` 只多兩鍵 |
| V17 | 真 repo `check` | `python tools/selfimproving.py check --json`（rc 先存變數）；貼 JSON | rc 0；`items` 為 33 項；`events.mea` 為 PASS（真事件帳本尚無 `mea.*`）；其餘各項同 P2 實況（PASS 或 nonblocking NE）；牆鐘小於 30 秒（3 次取最大值） |
| V18 | P0～P2 回歸與同步範圍 | 先以 `Get-ChildItem` 展開 SI 既有測試檔為明確路徑（OBS-SI-267），再 `python -m pytest <明確路徑…> -q -p no:xdist -o addopts=`（逐字貼末行）；`git diff -U0 -- tools/tests/`（Developer 棒範圍） | 全綠；既有測試函式與夾具的 diff hunk 只落在 R134 (a)～(f) 所列站點（斷言值或預設值同步）；P0 的 42、P1 的 163、P2 的 137 個 AT 各至少有一個對應函式（AT-340-8-1 同判） |
| V19 | P3 新 AT 全套 | 對五個新測試檔與 `test_selfimproving_capability.py` 各跑 `python -m pytest tools/tests/<檔> -q -p no:xdist -o addopts=`；另對 §2 每個 AT 以其判定指令各跑一次；腳本模式 `python tools/tests/<檔> -k <該檔任一 AT 的底線形>_` | 全綠；每個 `-k` 恰收一個測試；每個 AT 的驗收字樣已在交卷逐項列出；腳本模式收到至少一個測試而不是 `Ran 0 tests`；`__main__` 守衛在檔尾（OBS-SI-266） |
| V20 | 護欄與零退化 | `ruff check`（新增與改動的每個 `.py`）；`python AutoClaude/tools/check_loc_budget.py --json`；`python tools/sync_onboarding_baselines.py --check-snapshot`；官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`；期間不呼叫 `--pace`、不派 Agent）；`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（主控）；compat-ci `paths` 覆蓋現查；`git grep` 本檔、測試與程式碼的字面 ID | 皆 rc 0；護欄層重釘後淨差額 +0（具名一次性例外，名冊上限上修可見）；根層全套 unittest 通過數以實跑為準；無不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>`；每個套件檔斷言行不超過 400 |
| V21 | params 與能力登記 | 逐鍵對照 R131、R132：`params.json` 為 32 鍵、兩新鍵值為 200 與 25600；`CAPABILITY` 為 47 鍵（35／8／2／2；可選 `meaplan` 時 48 鍵 36／8／2／2） | `check` 的 `params.keys` 為 PASS；AT-340-4-1、AT-340-4-2 綠；`params.json` 與 `PARAM_SPECS` 同 commit 修改（Developer 同棒） |
| V22 | 出口 (a)：量測腳本在真實帳本上跑通（主控執行） | `python tools/probe/selfimproving_measure.py --json` 與文字形態（零 token；rc 先存變數；3 次取最大牆鐘） | rc 0；輸出含 M1～M5 各欄的值或 NOT-EVALUABLE（樣本不足如實印 NE 與理由，不印 0）、n、窗定義、判準指紋；兩次輸出逐位元相同；牆鐘小於 30 秒。**如實預期**：真事件帳本尚無 promoted PROP，M1 為 NE（`no-evaluable-window`）、M5 為 NE（`sample-below-w-min`）；達標判準是跑通且 NE 誠實 |
| V23 | 真實唯讀煙霧 | 真 repo：`python tools/selfimproving.py capacity --json`；`status --json`；`export --kind status --json`；前後各貼 `git status --porcelain` 與 HEAD | 三者 rc 0；`status` 為 15 鍵；`capacity` 的 `memory_index` 為 `read` 或 NE（如實）；`export` 的 `capacity` 恆為 NE（`export-reads-no-home`）；前後輸出逐字相同（零寫入）；牆鐘小於 30 秒 |
| V24 | 出口 (b)：至少一個採納量測窗關閉並入帳（主控執行；非構造） | 前置：存在真實 promoted PROP（P2 TCS 的真實運轉 V8、V9、V15 之一已走完）；`python tools/selfimproving.py measure`（`AUTOSDD_UNATTENDED` 未設），依窗進度重跑；`export --kind events --json` 取 `mea.*` | **現況（撰寫時 HEAD；凍結時以 `python tools/selfimproving.py status` 現查，不採信本句）**：真帳本只有一個 `proposed` 的 PROP、無 promoted PROP，本項**未達成（前置未成立）**，歸入 PRD §8.3 的 📎 驗收資料殘留（殘留＝缺真實 promoted PROP 與其關閉的窗），不以構造 PROP 或合成事件充當；前置成立且窗關閉後驗：`mea.close` 的 `result` 為四值之一、`events.mea` 為 PASS、窗內機會列計數可由 OBS 與 DEF 帳本獨立重算 |
| V25 | 出口 (c)：至少一筆退役提案走完人工閘（主控執行；掌舵者真人打字） | 前置：掌舵者指定某已被真實 promoted PROP 採納的工件退役（R127 (c)）；`prop-new --action retire`（本文欄位表含兩欄）→`card --issue`→掌舵者打字核准→`decide`→P2 的後續動詞→`promote`；貼各步輸出與 `git status --porcelain` | **現況（凍結時現查）**：真帳本無 promoted PROP（無在役工件可退役），也無掌舵者指定的真實退役對象，本項**未達成（前置未成立）**，歸入 PRD §8.3 的 📎 驗收資料殘留（殘留＝缺在役工件與掌舵者指定的退役對象）；`capacity` 的候選（若有）僅為提議；達成時驗：`prop` 事件的 `action` 為 `retire`、兩欄位在本文且 digest 綁定、每筆 `dec` 的逐字稿座標可取回為人類發言、`events.dec_quote` 為 PASS |
| V26 | 出口 (d)：反證條件已檢查並留紀錄（主控執行） | `python tools/selfimproving.py measure --record-check`（`AUTOSDD_UNATTENDED` 未設）；`export --kind events --json` 取最後一筆 `report` 為 `check` 的 `mea.report` | rc 0；追加（或內容相同而不追加）一筆全域檢查報告：`falsified` 為 null、`missing` 含 `no-evaluable-window`（真帳本無可評估窗；NE 也留紀錄並寫缺什麼）；`fingerprint` 等於探針輸出的指紋；`check` 的 `events.mea` 為 PASS。出口 (d) 不依賴 (b)(c) |
| V27 | SOP、流程型 AC 與流程摩擦 | QA 逐項對照 PRD AC-SI-22-3 與 SOP〈P3 動詞〉〈提案者〉的條文語意（不只關鍵字在）；Developer 與 QA 的文字交卷 | SOP 條文語意與 PRD 一致；交卷含「流程摩擦」節，節內項目於 SCG-4 收尾前由主控入帳為 OBS 列，入帳後 V17 仍為綠 |
| V28 | 跨平台實跑與未驗標示 | Windows 真機上 AT-340-6-1（子行程輸出位元組）、AT-327-1-E-2（CRLF 逐字）、AT-323-1-E-2（日精度與 tz）的輸出；報告對 macOS 與 Linux 標「未驗」 | Windows 全綠；未實跑的平台在報告明列「未驗」及其依賴的替身；路徑比較兩側先 `realpath`（§5.1 (q)）；不以替身綠燈宣稱 POSIX 行為已驗 |
| V29 | 本檔的編譯與錨定檢查 | 以 `SddToPlaybookAdapter` 的 `_parse_contracts` 與 `_unmapped_at_ids` 對本檔計 AT 數與 `unmapped_at_ids`；`python -m pytest tools/tests/test_selfimproving_p3_meta.py -k AT_340_9_ -q -p no:xdist -o addopts=` | `unmapped_at_ids` 為空；解析出的 AT 數等於 §1 的 78；AT-340-9-1 與 AT-340-9-E-1 綠 |
| V30 | 出口彙整與四格歸類 | 對 PRD §8.1 P3 出口 (a)～(d) 逐項填：達成、未達成（缺什麼）、NE（缺什麼）及證據座標；依 §8.2 把 FR-SI-22～27 與各 AC 歸入 §8.3 四格 | 無「未分類」列；未達成項明列前置與下一步；報告不宣稱 P3 出口全數達成（現況只有 (a)(d) 可達成） |
| V31 | D12：DEF-200-568 的真 CLI 重現與修復證據（QA 親跑） | 於 tmp 複本（`AUTOSDD_SI_DIR` 指向 tmp 家目錄、測試金鑰）以真 CLI 餵 DEF-200-568 所列變形（核准帶 `reason` 或 `flags`；空或含換行 `reason` 的否決；含換行字串欄的 `obs-add`；含換行 `disposition` 的 `obs-close`）：先以修復 commit 之前的 `tools/lib/selfimproving/{consoleaudit,decwrite,obswrite,obsrows}.py`（`git show <修復 commit>^:<路徑>` 置於 tmp 並遮蔽）跑一次，再以修後版本跑；各貼 rc 與 `check --json` | 修前：rc 0 入帳而 `check` 變紅（成因重現）；修後：每份 rc 1、`codes(out)` 為 R136 的對應碼、事件帳本與 OBS 帳本位元組不變、`check` 仍綠；AT-340-10 系六個 AT 綠；缺陷帳本 DEF-200-568 為 `fixed@<sha>`（由主控收尾以真 sha 入帳，該 sha 可達）；P2b 側碼表與 R136 四碼一致（主控連動） |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（凍結前無勘誤；凍結後的訂正逐條寫於此，既有 AT 的 id 與判定碼名稱不改、不刪 AT，函式名改名的對照亦登記於此。）

### 勘誤一（Developer 棒 ⚖ 回報、SCG-4 一審 FAIL 與修復棒後的規格訂正；既有 AT 的 id 與判定碼名稱一字未改、一個 AT 也未刪）

- **事由**：headless Developer 棒（2026-10-25 04:59～06:21）交卷的 ⚖／勘誤建議 1～8 與主控親驗；SCG-4 一審（報告 `docs/06_quality/SCG4-REVIEW-SelfImproving-P3-20261024.md`；判定 FAIL，P1／P2／P3／P4＝0／3／3／9）的 D-01～D-06 與 P4-1～P4-9；修復棒（10:47～11:09）交卷；二審 PASS（P4 2：N-1、N-2）。本節只登記條文訂正，條文本體不回改（凍結檔以本節為準）；PRD v0.10 不動。
- **R134 同步站點補列（主控裁決；「本表外若有既有函式而紅，Developer 以 ⚖ 回報、主控裁決後補入本表」）**：
  1. **(g)** `tools/tests/test_selfimproving_events.py` 的 `consumed_keys`：刪 L02（最小 `mea.amend`，只帶 `prop`／`window`／`to`）——R113／R114 要求 `from`、`cause` 且 PROP 須已晉升，最小形自 P3 起不再是合法對照；L01、L03 與 V 列不變；`test_AT_108_4_E_7` 斷言不變。
  2. **(h)** `tools/tests/test_selfimproving_p2_meta.py::test_AT_240_13_E_1`：REQ-02 探針句「呼叫它們一律 rc 3」由「附加在 SOP 尾端」改為「插在 `### P2 動詞` 標題之後」（SOP 尾端自 P3 起是〈P3 動詞〉節）；斷言不變。
  3. **(i)** `_selfimproving_fixtures.py` 的 `DROP` 哨兵、`_p2_defaults` 的 `mea.*` 預設、`compose` 的 DROP 過濾（§5.2 要求的 `DROP`；QA P4-3）。
- **TCS 內部未定或漏註的訂正（Developer ⚖）**：
  4. **§5.4 MEA-NEG 表 N7**（`mea.close.result` 表外值）：補註「P1 既有 fold 對 `result` 表外值連帶 `TRANSITION-ILLEGAL`，`events.transitions` 亦 FAIL；AT-340-1-E-1 對 N7 只斷言 `events.mea` 的碼、不斷言 `events.transitions`」；**N12 只准放過 `events.transitions`，不放過 `events.mutated`**（QA P4-2）。
  5. **§5.2 CR 情境表**：補「手寫 promoted PROP 皆屬運轉 1，會撞 `BUDGET-PROPOSALS`（`max_proposals_per_run` 3）；CR 測試以 `set_params(max_proposals_per_run=50)` 隔離，預算判準與容量判準正交」。
  6. **§5.2 `cap_index(trail=k)`**：精確定義為「對記憶索引最後 5 個條目行各補 k 個尾端空白」。
  7. **AT-340-6-* 探針 `ne` 欄位名**：定為 `success.m1`、`success.m4`、`success.m5.main`、`success.m5.all`、`info.m2`、`info.m3`、`info.global_m1`（`--json` 輸出鍵；文字形態不變）。
  8. **R130 (c)／AT-340-4-E-1 `status` 的 rc 3 驗證鍵**：`status` 入口驗 `capacity` 四鍵加 `measure` 五鍵（`w_opp`、`w_evt`、`w_min`、`w_n`、`stop_after_bad`）不合法即 rc 3；`export` 不驗、`measure` 值回 `{"status":"NOT-EVALUABLE","reason":"params-invalid"}`（R130 (c) 四個 NE 理由之外的第五個）。
  9. **§5.6 `capability_problems`（測試自有判準）**：新增兩條——`ro` 檔相對 import 非 `ro` 檔即問題；任何檔含 `set_maturity` 呼叫即問題；閉包規則改為只判起點的直接 import（AT-340-4-E-2 每份注入副本恰回一筆）。
  10. **R132 兩態**：實作採可選 `meaplan.py` ⇒ `CAPABILITY` 48 鍵（36 ro／8 rw／2 net／2 exec）；V21 以 48 鍵態驗。**R114 (f) 後備**：實作未用，條文保留為允許、不強制。
- **SCG-4 一審後的行為訂正（D-04～D-06；修復棒落地、二審驗收）**：
  11. **R118 (c)／R128 (a)(c) 群鍵集合**：`churn` 與 `mea.prop_keys` 共用 `fold.confirmed_root_causes(f, sources, cutoff)`（只認 `attr.confirm` 的 root attr）；`fold.prop_root_causes` 與 `cooldown.py`、`props.py` 的 P1 語意不變；新 AT **AT-326-1-E-3**（未確認的 root attr 鍵不屬同群、兩個抖動碼皆不觸發）。
  12. **型別壞 `mea.*` 的消費端行為（R126 (a)、R130 (c)(e)、R122 (c)）**：`meacheck.field_problems`（缺鍵、型別、列舉三類致命碼，與 `check` 共用 `_field_codes`；`MEA-KEY-UNKNOWN` 不算）使 `build_ctx` 設 `ctx.bad`；`status`／`export --kind status` 的 `measure` 回 `{"status":"NOT-EVALUABLE","reason":"mea-events-invalid"}`（R130 (c) 的**第六個** NE 理由）；`export --kind proposals` 受影響 PROP 的 `window` 為 null（R130 (e) 補「`mea.*` 欄位不合 ⇒ null」，QA N-1 (a)）；探針 rc 0、M1／M5／反證條件印 `mea-events-invalid`；`measure` 與 `--record-check` 於 `build` 開頭 rc 1、碼沿 `check` 的 `MEA-KEY-MISSING`／`MEA-TYPE`／`MEA-ENUM`、零寫入（R122 (c) 補此情形，QA N-1 (b)）；`plan_amends` 遇 `ctx.bad` 回空清單（`attr-confirm`／`attr-reject` 仍 rc 0、不追加 amend）；新 AT **AT-340-5-E-3**、**AT-340-6-E-4**、**AT-340-2-E-6**。**設計註記（QA N-2）**：`ctx.bad` 是全帳本旗標——任一壞 `mea.*` 事件即使全部窗指標 NE、全部 PROP 的 `window` 為 null、`measure` 一律 rc 1；這是安全側取捨（不在不可評估的帳本上追加），與 P1 R32／R37「壞事件被忽略、其餘照常」刻意不同；逃生口寫在 SOP〈P3 動詞〉：壞事件尚未 commit 時直接修回、已 commit 時由主控處置（帳本 append-only，無更正路徑）。
  13. **R122 (d) 不可解析的定義**：「主檔不存在、非 UTF-8 可解碼（容 BOM／CRLF）、或無合法表頭（`parse_ledger().header_ok`，即 P0 `ledger.structure` 的 `HEADER-COLS` 判準）⇒ `OBS-LEDGER-UNAVAILABLE`、rc 1、零寫入；表頭在而零列＝合法空帳本（基線 `opp=[]`）」；新 AT **AT-340-2-E-5**。
- **§6.2 條文→AT 對帳缺口（QA P4-1，12 個存活突變）補 AT**：**AT-323-1-E-6**（R120 (a) 同刻優先序）、**AT-323-1-E-7**（R121 (e) root 型落定不產 amend）、**AT-323-1-E-8**（R121 (e) amend 的 `by`）、**AT-323-1-E-9**（R121 (b) 多候選 `cause`）、**AT-340-2-E-3**（R122 (b) `MEASURE-NOT-CONVERGING`；「零寫入」解為「零額外追加」——上限內已追加者留在帳本、超過上限起零追加）、**AT-340-2-E-4**（R122 (g) 多事件逐行位元組）、**AT-340-1-E-3**（R113 `missing` 排序去重）、**AT-340-1-E-4**（R113 `MEA-NOT-PROMOTED` 先後）、**AT-322-1-E-4**（R124 (b) NE 理由先後）、**AT-326-1-E-2**（R128 (b)）、**AT-326-2-E-2**（R128 (d)）、**AT-327-2-E-2**（R129 (f)）、**AT-340-5-E-2**（R130 (e)）。各新 AT 的測試函式名含錨定底線形，所在檔：`test_selfimproving_measure.py`（AT-323-1-E-6～E-9）、`test_selfimproving_measure_verb.py`（AT-340-1-E-3／E-4、AT-340-2-E-3～E-6、AT-340-5-E-2／E-3）、`test_selfimproving_measure_probe.py`（AT-322-1-E-4、AT-340-6-E-4）、`test_selfimproving_capacity_retire.py`（AT-326-1-E-2／E-3、AT-326-2-E-2、AT-327-2-E-2）；判定指令與既有 AT 同形（`-k <錨定名>_ -q -p no:xdist -o addopts=`）；二審以突變重放 R1～R18 逐一驗證各 AT 殺掉所述突變。
- **測試寫法訂正（D-01～D-03，根層鎖）**：E501 以東亞寬度折行、`tools/tests/` 過長行維持 136；DEF-EDGE「ID 欄含空白」無效列以夾具 `d(99)` 執行期組出、不寫字面 DEF 編號；AT-340-8-1 對 `test_AT_140_1_E_1` 的斷言改以 `ast.get_source_segment` 取函式本身、不對整份活文件做缺席斷言。
- **SOP 訂正**：〈提案者隔離〉「只由主控與 QA 讀取」→「只對掌舵者與量測者（主控、QA）呈現」（PRD AC-SI-22-3；QA P4-7）；`measure` 列 rc 1 清單補 `MEASURE-NOT-CONVERGING`、`EVENT-BYTES-OVER`、`LEDGER-TORN` 並註明欄位不合時沿用 `check` 的碼且零寫入（QA P4-8）；逃生口一句（第 12 項）。
- **理論洞登記（不改碼）**：`mea.py` 依 PROP 號排序用字串序（破千時與 `export` 數字序不符，QA P4-5）；`meawrite.measure` 收斂上限在取鎖前算（並行晉升偽 `MEASURE-NOT-CONVERGING`，QA P4-6）；`meaplan.py` 頂層函式間單空行（QA P4-9）；`meaplan.py` 拆出而 `mea.py`＋`meaplan.py` 未達 ⚖15 的 380 條件（無害，QA P4-4）。
- **事實記錄（不改規格）**：Developer 棒工作樹內曾見 `ref.obs` FAIL，成因為並行 P2b 棒測試檔內「`OBS-SI-` 接 000／999」形的壞號字面（已改執行期組字串），與本鍵無關；`run_root_unittests.py` 於 `tools/tests` 檔數下限與 tools/lib 掃描檔數上界兩處棘輪早退／紅、護欄層行數棘輪與 shrink-only 分桶（`prose`、`guard_self`）成長，皆為收尾單人窗口重釘（NFR-P3-8），不是缺陷；Developer 閘門 (6) 的官方 runner 早退而未退而跑 pytest 子集，使三個真紅遲至 SCG-4 才現形（OBS-SI-298）。
- **數量**：AT 由 78 條增為 96 條（正控 35 不變、負控 43→61）；各測試檔：measure 21→25、measure_verb 10→18、measure_probe 12→14、capacity_retire 17→21、p3_meta 10、capability +2、console_obs +6；`test_AT_340_9_1` 以 `EXTRA_ATS` 同時容許本檔為 78 與 96 兩態（兩態皆綠、95 與 97 皆紅，二審驗證）。
- **凍結紀錄**：Stage-2 原凍結 `sha256:f7150d4a54e9439fd26585753d5b42f13a4dcb2d03eebe9a17d625ea8a1af170` 保留為歷史；本次訂正使檔案內容再度改變，修訂後的 digest 由主控以 `spec-refreeze` 重記，不以手改狀態檔代替。PRD 與研究方法 SOP 凍結摘要未動（兩份上位文件本次皆未改）。
