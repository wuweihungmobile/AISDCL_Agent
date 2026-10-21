# Test Contract Specification — SelfImproving P2（K=1 人工閘的 DEC 驗證與冷卻、沙盒套用、held-out 凍結與三態驗證、晉升與回滾、Console 載體的根層半、`apply_lock` 刪除待決修法、P1 殘留與資料面小項、可重跑檢查）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（PRD v0.10 與研究方法 SOP 於 Stage-1 凍結）的單一 Feature（P2 階段）；單一 FSM 功能鍵 `monorepo-si-p2-gate-apply`（`spec-frozen --doc` 指向本檔）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P2-20261021.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-003 |
| **Feature 名稱** | SelfImproving P2：K=1 人工閘（`decide` 自逐字稿抽取並驗證掌舵者引言、`card --issue`、拒絕紀錄與同型冷卻）、套用與驗證（`heldout-freeze`、`sandbox`、`verify`、三態判定、證據逐字入帳）、人工晉升與回滾（`promote`、`rollback`、SUSPENDED 與 `resume`）、Console 載體的根層半（`decide --carrier console`、`obs-add`、`obs-close`、`check` 與 `status` 與 `export` 的擴充）、事件詞彙與欄位表與狀態機的 P2 定稿、能力登記第四類 `exec`、`tools/lib/apply_lock.py` 的 Windows 刪除待決修法（DEF-200-559）、P1 殘留（來源表 host 僅限 ASCII、AT 序號與 `-k` 錨定規則）與資料面小項（`ref.carrier_families` 存在性判、`scan` 資訊型草稿列）、Operations SOP〈P2 動詞〉定稿 |
| **User Story** | US-201～US-206 |
| **建立日期** | 2026-10-21 |
| **QA 負責人** | SelfImproving P2 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝Developer 棒加主控〔收尾、帳本編修、真實運轉、重釘儀式〕，三方不同） |
| **FSM 功能鍵** | `monorepo-si-p2-gate-apply`（PRD §9.6 P2 列；P2b 的 AgentConsole 三層屬鍵 `agentconsole-si-decide` 與另一份 TCS，不在本檔） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（monorepo 根層；上位文件＝`docs/01_requirements/SelfImproving_PRD.md`〔v0.10〕與 `docs/05_development/SelfImproving_Research_Methodology_SOP.md`，已於 Stage-1 凍結）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。**凍結檔不得再改**：本檔發現 PRD 需修訂之處，一律寫在 §7 的 ⚖ 清單與交卷單，走掌舵者 T1／SPEC_REGRESSION_CHECK；本檔不自行改 PRD，凡 PRD 未定、本檔為使其可測而補定義者，一律標「本檔類推」並列入 §7.1。**本檔另有三處以本檔作者現查的實測事實為據、與 PRD 字面或任務書前提不一致者（沙盒內 `git apply` 的行尾轉換、`tarfile` 過濾器對絕對路徑成員的行為與其可用性、`status` 與 `export` 對家目錄的讀取衝突），皆列入 §7.1 並附實測輸出**。

### FRD-lite

**現況與變更（Before／After；brownfield）**

- Before：(1) P0 與 P1 已完成：`tools/selfimproving.py` 有 13 個動詞（`check`、`status`、`scan`、`card`、`export`、`run-open`、`run-close`、`attr`、`attr-confirm`、`attr-reject`、`prop-new`、`prop-revise`、`research`），`check` 共 28 項（P0 的 21 項加 P1 的 7 項），事件帳本的 `KINDS` 為 19 個而其中只有 `run.open`、`run.close`、`research.scan`、`research.skip`、`attr`、`attr.confirm`、`attr.reject`、`prop` 八種有完整欄位表（其餘只有被消費鍵的型別檢查），`params.json` 為 28 鍵，能力登記 `CAPABILITY` 為 24 鍵（19 `ro`／3 `rw`／2 `net`）；(2) `fold` 只認 P1 的轉移：`approve`／`reject`／`return`（僅 `proposed` 與 `verified` 且 FAIL）／`ack-handoff`／`unblock`／`promote`（僅 verdict 為 PASS，或 NE 且帶 `unverified_ack`）／`rollback`、`app.sandbox` 只收 `approved`、`app.verify` 只收 `sandboxed`，沒有複驗邊、沒有 `Prop` 的 `reasons`／`rollback_ok`／`touched_ok`；(3) 不存在：逐字稿載體與決定語法的解析、`decide`、冷卻的 `prop-new` 拒收、`heldout-freeze`、沙盒、子行程出口、驗證與三態判定、`promote`／`rollback`、Console 稽核檔與 HMAC、`obs-add`／`obs-close`；(4) `tools/lib/apply_lock.py` 三處（`_try_acquire`、`_reap_if_stale` 內的 `unlink`、釋放時的 `unlink`）只認 `FileExistsError`／`FileNotFoundError`，Windows 的刪除待決與共享違規（`PermissionError`，errno 13）直接穿出（DEF-200-559，OBS-SI-211 擴至三站點）；(5) P1 殘留：來源表驗證端不判 host 的非 ASCII 與 IDNA 形態（`https://１２７.0.0.1/x` 通過 `validate_table`），P1 TCS 的 AC-130-2 其 AT 序號已用到 9 而規則「每個 AC 內序號不超過 9」使它不能再加 AT；`attr --type link` 的 `--reopens` 只收已結列（P1 R45、R48 (b)），處置首詞為 `deferred`（必附再開症狀、本就預期被再開）的列被 `REOPENS-NOT-CLOSED` 拒收（主控 2026-10-21 裁決改採「已結列加 `deferred` 列」，§7.1 ⚖ 39）；(6) `refs.obs_findings` 對 `(ATT|PROP|DEC|APP|MEA|RUN)-SI-<數字>` 的任何提及恆印 `CARRIER-NOT-ESTABLISHED` 而不查存在（OBS-SI-217）；`scan` 的草稿列一律 `bug`／`P3`／`open`，含只是計數的 commit 觸及列，且來源行一律印「讀到 N 筆」（OBS-SI-218）；`export` 的 observations 項沒有 `buckets[]`（OBS-SI-237 另註：`rows.path_set` 先 `casefold`，不可餵給大小寫敏感的歸桶）；(7) Operations SOP 的〈P2 動詞（待補）〉節空白。
- After：新增 16 支套件模組（10 `ro`、4 `rw`、2 `exec`；PRD §9.1〈C4 套件檔案表（P2）〉）與 8 個動詞（共 21 個；`card` 另有 `--issue`）；事件詞彙增為 21 個（加 `obs.add`、`obs.close`）、九種 P2 事件（`card`、`dec`、`heldout.freeze`、`app.sandbox`、`app.verify`、`app.promote`、`app.rollback`、`obs.add`、`obs.close`）有完整欄位表與條件必備規則、帳本不變式與 P2 狀態機（複驗邊、退回前提、晉升前提）進 `events.transitions`；`check` 在 28 項之後追加 4 項（`events.dec_quote`、`events.dec_console`、`events.verdict`、`obs.console_audit`）共 32 項，P0 的 21 項與 P1 的 7 項原樣；`params.json` 加 `probe_timeout_seconds`（600）與 `verify_runs_max`（2）共 30 鍵；能力登記增第四類 `exec`（40 鍵：29／7／2／2）；`apply_lock` 三站點對 `PermissionError` 視同忙碌或可重試、逾時改拋原始例外；來源表 host 限 ASCII；`attr --type link` 的 `--reopens` 目標＝已結列加處置首詞為 `deferred` 的 OBS 列（R110）；本檔〈AC 編號規則〉明寫兩位序號與 `-k` 錨定規則並以可重跑檢查釘住；`ref.carrier_families` 對 ATT／PROP／RUN 三族做指標面的存在性判；`scan` 的資訊型草稿列改 `process`／`P4`／`decided：僅計數`、無內容解析的來源行改「計 N 筆（未解析內容）」；`export` 的 observations 項加 `buckets[]`、`status` 加 `console_pending`；SOP〈P2 動詞〉定稿。
- **本檔不含**：P3 的量測與退役（`capacity`、`mea.*`、M1～M5）、P2b 的 AgentConsole 三層（Bridge、backend、frontend、Flyway）、P1b 的 Console 唯讀鏡像；它們各有自己的 TCS。

**AC 編號規則**（本節回答「PRD 的 AC 與本檔的 AC 怎麼對應」；體例逐字沿 P1 TCS 的〈AC 編號規則〉，百位改 `2`）：

1. **編譯文法**：ADR-XPLAT-016 §8.1 規定 AC 文法為 `AC-[\d\-]+`、AT 文法為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC、§1 映射列的 AC 須等於 AT 前兩段推得者。PRD 的 `AC-SI-NN-Y` 含字母、不合此文法，故本檔採雙名：§1、§2 等機器可讀位置一律用合文法的數字 id，人讀處（FRD-lite 表的 AC 欄、§6）同時寫出 PRD 全名。
2. **對映規則**：階段前綴＝百位的 `2`（PRD §5〈編號注意〉的 `P2` 前綴）。PRD 的 AC：`AC-SI-NN-Y`＝本檔 `AC-2NN-Y`（例：PRD `AC-SI-12-4`＝本檔 `AC-212-4`、`AC-SI-35-1`＝本檔 `AC-235-1`、`AC-SI-30-2`＝本檔 `AC-230-2`）。本檔自增 AC：FR 號位自 40 起編，名為 `AC-240-1` 起；其 PRD 階段前綴形為 `AC-P2-040-1`，來源逐條標示於 FRD-lite 表（PRD 明文者標座標；PRD 只給機制未給編號者標「本檔自增」；PRD 未定而本檔為使其可測補定義者標「本檔類推」）。與 P1 的 `AC-1NN-Y`、`AC-140-x`～`AC-145-x` 不衝突（百位不同）。
3. **與任務書的差異**：任務書寫「本檔自增 AC 自 `AC-240-1` 起」，與本規則一致，無差異。
4. **AT 命名與序號規則（P1 TCS 勘誤四的殘留收口；AC-240-9）**：`AT-<AC 數字 id>-<序>`；負控／邊界 `AT-<AC 數字 id>-E-<序>`；測試函式名為 `test_<AT 底線形>_<slug>`（`AT-212-4-E-1`→`AT_212_4_E_1`，slug 為非空的小寫英數底線字串）。**序號用到 9 之後改開兩位序號**：同一 AC 的 AT 序號超過 9 時，第 10 個起寫作 `AT-<AC>-E-10`、`AT-<AC>-E-11`……（不另立 AC、不改既有 AT 的 id）。**判定指令的 `-k` 一律用「錨定名」**：`-k` 的值＝AT 底線形接一個結尾底線（例 `-k AT_212_4_E_1_`），因為 pytest 的 `-k` 是不分大小寫的子字串比對，`AT_212_4_E_1`（無結尾底線）會同時收到 `AT_212_4_E_10_…`；加結尾底線後只有函式名在底線形之後緊接底線者才命中。本檔全部 AT 的判定指令皆為錨定形；P1 TCS 的既有 AT 判定指令不變（P1 沒有兩位序號，不受影響）。可重跑檢查＝AT-240-9-1、AT-240-9-E-1（§2）：對 MT 檔以 `pytest --collect-only` 收集全部 P2 測試檔，對本檔每個 AT 的 `-k` 值各算子字串命中數，恰為 1。
5. **AC 數**：PRD 的 AC 35 個（FR-SI-12 四個、13 三個、15 四個、16 三個、17 兩個、18 兩個、19 三個、20 四個、21 兩個、AC-SI-30-2 一個、FR-SI-33 兩個、FR-SI-35 五個）加本檔自增 15 個（`AC-240-1`～`AC-240-15`；其中 `AC-240-15` 來自主控 2026-10-21 對 ⚖ 39 的裁決），合計 50 個。PRD 的 AC-SI-33-1／33-2 與 AC-SI-35-4 在 AgentConsole 側另有 backend 半（RBAC、白名單、DB 稽核表），本檔只承擔根層半，逐條標示於 FRD-lite 表。

**P2 交付物**（D1～D16）

| 編號 | 交付物 | 路徑（相對 monorepo 根） | 製作者 | 主要驗證 |
|------|--------|--------------------------|--------|----------|
| D1 | 事件詞彙與九種 kind 欄位表、`fold` 狀態機補強、OBS 標記鍵 | `tools/lib/selfimproving/{events,fold,rows}.py`（改；`events.py` 逼近 400 斷言行時先拆 `evspec`〔ro〕、不調 tier） | Developer | AC-240-1、AC-240-2 的 AT |
| D2 | DEC 驗證與 `decide`（逐字稿載體）、`card --issue` | `tools/lib/selfimproving/{transcript,decgrammar,decverify}.py`（新，ro）、`decwrite.py`（新，rw）、`card.py`（改）；`status.py`（改：逐字稿目錄規則搬進 `transcript.py`、`status` 改引用） | Developer | AC-212、AC-213-1、AC-240-6 的 AT |
| D3 | 同型冷卻 | `tools/lib/selfimproving/cooldown.py`（新，ro）、`props.py`（改：`prop-new` 前置檢查呼叫它） | Developer | AC-213-2、AC-213-3 的 AT |
| D4 | held-out 與 manifest、`heldout-freeze` | `tools/lib/selfimproving/{heldout,manifest}.py`（新，ro）、`decwrite.py` | Developer | AC-220-1、AC-220-2 的 AT |
| D5 | 沙盒 | `tools/lib/selfimproving/sandbox.py`（新，rw）、`git.py`（改：`Git.run` 加選用 `timeout`，預設仍 60 秒） | Developer | AC-215 系列 AT |
| D6 | 子行程出口、驗證、三態判定、證據入帳 | `tools/lib/selfimproving/{runner,verify}.py`（新，exec）、`verdict.py`（新，ro）、`propfiles.py`（改：`verifyK.json` 落地） | Developer | AC-217-1、AC-218-2、AC-219、AC-220-4、AC-221-1 的 AT |
| D7 | 晉升、回滾、SUSPENDED 與 `resume` | `tools/lib/selfimproving/promote.py`（新，rw） | Developer | AC-216、AC-240-7、AC-217-2、AC-220-3 的 AT |
| D8 | Console 載體的根層半 | `tools/lib/selfimproving/{consoleaudit,obsrows,decheck}.py`（新，ro）、`obswrite.py`（新，rw） | Developer | AC-233、AC-235 的 AT |
| D9 | `check` 追加四項與 `CHECK_RULES_REV`、`status`／`export`／`scan`／`refs`／`sources` 的擴充 | `tools/lib/selfimproving/{check,evcheck,params,status,export,scan,refs,sources}.py`（改） | Developer | AC-240-3、AC-240-10、AC-240-11、AC-240-12、AC-230-2 的 AT |
| D10 | 能力登記第四類 `exec` 與 40 鍵計數 | `tools/tests/test_selfimproving_capability.py`（改） | Developer | AC-240-5 的 AT |
| D11 | `apply_lock` 三站點修法（DEF-200-559；OBS-SI-210、211） | `tools/lib/apply_lock.py`（改）、`tools/tests/test_apply_lock.py`（改：增補替身測試） | Developer | AC-240-8 的 AT |
| D12 | P1 殘留與裁決收口：來源表 host 僅限 ASCII、AT 序號與 `-k` 錨定規則、`attr --type link` 的 `--reopens` 目標擴為已結列加 `deferred` 列（⚖ 39） | `tools/lib/selfimproving/sources.py`、`refs.py`（新增 `reopenable_rows`）、`writeverbs.py`（`attr` 改用它）（皆改）、本檔〈AC 編號規則〉第 4 點 | Developer；SA（條文） | AC-230-2、AC-240-9、AC-240-15 的 AT |
| D13 | 協定目錄：`params.json` 加兩鍵 | `docs/06_quality/SelfImproving_Protocol/params.json`（改；主控與 `PARAM_SPECS` 同 commit） | 主控 | AC-240-4 的 AT |
| D14 | 夾具升級與既有測試同步（零退化） | `tools/tests/_selfimproving_fixtures.py`（改）、`tools/tests/_selfimproving_p2_fixtures.py`（新）、P1 測試檔的同步站點（R107） | Developer | AC-240-1、AC-240-14 的 AT |
| D15 | Operations SOP〈P2 動詞〉定稿與流程型條文 | `docs/05_development/SelfImproving_Operations_SOP.md` | Developer（文件作者） | AC-218-1、AC-215-3、AC-221-2、AC-240-13 的 AT |
| D16 | 入口 | `tools/selfimproving.py`（改：八個新動詞與 `card --issue`；除 `ro` 以外的模組一律在 handler 內延遲 import） | Developer | AC-240-14 的 AT；全部動詞 AT |

**提交順序與責任**

- 實作分棒由主控依持有面切（根 `CLAUDE.md` 鐵律七檢查表）；依賴序為 D14（夾具升級與既有測試同步；須先於 D1 的欄位表落地，否則 P1 夾具的最小欄位事件被新欄位表判不合規，見 R107）→ D1（事件詞彙與折疊）→ D13（`params.json` 兩鍵與 `PARAM_SPECS` 同 commit）→ D2、D3（DEC 與冷卻）→ D4、D5、D6（held-out、沙盒、驗證）→ D7（晉升與回滾）→ D8（Console 載體）→ D9、D12（check／status／export／scan／refs／sources 擴充與 `attr link` 的 reopens 目標）→ D10、D11（能力登記、`apply_lock`；D11 與其他棒無持有面交集，可並行）→ D16（入口，隨各動詞同 commit）→ D15。每支程式完成立即跑該區 AT，不累積（根 `CLAUDE.md` 共通紀律第 2 條）。
- **鎖的持有面不得拆給並行包**（鐵律七）：`events.py` 的欄位表、`fold.py` 的轉移表與 `check` 的四個追加項是同一把「事件重放」鎖，D1 與 D9 的 `evcheck`／`decheck` 接線由同一棒做；`apply_lock.py` 屬全部寫入動詞共用的鎖，其修法與其替身測試同棒。
- 真帳本與真事件帳本只由主控寫（PRD C1「他人只讀」）：Developer 棒不得碰真 OBS 帳本、真事件帳本與真 `SelfImproving_Proposals/`；AT 一律在 tmp 目錄的合成 repo 內進行，逐字稿以合成檔放在 tmp 內的 `CLAUDE_CONFIG_DIR` 之下（R77），不讀真逐字稿。P2 出口 (a)(b)(c)(d)(e)(g) 的真實運轉與 P1 出口 (b) 的補證由主控於實作完成後執行，列於〈SCG-4 通過標準〉的實跑檢核 V8、V9、V10、V15（其中復發連結與出口 (c) 兩處的前提缺口見 §7.1 ⚖ 39、⚖ 40）。
- 重釘儀式（護欄層行數棘輪、`tools/tests` 檔數下限與 E501 棘輪、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE` 具名一次性例外〔名冊上限的上修須可見；PRD §9.0 估 P2 新增 `tools/` 約 4,300 斷言行〕）由主控單人窗口於同一個 commit 收齊，實作者不碰鎖檔（NFR-P2-8）。OBS-SI-213 的決定（P2 重釘時評估接鏈列允許 OBS-SI ID）屬重釘儀式的主控項，不入 AT。

**〈P2 行為規則〉**（R68～R110；各 AT 以 R 編號引用；判定碼見其後的〈判定碼表〉與〈P2 拒收碼表〉。P0 的 R1～R26 與 P1 的 R27～R67 在其範圍內不變；P2 對它們的重定與擴充見 R72（`KINDS`）、R75（`fold` 狀態機）、R98（`check` 的項數與碼）、R99（`status` 與 `export` 的鍵）、R101（R43 的 host 判準）、R103（R59 的草稿列與來源行）、R104（R36 (h)）、R106（R46 的鍵數）、R107（既有測試的同步站點）、R110（R48 (b) 的 `--reopens` 目標；R45 不變））

*A. 介面、rc 與輸出（P2 動詞；PRD §9.3、§7.2、§7.1；旗標的細部為本檔類推，§7.1 ⚖ 21）*

- **R68 21 個動詞與旗標**：`python tools/selfimproving.py <verb> [旗標]`。P1 的 13 個動詞（`check`、`status`、`scan`、`card`、`export`、`run-open`、`run-close`、`attr`、`attr-confirm`、`attr-reject`、`prop-new`、`prop-revise`、`research`）語意除本檔明文處外不變，加下表 8 個新動詞；`card` 另增旗標 `--issue [--by <標籤>]`。凡 P1 表與本表未列的動詞名（含 PRD 列為 P3 的 `capacity`）一律 rc 3、stdout 空、stderr 至少一行；`--help` 的頂層 usage 列出 21 個動詞。共通旗標 `--repo DIR`、`--json` 沿 P1 R27。**rc 通則**沿 P1 R27：寫入動詞 0＝已寫、1＝拒收（前置檢查失敗或取鎖逾時；未寫、印可貼入的 OBS 草稿列）、3＝用法或輸入錯誤（含家目錄不可寫）；`sandbox` 的 rc 0 涵蓋 `applied=false`；`verify` 的 rc 0 不論 verdict（主控須讀 verdict、不讀 rc，根 `CLAUDE.md` 鐵律四）；唯讀動詞 0／3。

| 動詞 | 旗標（＊必備） | 事件 kind | 規則 |
|------|----------------|-----------|------|
| `decide`（逐字稿載體） | 位置參數 `<PROP-SI-NNN｜RUN-SI-NNN>`＊ `--kind {approve,reject,return,promote,decline-promote,rollback,unblock,resume,ack-handoff}`＊ `--sid <UUID>`＊ `--line <N>`＊ `--reason-class <c>`（`reject`、`decline-promote`、`return` 必給）`--by <標籤>`（預設 `main`） | `dec` | R77～R81 |
| `decide`（Console 載體） | 位置參數＊ `--carrier console`＊ `--audit-ref <UUID>`＊ `--by`（此載體不收 `--kind`、`--sid`、`--line`、`--reason-class`，給了＝rc 3） | `dec`（`carrier=console`） | R94、R95 |
| `heldout-freeze` | `<PROP>`＊ `--from <目錄>`＊ `--by <標籤>`＊ | `heldout.freeze` | R83、R84 |
| `sandbox` | `<PROP>`＊ `--memory-dir <目錄>`（M 類必給）`--by` | `app.sandbox` | R85、R86 |
| `verify` | `<PROP>`＊ `--mutation <檔>` `--by` `--json` | `app.verify` | R87～R90 |
| `promote` | `<PROP>`＊ `--memory-dir`（M 類必給）`--by` | `app.promote` | R91 |
| `rollback` | `<PROP>`＊ `--memory-dir`（M 類必給）`--by` | `app.rollback` | R92 |
| `obs-add` | `--carrier console --audit-ref <UUID>` 或 `--dry-run --body-file <路徑或 -> `（兩者互斥、必其一）`--by` | `obs.add`（`--dry-run` 不寫） | R96 |
| `obs-close` | `--carrier console`＊ `--audit-ref <UUID>`＊ `--by` | `obs.close` | R97 |

- **R69 成功輸出文法與 `--json`**：沿 P1 R28 (a)：成功＝單行 `ok <kind> seq=<N>`、指派了 ID 者接 ` id=<ID>`、再接各動詞的附加欄（值不含空白；布林印 `true`／`false`、空值印 `null`、清單以逗號連接而空清單印 `-`）；`--json`＝單一 JSON 物件加換行，鍵序為 `ok`、`kind`、`seq`、`id`（無則 `null`）、其後附加欄。附加欄：`decide`＝`prop=<PROP>`（`resume` 為 `run=<RUN>`）、`dkind`、`digest8`（`resume` 無此欄）；`heldout-freeze`＝`prop`、`n`、`digest8`；`sandbox`＝`applied`、`touched_ok`、`rollback_ok`、`fail_code`；`verify`＝`verdict`、`probes_n`、`reasons`（另 `--json` 加 `baseline_red`、`patched_green`、`mutated_red`、`carrier_proof`）；`promote`＝`prop`、`unverified_ack`、`head_sha`；`rollback`＝`prop`；`obs-add`／`obs-close`＝`audit_ref`（`id` 為 CLI 配的或被改的 `OBS-SI-NNN`）。**`card --issue` 的例外**：stdout 與不帶 `--issue` 的 `card` 逐位元組相同（卡面文字須原樣貼給掌舵者），其單行 `ok card seq=<N> prop=<PROP> digest8=<8 碼>` 走 stderr；`--json` 時 stdout 為 P1 `card --json` 的物件加末鍵 `issued`（`{"seq": N, "card_sha256": "<sha256:…>"}`）。拒收（rc 1）與用法錯誤（rc 3）的輸出文法逐字沿 P1 R28 (b)(c)(d)。**`sandbox` 與 `obs-add`／`obs-close` 與 `verify` 的失敗側另印可貼入的 OBS 草稿列**（NFR-SI-09-3）：`sandbox` 於 `applied=false` 時、`verify` 於 verdict 為 NE 或 FAIL 時，stdout 末尾接 `obs-draft:` 與恰一行草稿列（草稿列沿 P1 R28 (d)，症狀以 `si <verb>` 起頭並含碼）。
- **R70 無人值守與家目錄（P2）**：環境變數 `AUTOSDD_UNATTENDED` 存在且值非空（含字面 `0`）時，`decide`、`promote`、`rollback`、`obs-add`、`obs-close`、`heldout-freeze`、`sandbox`、`verify`、`card --issue` 一律 rc 1、碼 `UNATTENDED-REFUSED`、**零寫入**（事件帳本位元組不變、`SelfImproving_Proposals/`、家目錄與 OBS 帳本皆無新檔或變動）；`obs-add --dry-run` 不寫任何東西、不受此限；P1 的寫入動詞（`run-open`、`run-close`、`attr` 系、`prop-new`、`prop-revise`、`research`）照常。`UNATTENDED-REFUSED` 於全部其他前置檢查之前判（先於 `PROP-NOT-FOUND` 等）。**家目錄**（沿 P1 R29）：P2 新增 `<si>/heldout/<PROP>/`、`<si>/sandbox/<PROP>/`、`<si>/console_audit/<audit_ref>.json`（後者由 Bridge 寫、CLI 讀；CLI 絕不寫它）；`sandbox`、`verify`、`heldout-freeze`、`promote`（M 類以外不需）、`rollback` 需要家目錄可寫（沿 R29 的探測，不可寫＝rc 3、`HOME-UNWRITABLE`、不退回暫存目錄）；唯讀動詞與 `obs-add --dry-run` 不建立、不要求家目錄；**`export` 不讀家目錄下任何檔**（沿 P1 R61，含 `console_audit/`）；`status` 只讀 `console_audit/` 的目錄清單與各 `<uuid>.json` 的 `kind` 欄（只取該欄、不輸出其餘內容；不讀 `heldout/`、`sandbox/`、`research/`，R99）。
- **R71 P2 拒收碼**：見〈P2 拒收碼表〉。拒收一律零殘留（沿 P1 R28 (b)）：除了 `sandbox` 與 `verify` 在**已寫事件**的路徑上留下的沙盒樹與 `verifyK.json`（那是成功寫入的產物）以外，任何 rc 1 的呼叫其事件帳本位元組、OBS 帳本位元組、`SelfImproving_Proposals/`、主工作樹與記憶目錄皆不變，家目錄除（已釋放的）鎖檔外無新檔；`sandbox` 與 `heldout-freeze` 在 rc 1 時不得留下半成品目錄（`<si>/sandbox/<PROP>/`、`<si>/heldout/<PROP>/` 皆不存在，若呼叫前已存在則維持呼叫前的狀態：`sandbox` 先在暫名目錄組裝完成才換入，`heldout-freeze` 同）。

*B. 事件詞彙、欄位表、帳本不變式與狀態機（PRD §9.2、§5.1.2、§9.7 #73～#79；表內欄位值域中標「本檔類推」者見 §7.1）*

- **R72 詞彙與九種 P2 事件的欄位表**：`events.KINDS` 為 21 個（P1 的 19 個加 `obs.add`、`obs.close`），`EVENT-KIND` 的 detail 字樣改為「不在 21 個詞彙內」。九種 P2 kind 的必備鍵（共通鍵 `seq`、`t`、`kind`、`by` 之外）、型別與值域如下，表外鍵＝`EVENT-KEY-UNKNOWN`、缺必備鍵＝`EVENT-KEY-MISSING`、型別或值域不合＝`EVENT-TYPE`（沿 P1 R37，單事件判準 `events.validate`；`mea.*` 仍只有被消費鍵的型別檢查，屬 P3）：

| kind | 必備鍵與型別 | 條件必備與值域 |
|------|--------------|----------------|
| `card` | `prop`（`PROP-SI-<≥3 位數>`）、`rev`（整數 ≥1）、`digest`（`sha256:` 接 64 位小寫 hex）、`card_sha256`（同形） | 無 |
| `dec` | `id`（`DEC-SI-<≥3 位數>`）、`dkind`（九值之一）、`decider`、`decided_at`（帶 offset、秒精度的 ISO 8601，沿 `valid_t`） | 對象：`prop`（除 `resume` 外必備）或 `run`（僅 `resume`，`RUN-SI-<≥3 位數>`），兩者恰一；`digest` 於 `approve`、`reject`、`return`、`promote`、`decline-promote`、`ack-handoff` 必備、其餘不得有；`reason`（非空單行字串）於 `reject`、`decline-promote`、`return`、`rollback`、`resume` 必備、其餘不得有；`reason_class`（七值：證據不足、風險過高、工件類別錯、已被涵蓋、範圍外、卡面不清、未說明）於 `reject`、`decline-promote`、`return` 必備、其餘不得有；`flags`（選用，字串陣列，元素只准 `unverified_ack`，且只准出現在 `promote`）；`carrier`（選用；`transcript` 或 `console`；缺＝`transcript`）。**`transcript` 載體**另必備 `quote`（非空單行字串）、`sid`（UUID 正規形）、`line`（整數 ≥1），且除 `resume` 外必備 `card_seq`（整數 ≥1 且小於本筆 `seq`）；`decider` 恆為字面「掌舵者」。**`console` 載體**另必備 `audit_ref`（UUID）、`audit_sha256`（`sha256:` 接 64 位 hex）、`key_id`（8 位小寫 hex），不得有 `quote`、`sid`、`line`、`card_seq`；`decider` 須合 `^[A-Za-z0-9_.-]{1,64}$` |
| `heldout.freeze` | `prop`、`digest`（`sha256:` 接 64 位 hex）、`n`（整數 ≥1）、`frozen_by`（標籤，沿 `valid_by`） | 無 |
| `app.sandbox` | `id`（`APP-SI-<≥3 位數>`）、`prop`、`rev`、`base`（40 位 hex）、`sandbox_sha256`（`sha256:` 接 64 位 hex 或 `null`）、`applied`（布林）、`touched_ok`（布林或 `null`）、`rollback_ok`（布林或 `null`）、`fail_code`（`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT` 或 `null`） | `applied` 為 `true` ⇒ `touched_ok` 與 `rollback_ok` 皆為布林、`fail_code` 為 `null`、`sandbox_sha256` 非 `null`；`applied` 為 `false` ⇒ `touched_ok` 與 `rollback_ok` 皆為 `null`；`fail_code` 為 `SANDBOX-EXPORT-FAILED` ⇔ `sandbox_sha256` 為 `null`（匯出失敗沒有樹可雜湊）；`fail_code` 為 `SANDBOX-APPLY-TIMEOUT` ⇒ `applied` 為 `false` 且 `sandbox_sha256` 非 `null`（patch 套不上而非逾時＝`fail_code` 為 `null` 且 `applied` 為 `false`） |
| `app.verify` | `id`、`prop`、`rev`、`verdict`（`PASS`、`FAIL`、`NE`）、`baseline_red`／`patched_green`／`mutated_red`／`carrier_proof`（各為布林或 `null`）、`probes_n`（整數 ≥0）、`verify_sha256`（`sha256:` 接 64 位 hex 或 `null`）、`heldout_digest`（同形或 `null`）、`reasons`（字串陣列，元素屬下列 16 碼） | `reasons` 的 16 個碼：`SANDBOX-NOT-APPLIED`、`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT`、`TOUCHED-SUPERSET`、`ROLLBACK-DRYRUN-FAILED`、`NO-PROBES`、`CARRIER-PROOF-FAILED`、`HELDOUT-DIGEST-MISMATCH`、`HELDOUT-TOO-SMALL`、`HELDOUT-EXPOSED`、`EXPOSURE-UNKNOWN`、`PROBE-TIMEOUT`、`BASELINE-NOT-RED`、`PATCHED-NOT-GREEN`、`MUTATION-NOT-RED`、`MUTATION-ABSENT`；`reasons` 為空陣列 ⇔ `verdict` 為 `PASS`；`probes_n` 為 0 ⇔ `verify_sha256` 為 `null` |
| `app.promote` | `id`、`prop`、`rev`、`head_sha`（40 位 hex）、`pre_sha256`、`post_sha256`（皆 `sha256:` 接 64 位 hex）、`unverified_ack`（布林） | 無 |
| `app.rollback` | `id`、`prop`、`rev`、`pre_sha256`、`post_sha256` | 無 |
| `obs.add` | `obs`（`OBS-SI-<≥3 位數>`）、`audit_ref`（UUID）、`audit_sha256`、`key_id`、`decider`（合 `^[A-Za-z0-9_.-]{1,64}$`）、`carrier`（恆為字面 `console`） | 無 |
| `obs.close` | 同 `obs.add` 之欄，另 `disposition`（非空單行字串，位元組數 ≤ `row_max_bytes`） | 無 |

  **ID 配號**：`DEC-SI-NNN`＝鎖內取既有 `dec` 事件 `id` 數字部分的最大值加 1（至少三位、零補齊）；`APP-SI-NNN`＝鎖內取**四種 `app.*` 事件合計**的最大值加 1（`app.sandbox`、`app.verify`、`app.promote`、`app.rollback` 共用一條計數）；`OBS-SI-NNN`（`obs-add`）沿 `ledger.max_valid_id` 加 1。`event_max_bytes` 仍為整行位元組上限（`EVENT-BYTES-OVER`；寫入端 rc 1）。
- **R73 `by` 與時間**：P2 寫入的事件 `by` 取 `--by`（預設 `main`；`heldout-freeze` 必給，並同時作為 `frozen_by`）；`decided_at`（逐字稿載體）＝被引記錄的 `timestamp` 轉本機 offset、秒精度（以 `astimezone()`；測試以「解析後同一時刻且帶 offset」斷言，不斷言本機時區）；`t` 一律 aware（沿 P1 R30）。
- **R74 帳本不變式（`events.transitions` 追加；碼皆 FAIL）**：(a) `FROZEN-BY-PROPOSER`：`heldout.freeze` 的 `frozen_by` 等於該 PROP 最近一筆 `prop` 事件的 `proposer`；(b) `HELDOUT-DUP`：同一 PROP 有二筆以上 `heldout.freeze`；(c) `HELDOUT-AFTER-SANDBOX`：`heldout.freeze` 的 `seq` 不小於同 PROP 第一筆 `app.sandbox` 的 `seq`，或該 PROP 有 `app.sandbox` 而無 `heldout.freeze`；(d) `SANDBOX-BASE-MISMATCH`：`app.sandbox.base` 不等於該 PROP（同 `rev`）`prop` 事件的 `base`；(e) `VERIFY-RUNS-EXCEEDED`：同 `(prop, rev)` 的 `app.verify` 事件數大於 `params.json` 的 `verify_runs_max`（`check` 對 `fold` 傳入該值；鍵無效則該判準不判並印 `SOURCE-UNAVAILABLE` 的 NE，沿 P1 R36 的形態）；(f) `PROMOTE-ACK-MISMATCH`：`app.promote.unverified_ack` 不等於其所消費之 `dec(promote)` 的 `flags` 是否含 `unverified_ack`；(g) `ROLLBACK-MANIFEST-MISMATCH`：`app.rollback.pre_sha256` 不等於該 PROP 最近一筆 `app.promote` 的 `post_sha256`，或 `post_sha256` 不等於該 `app.promote` 的 `pre_sha256`；(h) `DEC-TARGET-MISMATCH`：`dec` 的 `digest` 與當時 PROP 的 `digest` 不同（對六個綁卡面的 `dkind`；以該 `dec` 之前最近一筆 `prop` 事件的 `digest` 為準）；(i) `COOLDOWN-BYPASS-SUSPECT`（**warn**，項目狀態不變；R82 (f)）；(j) 沿 P1 的 `TRANSITION-ILLEGAL`、`TRANSITION-ORPHAN`、`CONFIRMER-IS-PROPOSER`。**`card_seq` 的連結檢查不在 `events.transitions`**（只驗型別與 `< seq`，§7.1 ⚖ 24）：它由 `events.dec_quote` 的 ③ 在逐字稿在場時驗，離線不驗。**P1 的 `QUOTE-VERIFIER-NOT-ESTABLISHED` warn 於 `events.transitions` 與 `events.research` 兩處皆移除**（引言回查自 P2 起由 `events.dec_quote` 與 `events.research` 的 `helmsman` 回查承接，R98）。
- **R75 狀態機（唯一合法轉移；`fold` 為唯一實作，`decide`、`promote`、`rollback`、`check` 共用其前提判定）**：

| 事件 | 前提（PROP 態與條件） | 結果態 |
|------|----------------------|--------|
| `prop`（rev 1） | 運轉為 open | `proposed` |
| `prop`（rev N＋1） | 態為 `returned` | `proposed`（`verdict`、`flags`、`reasons`、`rollback_ok`、`touched_ok` 歸零為 `null` 或空） |
| `dec` `approve` | `proposed` 且 `route` 為 `loop` | `approved` |
| `dec` `reject` | `proposed`（`fold` 只認 `dkind`、不認動詞，故「否決」與「不轉交」在重放側同為 `reject`；兩個動詞與 `route` 的配對〔否決要 `loop`、不轉交要 `handoff:*`，§7.2〕只在寫入端擋，碼 `ROUTE-VERB-MISMATCH`，不入重放） | `rejected`（啟動冷卻，R82） |
| `dec` `return` | `proposed`；或 `verified` 且（`verdict` 為 `FAIL`，或 `verdict` 為 `NE` 且 `reasons` 含 `SANDBOX-NOT-APPLIED`、`TOUCHED-SUPERSET`、`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT` 其一） | `returned` |
| `dec` `ack-handoff` | `proposed` 且 `route` 為 `handoff:*` | `handed-off` |
| `dec` `decline-promote` | `verified` | `rejected`（啟動冷卻） |
| `dec` `unblock` | `rejected` 且冷卻未被解除 | `rejected`（標記已解除） |
| `dec` `promote` | `verified` 且（`verdict` 為 `PASS`，或 `verdict` 為 `NE` 且 `flags` 含 `unverified_ack`）**且** `rollback_ok` 為 `true` **且** `touched_ok` 為 `true` | `verified`（待 `app.promote` 消費） |
| `dec` `rollback` | `promoted`、`measuring`、`closed` | 不變 |
| `dec` `resume` | 其 `run` 存在 | PROP 不變；解除 SUSPENDED（R93） |
| `app.sandbox` | `approved` | `sandboxed`；`Prop.rollback_ok`、`Prop.touched_ok` 取該事件的值（最近一筆為準） |
| `app.verify` | `sandboxed`；或 `verified`（**複驗邊**，同 `(prop, rev)` 至多 `verify_runs_max` 筆） | `verified`；`Prop.verdict`、`Prop.reasons` 取最近一筆 |
| `app.promote` | `verified` 且最近一筆未被消費的 `dec` 為 `promote` | `promoted` |
| `app.rollback` | `promoted`、`measuring`、`closed` 且有未被消費的 `dec(rollback)` | 不變 |

  `Prop` 增三個欄位 `reasons`（清單）、`rollback_ok`（布林或 `null`）、`touched_ok`（同）；`fold.cooldowns[]` 的元素增末鍵 `reason_class`（觸發冷卻的那筆 `dec` 的 `reason_class`）。`decide` 在記 DEC 時以**同一個前提判定**擋（rc 1、不記 DEC），否則手寫的 DEC 會被重放放行而寫入端擋、或反之（PRD §9.2 轉移註記）；AT-240-2-E-3 以格點差分釘住兩者一致。**測試 seam**：寫入端的前提判定函式為 `decwrite.preconditions(folded, prop, dkind, flags)`，回傳碼清單（空＝前提成立；§5.6）；`fold` 重放端是否把同一事件標為 `TRANSITION-ILLEGAL` 與它逐格一致（ `ROUTE-VERB-MISMATCH` 只在寫入端判，不納入差分格點）。
- **R76 OBS 標記鍵（`rows.MARK_KEYS` 加 `carrier`、`audit_ref`）**：值域——`carrier` 只准 `console`、`audit_ref` 為 UUID（小寫正規形；不合＝`MARK-VALUE`）；兩鍵成對（單有其一＝`CONSOLE-MARK-PAIR`）；`audit_ref` 全帳本唯一（二列同值＝`CONSOLE-AUDIT-DUP`，主語為後出現的列）；三碼皆歸 `row.markers`、FAIL，**只驗形態、不讀家目錄**。`row.provenance` 不新增判準。

*C. DEC 驗證、`decide` 與冷卻（FR-SI-12、13、14 的 P2 半；PRD §5.1.3、§7.2、AC-SI-12-4、§9.1 C8；機制細節中標「本檔類推」者見 §7.1）*

- **R77 逐字稿載體（`transcript.py`；ro；判準 fail-closed）**：(a) **路徑**：`claude_home()/projects/<slug>/<sid>.jsonl`；`claude_home()`＝`lib.platform_utils.claude_home()`（環境變數 `CLAUDE_CONFIG_DIR` 非空白則取之，否則 `Path.home()/".claude"`）；`<slug>`＝`re.sub(r"[^A-Za-z0-9]", "-", str(<--repo 的 realpath>))`（P1 `status._transcript_dir` 的同一規則；P2 把它搬進 `transcript.py`、`status` 改為引用，單一實作；觀察所得、非官方契約）。(b) **解析**：讀位元組、去開頭 UTF-8 BOM、以 `\n` 分行（行尾單一 `\r` 容忍）、**實體行號自 1 起算、空白行與壞行都計**；逐行 `json.loads`，**一律以解析後的結構欄位判定，不做整行子字串比對**（工具內容可含 `"origin":…` 字樣）。`line` 超出行數或小於 1＝`LINE-OUT-OF-RANGE`；該行不是 JSON 物件＝`RECORD-UNPARSABLE`。(c) **兩種真人發言載體**：(i) `type` 為 `user`、頂層 `origin` 為物件且 `origin.kind` 為 `human`、頂層 `isMeta` 不為 `true`；文字＝`message.content`（字串則取之；清單則取 `type` 為 `text` 的區塊之 `text` 以 `\n` 連接）。(ii) `type` 為 `attachment`、`attachment.type` 為 `queued_command`、`attachment.origin.kind` 為 `human`；文字＝`attachment.prompt`（字串）；**時序欄＝`attachment.timestamp`**（附件物件自帶＝入列＝打字時刻；不是記錄頂層的 `timestamp`，後者是寫入時刻，§7.1 ⚖ 6）。**不算**：`origin.kind` 為 `sdk`（`claude -p` 的 prompt，主控可自製）、`task-notification`、`peer` 與其餘任何值；`isMeta` 為 `true`；`type` 為 `assistant`、`system` 等；`tool_result`（含 `AskUserQuestion` 的答覆，其記錄無 `origin`）——一律 `NOT-HUMAN-UTTERANCE`。出處欄位缺席（`origin` 不存在或不是物件、或其 `kind` 缺）＝NOT-EVALUABLE（碼 `ORIGIN-MISSING`；不得記為已核准）；文字為空＝`TEXT-EMPTY`。(d) **assistant 文字**：`type` 為 `assistant` 的記錄，`message.content` 清單中 `type` 為 `text` 的區塊文字以 `\n` 連接（CRLF 先換 LF）；沒有任何 `text` 區塊（只含 `tool_use`、`thinking`）的訊息**略過**（工具輸出不算送達）。(e) **「發言之前最近一則含 text 區塊的 assistant 訊息」**：user 載體＝實體行號小於 `line` 的最近一則；附件載體＝以時間比對——有可解析頂層 `timestamp` 且**嚴格早於** `attachment.timestamp` 的 assistant 訊息中取 `timestamp` 最大者（同時刻取實體行號較大者）；`attachment.timestamp` 缺或不可解析＝NOT-EVALUABLE（`ATTACHMENT-TIME-UNKNOWN`）；沒有任何合格的 assistant 訊息＝`CARD-NOT-DELIVERED`。時間戳解析：ISO 8601，`Z` 視同 `+00:00`，比對以 aware UTC。(f) `verify_human_ref(sid, line)`：只驗 (c) 的載體與非空文字（`research.skip` 的 `helmsman` 回查用，R98 (e)）。(g) 逐字稿取不到（目錄或檔不存在）＝`TRANSCRIPT-UNAVAILABLE`（NE，不判紅）。
- **R78 決定語法解析（`decgrammar.py`；ro；純函式、不碰 I/O、不依賴 PROP 狀態）**：(a) 輸入為整則訊息文字；先 CRLF→LF，整則 `strip()`（含 U+3000 等 Unicode 空白），再以 `\n` 分行、每行 `strip()` 後比對。(b) **動詞表**（PRD §7.2 九列；動詞與 ID、ID 與理由之間**恰一個 ASCII 空格**，全形空格或連續空格不是決定行；`N` 為至少 3 位數字）：

| 動詞 | 行文法 | 尾隨規則 | ID | 導出 dkind |
|------|--------|----------|----|-----------|
| 核准 | `核准 PROP-SI-N` | 無 | PROP | `approve` |
| 否決 | `否決 PROP-SI-N <理由>` | 理由必填（寫不出填「未說明」） | PROP | `reject` 或 `decline-promote`（依 PROP 態，由 `decide` 定） |
| 退回 | `退回 PROP-SI-N <要求>` | 必填 | PROP | `return` |
| 晉升 | `晉升 PROP-SI-N`（前式）或 `晉升 PROP-SI-N 未驗採納`（後式） | 前式無；後式只准「未驗採納」四字 | PROP | `promote`（後式 `flags` 為 `unverified_ack`） |
| 轉交 | `轉交 PROP-SI-N` | 無 | PROP | `ack-handoff` |
| 不轉交 | `不轉交 PROP-SI-N <理由>` | 必填 | PROP | `reject` |
| 回滾 | `回滾 PROP-SI-N <理由>` | 必填 | PROP | `rollback` |
| 解除 | `解除 PROP-SI-N` | 無 | PROP | `unblock` |
| 恢復 | `恢復 RUN-SI-N <理由>` | 必填 | RUN | `resume` |

(c) **決定行**：某行（`strip()` 後）以九個動詞之一加一個 ASCII 空格起頭（取最長動詞：`不轉交` 先於 `轉交`；`不核准`、`請核准` 之類不是動詞起頭）。整行**完全符合**該列行文法＝**合法決定行**；以動詞加空格起頭卻不完全符合＝**畸形決定行**，其碼依違反項：`GRAMMAR-TRAILING`（無尾隨規則的動詞後有字、或後式晉升的尾隨不是「未驗採納」）、`GRAMMAR-REASON-MISSING`（理由必填而缺）、`GRAMMAR-FORM`（`晉升` 的式不合）、`GRAMMAR-ID-FORMAT`（ID 不合形態或與動詞不配，例：`恢復` 配 `PROP-SI-N`）。(d) **受理條件**：(c) 的決定行在整則訊息中**恰一個**且合法；其餘行為非決定行（可為任意閒聊文字，故「決定語法位於整則開頭」與「獨立成一行」兩種形態都滿足）。0 個＝`GRAMMAR-NO-DECISION`（否定句「不核准 PROP-SI-N」、前綴字、疑問式落此）；≥2 個（同 PROP 或異 PROP、動詞同或異）＝`GRAMMAR-MULTI`；唯一一個畸形＝其畸形碼。**理由句內出現的其他 `PROP-SI-N`／`RUN-SI-N` 字樣不構成第二個決定**（§7.1 ⚖ 7）。(e) **引用卡面**（先於 (d) 判）：整則訊息含字面 `--- 以下不計入核心區 ---`，或某行以 `[PROP-SI-` 起頭且含 `｜digest：`，或含字面 `決定：核准 ／` ⇒ `GRAMMAR-CARD-QUOTED`（整則不受理，不論其中有無合法決定行，§7.1 ⚖ 8）。(f) **疑問與尾隨**：`核准 PROP-SI-N？先等一下` 以 `核准 PROP-SI-N` 起頭但有尾隨字，屬畸形決定行 `GRAMMAR-TRAILING`。(g) **輸出**：`Parsed(verb, id, kind_candidates, trailing, flags, line_no)`；理由句＝ID 之後那一個空格之後的全部文字（`strip()` 後非空、不含換行；**不剖析標點，「一句」＝同一行**，§7.1 ⚖ 7）。
- **R79 引言驗證 `decverify.verify_dec(event, ctx)`（ro；`decide` 寫入前、`check` 的 `events.dec_quote`、`promote` 對 `approve` 與 `promote` 兩筆 DEC 的回查共用的唯一函式；依 `carrier` 分派，缺欄＝`transcript`）**：`transcript` 分支依序——① 以 `sid`＋`line` 取記錄（R77），須為兩種真人載體之一；② 先驗 `quote` 逐字等於該記錄文字中的某一行（兩者各 `strip()` 後相等；否則 `QUOTE-MISMATCH`），再把記錄全文餵 R78，須恰一個合法決定行且 `quote` 即該決定行，其動詞、ID 與事件的 `dkind`、`prop`（或 `run`）、`flags` 同列一致（`否決` 配 `reject` 或 `decline-promote`；`晉升` 的式與 `flags` 一致；不一致＝`KIND-MISMATCH` 或 `ID-MISMATCH`），理由句等於 `reason`；③（`resume` 不驗）卡面送達——見下；④ 逐字稿取不到＝`TRANSCRIPT-UNAVAILABLE`（NE）；⑤ 同函式被 `check`／`promote` 對已存 `dec` 重跑。回傳 `Verdict(status, code, detail)`：`ok`、`fail`（碼）、`ne`（`TRANSCRIPT-UNAVAILABLE`、`ORIGIN-MISSING`、`ATTACHMENT-TIME-UNKNOWN`）。失敗碼：`QUOTE-MISMATCH`（引言與記錄不符）、`NOT-HUMAN-UTTERANCE`、R78 的 `GRAMMAR-*`、`ID-MISMATCH`（引言的 ID 不等於事件的 `prop` 或 `run`）、`KIND-MISMATCH`、`CARD-NOT-DELIVERED`、`CARD-SHA-MISMATCH`、`LINE-OUT-OF-RANGE`、`RECORD-UNPARSABLE`、`TEXT-EMPTY`。**③ 的機制**（本檔類推，§7.1 ⚖ 5）：`card_seq` 所指的事件須是同 PROP 的 `card` 事件，其 `digest` 等於該 `dec` 的 `digest`（`rollback`、`unblock` 無 `digest` 者，等於該 `card` 事件當時 PROP 的 `digest`）；以事件帳本在該 `card` 事件**之前**的前綴折疊，用 `card.build` 的同一函式重建當時的卡面文字，其 `sha256:`（CRLF→LF 後的 UTF-8 位元組）須等於該 `card` 事件的 `card_sha256`（否則 `CARD-SHA-MISMATCH`——帳本內部不一致）；**卡面核心區**（卡面文字中 `--- 以下不計入核心區 ---` 之前的各行，以 `\n` 連接）須整段（逐字、行序與內容皆同）出現在 R77 (e) 所定「最近一則含 text 區塊的 assistant 訊息」的文字內，否則 `CARD-NOT-DELIVERED`——掌舵者沒有看到那張卡。`console` 分支呼叫 `consoleaudit`（R95）。
- **R80 `decide`（逐字稿載體）的流程與前提（`decwrite.py`；rw）**：(a) **用法（rc 3）**：`--sid` 非 UUID 正規形、`--line` 非正整數、`--kind` 不在九值、`--by` 非標籤、`--reason-class` 不在七值（給了才判）、`--carrier console` 與 `--kind`、`--sid`、`--line`、`--reason-class` 並用、位置參數不合 `PROP-SI-N` 或 `RUN-SI-N`、未知旗標（含 `--reason`、`--quote`、`--unverified-ack`：**不收引言文字、不收 `--reason`、不收 `--unverified-ack`**，理由取自引言尾隨句、旗標由引言式導出，AC-SI-12-1「非主控輸入」）。(b) `UNATTENDED-REFUSED`（R70）。(c) 存在性（依位置參數的形態）：`PROP-SI-N` 者驗該 PROP 存在（`PROP-NOT-FOUND`）、`RUN-SI-N` 者驗事件帳本有該運轉的 `run.open`（`RUN-NOT-FOUND`）。(d) **逐字稿層**（依序、遇第一個失敗即回；rc 1，不記 DEC）：R77 取記錄（`TRANSCRIPT-UNAVAILABLE` 於此：逐字稿取不到＝rc 1 而非 rc 3）→ R78 語法 → 引言動詞所要求的 ID 種類（`恢復` 為 RUN、其餘八個動詞為 PROP）不等於位置參數的種類（`ID-KIND`，先判）→ 引言的 ID 等於位置參數（種類相同而號碼不同＝`ID-MISMATCH`）→ `--kind` 等於（動詞, PROP 態）導出的 dkind（`KIND-MISMATCH`；`否決` 於 PROP 為 `proposed` 導出 `reject`、`verified` 導出 `decline-promote`、其餘態＝`PRECONDITION-STATE`）。(e) **狀態層**（全部收集後一併回報）：R75 的前提（`PRECONDITION-STATE`）、`ROUTE-HANDOFF`（對 `route` 為 `handoff:*` 的 PROP 說核准或晉升）、`ROUTE-VERB-MISMATCH`（否決對 handoff 路由、或不轉交對 loop 路由）、`PROMOTE-FORM-MISMATCH`（`PASS` 配後式或 `NE` 配前式；`FAIL` 一律不收）、`PROMOTE-PREMISE-ROLLBACK`（最近一筆 `app.sandbox` 的 `rollback_ok` 不為 `true`）、`PROMOTE-PREMISE-TOUCHED`（`touched_ok` 不為 `true`）、`PRECONDITION-VERDICT`（`return` 於 `verified` 而 verdict 為 NE 且 `reasons` 不含四碼之一）、`NOT-IN-COOLDOWN`（`unblock` 對非冷卻中）、`RUN-MISMATCH`（`resume` 的 RUN 不等於折疊出的 SUSPENDED 所在運轉）、`NOT-SUSPENDED`（迴圈未 SUSPENDED）、理由類——`REASON-CLASS-MISSING`（`reject`、`decline-promote`、`return` 未給）、`REASON-CLASS-INVALID`（R82 的七值之外；寫入端在 (a) 已 rc 3，此碼供 `check` 回查事件欄位用）、`REASON-CLASS-UNEXPECTED`（給了不收的 dkind）、`REASON-CLASS-MISMATCH`（引言尾隨句恰為「未說明」而 `--reason-class` 不是 `未說明`，反之亦然）。(f) **卡面層**：`CARD-NOT-ISSUED`（同 PROP 無任何 `card` 事件；`resume` 免）、`STALE-CARD`（最近一筆 `card` 的 `digest` 不等於 PROP 當下 digest）、`CARD-CHANGED`（最近一筆 `card` 的 `card_sha256` 不等於當下重算的卡面雜湊）、`CARD-NOT-DELIVERED`（R79 ③）。(g) 取鎖、鎖內重驗（PROP 態與 digest 未變，否則 `STATE-CHANGED`）、配 `DEC-SI-NNN`、組事件（`quote`＝決定行、`reason`＝理由句〔無則省略〕、`flags`＝後式晉升導出、`card_seq`＝最近一筆 `card` 的 `seq`〔`resume` 無〕、`decider` 為「掌舵者」、`decided_at`＝R73）後追加；成功印 R69 的單行（含 PROP 或 RUN、dkind、digest 前 8 碼，§7.1 回饋）。(h) 事件行超 `event_max_bytes`＝rc 1 `EVENT-BYTES-OVER`（`dec` 的最壞行隨 `quote`、`reason` 長度）。
- **R81 `card --issue`（`card.py` 加旗標；寫入由 `decwrite.py` 做、`card.py` 維持 ro；PRD §9.3 `card` 列）**：前置——`UNATTENDED-REFUSED`；PROP 不存在＝rc 3（沿 P1 `card` 的 `PROP-NOT-FOUND`）；PROP 態須是 §7.2 任一列的前提態（`proposed`、`verified`、`promoted`、`measuring`、`closed`，或 `rejected` 且冷卻中〔未被 `unblock`〕），否則 rc 1 `STATE-ILLEGAL`。於寫入鎖內重算卡面並追加 `card` 事件（`prop`、`rev`＝PROP 當下 `rev`、`digest`＝PROP 當下 digest、`card_sha256`＝卡面文字〔CRLF→LF〕UTF-8 位元組的 `sha256:`）；重複 `--issue` 追加新事件（不去重）；stdout 規則見 R69。不帶 `--issue` 的 `card` 仍唯讀（P1 不變）。
- **R82 拒絕紀錄與同型冷卻（FR-SI-13；`cooldown.py`；ro；`props.py` 的 `prop-new` 前置檢查呼叫它）**：(a) **拒絕紀錄**：`reject`、`decline-promote`、`return` 的 `dec` 必有 `reason_class`（七值：證據不足、風險過高、工件類別錯、已被涵蓋、範圍外、卡面不清、未說明）與 `reason`；引言尾隨句恰為「未說明」者 `reason_class` 只准 `未說明`，且採最嚴冷卻：**其冷卻只能由 (b-1)「解除」結束，(b-2) 新證據不適用**（§7.1 ⚖ 9）。(b) **冷卻的起訖**：PROP 因 `reject` 或 `decline-promote` 進入 `rejected` 即啟動冷卻（`return` 不啟動）；結束＝(b-1) `dec(unblock)`；或 (b-2) 否決後新立、與該 PROP 同根因鍵、且證據座標集合與原提案證據集合**不相交**的 OBS 列 ≥1 筆。(c) **同型**＝新提案（標記後的 `cls`）與某 `rejected` PROP：`cls` 相同 ∧ `target` 路徑集合相同（排序去重後逐一相等，沿 `props._dup_code`）∧（根因鍵集合有交集 ∨ **證據座標集合**有交集）。根因鍵集合＝該 PROP 的 `sources` 中 OBS 為 `attr`（root）事件 `obs` 的已確認事件之 `root_cause`（沿 `fold.prop_root_causes`）；證據座標集合＝該 PROP 各 `sources` 列（OBS 列取證據座標格、DEF 列取「現象與證據」欄）以九形態座標抽出的全部片段（逐片段 `\\` 換 `/`、`casefold`；`rows` 增函式 `coord_set(cell)`，本檔類推）的聯集。(d) **新證據列（b-2）的認定**（只認 OBS 列：根因鍵經 `attr.confirm` 確認的機制只對 OBS 列存在，DEF 列無根因鍵、不構成 (b-2)，§7.1 ⚖ 10）：`時間` 不早於該筆否決 `dec` 的 `decided_at`；其根因鍵經確認且等於原 PROP 的根因鍵之一；其證據座標集合與原 PROP 的證據座標集合不相交——三條件皆須。(e) **`prop-new` 的拒收**：與某冷卻中（`rejected`、未被 `unblock`）PROP 同型，且 (b-2) 不成立 ⇒ rc 1、碼 `COOLDOWN`（detail 列被擋於哪個 PROP）；已 `unblock` 或 (b-2) 成立者放行。**再提案須附逐項回應否決理由**：存在同型的 `rejected` PROP（含已解除者）時，新提案本文欄位表須有非空的 `reject_response` 鍵，否則 rc 1 `REJECT-RESPONSE-MISSING`（本檔類推，§7.1 ⚖ 10）。`COOLDOWN` 與 P1 的 `DUPLICATE-TYPE`（活躍 PROP 同型）互不取代、可同時命中。(f) **重放偵測（D 型）**：`events.transitions` 對每筆 `prop`（rev 1）事件，若其前已有同型（`cls`、`target`、根因鍵相交；證據座標離線不重算）且冷卻中（未被 `unblock`）的 `rejected` PROP，印 warn `COOLDOWN-BYPASS-SUSPECT`（項目狀態不變；離線無法重放 (b-2) 的新證據判定，所以只能是 warn，誠實劃界）。M4 的計數與自動入 OBS 屬 P3（§4〈刻意不做〉）。

*D. held-out、沙盒、驗證與證據（FR-SI-15、17～21；PRD §9.1 C9／C10、§9.2〈held-out 目錄格式〉〈manifest 規則〉、§9.4〈沙盒與驗證執行的邊界〉〈三態判定表〉；機制細節中標「本檔類推」者見 §7.1）*

- **R83 held-out 目錄格式與 `heldout-freeze`（FR-SI-20；`heldout.py` ro、`decwrite.py` rw）**：(a) **目錄**：`<dir>/manifest.json`（UTF-8 無 BOM、LF）頂層鍵恰 `schema_rev`（整數 1）、`cases`、`probes`、選用 `mutation`；`cases`＝`[{"id": <非空字串，唯一>, "ref": <OBS-SI-N 或 DEF-…>}…]`（`ref` 須存在於 OBS 帳本含封存檔或缺陷帳本家族，否則 `HELDOUT-REF-UNRESOLVED`）；`probes`＝`[{"id": <非空字串，唯一>, "argv": [<字串…>], "module": <選用，合 ^[A-Za-z_][A-Za-z0-9_.]*$>, "n_pop": <整數 ≥0>}…]`，`argv` 非空、第 0 項恰為字面 `{python}`、其餘項可含佔位 `{sandbox}`、`{heldout}`；`mutation`＝選用的相對檔名（無分隔符號、非 `..`、不以 `.` 起頭），該檔須在目錄內；`probes` 可為空陣列（M／D 類無確定性探針）。形態不合＝`HELDOUT-MANIFEST-INVALID`（detail 列出違反項）。(b) **`heldout-freeze <PROP> --from <dir> --by <標籤>` 前置**（rc 1，碼）：`UNATTENDED-REFUSED`；`PROP-NOT-FOUND`；`ROUTE-HANDOFF`（`route` 為 `handoff:*` 的 PROP 不進沙盒、不凍結）；`HELDOUT-EXISTS`（`<si>/heldout/<PROP>/` 已存在，或事件帳本已有同 PROP 的 `heldout.freeze`；每 PROP 至多一次）；`HELDOUT-AFTER-SANDBOX`（該 PROP 已有 `app.sandbox`）；`PROP-STATE-ILLEGAL`（PROP 態為 `rejected`、`handed-off`、`promoted`、`measuring`、`closed`）；`FROZEN-BY-PROPOSER`（`--by` 等於該 PROP 最近一筆 `prop` 事件的 `proposer`）；`HELDOUT-FROM-INSIDE`（`--from` 的 realpath 在 `<si>/heldout/` 之下）；`HELDOUT-LINK`（`--from` 目錄內含符號連結，本檔類推，§7.1 ⚖ 20）；`HELDOUT-MANIFEST-INVALID`、`HELDOUT-REF-UNRESOLVED`、`HELDOUT-EMPTY`（`cases` 為空，事件的 `n` 須 ≥1）；`--from` 不存在或非目錄＝rc 3。案例數 `n` 小於 `min_heldout` **仍可凍結**（`verify` 判 NE，AC-SI-20-2）。(c) **成功**：把 `--from` 目錄全部檔案（遞迴、原位元組、保留相對路徑）複製進暫名目錄、算 digest（R84 原始位元組式）、換入 `<si>/heldout/<PROP>/`；鎖內重驗（PROP 態、無 `heldout.freeze`、無 `app.sandbox`）後追加事件（`prop`、`digest`、`n`＝`len(cases)`、`frozen_by`＝`--by`）；`heldout-freeze` 的 `by` 即 `--by`。(d) **盲性**：held-out 內容只在家目錄、不入 git；事件只存 digest 與 `n`；提案者拿不到內容屬任務書約束（P），暴露偵測見 R90 (b)（D）。
- **R84 `manifest`（ro；沙盒、held-out、pre／post 三處共用同一份實作）**：manifest 文字＝逐檔一行 `<posix 相對路徑，保留原大小寫>\t<hex 或 absent>\n`，依路徑的 UTF-8 位元組序排序，整體取 `sha256` 並加 `sha256:` 前綴。兩式：**原始位元組式**（每檔取 `sha256(原始位元組)`；用於 `sandbox_sha256` 與 held-out `digest`；機器本地證據，不跨機比對）；**LF 正規化式**（每檔先 CRLF→LF 再 `sha256`，指名路徑缺檔記 `absent`；用於 `pre_sha256`、`post_sha256`，使 `touched` 路徑在兩平台工作樹與 M 類記憶檔得同一值）。樹 manifest 涵蓋目錄樹下全部一般檔（遞迴；不含空目錄）。成員型別預檢（只收一般檔與目錄）與路徑長度預檢（Windows：`len(根)＋1＋最長成員相對路徑` 大於 259＝`SANDBOX-PATH-TOO-LONG`；POSIX 不判）住本檔。
- **R85 沙盒的匯出、抽取預檢、套用與回滾乾跑（FR-SI-15、AC-SI-16-2；ADR-SI-04；`sandbox.py`；rw）**：(a) **根**：`<si>/sandbox/<PROP>`；`<si>/sandbox` 的 realpath 落在 repo 樹內，或路徑含 `.claude/worktrees/` 片段 ⇒ rc 3、碼 `SANDBOX-ROOT-IN-REPO`、不寫事件（AC-SI-15-1；根層跨平台整合輪第 178 輪實測：樹內 worktree 被全庫掃描鎖算成第二份複本而假紅）；清理＝刪除 `<si>/sandbox/<PROP>` 目錄樹（其 realpath 須在 `<si>/sandbox/` 之下且本身不是符號連結或 junction，否則 rc 3），**絕不經 git 清理**（鐵律五）。(b) **匯出**：`git -c core.autocrlf=false archive --format=tar --output=<暫存 tar 檔> <PROP 的 base>`（M 類改為把 `--memory-dir` 內被 `touched` 觸及的記憶檔複製到沙盒的 `memory/` 之下）；tar 檔放在沙盒根旁的暫名處（不放 repo 內）；匯出子行程牆鐘上界 `probe_timeout_seconds`（`Git.run` 的 `timeout` 選用參數，預設仍 60 秒）。(c) **抽取預檢（自寫、必備；§7.1 ⚖ 2）**：對 tar 每個成員，**先於任何寫入**檢查——名稱含 `..` 片段、絕對路徑（`/` 或 `\\` 起頭）、磁碟機代號或任何 `:`（含 NTFS 資料流）、控制字元或 NUL、片段尾端為點或空白、型別非一般檔與目錄（符號連結、硬連結、字元與區塊裝置、FIFO 皆拒）、同名重複成員——任一命中 ⇒ 匯出失敗（stderr 碼 `SANDBOX-MEMBER-REJECTED`；事件 `fail_code` 為 `SANDBOX-EXPORT-FAILED`）。通過預檢才 `extractall(…, filter="data")`；**直譯器無 `tarfile.data_filter` 屬性＝rc 3、不降級、不寫事件**（PRD §9.3；碼 `TARFILE-FILTER-MISSING`）。**函式級入口（測試 seam，§5.6）**：`sandbox.precheck_members(tar, root)` 回 `[(成員名, 原因碼), …]`（空＝通過；路徑過長判於此，平台取自 `sys.platform`）；`sandbox.extract_checked(tar_path, root)` ＝預檢加 `extractall(…, filter="data")`，預檢不過拋 `SandboxError`（先於任何寫入）。**實測**（本檔作者探針，Windows、Python 3.11.9）：`hasattr(tarfile, "data_filter")` 為真；`data_filter` 對 `../evil.txt` 成員拋 `OutsideDestinationError`、對符號連結成員拋 `LinkOutsideDestinationError`，但對絕對路徑成員 `/abs_evil.txt` **不拋例外、只靜默剝掉前導斜線**後把檔寫進目的目錄——所以自寫預檢不是冗餘，它把「靜默改名」變成「匯出失敗」。(d) **套用**：抽取後立即算 `sandbox_sha256`（R84 原始位元組式）；`git -c core.autocrlf=false apply <rN.patch>`（cwd＝沙盒根；**沙盒內沒有 `.git`，實測 `git apply` 在無 `.git` 的樹內可用**，含 `--numstat` 與 `-R`，§7.1 ⚖ 4）；牆鐘上界 `probe_timeout_seconds`，逾時＝`applied` 為 `false`、`fail_code` 為 `SANDBOX-APPLY-TIMEOUT`；套不上（rc 非 0）＝`applied` 為 `false`、`fail_code` 為 `null`。**`-c core.autocrlf=false` 是必備旗標**：Git for Windows 的系統層設定 `core.autocrlf=true` 使無 `.git` 的樹內 `git apply` 把被改的檔整個寫成 CRLF，正向加反向套用後與 base 逐位元不同（本檔作者實測，`git -C <無 .git 目錄> apply`：預設設定 `fwdCRLF=True`、`revEqualsBase=False`；`-c core.autocrlf=false`、`GIT_CONFIG_NOSYSTEM=1`、空的 `GIT_CONFIG_GLOBAL` 或 `GIT_CONFIG_COUNT` 環境變數式設定皆 `fwdCRLF=False`、`revEqualsBase=True`；§7.1 ⚖ 3）。故 P2 全部 `git apply`（沙盒、`promote`、`rollback`、M 類的記憶目錄）與 `git archive` 一律帶 `-c core.autocrlf=false`；AT-215-1-E-3 以 `GIT_CONFIG_GLOBAL` 指向含 `autocrlf = true` 的設定檔重現 Windows 預設（P1 的 hermetic 環境把全域與系統設定清空，看不到這個危害）。(e) **`touched_ok`**：套用前後樹 manifest（R84）的差異路徑集合（新增、刪除、內容變更）須 ⊆ `touched`（自 `rN.patch` 導出、含改名兩端）⇒ `true`，否則 `false`（僅 `applied` 為 `true` 才判）。測試以替身包住 `sandbox.apply_patch(root, patch_path) -> set[str]`（真實函式先套用並回傳套用器實際寫入的路徑集合；替身在回傳集合加一個字面路徑）令它多寫一個路徑製造 `false`。(f) **回滾乾跑**：`git -c core.autocrlf=false apply -R <rN.patch>`（函式 `sandbox.reverse_apply(root, patch_path) -> bool`，回傳 git 是否成功）後重算樹 manifest 須逐位元等於 `sandbox_sha256` ⇒ `rollback_ok` 為 `true`，否則 `false`（僅 `applied` 為 `true` 才判；`touched_ok` 為 `false` 時仍判）；測試以替身包住 `sandbox.reverse_apply`（真實函式先反向套用，替身再於沙盒根多寫一個檔）製造 `false`；乾跑結束時樹回到 base 狀態（供 `verify` 的 RED 步使用）。(g) **事件**：全部成功與失敗路徑**一律寫 `app.sandbox`**（R72 的條件必備規則）；匯出失敗另於 stderr 印具體成因碼之一：`SANDBOX-EXPORT-TIMEOUT`、`SANDBOX-PATH-TOO-LONG`（僅 Windows）、`SANDBOX-MEMBER-REJECTED`、`SANDBOX-GIT-FAILED`（git 不可用或 `archive` rc 非 0）。
- **R86 `sandbox` 動詞（rc 與前置；PRD §9.3）**：前置（rc 1，碼）：`UNATTENDED-REFUSED`；`PROP-NOT-FOUND`；`STATE-NOT-APPROVED`（態不是 `approved`）；`HELDOUT-NOT-FROZEN`（同 PROP 無 `heldout.freeze`；AC-SI-20-1 要求凍結的 `seq` 早於第一筆 `app.sandbox`）；`DEC-VERIFY-FAILED`（`dec(approve)` 以 `verify_dec` 回查失敗，detail 帶回查碼）、`TRANSCRIPT-UNAVAILABLE`（因逐字稿取不到而無法回查，fail-closed 拒收）、`CONSOLE-AUDIT-MISSING`／`CONSOLE-KEY-MISSING`（`approve` 為 Console 載體者同）；`DIGEST-MISMATCH`（自 `rN.patch`、`rN.md` 重算的 digest 不同於 PROP 事件 digest 或 `approve` 的 `digest`，AC-SI-12-2）；`MEMORY-DIR-MISSING`（M 類未給 `--memory-dir`）；rc 3：用法、家目錄不可寫、沙盒根在 repo 內、`TARFILE-FILTER-MISSING`、`probe_timeout_seconds` 鍵無效。每次呼叫重建 `<si>/sandbox/<PROP>`（先在暫名目錄組裝、成功才換入）；匯出與套用在寫入鎖外，鎖內重驗（PROP 仍 `approved`、digest 未變）後才追加 `app.sandbox`，重驗失敗＝rc 1 `STATE-CHANGED` 且零殘留。**rc 0 涵蓋 `applied=false`**（印出 `applied=false` 與 `fail_code`，並印 OBS 草稿列，R69）。**正式面不變**：呼叫前後 repo 的 `git status --porcelain` 輸出、`HEAD`、`git worktree list` 輸出逐字相同（AC-SI-15-1）。
- **R87 子行程出口 `runner.py`（exec；整個套件除 `git.py` 外唯一出現 `subprocess` 字樣的檔；PRD §9.4）**：(a) 以 `subprocess.Popen` 加 `communicate(timeout=…)`，`shell=False`；`argv[0]` 的佔位 `{python}` 換成 `sys.executable`，其餘項的 `{sandbox}`、`{heldout}` 換成對應路徑（`verifyK.json` 的 `cmd` 保留**未展開**的佔位字面）；cwd＝沙盒樹根；`encoding="utf-8"`、`errors="replace"`；**不帶 `-I`／`-P`**（它們忽略 `PYTHONPATH`，載具自證會失效）。(b) **環境白名單**：只傳 `PATH`、`SYSTEMROOT`、`TEMP`、`TMP`、`HOME`、`USERPROFILE`、`LANG`、`LC_ALL`（父行程有設才傳），加固定的 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`，與 `PYTHONPATH`＝**只有**沙盒樹根（單一元素；不繼承父行程的 `PYTHONPATH`）；不繼承任何 `AUTOSDD_*`（含金鑰環 `AUTOSDD_SI_AUDIT_KEY`）與其他機密。(c) **逾時**：每個子行程牆鐘上界 `probe_timeout_seconds`；逾時即**殺行程樹**（Windows：`taskkill /T /F /PID <pid>`；POSIX：對以 `start_new_session=True` 啟動的行程群組呼叫 `os.killpg`），兩條各在 `sys.platform` 守衛作用域內（根層 `TestForeignExecutableArgvIsGuarded` 與 `TestForeignPlatformApiIsGuarded` 所認的站點級守衛形態；Windows 的 `creationflags` 以 `getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)` 兜底傳入、不判 kwarg 本身），殺完回收（不留殭屍、不留孫行程），回報 `timed_out`。(d) **輸出摘要**：完整 stdout 與 stderr 位元組（合併，stdout 在前）算 `out_sha256`（`sha256:` 前綴）與 `out_bytes`（完整位元組數）；`tail`＝合併輸出經遮蔽後取**最後 ≤300 位元組**（依 UTF-8 邊界截斷、不切半個字元）；遮蔽四型：`Bearer <token>`、`sk-` 起頭的金鑰、`Authorization:` 標頭值、DSN 的 `://<user>:<pass>@`（皆換成 `[REDACTED]`；於 `runner.py` 自備、不 import `autoclaude`，能力登記判準：非標準庫 import 一律紅）；**原始輸出全文不入 git、不落任何檔**（NFR-SI-02-4）。(e) 不得有 `time.sleep`、`while True`、`os.fork`、`signal.alarm`（套件禁字樣，AT-240-5-E-2）。(f) **探針入口（測試 seam，§5.6）**：`runner.run_probe(argv, *, cwd, sandbox_root, timeout)` 回 `ProbeResult(rc, timed_out, out_sha256, out_bytes, tail)`；`verify` 的每個探針與每次載具自證子行程都只經它；測試以記錄器包住它計呼叫數（⓪ 路徑與超限拒收須為 0 次）、或以替身在第一次呼叫時改動帳本製造鎖內重驗競態。
- **R88 `verify` 動詞與三步編排（`verify.py`；exec）**：前置（rc 1，碼）：`UNATTENDED-REFUSED`；`PROP-NOT-FOUND`；`STATE-NOT-VERIFIABLE`（態不是 `sandboxed` 或 `verified`）；`HELDOUT-NOT-FROZEN`；`VERIFY-RUNS-EXCEEDED`（同 `(prop, rev)` 的 `app.verify` 已達 `verify_runs_max`，須升級人工）；`SANDBOX-TREE-DRIFT`（沙盒樹不在或樹 manifest 不等於 `sandbox_sha256` 時重新匯出，仍不等於＝他機或 git 版本差異，§7.1 ⚖ 15）；rc 3：用法、家目錄不可寫、`probe_timeout_seconds` 或 `verify_runs_max` 鍵無效（stderr 點名鍵、不以預設值頂替）。**判定順序（與 R89 同序）**：**⓪ 沙盒失敗先於預檢**——讀同 `(prop, rev)` 最近一筆 `app.sandbox`，`applied` 不為 `true`、或 `touched_ok` 為 `false`、或 `rollback_ok` 不為 `true` 時，不做預檢、不跑探針，直接收 R89 ⓪ 的 verdict（`probes_n` 為 0、`verify_sha256` 與 `heldout_digest` 為 `null`、四個步驟欄皆 `null`）。通過 ⓪ 後的**預檢**：重算 held-out 目錄 digest（不符 `heldout.freeze.digest`＝`HELDOUT-DIGEST-MISMATCH`）、`n` 小於 `min_heldout`＝`HELDOUT-TOO-SMALL`、暴露掃描（R90 (b)；命中＝`HELDOUT-EXPOSED`、逐字稿取不到＝`EXPOSURE-UNKNOWN`）——預檢的 NE 碼只記入 `reasons`、**仍照常跑探針與三步**（使證據齊備，由 R89 ① 判 NE）；`probes` 為空＝不跑三步、`probes_n` 為 0、`NO-PROBES`。**三步**（沙盒樹自 base 起；每步每個探針各一個子行程，R87）：RED（未套用）→ `baseline_red`＝全部探針 rc 非 0 且無逾時；GREEN（`git -c core.autocrlf=false apply <rN.patch>` 後）→ `patched_green`＝全部探針 rc 為 0 且無逾時；突變（`--mutation <檔>` 或 manifest 的 `mutation`，疊在已套用的樹上 `git apply`）→ `mutated_red`＝全部探針 rc 非 0 且無逾時；兩者皆無＝突變步不執行、`mutated_red` 為 `null`；**兩者並存＝rc 3（用法錯誤，stderr 含字樣「突變來源二擇一」，零寫入；本檔類推，§7.1 ⚖ 25）**——突變來源不得由驗證者與凍結者各給一份而事後擇優。非逾時的失敗（如 `patched_green` 為 `false`）**不略過其後步驟**（證據齊備，由 R89 判級）；只有逾時才使其後步驟不執行。**探針慣例**：rc 為 0＝症狀不在、非 0＝症狀在（與 pytest、ruff 同向）；探針逾時不是 rc、單獨判（該步欄位為 `null`、其後的步驟不執行、`reasons` 含 `PROBE-TIMEOUT`）。**探針在單次驗證內不重試至通過**（每步每個探針恰執行一次；重試至通過是 Goodhart 路徑，禁令 4）。三步結束後反向套用還原沙盒樹到 base。**載具自證**：manifest 有任一探針宣告 `module` 時，對每個相異的 `module`（名稱先驗正規式）以 `{python} -c` 在沙盒環境（R87）取其 `__file__`，realpath 後須在沙盒樹根之下，全部成立＝`carrier_proof` 為 `true`、任一不成立＝`false`；**manifest 沒有任何探針宣告 `module` 時 `carrier_proof` 為 `true`**（探針以 `{sandbox}` 路徑定址、不 import 受測模組；本檔類推，§7.1 ⚖ 13；不聲稱防止探針自行讀主樹）。`verifyK.json` 落地（R90）後**鎖內重驗**（PROP 態仍為 `sandboxed` 或 `verified`、digest 未變、`app.verify` 數仍小於 `verify_runs_max`、held-out digest 仍同）才追加 `app.verify`；重驗失敗＝rc 1 `STATE-CHANGED` 並刪除剛落地的 `verifyK.json`（零殘留）。**rc 0 不論 verdict**；verdict 印在 stdout 與 `--json`。探針在寫入鎖之外執行。
- **R89 三態判定 `verdict.verdict_of`（ro；純函式；`verify` 與 `check` 的 `events.verdict` 共用）**：輸入＝同 `(prop, rev)` 最近一筆 `app.sandbox` 的 `applied`、`touched_ok`、`rollback_ok`、`fail_code`，與 `app.verify` 的 `probes_n`、`carrier_proof`、`baseline_red`、`patched_green`、`mutated_red`、`heldout_digest`、`reasons`，與 `heldout.freeze` 的 `digest` 與 `n`，與 `min_heldout`；輸出 `(verdict, reasons)`。**依層判、先中者定案；`reasons` 為決定層的全部成立碼**（PRD〈三態判定表〉「列出所有成立的碼」的讀法：只指決定層內全部，不跨層，§7.1 ⚖ 42）：
  - ⓪ 沙盒失敗（三條各自判、全部列出，verdict 取第一個成立者）：`applied` 不為 `true` ⇒ NE，碼＝該 `fail_code`（`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT`；`fail_code` 為 `null`＝`SANDBOX-NOT-APPLIED`）；`touched_ok` 為 `false` ⇒ NE `TOUCHED-SUPERSET`；`rollback_ok` 為 `false` ⇒ FAIL `ROLLBACK-DRYRUN-FAILED`（`applied` 不為 `true` 時 `touched_ok`、`rollback_ok` 皆 `null`＝不適用，不另列）。
  - ① 測量無效 ⇒ NE（`probes_n` 為 0 ⇒ 只列 `NO-PROBES`，不列 `CARRIER-PROOF-FAILED`、`BASELINE-NOT-RED`、`MUTATION-ABSENT`；`probes_n` ≥1 時各自判）：`NO-PROBES`；`CARRIER-PROOF-FAILED`（`carrier_proof` 不為 `true`）；`HELDOUT-DIGEST-MISMATCH`（`heldout_digest` 不等於 `heldout.freeze.digest`）；`HELDOUT-TOO-SMALL`（`n` 小於 `min_heldout`）；`HELDOUT-EXPOSED`、`EXPOSURE-UNKNOWN`、`PROBE-TIMEOUT`（記錄的 `reasons` 含它即成立；這三碼無法由其他欄位導出）。
  - ② `baseline_red` 不為 `true` ⇒ NE `BASELINE-NOT-RED`。③ `patched_green` 不為 `true` ⇒ FAIL `PATCHED-NOT-GREEN`。④ `mutated_red` 不為 `true` ⇒ NE（`false`＝`MUTATION-NOT-RED`、`null`＝`MUTATION-ABSENT`）。⑤ 其餘 ⇒ PASS、`reasons` 為空。
  **FAIL 只來自測得的失敗，不來自逾時、不來自缺資料。**WHY 先測量有效、後判定：載具自證失敗時 GREEN 是測在主樹上，判成 FAIL 或 PASS 都無依據。
- **R90 逐探針驗證檔、暴露掃描與證據入帳（AC-SI-19、20-4、21-1；`propfiles.py`、`transcript.py`）**：(a) **`verifyK.json`**（`docs/06_quality/SelfImproving_Proposals/PROP-SI-NNN/verify<K>.json`，K＝該 PROP 已有的 `app.verify` 事件數加 1、自 1 起；只新建、不改寫；UTF-8 無 BOM、LF、結尾換行；`ensure_ascii=False`、鍵序固定）：`{"schema_rev":1,"prop","rev","k","base","heldout_digest","carrier":{"<module>":"<`__file__` 的沙盒相對 posix 路徑>"},"steps":{"baseline":[rec…],"patched":[rec…],"mutated":[rec…] 或 null}}`（逾時使其後步驟不執行：未執行的 `baseline`、`patched` 為空清單，未執行或不存在的 `mutated` 為 `null`）；`rec`＝`{"id","cmd"（未展開的 argv）,"rc"（逾時為 null）,"timed_out","out_sha256","out_bytes","n_pop","tail"}`；`app.verify.verify_sha256`＝該檔位元組（原樣、不做 CRLF 正規化）的 `sha256:`；`check` 的 `events.prop_files` 擴充重算：對每筆 `verify_sha256` 非 `null` 的 `app.verify` 事件（它是該 PROP 的第 K 筆 `app.verify`，K 自 1 起依事件序，含 `verify_sha256` 為 `null` 者），驗證檔 `verify<K>.json` 缺＝`PROP-FILE-MISSING`、位元組雜湊不等於 `verify_sha256`＝新碼 `PROP-VERIFY-SHA-MISMATCH`（皆 FAIL；subject 為 `<PROP> verify<K>`，沿 P1 `<PROP> r<rev>` 的形態）；`verify_sha256` 為 `null` 者不要求驗證檔。⓪ 路徑與 `NO-PROBES` 不產生此檔。(b) **暴露掃描**（AC-SI-20-4 ②；本檔類推，§7.1 ⚖ 12）：掃描面＝`claude_home()/projects/<slug>/` 之下遞迴的全部 `subagents/**/*.jsonl`（子代理逐字稿；主控逐字稿不掃——主控本就持有 held-out 路徑與 `params.json`）；只看 `type` 為 `assistant` 的記錄 `message.content` 中 `tool_use` 區塊的 `input`，遞迴取其全部字串值；**只計入頂層 `timestamp` 不早於該 PROP 的 `heldout.freeze` 事件時刻 `t` 的 assistant 記錄**（凍結之前的工具呼叫不可能取得凍結之後才存在的 held-out 內容；真實語料已含 `params.json` 與量測腳本兩種針，不限窗則每個真實 PROP 都被判 NE，§7.1 ⚖ 12、⚖ 41）；**缺頂層 `timestamp` 或其值不可解析的 assistant 記錄一律視為落在窗口內**（保守：計入掃描，其 `tool_use` 含針即命中），不新增狀態；檔案 mtime 早於 `t` 者可直接略過（效能；不改判定）；時間戳解析沿 R77 (e)（ISO 8601，`Z` 視同 `+00:00`，比對以 aware UTC）；正規化（`\\` 換 `/`、`casefold`）後含下列任一針（needle）即命中：該 PROP 的 held-out 凍結目錄絕對路徑（`<si>/heldout/<PROP>`）、字面 `selfimproving_protocol/params.json`、字面 `tools/probe/selfimproving_measure.py`。命中任一 ⇒ `HELDOUT-EXPOSED`（NE）；`projects/<slug>/` 目錄不存在 ⇒ `EXPOSURE-UNKNOWN`（NE）；目錄存在而無任何 `subagents/` 逐字稿 ⇒ 未命中（可評估）；assistant 文字區塊與 user 記錄內的字串**不計**（只量工具呼叫）；本檢查只量不阻擋（D）。(c) **證據入帳**（AC-SI-21-1）：每筆 `rec` 含指令（`cmd`）、rc、輸出摘錄座標（`out_sha256`、`out_bytes`、`tail`）、母體數（`n_pop`）；執行者與時間在事件的 `by` 與 `t`（帶 offset）；轉述他包者標 `[他包回報]`、主控親跑後才升格為「已驗證」屬流程型（SOP，AC-221-2）；稽核靠「同指令於同 base 沙盒重跑」（QA 動作）。

*E. 晉升、回滾與 SUSPENDED（FR-SI-16、17；PRD §9.3 `promote`／`rollback` 列、§9.4）*

- **R91 `promote`（`promote.py`；rw）**：前置（依序判；碼）：`UNATTENDED-REFUSED`（先於其餘）；`PROP-NOT-FOUND`；`STATE-NOT-VERIFIED`（態不是 `verified`）；`ROUTE-HANDOFF`；`NO-PROMOTE-DEC`（事件帳本中沒有晚於最近一筆 `app.promote`〔若有〕的 `dec(promote)`；**以事件掃描判、不依重放合法與否**）；`PROMOTE-FORM-MISMATCH`（該筆 `dec(promote)` 的式與當下 verdict 不符：`PASS` 配 `flags` 含 `unverified_ack`、`NE` 配無 `flags`；`FAIL` 一律不收；同樣以事件掃描判，故手寫的 FAIL 態或式不符的 DEC 回報本碼、而不是 `NO-PROMOTE-DEC`；§7.1 ⚖ 26）；**`DEC-VERIFY-FAILED`、`TRANSCRIPT-UNAVAILABLE`、`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`**（對該 PROP 的 `approve` 與 `promote` 兩筆 DEC 以 `verify_dec` 回查；任一不符，或因逐字稿、稽核檔、金鑰取不到而無法回查，**拒絕，fail-closed**；晉升須在持有該逐字稿的機器上進行）；`DIGEST-MISMATCH`（自 `rN.patch`、`rN.md` 重算的 digest 不同於 PROP 事件 digest 或兩筆 DEC 的 `digest`）；`PROMOTE-PREMISE-ROLLBACK`、`PROMOTE-PREMISE-TOUCHED`（最近一筆 `app.sandbox` 的 `rollback_ok`、`touched_ok` 不為 `true`；在寫主工作樹前再驗一次，不依賴入帳時的把關）；**`NON-EVOLVABLE-NOW`**（以**當下** `params.json`〔含當下 LATEST，`lib.sdd_latest` 現查；解析失敗＝整個 `AISDLC_SDD_v*/**` 視為凍結〕重新解析 `rN.patch` 並重驗全部路徑——`non_evolvable_globs`、合法根、`spec_body_globs`、別名形態，與 P1 R51、R52 同一函式；任一命中即拒絕並改走轉交、不寫事件，AC-SI-07-3）；`MEMORY-DIR-MISSING`；`PREIMAGE-MISMATCH`（M 類：對 `--memory-dir` 目標檔先跑 `git -c core.autocrlf=false apply --check`，失敗⇒不套用、印可貼入的 OBS 草稿列並要求重新上卡）；`APPLY-FAILED`（非 M 類對主工作樹的 `git apply --check` 失敗）。通過後：`git -c core.autocrlf=false apply <rN.patch>`（主工作樹，cwd＝repo 根；M 類改對 `--memory-dir`，以 `memory/` 為邏輯根——patch 路徑 `memory/<檔>` 對映 `<memory-dir>/<檔>`，本檔類推，§7.1 ⚖ 23）；算 `pre_sha256`（套用前）與 `post_sha256`（套用後）＝`touched` 路徑的 LF 正規化式 manifest（R84；M 類路徑取 `memory/<檔>` 邏輯名）；鎖內重驗並追加 `app.promote`（`head_sha`＝當下 `git rev-parse HEAD`、`unverified_ack`＝所消費 `dec(promote)` 的 `flags` 是否含 `unverified_ack`）。**不 commit**（HEAD 與 `git log` 不變；`git status --porcelain` 只多 `touched` 路徑的變更；commit 由主控走一般流程，訊息引 DEC-ID）。套用失敗＝零變更（`git apply` 全有或全無）。M 類以逐行 patch 套用、不整檔還原（harness 可能併發自寫索引）。
- **R92 `rollback`（`promote.py`）**：前置（碼）：`UNATTENDED-REFUSED`；`PROP-NOT-FOUND`；`STATE-NOT-PROMOTED`（態不是 `promoted`、`measuring`、`closed`）；`NO-ROLLBACK-DEC`（沒有未被消費的 `dec(rollback)`）；`DEC-VERIFY-FAILED`、`TRANSCRIPT-UNAVAILABLE`、`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`（對該 `rollback` DEC 回查，fail-closed）；`TREE-CHANGED`（`touched` 路徑現況的 manifest 不等於最近一筆 `app.promote` 的 `post_sha256`：樹已被他處改動，改人工處理）；`MEMORY-DIR-MISSING`。通過後 `git -c core.autocrlf=false apply -R <rN.patch>`，結果 manifest 須等於該 `app.promote` 的 `pre_sha256`（逐位元還原）；不符＝把剛套用的反向 patch 還原回去（零變更）並 rc 1 `ROLLBACK-NOT-EXACT`；成功追加 `app.rollback`（`pre_sha256`＝套用前現況、`post_sha256`＝還原後）。PROP 狀態不變；不 commit。
- **R93 SUSPENDED 與 `resume`（FR-SI-17；AC-SI-17-2）**：SUSPENDED 的折疊沿 P1 R35（連續 `stop_after_bad` 個壞窗）；SUSPENDED 期間 `prop-new` 與 `prop-revise` 拒收（碼 `SUSPENDED`，P1 已實作，本檔以 AT 重釘）；唯一恢復路徑＝`dec(resume)`：`decide <RUN-SI-N> --kind resume …`，其 RUN 須等於折疊出的 SUSPENDED 所在運轉（`RUN-MISMATCH`，防舊回覆重播），恢復後 `prop-new` 重新受理；迴圈與子代理不得自動恢復、自行重試（沒有任何動詞在無 `dec(resume)` 下清除 SUSPENDED）。**本迴圈不讀寫 FSM 狀態檔、不恢復任何 FSM 鍵**：`tools/lib/selfimproving/` 全部原始碼不含 `FSM-STATE`、`fsm_runtime`、`resume-from-escalation` 字樣（邊界型 P；以靜態掃描釘住結構，不得讀成「被擋」）。

*F. Console 載體的根層半與 `check`／`status`／`export` 的擴充（FR-SI-33、35 的根層半；PRD §9.1 C21、§9.2〈Console 稽核 JSON〉、§9.3；Console 側的 RBAC、白名單、Bridge 權杖、DB 稽核表屬 AgentConsole 的另一份 TCS）*

- **R94 Console 稽核檔與 HMAC（`consoleaudit.py`；ro）**：檔＝`<si>/console_audit/<audit_ref>.json`（UTF-8 無 BOM、單一 JSON 物件；CLI 只讀、絕不寫）；外層鍵恰 `schema_rev`（整數 1）、`kind`（`decide`、`obs-add`、`obs-close`）、`audit_ref`（UUID）、`subject`（字串或 `null`：`decide`＝`PROP-SI-N`〔`resume` 為 `RUN-SI-N`〕、`obs-close`＝`OBS-SI-N`、`obs-add`＝`null`）、`body`（**字串**：JSON 物件文字）、`key_id`（8 位小寫 hex）、`mac`（64 位小寫 hex）。**簽章對象＝`body` 字串的 UTF-8 位元組、不重新序列化**：`mac`＝`HMAC-SHA256(金鑰位元組, body 的 UTF-8 位元組)` 的小寫 hex；金鑰＝環境變數字串的 UTF-8 位元組（不做 base64 解碼）；金鑰環 `AUTOSDD_SI_AUDIT_KEY`＝逗號分隔的金鑰字串（各自去前後空白、空項略過；全為空項＝環為空＝`AUDIT-KEY-MISSING`）、依 `key_id`（金鑰位元組之 sha256 的前 8 碼 hex）選用。**驗證順序與碼（皆 rc 1）**：檔不存在＝`AUDIT-FILE-MISSING`；外層 schema 不合（鍵集合、型別、`schema_rev`）＝`AUDIT-SCHEMA`；`body` 不是 JSON 物件＝`AUDIT-BODY-INVALID`（先於其後各項，因其後各項都要讀 `body`）；`audit_ref` 在檔名、外層、`body` 三處須相等（`AUDIT-REF-MISMATCH`；`body` 缺 `audit_ref` 視為不相等）；外層與 `body` 的 `kind` 須相等且屬三值（`AUDIT-KIND-MISMATCH`）；`user` 合 `^[A-Za-z0-9_.-]{1,64}$`（`AUDIT-USER-FORMAT`；含 `;`、`=` 者必拒，因帳號名會進 OBS 標記欄；**缺鍵視同值不合**：缺 `user`＝`AUDIT-USER-FORMAT`、缺 `role`＝`ROLE-NOT-ADMIN`、缺 `time`＝`AUDIT-TIME-FORMAT`）；`role` 恆為 `ADMIN`（`ROLE-NOT-ADMIN`）；`time` 合 `YYYY-MM-DDTHH:MM:SS±HH:MM`（秒精度、明示 offset、**不收 `Z`**；`AUDIT-TIME-FORMAT`）；外層 `subject` 與 `body.prop`（`resume` 為 `body.run`；`obs-close` 為 `body.obs_id`；`obs-add` 須為 `null`）相等（`AUDIT-SUBJECT-MISMATCH`）；金鑰環未設或空＝`AUDIT-KEY-MISSING`（**入帳不是回查，不得降為 NE**；`check` 與 `promote` 的回查路徑則視為 NE，R95、R98）；`key_id` 不在金鑰環＝`AUDIT-KEY-UNKNOWN`；`mac` 不符＝`AUDIT-MAC-MISMATCH`。`audit_sha256`＝該檔位元組的 `sha256:`。**金鑰衛生**：CLI 的任何輸出（stdout、stderr、OBS 草稿列、事件）絕不含金鑰位元組、金鑰環字串，或其任何 ≥8 字元的子字串（AT 斷言）。**`body` 欄位表**（鍵序依下列、選用鍵缺席時不出現）：共通 `schema_rev`（1）、`audit_ref`、`kind`、`user`、`role`、`time`；`decide`＝`prop`（`resume` 無）或 `run`（僅 `resume`）、`digest`（`resume` 無）、`dkind`、`reason_class`（`reject`、`decline-promote`、`return` 必備）、`reason`（需理由的 dkind 必備）、`flags`（字串陣列，可空）；`obs-add`＝`context`、`symptom`、`evidence`（皆非空字串）、`category`、`severity`、`face`、`exposure`（`face` 為 `守衛` 必備、其餘不得有）、`external_derived`（布林）、`marks_extra`（選用物件，只准 `rel`、`reopens`、`根因` 三鍵）、`corrects`（選用，被更正的 `OBS-SI-N`）；`obs-close`＝`obs_id`、`disposition`。**跨語言測試向量**（Java 側 P2b 以同一組逐字相同；§5.5 逐字列出）：固定金鑰、固定 `body` 字串與預期 `mac`；AT-233-1-2 以標準庫 `hmac` 加 `hashlib` 重算須逐字相等，AT-233-1-E-3 的負控（body 改一個字元、換金鑰、`time` 改 `Z`）各自轉紅。
- **R95 `decide --carrier console --audit-ref <UUID>`（FR-SI-33 的根層半）**：前置（碼；rc 1）：`UNATTENDED-REFUSED`；R94 的全部驗證碼；`AUDIT-REF-REUSED`（同一 `audit_ref` 已有任一 `dec`、`obs.add`、`obs.close` 事件，或 OBS 列標記 `audit_ref` 相同——跨 kind 計）；`AUDIT-KIND-MISMATCH`（稽核檔 `kind` 不是 `decide`）；`AUDIT-SUBJECT-MISMATCH`（位置參數 ID 不等於稽核 `subject`）；`STALE-CARD`（`body.digest` 不等於 PROP 當下 digest）；其後與逐字稿載體同一組狀態層前提（R80 (e)：`PRECONDITION-STATE`、`ROUTE-HANDOFF`、`PROMOTE-FORM-MISMATCH`〔Console 以 `flags` 表達：`promote` 的 `flags` 含 `unverified_ack` ⇔ NE 式〕、`PROMOTE-PREMISE-*`、`NOT-IN-COOLDOWN`、`RUN-MISMATCH`、理由類；`dkind` 取自 `body.dkind`、不收 `--kind`）。**不驗 ③ 卡面送達與 `CARD-NOT-ISSUED`**（Console 路徑沒有逐字稿；卡面由 Console 頁逐字顯示 `si card` 輸出，AC-SI-32-1）。成功追加 `dec`：`carrier` 為 `console`、`audit_ref`、`audit_sha256`、`key_id`、`decider`＝`body.user`、`decided_at`＝`body.time`、`digest`（綁卡面的 dkind）、`dkind`、`reason`／`reason_class`／`flags`（取自 `body`）；無 `quote`、`sid`、`line`、`card_seq`。**回查**（`check` 的 `events.dec_console`、`promote`）：`verify_dec` 的 `console` 分支對已存 `dec` 重驗——稽核檔存在、`audit_sha256` 等於檔位元組雜湊、`body` 與事件的 `prop`（或 `run`）、`digest`、`dkind`、`decider`、`decided_at`、`reason`、`reason_class`、`flags` 逐欄相符，金鑰在場再驗 HMAC；不符＝`CONSOLE-AUDIT-MISMATCH`（FAIL）；稽核檔不存在（他機）＝`CONSOLE-AUDIT-MISSING`（NE nonblocking；`promote` 因無法回查而拒）；金鑰環缺或無對應 `key_id`＝`CONSOLE-KEY-MISSING`（NE nonblocking；`promote` 拒，fail-closed）。
- **R96 `obs-add`（FR-SI-35；`obsrows.py` ro、`obswrite.py` rw）**：(a) **入帳 `obs-add --carrier console --audit-ref <UUID>` 前置**（碼）：`UNATTENDED-REFUSED`；R94 驗證碼；`AUDIT-KIND-MISMATCH`（`kind` 不是 `obs-add`）；`AUDIT-REF-REUSED`；本文欄位規則——`PIPE-IN-FIELD`（任一字串欄含 `|`）、`FIELD-EMPTY`、`ENUM-CATEGORY`、`ENUM-SEVERITY`、`FACE-INVALID`、`EXPOSURE-REQUIRED`（`face` 為 `守衛` 而無 `exposure`）、`EXPOSURE-UNEXPECTED`（`face` 非 `守衛` 而有 `exposure`）、`MARKS-EXTRA-KEY`（`marks_extra` 含 `rel`、`reopens`、`根因` 以外的鍵；`src` 一律拒）、`REL-CONFLICT`（有 `corrects` 而 `marks_extra` 又含 `rel`）、`CORRECTS-NOT-FOUND`（被更正的 ID 不在 OBS 帳本含封存檔）；組列後自驗＝`rows.evaluate_rows` 對僅含該列的合成帳本（`src_ids` 為 `None`）零 `fail` finding，否則拒收並帶各 finding 碼（含 `ROW-BYTES-OVER`：列位元組數大於 `row_max_bytes`，**700 放行、701 拒收**）。(b) **列的組成**（九欄、鍵序固定，使位元組可重現）：`ID`＝鎖內重讀帳本後 `ledger.max_valid_id` 加 1（`OBS-SI-NNN`，至少三位）；`時間`＝`body.time` 轉成 `YYYY-MM-DD HH:MM ±HH:MM`（**保留其 offset、丟秒**；人不可輸入）；`情境`、`症狀`、`證據座標` 取 `context`、`symptom`、`evidence`；`分類`、`嚴重度` 取 `category`、`severity`；`處置` 固定 `open`；`標記`＝`面=<face>`、（有才帶）`暴露=<exposure>`、（真才帶）`外部衍生=是`、（有 `corrects` 者）`rel=corrects:<ID>`、`marks_extra`（鍵序 `rel`、`reopens`、`根因`）、`來源=人`、`回報者=<user>`、`carrier=console`、`audit_ref=<UUID>`，以 `;` 連接。(c) **寫入**：於事件帳本寫入鎖內「重讀 OBS 帳本末列配號 → 追加該列於表尾（最後一個資料列之後）→ 追加 `obs.add` 事件」（先列後事件）；寫入工作樹、**不 commit**；任一步失敗＝回退（`State.cleanups`）：事件追加失敗時，僅在帳本檔長度仍等於追加後長度時還原（截回追加前位元組），否則不動並於 stderr 印 `OBS-ORPHAN`（由 `check` 的 `obs.console_audit` 標紅承接）。**函式級入口（測試 seam，§5.6）**：`obswrite.add_console_row(repo, audit_ref, by)` 回 `(rc, out)`，CLI 動詞只是它的薄殼；執行緒競態測試直接呼叫它（避開 `contextlib.redirect_stdout` 的行程級衝突）；`obswrite.close_console_row(repo, audit_ref, by)` 同形。(d) **`--dry-run --body-file <路徑或 ->`**：唯讀預檢——只走 `ro` 模組（行程不載入 `obswrite`、`runner`、`fetch`、`research`；不取鎖、不需家目錄與金鑰）；`-` 讀 stdin 的 `body` JSON 文字；`time` 缺則以現在時刻預覽；rc 0＝會被收、1＝會被拒（皆印）；`--json` 時 stdout 為 `{"ok": <bool>, "row": "<列>", "row_bytes": <n>, "row_max_bytes": <n>, "findings": [{"code", "detail"}…]}`（與 Bridge `POST /si/observations:validate` 的 200 回應同形；`ok` 為 `false` 時 rc 為 1）；文字形態為 `dry-run ok` 或 `dry-run reject`、`row: <列>`、`row_bytes=<n> row_max_bytes=<n>` 與各 finding 一行；**零寫入**（repo 與家目錄位元組不變）。
- **R97 `obs-close`（FR-SI-35；AC-SI-04-3 唯一合法的原地改寫）**：前置（碼；rc 1）：`UNATTENDED-REFUSED`；R94 驗證碼；`AUDIT-KIND-MISMATCH`（`kind` 不是 `obs-close`）；`AUDIT-REF-REUSED`；`OBS-NOT-FOUND`（`obs_id` 不在 OBS 主帳本）、`OBS-ARCHIVED`（該列只在封存檔）；`NOT-OPEN`（該列處置目前不是恰為 `open`）；`DISPOSITION-INVALID`（`disposition` 首詞不屬終值枚舉：`fixed@<sha>`、`DEF-<id>`、`deferred`、`retired`、`decided`、`merged@OBS-SI-N`、`proposed@PROP-SI-N`；`open` 不是終值）、`DISPOSITION-TEXT-MISSING`（`deferred`、`retired`、`decided` 缺附加文字，或 `retired` 缺座標，沿 P0 `DISP-TEXT-MISSING`）、`PIPE-IN-FIELD`（`disposition` 含 `|`）；改寫後的列以 `rows.evaluate_rows` 自驗零 `fail`（含 `ROW-BYTES-OVER`）。**改寫**：鎖內重讀帳本並與預檢時讀到的位元組比雜湊，不符＝rc 1 `LEDGER-CHANGED`（零殘留；測試以 `obswrite.PAUSE_HOOK`〔形態同 `evwrite.PAUSE_HOOK`，在預檢之後、鎖內重讀之前呼叫〕改動帳本製造）；**只改該列第 8 欄（處置），其餘位元組逐字不變**（含該列其他欄、其他列、檔頭、行尾）；同目錄 tmp 檔寫完、`flush`、`os.fsync` 後 `os.replace` 換入（沿 `tools/lib/quota_availability.py` 的 R7 原子寫入骨架）；寫 tmp 或 `os.replace` 失敗＝rc 1、帳本未變、tmp 於 `finally` 刪除（零殘留）、**單次嘗試不重試**（套件禁 `time.sleep`）；成功於同一把鎖內追加 `obs.close`；其後 `check` 的 `history.row_mutated` 視 `open`→終值為合法（P0 `history._allowed` 既有語意）。無 DELETE、無改號（AC-SI-35-3）：OBS 寫入動詞只有 `obs-add` 與 `obs-close` 兩個。
- **R98 `check` 的 P2 追加項（PRD §9.3 `check` 列）**：項目 ID 與順序（接在 P1 的 `research.sources` 之後；P0 的 21 項與 P1 的 7 項的 id、順序、語意、碼原樣）：`events.dec_quote`、`events.dec_console`、`events.verdict`、`obs.console_audit`，故首行 `si-check rows=<N> items=32`。載體缺席（事件帳本或 OBS 帳本不存在）一律 nonblocking NE `CARRIER-NOT-ESTABLISHED`（P0 基線 repo 的 rc 與 overall 不變）。`_NONBLOCKING` 增三碼：`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`、`TRANSCRIPT-UNAVAILABLE`。**`CHECK_RULES_REV` 由 2 增為 3**（判準指紋的 `check_rules_rev` 部分隨之改變）。(a) `events.dec_quote`：對每筆 `carrier` 缺或為 `transcript` 的 `dec`，以 `verify_dec` 重跑 ①～③（R79）；`fail`⇒FAIL（subject 為 `seq=<N>`，碼為回查碼）；逐字稿取不到⇒nonblocking NE `TRANSCRIPT-UNAVAILABLE`（不判紅）；無 `dec`⇒PASS。(b) `events.dec_console`：對每筆 `carrier` 為 `console` 的 `dec` 回查（R95）。(c) `events.verdict`：對每筆 `app.verify`，以 R89 的 `verdict_of` 由記錄欄位（與同 `(prop, rev)` 最近一筆 `app.sandbox`、`heldout.freeze`、`min_heldout`）重算：(i) 重算 verdict 不等於記錄 verdict；(ii) 重算出的 `reasons`（可由欄位導出的碼）不是記錄 `reasons` 的子集；(iii) 記錄 `reasons` 含 `HELDOUT-EXPOSED`、`EXPOSURE-UNKNOWN`、`PROBE-TIMEOUT` 以外而無法由欄位導出的碼；(iv) ⓪ 成立而 `probes_n` 不為 0 或 `verify_sha256` 不為 `null`——四者皆 FAIL `VERDICT-MISMATCH`。**欄位全部自洽的偽 PASS 不被偵測**（誠實劃界，PRD §9.4）。(d) `obs.console_audit`：每個帶 `carrier=console` 標記的 OBS 列須有一筆 `obs` 指向該列且 `audit_ref` 相符的 `obs.add`（缺＝FAIL `CONSOLE-EVENT-MISSING`）；每筆 `obs.close` 須指向處置已非 `open` 的列（否則 FAIL `CONSOLE-CLOSE-NOT-APPLIED`）；稽核檔在場時再驗 `audit_sha256`、`body` 與列、事件逐欄相符（時間、情境、症狀、座標、分類、嚴重度、面、暴露、外部衍生、帳號名；`obs-close` 的 `disposition` 與該列處置欄逐字相等）與 HMAC（不符＝FAIL `CONSOLE-AUDIT-MISMATCH`）；稽核檔不在場＝nonblocking NE `CONSOLE-AUDIT-MISSING`（**不是零筆通過**）；金鑰環缺或無對應 `key_id`＝nonblocking NE `CONSOLE-KEY-MISSING`；無任何 `carrier=console` 的列與 `obs.*` 事件⇒PASS。(e) `events.research` 的 `helmsman` 回查：對每筆 `research.skip`（`reason` 為 `helmsman`）以 `verify_human_ref(sid, line)` 只驗 ①（記錄是兩種真人載體之一、文字非空）：失敗⇒FAIL `HELMSMAN-REF-INVALID`；逐字稿取不到⇒nonblocking NE `TRANSCRIPT-UNAVAILABLE`；免掃不是 §7.2 決定，不驗 ②③。
- **R99 `status` 與 `export` 的 P2 擴充（`status.py`、`export.py`）**：(a) `status` 物件於既有 13 鍵（次序與值不變）**之後**附加末鍵 `console_pending`：`{"status": "read", "count": <n>, "items": [{"audit_ref", "kind"}…]}`（`items` 依 `audit_ref` 的字串序）——`<si>/console_audit/` 內檔名合 `<uuid>.json` 且**尚無對應事件**（`dec`、`obs.add`、`obs.close` 任一的 `audit_ref` 相同）者；檔內容無法解析或 `kind` 不在三值者 `kind` 印 `null`、仍列出（不隱藏待入帳檔）；該目錄不存在或讀不到＝`{"status": "NOT-EVALUABLE", "reason": "home-unavailable"}`（不得印成空清單）；資訊欄、不接閘門；`status` 只列目錄清單與解析 `kind`、不輸出稽核檔其他內容。文字形態加一行 `console_pending: <n>`（NOT-EVALUABLE 時 `console_pending: NOT-EVALUABLE（<reason>）`）。(b) **`export --kind status` 的 `items[0]` 同一鍵，但值恆為 `{"status": "NOT-EVALUABLE", "reason": "export-reads-no-home"}`**：PRD §9.2 要求 `export` 不讀、不印家目錄任何檔（哨兵測試），與 §9.3「`items[0]` 同一欄」字面衝突；本檔取前者（§7.1 ⚖ 16），鍵仍在、值明示量不到，Console 以 `si_console_writes` 自行對帳。(c) `export --kind observations` 的每個九欄 OBS 項加 `buckets[]`（置於 `marks_kv` 與 `line` 之後的末鍵）：對該列證據座標格的每個**路徑片段**（`path`、`file`、`dir` 三形態的**原文**：保留大小寫、去結尾行號、`\\` 換 `/`；**不 `casefold`**——`rows` 另增不 `casefold` 的取法 `path_fragments(cell)`，OBS-SI-237）呼叫 `scan.bucket_of`（同一函式，前端不重算），結果依 `scan.BUCKETS` 次序去重、`未分類` 排最後；零個路徑片段＝`["未分類"]`；欄數非 9 的壞列（`{line, raw, valid: false}`）無 `buckets`；`schema_rev` 維持 1。

*G. 殘留收口、資料面小項與元層（DEF-200-559；P1 TCS 勘誤三、四的殘留；OBS-SI-210、211、214、217、218、237；PRD §8.1 P2 出口 (f)、(g)、§9.4）*

- **R100 `apply_lock` 的 Windows 刪除待決（DEF-200-559；OBS-SI-210、211；`tools/lib/apply_lock.py`；PRD §9.4）**：現碼三處只認 `FileExistsError`／`FileNotFoundError`（`_try_acquire`、`_reap_if_stale` 內的 `unlink`、釋放時的 `unlink`；**函式名一律用碼內真名 `_try_acquire`**，原缺陷列與 P1 的 SCG-4 報告沿用的 `_try_create` 在碼內不存在）。成因（Windows 語意的推論，由下列替身測試承接）：Windows 對「被另一行程開著的檔」的兩種拒絕——**刪除待決**（已刪、但對方的控制代碼未關，此時重建同名檔拋 `PermissionError`）與**共享違規**（`unlink` 時對方開著而未授 `FILE_SHARE_DELETE`，例如 `_read_holder` 正在讀鎖檔）——在 Python 都映成 `PermissionError`（errno 13）；POSIX 兩者皆無。修法（消除成因類別、不壓制）：(1) `_try_acquire`：`os.open` 拋 `PermissionError` 視同「忙碌」，納入既有有界重試（仍受 `timeout` 總時限）；**逾時改拋最後一次的原始例外（`PermissionError`，不是 `LockBusyError`）**，使真正的「目錄不可寫」不被誤報為「別的行程持有」；`FileExistsError` 的逾時行為（`LockBusyError` 加持鎖者資訊）不變。(2) `_reap_if_stale` 的 `unlink` 遇 `PermissionError`＝「這輪沒收成」，同 `FileNotFoundError` 的處理（不是錯誤，進入下一輪有界重試）。(3) 釋放的 `unlink` 遇 `PermissionError`＝有界重試：初次嘗試之後**最多再重試 `RELEASE_RETRIES` 次**（模組常數，初值 5，共最多 `RELEASE_RETRIES` 加 1 次嘗試；每次重試之前等待 `poll_interval`；初值未校準，不得無界）；**用盡後不改 rc、不拋例外**，只印警告到 stderr（含鎖檔路徑與原始例外類名）並讓鎖檔殘留、交陳舊回收——釋放發生在事件已追加之後，若此處拋例外，呼叫端 `writeverbs.append` 會回 rc 3 並印「帳本未變動」（失實），重送即重複寫入。(4) 公開面不變：`acquire(lock_path, timeout, stale_after, poll_interval=0.2)`、`LockBusyError`；`tools/archive_apply_locked.py` 只接 `LockBusyError` 的行為不變。(5) 替身測試任一平台可重現、不靠真實競態：以 `mock.patch` 令 `os.open` 與 `Path.unlink` 依序拋 `PermissionError`；既有 `tools/tests/test_apply_lock.py` 全綠。(6) 修法後釋放失敗不再經 `writeverbs.append` 的 `except OSError`（AT-240-8-E-4 於 `evwrite` 層斷言：釋放耗盡時事件已追加、呼叫端回 0 而非 3、輸出不含「帳本未變動」）。
- **R101 來源表 host 僅限 ASCII（PRD AC-SI-30-2；P1 TCS 勘誤三、四留下的二擇一，主控 2026-10-21 定案為拒收；`sources.py`；對 P1 R43 的擴充）**：`validate_table`（`check` 的 `research.sources` 與 `research --fetch` 預檢共用的唯一函式）對每個來源 `url` 的 host：含任何非 ASCII 字元（`ord(c) > 127`，含全形數字與全形字母、U+3000、全形句點），或任一 label（以 `.` 切開）以 `xn--` 起頭（**不分大小寫**，`XN--`、`Xn--` 亦是）⇒ 沿用既有碼 `SRC-URL-HOST`（detail 加註「非 ASCII 或 IDNA 形態」）。**不做正規化後比對**：`https://１２７.0.0.1/x` 因此在表驗證即紅（以 ASCII 規則判，不是因它解析到 loopback）。`research --fetch` 發出任何請求之前先過此驗證，不合＝整次 rc 1、不抓、不寫事件、零連線（以 loopback 夾具的請求計數斷言為 0）。重導向目標的 host 本就須在來源表內（P1 R58），不另判。既有真來源表的 host 皆為 ASCII，`check` 對它仍 PASS（AT 唯讀斷言）。誠實劃界：只判 host 字串、不證明可達；host 含底線等其他 ASCII 怪形態不在本判準內。
- **R102 AT 序號與 `-k` 錨定規則的可重跑檢查（P1 TCS 勘誤四殘留；PRD §8.1 P2 出口 (f)；AC-240-9）**：規則本文見〈AC 編號規則〉第 4 點。檢查（`tools/tests/test_selfimproving_p2_meta.py`）：(a) 自本檔 §2 解析每個 AT 標頭的「測試檔」與「判定指令」，取 `-k` 後的值；(b) 對涉及的每個測試檔以 `python -m pytest --collect-only -q -p no:xdist -o addopts= <檔>` 收集測試函式名；(c) 對每個 AT：其 `-k` 值以**不分大小寫的子字串**比對該檔收集到的**節點 id 全字串**（含檔名、類別名與函式名，沿 pytest `-k` 對各層名稱的比對），命中數須**恰為 1**；(d) 每個 AT 的 `-k` 值須以 `_` 結尾，且去掉結尾底線後等於其 AT 底線形；(e) 同一 AC 的 AT 序號 ≥10 者須為兩位（`E_10` 起），且其個位前綴者的 `-k`（例如個位序號的錨定名）不得命中它；(f) 合成自證：以兩個函式名（底線形 `AT_999_1_E_1` 接 slug、`AT_999_1_E_10` 接 slug）組成的合成測試檔，非錨定的 `-k` 值命中 2（紅）、錨定的命中 1（綠）。判準不讀 P1 TCS 的 AT（P1 沒有兩位序號）。
- **R103 `scan` 的資訊型草稿列與來源行（OBS-SI-218；對 P1 R59 (b)(c) 的擴充；`scan.py`、`rows.draft_row`）**：(a) `observations` 證據來源的**模組桶候選列**（「`<桶> 窗內有 <k> 個 commit 觸及…`」）是計數資訊、不是缺陷：其草稿列改為分類 `process`、嚴重度 `P4`、處置 `decided：僅計數`（其餘欄與標記沿 R59 (c)：`面=流程;來源=工具;回報者=scan`）；`defects` 來源的候選列（缺陷帳本新立 P≤2 未結列）維持 `bug`／`P3`／`open`（那是真候選）。`rows.draft_row` 增選用參數（分類、嚴重度、處置），預設仍 `bug`／`P3`／`open`——**P1 的拒收草稿列（R28 (d)）與 `check` 草稿列不變**。草稿列仍須自身通過 P0 R9～R17（`decided：僅計數` 滿足 `DISP-TEXT-MISSING` 的附加文字要求）、≤ `row_max_bytes`。(b) **來源行文字**：`observations`、`build_reports`、`probe_outputs` 三個「只計數、未解析內容」的來源，文字形態由 `source <id> 讀到 <N> 筆` 改為 `source <id> 計 <N> 筆（未解析內容）`；`defects`（逐列解析嚴重度與狀態）與 `event_ledger`（折疊）維持 `讀到 <N> 筆`；量不到的 `source <id> 量不到：<原因>` 不變。`--json` 的 `sources[]` 鍵集合與值**不變**（只改文字形態，P1 的 JSON 斷言不受影響）。(c) `status`（`candidates`／`no-event`）、`buckets` 計數與零候選規則（P1 R59 (e)）不變：資訊型草稿列仍是候選列、照常計入 `candidates` 與 `buckets`。
- **R104 `ref.carrier_families` 的存在性判（OBS-SI-217；P1 TCS ⚖ 2 的「P1 修訂時改查事件帳本」於此落實；取代 P1 R36 (h)；`refs.py`）**：(a) **家族切分**：ATT、PROP、RUN 三族在「載體在場」時判存在；DEC、APP、MEA 三族維持 P1 語意（任何提及印 nonblocking NE `CARRIER-NOT-ESTABLISHED`，detail 的 `families=` 只列這三族中有提及者）。載體在場＝事件帳本檔存在且可解析至少一行事件；不在場＝全部家族維持 P1 語意（P0 基線 repo 的 rc 與 overall 不變）。(b) **引用面**（本檔類推，§7.1 ⚖ 17）：只判**指標形態的引用**，不判散文提及——(i) OBS 帳本（含封存檔）各列處置欄的 `proposed@PROP-SI-N`：N 不是事件帳本某筆 `prop` 事件的 `id` ⇒ **warn** finding `FAMILY-REF-DANGLING`（subject 為該 OBS 列 ID；項目狀態不變）。只到 warn 的緣由：OBS 帳本含事件帳本建立之前的歷史列與夾具的合成指標——P1 baseline 夾具的第 8 列（`base_rows`）處置就是 `proposed@` 接一個執行期組出的 PROP 號，該號在任何 P1 測試的事件帳本裡都不存在（本檔作者以 P1 夾具建 baseline、對它 `git grep` 家族提及，得到唯一一筆即該列）；判 FAIL 會使 P1 的全部 AT 在事件帳本在場時整批轉紅，而歷史列的懸空指標不是迴圈機器狀態的完整性問題（§7.1 ⚖ 17）；(ii) 事件帳本內各事件的 ID 型欄位（`dec.prop`、`dec.run`、`app.*.prop`、`attr.att`、`research.*.run`、`prop.run`、`card.prop` 等）須指向事件帳本內已定義的 ATT／PROP／RUN（與 `fold` 的 `TRANSITION-ORPHAN` 重疊，本項只重報、不增判級，碼 `FAMILY-REF-DANGLING`，subject 為 `seq=<N>`）；(iii) `SelfImproving_Proposals/` 之下的目錄名 `PROP-SI-N` 須為某 `prop` 事件的 `id`（碼 `PROP-DIR-ORPHAN`）。(ii)(iii) 不合＝FAIL；(i) 不合＝warn。(c) **不判**：OBS 帳本列的散文提及（症狀、處置文字、證據座標內非 `proposed@` 的 `PROP-SI-N`、`RUN-SI-N`）、規格與報告類文件（PRD、TCS、SOP、審查報告、RTM）、程式碼與測試——這些以示意編號舉例（PRD 的卡面範例）或指向尚未開的運轉（OBS 列的 `RUN-SI-` 前向引用），判它們會製造大批假紅（本檔作者現查，§7.1 ⚖ 17）。(d) 真 repo 上 `check` 對本項維持 rc 0（V2）。
- **R105 能力登記第四類 `exec`（PRD §9.4〈能力登記與純度判準〉P2 擴充；`tools/tests/test_selfimproving_capability.py`）**：類別增為四種：`ro`、`rw`、`net`、`exec`（可 import `subprocess`＝子行程出口；可寫 repo 內 `docs/` 與家目錄；零網路）。判準：① 套件內每個 `*.py` 都在登記表（新檔未登記＝紅）；② 逐檔掃描符合所登類別——`subprocess` 字樣的規則改為「只准 `git.py`（`ro`）與 `runner.py`（`exec`）」，`exec` 檔同樣不得 import 網路模組；**②′ 任何相對 import `runner` 的檔須登記為 `exec`**（AST 掃每個 `*.py` 的相對 import；`ro`、`rw`、`net` 檔 import `runner`＝紅）；③ `check.py`、`status.py`、`scan.py`、`export.py`、`card.py` 的相對 import 閉包 ⊆ `ro`（P2 的 `decverify`、`verdict`、`decheck`、`transcript`、`decgrammar`、`consoleaudit`、`cooldown`、`obsrows`、`heldout`、`manifest` 因此必須是 `ro`）；④ 全套件禁字樣（`time.sleep`、`while True`、`os.fork`、`signal.alarm` 等）對 `runner.py` 照樣適用。`CAPABILITY` 鍵數與分類計數斷言由 24 鍵（19／3／2）改為 **40 鍵（29 `ro`／7 `rw`／2 `net`／2 `exec`）**；`exec` 類恰為 `runner.py` 與 `verify.py`。**平台守衛**：`runner.py` 的 `taskkill` 站點與 `os.killpg` 站點各在 `sys.platform` 守衛作用域內；根層 `tools/tests/test_platform_neutral_paths.py` 的 `TestForeignExecutableArgvIsGuarded`、`TestForeignPlatformApiIsGuarded`、`TestForeignApiVocabularyOnlyGrows` 不因 P2 新增任何 offender 或存量債（兩張債表 `_FOREIGN_EXE_ARGV_DEBT`、`_FOREIGN_API_SCOPE_DEBT` 無 `selfimproving` 條目）。**鐵律五形態靜態掃描**（AC-215-2）：套件內任何 `Git.run(...)` 引數、argv 清單與字串字面，不含 `stash`、`reset`、`checkout`、`clean`、`restore`、`switch`、`worktree` 這幾個 git 子命令詞（以「`git` 之後第一個非旗標位置詞」判；`apply`、`archive`、`status`、`rev-parse`、`log`、`show`、`grep`、`merge-base` 不在其列）。
- **R106 `params.json` 兩新鍵（C5；對 P1 R46 的鍵數擴充）**：`probe_timeout_seconds`（整數 ≥1，初值 600；先例 `AutoClaude/autoclaude/utils/config.py` 的 `step_timeout_seconds`）與 `verify_runs_max`（整數 ≥1，初值 2）加入 `PARAM_SPECS`（型別規則 `int1`），故 `params.json` 為 30 鍵、頂層鍵依位元組序；缺、型別不符或範圍不符＝`PARAM-MISSING`／`PARAM-TYPE`／`PARAM-RANGE`（`params.keys` FAIL）；`sandbox`、`verify`（與 `check` 的 `VERIFY-RUNS-EXCEEDED` 判準）只讀它們需要的鍵，鍵無效＝rc 3 並於 stderr 點名該鍵、**不以預設值頂替**（沿 P0 R5）。`non_evolvable_globs` 與 `spec_body_globs` 不變（AT-240-14-E-1 斷言）。`params.json` 屬不可進化面、由主控與 `PARAM_SPECS` 同 commit 加入。
- **R107 夾具升級與既有測試的同步站點（零退化；D14）**：P2 的完整欄位表使 P1 夾具以最少欄位手寫的 `dec`、`app.*`、`card`、`heldout.freeze` 事件被 `events.validate` 判不合規而退出折疊（`sound()`），故夾具須同步升級；**夾具升級（(a)(b)）本身不改任何 P1 AT 的斷言值；P1 全部 163 個 AT 在 (c) 列出的同步站點改完期望值之後全部維持綠，其餘一字不改**（P1 斷言值的變動只准出現在 (c) 的站點；本輪新增的兩個站點來自 R104 與 R110）。(a) `tools/tests/_selfimproving_fixtures.py`：`dec_ev(n, dkind, **kw)`、`_verify(n, verdict)`、`ev("app.sandbox"…)`、`ev("card"…)`、`ev("app.promote"…)`、`ev("app.rollback"…)`、`ev("heldout.freeze"…)` 的**既有呼叫形態**不變，但產出的事件（經 `compose()` 補欄）須通過 R72 的欄位表：缺鍵以確定性預設補齊（呼叫端傳入的鍵優先），預設值列於 §5.2；P1 夾具 `prop_ev` 的預設 digest `H(4)` 即 `dec` 預設 digest（使 R74 (h) 不誤報）。(b) 新模組 `_selfimproving_p2_fixtures.py`：本檔 §5 列出的建構器（逐字稿、held-out 目錄、沙盒 repo、稽核檔、探針腳本、`make_p2_repo`）；`make_p1_repo` 的 `params.json` 增兩鍵（`probe_timeout_seconds`＝600、`verify_runs_max`＝2，共 30 鍵；P1 其餘鍵值不變）。(c) **需同步的既有 P1 測試站點**（只改下列站點的期望值，其餘一字不動；以函式名定位）：`tools/tests/test_selfimproving_events.py` 的 `test_AT_142_1_1_p1_items_on_p0_baseline_and_after_a_round`（`items=28` 改 `32`；其後半「一輪之後」的 `ref.carrier_families` 由 `NE` 改 `PASS`——R104：事件帳本在場、無 DEC／APP／MEA 提及，baseline 列的 warn 不改狀態）、`test_AT_106_2_E_1_link_rejections`（R110：情境一的第二個案例以 baseline 第 4 列〔處置首詞 `deferred`〕為 `--reopens`，由 `REOPENS-NOT-CLOSED` 改為 rc 0 並寫入一筆 `type` 為 `link` 的 `attr`；該案例移出負控集合、改於 `snap0` 比對之後獨立呼叫並斷言事件帳本恰多該筆 `attr`；其餘四個負控案例與 `snap0` 比對一字不動）、`test_AT_142_2_E_1_p0_negatives_unchanged`（`items=28` 改 `32`；原斷言 `decide` 與 `promote` 為 rc 3 的字串集合改選仍未實作的動詞 `capacity`）、`test_AT_140_1_E_1_unimplemented_verbs_and_reject_grammar`（未實作動詞清單剔除 P2 的六個動詞、只留 `capacity`；頂層 usage 動詞數 13 改 21）、`test_AT_108_4_E_3_weird_events_are_event_type_only` 與 `TestDecFlagsAndConsumedKeys.check_case`（`len(items)` 28 改 32；`dec` 等被消費鍵的型別案例改指 P2 完整欄位表的預期碼）；`tools/tests/test_selfimproving_check.py` 的 `test_AT_001_1_1_baseline_is_green`（`items=28` 改 `32`）、`test_AT_003_1_1_no_resident_mechanism`、`test_AT_030_1_E_1_usage_errors`（未實作動詞改選 `capacity`）；`tools/tests/test_selfimproving_capability.py` 的 `test_AT_143_1_E_2_dynamic_purity_and_forbidden_words`（`len(items)` 28 改 32）與 `CAPABILITY` 登記表及其計數斷言（R105）；P1 的 `export`／`status` 測試中斷言 `status` 物件鍵序為 13 鍵者，改為「前 13 鍵次序不變、其後為 `console_pending`」；`QUOTE-VERIFIER-NOT-ESTABLISHED` warn 的 P1 斷言（`events.transitions`、`events.research`）改為斷言它不再出現；`scan` 的 P1 AT 對 `讀到 N 筆` 的文字斷言對三個計數來源改為 `計 N 筆（未解析內容）`、對模組桶候選列的 `bug`／`P3`／`open` 斷言改為 `process`／`P4`／`decided：僅計數`；`cooldowns[]` 元素的 P1 斷言改容許末鍵 `reason_class`。(d) **夾具自測**：AT-240-1-1 對升級後每個建構器的輸出跑 `events.validate` 零問題；AT-240-14-1 以升級後夾具重放全部 P1 情境表（`sc_close`、`sc_seq`、`sc_legal`、`sc_rev`、`sc_susp`），`events.structure` 為 PASS、`fold` 的狀態與 problems 與 P1 預期相同。
- **R108 Operations SOP〈P2 動詞〉與流程型條文（PRD §8.1 P2 出口 (g)；C.2 #20 (k)；`docs/05_development/SelfImproving_Operations_SOP.md`）**：把 SOP 的〈P2 動詞（待補）〉節定稿為〈P2 動詞〉（刪「待補」字樣與「呼叫它們一律 rc 3」句）：(a) rc 契約表補 `decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`card --issue`、`obs-add`、`obs-close` 各列（含 rc 0／1／3 與下一步；`verify` 列寫明「rc 0 不論 verdict，讀 verdict 不讀 rc」、`sandbox` 列寫明「rc 0 涵蓋 `applied=false`」、`verify` 的 rc 1 列 `VERIFY-RUNS-EXCEEDED` 須升級人工）；(b) 有提案的運轉最小序列續寫：`card --issue` → 貼卡面給掌舵者 → 掌舵者打字決定 → `decide`（`--sid`、`--line` 取自該則發言，**不寫引言、不寫 `--reason`**）→ `heldout-freeze`（凍結者≠提案者，`prop-new` 之後、`sandbox` 之前）→ `sandbox` → `verify`（含 `--mutation`）→ 掌舵者打字晉升（PASS 用前式、NE 用「未驗採納」式）→ `decide --kind promote` → `promote` → 主控 commit（訊息引 DEC-ID）；回滾只在掌舵者打字「回滾」後以 `decide --kind rollback` 加 `rollback` 執行；PowerShell 與 bash 兩形態；(c) Console 載體：`obs-add`、`obs-close`、`decide --carrier console` 由主控在**主機端**單窗口執行（pull），入帳動詞執行期間主控不手編 OBS 帳本；`AUTOSDD_UNATTENDED` 有設時這些動詞一律 rc 1；(d) 〈審查者〉節補：審查者≠提案者、全程唯讀、不自起背景長任務、主依據為外部可重跑訊號（指令 rc、`verify` 的 verdict 與 `verifyK.json`）而不是 LLM 意見，LLM 意見不得單獨把 FAIL 改成 PASS（AC-SI-18-1）；(e) 遇 R-9.6 擋寫或 harness 分類器拒絕（`.claude/**`）**不得以改派子代理或換路徑繞過**，改由符合條件的視窗處理或走轉交（AC-SI-15-3）；(f) 證據條文：驗證證據逐字入帳（指令、rc、`out_sha256`、`out_bytes`、遮蔽末段）、轉述他包者標 `[他包回報]`、主控親跑後才升格為「已驗證」、貼不出輸出者改寫為「未驗證」（AC-SI-21-2）；(g) 流程摩擦入帳時點：Developer 棒與 QA 棒交卷的〈流程摩擦〉節項目於 **SCG-4 收尾前**由主控入帳（OBS-SI-214：P1 TCS 的 V7 寫「SCG-4 前」，對 SCG-4 的 QA 本身不可能；自本檔起該句改讀「收尾前」）。AT 以 `## `、`### ` 標題切段取關鍵片段判準，並以逐項刪去的副本自證判準有牙（沿 P1 TCS 的 SOP 逐項刪去自證手法）。
- **R109 範圍與持有面（§5.7 的允許變更集合與 PRD §9.1〈C4 套件檔案表（P2）〉逐格一致；唯一的增列是 R110 所需的 `writeverbs.py` 一處修改，本檔類推、§7.1 ⚖ 39）**：Developer 棒只新增或修改 §5.7 列出的檔案；不改 `.claude/**`、不改任何凍結檔（PRD、研究方法 SOP、P0 與 P1 TCS）、不改 `autoclaude/` 引擎原始碼、不改 `AgentConsole/**`（P2b 的 AgentConsole 三層屬另鍵與另一份 TCS；AgentConsole 鐵律 7：其開發 agent 不動根層 `tools/`，反向亦然）；`non_evolvable_globs` 與 `spec_body_globs` 的內容不變；真帳本、真事件帳本、真 `SelfImproving_Proposals/` 與家目錄只由主控於實跑時寫。每個 `tools/lib/selfimproving/*.py` 斷言行 ≤400（`guardrail_lib`）、入口 `tools/selfimproving.py` ≤750（`guardrail_cli`）；P2 新增與增量後的行數估算見 PRD §9.1。
- **R110 `attr --type link` 的 `--reopens` 目標（§7.1 ⚖ 39 採甲；主控 2026-10-21 裁決；P1 R48 (b) 的擴充；`refs.py`、`writeverbs.py`）**：(a) **目標集合**：新增獨立函式 `refs.reopenable_rows(repo, obs_text)`（住 `refs.py`〔`ro`〕，簽名同既有的 `closed_rows`，回 `ID → 證據路徑集合`）＝`closed_rows`（P1 R45 的已結列：OBS 處置首詞屬 `fixed@…`、`DEF-…`、`merged@…`、`retired`、`decided`，與缺陷帳本家族中分類為 `fixed`／`wontfix`／`closed-by-decision`／`routed` 的列）∪ OBS 帳本（含封存檔）中處置首詞為 `deferred` 的九欄列；`deferred` 依 P0 規則必附附加文字（再開症狀），被再開即其語意；處置首詞 `open` 與其餘一律不入集合。(b) **`attr --type link`（只在寫入端判）**：`--reopens` 改以 `reopenable_rows` 判，不在其內者——存在於 OBS 帳本或缺陷帳本家族＝rc 1、碼 `REOPENS-NOT-CLOSED`（含處置首詞為 `open` 者）；不存在＝rc 1、碼 `REOPENS-NOT-FOUND`；`--from` 須在 OBS 帳本（`OBS-NOT-FOUND`）、`root` 與 `link` 專屬旗標互斥、輸出文法與 `attr` 事件鍵集（`seq`、`t`、`kind`、`by`、`id`、`type`、`from`、`reopens`）一律沿 P1 R48 不變；重放端 `events.validate` 對 `link.reopens` 只驗 ID 形態（P1 R37 不變），故既有事件不受影響。(c) **`closed_rows` 與 R45 的 `REOPEN-CANDIDATE` 判準不變**：復發候選提示仍只認已結列，處置為 `deferred` 的列不會被提示為候選（WHY：`deferred` 的再開由立案者以 `attr link` 明示連結、不是路徑相交的推測；兩個函式分開，使一個判準的擴充不連帶改動另一個）。(d) 無新檔、無新 import 邊：`writeverbs.py`（`rw`）既已 import `refs`，R105 的 40 鍵與純度判準不變。(e) 對 P1 測試的影響只有 R107 (c) 列出的 `test_AT_106_2_E_1_link_rejections` 一處。

**〈P2 判定碼表（`check` 的 P2 追加；P0 的 21 項與 P1 的 7 項及其碼不變）〉**（項序即輸出序）

| 項目 ID | 碼 | 狀態 | 觸發 |
|---------|-----|------|------|
| `events.structure` | `EVENT-KIND`、`EVENT-TYPE`、`EVENT-KEY-MISSING`、`EVENT-KEY-UNKNOWN` | FAIL | `kind` 不在 21 個詞彙；九種 P2 kind 的欄位表違反（R72） |
| `events.transitions` | `FROZEN-BY-PROPOSER`、`HELDOUT-DUP`、`HELDOUT-AFTER-SANDBOX`、`SANDBOX-BASE-MISMATCH`、`VERIFY-RUNS-EXCEEDED`、`PROMOTE-ACK-MISMATCH`、`ROLLBACK-MANIFEST-MISMATCH`、`DEC-TARGET-MISMATCH` | FAIL | R74 (a)～(h) |
| `events.transitions` | `COOLDOWN-BYPASS-SUSPECT` | PASS（warn finding；項目狀態不變） | 同型冷卻中又出現新 `prop`（R82 (f)） |
| `events.prop_files` | `PROP-VERIFY-SHA-MISMATCH`（缺檔沿 P1 碼 `PROP-FILE-MISSING`） | FAIL | `verify<K>.json` 的位元組雜湊與 `app.verify.verify_sha256` 不符；缺檔為 `PROP-FILE-MISSING`（R90 (a)） |
| `events.dec_quote` | `QUOTE-MISMATCH`、`NOT-HUMAN-UTTERANCE`、`GRAMMAR-*`、`ID-MISMATCH`、`KIND-MISMATCH`、`CARD-NOT-DELIVERED`、`CARD-SHA-MISMATCH`、`LINE-OUT-OF-RANGE`、`RECORD-UNPARSABLE`、`TEXT-EMPTY` | FAIL | 已存 `dec` 的引言回查不符（R79、R98 (a)） |
| `events.dec_quote`、`events.research` | `TRANSCRIPT-UNAVAILABLE`、`ORIGIN-MISSING`、`ATTACHMENT-TIME-UNKNOWN` | NE nonblocking（`ORIGIN-MISSING`、`ATTACHMENT-TIME-UNKNOWN` 於 `events.dec_quote` 同為 NE nonblocking） | 逐字稿取不到、出處欄位缺、附件時序欄缺（R77、R98） |
| `events.research` | `HELMSMAN-REF-INVALID` | FAIL | `helmsman` 免掃的座標回查不是真人載體或文字為空（R98 (e)） |
| `events.dec_console` | `CONSOLE-AUDIT-MISMATCH` | FAIL | 稽核檔與 `dec` 逐欄不符、`audit_sha256` 或 HMAC 不符（R95） |
| `events.dec_console` | `CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING` | NE nonblocking | 稽核檔不在場（他機）、金鑰環缺或無對應 `key_id`（R95） |
| `events.verdict` | `VERDICT-MISMATCH` | FAIL | `app.verify` 的 verdict 與欄位重算不符（R98 (c)） |
| `obs.console_audit` | `CONSOLE-EVENT-MISSING`、`CONSOLE-CLOSE-NOT-APPLIED`、`CONSOLE-AUDIT-MISMATCH` | FAIL | R98 (d) |
| `obs.console_audit` | `CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING` | NE nonblocking | R98 (d) |
| `row.markers` | `MARK-VALUE`、`CONSOLE-MARK-PAIR`、`CONSOLE-AUDIT-DUP` | FAIL | `carrier`、`audit_ref` 標記的值域、成對與唯一規則（R76） |
| `ref.carrier_families` | `FAMILY-REF-DANGLING`（事件帳本內的 ID 型欄位）、`PROP-DIR-ORPHAN` | FAIL | 事件帳本內 ATT／PROP／RUN 的指標指向不存在者、提案目錄名無對應 `prop` 事件（R104 (b)(ii)(iii)） |
| `ref.carrier_families` | `FAMILY-REF-DANGLING`（OBS 列處置的 `proposed@PROP-SI-N`） | PASS（warn finding；項目狀態不變） | OBS 列的 `proposed@` 指標指向不存在的 `prop` 事件（R104 (b)(i)；歷史列與夾具的合成指標不致使項目轉紅） |
| `ref.carrier_families` | `CARRIER-NOT-ESTABLISHED` | NE nonblocking | 事件帳本不在場，或提及 DEC／APP／MEA 家族（R104） |
| `research.sources` | `SRC-URL-HOST` | FAIL | host 含非 ASCII 字元或任一 label 以 `xn--` 起頭（R101；P1 R43 的碼、判準擴充） |
| `params.keys` | `PARAM-MISSING`、`PARAM-TYPE`、`PARAM-RANGE` | FAIL | 必備鍵由 28 增為 30（R106） |

**〈P2 拒收碼表（rc 1；R71）〉**（供 AT 以「碼集合」斷言；沿 P1 R28 的階段二＝政策與狀態類、全部收集；階段一＝輸入類、遇第一個即回——逐字稿層碼屬階段一）

| 動詞 | 碼 |
|------|-----|
| 全部 P2 寫入動詞 | `UNATTENDED-REFUSED`、`PROP-NOT-FOUND`、`LOCK-BUSY`、`LEDGER-TORN`、`EVENT-BYTES-OVER`、`STATE-CHANGED` |
| `decide`（逐字稿載體；階段一） | `TRANSCRIPT-UNAVAILABLE`、`LINE-OUT-OF-RANGE`、`RECORD-UNPARSABLE`、`NOT-HUMAN-UTTERANCE`、`ORIGIN-MISSING`、`TEXT-EMPTY`、`ATTACHMENT-TIME-UNKNOWN`、`GRAMMAR-NO-DECISION`、`GRAMMAR-MULTI`、`GRAMMAR-TRAILING`、`GRAMMAR-REASON-MISSING`、`GRAMMAR-FORM`、`GRAMMAR-ID-FORMAT`、`GRAMMAR-CARD-QUOTED`、`ID-MISMATCH`、`ID-KIND`、`KIND-MISMATCH`、`RUN-NOT-FOUND` |
| `decide`（階段二；兩種載體共用） | `PRECONDITION-STATE`、`PRECONDITION-VERDICT`、`ROUTE-HANDOFF`、`ROUTE-VERB-MISMATCH`、`PROMOTE-FORM-MISMATCH`、`PROMOTE-PREMISE-ROLLBACK`、`PROMOTE-PREMISE-TOUCHED`、`NOT-IN-COOLDOWN`、`RUN-MISMATCH`、`NOT-SUSPENDED`、`REASON-CLASS-MISSING`、`REASON-CLASS-UNEXPECTED`、`REASON-CLASS-MISMATCH`、`CARD-NOT-ISSUED`、`STALE-CARD`、`CARD-CHANGED`、`CARD-NOT-DELIVERED` |
| `decide`（Console 載體） | `AUDIT-FILE-MISSING`、`AUDIT-SCHEMA`、`AUDIT-REF-MISMATCH`、`AUDIT-BODY-INVALID`、`AUDIT-KIND-MISMATCH`、`AUDIT-USER-FORMAT`、`ROLE-NOT-ADMIN`、`AUDIT-TIME-FORMAT`、`AUDIT-SUBJECT-MISMATCH`、`AUDIT-KEY-MISSING`、`AUDIT-KEY-UNKNOWN`、`AUDIT-MAC-MISMATCH`、`AUDIT-REF-REUSED`、`STALE-CARD` 與階段二各碼 |
| `card --issue` | `STATE-ILLEGAL` |
| `prop-new`、`prop-revise`（P2 追加） | `COOLDOWN`、`REJECT-RESPONSE-MISSING` |
| `heldout-freeze` | `ROUTE-HANDOFF`、`HELDOUT-EXISTS`、`HELDOUT-AFTER-SANDBOX`、`PROP-STATE-ILLEGAL`、`FROZEN-BY-PROPOSER`、`HELDOUT-FROM-INSIDE`、`HELDOUT-LINK`、`HELDOUT-MANIFEST-INVALID`、`HELDOUT-REF-UNRESOLVED`、`HELDOUT-EMPTY` |
| `sandbox` | `STATE-NOT-APPROVED`、`HELDOUT-NOT-FROZEN`、`DEC-VERIFY-FAILED`、`TRANSCRIPT-UNAVAILABLE`、`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`、`DIGEST-MISMATCH`、`MEMORY-DIR-MISSING`（rc 3：`SANDBOX-ROOT-IN-REPO`、`TARFILE-FILTER-MISSING`、`HOME-UNWRITABLE`） |
| `verify` | `STATE-NOT-VERIFIABLE`、`HELDOUT-NOT-FROZEN`、`VERIFY-RUNS-EXCEEDED`、`SANDBOX-TREE-DRIFT`（rc 3：`HOME-UNWRITABLE`、參數鍵無效） |
| `promote` | `STATE-NOT-VERIFIED`、`ROUTE-HANDOFF`、`NO-PROMOTE-DEC`、`PROMOTE-FORM-MISMATCH`、`DEC-VERIFY-FAILED`、`TRANSCRIPT-UNAVAILABLE`、`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`、`DIGEST-MISMATCH`、`PROMOTE-PREMISE-ROLLBACK`、`PROMOTE-PREMISE-TOUCHED`、`NON-EVOLVABLE-NOW`、`MEMORY-DIR-MISSING`、`PREIMAGE-MISMATCH`、`APPLY-FAILED` |
| `rollback` | `STATE-NOT-PROMOTED`、`NO-ROLLBACK-DEC`、`DEC-VERIFY-FAILED`、`TRANSCRIPT-UNAVAILABLE`、`CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`、`TREE-CHANGED`、`ROLLBACK-NOT-EXACT`、`MEMORY-DIR-MISSING` |
| `obs-add` | R94 各碼、`AUDIT-REF-REUSED`、`PIPE-IN-FIELD`、`FIELD-EMPTY`、`ENUM-CATEGORY`、`ENUM-SEVERITY`、`FACE-INVALID`、`EXPOSURE-REQUIRED`、`EXPOSURE-UNEXPECTED`、`MARKS-EXTRA-KEY`、`REL-CONFLICT`、`CORRECTS-NOT-FOUND`、`ROW-BYTES-OVER`（與其他 `rows.evaluate_rows` 的列規則碼）、`OBS-ORPHAN`（stderr） |
| `obs-close` | R94 各碼、`AUDIT-REF-REUSED`、`OBS-NOT-FOUND`、`OBS-ARCHIVED`、`NOT-OPEN`、`DISPOSITION-INVALID`、`DISPOSITION-TEXT-MISSING`、`PIPE-IN-FIELD`、`LEDGER-CHANGED`、`ROW-BYTES-OVER` |

| US ID | User Story | AC ID | AC（Given／When／Then；括號內為 PRD 全名與所指動詞或規則） |
|-------|------------|-------|-----------------------------------------------------------|
| US-201 | 作為掌舵者，我要在主控貼出的一張提案卡上用一句話下決定（核准、否決、退回、晉升、轉交、回滾、解除、恢復），且決定只認我本人在逐字稿裡的文字訊息，使「主控偽造核准」可被事後稽核，審閱成本才不隨提案複雜度增加 | AC-212-1 | （PRD AC-SI-12-1；`decide`，R77、R78、R80）Given 一張 PROP 卡或迴圈處 SUSPENDED When 掌舵者回覆 Then 僅 §7.2 動詞表九列語法之一構成決定；綁 PROP 的動詞綁定該 PROP 最近一次送達之卡面 digest、`恢復` 綁 RUN；DEC 附掌舵者原句與 `sid`＋`line`；無決定或無法解析＝預設拒絕、狀態不變 |
| US-201 | 同上 | AC-212-2 | （PRD AC-SI-12-2；R80 (f)、R86、R91）Given 核准後 PROP 內容改變（digest 不同），或決定對應的卡面 digest 不等於現行 digest（過期卡） When 記 DEC、進沙盒或晉升 Then 核准失效、決定被拒、須重新上卡 |
| US-201 | 同上 | AC-212-3 | （PRD AC-SI-12-3；R78、R80）Given 多張 PROP When 呈現與決定 Then 逐張（K=1）、沒有「全部核准」、一則訊息只受理一個決定；DEC 記 `decider`（掌舵者），主控不得代決、不得替人補話 |
| US-201 | 同上 | AC-212-4 | （PRD AC-SI-12-4；R77、R79、R98 (a)）Given 一筆待記的 DEC 或帳本中已存的 `dec` When 驗證 Then ① 引言逐字出現在兩種真人載體之一（sdk、isMeta、tool_result 不算；出處欄位缺＝NE）② 錨定於動詞表某列（否定句、疑問句、引用卡面、多 PROP 同則、尾隨文字皆拒）③ 卡面於發言之前最近一則含 text 的 assistant 訊息送達（user 載體用實體行序、附件載體用附件自帶時間戳）④ 逐字稿取不到＝NE、不記 DEC ⑤ `check` 與 `promote` 對已存 `dec` 以同一函式回查 |
| US-201 | 同上 | AC-213-1 | （PRD AC-SI-13-1；R80 (e)、R82 (a)）Given 否決或退回 When 記 DEC Then 必含 `reason_class`（七值）與一句理由；「未說明」亦可、但採最嚴冷卻 |
| US-201 | 同上 | AC-240-6 | （本檔自增；PRD §9.3 `card` 列、AC-SI-12-4 ③ 的前提；`card --issue`，R81）Given 一張待決或已晉升的 PROP When `card --issue` Then 於寫入鎖內記 `card` 事件（`prop`、`rev`、`digest`、`card_sha256`），stdout 的卡面與不帶旗標相同；非前提態拒收 |
| US-202 | 作為掌舵者，我要被否決的同型提案在沒有新證據或我的明示解除前不再出現，才不必重複審同一件事 | AC-213-2 | （PRD AC-SI-13-2；R82）Given 某型（`cls`、`target`、根因鍵或證據座標）剛被否決 When 同型提案再生成 Then 被擋（`COOLDOWN`）直到 (a)「解除」或 (b) 新立且證據座標不相交的同根因觀察；再提案須附逐項回應否決理由 |
| US-202 | 同上 | AC-213-3 | （PRD AC-SI-13-3；R82 (f)）Given 冷卻被繞過（手寫事件直接追加） When `check` 重放 Then 標 warn `COOLDOWN-BYPASS-SUSPECT`（偵測型）；M4 的計數與自動入 OBS 屬 P3 |
| US-203 | 作為主控與審查者，我要核准後的提案只在樹外的隔離沙盒套用、正式面零變更，並在凍結評估集、對照與突變之下得到 PASS／FAIL／NE 三態判定與逐字入帳的證據，使驗證有鑑別力、不是自說自話 | AC-215-1 | （PRD AC-SI-15-1；`sandbox`，R85、R86）Given 已核准 PROP When 套用 Then 只作用於 `git archive` 匯出到樹外的隔離副本；沙盒根不在 repo 樹內、不在 `.claude/worktrees/`；套用前後正式面 `git status --porcelain`、HEAD、`git worktree list` 逐字相同；套用不受機器 `core.autocrlf` 影響 |
| US-203 | 同上 | AC-215-2 | （PRD AC-SI-15-2；R105）Given 沙盒建立與清理 When 執行 Then 不使用鐵律五的毀滅性 git 形態；清理＝丟棄副本 |
| US-203 | 同上 | AC-215-3 | （PRD AC-SI-15-3；R108 (e)；流程型 P，以 SOP 條文代位）Given 遇 R-9.6 擋寫或 harness 分類器拒絕 When 套用 Then 不得以改派子代理或換路徑繞過，改由符合條件的視窗處理或走轉交 |
| US-203 | 同上 | AC-215-4 | （PRD AC-SI-15-4；R85、R86）Given 已核准 PROP 的沙盒失敗（匯出失敗、patch 套不上、`git apply` 逾時、`touched` 超集、回滾乾跑不過） When `sandbox` Then 仍寫 `app.sandbox`（`applied`、`touched_ok`、`rollback_ok`、`fail_code` 實況）、PROP 進 `sandboxed`、不卡在 `approved` |
| US-203 | 同上 | AC-217-1 | （PRD AC-SI-17-1；R87、R88）Given 沙盒套用或驗證超出固定上限 When 超界 Then 立即停止並收 verdict：探針逾時＝殺行程樹、收 NE（不收 FAIL）；`app.verify` 超過 `verify_runs_max`＝rc 1 並升級人工 |
| US-203 | 同上 | AC-218-1 | （PRD AC-SI-18-1；R108 (d)；流程型 P，以 SOP 條文代位）Given 一張 PROP When 驗證 Then 審查者與提案者為不同代理實例與不同 context，審查者全程唯讀、不得自起背景長任務 |
| US-203 | 同上 | AC-218-2 | （PRD AC-SI-18-2；R88、R89）Given 判定 When 記 PASS Then 主依據必為外部可重跑訊號（探針 rc、重放結果）；LLM 意見不得單獨把 FAIL 改成 PASS（`verify` 沒有任何覆寫 verdict 的旗標） |
| US-203 | 同上 | AC-219-1 | （PRD AC-SI-19-1；R88、R89）Given 驗證計畫 When 執行 Then 先對照：基線重現症狀（RED）、套用後消失（GREEN）、突變後回來（RED），三者缺一＝NE；載具自證：沙盒內被測模組的 `__file__` 在沙盒內（`PYTHONPATH` 遮蔽），否則 NE |
| US-203 | 同上 | AC-219-2 | （PRD AC-SI-19-2；R89）Given 結果 When 判定 Then 僅 PASS／FAIL／NE；NE 不得視為 PASS，晉升須「未驗採納」式；M／D 類無確定性探針者預設 NE（`NO-PROBES`） |
| US-203 | 同上 | AC-219-3 | （PRD AC-SI-19-3；R88）Given R 類重放 When 命中率高 Then 僅為證據、不得據此自動核准（`verify` 不寫 `dec`、無命中率欄位） |
| US-203 | 同上 | AC-220-1 | （PRD AC-SI-20-1；`heldout-freeze`，R83）Given 一個驗證計畫 When 於 `prop-new` 之後、`sandbox` 之前 Then 評估集由提案者以外的角色以 `prop` 為鍵凍結（每 PROP 至多一筆；凍結者≠提案者；`seq` 早於第一筆 `app.sandbox`；內容在家目錄、digest 入帳） |
| US-203 | 同上 | AC-220-2 | （PRD AC-SI-20-2；R88、R89）Given 評估集 When 規模小於 `min_heldout` Then 判 NE，不得以小樣本宣稱有效 |
| US-203 | 同上 | AC-220-3 | （PRD AC-SI-20-3；R91 `NON-EVOLVABLE-NOW`、P1 R52）Given 任一角色嘗試修改評估指令、評分權重、held-out 或量測腳本 When 提案或晉升 Then 視為 `evaluator-change`／`loop-self`，不進採納流程；僅掌舵者經 T1 可改 |
| US-203 | 同上 | AC-220-4 | （PRD AC-SI-20-4；R88、R90 (b)）Given 一筆 PROP 進入驗證 When 預檢 Then ① 重算 held-out digest，不符＝NE ② 掃提案者逐字稿（含 `subagents/`）的工具呼叫，命中 held-out 目錄、`params.json` 或量測腳本者標 `exposed`＝NE；逐字稿取不到＝NE；只量不阻擋 |
| US-203 | 同上 | AC-221-1 | （PRD AC-SI-21-1；R87 (d)、R90）Given 驗證記錄 When 入帳 Then 含執行者、時間（帶 offset）、指令、rc、輸出摘錄座標（`out_sha256`、`out_bytes`、遮蔽末段 ≤300 位元組）、母體數；原始輸出全文不入 git |
| US-203 | 同上 | AC-221-2 | （PRD AC-SI-21-2；R108 (f)；流程型 P，以 SOP 條文代位）Given「已驗證／已達標」宣稱 When 檢視 Then 附當回合真跑輸出，貼不出者改寫為「未驗證」；轉述他包者標 `[他包回報]` |
| US-204 | 作為掌舵者，我要晉升是我下達的人工動作、不 commit，且任何已晉升的改進都能以一個動作回滾並被機械驗證還原，出錯時損失才有界 | AC-216-1 | （PRD AC-SI-16-1；`promote`，R91）Given 驗證 verdict 為 PASS（或 NE 而掌舵者以「未驗採納」式）且 digest 與核准時相同 When 掌舵者下達晉升 Then 才合入正式面（不 commit）；FAIL、NE 無 ack、digest 不同、DEC 回查不符或逐字稿取不到者拒收（fail-closed） |
| US-204 | 同上 | AC-216-2 | （PRD AC-SI-16-2；R85 (f)、R80 (e)、R91）Given 每筆 PROP When 受理 Then 回滾配方乾跑（正向→反向後與 base 逐位元相同）通過才可晉升；晉升前提＝最近一筆 `app.sandbox` 的 `rollback_ok` 與 `touched_ok` 皆為 `true`，`decide --kind promote` 於記 DEC 時就擋、`promote` 再驗 |
| US-204 | 同上 | AC-216-3 | （PRD AC-SI-16-3；R91）Given 晉升完成 When 記 DEC 與事件 Then 含晉升者、時間（帶 offset）、`head_sha` 與前後 manifest 快照座標（不 commit，故無 `commit_sha`） |
| US-204 | 同上 | AC-217-2 | （PRD AC-SI-17-2；R93）Given 迴圈進入 SUSPENDED When 要繼續 Then 僅能由掌舵者以 `dec(resume)`（綁折疊出的 SUSPENDED 運轉）恢復；SUSPENDED 期間 `prop-new` 拒收；本迴圈不讀寫 FSM 狀態檔 |
| US-204 | 同上 | AC-240-7 | （本檔自增；PRD §9.3 `rollback` 列、FR-SI-16 回滾配方的執行半；R92）Given 已晉升 PROP 與經回查的 `dec(rollback)` When `rollback` Then `touched` 路徑現況須等於晉升後 manifest，反向套用後逐位元還原為晉升前（不符則零變更）；不 commit |
| US-205 | 作為掌舵者與主控，我要在 Console 以帳號下決定、新增觀察與處置終值，並由主機端 CLI 驗簽後在寫入鎖內入帳，使 Console 是帳本的第二種載體而不是第二個寫入者 | AC-233-1 | （PRD AC-SI-33-1 的根層半；`decide --carrier console`，R94、R95）Given Console 為 DEC 的第二種載體 When 主機端 CLI 驗證稽核 JSON Then 驗 HMAC、欄位、§7.2 前提與 digest 後於寫入鎖內寫 `dec`（`carrier=console`、`audit_ref`、`audit_sha256`、`key_id`）；金鑰缺＝拒收；同一 `audit_ref` 不得二次入帳；`AUTOSDD_UNATTENDED` 有設＝rc 1；回查不符＝`check` 紅、`promote` 拒；跨語言測試向量逐字相同 |
| US-205 | 同上 | AC-233-2 | （PRD AC-SI-33-2 的根層半；R95、R98 (b)）Given 一次 Console 決定 When 稽核檔與 `dec` 對帳 Then PROP、digest、動詞、決定者、時間逐欄相符；不符＝紅；稽核檔不在場＝NE（Console DB 稽核表的對帳屬 AgentConsole 側） |
| US-205 | 同上 | AC-235-1 | （PRD AC-SI-35-1；`obs-add`，R96）Given Console 表單提交的稽核 JSON When 主機端 `obs-add` Then 驗簽、以與 `check` 同一函式驗列規則通過後，於寫入鎖內追加一列（ID 由 CLI 配、時間取稽核 `time` 並保留 offset、處置固定 `open`、標記含 `carrier=console;audit_ref`）與 `obs.add`；任一不符＝零變動；同一 `audit_ref` 不得二次入帳 |
| US-205 | 同上 | AC-235-2 | （PRD AC-SI-35-2；`obs-close`，R97）Given 既有 OBS 列 When Console 更新 Then 只有更正列（走 `obs-add`）與處置 `open`→終值一次（`obs-close`：只動處置欄、其餘位元組逐字不變、原子改寫）；已非 `open`＝拒收 |
| US-205 | 同上 | AC-235-3 | （PRD AC-SI-35-3；R97）Given CLI 的全部介面 When 檢視刪除能力 Then 沒有：動詞表沒有刪除或改號類動詞；退場一律＝處置終值 `retired：<座標>` |
| US-205 | 同上 | AC-235-4 | （PRD AC-SI-35-4 的根層半；R94）Given Console 的寫入稽核 JSON When CLI 判定資格 Then `role` 須為 `ADMIN`、帳號名合 `^[A-Za-z0-9_.-]{1,64}$`（含 `;`、`=` 者拒）；帳號白名單 `console.si.deciders` 與 403 屬 AgentConsole 側 |
| US-205 | 同上 | AC-235-5 | （PRD AC-SI-35-5 的根層半；R98 (d)、R99 (a)）Given 一次 Console 寫入 When `check` 與 `status` Then 帶 `carrier=console` 的列須有 `obs.add` 且稽核檔（在場時）逐欄相符、HMAC 相符；稽核檔不在場＝NE；`status` 列出尚未入帳的稽核檔（`audit_ref`、`kind`） |
| US-205 | 同上 | AC-240-12 | （本檔自增；PRD §9.2 `export --json` 輸出、AC-SI-31-4 與 AC-SI-32-1 的 `buckets[]`、OBS-SI-237；R99）Given `export --kind observations` 與 `status` When 輸出 Then 每個九欄 OBS 項有 `buckets[]`（不 `casefold` 的路徑片段、同一個 `scan.bucket_of`）；`status` 有 `console_pending`；`export` 不讀家目錄 |
| US-206 | 作為維護者，我要 P2 的事件詞彙、狀態機、檢查項、參數與能力登記一致落定，寫入鎖在 Windows 的刪除待決下不再偶發失敗，P1 的殘留與資料面小缺口各有可重跑檢查，並有零退化保證 | AC-240-1 | （本檔自增；PRD §9.2 事件欄位表 P2 段、§9.7 #73～#75、#78；R72、R73、R107 (d)）Given 事件帳本 When 寫入或 `check` 重放 Then `KINDS` 為 21 個、九種 P2 kind 有完整欄位表（必備鍵、條件必備、表外鍵、型別、null 規則）；升級後的夾具建構器輸出全部通過它 |
| US-206 | 同上 | AC-240-2 | （本檔自增；PRD §5.1.2 狀態機、§9.2 轉移註記、§9.7 #76；R74、R75）Given 事件序列 When `fold` 重放 Then 依 P2 轉移表折疊（複驗邊受 `verify_runs_max`、`return` 與 `promote` 的新前提、`Prop` 新欄、帳本不變式）；`decide` 與 `fold` 用同一前提判定 |
| US-206 | 同上 | AC-240-3 | （本檔自增；PRD §9.3 `check` 列；R98）Given `check` When 執行 Then 共 32 項（P0 21＋P1 7 原樣＋P2 四項）；載體缺席一律 nonblocking NE、P0 基線 repo 的 rc 與 overall 不變；`CHECK_RULES_REV` 為 3 |
| US-206 | 同上 | AC-240-4 | （本檔自增；PRD §9.1 C5 P2 新增兩鍵；R106）Given `params.json` When 讀取 Then 30 鍵，`probe_timeout_seconds`、`verify_runs_max` 為正整數；缺或無效＝`check` 紅、動詞 rc 3 並點名、不以預設值頂替 |
| US-206 | 同上 | AC-240-5 | （本檔自增；PRD §9.4〈能力登記與純度判準〉P2 擴充；R105）Given 套件原始碼 When 掃描 Then 40 鍵（29 `ro`／7 `rw`／2 `net`／2 `exec`）；除 `git.py` 與 `runner.py` 外無 `subprocess`；import `runner` 者必為 `exec`；唯讀動詞閉包全 `ro`；`taskkill`、`os.killpg` 各在平台守衛內；無禁字樣 |
| US-206 | 同上 | AC-230-2 | （PRD AC-SI-30-2 的 P2 收口；R101）Given 研究來源表 When 驗證 Then host 僅限 ASCII（非 ASCII、全形數字、任一 label 以 `xn--` 起頭者拒收、不做正規化後比對）；`research --fetch` 對不合的表零請求 |
| US-206 | 同上 | AC-240-8 | （本檔自增；DEF-200-559、OBS-SI-210、211；PRD §9.4 `apply_lock` 段；R100）Given `apply_lock` When Windows 刪除待決或共享違規（`PermissionError`） Then 三站點視同忙碌或可重試；取鎖逾時拋原始例外；釋放耗盡不改 rc；`FileExistsError` 路徑不變；既有測試全綠 |
| US-206 | 同上 | AC-240-9 | （本檔自增；P1 TCS 勘誤四殘留；R102）Given 本檔 AT 清單 When 解析與收集 Then 每個 AT 的錨定 `-k` 恰收一個測試函式；兩位序號不與個位序號互收 |
| US-206 | 同上 | AC-240-10 | （本檔自增；OBS-SI-218；R103）Given `scan` When 彙整 Then 資訊型的模組桶草稿列為 `process`／`P4`／`decided：僅計數`、缺陷候選列維持 `bug`／`P3`／`open`；三個計數來源的來源行改「計 N 筆（未解析內容）」；JSON 不變 |
| US-206 | 同上 | AC-240-11 | （本檔自增；OBS-SI-217；P1 TCS ⚖ 2；R104）Given 事件帳本已建立 When `check` 的 `ref.carrier_families` Then 對 ATT／PROP／RUN 三族的指標形態引用做存在性判（事件帳本內與提案目錄的懸空指標＝FAIL；OBS 列處置的懸空 `proposed@` 指標＝warn、項目狀態不變），DEC／APP／MEA 與載體缺席維持 NE；散文提及與規格文件不判 |
| US-206 | 同上 | AC-240-13 | （本檔自增；PRD §8.1 P2 出口 (g)、C.2 #20 (k)、OBS-SI-214；R108；流程型 P，以 SOP 條文代位）Given Operations SOP When 定稿 Then 〈P2 動詞〉節補齊各動詞的 rc 契約、運轉序列、Console 載體配方與流程條文，且流程摩擦入帳時點為「SCG-4 收尾前」 |
| US-206 | 同上 | AC-240-14 | （本檔自增；PRD §8.1 P2 出口 (f)；R107、R109）Given P2 變更落地 When 全套 Then P0 的 42 個 AT 與 P1 的 163 個 AT 全綠（P1 斷言值只於 R107 (c) 列出的站點同步）、`non_evolvable_globs` 與 `spec_body_globs` 不變、真 repo 的 `check` 為 rc 0 |
| US-206 | 同上 | AC-240-15 | （本檔自增；來源＝主控 2026-10-21 對 ⚖ 39 的裁決，PRD 修訂建議 6；R110）Given 一個 OBS 列的處置首詞為 `deferred`（必附再開症狀）或該列為已結列 When `attr --type link --reopens <該列>` Then rc 0 並寫入一筆 `type` 為 `link` 的 `attr`；處置首詞為 `open` 者 rc 1 `REOPENS-NOT-CLOSED`、不存在者 rc 1 `REOPENS-NOT-FOUND`、零寫入；R45 的 `REOPEN-CANDIDATE` 判準不變 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。本檔除 §1 外沒有任何第一欄以 AC 起頭的表格；AT ID 於 §1 與 §2 的宣告位置之外，只出現在說明性文字與表格的非第一欄（不在第一欄形如 AC 的列的第三欄）。

**INVEST 自檢**：獨立（只依賴 git、PRD 與根 `CLAUDE.md` 的現況文字、既有 `tools/_stdio_utf8.py`、`lib.apply_lock`、`lib.sdd_latest`、`lib.platform_utils`，與 P1 已交付的 `tools/lib/selfimproving/` 套件）、可協商（旗標細部、拒收碼、`status`／`export` 的新鍵形態、`reject_response`、暴露掃描的範圍、`carrier_proof` 的空集合語意由本檔定義並列入 §7.1，掌舵者可裁決）、有價值（P2 出口 (a)～(g) 除真實運轉與真實 Console 外皆可由 AT 判定，且每條「不能做」都標邊界型 M／D／P）、可估計（16 支新套件模組＋入口增 8 個動詞與 `card --issue`＋7 個新測試檔＋1 個新夾具模組＋既有 4 個測試檔的同步站點＋`apply_lock` 與其測試＋SOP；PRD §9.0 估新增 `tools/` 約 4,300 斷言行）、小（P2 範圍已由 PRD 與 C.2 #19 劃定；P3 與 P2b 不在本檔）、可測（AT 數見 §1 覆蓋率統計；絕大多數用 tmp 目錄的合成 repo、合成事件帳本、合成逐字稿與本機子行程，皆不碰真帳本、不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P2-1 | 純度與能力登記：R105（40 鍵四類、②′ import `runner` 必為 `exec`、唯讀動詞閉包全 `ro`、套件禁字樣含 `runner.py`、鐵律五形態掃描）；`check`、`status`、`scan`、`export`、`card`（不帶 `--issue`）與 `obs-add --dry-run` 的行程**不載入** `evwrite` 以外的寫入類與 `exec`、`net` 模組（`obswrite`、`decwrite`、`sandbox`、`promote`、`runner`、`verify`、`fetch`、`research`、`writeverbs`）；`check` 的動態純度（P0 R8：檔案摘要與 `git status --porcelain` 前後相同、子行程只有淨化 `git`）涵蓋四個追加項 | AT-240-5-1、AT-240-5-E-1、AT-240-5-E-2、AT-235-1-E-3；SCG-4 程式碼審查 |
| NFR-P2-2 | 效能（皆 AT 只做不等式、不列入 AT 者另述）：合成 repo 上單次 `check`（32 項）、`status`、`export` 小於 5 秒；單次寫入動詞（不含 `sandbox`、`verify`）小於 5 秒；`sandbox` 於合成 repo 小於 30 秒；`verify` 的探針逾時案例（`probe_timeout_seconds` 為 2）整體小於 15 秒且行程樹於其後 3 秒內全部消失；每個新測試檔在 CI 上小於 300 秒（超過時依持有面拆檔、不降低覆蓋；OBS-SI-219：SelfImproving 測試模組是根層全套 makespan 的瓶頸，故 P2 的 AT 分散於 7 個新檔、每檔不超過 35 個 AT）；真 repo 上單次 `check` 小於 30 秒（沿 NFR-P1-2） | 合成情境以 AT 內的牆鐘上界斷言（寬鬆上界，避免 CI 抖動）；真 repo 以 SCG-4 實跑量測（3 次取最大值），不列 AT |
| NFR-P2-3 | 跨平台（根 `CLAUDE.md` 鐵律三；§7.1 ⚖ 3）：全部 `git apply` 與 `git archive` 帶 `-c core.autocrlf=false`，不依賴機器 global 與 system 設定（AT-215-1-E-3 以含 `autocrlf = true` 的 `GIT_CONFIG_GLOBAL` 重現 Windows 預設）；`taskkill` 與 `os.killpg` 各在 `sys.platform` 守衛內；沙盒根在 repo 樹外且路徑長度預檢（Windows 259）；路徑一律 `Path`／`os.path`、git 路徑 POSIX 斜線；逐字稿容忍 BOM 與 CRLF；時間戳一律 aware；輸出位元組直寫、UTF-8、LF；macOS 未實跑項在報告標「未驗」（NFR-SI-06-5）；測試字面值不含磁碟機代號開頭的路徑與 POSIX 絕對路徑整串（沿 P1 NFR-P1-10 (11) ⑤） | AT-215-1-E-3、AT-240-5-E-2、AT-212-4-E-4；根層 `tools/tests/test_platform_neutral_paths.py` 相關鎖；SCG-4 審查 |
| NFR-P2-4 | 根層護欄相容：測試與工具不新增 skip、skipTest、skipIf、xfail（git 缺席視為環境壞、直接失敗；Windows 專屬案例以「替身模擬平台」而非跳過）；所有 `open`、`read_text`、`write_text` 帶 `encoding="utf-8"`；測試以 `unittest.TestCase` 撰寫並可被 `python -m pytest` 與 `python -m unittest discover -s tools/tests` 兩種方式收集；不得另寫 stdout 重設站點；子行程夾具必回收（含探針孫行程）；本機 HTTP 夾具只綁 loopback、測試結束必關 | 根層 unittest 閘門；SCG-4 |
| NFR-P2-5 | LOC 分級：`tools/lib/selfimproving/*.py` 每檔 `guardrail_lib` 400 斷言行、入口 `tools/selfimproving.py` `guardrail_cli` 750；`events.py` 增量後逼近 400 時先拆 `evspec`（ro）、不調 tier；現查 `python AutoClaude/tools/check_loc_budget.py --json`（`root_tools_tiers`）rc 0 | SCG-4 實跑 |
| NFR-P2-6 | 靜態檢查：`ruff check` 對新增與改動的每個 `.py` 0 錯 | SCG-4 實跑 |
| NFR-P2-7 | 測試 hermetic：全部 AT 只用 tmp 目錄內的合成 repo、合成帳本、合成逐字稿（置於 tmp 內的 `CLAUDE_CONFIG_DIR`）與以 `AUTOSDD_SI_DIR` 指向 tmp 的家目錄；唯讀存取真 repo 的 `params.json`、PRD、SOP、SSOT、`tools/` 原始碼、`research_sources.json`、`.claude/settings.json`；**不讀真逐字稿、不寫真帳本、真事件帳本、真 `SelfImproving_Proposals/` 與真家目錄**；不連外網（既有 loopback 夾具除外）；不得在測試原始碼或本檔寫出不存在於真帳本與真缺陷帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>` 編號（合成編號於執行期組出，先例 `tools/tests/test_defect_id_reference_integrity.py` 的 `_syn()`；P1 R18 (a) 與本檔 R104 的 `git grep` 會掃整個 repo 的非忽略檔）；環境的 git 設定一律被測試改寫（`GIT_CONFIG_NOSYSTEM=1`、`GIT_CONFIG_GLOBAL` 指向 tmp 內設定檔），需要重現 Windows 預設的 AT 明文寫出設定內容 | 實跑檢核 V2（真帳本 `ref.obs`、`ref.carrier_families`）與既有鎖 `test_defect_id_reference_integrity.py` |
| NFR-P2-8 | 範圍守衛：實作者只新增或修改 §5.7 允許集合內的檔案；不改 `.claude/**`、不改任何凍結檔、不改 `autoclaude/` 引擎原始碼、不改 `AgentConsole/**`；重釘根層棘輪（檔案數下限、LOC、E501；現查 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `repin_growth_problems()`、`tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS`、`tools/tests/test_platform_neutral_paths.py` 的 `_tmpdir_scan_roots` 檔數雙邊帶）與 SSOT 登記列同步由主控收尾，實作者不碰鎖檔 | 實跑檢核 V1（`git diff --name-only`） |
| NFR-P2-9 | CI 與棘輪：P2 新增 `tools/` 估約 4,300 斷言行與 7 個新測試檔，遠超護欄層單輪淨額上限，須由主控以具名一次性例外重釘（`_REPIN_APPROVED_ROUND_OVERAGE`，名冊上限的上修須可見）；compat-ci 兩支 `paths` 已含 `tools/lib/selfimproving/**` 與 `tools/selfimproving.py`，新測試檔在 `tools/tests/` 不必另加；`tools/lib/apply_lock.py` 不在該 `paths` 內——它被 `evwrite` 匯入，現查 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 是否要求列入，同一個 commit 收齊（OBS-SI-215 的結構條件：兩支 compat-ci 不含 SelfImproving 測試實際讀取的 PRD、SOP、`params.json`、TCS，本檔不擴大它，只在 V5 現查） | 實跑檢核 V5；根層全套 unittest |
| NFR-P2-10 | **Developer 交卷前閘門清單（缺一即不得交卷；輸出逐字貼入交卷）**：(1) 本檔 AT 與 P0、P1 的全部 AT 全綠（`python -m pytest tools/tests/test_selfimproving_check.py tools/tests/test_selfimproving_events.py tools/tests/test_selfimproving_props.py tools/tests/test_selfimproving_research_scan.py tools/tests/test_selfimproving_export_status.py tools/tests/test_selfimproving_capability.py tools/tests/test_root_module_layout.py tools/tests/test_selfimproving_decide.py tools/tests/test_selfimproving_events_p2.py tools/tests/test_selfimproving_sandbox.py tools/tests/test_selfimproving_verify.py tools/tests/test_selfimproving_promote.py tools/tests/test_selfimproving_console_obs.py tools/tests/test_selfimproving_p2_meta.py tools/tests/test_apply_lock.py -q -p no:xdist -o addopts=`；鍵 B 的 AutoClaude 測試不在本鍵範圍、不重跑）；(2) `python tools/selfimproving.py check` 對真 repo rc 0（32 項）；(3) `ruff check` 對新增與改動的每個 `.py` 為 0 錯；(4) `python AutoClaude/tools/check_loc_budget.py --json` rc 0；(5) `python tools/sync_onboarding_baselines.py --check-snapshot` rc 0；(6) 官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）rc 0；(7) 護欄層重釘儀式做到 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` 的淨差額為 +0（由主控收尾）；(8) 文件引用子專案檔案一律寫 monorepo 根起算路徑；(9) 大檔（>100KB）編修先備自 pristine 的冪等重建腳本、交卷即退役；(10) 交卷含「流程摩擦」節（根 `CLAUDE.md` 與 SOP 擷取者節），其項目於 SCG-4 收尾前由主控入帳；(11) **新增 `tools/tests/` 檔會撞的根層鎖，逐項過**（沿 P1 NFR-P1-10 (11) 的 ①～⑨：`_TREE_FILE_FLOORS`、`_tmpdir_scan_roots` 雙邊帶、E501 存量棘輪〔東亞寬度〕、編碼衛生掃描下限、POSIX 絕對路徑字面、死信引用、NTFS 錨站點登記、`unittest discover` 靜態守門〔跨檔基底鏈不解析，自夾具檔匯入的測試基底類別其名稱須含 `TestCase`〕、`MIN_TESTS` 下限；修法一律是「重釘為現查值」或「改正成因」、不得壓制）；(12) 測試 class 與夾具 def 的 docstring 指名受測模組（`tools/lib/selfimproving/<x>.py`），使分桶棘輪歸 mixed（沿 P1 NFR-P1-10 (12)）；(13) `--print-guard-lines` 住 `tools/tests/test_adr_xplat001_c1c2_lock.py`、不是分桶探針的旗標；(14) **測試檔的腳本入口必須在檔尾**（`if __name__ == "__main__": unittest.main()` 為該檔最後一個頂層敘述；Developer 交卷前對每個新增或改動的測試檔以腳本模式跑其任一 AT 的 `-k`，須收到至少 1 個測試）；(15) **本檔 R102 的錨定規則檢查（AT-240-9-1）綠**；(16) **`git grep` 本檔、測試與程式碼無不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>`**（V5） | SCG-4 實跑檢核 V2～V5（讀 rc 先存變數再讀，不接管線） |
| NFR-P2-11 | 失效可偵測（NFR-SI-09）：量不到＝NOT-EVALUABLE、不得印成零或綠——`events.dec_quote` 與 `events.research` 的 `TRANSCRIPT-UNAVAILABLE`、`events.dec_console` 與 `obs.console_audit` 的 `CONSOLE-AUDIT-MISSING`／`CONSOLE-KEY-MISSING`（不是零筆通過）、`status` 的 `console_pending`（NOT-EVALUABLE 不得印成空清單）與 `export` 的 NOT-EVALUABLE 值、`verify` 的 `EXPOSURE-UNKNOWN`、`NO-PROBES`（M／D 類預期為 NE 不是 PASS）、沙盒與驗證逾時收 NE（FAIL 只來自測得的失敗）；P1 的 `ne` 與 `unavailable` 語意不變 | §2 對應各 AT |
| NFR-P2-12 | 安全與最小留存：CLI 輸出與事件不含 HMAC 金鑰任何 ≥8 字元子字串（R94）；探針子行程環境為白名單、不繼承 `AUTOSDD_*` 與機密（R87）；`tail` 遮蔽四型、原始輸出全文不落任何檔（R87 (d)）；`console_audit/` 由 CLI 只讀（任何 P2 動詞不寫該目錄）；`export` 不讀家目錄（哨兵字串不出現在輸出）；拒收一律零殘留（R71） | AT-233-1-E-1、AT-233-1-E-3、AT-219-1-E-2、AT-221-1-E-1、AT-240-12-E-1；SCG-4 |

**追溯矩陣**：F-003 ← PRD FR-SI-12、13、15～21 與 FR-SI-33、35 的根層半（§5.2）、AC-SI-30-2、§9.1 的 C4（P2 檔案表）、C8、C9、C10、C21，§9.2（事件欄位表 P2 段、held-out 目錄格式、manifest 規則、verifyK、Console 稽核 JSON）、§9.3（P2 動詞、rc 通則）、§9.4（`apply_lock`、沙盒與驗證執行的邊界、三態判定表、能力登記 P2 擴充）、§9.5 的 ADR-SI-03′、04、08、09、10、§9.6 P2 列、§8.1 P2 出口 (a)～(g)、§9.7 #64～#81、C.2 #19、#20；主控 2026-10-21 對 §7.1 ⚖ 39 的裁決（AC-240-15；PRD 修訂建議 6）；US-201～US-206 → AC-212-1～AC-240-15（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；單一 FSM 鍵 `monorepo-si-p2-gate-apply`）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v0.10 全文（§8.1 P2、§9.6 P2）；Stage-1 凍結依常態規則由主控執行（`--approver` 引 sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-003（本檔 FRD-lite）；FR-SI-12、13、15～21、AC-SI-30-2，與 FR-SI-33、35 的根層半 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／NFR 已量化定義 | NFR-P2-1～12（本檔）；最近依據 PRD NFR-SI-01、02、03、04、05、06、09 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-201～US-206（本檔 INVEST 自檢） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／利害關係人已確認簽核 | PRD 附錄 C.2（授權代決 #17～#20；授權座標 sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；凍結依常態規則由主控執行、掌舵者可隨時以 T1 推翻） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC 到 AT 映射）；根層 RTM 檔另依 SSOT §2 落 `docs/06_quality/RTM-SelfImproving-P2-<日期>.md` | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | 不適用（功能級增量；設計載於 PRD §9）；最近依據 PRD §9.0～§9.6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／API Spec 草稿完成（所有端點清單） | 不適用（P2 根層半無 HTTP 端點；Console 端點屬 P2b 另一份 TCS）；命令列介面即契約：本檔 R68～R71 與 PRD §9.3 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／資料模型設計完成 | PRD §5.1.2、§5.1.3、§9.2（事件欄位表、held-out 目錄、manifest、verifyK、Console 稽核 JSON、digest）；本檔 R72～R76、R83、R84、R90、R94 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-P2-1～12 對應 R105（純度）、R87（有界與逾時）、R85 (d)（行尾中立）、R89（NE 不是綠）、R94（金鑰衛生）；PRD NFR-SI-01、02、09 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／整合架構說明完整（第三方服務已識別） | 無第三方服務；依賴 git（`archive`、`apply`）、標準庫 `tarfile`／`hmac`／`hashlib`、`lib.apply_lock`、`lib.sdd_latest`、`lib.platform_utils`、既有 `tools/_stdio_utf8.py`；逐字稿為本機讀取（`claude_home()`） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | PRD §9.1 載體對映表（C4、C7 的 `--issue`、C8、C9、C10、C14 的 `console_pending`、C21 的根層半）；P2 不新增系統邊界（P2b 的 Console 邊界屬另鍵） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／C4 Container 圖完成（主要組件識別） | 落點：根層 `tools/`（CLI `selfimproving.py` 與套件 `lib/selfimproving/` 的 40 檔）、`tools/lib/apply_lock.py`、`tools/tests/`、`docs/06_quality/`（事件帳本、提案內容檔含 `verifyK.json`、協定目錄）、`docs/05_development/`（SOP）；家目錄機器狀態 `<si>/{locks,research,heldout,sandbox,console_audit}/`（repo 外） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | PRD §9.5：ADR-SI-03′、ADR-SI-04、ADR-SI-08、ADR-SI-09、ADR-SI-10；本增量無新架構決策（能力登記第四類 `exec` 與 `apply_lock` 修法為 PRD §9.4 明文），ADR 不新開 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 brownfield，非 security）；信任邊界要點：DEC 只認逐字稿真人載體（fail-closed、不 import hook）、HMAC 金鑰不入探針環境、探針內容是凍結者的指令（信任邊界＝凍結者角色，P）、不可進化面於 `promote` 以當下參數重驗、`tarfile` 成員預檢 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 本檔 FRD-lite〈現況與變更〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | 不適用（無 HTTP API）；介面為命令列 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／Request／Response Schema 定義完整 | 輸出形態：本檔 R69、R96 (d)、R99；事件欄位表 R72；稽核檔 R94；`verifyK.json` R90 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／錯誤碼定義（400／401／403／404／500） | rc 表 0、1、3（R68）、〈P2 判定碼表〉與〈P2 拒收碼表〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／Consumer Contract 完成（整合情境） | 消費者＝主控與 QA（讀 `check`、`status`、`card`、`decide` 的輸出）、P2b 的 Bridge 與 backend（消費稽核 JSON 與 HMAC 向量，R94、§5.5）、P3 量測腳本（讀事件帳本與 `app.*`）；SOP 是各角色任務書的上位（研究方法 SOP，本增量不改它） | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查 | docs/05_development/SelfImproving_Research_Methodology_SOP.md | sha256:deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 的值是 v0.10 Stage-1 凍結的 digest（本檔作者以 `Get-FileHash -Algorithm SHA256` 對工作樹現況重算一致：`1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406`，HEAD `5593d0bb4c6c1d0df9fdcb7863ad192604aa314f`）；研究方法 SOP 的值不變，同樣重算一致（`deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2`）。凍結後的實際 digest 以該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 為準，與本表不符時以 `show` 為準並更正本表。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（見〈AC 編號規則〉）；邊界與錯誤（負控）AT 以 `AT-<NNN>-<Y>-E-<n>` 命名並列於本表。標「流程型」者＝以 SOP 條文（加刪去自證）判定的 AC，其機器守的一半另有 AT。其餘 AT 的判定指令與測試檔見 §2 各 AT 標頭。測試檔縮寫見 §2 開頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-1 | （DC）逐字稿載體（user 記錄）的九個動詞正控：各動詞的 DEC 欄位齊備、狀態依 R75 轉移、DEC 附原句與 `sid`＋`line` | ✅ | Integration | □ |
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-2 | （DC）附件載體（`queued_command`）的真人核准在卡面送達之後打出時受理，時序以附件自帶時間戳為準、不用實體行序 | ✅ | Integration | □ |
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-3 | （DC）決定語法解析器 `decgrammar` 的合法形態正控：開頭式、獨立行式、九列行文法、`晉升` 兩式、Unicode 空白修剪 | ✅ | Unit | □ |
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-E-1 | （DC）語法負控：否定句、疑問句、引用卡面、多決定行、尾隨文字、前綴字、缺理由、全形空格、ID 形態不配 | ✅ | Unit | □ |
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-E-2 | （DC）出處負控：sdk、isMeta、tool_result、assistant、出處缺席、他 PROP、sid 檔不存在、行號超界、壞行 | ✅ | Integration | □ |
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-E-3 | （DC）動詞表前提負控：`恢復` 的 RUN 不符、`回滾` 對未晉升、`晉升` 的式與 verdict 不符、handoff 的核准與晉升、動詞與 route 的配對、`--kind` 與引言不一致、態不合 | ✅ | Integration | □ |
| AC-212-1 | 決定語法與逐字稿出處（PRD AC-SI-12-1） | AT-212-1-E-4 | （DC）用法錯誤 rc 3、`UNATTENDED-REFUSED` rc 1、預設拒絕（無法解析不改狀態）、不收引言與 `--reason` 與 `--unverified-ack`、ID 的存在性與種類（`PROP-NOT-FOUND`、`RUN-NOT-FOUND`、`ID-KIND`）、撕裂的事件帳本（`LEDGER-TORN`） | ✅ | Integration | □ |
| AC-212-2 | 決定綁定現行卡面 digest（PRD AC-SI-12-2） | AT-212-2-1 | （DC）決定綁定現行卡面 digest：`dec` 記錄的 digest 與 `card_seq` 指向現行卡，之後 `sandbox` 受理 | ✅ | Integration | □ |
| AC-212-2 | 決定綁定現行卡面 digest（PRD AC-SI-12-2） | AT-212-2-E-1 | （DC）過期卡與 digest 變更：`STALE-CARD`、`CARD-NOT-ISSUED`、`CARD-CHANGED`；核准後內容檔被改寫使 `sandbox` 與 `promote` 拒 | ✅ | Integration | □ |
| AC-212-3 | K=1 逐張決定（PRD AC-SI-12-3） | AT-212-3-1 | （DC）K=1 逐張決定：兩張 PROP 各自一則決定、各一筆 DEC；`decider` 恆為掌舵者 | ✅ | Integration | □ |
| AC-212-3 | K=1 逐張決定（PRD AC-SI-12-3） | AT-212-3-E-1 | （DC）沒有「全部核准」：整批用語、多個決定行、無 ID、兩個位置參數、代決旗標皆被拒 | ✅ | Integration | □ |
| AC-212-4 | 引言驗證：載體、語法錨定、卡面送達、取不到即 NE、同一函式回查（PRD AC-SI-12-4） | AT-212-4-1 | （DC）卡面送達的正控：只含 `tool_use` 的 assistant 訊息被略過、user 載體以實體行序、附件載體以時間戳；已存 `dec` 的回查由 `check` 重放通過 | ✅ | Integration | □ |
| AC-212-4 | 引言驗證：載體、語法錨定、卡面送達、取不到即 NE、同一函式回查（PRD AC-SI-12-4） | AT-212-4-E-1 | （DC）附件時序負控：打出時刻早於卡面送達但物理上注入在其後、等於同一時刻、時間戳缺或不可解析 | ✅ | Integration | □ |
| AC-212-4 | 引言驗證：載體、語法錨定、卡面送達、取不到即 NE、同一函式回查（PRD AC-SI-12-4） | AT-212-4-E-2 | （DC）卡面負控：被改寫的卡面、卡面只在較早的 assistant 文字、卡面在 tool_result 或 user 記錄、`card_sha256` 與重建不符 | ✅ | Integration | □ |
| AC-212-4 | 引言驗證：載體、語法錨定、卡面送達、取不到即 NE、同一函式回查（PRD AC-SI-12-4） | AT-212-4-E-3 | （DC）已存 `dec` 的回查：偽造的 `dec`（格式合法、引言不在逐字稿）使 `check` 紅；逐字稿取不到＝NE 不判紅；各種回查失敗碼 | ✅ | Integration | □ |
| AC-212-4 | 引言驗證：載體、語法錨定、卡面送達、取不到即 NE、同一函式回查（PRD AC-SI-12-4） | AT-212-4-E-4 | （DC）逐字稿結構：BOM、CRLF、空白行計入實體行號、壞行、結構判定而非子字串比對、附件的行號取附件記錄本身 | ✅ | Integration | □ |
| AC-213-1 | 拒絕紀錄含理由類（PRD AC-SI-13-1） | AT-213-1-1 | （DC）`reason_class` 七值對 `reject`、`decline-promote`、`return` 皆受理，DEC 記 `reason_class` 與理由句 | ✅ | Integration | □ |
| AC-213-1 | 拒絕紀錄含理由類（PRD AC-SI-13-1） | AT-213-1-E-1 | （DC）理由類負控：缺、七值之外、不收的 dkind 給了、「未說明」的最嚴對應 | ✅ | Integration | □ |
| AC-213-2 | 同型冷卻（PRD AC-SI-13-2） | AT-213-2-1 | （EP）同型冷卻的正控：被否決後同型 `prop-new` 被擋；不同型放行；(a) 解除與 (b-2) 新證據後可再提，須附 `reject_response` | ✅ | Integration | □ |
| AC-213-2 | 同型冷卻（PRD AC-SI-13-2） | AT-213-2-E-1 | （EP）冷卻解除條件的負控：證據相交、未確認根因、新證據不新、DEF 列、「未說明」最嚴、退回不啟動冷卻 | ✅ | Integration | □ |
| AC-213-3 | 冷卻繞過偵測（PRD AC-SI-13-3） | AT-213-3-1 | （EP）合法的再提案不被標成冷卻繞過（解除後再提、不同型）；(b-2) 新證據路徑是離線重放不到的誠實劃界，只出 warn；`status` 列出冷卻與其 `reason_class` | ✅ | Integration | □ |
| AC-213-3 | 冷卻繞過偵測（PRD AC-SI-13-3） | AT-213-3-E-1 | （EP）冷卻被繞過（手寫事件）時 `check` 標 warn `COOLDOWN-BYPASS-SUSPECT`（偵測型 D）；項目狀態不變 | ✅ | Integration | □ |
| AC-215-1 | 沙盒隔離與正式面不變（PRD AC-SI-15-1） | AT-215-1-1 | （SB）沙盒正控：只作用於樹外的 `git archive` 匯出副本、正式面逐字不變、`sandbox_sha256` 可由獨立實作重算 | ✅ | Integration | □ |
| AC-215-1 | 沙盒隔離與正式面不變（PRD AC-SI-15-1） | AT-215-1-2 | （SB）M 類（記憶檔）沙盒與既有沙盒目錄的重建：M 類只複製被觸及的記憶檔、真記憶目錄位元組不變；前一輪遺留的 `<si>/sandbox/<P>` 被整個換掉 | ✅ | Integration | □ |
| AC-215-1 | 沙盒隔離與正式面不變（PRD AC-SI-15-1） | AT-215-1-E-1 | （SB）沙盒根的位置負控：根在 repo 樹內、路徑含 `.claude/worktrees/` 片段、沙盒目錄經符號連結指向樹內、清理目標本身是連結——rc 3、零寫入、清理不跟隨連結 | ✅ | Integration | □ |
| AC-215-1 | 沙盒隔離與正式面不變（PRD AC-SI-15-1） | AT-215-1-E-2 | （SB）`sandbox` 的前置與用法負控：態、凍結、DEC 回查、逐字稿、digest、記憶目錄、無人值守、不存在、用法與家目錄；全部零殘留，既有沙盒目錄維持原狀；鎖內重驗競態 | ✅ | Integration | □ |
| AC-215-1 | 沙盒隔離與正式面不變（PRD AC-SI-15-1） | AT-215-1-E-3 | （SB）套用不受機器 `core.autocrlf` 影響：以含 `autocrlf = true` 的 `GIT_CONFIG_GLOBAL` 重現 Windows 預設，沙盒仍得到 LF 位元組且回滾乾跑逐位元還原 | ✅ | Integration | □ |
| AC-215-1 | 沙盒隔離與正式面不變（PRD AC-SI-15-1） | AT-215-1-E-4 | （SB）tar 抽取預檢負控：路徑穿越、絕對路徑、磁碟機代號與資料流、控制字元、尾端點或空白、非一般檔型別、同名重複、路徑過長邊界；`tarfile.data_filter` 缺席 rc 3 不降級 | ✅ | Unit | □ |
| AC-215-2 | 不使用毀滅性 git 形態（PRD AC-SI-15-2） | AT-215-2-1 | （SB）不使用鐵律五的毀滅性 git 形態：靜態掃描套件原始碼，並以執行期記錄器對整條沙盒到回滾的流程驗證每個 `git` 子行程的子命令 | ✅ | Integration | □ |
| AC-215-2 | 不使用毀滅性 git 形態（PRD AC-SI-15-2） | AT-215-2-E-1 | （SB）掃描判準自證與清理語意：毀滅性形態被判紅、白名單形態不誤判；清理只丟棄該 PROP 的副本，不經 git、不動兄弟目錄與 repo | ✅ | Unit | □ |
| AC-215-3 | 遇擋寫不得繞過（流程型；PRD AC-SI-15-3） | AT-215-3-1 | （MT）遇 R-9.6 擋寫或 harness 分類器拒絕時不得繞過：SOP 條文在場；機器守的一半——觸及 `.claude/**` 的提案不進採納流程 | ✅ | Integration | □ |
| AC-215-3 | 遇擋寫不得繞過（流程型；PRD AC-SI-15-3） | AT-215-3-E-1 | （MT）即使核准當時的規則較寬而使提案走 loop 路由，`promote` 也以當下規則重驗而不寫守衛面（`.claude/**`）；SOP 條文逐項刪去被判紅 | ✅ | Integration | □ |
| AC-215-4 | 沙盒失敗仍寫事件（PRD AC-SI-15-4） | AT-215-4-1 | （SB）沙盒失敗仍寫 `app.sandbox`：patch 套不上、`touched` 超集、回滾乾跑不過、`git apply` 逾時——欄位如實、PROP 進 `sandboxed`、rc 0、`applied=false` 者印 OBS 草稿列 | ✅ | Integration | □ |
| AC-215-4 | 沙盒失敗仍寫事件（PRD AC-SI-15-4） | AT-215-4-E-1 | （SB）失敗之後的收尾：不可靜默重試、無半成品與暫名目錄、兄弟沙盒不受影響、匯出失敗沒有沙盒目錄而套用失敗有（逐位元為 base） | ✅ | Integration | □ |
| AC-215-4 | 沙盒失敗仍寫事件（PRD AC-SI-15-4） | AT-215-4-E-2 | （SB）匯出階段的四種失敗與成因碼：git 失敗、匯出逾時、成員被拒（真 git 的符號連結成員）、`Git.run` 逾時上界取自參數 | ✅ | Integration | □ |
| AC-216-1 | 人工晉升、不 commit（PRD AC-SI-16-1） | AT-216-1-1 | （PM）晉升正控：PASS 配前式、NE 配「未驗採納」後式；patch 合入正式面工作樹、不 commit、HEAD 與 `git log` 與暫存區不變、PROP 態為 `promoted` | ✅ | Integration | □ |
| AC-216-1 | 人工晉升、不 commit（PRD AC-SI-16-1） | AT-216-1-E-1 | （PM）`promote` 的前置負控：態、無決定、式與 verdict 不符（含 FAIL）、digest 被改、無人值守、不存在、M 類記憶目錄與前像、主工作樹已漂移、用法；全部零變更 | ✅ | Integration | □ |
| AC-216-1 | 人工晉升、不 commit（PRD AC-SI-16-1） | AT-216-1-E-2 | （PM）DEC 回查 fail-closed：對 `approve` 與 `promote` 兩筆 DEC 以同一函式回查；逐字稿取不到、引言不符、出處非真人、卡面未送達、Console 稽核檔缺或金鑰缺，一律拒絕、不降為通過 | ✅ | Integration | □ |
| AC-216-2 | 回滾乾跑為晉升前提（PRD AC-SI-16-2） | AT-216-2-1 | （PM）回滾配方乾跑通過才可晉升：`rollback_ok` 與 `touched_ok` 皆 `true` 時 `decide --kind promote` 受理、`promote` 再驗通過；乾跑結果可由獨立實作重算 | ✅ | Integration | □ |
| AC-216-2 | 回滾乾跑為晉升前提（PRD AC-SI-16-2） | AT-216-2-E-1 | （PM）乾跑未通過或 touched 超集時晉升前提不成立：記 DEC 時就擋，繞過 `decide` 的手寫 DEC 也被 `promote` 在寫主工作樹前再驗一次擋下 | ✅ | Integration | □ |
| AC-216-3 | 晉升記錄的內容（PRD AC-SI-16-3） | AT-216-3-1 | （PM）晉升記錄的內容：晉升者、時間帶 offset、`head_sha`、前後 manifest 快照座標可由獨立實作重算；沒有 `commit_sha`；新增檔的 `absent` 語意 | ✅ | Integration | □ |
| AC-216-3 | 晉升記錄的內容（PRD AC-SI-16-3） | AT-216-3-E-1 | （PM）晉升與回滾不 commit：事件沒有 `commit_sha`、`head_sha` 形態受檢；`HEAD`、`git log`、暫存區皆不變 | ✅ | Integration | □ |
| AC-217-1 | 驗證有界：逾時與複驗次數上限（PRD AC-SI-17-1） | AT-217-1-1 | （VF）驗證在上限內完成的正控：探針在 `probe_timeout_seconds` 內結束不被誤殺；複驗到 `verify_runs_max` 次為止仍受理（上限含端點） | ✅ | Integration | □ |
| AC-217-1 | 驗證有界：逾時與複驗次數上限（PRD AC-SI-17-1） | AT-217-1-E-1 | （VF）`app.verify` 超過 `verify_runs_max`：rc 1、須升級人工、零殘留；上限取自參數、以 `(prop, rev)` 計；手寫帳本超限被 `check` 標紅 | ✅ | Integration | □ |
| AC-217-1 | 驗證有界：逾時與複驗次數上限（PRD AC-SI-17-1） | AT-217-1-E-2 | （VF）探針逾時：殺行程樹、收 NE（不收 FAIL）、其後步驟不執行、`PROBE-TIMEOUT` 記入、孫行程不殘留、整體有界 | ✅ | Integration | □ |
| AC-217-2 | SUSPENDED 與 resume（PRD AC-SI-17-2） | AT-217-2-1 | （PM）SUSPENDED 與恢復正控：只有掌舵者的 `dec(resume)`（綁折疊出的運轉）能恢復；SUSPENDED 期間 `prop-new` 與 `prop-revise` 拒收、恢復後受理；本迴圈不碰 FSM | ✅ | Integration | □ |
| AC-217-2 | SUSPENDED 與 resume（PRD AC-SI-17-2） | AT-217-2-E-1 | （PM）沒有任何其他路徑恢復 SUSPENDED：其他寫入動詞不解除、RUN 不符與未 SUSPENDED 被拒、舊回覆重播被拒、無人值守與引言文法負控 | ✅ | Integration | □ |
| AC-218-1 | 審查者與提案者分離（流程型；PRD AC-SI-18-1） | AT-218-1-1 | （MT）審查者條文正控：SOP〈審查者〉節含四項流程條文；機器能守的那一半（審查者≠提案者、凍結者≠提案者）在合法分工下受理 | ✅ | Integration | □ |
| AC-218-1 | 審查者與提案者分離（流程型；PRD AC-SI-18-1） | AT-218-1-E-1 | （MT）審查者條文的負控：機器守的一半被擋（審查者等於提案者、凍結者等於提案者）；條文逐項刪去被判紅 | ✅ | Integration | □ |
| AC-218-2 | 判定主依據為外部可重跑訊號（PRD AC-SI-18-2） | AT-218-2-1 | （VF）判定的主依據是外部可重跑訊號：同一組探針在同一 base 的全新沙盒重跑得到相同的 rc 序列；提案本文與審查文字不影響 verdict | ✅ | Integration | □ |
| AC-218-2 | 判定主依據為外部可重跑訊號（PRD AC-SI-18-2） | AT-218-2-E-1 | （VF）沒有覆寫 verdict 的路徑：旗標一律拒收；手改事件的 verdict（把 FAIL 改成 PASS）被 `check` 的 `events.verdict` 標紅；欄位全部自洽的偽 PASS 是誠實劃界 | ✅ | Integration | □ |
| AC-219-1 | 對照與突變三步、載具自證（PRD AC-SI-19-1） | AT-219-1-1 | （VF）三步對照的正控：基線重現症狀（RED）、套用後消失（GREEN）、突變後回來（RED）→ PASS；證據檔與事件欄位齊備；每個探針每步恰執行一次；沙盒樹還原 | ✅ | Integration | □ |
| AC-219-1 | 對照與突變三步、載具自證（PRD AC-SI-19-1） | AT-219-1-E-1 | （VF）三步缺一的負控：基線不紅、套用不綠、突變不紅、無突變、突變來源重複；三步不因早失敗而略過 | ✅ | Integration | □ |
| AC-219-1 | 對照與突變三步、載具自證（PRD AC-SI-19-1） | AT-219-1-E-2 | （VF）載具自證：模組在沙盒內才算數；上層 `PYTHONPATH` 不洩入；不帶 `-I`；未宣告 `module` 時自證為真（空集合語意） | ✅ | Integration | □ |
| AC-219-1 | 對照與突變三步、載具自證（PRD AC-SI-19-1） | AT-219-1-E-3 | （VF）`verify` 的前置與用法負控：態、凍結、無人值守、不存在、參數鍵、旗標、沙盒樹漂移與重新匯出、鎖內重驗競態；全部零殘留 | ✅ | Integration | □ |
| AC-219-2 | 三態判定與 NE 語意（PRD AC-SI-19-2） | AT-219-2-1 | （VF）三態判定表的正控：`verdict_of` 純函式逐列、決定層全部成立碼；M／D 類無確定性探針預設 NE（`NO-PROBES`） | ✅ | Unit | □ |
| AC-219-2 | 三態判定與 NE 語意（PRD AC-SI-19-2） | AT-219-2-E-1 | （VF）沙盒失敗先於預檢：`verify` 不跑探針、直接收 NE（或 FAIL）；`check` 的 `events.verdict` 認得它並偵測欄位不自洽 | ✅ | Integration | □ |
| AC-219-3 | 命中率只是證據、不自動核准（PRD AC-SI-19-3） | AT-219-3-1 | （VF）命中率只是證據、不得據此自動核准：`verify` 不寫 `dec`、不改 PROP 於核准或晉升的態、事件與驗證檔沒有命中率欄位；R 類（SDD 規則草案）走轉交、進不了沙盒與驗證 | ✅ | Integration | □ |
| AC-219-3 | 命中率只是證據、不自動核准（PRD AC-SI-19-3） | AT-219-3-E-1 | （VF）沒有任何自動核准或晉升的旗標與路徑：`verify` 與 `sandbox` 不收 `--approve`、`--auto-promote`、`--hit-rate` 等；用法錯誤 rc 3、零寫入 | ✅ | Integration | □ |
| AC-220-1 | held-out 凍結（PRD AC-SI-20-1） | AT-220-1-1 | （EP）`heldout-freeze` 正控：複製目錄、算 digest、事件以 `prop` 為鍵 | ✅ | Integration | □ |
| AC-220-1 | held-out 凍結（PRD AC-SI-20-1） | AT-220-1-E-1 | （EP）`heldout-freeze` 的拒收：凍結者即提案者、重複凍結、已有沙盒、手冊形態錯、來源不在、`--from` 在家目錄之內、連結、handoff | ✅ | Integration | □ |
| AC-220-1 | held-out 凍結（PRD AC-SI-20-1） | AT-220-1-E-2 | （EP）凍結先於沙盒：無凍結的 `sandbox` 被拒；手寫的凍結次序與凍結者違規被 `check` 標紅 | ✅ | Integration | □ |
| AC-220-2 | held-out 規模下限（PRD AC-SI-20-2） | AT-220-2-1 | （VF）評估集規模達 `min_heldout` 時不因小樣本判 NE：案例數恰等於下限放行；下限取自參數 | ✅ | Integration | □ |
| AC-220-2 | held-out 規模下限（PRD AC-SI-20-2） | AT-220-2-E-1 | （VF）小樣本不得宣稱有效：`n` 小於 `min_heldout` ⇒ NE，即使三步全成立；NE 不能以前式晉升 | ✅ | Integration | □ |
| AC-220-3 | 不可進化面於晉升時重驗（PRD AC-SI-20-3） | AT-220-3-1 | （PM）合法 PROP 的晉升重驗通過：以當下參數與當下 LATEST 重新解析 patch 全部路徑，未命中不可進化面時放行 | ✅ | Integration | □ |
| AC-220-3 | 不可進化面於晉升時重驗（PRD AC-SI-20-3） | AT-220-3-E-1 | （PM）可進化面在核准之後縮小：當下重驗命中即拒絕並改走轉交、不寫事件、不動主工作樹 | ✅ | Integration | □ |
| AC-220-4 | 預檢：digest 重算與暴露掃描（PRD AC-SI-20-4） | AT-220-4-1 | （VF）預檢正控：held-out 目錄 digest 重算相符；暴露掃描在可評估且未命中時不產生 NE；掃描範圍只含子代理逐字稿中凍結時刻之後的工具呼叫（含針但早於凍結者不計） | ✅ | Integration | □ |
| AC-220-4 | 預檢：digest 重算與暴露掃描（PRD AC-SI-20-4） | AT-220-4-E-1 | （VF）預檢負控：held-out 被改動、子代理逐字稿在凍結時刻之後的工具呼叫命中凍結目錄、`params.json`、量測腳本（缺或不可解析的時間戳視為窗口內）——皆 NE、探針照常跑、只量不阻擋 | ✅ | Integration | □ |
| AC-220-4 | 預檢：digest 重算與暴露掃描（PRD AC-SI-20-4） | AT-220-4-E-2 | （VF）暴露掃描的量不到與範圍邊界：逐字稿目錄不存在 ⇒ `EXPOSURE-UNKNOWN`（不是未命中）；壞行不使掃描失敗；只掃 `subagents/**` 的 assistant `tool_use` | ✅ | Integration | □ |
| AC-221-1 | 驗證證據逐字入帳（PRD AC-SI-21-1） | AT-221-1-1 | （VF）證據入帳正控：每筆 `rec` 含指令、rc、輸出摘錄座標、母體數；`out_sha256` 與 `out_bytes` 可獨立重算；`tail` 不超過 300 位元組且不切半個字元；原始輸出全文不落任何檔 | ✅ | Integration | □ |
| AC-221-1 | 驗證證據逐字入帳（PRD AC-SI-21-1） | AT-221-1-E-1 | （VF）機密與環境的負控：遮蔽四型、環境白名單（不繼承 `AUTOSDD_*`、金鑰環與上層 `PYTHONPATH`）、輸出極大時摘要仍有界、CLI 輸出不含金鑰子字串 | ✅ | Integration | □ |
| AC-221-1 | 驗證證據逐字入帳（PRD AC-SI-21-1） | AT-221-1-E-2 | （VF）驗證檔完整性的負控：`verify<K>.json` 被改一個字元、被刪、被多加一個換行，或事件的 `verify_sha256` 被手改，`check` 的 `events.prop_files` 各回對應碼；未動時為綠；無探針的驗證不產生驗證檔、也不被要求有 | ✅ | Integration | □ |
| AC-221-2 | 證據條文（流程型；PRD AC-SI-21-2） | AT-221-2-1 | （MT）證據條文正控：SOP 含逐字入帳、轉述標記、親跑升格、貼不出改寫四項；機器守的一半——驗證證據含執行者與帶 offset 的時間 | ✅ | Integration | □ |
| AC-221-2 | 證據條文（流程型；PRD AC-SI-21-2） | AT-221-2-E-1 | （MT）證據條文有牙：逐項刪去或移入圍欄被判紅；`verify` 的非 PASS 結果不被靜默吞掉（草稿列與 verdict 並列） | ✅ | Integration | □ |
| AC-230-2 | 來源表 host 僅限 ASCII（PRD AC-SI-30-2 的 P2 收口） | AT-230-2-1 | （RS）來源表 host 僅限 ASCII 的正控：合規的 ASCII host（含大寫、帶埠、`xn--` 只出現在 label 中段、單連字號的 `xn-`）不被新規則誤判；真來源表仍 PASS | ✅ | Unit | □ |
| AC-230-2 | 來源表 host 僅限 ASCII（PRD AC-SI-30-2 的 P2 收口） | AT-230-2-E-1 | （RS）非 ASCII 與 IDNA 形態的 host 一律拒收：全形數字與字母、表意句號、中文、任一 label 以 `xn--`（不分大小寫）起頭；不做正規化後比對 | ✅ | Unit | □ |
| AC-230-2 | 來源表 host 僅限 ASCII（PRD AC-SI-30-2 的 P2 收口） | AT-230-2-E-2 | （RS）`research --fetch` 在發出任何請求之前先過表驗證：含非 ASCII host 的表使整次 rc 1、不抓、不寫事件、零連線（即使表內另有合規的 loopback 來源） | ✅ | Integration | □ |
| AC-233-1 | Console 載體的 `decide`（PRD AC-SI-33-1 的根層半） | AT-233-1-1 | （CN）`decide --carrier console` 九個動詞（晉升兩式）正控：稽核檔經 HMAC 驗證、與逐字稿載體同一組前提，`dec` 帶 `carrier=console` 與稽核座標；不要求卡面送達 | ✅ | Integration | □ |
| AC-233-1 | Console 載體的 `decide`（PRD AC-SI-33-1 的根層半） | AT-233-1-2 | （CN）跨語言測試向量：以標準庫 `hmac` 加 `hashlib` 重算須與本檔逐字列出的 `body` 字串、`mac`、`key_id` 完全相同，且 `consoleaudit` 對四組向量驗證通過 | ✅ | Unit | □ |
| AC-233-1 | Console 載體的 `decide`（PRD AC-SI-33-1 的根層半） | AT-233-1-E-1 | （CN）稽核檔驗證失敗表：每個違規恰一個碼、rc 1、零寫入、CLI 不寫 `console_audit/` | ✅ | Integration | □ |
| AC-233-1 | Console 載體的 `decide`（PRD AC-SI-33-1 的根層半） | AT-233-1-E-2 | （CN）重複入帳、無人值守、用法與狀態層前提：同一 `audit_ref` 不得二次入帳（跨 kind 計）；與逐字稿載體同一組前提；`STALE-CARD` 取自 `body.digest` | ✅ | Integration | □ |
| AC-233-1 | Console 載體的 `decide`（PRD AC-SI-33-1 的根層半） | AT-233-1-E-3 | （CN）向量負控與金鑰衛生：body 改一字、換金鑰、`time` 改 `Z` 各自轉紅；金鑰環選用依 `key_id`；任何輸出不含金鑰的 8 字元子字串 | ✅ | Integration | □ |
| AC-233-2 | Console 決定與稽核檔對帳（PRD AC-SI-33-2 的根層半） | AT-233-2-1 | （CN）Console 決定與稽核檔對帳正控：逐欄相符、HMAC 相符時 `events.dec_console` 為 `PASS` | ✅ | Integration | □ |
| AC-233-2 | Console 決定與稽核檔對帳（PRD AC-SI-33-2 的根層半） | AT-233-2-E-1 | （CN）對帳負控：欄位不符、雜湊與 HMAC 不符＝FAIL；稽核檔或金鑰不在場＝nonblocking NE（不是零筆通過） | ✅ | Integration | □ |
| AC-235-1 | `obs-add`（PRD AC-SI-35-1） | AT-235-1-1 | （CN）`obs-add` 正控：驗簽、組列、於寫入鎖內先列後事件，列的九欄與標記逐字等於預期，其餘帳本位元組不變、不 commit | ✅ | Integration | □ |
| AC-235-1 | `obs-add`（PRD AC-SI-35-1） | AT-235-1-2 | （CN）`obs-add --dry-run` 唯讀預檢：預覽的列與實寫逐字相同、零寫入、不需家目錄與金鑰、`--json` 形態與 Bridge 驗證端點同形 | ✅ | Integration | □ |
| AC-235-1 | `obs-add`（PRD AC-SI-35-1） | AT-235-1-E-1 | （CN）`obs-add` 本文規則負控：每個違規一個碼、組列後自驗（`evaluate_rows`）、列位元組 700 放行 701 拒收；任一不符零變動 | ✅ | Integration | □ |
| AC-235-1 | `obs-add`（PRD AC-SI-35-1） | AT-235-1-E-2 | （CN）寫入順序與回退：先列後事件；事件追加失敗時回退列、帳本已被他人動過則不動並印 `OBS-ORPHAN`；ID 於鎖內重讀帳本後配號、並行不重號 | ✅ | Integration | □ |
| AC-235-1 | `obs-add`（PRD AC-SI-35-1） | AT-235-1-E-3 | （CN）動態純度：唯讀動詞與 `obs-add --dry-run` 的行程不載入寫入類、`exec`、`net` 模組；以子行程的 import 時間表判，並以寫入動詞自證判準有牙 | ✅ | Integration | □ |
| AC-235-2 | `obs-close`（PRD AC-SI-35-2） | AT-235-2-1 | （CN）`obs-close` 正控：只有 `open` 變終值一次；只動該列第 8 欄、其餘位元組逐字不變；原子改寫；同鎖內追加 `obs.close`；七種終值形態皆可 | ✅ | Integration | □ |
| AC-235-2 | `obs-close`（PRD AC-SI-35-2） | AT-235-2-E-1 | （CN）`obs-close` 前置負控：不存在、只在封存檔、非 `open`、終值不合、缺附加文字、含 `／`、改寫後超列長、帳本在預檢後被改動 | ✅ | Integration | □ |
| AC-235-2 | `obs-close`（PRD AC-SI-35-2） | AT-235-2-E-2 | （CN）原子改寫的失敗路徑：寫暫名檔或 `os.replace` 失敗＝rc 1、帳本未變、暫名檔清掉、單次嘗試不重試、不追加 `obs.close` | ✅ | Integration | □ |
| AC-235-3 | 沒有刪除與改號（PRD AC-SI-35-3） | AT-235-3-1 | （CN）CLI 的全部介面沒有刪除或改號能力：OBS 寫入動詞恰 `obs-add` 與 `obs-close`；任何名為刪除、改號、編輯的動詞一律 rc 3；退場只能是處置終值 `retired：<座標>` | ✅ | Integration | □ |
| AC-235-3 | 沒有刪除與改號（PRD AC-SI-35-3） | AT-235-3-E-1 | （CN）改寫不變量：任意序列的 `obs-add` 與 `obs-close` 之後列數只增不減、ID 序列嚴格遞增且不重號、既有列的第 1～7、9 欄位元組不變；更正走新列 | ✅ | Integration | □ |
| AC-235-4 | Console 帳號資格（PRD AC-SI-35-4 的根層半） | AT-235-4-1 | （CN）資格正控：`role` 為 `ADMIN`、帳號名合 `^[A-Za-z0-9_.-]{1,64}$` 時受理，帳號名進 `回報者` 與事件 `decider` | ✅ | Integration | □ |
| AC-235-4 | Console 帳號資格（PRD AC-SI-35-4 的根層半） | AT-235-4-E-1 | （CN）資格負控：非 ADMIN、帳號名含會破壞標記欄的字元、過長、缺鍵；標記注入無從得逞 | ✅ | Integration | □ |
| AC-235-5 | Console 寫入對帳與待入帳（PRD AC-SI-35-5 的根層半） | AT-235-5-1 | （CN）`check` 與 `status` 正控：帶 `carrier=console` 的列有 `obs.add` 且稽核檔逐欄相符、HMAC 相符；`status` 列出尚未入帳的稽核檔 | ✅ | Integration | □ |
| AC-235-5 | Console 寫入對帳與待入帳（PRD AC-SI-35-5 的根層半） | AT-235-5-E-1 | （CN）對帳負控：缺事件、處置未改、欄位不符、稽核檔或金鑰不在場＝NE 而非零筆通過、標記值域與成對與唯一 | ✅ | Integration | □ |
| AC-240-1 | 事件詞彙與欄位表（本檔自增） | AT-240-1-1 | （EP）`KINDS` 為 21 個；九種 P2 事件的完整欄位通過單事件判準；升級後的夾具建構器與 P1 既有呼叫形態的輸出全部合規 | ✅ | Unit | □ |
| AC-240-1 | 事件詞彙與欄位表（本檔自增） | AT-240-1-E-1 | （EP）欄位表負控：缺必備鍵、表外鍵、型別與值域、條件必備、null 規則、載體互斥 | ✅ | Unit | □ |
| AC-240-1 | 事件詞彙與欄位表（本檔自增） | AT-240-1-E-2 | （EP）事件行位元組上界的邊界：`dec` 的行長 L 放行、L 減 1 拒收（寫入端與 `check` 端） | ✅ | Integration | □ |
| AC-240-2 | 狀態機與帳本不變式（本檔自增） | AT-240-2-1 | （EP）P2 全轉移表的正控：完整生命週期、NE 以未驗採納晉升、沙盒失敗退回後重提、複驗邊、`Prop` 新欄、冷卻欄 `reason_class` | ✅ | Integration | □ |
| AC-240-2 | 狀態機與帳本不變式（本檔自增） | AT-240-2-E-1 | （EP）非法轉移負控：越級、前提不符、複驗超限、無對應 dec 的 app.promote | ✅ | Integration | □ |
| AC-240-2 | 狀態機與帳本不變式（本檔自增） | AT-240-2-E-2 | （EP）帳本不變式負控：凍結者、重複凍結、凍結晚於沙盒、base 不符、晉升 ack 不符、回滾 manifest 不符、DEC 的 digest 不符 | ✅ | Integration | □ |
| AC-240-2 | 狀態機與帳本不變式（本檔自增） | AT-240-2-E-3 | （EP）寫入端與重放端用同一前提：`decide` 與 `fold` 在（動詞 dkind × 態）格點上逐格一致 | ✅ | Integration | □ |
| AC-240-3 | `check` 的 P2 追加項（本檔自增） | AT-240-3-1 | （EP）`check` 共 32 項：P0 21 項與 P1 7 項原樣（以 §5.6 的 28 項常數表判定；唯一有意差異是 R1 的 `ref.carrier_families`，R104）、P2 四項接其後；載體缺席一律 nonblocking NE；P0 基線 repo 的 rc 與 overall 不變；`CHECK_RULES_REV` 為 3 | ✅ | Integration | □ |
| AC-240-3 | `check` 的 P2 追加項（本檔自增） | AT-240-3-E-1 | （EP）四個追加項的失敗碼與 P1 warn 的移除 | ✅ | Integration | □ |
| AC-240-4 | `params.json` 兩個新鍵（本檔自增） | AT-240-4-1 | （EP）`params.json` 為 30 鍵，兩個新鍵被 `sandbox` 與 `verify` 讀用 | ✅ | Integration | □ |
| AC-240-4 | `params.json` 兩個新鍵（本檔自增） | AT-240-4-E-1 | （EP）新鍵缺、型別或範圍不符：`check` 紅、動詞 rc 3 並點名、不以預設值頂替 | ✅ | Integration | □ |
| AC-240-5 | 能力登記第四類 exec（本檔自增） | AT-240-5-1 | （CP）能力登記正控：40 鍵四類（29 `ro`／7 `rw`／2 `net`／2 `exec`）、`exec` 恰兩檔、`subprocess` 字樣只在 `git.py` 與 `runner.py`、import `runner` 者為 `exec`、唯讀動詞閉包全 `ro`、平台守衛站點 | ✅ | Unit | □ |
| AC-240-5 | 能力登記第四類 exec（本檔自增） | AT-240-5-E-1 | （CP）能力登記判準有牙：對真套件的 tmp 副本逐項注入違規，`capability_problems` 各回對應問題；未動的副本為空 | ✅ | Unit | □ |
| AC-240-5 | 能力登記第四類 exec（本檔自增） | AT-240-5-E-2 | （CP）子行程出口的靜態不變量與根層平台守衛：`shell=False`、`communicate(timeout=…)`、不帶 `-I`／`-P`、無禁字樣；根層三個平台守衛測試類別與兩張債表不因 P2 新增任何項目 | ✅ | Integration | □ |
| AC-240-6 | `card --issue`（本檔自增） | AT-240-6-1 | （EP）`card --issue` 記 `card` 事件，stdout 卡面與不帶旗標逐位元組相同 | ✅ | Integration | □ |
| AC-240-6 | `card --issue`（本檔自增） | AT-240-6-E-1 | （EP）`card --issue` 的態前提與無人值守：非 §7.2 前提態拒收 | ✅ | Integration | □ |
| AC-240-7 | `rollback`（本檔自增） | AT-240-7-1 | （PM）回滾正控：`touched` 路徑現況等於晉升後 manifest 時，反向套用逐位元還原為晉升前、記 `app.rollback`、PROP 態不變、不 commit | ✅ | Integration | □ |
| AC-240-7 | `rollback`（本檔自增） | AT-240-7-E-1 | （PM）回滾負控：態不是已晉升、無回滾決定、DEC 回查失敗、晉升後樹被他處改動、反向結果不等於晉升前、記憶目錄缺；全部零變更 | ✅ | Integration | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-1 | （AL）取鎖：`os.open` 遇 `PermissionError`（Windows 刪除待決）視同忙碌、納入有界重試，之後取鎖成功 | ✅ | Unit | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-2 | （AL）陳舊鎖回收：`unlink` 遇 `PermissionError` 視為「這輪沒收成」，與 `FileNotFoundError` 同樣不是錯誤，下一輪有界重試後回收成功 | ✅ | Unit | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-3 | （AL）釋放：`unlink` 遇 `PermissionError` 為有界重試，初次嘗試之後最多再重試 `RELEASE_RETRIES` 次；邊界值成功時鎖檔被刪除、不印警告 | ✅ | Unit | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-E-1 | （AL）取鎖逾時的例外型別：最後一次失敗是 `PermissionError` ⇒ 逾時拋原始 `PermissionError`（不誤報成別的行程持有）；最後一次是 `FileExistsError` ⇒ 仍是 `LockBusyError` 加持鎖者資訊；其他 `OSError` 立即穿出、不納入重試 | ✅ | Unit | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-E-2 | （AL）回收的負控：回收一直被拒時整體仍有界（以 `LockBusyError` 逾時）；回收時其他 `OSError` 不被吞；新鮮鎖永不回收 | ✅ | Unit | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-E-3 | （AL）釋放用盡後不改 rc、不拋例外：印警告到標準錯誤、鎖檔殘留交陳舊回收；區塊本身的例外不被遮蔽；殘留鎖在 `stale_after` 之後被下一個取鎖者回收 | ✅ | Unit | □ |
| AC-240-8 | `apply_lock` 的 Windows 刪除待決（本檔自增） | AT-240-8-E-4 | （AL）`evwrite` 層：釋放用盡時事件已追加、呼叫端回 rc 0 而非 rc 3、輸出不含「帳本未變動」；取鎖階段的 `PermissionError` 逾時仍是 rc 3 且該句為真；`FileExistsError` 逾時仍是 rc 1 的 `LOCK-BUSY` | ✅ | Integration | □ |
| AC-240-9 | AT 序號與錨定規則的可重跑檢查（本檔自增） | AT-240-9-1 | （MT）AT 序號與 `-k` 錨定規則的可重跑檢查正控：本檔每個 AT 的 `-k` 以節點 id 子字串比對恰命中一個測試函式 | ✅ | Integration | □ |
| AC-240-9 | AT 序號與錨定規則的可重跑檢查（本檔自增） | AT-240-9-E-1 | （MT）錨定檢查有牙：以合成測試檔證明「非錨定 `-k` 命中兩個」「無結尾底線」「值與 AT id 不符」「零命中」「重複命中」「缺 slug」各被判紅，錨定形判綠 | ✅ | Integration | □ |
| AC-240-10 | `scan` 的資訊型草稿列（本檔自增） | AT-240-10-1 | （RS）`scan` 的資訊型草稿列與來源行：模組桶候選列為 `process`／`P4`／`decided：僅計數`、缺陷候選列維持 `bug`／`P3`／`open`、三個計數來源的來源行改「計 N 筆（未解析內容）」、JSON 不變 | ✅ | Integration | □ |
| AC-240-10 | `scan` 的資訊型草稿列（本檔自增） | AT-240-10-E-1 | （RS）P1 的拒收草稿列與 `check` 草稿列維持 `bug`／`P3`／`open`；`status` 的候選與桶計數、零候選規則不變；失敗草稿列不被資訊型規則波及 | ✅ | Integration | □ |
| AC-240-11 | `ref.carrier_families` 存在性判（本檔自增） | AT-240-11-1 | （EP）`ref.carrier_families` 對 ATT／PROP／RUN 三族的指標形態引用做存在性判：全部解析得到時 PASS | ✅ | Integration | □ |
| AC-240-11 | `ref.carrier_families` 存在性判（本檔自增） | AT-240-11-E-1 | （EP）指向不存在的 ATT／PROP／RUN 的指標引用：事件帳本內與提案目錄的被標紅（FAIL）、OBS 列處置的懸空 `proposed@` 指標印 warn；真 repo 零假紅 | ✅ | Integration | □ |
| AC-240-12 | `export` 的 `buckets[]` 與 `status` 的 `console_pending`（本檔自增） | AT-240-12-1 | （CN）`export` 的 observations 項加 `buckets[]`（不 casefold、同一個 `scan.bucket_of`）；`status` 加 `console_pending`；`export --kind status` 的同鍵量不到 | ✅ | Integration | □ |
| AC-240-12 | `export` 的 `buckets[]` 與 `status` 的 `console_pending`（本檔自增） | AT-240-12-E-1 | （CN）`export` 不讀家目錄任何檔：以哨兵字串釘住；`status` 只列稽核檔目錄清單、不讀其內容；缺家目錄時 NOT-EVALUABLE 而非空清單 | ✅ | Integration | □ |
| AC-240-13 | SOP〈P2 動詞〉定稿（本檔自增；流程型） | AT-240-13-1 | （MT）Operations SOP〈P2 動詞〉定稿的正控：標題無「待補」、rc 契約表九列、最小序列、Console 載體、審查者、R-9.6、證據條文、流程摩擦時點 | ✅ | Unit | □ |
| AC-240-13 | SOP〈P2 動詞〉定稿（本檔自增；流程型） | AT-240-13-E-1 | （MT）SOP 判準有牙：對真 SOP 的副本逐項刪去必備片段，`sop_p2_problems` 各點名該項；條文只放在程式碼圍欄內不算數；序列順序對調被判紅；「待補」復現被判紅 | ✅ | Unit | □ |
| AC-240-14 | 零退化（本檔自增） | AT-240-14-1 | （MT）零退化正控：升級後夾具重放全部 P1 情境表皆合規；P0 與 P1 的全部 AT 在測試檔中各有對應函式（P1 斷言值只於 R107 (c) 列出的站點同步，含 R104、R110 造成的兩處）；`params` 規格為 28 加 2 鍵 | ✅ | Integration | □ |
| AC-240-14 | 零退化（本檔自增） | AT-240-14-E-1 | （MT）夾具升級不吞掉違規：呼叫端明示的錯誤值不被預設值覆蓋，P1 的負控事件在升級後仍被同一個碼擋下 | ✅ | Unit | □ |
| AC-240-15 | `attr link` 的 `--reopens` 目標（本檔自增；主控裁決） | AT-240-15-1 | （EP）`attr --type link` 的 `--reopens` 目標＝已結列加處置首詞為 `deferred` 的列：三個 `deferred` 形態的列各被連結一次 rc 0 並寫入 `attr` 事件；已結列照舊可連結 | ✅ | Integration | □ |
| AC-240-15 | `attr link` 的 `--reopens` 目標（本檔自增；主控裁決） | AT-240-15-E-1 | （EP）`--reopens` 目標的拒收與不變項：處置首詞為 `open` 者 `REOPENS-NOT-CLOSED`、不存在者 `REOPENS-NOT-FOUND`、`--from` 不存在者 `OBS-NOT-FOUND`，一律零寫入；復發候選提示（R45 的 `REOPEN-CANDIDATE`）的判準不變，不因 `deferred` 列而多出候選 | ✅ | Integration | □ |

**覆蓋率統計**:
- 總 AC 數: 50（PRD 的 35 個加本檔自增的 15 個）
- 已映射 AT 數: 137（正控 57 個、負控〔E 類〕80 個；每個 AC 至少一個正控與一個負控）
- 各測試檔的 AT 數: DC 18；EP 24；SB 11；VF 21；PM 13；CN 23；MT 12；CP 3；RS 5；AL 7
- 映射覆蓋率: 100% （目標: 100%）

---

---

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_212_1_1]`；E 類為 `[AT_OK_212_1_E_1]`），本節 Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，單引號字元用文字描述。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑判定指令（cwd 為 monorepo 根），**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。判定指令一律為：
> - `python -m pytest tools/tests/<檔名> -k <AT 底線形>_ -q -p no:xdist -o addopts=`（`-p no:xdist -o addopts=` 排除全域 `addopts` 與 xdist 對單一 AT 的影響，與 NFR-P2-10 (1) 同形）
>
> **AT 底線形與錨定 `-k`**：AT 底線形＝把 AT ID 的連字號換成底線（`AT-212-4-E-1` 的底線形是 `AT_212_4_E_1`）；每個 AT 的測試函式名稱為 `test_<AT 底線形>_<slug>`（slug 為非空的小寫英數底線字串，例 `test_AT_212_4_E_1_attachment_time_order`）；判定指令的 `-k` 值＝AT 底線形接一個結尾底線（錨定名，見〈AC 編號規則〉第 4 點與 R102），使 `-k` 的不分大小寫子字串比對恰收一個測試。本檔沒有兩位序號的 AT（每個 AC 內的序號仍不超過 9），規則為日後增補預留，並由 R102 的可重跑檢查釘住。
>
> **測試檔縮寫**（判定指令的檔名依各 AT 標頭所列；全部在 `tools/tests/`）：**DC**＝`test_selfimproving_decide.py`、**EP**＝`test_selfimproving_events_p2.py`、**SB**＝`test_selfimproving_sandbox.py`、**VF**＝`test_selfimproving_verify.py`、**PM**＝`test_selfimproving_promote.py`、**CN**＝`test_selfimproving_console_obs.py`、**MT**＝`test_selfimproving_p2_meta.py`（以上七檔為本檔新增）；**CP**＝`test_selfimproving_capability.py`、**RS**＝`test_selfimproving_research_scan.py`、**AL**＝`test_apply_lock.py`（以上三檔為既有檔，新增 AT 函式並依 R107 同步既有站點）。共用夾具住 `tools/tests/_selfimproving_fixtures.py`（P1 既有，依 R107 升級）與 `tools/tests/_selfimproving_p2_fixtures.py`（新增；底線開頭、不被收集；§5）。
>
> **斷言簡寫**（本節各 AT 共用；建構器與表的定義見 §5）：
> - `M(R, <動詞>, <旗標…>)`＝以 `contextlib.redirect_stdout`／`redirect_stderr` 行程內呼叫 `selfimproving.main`（自動補 `--repo <R>`，AT 另指定者除外），回傳 `(rc, stdout, stderr)`（P1 夾具 `SiTestCase.run_main` 的形態）；`MJ(R, <動詞>, <旗標…>)`＝同上、附 `--json` 並 `json.loads` stdout。旗標以逗號分隔的字面詞書寫（例 `M(R, sandbox, P, --by, SB1)`），不是 Python 字面值。
> - `R`＝`make_p2_repo(...)` 回傳的 tmp git repo（§5.1）；`HOME`＝tmp 內的家目錄，環境變數 `AUTOSDD_SI_DIR` 指向它；`P`、`P1`…＝PROP 號，`RUN`＝運轉號，皆於執行期取自 CLI 輸出（NFR-P2-7：本檔與測試原始碼不寫死不存在於真帳本的編號字面）；`<n>`、`<NNN>`＝輸出中的數字，斷言以正規式判。
> - `snap(R)`＝`R` 內除 `.git/` 之外全部檔案的〔相對路徑→位元組 sha256〕對照加 `git status --porcelain` 輸出（P1 §2 同名簡寫）；`surface(R)`＝`git status --porcelain` 輸出、`git rev-parse HEAD`、`git worktree list` 輸出與 `snap(R)` 的組合（「正式面」）；「**零殘留**」＝拒收後 `snap(R)` 等於拒收前、`HOME` 內除（已釋放的）鎖檔外無新檔（R71）；`codes(out)`＝自拒收輸出的 `  <CODE> <detail>` 行取出的碼集合（P1 夾具 `codes_of`）；`draft_ok(R, out)`＝取拒收輸出 `obs-draft:` 之下那一行附加到 `R` 的複本的 OBS 帳本、跑 `check --json`，該列 ID 的 finding 為零（P1 夾具 `draft_ok`）；`S(項目)`、`F(項目)`＝P1 夾具的同名簡寫（項目狀態、`findings` 的 `(subject, code)` 集合）；「恰為」＝集合相等、「含」＝子集。
> - `drive_to(R, 狀態, …)`、`decide_say(…)`、`forge_dec(…)`、`rewrite_event(…)`、`drop_events(…)`、`make_heldout(…)`、`write_audit(…)`、`make_transcript(…)`、各情境表與負控目錄（`DEC-STATES`、`COOL-BASE`、`NC-01`～`NC-20`、`PC-01`～`PC-03`…）一律定義於 §5。
>
> **變異慣例**：預設自基線複製一份（`shutil.copytree`，含 `.git`）、在工作樹改寫、不 commit；AT 內以「情境 (a)」「第 k 列」等列舉的子情境，測試一律以 `subTest` 或參數化實作（保留 AT ID 對映），任一子情境失敗時失敗訊息須指出是哪個情境。**AT 內不引用其他 AT 的 ID**（只有 §1、§3、§4、§6 的表格引用 AT ID）。**不得 skip**：git 缺席視為環境壞、測試直接失敗（NFR-P2-4）；Windows 專屬案例以替身模擬平台、不跳過。各 AT 只斷言自己指名的項目與集合，除非該 AT 明文寫 `overall` 或 rc。**本節各 AT 的 `Given` 描述測試佈置、`When` 描述被測動作；佈置所需的 git、tar、子行程與檔案系統操作都在 tmp 目錄內，不碰真帳本、真事件帳本、真提案目錄、真家目錄與真逐字稿（NFR-P2-7）。**


**A. DEC 驗證、`decide`（逐字稿載體）與拒絕紀錄（DC）**

```gherkin
# AT-212-1-1
# 對應 AC: AC-212-1（PRD AC-SI-12-1；R77、R78、R80；PC-01）逐字稿載體（user 記錄）的九個動詞正控：各動詞的 DEC 欄位齊備、狀態依 R75 轉移、DEC 附原句與 `sid`＋`line`
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_1_ -q -p no:xdist -o addopts=

Feature: decide 逐字稿載體正控

Scenario: 九個動詞各自在合法前提態下受理，DEC 欄位逐一等於預期
  Given 依 §5.1 建 `R`；對每個動詞以 §5.2 的 `drive_to` 與 `write_events` 備妥前提態（核准用 `proposed` 的 loop 路由；否決用 `proposed` 與 `verified`〔得 `reject` 與 `decline-promote`〕；退回用 `proposed`；晉升用 PASS 的 `verified`（前式）與 NE 的 `verified`（後式，其 `app.sandbox` 的 `rollback_ok` 與 `touched_ok` 皆 `true`）；轉交與不轉交用 `handoff:T1` 的 `proposed`；回滾用 `promoted`；解除用冷卻中的 `rejected`；恢復用折疊出 SUSPENDED 的帳本），並對該 PROP 先 `card --issue`（`resume` 免）
  When 對每個動詞以 §5.3 的 PC-01 形態（卡面核心區在 assistant 文字、其後一則只含 `tool_use` 的 assistant 訊息、再其後 human 的 user 記錄為該動詞的決定行）建合成逐字稿，呼叫 `decide <ID> --kind <導出 dkind> --sid <SID> --line <該 user 記錄的實體行號>`（需理由者附 `--reason-class`，理由句取七值之一對應的引言）
  Then 每次 rc 皆為 `0`，stdout 單行符合 `ok dec seq=<n> id=DEC-SI-<NNN> prop=<ID> dkind=<k> digest8=<8 碼>`（`resume` 為 `run=<RUN>` 且無 `digest8`）；事件帳本新增恰一行 `dec`，鍵集合符合 R72（`transcript` 載體：含 `quote`、`sid`、`line`、`card_seq`〔`resume` 無〕，無 `audit_ref`、`audit_sha256`、`key_id`）
  And `quote` 逐字等於決定行、`reason` 等於引言尾隨句（無尾隨者無此鍵）、`decider` 為字串`掌舵者`、`decided_at` 解析後等於被引記錄 `timestamp` 的同一時刻且帶 offset、`digest` 等於該 PROP 事件的 `digest`（綁卡面的六個 dkind）、`card_seq` 等於該 PROP 最近一筆 `card` 的 `seq`、晉升後式的 `flags` 為只含 `unverified_ack` 一個元素的清單、前式無 `flags`
  And `MJ(status)` 與 `fold` 顯示的狀態依序為 `approved`、`rejected`（兩個否決）、`returned`、`verified`（兩個晉升，待 `app.promote`）、`handed-off`、`rejected`（不轉交）、`promoted`（回滾不改態）、`rejected`（解除後標記已解除）、SUSPENDED 解除
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_1]"
```

```gherkin
# AT-212-1-2
# 對應 AC: AC-212-1（PRD AC-SI-12-1；R77 (c)(ii)(e)；PC-02）附件載體（`queued_command`）的真人核准在卡面送達之後打出時受理，時序以附件自帶時間戳為準、不用實體行序
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_2_ -q -p no:xdist -o addopts=

Feature: decide 附件載體正控

Scenario: 附件的 `attachment.timestamp` 晚於卡面 assistant 訊息，即使附件記錄物理上落在更早的行
  Given `R` 與 `proposed` 的 PROP `P`（已 `card --issue`）；合成逐字稿依實體行序為：行 1 assistant 文字（含卡面核心區，頂層 `timestamp` 為 `T0`）、行 2 附件記錄（`attachment.type` 為 `queued_command`、`attachment.origin.kind` 為 `human`、`attachment.prompt` 為 `核准 <P>`、`attachment.timestamp` 為 `T0` 加 10 秒、記錄頂層 `timestamp` 為 `T0` 加 40 秒）、行 3 只含 `tool_use` 的 assistant 訊息（頂層 `timestamp` 為 `T0` 加 30 秒）
  When 呼叫 `decide <P> --kind approve --sid <SID> --line 2`
  Then rc 為 `0`；事件 `dec` 的 `line` 為 `2`（附件記錄本身的實體行號）、`quote` 為 `核准 <P>`、`card_seq` 等於該 PROP 最近一筆 `card` 的 `seq`、`decided_at` 的時刻等於 `attachment.timestamp`（不是記錄頂層的 `timestamp`）
  And 同一份逐字稿在附件載體被改為 `attachment.origin.kind` 為 `sdk` 的對照組，rc 為 `1`、碼 `NOT-HUMAN-UTTERANCE`（對照組證明受理不是因為任何附件都放行）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_2]"
```

```gherkin
# AT-212-1-3
# 對應 AC: AC-212-1（PRD AC-SI-12-1；R78）決定語法解析器 `decgrammar` 的合法形態正控：開頭式、獨立行式、九列行文法、`晉升` 兩式、Unicode 空白修剪
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_3_ -q -p no:xdist -o addopts=

Feature: decgrammar 合法形態

Scenario: 合法決定行解析出動詞、ID、候選 dkind、尾隨句與旗標
  Given §5.3 的 GRAMMAR-OK 表（每列一個整則訊息文字與預期 `Parsed`）：九個動詞各一個單行；`晉升 <P>` 與 `晉升 <P> 未驗採納`；`否決 <P> 未說明`；同一則訊息有閒聊兩行加一個獨立決定行（獨立行式，決定行在中間或末尾）；整則前後含 U+3000 與換行；CRLF 換行的多行訊息；理由句含另一個 PROP ID 字樣（`否決 <P> 已被 <P2> 涵蓋`）；理由句含標點與全形空格
  When 對每列呼叫 `decgrammar.parse(text)`
  Then 每列皆受理，`Parsed.verb`、`id`、`kind_candidates`（`否決` 為 `reject` 與 `decline-promote` 兩個候選，`不轉交` 為 `reject`，`晉升` 後式帶 `flags` 為 `unverified_ack`）、`trailing`（理由句，無則空）與 `line_no` 逐列等於表值
  And 理由句內的其他 `PROP-SI-N` 字樣不使該則成為多決定（受理）；理由句的標點與全形空格原樣保留於 `trailing`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_3]"
```

```gherkin
# AT-212-1-E-1
# 對應 AC: AC-212-1（PRD AC-SI-12-1、12-4 ②；R78；NC-05～NC-08、NC-10、NC-11）語法負控：否定句、疑問句、引用卡面、多決定行、尾隨文字、前綴字、缺理由、全形空格、ID 形態不配
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_E_1_ -q -p no:xdist -o addopts=

Feature: decgrammar 負控

Scenario: 每個違規形態都被拒，碼與表一致，且沒有任何一列被靜默受理
  Given §5.3 的 GRAMMAR-BAD 表（每列＝整則文字、預期拒絕碼）：NC-05 `不核准 <P>`、`請核准 <P>` 與 `OK 核准 <P>`（前綴字）⇒ `GRAMMAR-NO-DECISION`；NC-06 `核准 <P>？先等一下` 與 `核准 <P> 謝謝` ⇒ `GRAMMAR-TRAILING`；NC-07 整則含字面 `--- 以下不計入核心區 ---`、或含以 `[PROP-SI-` 起頭且含 `｜digest：` 的行、或含字面 `決定：核准 ／`（其中並有一行合法的 `核准 <P>`）⇒ `GRAMMAR-CARD-QUOTED`；NC-08 兩個決定行（異 PROP、同 PROP、動詞不同）⇒ `GRAMMAR-MULTI`；NC-10 `解除 <P> 謝謝`、`轉交 <P> 好`、`核准 <P> 。` ⇒ `GRAMMAR-TRAILING`；`否決 <P>`、`退回 <P>`、`回滾 <P>`、`恢復 <R>`（理由必填而缺）⇒ `GRAMMAR-REASON-MISSING`；NC-11 `恢復 先試試`（缺 RUN 號）、`恢復 <P> 理由`（RUN 配 PROP 號）、`核准 RUN-SI-001x` ⇒ `GRAMMAR-ID-FORMAT`；`晉升 <P> 好` 與 `晉升 <P> 未驗 採納` ⇒ `GRAMMAR-FORM`；全形空格分隔 `核准　<P>` 與雙空格 `核准  <P>` ⇒ 不是決定行（`GRAMMAR-NO-DECISION`）；空字串與只有空白 ⇒ `GRAMMAR-NO-DECISION`
  When 對每列呼叫 `decgrammar.parse(text)`
  Then 每列皆拒絕，碼等於表值（一列恰一個碼）；`GRAMMAR-CARD-QUOTED` 先於 `GRAMMAR-MULTI` 與其他碼判（NC-07 含合法決定行者仍為 `GRAMMAR-CARD-QUOTED`）
  And 對照組（同一批文字去掉違規部分後的合法形態）全部受理，證明拒絕不是因為判準過嚴
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_E_1]"
```

```gherkin
# AT-212-1-E-2
# 對應 AC: AC-212-1（PRD AC-SI-12-1、12-4 ①；R77、R79；NC-01、NC-02、NC-09、NC-17～NC-19）出處負控：sdk、isMeta、tool_result、assistant、出處缺席、他 PROP、sid 檔不存在、行號超界、壞行
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_E_2_ -q -p no:xdist -o addopts=

Feature: decide 出處負控

Scenario: 不是兩種真人載體的記錄一律 rc 1、零 DEC
  Given `R` 與 `proposed` 的 PROP `P`（已 `card --issue`、卡面已在 assistant 文字送達）；`snap0＝snap(R)`、`HOME` 檔案清單；十個逐字稿情境，每個在送達卡面之後放一筆決定記錄：NC-01 `user` 記錄 `origin.kind` 為 `sdk` 且文字為 `核准 <P>`；`user` 記錄頂層 `isMeta` 為 `true` 且 `origin.kind` 為 `human`；NC-09 `user` 記錄無 `origin`、內容為 `tool_result` 區塊而其文字含字面 `{"origin":{"kind":"human"}}` 與 `核准 <P>`；`assistant` 記錄文字為 `核准 <P>`；`attachment` 記錄 `attachment.type` 為 `queued_command` 而 `attachment.origin.kind` 為 `task-notification`；`user` 記錄 `origin.kind` 為 `peer`；NC-19 `user` 記錄完全沒有 `origin` 欄位、內容為 `核准 <P>`；`user` 的 `origin` 是字串而非物件；NC-02 human 說 `核准 <P2>`（另一個存在的 PROP）而位置參數為 `<P>`；human 的 user 記錄內容清單只含 `tool_result` 區塊（文字為空）
  When 各情境呼叫 `decide <P> --kind approve --sid <SID> --line <該決定記錄的實體行號>`；另加三個呼叫：`--line` 為檔案行數加 1、`--line` 指向一個非 JSON 的壞行、`--sid` 為不存在的合法 UUID
  Then 依序 rc 皆為 `1`、`codes(out)` 恰為 `NOT-HUMAN-UTTERANCE`（sdk、isMeta、tool_result、assistant、task-notification、peer、origin 為字串各一）、`ORIGIN-MISSING`（NC-19）、`ID-MISMATCH`（NC-02）、`TEXT-EMPTY`（只含 tool_result 的 human 記錄）、`LINE-OUT-OF-RANGE`、`RECORD-UNPARSABLE`、`TRANSCRIPT-UNAVAILABLE`；每個 rc 為 `1` 的呼叫其 stdout 依序為 `reject decide …`、碼行、`obs-draft:`、恰一行草稿列，`draft_ok` 成立
  And `snap(R)` 等於 `snap0`、`HOME` 檔案清單不變（零 DEC、零殘留）；`ORIGIN-MISSING` 的 detail 含 `NOT-EVALUABLE` 字樣（量不到、不得記為已核准）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_E_2]"
```

```gherkin
# AT-212-1-E-3
# 對應 AC: AC-212-1（PRD AC-SI-12-1、§7.2 前提欄；R80 (d)(e)；NC-11～NC-14、NC-20）動詞表前提負控：`恢復` 的 RUN 不符、`回滾` 對未晉升、`晉升` 的式與 verdict 不符、handoff 的核准與晉升、動詞與 route 的配對、`--kind` 與引言不一致、態不合
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_E_3_ -q -p no:xdist -o addopts=

Feature: decide 前提負控

Scenario: 每個前提不符都 rc 1、碼與表一致、不記 DEC
  Given `R`；以 §5.2 的 `write_events` 備下列帳本情境（所有 `verified` 情境的 `app.sandbox` 皆 `rollback_ok` 與 `touched_ok` 為 `true`，使晉升前提成立；每個 PROP 皆已 `card --issue`），每個情境配一份 PC-01 形態的合成逐字稿（卡面已送達、human 的決定記錄為下列引言）：(a) `恢復 <舊 RUN> 理由`，而折疊出的 SUSPENDED 所在運轉為另一個 RUN；(b) `恢復 <RUN> 理由`，而帳本未 SUSPENDED；(c) `回滾 <P> 太慢`，PROP 為 `verified`；(d) PROP 為 PASS 的 `verified`，引言 `晉升 <P> 未驗採納`；(e) PROP 為 NE 的 `verified`（`reasons` 為 `NO-PROBES`），引言 `晉升 <P>`；(f) PROP 為 `handoff:T1` 的 `proposed`，引言 `核准 <P>`；(g) 同上而引言 `否決 <P> 理由`；(h) PROP 為 loop 的 `proposed`，引言 `不轉交 <P> 理由`；(i) PROP 為 `approved`，引言 `核准 <P>`；(j) PROP 為 `proposed`，引言 `核准 <P>` 而 `--kind reject`；(k) PROP 為 `rejected`（冷卻已被解除），引言 `解除 <P>`；(l) PROP 為 `verified` 而 verdict 為 NE、`reasons` 為 `NO-PROBES`，引言 `退回 <P> 補探針`
  When 各情境呼叫 `decide`（`--kind` 取引言導出者，(j) 另給 `--kind reject` 對 `核准`）
  Then rc 皆為 `1`；`codes(out)` 依序恰為 (a) `RUN-MISMATCH`、(b) `NOT-SUSPENDED`、(c) `PRECONDITION-STATE`、(d) `PROMOTE-FORM-MISMATCH`、(e) `PROMOTE-FORM-MISMATCH`、(f) `ROUTE-HANDOFF`、(g) `ROUTE-VERB-MISMATCH`、(h) `ROUTE-VERB-MISMATCH`、(i) `PRECONDITION-STATE`、(j) `KIND-MISMATCH`、(k) `NOT-IN-COOLDOWN`、(l) `PRECONDITION-VERDICT`
  And 事件帳本位元組逐情境不變（零 DEC）；每個情境另有`前提成立`的對照呼叫（改正該情境的一個條件）rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_E_3]"
```

```gherkin
# AT-212-1-E-4
# 對應 AC: AC-212-1（PRD AC-SI-12-1、§9.3 rc 通則；R70、R71、R80 (a)(b)(c)(d)(h)）用法錯誤 rc 3、`UNATTENDED-REFUSED` rc 1、預設拒絕（無法解析不改狀態）、不收引言與 `--reason` 與 `--unverified-ack`、ID 的存在性與種類（`PROP-NOT-FOUND`、`RUN-NOT-FOUND`、`ID-KIND`）、撕裂的事件帳本（`LEDGER-TORN`）
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_1_E_4_ -q -p no:xdist -o addopts=

Feature: decide 用法與預設拒絕

Scenario: 用法錯誤 rc 3、無人值守 rc 1、不可解析的回覆不改狀態
  Given `R`、`proposed` 的 PROP `P`（已 `card --issue`）與 PC-01 逐字稿；`snap0＝snap(R)`
  When 情境一（rc 3）：`--sid` 為非 UUID 字串、`--line 0`、`--line abc`、`--kind` 為 `approve-all`、`--by` 含空白、`--reason-class` 為 `隨便`、`--carrier console` 並用 `--kind approve`、位置參數為只有兩位數字的 PROP 號（執行期把真 PROP 號的前導零少放一位組出）、同時給兩個位置參數、缺 `--sid`、未知旗標 `--reason 好`、`--quote 核准`、`--unverified-ack`
  And 情境二：設環境變數 `AUTOSDD_UNATTENDED` 為 `0`（值非空即算有設）後呼叫一個本來會成功的 `decide`
  And 情境三：human 的回覆為閒聊 `我再想想`（無決定行），其後呼叫 `decide <P> --kind approve …`
  And 情境四（各自於 `R` 的複本上呼叫）：(a) 位置參數為既存運轉的 RUN 號、引言 `核准 <P>`、`--kind approve`；(b) 位置參數為 `P`、引言 `恢復 <RUN> 理由`、`--kind resume`；(c) 位置參數為不存在的 RUN 號（執行期取現有最大 RUN 號加 900 組出）、`--kind resume`；(d) 位置參數為不存在的 PROP 號（現有最大 PROP 號加 900）、`--kind approve`
  And 情境五：自合規事件帳本去掉結尾 LF 的複本 `Rt`（P1 撕裂帳本的同款建法），在其上呼叫一個本來會成功的 `decide`
  Then 情境一每個呼叫 rc 為 `3`、stdout 空、stderr 至少一行且以 `selfimproving:` 起頭、零寫入
  And 情境二 rc 為 `1`、碼恰為 `UNATTENDED-REFUSED`、事件帳本與家目錄零變動；取消該環境變數後同一呼叫 rc 為 `0`（對照）
  And 情境三 rc 為 `1`、碼 `GRAMMAR-NO-DECISION`，`MJ(status)` 的 `pending_props` 仍含 `P` 且態仍為 `proposed`（預設拒絕、狀態不變）
  And 情境四 rc 皆為 `1`、`codes(out)` 依序恰為 (a) `ID-KIND`、(b) `ID-KIND`、(c) `RUN-NOT-FOUND`、(d) `PROP-NOT-FOUND`；情境五 rc 為 `1`、`codes(out)` 恰為 `LEDGER-TORN`、事件帳本位元組不變、`HOME` 無新檔；全部 rc 為 `1` 的呼叫零殘留（`snap(R)` 等於 `snap0`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_1_E_4]"
```

```gherkin
# AT-212-2-1
# 對應 AC: AC-212-2（PRD AC-SI-12-2；R80 (f)(g)）決定綁定現行卡面 digest：`dec` 記錄的 digest 與 `card_seq` 指向現行卡，之後 `sandbox` 受理
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_2_1_ -q -p no:xdist -o addopts=

Feature: 決定綁定現行卡面

Scenario: 現行 digest 與卡面的核准被記錄、其後能進沙盒
  Given `R`；`drive_to(R, "carried")`（已 `prop-new`、`card --issue` 一次）；對該 PROP 先 `card --issue` 第二次（兩筆 `card` 事件，digest 相同）
  When 以 PC-01 逐字稿呼叫 `decide <P> --kind approve …`
  Then rc 為 `0`；`dec.digest` 等於 PROP 事件 `digest`；`dec.card_seq` 等於**第二筆** `card` 事件的 `seq`（最近一筆）；`MJ(check)` 的 `events.dec_quote` 為 `PASS`（逐字稿在場時回查通過）
  And 其後 `heldout-freeze` 與 `sandbox` 對該 PROP rc 皆為 `0`（核准有效）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_2_1]"
```

```gherkin
# AT-212-2-E-1
# 對應 AC: AC-212-2（PRD AC-SI-12-2；R80 (f)、R86、R91；NC-03）過期卡與 digest 變更：`STALE-CARD`、`CARD-NOT-ISSUED`、`CARD-CHANGED`；核准後內容檔被改寫使 `sandbox` 與 `promote` 拒
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_2_E_1_ -q -p no:xdist -o addopts=

Feature: 過期卡與 digest 變更

Scenario: 卡面過期或內容被改，決定被拒、核准失效、須重新上卡
  Given `R`；情境一：`prop-new` 後**未** `card --issue`；情境二：`card --issue` 之後該 PROP 被退回修訂為 rev 2（digest 改變）而尚未重發 `card`，human 對舊卡說 `核准 <P>`（NC-03）；情境三：PROP 已 `verified`（verdict `PASS`）並 `card --issue`，其後以 `write_events` 追加一筆複驗 `app.verify`（verdict 改為 `NE`、`reasons` 為 `NO-PROBES`），卡面的「驗證」欄隨之改變而未重發，human 對舊卡說 `晉升 <P> 未驗採納`；情境四：已核准並 `heldout-freeze`、`sandbox` 之前，把 `SelfImproving_Proposals/<P>/r1.md` 的一個字元改掉（digest 重算不同）；情境五：同情境四但已 `verified` 並記了「晉升」的 DEC，之後改 `rN.md`
  When 情境一至三各呼叫 `decide <P> --kind approve …`；情境四呼叫 `sandbox <P>`；情境五呼叫 `promote <P>`
  Then 情境一 rc 為 `1`、碼恰為 `CARD-NOT-ISSUED`；情境二 `STALE-CARD`；情境三 `CARD-CHANGED`；情境四 rc 為 `1`、碼 `DIGEST-MISMATCH`（核准失效）；情境五 rc 為 `1`、碼含 `DIGEST-MISMATCH`；全部零 DEC、零 `app.*` 事件、主工作樹不變
  And 各情境於重新 `card --issue` 並重做（情境二另 `prop-revise` 後）後同一動作 rc 為 `0`（重新上卡即恢復）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_2_E_1]"
```

```gherkin
# AT-212-3-1
# 對應 AC: AC-212-3（PRD AC-SI-12-3；R80、R72）K=1 逐張決定：兩張 PROP 各自一則決定、各一筆 DEC；`decider` 恆為掌舵者
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_3_1_ -q -p no:xdist -o addopts=

Feature: K=1 逐張決定

Scenario: 兩張 PROP 逐張決定
  Given `R`、同一運轉內兩張 `proposed` 的 PROP `P1`、`P2`（皆已 `card --issue`；卡面皆在 assistant 文字送達）；兩則 human 的 user 記錄分別為 `核准 <P1>` 與 `否決 <P2> 證據不足`
  When 依序呼叫 `decide <P1> --kind approve …`、`decide <P2> --kind reject --reason-class 證據不足 …`（`--by reviewer`）
  Then 兩次 rc 皆為 `0`；事件帳本新增兩筆 `dec`，`prop` 分別為 `P1` 與 `P2`，`decider` 皆為字串`掌舵者`（`--by` 只改事件的 `by`、不改 `decider`）；`P1` 態為 `approved`、`P2` 態為 `rejected`、互不影響
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_3_1]"
```

```gherkin
# AT-212-3-E-1
# 對應 AC: AC-212-3（PRD AC-SI-12-3；R78 (d)、R80 (a)(h)）沒有「全部核准」：整批用語、多個決定行、無 ID、兩個位置參數、代決旗標皆被拒
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_3_E_1_ -q -p no:xdist -o addopts=

Feature: 不提供全部核准

Scenario: 任何批次或代決形態都被拒，狀態不變
  Given `R`、同一運轉內兩張 `proposed` 的 PROP `P1`、`P2`（皆已 `card --issue`、卡面皆在 assistant 文字送達）；`snap0＝snap(R)`
  When human 的訊息依序為 `全部核准`、`核准 PROP-SI-*`、`核准 <P1> <P2>`、兩行各一個決定行（`核准 <P1>` 與 `核准 <P2>`）、`核准`；各以 `decide <P1> --kind approve …` 呼叫；另呼叫 `decide <P1> <P2> --kind approve --sid … --line …` 與 `decide <P1> --kind approve --sid … --line … --by 掌舵者 --decider 掌舵者`
  Then 前五個呼叫 rc 皆為 `1`，碼依序為 `GRAMMAR-NO-DECISION`、`GRAMMAR-NO-DECISION`、`GRAMMAR-TRAILING`、`GRAMMAR-MULTI`、`GRAMMAR-NO-DECISION`；後兩個呼叫 rc 為 `3`（兩個位置參數、未知旗標 `--decider`）
  And `snap(R)` 等於 `snap0`（零 DEC）；`MJ(status)` 的 `pending_props` 仍含 `P1`、`P2`，態皆為 `proposed`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_3_E_1]"
```

```gherkin
# AT-212-4-1
# 對應 AC: AC-212-4（PRD AC-SI-12-4 ①～③、⑤；R77、R79、R98 (a)；PC-01、PC-02）卡面送達的正控：只含 `tool_use` 的 assistant 訊息被略過、user 載體以實體行序、附件載體以時間戳；已存 `dec` 的回查由 `check` 重放通過
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_4_1_ -q -p no:xdist -o addopts=

Feature: 卡面送達與回查

Scenario: PC-01 與 PC-02 受理，之後 `check` 對兩筆 `dec` 回查皆綠
  Given `R`、兩個 `proposed` 的 PROP `P1`、`P2`（皆已 `card --issue`）；`P1` 用 PC-01 逐字稿（卡面 assistant 文字、其後兩則只含 `tool_use` 與一則只含 `thinking` 的 assistant 訊息、再其後 human 的 user 記錄）；`P2` 用 PC-02 逐字稿（附件載體）
  When 分別呼叫 `decide`（兩筆皆 rc 0）；再呼叫 `MJ(check)`
  Then `events.dec_quote` 為 `PASS`、無 findings；把 `CLAUDE_CONFIG_DIR` 指向空目錄後重跑 `MJ(check)`：`events.dec_quote` 為 `NE`、nonblocking、碼 `TRANSCRIPT-UNAVAILABLE`、整體 rc 不為 `1`（量不到不判紅）
  And 對 `P1` 的卡面核心區做`CRLF 換行版`的 assistant 文字（`\r\n`）仍受理（比對前 CRLF→LF）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_4_1]"
```

```gherkin
# AT-212-4-E-1
# 對應 AC: AC-212-4（PRD AC-SI-12-4 ③；R77 (c)(e)；NC-15）附件時序負控：打出時刻早於卡面送達但物理上注入在其後、等於同一時刻、時間戳缺或不可解析
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_4_E_1_ -q -p no:xdist -o addopts=

Feature: 附件時序負控

Scenario: 附件的打出時刻不晚於卡面時，一律拒收
  Given `R` 與 `proposed` 的 PROP `P`（已 `card --issue`）；四份逐字稿，皆為行 1 assistant 文字（含卡面核心區、`timestamp` 為 `T0`）、行 2 附件（`prompt` 為 `核准 <P>`）：(a) NC-15 的 `attachment.timestamp` 為 `T0` 減 5 秒、記錄頂層 `timestamp` 為 `T0` 加 5 秒；(b) `attachment.timestamp` 恰等於 `T0`；(c) 附件缺 `attachment.timestamp`（只有記錄頂層 `timestamp`）；(d) `attachment.timestamp` 為 `not-a-time`
  When 各呼叫 `decide <P> --kind approve --sid … --line 2`
  Then (a)(b) rc 為 `1`、碼 `CARD-NOT-DELIVERED`（嚴格晚於才算看過卡）；(c)(d) rc 為 `1`、碼 `ATTACHMENT-TIME-UNKNOWN`（NOT-EVALUABLE，不得記為已核准）；零 DEC
  And 對照組：把 (a) 的 `attachment.timestamp` 改為 `T0` 加 1 秒，rc 為 `0`（證明時序比對確實用 `attachment.timestamp`、而非記錄頂層或實體行序）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_4_E_1]"
```

```gherkin
# AT-212-4-E-2
# 對應 AC: AC-212-4（PRD AC-SI-12-4 ③；R79；NC-04、NC-17）卡面負控：被改寫的卡面、卡面只在較早的 assistant 文字、卡面在 tool_result 或 user 記錄、`card_sha256` 與重建不符
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_4_E_2_ -q -p no:xdist -o addopts=

Feature: 卡面送達負控

Scenario: 掌舵者沒有看到那張卡時，不論形態都拒收
  Given `R` 與 `proposed` 的 PROP `P`（已 `card --issue`）；五份 user 載體逐字稿：(a) NC-04 assistant 文字的卡面第二行改掉一個字；(b) NC-17 卡面在較早的 assistant 文字，其後另有一則含 text 的 assistant 訊息（不含卡面）再接 human 決定；(c) 卡面只出現在一筆 `tool_result` 的文字內（assistant 文字無卡面）；(d) 卡面出現在 human 自己的 user 記錄文字內（而非 assistant）；(e) 卡面核心區的行序被對調
  When 各呼叫 `decide <P> --kind approve --sid … --line <human 決定的行號>`；另以 `write_events` 構造「`card` 事件的 `card_sha256` 被竄改」（與前綴折疊重建的卡面雜湊不符）的帳本，並以合法逐字稿呼叫
  Then (a)～(e) rc 皆為 `1`、碼 `CARD-NOT-DELIVERED`（NC-04 的 detail 指出第 2 行不符）；竄改 `card_sha256` 的帳本 rc 為 `1`、碼 `CARD-CHANGED`（寫入端以當下重算比對）
  And 對 (a)～(e) 與竄改情境，以手寫追加格式合法的 `dec`再跑 `MJ(check)`：`events.dec_quote` 為 `FAIL`，碼依序 `CARD-NOT-DELIVERED`（五個）與 `CARD-SHA-MISMATCH`（竄改者，帳本內部不一致與`沒看到卡`是兩個不同碼）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_4_E_2]"
```

```gherkin
# AT-212-4-E-3
# 對應 AC: AC-212-4（PRD AC-SI-12-4 ⑤；R79、R98 (a)；NC-16）已存 `dec` 的回查：偽造的 `dec`（格式合法、引言不在逐字稿）使 `check` 紅；逐字稿取不到＝NE 不判紅；各種回查失敗碼
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_4_E_3_ -q -p no:xdist -o addopts=

Feature: 已存 dec 的回查

Scenario: 偵測型（D）：事後由 check 標紅，不是被擋住的寫入
  Given `R`、`proposed` 的 PROP `P`（已 `card --issue`）與其 PC-01 逐字稿；以 `append_events` 追加五筆格式合法的 `dec`（各自 `id` 不同、`prop` 為 `P`、`card_seq` 指向該 `card`）：(a) NC-16 `quote` 為 `核准 <P>` 而 `line` 指向逐字稿中不含該文字的行；(b) `quote` 與逐字稿該行相同但 `sid` 指向另一份逐字稿（其該行是 human 的另一句話）；(c) `line` 指向 human 的記錄而 `quote` 逐字符合，但 `dkind` 為 `reject`（與引言動詞不同列）；(d) `quote` 逐字符合而 `prop` 為另一個 PROP；(e) `line` 超出檔案行數
  When 對五個情境各自（每個情境獨立帳本）呼叫 `MJ(check)`
  Then 每個情境 `events.dec_quote` 為 `FAIL`、rc 為 `1`，碼依序為 `QUOTE-MISMATCH`、`QUOTE-MISMATCH`、`KIND-MISMATCH`、`ID-MISMATCH`、`LINE-OUT-OF-RANGE`；subject 為該 `dec` 的 `seq=<n>`
  And 合法的 `dec`（引言、行號、`dkind`、`prop` 皆對）加同一逐字稿：`events.dec_quote` 為 `PASS`（對照）；同一份帳本在 `CLAUDE_CONFIG_DIR` 為空目錄時：`NE`、nonblocking、`TRANSCRIPT-UNAVAILABLE`，不判紅
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_4_E_3]"
```

```gherkin
# AT-212-4-E-4
# 對應 AC: AC-212-4（PRD AC-SI-12-4 ①、座標；R77 (b)(c)）逐字稿結構：BOM、CRLF、空白行計入實體行號、壞行、結構判定而非子字串比對、附件的行號取附件記錄本身
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_212_4_E_4_ -q -p no:xdist -o addopts=

Feature: 逐字稿結構判準

Scenario: 實體行號與結構欄位判定在各種檔案形態下穩定
  Given `R` 與 `proposed` 的 PROP `P`（已 `card --issue`）；逐字稿情境：(a) 檔首有 UTF-8 BOM、各行以 CRLF 結尾；(b) human 決定記錄之前有兩個空白行與一個壞行（皆計入行號）；(c) 同一行內 `message.content` 的文字含字面 `"origin":{"kind":"human"}` 但該記錄頂層無 `origin`（NC-09 的整行子字串陷阱）；(d) 一則 user 記錄的 `content` 為字串而非清單；(e) `content` 為清單且含兩個 `text` 區塊，決定行在第二個區塊（區塊以換行連接）
  When 各呼叫 `decide` 並以記錄的**實體行號**為 `--line`（(a)(b)(d)(e)），(c) 以該記錄行號呼叫
  Then (a)(b)(d)(e) rc 為 `0`、`dec.line` 等於該實體行號；(c) rc 為 `1`、碼 `NOT-HUMAN-UTTERANCE`（結構判定：頂層無 `origin`）
  And (b) 若把 `--line` 改為`不計空白行與壞行的序號`則 rc 為 `1`（`NOT-HUMAN-UTTERANCE` 或 `RECORD-UNPARSABLE`，證明行號是實體行號）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_212_4_E_4]"
```

```gherkin
# AT-213-1-1
# 對應 AC: AC-213-1（PRD AC-SI-13-1；R80 (e)、R82 (a)）`reason_class` 七值對 `reject`、`decline-promote`、`return` 皆受理，DEC 記 `reason_class` 與理由句
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_213_1_1_ -q -p no:xdist -o addopts=

Feature: 拒絕紀錄必含理由類

Scenario: 七個 reason_class 值各有一筆被受理的拒絕或退回
  Given `R`；對七個值各備一個 `proposed` 的 PROP 與其 PC-01 逐字稿；引言依序為 `否決 <P> 證據座標不足`（配 `證據不足`）、`否決 <P> 風險太高`（`風險過高`）、`退回 <P> 改用 M 類`（`工件類別錯`）、`否決 <P> 已有同型的 <P0>`（`已被涵蓋`）、`退回 <P> 超出本輪範圍`（`範圍外`）、`否決 <P> 看不懂卡面`（`卡面不清`）、`否決 <P> 未說明`（`未說明`）；另備一個 `verified` 的 PROP，引言 `否決 <P> 不想晉升`（`decline-promote`，配 `風險過高`）
  When 各呼叫 `decide … --reason-class <對應值>`（`--kind` 依動詞與態導出）
  Then 八次 rc 皆為 `0`；各 `dec` 的 `reason_class` 為所給值、`reason` 為引言尾隨句；`未說明` 者 `reason` 為字串`未說明`
  And `MJ(status)` 的 `cooldowns` 含四個否決（含 `decline-promote`）的 PROP，且 `reason_class` 末鍵逐一等於所給值；兩個退回的 PROP 不在 `cooldowns`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_213_1_1]"
```

```gherkin
# AT-213-1-E-1
# 對應 AC: AC-213-1（PRD AC-SI-13-1；R80 (a)(e)、R82 (a)）理由類負控：缺、七值之外、不收的 dkind 給了、「未說明」的最嚴對應
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_decide.py -k AT_213_1_E_1_ -q -p no:xdist -o addopts=

Feature: 理由類負控

Scenario: 理由類不合時拒收、零 DEC
  Given `R`、`proposed` 的 PROP `P`（已 `card --issue`）與逐字稿；`snap0＝snap(R)`
  When 情境 (a) 引言 `否決 <P> 證據不足` 而不給 `--reason-class`；(b) 給 `--reason-class 隨便`；(c) 引言 `核准 <P>` 而給 `--reason-class 證據不足`；(d) 引言 `否決 <P> 未說明` 而 `--reason-class 證據不足`；(e) 引言 `否決 <P> 證據不足` 而 `--reason-class 未說明`；(f) 以 `write_events` 手寫一筆 `reject` 的 `dec` 事件但 `reason_class` 為 `隨便`（供 `check` 回查）
  Then (a) rc 為 `1`、碼 `REASON-CLASS-MISSING`；(b) rc 為 `3`（`--reason-class` 不在七值，用法錯誤）；(c) rc 為 `1`、碼 `REASON-CLASS-UNEXPECTED`；(d)(e) rc 為 `1`、碼 `REASON-CLASS-MISMATCH`（引言尾隨句恰為`未說明`者只准 `未說明`，反之亦然）；零 DEC
  And (f) 的 `MJ(check)`：`events.structure` 為 `FAIL`、碼 `EVENT-TYPE`（`dec.reason_class` 值域不合）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_213_1_E_1]"
```


**B. 事件詞彙與欄位表、狀態機、`check` 追加項、`params.json`、冷卻、`card --issue`、held-out 凍結、`ref.carrier_families`（EP）**

```gherkin
# AT-240-1-1
# 對應 AC: AC-240-1（本檔自增；PRD §9.2 事件欄位表 P2 段；R72、R73、R107 (d)）`KINDS` 為 21 個；九種 P2 事件的完整欄位通過單事件判準；升級後的夾具建構器與 P1 既有呼叫形態的輸出全部合規
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_1_1_ -q -p no:xdist -o addopts=

Feature: 事件詞彙與欄位表

Scenario: 21 個詞彙與九種 P2 事件的合規形態
  Given `events.KINDS` 與 §5.2 的 EV-OK 表（每個 P2 kind 的代表事件：`card`；`dec` 的 `transcript` 載體九個 dkind 與 `console` 載體九個 dkind；`heldout.freeze`；`app.sandbox` 的 `applied` 為真與 `applied` 為假（`SANDBOX-EXPORT-FAILED`、`SANDBOX-APPLY-TIMEOUT`、`fail_code` 為 `null` 三形態）；`app.verify` 的 `PASS`、`FAIL`、`NE`（含 `probes_n` 為 0）；`app.promote`；`app.rollback`；`obs.add`；`obs.close`）
  When 對 `events.KINDS` 取長度與成員，並對 EV-OK 每個事件（補上共通鍵後）呼叫 `events.validate`，再對 §5.2 升級後的建構器（`card_ev`、`dec_ev`、`freeze_ev`、`sandbox_ev`、`verify_ev`、`promote_ev`、`rollback_ev`、`obs_add_ev`、`obs_close_ev`）與 P1 既有呼叫形態（`dec_ev(n, "approve")`、`_verify(n, "PASS")`、`ev("app.sandbox", "main", prop=…)`、`ev("card", "main", prop=…)`）經 `compose()` 的輸出各呼叫一次
  Then `len(KINDS)` 為 `21` 且含 `obs.add`、`obs.close`；EV-OK 每個事件與每個建構器輸出的 `validate` 回傳空清單
  And `validate` 對 `kind` 為 `x.y` 的事件回傳碼 `EVENT-KIND`，其 detail 含字樣`21 個詞彙`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_1_1]"
```

```gherkin
# AT-240-1-E-1
# 對應 AC: AC-240-1（本檔自增；R72；PRD §9.2）欄位表負控：缺必備鍵、表外鍵、型別與值域、條件必備、null 規則、載體互斥
# 測試類型: Unit
# 自動化工具: pytest（純函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_1_E_1_ -q -p no:xdist -o addopts=

Feature: 欄位表負控

Scenario: 對合規基底事件逐一施加一個違規，碼與表一致
  Given §5.2 的 EV-NEG 表（每列＝基底事件鍵、變異動作、預期碼集合；基底事件取自 EV-OK）：`card` 缺 `card_sha256`、多 `note`、`rev` 為 0、`digest` 為 `sha256:XYZ`；`dec` 的 `transcript` 載體缺 `quote`、缺 `card_seq`（除 `resume`）、`card_seq` 不小於本筆 `seq`、`decider` 不是「掌舵者」、`console` 載體多 `quote`、`console` 的 `decider` 為 `a;b`、`prop` 與 `run` 同時有、`dkind` 為 `approve-all`、`flags` 為 `["x"]`、`approve` 帶 `flags`、`approve` 帶 `reason_class`、`reject` 缺 `reason`、`reject` 缺 `reason_class`、`promote` 缺 `digest`、`rollback` 帶 `digest`、`decided_at` 不帶 offset；`heldout.freeze` 的 `n` 為 0、`frozen_by` 含空白；`app.sandbox` 的 `applied` 真而 `touched_ok` 為 `null`、`applied` 假而 `rollback_ok` 為 `true`、`fail_code` 為 `X`、`SANDBOX-EXPORT-FAILED` 而 `sandbox_sha256` 非 `null`、`sandbox_sha256` 為 `null` 而 `fail_code` 為 `null`、`SANDBOX-APPLY-TIMEOUT` 而 `applied` 真、`base` 為 39 位 hex；`app.verify` 的 `verdict` 為 `OK`、`reasons` 含未知碼、`PASS` 而 `reasons` 非空、`NE` 而 `reasons` 為空、`probes_n` 為 0 而 `verify_sha256` 非 `null`、`probes_n` 為 2 而 `verify_sha256` 為 `null`、`baseline_red` 為字串、`heldout_digest` 形態不合；`app.promote` 的 `unverified_ack` 為字串、`head_sha` 為 7 位、缺 `post_sha256`；`app.rollback` 多 `commit_sha`；`obs.add` 的 `carrier` 為 `transcript`、`decider` 含 `;`、`obs` 形態不合；`obs.close` 的 `disposition` 為空字串
  When 對每列的變異事件呼叫 `events.validate`；另對 `obs.close` 的 `disposition` 為 `row_max_bytes` 加 1 位元組者以 `check` 的 `events.structure`（帶 `params.json`）判
  Then 每列的回傳碼集合恰等於預期碼集合（缺鍵＝`EVENT-KEY-MISSING`、表外或不得有的條件鍵＝`EVENT-KEY-UNKNOWN`、型別或值域或互斥或 null 規則或 `reasons` 與 `verdict` 不一致＝`EVENT-TYPE`）；`disposition` 超長者 `events.structure` 為 `FAIL`、碼 `EVENT-TYPE`
  And 基底事件本身（未變異）回傳空清單（對照）；未被任何列引用的 P2 kind 為零
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_1_E_1]"
```

```gherkin
# AT-240-1-E-2
# 對應 AC: AC-240-1（本檔自增；R72；PRD §9.2 NFR-SI-08-1）事件行位元組上界的邊界：`dec` 的行長 L 放行、L 減 1 拒收（寫入端與 `check` 端）
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_1_E_2_ -q -p no:xdist -o addopts=

Feature: dec 事件行長邊界

Scenario: 自我校準：`event_max_bytes` 恰等於一行的位元組數
  Given `R` 與 `proposed` 的 PROP `P`（已 `card --issue`）與 PC-01 逐字稿（決定行含中文理由句 `否決 <P> 證據座標不足`）；先以 `event_max_bytes` 為 4096 呼叫一次 `decide … --reason-class 證據不足` 於一份複製的 `Rb` 上，量得新增事件行的位元組數 `L`（UTF-8，不含結尾 LF）
  When 在 `R` 以 `params.json` 的 `event_max_bytes` 為 `L` 呼叫同一個 `decide`；再於另一份複製 `Rc` 以 `L` 減 1 呼叫；另以 `write_events` 手寫一行長度恰為 `L` 與 `L` 加 1 的 `dec` 於兩份帳本後各跑 `MJ(check)`
  Then 寫入端：`L` 時 rc 為 `0`；`L` 減 1 時 rc 為 `1`、碼 `EVENT-BYTES-OVER`、零 DEC
  And `check` 端：行長 `L` 時 `events.structure` 為 `PASS`、行長 `L` 加 1（`event_max_bytes` 為 `L`）時為 `FAIL`、碼 `EVENT-BYTES-OVER`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_1_E_2]"
```

```gherkin
# AT-240-2-1
# 對應 AC: AC-240-2（本檔自增；PRD §5.1.2；R75）P2 全轉移表的正控：完整生命週期、NE 以未驗採納晉升、沙盒失敗退回後重提、複驗邊、`Prop` 新欄、冷卻欄 `reason_class`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_2_1_ -q -p no:xdist -o addopts=

Feature: P2 狀態機正控

Scenario: SC-P2-LEGAL 重放後的狀態與欄位逐一等於預期
  Given §5.2 的情境表 SC-P2-LEGAL（五個 PROP：A 走完 `proposed`→`approved`→`sandboxed`→`verified`（PASS）→`dec(promote)`→`promoted`，再 `dec(rollback)` 加 `app.rollback`；B 為 NE（`NO-PROBES`）以後式晉升且 `app.promote.unverified_ack` 為 `true`；C 為沙盒 `TOUCHED-SUPERSET` 的 NE 經 `dec(return)` 退回、`prop` rev 2 重提；D 為 `sandboxed` 後 `app.verify` 兩次（先 NE 的 `MUTATION-ABSENT`、再 PASS，複驗邊，`verify_runs_max` 為 2）；E 為 `verified` 後 `dec(decline-promote)` 進冷卻）
  When 對 `write_events` 寫出的帳本呼叫 `MJ(check)` 與 `fold.fold(events, stop_after_bad, verify_runs_max)`
  Then `events.transitions` 與 `events.structure` 皆為 `PASS` 且無 FAIL finding；折疊結果 A 為 `promoted`（`dec(rollback)` 與 `app.rollback` 後仍是 `promoted`）、B 為 `promoted`、C 的 rev 1 為 `returned` 而 rev 2 為 `proposed`（`verdict`、`flags`、`reasons` 清空、`rollback_ok` 與 `touched_ok` 為 `null`）、D 為 `verified` 且 `verdict` 為 `PASS`、`reasons` 為空（取最近一筆）、E 為 `rejected`
  And `Prop` 的新欄：A 的 `rollback_ok` 與 `touched_ok` 為 `true`（取最近一筆 `app.sandbox`）、C 的 rev 1 `reasons` 含 `TOUCHED-SUPERSET`；`fold.cooldowns` 含 E 且其末鍵 `reason_class` 等於該筆 `dec` 的 `reason_class`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_2_1]"
```

```gherkin
# AT-240-2-E-1
# 對應 AC: AC-240-2（本檔自增；R75、R74 (e)）非法轉移負控：越級、前提不符、複驗超限、無對應 dec 的 app.promote
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_2_E_1_ -q -p no:xdist -o addopts=

Feature: P2 非法轉移

Scenario: 每個非法序列在 `events.transitions` 被標紅，合法對照組不紅
  Given §5.2 的 TRANS-BAD 表（每列＝手寫事件序列、預期碼）：(a) `proposed` 直接 `app.sandbox`；(b) `approved` 直接 `app.verify`；(c) `verified` 的 `rollback_ok` 為 `false` 後 `dec(promote)`；(d) 同上而 `touched_ok` 為 `false`；(e) `verified` 為 NE 且 `reasons` 為 `NO-PROBES` 後 `dec(return)`；(f) 同 `(prop, rev)` 的第 3 筆 `app.verify`（`verify_runs_max` 為 2）；(g) `app.promote` 之前沒有 `dec(promote)`；(h) `app.rollback` 之前沒有 `dec(rollback)`；(i) `dec(resume)` 的 `run` 不存在；(j) `dec(unblock)` 對未被否決的 PROP；(k) `app.sandbox` 發生在 `returned` 態；(l) `verified` 的 PASS 後再 `dec(approve)`
  When 各情境寫入帳本後呼叫 `MJ(check)`（帶 `params.json` 的 `verify_runs_max`）
  Then 依序 `events.transitions` 為 `FAIL`，碼為 (a)(b)(c)(d)(e)(g)(h)(j)(k)(l) `TRANSITION-ILLEGAL`、(f) `VERIFY-RUNS-EXCEEDED`、(i) `TRANSITION-ORPHAN`；subject 指出該 PROP 或 `seq`
  And 對照組各一：(e2) `verified` 為 NE 且 `reasons` 含 `TOUCHED-SUPERSET` 後 `dec(return)`、(f2) 第 2 筆 `app.verify`（恰等於 `verify_runs_max`）、(c2) `rollback_ok` 與 `touched_ok` 皆 `true` 後 `dec(promote)`：`events.transitions` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_2_E_1]"
```

```gherkin
# AT-240-2-E-2
# 對應 AC: AC-240-2（本檔自增；R74 (a)～(h)）帳本不變式負控：凍結者、重複凍結、凍結晚於沙盒、base 不符、晉升 ack 不符、回滾 manifest 不符、DEC 的 digest 不符
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_2_E_2_ -q -p no:xdist -o addopts=

Feature: 帳本不變式

Scenario: 手寫的不變式違規各被對應碼標紅
  Given §5.2 的 INVAR 表（每列＝手寫事件序列、預期碼）：(a) `heldout.freeze` 的 `frozen_by` 等於該 PROP `prop` 事件的 `proposer`；(b) 同 PROP 兩筆 `heldout.freeze`；(c) `heldout.freeze` 的 `seq` 大於第一筆 `app.sandbox`；(c2) 有 `app.sandbox` 而全無 `heldout.freeze`；(d) `app.sandbox.base` 與該 PROP 事件的 `base` 不同；(e) `dec(promote)` 帶 `flags` 為 `["unverified_ack"]` 而其後 `app.promote.unverified_ack` 為 `false`；(e2) 無 `flags` 而 `app.promote.unverified_ack` 為 `true`；(f) `app.rollback.pre_sha256` 不等於最近一筆 `app.promote` 的 `post_sha256`；(f2) `post_sha256` 不等於該 `app.promote` 的 `pre_sha256`；(g) `dec(approve)` 的 `digest` 與該 PROP 事件的 `digest` 不同
  When 各情境寫入帳本後呼叫 `MJ(check)`
  Then `events.transitions` 為 `FAIL`，碼依序為 `FROZEN-BY-PROPOSER`、`HELDOUT-DUP`、`HELDOUT-AFTER-SANDBOX`（兩個）、`SANDBOX-BASE-MISMATCH`、`PROMOTE-ACK-MISMATCH`（兩個）、`ROLLBACK-MANIFEST-MISMATCH`（兩個）、`DEC-TARGET-MISMATCH`
  And 每列的合規對照（改正該欄位）`events.transitions` 為 `PASS`；`card_seq` 指向不存在事件的 `dec` **不**被 `events.transitions` 標紅（只驗型別與小於本筆 `seq`；離線不驗連結，§7.1 ⚖ 24），`events.dec_quote` 在逐字稿在場時才驗
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_2_E_2]"
```

```gherkin
# AT-240-2-E-3
# 對應 AC: AC-240-2（本檔自增；PRD §9.2 轉移註記；R75 末段）寫入端與重放端用同一前提：`decide` 與 `fold` 在（動詞 dkind × 態）格點上逐格一致
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_2_E_3_ -q -p no:xdist -o addopts=

Feature: decide 與 fold 前提一致

Scenario: 差分：寫入端接受者重放端必收，寫入端拒絕者重放端必標非法
  Given §5.2 的 PARITY 格點（態：`proposed`〔loop〕、`proposed`〔handoff〕、`approved`、`sandboxed`、`verified`〔PASS〕、`verified`〔NE `NO-PROBES`〕、`verified`〔NE `TOUCHED-SUPERSET`〕、`verified`〔FAIL〕、`verified`〔PASS 而 `rollback_ok` 為 `false`〕、`verified`〔PASS 而 `touched_ok` 為 `false`〕、`rejected`〔冷卻中〕、`rejected`〔已解除〕、`promoted`；dkind：`approve`、`reject`、`return`、`ack-handoff`、`decline-promote`、`unblock`、`promote`〔含與不含 `unverified_ack`〕、`rollback`），共 13 態乘 9 形態
  When 對每格：(1) 以 `write_events` 建該態並追加手寫的 `dec`（補齊欄位）後以 `fold` 重放，記錄是否出現 `TRANSITION-ILLEGAL`（重放端）；(2) 以同一態、同一 dkind 呼叫寫入端的前提判定函式 `decwrite.preconditions(folded, prop, dkind, flags)`（回傳碼清單；測試 seam），並對格點中抽出的 16 格（每個 dkind 至少一格接受與一格拒絕）以 CLI `decide` 與 PC-01 逐字稿實際呼叫
  Then 每格`重放端非法`恆等於`寫入端前提判定回傳非空碼清單`；CLI 抽樣 16 格的 rc（0 或 1）與其一致；回傳碼不屬 `PRECONDITION-STATE`、`PRECONDITION-VERDICT`、`ROUTE-HANDOFF`、`PROMOTE-FORM-MISMATCH`、`PROMOTE-PREMISE-ROLLBACK`、`PROMOTE-PREMISE-TOUCHED`、`NOT-IN-COOLDOWN` 的格不存在
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_2_E_3]"
```

```gherkin
# AT-240-3-1
# 對應 AC: AC-240-3（本檔自增；PRD §9.3 `check` 列；R98）`check` 共 32 項：P0 21 項與 P1 7 項原樣（以 §5.6 的 28 項常數表判定；唯一有意差異是 R1 的 `ref.carrier_families`，R104）、P2 四項接其後；載體缺席一律 nonblocking NE；P0 基線 repo 的 rc 與 overall 不變；`CHECK_RULES_REV` 為 3
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_3_1_ -q -p no:xdist -o addopts=

Feature: check 的 P2 追加項

Scenario: 項數、順序、載體缺席與基線不變
  Given 兩個 repo：`R0`＝`make_p2_repo(commit=True)` 的 P0 基線（無事件帳本）；`R1`＝`R0` 的複本加一次 `run-open`（`--trigger a --coord tools/a.py:1 --by main`）並 commit 的最小事件帳本（唯一一筆 `run.open`）；P1 的 28 項以 §5.6 的常數表 `P1_ITEMS_R0`、`P1_ITEMS_R1` 為 ground truth，由測試端 `p1_items(R)` 自被測輸出取 `(id, status, blocking, 排序後 findings 碼清單)`
  When 對 `R0`、`R1` 各呼叫 `MJ(check)`，並讀 `fingerprint_parts`
  Then 首行（文字形態）為 `si-check rows=10 items=32`；`items` 的前 28 項 id 順序與 P1 一字不差，`p1_items(R0)` 逐項等於 `P1_ITEMS_R0`、`p1_items(R1)` 逐項等於 `P1_ITEMS_R1`（R1 唯一與 P1 現碼不同的一格是第 14 項 `ref.carrier_families`，見 §5.6 與 R104）；第 29～32 項依序為 `events.dec_quote`、`events.dec_console`、`events.verdict`、`obs.console_audit`
  And `R0` 上四項皆為 `NE`、nonblocking、碼 `CARRIER-NOT-ESTABLISHED`，整體 `overall` 為 `PASS`、rc 為 `0`；`R1` 上四項皆為 `PASS`；`fingerprint_parts.check_rules_rev` 為 `3`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_3_1]"
```

```gherkin
# AT-240-3-E-1
# 對應 AC: AC-240-3（本檔自增；R98 (a)～(e)、R74）四個追加項的失敗碼與 P1 warn 的移除
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_3_E_1_ -q -p no:xdist -o addopts=

Feature: check 追加項的紅燈

Scenario: 每個追加項的 FAIL 與 NE 路徑各被觸發一次
  Given 手寫帳本情境：(a) 一筆 `app.verify` 的 `verdict` 為 `PASS` 而 `probes_n` 為 0、`reasons` 為空（`verdict_of` 重算為 NE）；(b) `app.verify` 的 `verdict` 為 `NE` 而 `reasons` 缺重算得出的碼；(c) `app.verify` 的 `reasons` 含無法由欄位導出的 `BASELINE-NOT-RED`（而 `baseline_red` 為 `true`）；(d) ⓪ 成立（`app.sandbox.applied` 為 `false`）而 `app.verify.probes_n` 為 2；(e) 一個 OBS 列帶 `carrier=console;audit_ref=<UUID>` 而事件帳本沒有對應 `obs.add`（`obs.console_audit`）；(f) 一筆 `obs.close` 指向處置仍為 `open` 的列；(g) 一筆 `research.skip`（`reason` 為 `helmsman`）的 `sid` 與 `line` 指向合成逐字稿中一筆 `assistant` 記錄；(h) 同上而逐字稿目錄不存在；(i) 含 `dec` 與 `helmsman` 免掃的帳本在 P1 會印 `QUOTE-VERIFIER-NOT-ESTABLISHED`
  When 各情境呼叫 `MJ(check)`
  Then (a)～(d) `events.verdict` 為 `FAIL`、碼 `VERDICT-MISMATCH`（四個子情形各一）；(e) `obs.console_audit` 為 `FAIL`、碼 `CONSOLE-EVENT-MISSING`；(f) 為 `FAIL`、碼 `CONSOLE-CLOSE-NOT-APPLIED`；(g) `events.research` 為 `FAIL`、碼 `HELMSMAN-REF-INVALID`；(h) `events.research` 為 `NE`、nonblocking、碼 `TRANSCRIPT-UNAVAILABLE`；(i) 全部項目的 findings 不含 `QUOTE-VERIFIER-NOT-ESTABLISHED`（`events.transitions` 與 `events.research` 皆無）
  And 每個子情形的合規對照（改正後）該項為 `PASS`；`_NONBLOCKING` 含 `CONSOLE-AUDIT-MISSING`、`CONSOLE-KEY-MISSING`、`TRANSCRIPT-UNAVAILABLE` 三碼（NE 不使 rc 為 2）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_3_E_1]"
```

```gherkin
# AT-240-4-1
# 對應 AC: AC-240-4（本檔自增；PRD §9.1 C5 P2 新增兩鍵；R106）`params.json` 為 30 鍵，兩個新鍵被 `sandbox` 與 `verify` 讀用
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_4_1_ -q -p no:xdist -o addopts=

Feature: P2 參數鍵

Scenario: 30 鍵合規，兩個新鍵的值影響行為
  Given `make_p2_repo` 的 `params.json`（30 鍵：P1 的 28 鍵加 `probe_timeout_seconds`＝600、`verify_runs_max`＝2）與真 repo 的 `docs/06_quality/SelfImproving_Protocol/params.json`（唯讀）
  When 對基線 `R` 呼叫 `MJ(check)`；讀真 `params.json` 的鍵集合；再把 `R` 的 `verify_runs_max` 改為 1、`probe_timeout_seconds` 改為 2 後各跑一次 `verify`（以 `drive_to(R, "sandboxed")` 備妥）
  Then `params.keys` 為 `PASS`；真 `params.json` 含兩個新鍵且為正整數（600 與 2）；`verify_runs_max` 為 1 時第二次 `verify` rc 為 `1`、碼 `VERIFY-RUNS-EXCEEDED`；`probe_timeout_seconds` 為 2 時逾時探針案例在小於 8 秒內收 NE（行程樹的清除另有專責負控，此處不重複）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_4_1]"
```

```gherkin
# AT-240-4-E-1
# 對應 AC: AC-240-4（本檔自增；R106；沿 P0 R5）新鍵缺、型別或範圍不符：`check` 紅、動詞 rc 3 並點名、不以預設值頂替
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_4_E_1_ -q -p no:xdist -o addopts=

Feature: P2 參數鍵負控

Scenario: 新鍵無效時不退回預設值
  Given 基線 `R` 與六份 `params.json` 變異：缺 `probe_timeout_seconds`；`probe_timeout_seconds` 為 `0`；為字串 `"600"`；為布林 `true`；缺 `verify_runs_max`；`verify_runs_max` 為 `-1`
  When 對每份變異呼叫 `MJ(check)`，並對 `drive_to` 備妥的 PROP 呼叫 `sandbox` 與 `verify`
  Then `params.keys` 為 `FAIL`，碼依序 `PARAM-MISSING`、`PARAM-RANGE`、`PARAM-TYPE`、`PARAM-TYPE`、`PARAM-MISSING`、`PARAM-RANGE`（subject 為該鍵名）
  And `sandbox` 與 `verify` 在鍵無效時 rc 皆為 `3`、stderr 點名該鍵、零寫入（不以 600 或 2 頂替）；`check` 的 `events.verdict` 對 `verify_runs_max` 無效時為 `NE`、碼 `SOURCE-UNAVAILABLE`（不判）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_4_E_1]"
```

```gherkin
# AT-213-2-1
# 對應 AC: AC-213-2（PRD AC-SI-13-2；R82）同型冷卻的正控：被否決後同型 `prop-new` 被擋；不同型放行；(a) 解除與 (b-2) 新證據後可再提，須附 `reject_response`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_213_2_1_ -q -p no:xdist -o addopts=

Feature: 同型冷卻

Scenario: 冷卻期內同型被擋，解除或新證據後放行
  Given §5.2 的 COOL-BASE（`R`；OBS 帳本含 `O1`、`O2` 證據座標皆 `docs/notes/demo.md:12`、`O3` 證據座標 `docs/notes/other.md:7`；`O1` 與 `O3` 的 `attr`（root）皆已 `attr.confirm`，根因鍵皆 `docs/stale-note`；一個開著且已有研究事件的運轉 `RUN`；PROP `A`〔`cls` 為 `D`、`target` 為 `docs/notes/demo.md`、`sources` 為 `O1`〕以 `write_events` 走到 `proposed` 後 `dec(reject)`，`reason_class` 為 `證據不足`，故 `A` 為 `rejected` 且冷卻中）
  When (1) `prop-new`（`cls D`、`target docs/notes/demo.md`、`sources O2`〔證據座標與 `A` 相同〕）；(2) `prop-new`（`cls P`〔不同 cls〕、其餘同）；(3) `prop-new`（`cls D`、`target docs/notes/other.md`）；(4) 加 `dec(unblock)` 於 `A` 後重跑 (1)，本文欄位表不含 `reject_response`；(5) 同 (4) 但本文欄位表有非空 `reject_response`；(6) 另一份帳本：不 `unblock`，而 OBS 新列 `O4`（`時間` 晚於否決的 `decided_at`、證據座標 `docs/notes/other.md:7`、根因鍵 `docs/stale-note` 已確認）後 `prop-new`（`cls D`、`target docs/notes/demo.md`、`sources O4`、本文有 `reject_response`）
  Then (1) rc 為 `1`、碼含 `COOLDOWN`（detail 指出 `A`）；(2)(3) rc 為 `0`（不同型放行）；(4) rc 為 `1`、碼 `REJECT-RESPONSE-MISSING`；(5) rc 為 `0`；(6) rc 為 `0`（(b-2) 成立：同根因鍵、證據座標與 `A` 的證據集合不相交）
  And `COOLDOWN` 的拒收輸出含 OBS 草稿列且 `draft_ok` 成立、零殘留；(1) 的 `COOLDOWN` 可與 P1 `DUPLICATE-TYPE` 同時命中（`A` 仍為活躍時不同；本情境 `A` 已 `rejected`，故只有 `COOLDOWN`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_213_2_1]"
```

```gherkin
# AT-213-2-E-1
# 對應 AC: AC-213-2（PRD AC-SI-13-2；R82 (b)(d)）冷卻解除條件的負控：證據相交、未確認根因、新證據不新、DEF 列、「未說明」最嚴、退回不啟動冷卻
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_213_2_E_1_ -q -p no:xdist -o addopts=

Feature: 冷卻解除負控

Scenario: 不滿足 (b-2) 的再提案仍被擋
  Given §5.2 的 COOL-BASE（`R` 與冷卻中的 `A`）；六個情境各自備 `prop-new`（`cls D`、`target docs/notes/demo.md`）：(a) 新列 `O5` 的證據座標與 `A` 的證據集合相交（`docs/notes/demo.md:12`）；(b) 新列 `O6` 的 `attr`（root）有但**未** `attr.confirm`；(c) 新列 `O7` 的 `時間` 早於否決的 `decided_at`；(d) 新證據是缺陷帳本新立的 DEF 列（證據不相交、根因無）；(e) `A` 是以 `reason_class` 為 `未說明` 被否決，而新列 `O8` 滿足同根因與證據不相交；(f) `A` 是被 `dec(return)` 退回的（不是否決）
  When 各呼叫 `prop-new`
  Then (a)～(e) rc 皆為 `1`、碼含 `COOLDOWN`；(f) rc 為 `1`、碼含 `DUPLICATE-TYPE`（P1：`returned` 屬活躍態，`ACTIVE_STATES`）而**不含** `COOLDOWN`（退回不啟動冷卻）
  And (e) 在 `A` 之後加 `dec(unblock)` 重跑：rc 為 `0`（只有`解除`能結束最嚴冷卻，附 `reject_response`）；(a)～(d) 各自補上 `dec(unblock)` 並附 `reject_response` 後重跑：rc 皆為 `0`（對照：被擋的原因是冷卻，不是其他前置）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_213_2_E_1]"
```

```gherkin
# AT-213-3-1
# 對應 AC: AC-213-3（PRD AC-SI-13-3；R82 (f)）合法的再提案不被標成冷卻繞過（解除後再提、不同型）；(b-2) 新證據路徑是離線重放不到的誠實劃界，只出 warn；`status` 列出冷卻與其 `reason_class`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_213_3_1_ -q -p no:xdist -o addopts=

Feature: 冷卻繞過偵測無假紅

Scenario: 解除後再提與不同型提案不被標 warn，新證據路徑只被標 warn 而不判紅
  Given 四份帳本，皆自 §5.2 的 COOL-BASE 出發：`L1`＝`dec(unblock)` 之後同型 `prop-new`（附 `reject_response`）；`L2`＝同運轉內另有一個不同型（`cls P`）的第二個 PROP、第一個 PROP 仍在冷卻中；`L3`＝((b-2) 新證據成立：新立 OBS 列 `O4`，`時間` 晚於否決、證據座標 `docs/notes/other.md:7`、根因鍵同為 `docs/stale-note` 且已確認；無 `dec(unblock)` 而同型 `prop-new` 受理)；`L0`＝只有 `reject`、尚無再提案
  When 對各帳本呼叫 `MJ(check)` 與 `MJ(status)`
  Then `L1`、`L2` 的 `events.transitions` 為 `PASS` 且 findings 不含 `COOLDOWN-BYPASS-SUSPECT`；`L3` 的 findings 含恰一筆 `COOLDOWN-BYPASS-SUSPECT`（level 為 `warn`、subject 為新 PROP）——離線 `check` 不重放 (b-2) 的新證據判定，同型的新 `prop` 落在未被 `unblock` 的冷卻內即只能是 warn（R82 (f)，§4〈刻意不做〉），該項狀態仍為 `PASS`、整體 rc 為 `0`
  And `MJ(status)` 於 `L0` 的 `cooldowns` 含被否決的 PROP 且元素末鍵 `reason_class` 等於否決時的值；於 `L1` 的 `cooldowns` 不含已解除的 PROP
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_213_3_1]"
```

```gherkin
# AT-213-3-E-1
# 對應 AC: AC-213-3（PRD AC-SI-13-3；R82 (f)）冷卻被繞過（手寫事件）時 `check` 標 warn `COOLDOWN-BYPASS-SUSPECT`（偵測型 D）；項目狀態不變
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_213_3_E_1_ -q -p no:xdist -o addopts=

Feature: 冷卻繞過偵測

Scenario: 同型 PROP 在冷卻中被手寫追加
  Given 帳本：`A`（`cls D`、`target X`、根因鍵 `K`）被 `dec(reject)`；其後以 `append_events` 直接追加一筆同型 `prop`（rev 1、`id` 為新號、`cls D`、`target X`、`sources` 的根因鍵亦為 `K`），未經 `dec(unblock)`
  When 呼叫 `MJ(check)`
  Then `events.transitions` 的 findings 含 `COOLDOWN-BYPASS-SUSPECT`（level 為 `warn`、subject 為新 PROP），該項狀態仍為 `PASS`、rc 為 `0`（warn 不影響 rc）
  And 對照：先加 `dec(unblock)` 再追加同型 `prop` 者無此 warn；不同 `target` 者無此 warn；`cls` 不同者無此 warn
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_213_3_E_1]"
```

```gherkin
# AT-240-6-1
# 對應 AC: AC-240-6（本檔自增；PRD §9.3 `card` 列；R81）`card --issue` 記 `card` 事件，stdout 卡面與不帶旗標逐位元組相同
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_6_1_ -q -p no:xdist -o addopts=

Feature: card --issue

Scenario: 事件欄位與輸出
  Given `R` 與 `proposed` 的 PROP `P`；`out0＝M(card P)` 的 stdout 位元組
  When 呼叫 `M(card P --issue --by main)` 兩次，與 `MJ(card P --issue)` 一次
  Then 兩次文字形態 rc 皆為 `0`、stdout 位元組逐位元組等於 `out0`、stderr 單行 `ok card seq=<N> prop=<P> digest8=<8 碼>`；事件帳本新增兩筆（再加 JSON 呼叫共三筆）`card`，鍵集合恰為 `seq`、`t`、`kind`、`by`、`prop`、`rev`、`digest`、`card_sha256`
  And `digest` 等於 PROP 事件的 `digest`、`rev` 等於 PROP 當下 `rev`、`card_sha256` 等於 `out0`（CRLF→LF 後的 UTF-8 位元組）的 `sha256:`；兩次 `--issue` 的 `seq` 不同（不去重）；JSON 形態的 stdout 為 P1 `card --json` 的物件加末鍵 `issued`（含 `seq` 與 `card_sha256`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_6_1]"
```

```gherkin
# AT-240-6-E-1
# 對應 AC: AC-240-6（本檔自增；R81、R70）`card --issue` 的態前提與無人值守：非 §7.2 前提態拒收
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_6_E_1_ -q -p no:xdist -o addopts=

Feature: card --issue 負控

Scenario: 不在前提態的 PROP 不能發卡
  Given 帳本中六個 PROP 的態：`approved`、`sandboxed`、`returned`、`handed-off`、`rejected`（冷卻已被解除）、以及 `proposed`、`verified`、`promoted`、`rejected`（冷卻中）各一（後四者為合法對照）；一個不存在的 PROP 號（執行期組出）
  When 對各 PROP 呼叫 `card <P> --issue`；另設 `AUTOSDD_UNATTENDED` 後呼叫合法態的一個
  Then 前五個態 rc 皆為 `1`、碼 `STATE-ILLEGAL`、零 `card` 事件；後四個合法對照 rc 為 `0`；不存在的 PROP rc 為 `3`（沿 P1 `card`）；無人值守 rc 為 `1`、碼 `UNATTENDED-REFUSED`、零寫入
  And 不帶 `--issue` 的 `card` 對前五個態仍 rc 為 `0`（唯讀，P1 不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_6_E_1]"
```

```gherkin
# AT-220-1-1
# 對應 AC: AC-220-1（PRD AC-SI-20-1；R83）`heldout-freeze` 正控：複製目錄、算 digest、事件以 `prop` 為鍵
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_220_1_1_ -q -p no:xdist -o addopts=

Feature: heldout-freeze 正控

Scenario: 凍結者不同於提案者，內容進家目錄、digest 進帳本
  Given `R` 與 `approved` 的 PROP `P`（`proposer` 為 `SA`）；§5.4 的 `make_heldout(dir, cases=5, probes="count")` 建出 `dir`（含 `manifest.json`、`probe_count.py` 與一個子目錄 `data/` 內的檔）；`dir` 在 `HOME` 之外
  When 呼叫 `MJ(heldout-freeze P --from dir --by FZ)`
  Then rc 為 `0`；stdout 為 `ok heldout.freeze seq=<n> prop=<P> n=5 digest8=<8 碼>` 的 JSON 對應物；事件鍵集合恰為 `seq`、`t`、`kind`、`by`、`prop`、`digest`、`n`、`frozen_by`，`by` 與 `frozen_by` 皆為 `FZ`、`n` 為 `5`
  And `<HOME>/heldout/<P>/` 存在且逐檔位元組與 `dir` 相同（含子目錄）；事件 `digest` 等於以 R84 原始位元組式對 `<HOME>/heldout/<P>/` 重算者；`git status --porcelain` 的輸出與呼叫前相同（held-out 內容不入 git）；`MJ(check)` 的 `events.transitions` 為 `PASS`
  And `n` 小於 `min_heldout`（案例數 4）的 `dir` 仍可凍結（rc `0`、事件 `n` 為 `4`；NE 留給 `verify`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_1_1]"
```

```gherkin
# AT-220-1-E-1
# 對應 AC: AC-220-1（PRD AC-SI-20-1；R83 (a)(b)）`heldout-freeze` 的拒收：凍結者即提案者、重複凍結、已有沙盒、手冊形態錯、來源不在、`--from` 在家目錄之內、連結、handoff
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_220_1_E_1_ -q -p no:xdist -o addopts=

Feature: heldout-freeze 負控

Scenario: 每個違規 rc 1、零殘留（無半成品目錄）
  Given `R`；`approved` 的 PROP `P`（`proposer` 為 `SA`）；`snap0`、`home0`；§5.4 的 HELDOUT-BAD 表（每列＝`dir` 變異、預期碼）：`--by SA`（凍結者即提案者）；已凍結後再凍結一次；PROP 已有 `app.sandbox`；`manifest.json` 缺；頂層多鍵；`schema_rev` 為 2；`cases` 為空；`cases` 的 `ref` 指向不存在的 OBS；`probes[0].argv[0]` 不是 `{python}`；`module` 含非法字元；`mutation` 含路徑分隔符或指向不存在的檔；`probes` 的 `id` 重複；`--from` 為 `<HOME>/heldout/` 之下的目錄；`--from` 內含符號連結；PROP 的 `route` 為 `handoff:T1`；PROP 態為 `rejected`；`--from` 不存在
  When 各呼叫 `heldout-freeze P --from dir --by FZ`（第一列用 `--by SA`）
  Then 預期碼依序為 `FROZEN-BY-PROPOSER`、`HELDOUT-EXISTS`、`HELDOUT-AFTER-SANDBOX`、`HELDOUT-MANIFEST-INVALID`（缺檔、多鍵、`schema_rev`、`argv[0]`、`module`、`mutation`、`id` 重複各一）、`HELDOUT-EMPTY`、`HELDOUT-REF-UNRESOLVED`、`HELDOUT-FROM-INSIDE`、`HELDOUT-LINK`、`ROUTE-HANDOFF`、`PROP-STATE-ILLEGAL`；`--from` 不存在為 rc `3`；其餘 rc 皆為 `1`；用於符號連結的案例若平台無法建立符號連結，改以替身 `os.scandir` 回報連結型條目（不得 skip）
  And 每個 rc 為 `1` 的呼叫零殘留：`snap(R)` 等於 `snap0`、`<HOME>/heldout/` 下除第一次成功凍結者外無新目錄或暫名目錄；`AUTOSDD_UNATTENDED` 有設時 rc 為 `1`、碼 `UNATTENDED-REFUSED`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_1_E_1]"
```

```gherkin
# AT-220-1-E-2
# 對應 AC: AC-220-1（PRD AC-SI-20-1、§9.3 `sandbox` 列；R74 (a)(b)(c)、R86）凍結先於沙盒：無凍結的 `sandbox` 被拒；手寫的凍結次序與凍結者違規被 `check` 標紅
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_220_1_E_2_ -q -p no:xdist -o addopts=

Feature: 凍結次序

Scenario: 先沙盒後凍結在寫入端被擋、在重放端被標紅
  Given `R` 與已核准、未凍結的 PROP `P`（`dec(approve)` 的逐字稿回查通過）
  When 呼叫 `sandbox P`；再 `heldout-freeze P --from <dir> --by FZ` 後 `sandbox P`；另以 `write_events` 手寫「`app.sandbox` 的 `seq` 小於 `heldout.freeze` 的 `seq`」「同 PROP 兩筆 `heldout.freeze`」「`frozen_by` 等於提案者」三個帳本後各跑 `MJ(check)`
  Then 第一次 `sandbox` rc 為 `1`、碼 `HELDOUT-NOT-FROZEN`、零 `app.sandbox`；凍結後的 `sandbox` rc 為 `0`；三個手寫帳本 `events.transitions` 為 `FAIL`，碼依序 `HELDOUT-AFTER-SANDBOX`、`HELDOUT-DUP`、`FROZEN-BY-PROPOSER`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_1_E_2]"
```

```gherkin
# AT-240-11-1
# 對應 AC: AC-240-11（本檔自增；OBS-SI-217；P1 TCS ⚖ 2；R104）`ref.carrier_families` 對 ATT／PROP／RUN 三族的指標形態引用做存在性判：全部解析得到時 PASS
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_11_1_ -q -p no:xdist -o addopts=

Feature: ref.carrier_families 存在性判

Scenario: 事件帳本在場時，指標引用全部解析
  Given `R`：事件帳本含 `run.open`（RUN）、`attr`（ATT）、`prop`（PROP `P`）；OBS 帳本某列處置為 `proposed@<P>`；`SelfImproving_Proposals/<P>/r1.{md,patch}` 在場；另有 OBS 列的**散文**提及不存在的 `PROP-SI-` 與 `RUN-SI-` 編號（執行期組出）、一份規格類文件（`docs/01_requirements/` 之下）提及不存在的 PROP 編號、一個提及 `DEC-SI-` 的 OBS 列
  When 呼叫 `MJ(check)`
  Then `F(ref.carrier_families)` 不含 `PROP-DIR-ORPHAN`，其 `FAMILY-REF-DANGLING` 的 subject 集合恰為夾具 baseline 自帶的那一列（P1 `base_rows` 第 8 列：處置為 `proposed@` 接一個永遠不在事件帳本的合成 PROP 號；level 為 `warn`），本 AT 自加的已解析指標列、散文提及的列與規格文件皆不在其中（散文提及與規格文件不判）；其狀態為 `NE`、nonblocking，且碼 `CARRIER-NOT-ESTABLISHED` 的 finding 其 detail 的 `families=` 只含 `DEC`（有提及的未建族；不含 `ATT`、`PROP`、`RUN`）；整體 rc 為 `0`
  And 移除 `DEC-SI-` 提及後該項為 `PASS`（baseline 列的 warn 仍在、不改狀態）；事件帳本不存在（P0 基線）時三族提及仍印 `CARRIER-NOT-ESTABLISHED`（P1 語意，rc 與 overall 不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_11_1]"
```

```gherkin
# AT-240-11-E-1
# 對應 AC: AC-240-11（本檔自增；OBS-SI-217；R104）指向不存在的 ATT／PROP／RUN 的指標引用：事件帳本內與提案目錄的被標紅（FAIL）、OBS 列處置的懸空 `proposed@` 指標印 warn；真 repo 零假紅
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_11_E_1_ -q -p no:xdist -o addopts=

Feature: 指標引用懸空

Scenario: 三種指標面各一個懸空引用，以及真 repo 的唯讀對照
  Given `R` 的事件帳本在場；三個變異：(a) OBS 列處置為 `proposed@<不存在的 PROP>`（執行期組出）；(b) 手寫事件 `dec` 的 `prop` 指向不存在的 PROP、`attr.confirm` 的 `att` 指向不存在的 ATT、`research.skip` 的 `run` 指向不存在的 RUN；(c) `SelfImproving_Proposals/` 下有目錄 `<不存在的 PROP>`；另唯讀取真 repo
  When 各呼叫 `MJ(check)`；對真 repo 取 `python tools/selfimproving.py check --json`（子行程，讀 rc 先存變數）
  Then (a) `ref.carrier_families` 的狀態不變（沒有 DEC、APP、MEA 提及時為 `PASS`）、`F(ref.carrier_families)` 含 `(該 OBS 列 ID, FAMILY-REF-DANGLING)` 且該 finding 的 level 為 `warn`、整體 rc 為 `0`；(b) 為 `FAIL`、碼 `FAMILY-REF-DANGLING`（三個 subject 皆 `seq=<N>`），且 `events.transitions` 同時為 `FAIL`（`TRANSITION-ORPHAN`；兩項各自獨立判）；(c) 為 `FAIL`、碼 `PROP-DIR-ORPHAN`
  And 真 repo 的 `ref.carrier_families` 狀態不是 `FAIL`（OBS 列對 `RUN-SI-` 與 `PROP-SI-` 的前向引用與歷史散文引用不被判；本檔作者現查該列有此類提及）；整體 rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_11_E_1]"
```

```gherkin
# AT-240-15-1
# 對應 AC: AC-240-15（本檔自增；主控 2026-10-21 對 ⚖ 39 的裁決；R110）`attr --type link` 的 `--reopens` 目標＝已結列加處置首詞為 `deferred` 的列：三個 `deferred` 形態的列各被連結一次 rc 0 並寫入 `attr` 事件；已結列照舊可連結
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_15_1_ -q -p no:xdist -o addopts=

Feature: attr link 的 reopens 目標

Scenario: deferred 列與已結列都能被再開連結
  Given `R`＝`make_p2_repo(commit=True)`，其 OBS 帳本另含：三個處置為 `deferred；再開症狀：<文字>` 的列 `D1`～`D3`（形態同真帳本中被體檢子代理指為再開的三筆：處置首詞 `deferred`、其後附再開症狀）、三個處置為 `open` 的新列 `N1`～`N3`、baseline 內處置首詞為 `fixed@` 的已結列 `C1`；`snap0＝snap(R)`
  When 依序呼叫 `M(R, attr, --type, link, --by, SA, --from, <Nk>, --reopens, <Dk>)`（k 為 1～3），再呼叫 `M(R, attr, --type, link, --by, SA, --from, <N1>, --reopens, <C1>)`；其後呼叫 `MJ(R, check)`
  Then 四次呼叫 rc 皆為 `0`，stdout 皆為單行 `ok attr seq=<n> id=<ATT> type=link`；事件帳本相對 `snap0` 恰多四筆 `attr`，每筆鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`type`、`from`、`reopens`，`type` 為 `link`、`from` 與 `reopens` 依呼叫、`id` 的 ATT 號嚴格遞增
  And `check` 的 `events.structure`、`events.transitions` 皆為 `PASS`、整體 rc 為 `0`；`attr-confirm` 由另一個 `--by` 確認第一筆後 rc 為 `0`、`MJ(R, status)` 的 `reopen_candidates.unsettled` 為 `3`（四筆連結減一筆已確認，沿 P1 的 `status` 語意）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_15_1]"
```

```gherkin
# AT-240-15-E-1
# 對應 AC: AC-240-15（本檔自增；R110；P1 R45）`--reopens` 目標的拒收與不變項：處置首詞為 `open` 者 `REOPENS-NOT-CLOSED`、不存在者 `REOPENS-NOT-FOUND`、`--from` 不存在者 `OBS-NOT-FOUND`，一律零寫入；復發候選提示（R45 的 `REOPEN-CANDIDATE`）的判準不變，不因 `deferred` 列而多出候選
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_events_p2.py -k AT_240_15_E_1_ -q -p no:xdist -o addopts=

Feature: attr link 的 reopens 目標拒收

Scenario: open 列與不存在者被拒收，候選提示只認已結列
  Given `R`＝`make_p2_repo(commit=True)` 再 commit 一份 OBS 帳本：含處置為 `open` 的 `O1`、處置首詞為 `deferred` 的 `D1`（附再開症狀）、已結列 `C1`（處置首詞 `fixed@`），三者的證據座標路徑相同；`R` 的工作樹另有不在 HEAD 版的新列 `N1`（處置 `open`、證據座標路徑同上、標記無 `reopens`）；`snap0＝snap(R)`
  When 呼叫 `attr --type link --by SA`：(a) `--from <N1> --reopens <O1>`；(b) `--from <N1> --reopens <不存在的 OBS 號>`；(c) `--from <N1> --reopens <不存在的 DEF 號>`；(d) `--from <不存在的 OBS 號> --reopens <D1>`（不存在的編號於執行期以字串相加組出）；另呼叫 `MJ(R, check)`
  Then (a) rc 為 `1`、`codes(out)` 恰為 `REOPENS-NOT-CLOSED`；(b)(c) rc 為 `1`、`codes(out)` 恰為 `REOPENS-NOT-FOUND`；(d) rc 為 `1`、`codes(out)` 恰為 `OBS-NOT-FOUND`；四者 stdout 皆含 `obs-draft:` 且 `draft_ok` 成立
  And 四次拒收後 `snap(R)` 等於 `snap0`（零寫入）；`check` 對 `N1` 的 `REOPEN-CANDIDATE` finding 的 detail 含 `C1` 的 ID 且不含 `D1` 與 `O1` 的 ID（候選提示仍只認已結列）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_15_E_1]"
```


**C. 沙盒（SB）**

```gherkin
# AT-215-1-1
# 對應 AC: AC-215-1（PRD AC-SI-15-1；R85、R86、R84）沙盒正控：只作用於樹外的 `git archive` 匯出副本、正式面逐字不變、`sandbox_sha256` 可由獨立實作重算
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_1_1_ -q -p no:xdist -o addopts=

Feature: sandbox 正控

Scenario: D 類 PROP 進沙盒，套用與回滾乾跑皆成功，樹回到 base 狀態
  Given `R`＝`make_p2_repo`；`P`＝`drive_to(R, "frozen")`（D 類、route `loop`、對 `docs/notes/demo.md` 的一處修改；`dec(approve)` 經 PC-01 逐字稿真跑 `decide` 受理；`heldout-freeze` 已做、`frozen_by` 為 `FZ`）；`surf0＝surface(R)`（`git status --porcelain` 輸出、`HEAD`、`git worktree list` 輸出、工作樹各檔位元組雜湊）、`home0＝tree_files(HOME)`；`base`＝該 PROP 事件的 `base`
  When 呼叫 `M(R, "sandbox", P, "--by", "SB1")`，並以牆鐘量測整次呼叫
  Then rc 為 `0`，整次小於 30 秒；stdout 單行 `ok app.sandbox seq=<n> id=APP-SI-<NNN> applied=true touched_ok=true rollback_ok=true fail_code=null`，stderr 空；事件鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`prop`、`rev`、`base`、`sandbox_sha256`、`applied`、`touched_ok`、`rollback_ok`、`fail_code`，`by` 為 `SB1`、`rev` 等於 PROP 當下 `rev`、`base` 等於 PROP 事件的 `base`
  And 沙盒樹：`<HOME>/sandbox/<P>` 存在；其 realpath 不在 `R` 的 realpath 之內（`os.path.commonpath` 判）、路徑不含 `.claude/worktrees/` 片段、樹內無 `.git`；樹內全部一般檔的相對路徑與位元組逐檔等於測試自行以 `git archive <base>` 加標準庫 `tarfile` 抽出的獨立副本
  And `sandbox_sha256` 等於測試自寫的 R84 原始位元組式 manifest 對`沙盒樹現況`與`獨立副本`兩者的值（三者相同，證明 `sandbox` 結束時樹已回到 base 狀態，而非停在套用後）
  And 正式面：`surface(R)` 等於 `surf0`（輸出與位元組逐字相同）；`tree_files(HOME)` 相對 `home0` 的新增只落在 `sandbox/<P>/` 與 `locks/` 之下；`MJ(R, status)` 顯示 `P` 為 `sandboxed`；`MJ(R, check)` 的 `events.transitions` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_1_1]"
```

```gherkin
# AT-215-1-2
# 對應 AC: AC-215-1（PRD AC-SI-15-1；R85 (b)、R86）M 類（記憶檔）沙盒與既有沙盒目錄的重建：M 類只複製被觸及的記憶檔、真記憶目錄位元組不變；前一輪遺留的 `<si>/sandbox/<P>` 被整個換掉
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_1_2_ -q -p no:xdist -o addopts=

Feature: sandbox M 類與重建

Scenario: 記憶檔進 `memory/`、真記憶目錄不動；遺留目錄被換掉
  Given `R`；`memdir`＝tmp 內的記憶目錄（沿 P1 夾具 `memory_dir`：含 `MEMORY.md` 與 `feedback_demo.md`）；M 類 PROP `PM`＝`drive_to(R, "frozen", cls="M", memory=memdir)`（patch 路徑為 `memory/feedback_demo.md` 與 `memory/MEMORY.md` 的逐行 patch）；另一個 D 類 PROP `PD`＝`drive_to(R, "frozen")`，並在 `<HOME>/sandbox/<PD>/` 預先放一個遺留檔 `stale.txt`（內容為「前一輪遺留」）；`mem0＝memdir 內各檔位元組雜湊`、`surf0＝surface(R)`
  When 依序呼叫 `M(R, "sandbox", PM, "--memory-dir", memdir)` 與 `M(R, "sandbox", PD)`
  Then 兩次 rc 皆為 `0`、事件的 `applied`、`touched_ok`、`rollback_ok` 皆為 `true`、`fail_code` 為 `null`
  And `PM`：沙盒樹的一般檔恰為 `memory/feedback_demo.md` 與 `memory/MEMORY.md`（被 `touched` 觸及者，不含 `memdir` 內其他檔），位元組等於 `memdir` 內對應檔；`sandbox_sha256` 等於測試自算的樹 manifest；`memdir` 內各檔位元組雜湊等於 `mem0`（真記憶目錄零變更）
  And `PD`：`stale.txt` 不存在、樹等於 base 的獨立副本（舊目錄整個被換掉，不是疊加）；兩個沙盒目錄互不相涉；`surface(R)` 等於 `surf0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_1_2]"
```

```gherkin
# AT-215-1-E-1
# 對應 AC: AC-215-1（PRD AC-SI-15-1；R85 (a)、R86；根層第 178 輪實測）沙盒根的位置負控：根在 repo 樹內、路徑含 `.claude/worktrees/` 片段、沙盒目錄經符號連結指向樹內、清理目標本身是連結——rc 3、零寫入、清理不跟隨連結
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_1_E_1_ -q -p no:xdist -o addopts=

Feature: 沙盒根位置

Scenario: 沙盒根不得落在 repo 樹內，且不得經連結繞進樹內
  Given `R` 與已凍結、已核准的 PROP `P`（`drive_to(R, "frozen")`）；`snap0＝snap(R)`；四個環境情境：(a) `AUTOSDD_SI_DIR` 指向 `R` 之內的子目錄 `.si_home`；(b) `AUTOSDD_SI_DIR` 指向 tmp 內路徑含片段 `.claude/worktrees/x` 的目錄（realpath 不在 `R` 內）；(c) `<si>/sandbox` 是指向 `R` 內某子目錄的符號連結（平台無法建符號連結時，以替身令 `os.path.realpath` 對 `<si>/sandbox` 回報落在 `R` 內的路徑，不得跳過）；(d) `<si>/sandbox/<P>` 本身是符號連結（指向 tmp 內另一個目錄 `elsewhere/`，其內有哨兵檔 `canary.txt`）
  When 各情境呼叫 `M(R, "sandbox", P)`
  Then (a)(b)(c) rc 皆為 `3`、stdout 空、stderr 含碼 `SANDBOX-ROOT-IN-REPO`、事件帳本位元組不變（零 `app.sandbox`）、`R` 與家目錄零新檔；(d) rc 為 `3`（清理守衛：目標本身是符號連結或 junction，不得清理）、`elsewhere/canary.txt` 仍在且位元組不變（清理不跟隨連結）
  And 對照組：`AUTOSDD_SI_DIR` 在 `R` 之外且路徑正常、`<si>/sandbox` 為一般目錄時，同一 PROP 的 `sandbox` rc 為 `0`；對照組的沙盒 realpath 不在 `R` 之內
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_1_E_1]"
```

```gherkin
# AT-215-1-E-2
# 對應 AC: AC-215-1（PRD AC-SI-15-1、§9.3 `sandbox` 列；R86、R70、R71）`sandbox` 的前置與用法負控：態、凍結、DEC 回查、逐字稿、digest、記憶目錄、無人值守、不存在、用法與家目錄；全部零殘留，既有沙盒目錄維持原狀；鎖內重驗競態
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_1_E_2_ -q -p no:xdist -o addopts=

Feature: sandbox 前置與用法負控

Scenario: 每個前置不符都 rc 1 或 rc 3、碼與表一致、不寫事件、不留半成品
  Given `R`；§5.2 的 SBX-PRE 表（每列＝一個獨立複本情境、預期 rc 與碼）：(a) PROP 為 `proposed`（未核准）；(b) PROP 已 `sandboxed`；(c) PROP 為 `approved` 而尚無 `heldout.freeze`；(d) `dec(approve)` 是手寫事件、`quote` 不在逐字稿內；(e) `dec(approve)` 合法而 `CLAUDE_CONFIG_DIR` 為空目錄（逐字稿取不到）；(f) 核准後 `SelfImproving_Proposals/<P>/r1.patch` 被改一個位元組（digest 重算不同）；(g) M 類 PROP 未給 `--memory-dir`；(h) `AUTOSDD_UNATTENDED` 設為 `1`；(i) 位置參數為不存在的 `PROP-SI-<執行期組出的號>`；(j) `dec(approve)` 的 `carrier` 為 `console` 而稽核檔不存在；(k) 同上而稽核檔在場、金鑰環未設；rc 3 組：(l) 不給位置參數；(m) `AUTOSDD_SI_DIR` 指向一個一般檔（家目錄不可寫）；(n) `params.json` 的 `probe_timeout_seconds` 為字串 `"600"`；每個情境另在 `<HOME>/sandbox/<P>/` 預先放哨兵檔 `keep.txt`（(c)(g) 等不存在目錄者除外）
  When 各呼叫 `M(R, "sandbox", ...)`
  Then 依序 rc 與碼為：(a)(b) rc 1、`STATE-NOT-APPROVED`；(c) rc 1、`HELDOUT-NOT-FROZEN`；(d) rc 1、`DEC-VERIFY-FAILED`（detail 含 `QUOTE-MISMATCH`）；(e) rc 1、`TRANSCRIPT-UNAVAILABLE`；(f) rc 1、`DIGEST-MISMATCH`；(g) rc 1、`MEMORY-DIR-MISSING`；(h) rc 1、`UNATTENDED-REFUSED`（先於其餘判，且零寫入）；(i) rc 1、`PROP-NOT-FOUND`；(j) rc 1、`CONSOLE-AUDIT-MISSING`；(k) rc 1、`CONSOLE-KEY-MISSING`；(l) rc 3；(m) rc 3、碼 `HOME-UNWRITABLE`、不退回暫存目錄；(n) rc 3、stderr 點名 `probe_timeout_seconds`、不以 600 頂替；rc 1 的呼叫其 stdout 依序為 `reject sandbox …`、碼行、`obs-draft:`、恰一行草稿列且 `draft_ok` 成立；rc 3 的呼叫 stdout 空、stderr 以 `selfimproving:` 起頭
  And 全部情境：事件帳本與 OBS 帳本位元組不變、`snap(R)` 不變、`keep.txt` 仍在且位元組不變（呼叫前已存在的沙盒目錄維持原狀）、`<HOME>/sandbox/` 下無暫名目錄；`AUTOSDD_UNATTENDED` 的情境 (h) 另確認家目錄逐檔位元組不變
  And 競態：以替身 `sandbox.apply_patch` 的副作用手寫追加一筆 `app.sandbox`（令 PROP 在鎖外組裝期間變成 `sandboxed`），外層呼叫 rc 為 `1`、碼 `STATE-CHANGED`、`<HOME>/sandbox/<P>` 不存在、無暫名目錄、事件帳本只多那筆手寫事件
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_1_E_2]"
```

```gherkin
# AT-215-1-E-3
# 對應 AC: AC-215-1（PRD AC-SI-15-1；R85 (d)；NFR-P2-3；§7.1 ⚖ 3）套用不受機器 `core.autocrlf` 影響：以含 `autocrlf = true` 的 `GIT_CONFIG_GLOBAL` 重現 Windows 預設，沙盒仍得到 LF 位元組且回滾乾跑逐位元還原
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_1_E_3_ -q -p no:xdist -o addopts=

Feature: sandbox 行尾中立

Scenario: 全域設定要求 autocrlf 時，沙盒與回滾乾跑仍不被改寫
  Given `R` 的追蹤檔全為 LF（`docs/notes/demo.md`）；已凍結已核准的 PROP `P`；測試檔 `crlf.gitconfig`（內容為 `[core]` 節與縮排一個 Tab 的 `autocrlf = true`）；環境改為 `GIT_CONFIG_NOSYSTEM=1` 且 `GIT_CONFIG_GLOBAL` 指向 `crlf.gitconfig`（P1 夾具的 hermetic 環境預設把兩者清空，看不到此危害，故本 AT 必須明文覆寫）
  When 先做危害見證：在無 `.git` 的 tmp 目錄內放同一個 `docs/notes/demo.md` 與 `r1.patch`，以「不帶 `-c core.autocrlf=false`」的裸 `git apply` 套用，記錄結果檔是否含 CR（見證結果只記錄、不當作通過條件）；再呼叫 `M(R, "sandbox", P)`，並對沙盒樹重算 manifest
  Then `sandbox` rc 為 `0`、`applied` 為 `true`、`rollback_ok` 為 `true`；沙盒樹內 `docs/notes/demo.md` 的位元組逐位元等於 `git show <base>:docs/notes/demo.md`（不含任何 `\r`）；`sandbox_sha256` 等於獨立副本的 manifest
  And 以替身（`mock.patch.object` 包住 `subprocess.run`）記錄 `sandbox` 呼叫期間所有 `git` 子行程的 argv：每個 `apply` 與 `archive` 的 argv 都含相鄰的兩項 `-c`、`core.autocrlf=false`
  And 見證結果為`含 CR`時，上述斷言即`旗標確實擋下了此機器的危害`；見證結果為`不含 CR`時斷言同樣成立（危害不重現的平台上旗標無害）——本 AT 在兩種見證結果下都無條件斷言，不以平台跳過
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_1_E_3]"
```

```gherkin
# AT-215-1-E-4
# 對應 AC: AC-215-1（PRD AC-SI-15-1、§9.3；R85 (c)、R84；§7.1 ⚖ 2）tar 抽取預檢負控：路徑穿越、絕對路徑、磁碟機代號與資料流、控制字元、尾端點或空白、非一般檔型別、同名重複、路徑過長邊界；`tarfile.data_filter` 缺席 rc 3 不降級
# 測試類型: Unit
# 自動化工具: pytest（合成 tar，不經 git）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_1_E_4_ -q -p no:xdist -o addopts=

Feature: 抽取預檢

Scenario: 每個危險成員先於任何寫入被拒，邊界值各一組
  Given §5.4 的 TAR-BAD 表（每列＝一個**只含該成員**的合成 tar 檔、預期拒絕；成員名於執行期以字串相加組出，測試原始碼不寫出磁碟機代號開頭或斜線起頭的路徑字面，NFR-P2-3）：成員名 `../evil.txt`；`sub/../../evil2.txt`；`/abs_evil.txt`（前導斜線）；以反斜線起頭的 `\abs_evil2.txt`；`C:evil3.txt`；`C:/evil4.txt`；`a/b.txt:stream`（NTFS 資料流）；含控制字元 `ctl\x01.txt`；片段尾端為點的 `dir./f.txt`；片段尾端為空白的 `trail /f.txt`；型別為符號連結、硬連結、字元裝置、區塊裝置、FIFO 的成員各一；兩個同名成員 `dup.txt`；另一個合規的對照 tar（`ok/` 目錄與 `ok/a.txt` 一般檔）；沙盒根 `root` 為 tmp 內尚不存在的目錄，其兩側各有哨兵路徑 `root/../evil.txt`、`root_parent/abs_evil.txt`
  When 對每個 tar 呼叫 `sandbox.precheck_members(tar, root)`；通過者再呼叫 `sandbox.extract_checked(tar_path, root)`（預檢加 `extractall(filter="data")`）
  Then 十八個危險 tar 的預檢皆回非空的拒絕清單，每筆含成員名與原因碼（`SANDBOX-MEMBER-REJECTED`）；對它們呼叫 `extract_checked` 皆拋 `SandboxError`，`root` 不存在或內無任何檔，兩個哨兵路徑皆不存在（先於任何寫入）；對照 tar 預檢回空清單、抽取後 `ok/a.txt` 位元組正確
  And 絕對路徑成員 `/abs_evil.txt` 的拒絕不是靠 `data_filter`：直接以 `tarfile.data_filter` 處理同一 tar 會靜默剝掉前導斜線而寫出 `abs_evil.txt`（本 AT 在 tmp 內用另一個目的目錄示範並斷言此事實，作為`自寫預檢不是冗餘`的證據）
  And 路徑長度邊界：`sys.platform` 以替身設為 `win32` 時，成員相對路徑長度使 `len(str(root))` 加 1 加成員長度恰為 259 者預檢通過、為 260 者拒絕且碼 `SANDBOX-PATH-TOO-LONG`；`sys.platform` 設為 `linux` 時 260 者通過（POSIX 不判）
  And `tarfile.data_filter` 缺席：以 `mock.patch.object` 包住 `tarfile` 的 `data_filter` 屬性、於其內 `delattr` 之後，經 CLI 呼叫 `sandbox` 的合法 PROP：rc 為 `3`、stderr 含 `TARFILE-FILTER-MISSING`、零 `app.sandbox`、`<HOME>/sandbox/` 下無目錄（不降級為無過濾抽取）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_1_E_4]"
```

```gherkin
# AT-215-2-1
# 對應 AC: AC-215-2（PRD AC-SI-15-2；R105）不使用鐵律五的毀滅性 git 形態：靜態掃描套件原始碼，並以執行期記錄器對整條沙盒到回滾的流程驗證每個 `git` 子行程的子命令
# 測試類型: Integration
# 自動化工具: pytest + AST 掃描 + 子行程記錄器 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_2_1_ -q -p no:xdist -o addopts=

Feature: 不使用毀滅性 git 形態

Scenario: 原始碼與實跑流程都只有白名單內的 git 子命令
  Given 真 repo 的 `tools/lib/selfimproving/*.py`（唯讀）；§5.6 的 `git_subcommands(argv)`（取 `git` 之後、略過 `-C <目錄>` 與 `-c <鍵=值>` 後的第一個非旗標位置詞）；禁用集合＝`stash`、`reset`、`checkout`、`clean`、`restore`、`switch`、`worktree`；允許集合＝`apply`、`archive`、`status`、`rev-parse`、`log`、`show`、`grep`、`merge-base`；tmp 內的 `R` 與以真動詞走完的全流程：`drive_to(R, "promoted", via="cli")`（含 `sandbox`、`verify`、`decide --kind promote`、`promote`），再 `decide --kind rollback` 與 `rollback`
  When (1) 以 `ast` 掃描每個套件原始檔：對每個 `Git(...).run(...)`／`<x>.run(...)` 呼叫的字面引數序列與每個以字面 `"git"` 起頭的 argv 清單取子命令；(2) 以 `mock.patch.object` 包住 `subprocess.run` 與 `subprocess.Popen`（轉呼叫真實函式並記錄 argv），在同一個行程內跑上述全流程
  Then 靜態掃描找到的子命令集合不含任何禁用詞，且包含 `apply` 與 `archive`、呼叫站點總數至少 6（掃描不是空轉）；執行期記錄到的 `git` argv 至少 10 筆，子命令集合 ⊆ 允許集合、不含任何禁用詞；`apply` 與 `archive` 的 argv 皆含 `-c`、`core.autocrlf=false`
  And 沙盒與驗證兩個動詞呼叫前後 `surface(R)` 不變（只有 `promote` 之後正式面才變，且 `HEAD` 不變、`git log` 無新 commit）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_2_1]"
```

```gherkin
# AT-215-2-E-1
# 對應 AC: AC-215-2（PRD AC-SI-15-2；R105、R85 (a)）掃描判準自證與清理語意：毀滅性形態被判紅、白名單形態不誤判；清理只丟棄該 PROP 的副本，不經 git、不動兄弟目錄與 repo
# 測試類型: Unit
# 自動化工具: pytest（合成原始碼）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_2_E_1_ -q -p no:xdist -o addopts=

Feature: 掃描判準有牙

Scenario: 合成的違規原始碼各被命中，合規的不被誤判；重建沙盒時的清理不碰別處
  Given §5.6 的 `scan_git_forms(source_text)`（與全流程掃描共用同一函式，§5.6）；GITFORM-BAD 表（每列一段合成原始碼）：`Git(repo).run("reset", "--hard")`；`Git(repo).run("-c", "core.quotepath=false", "checkout", "--", "f")`；`Git(repo).run("clean", "-fd")`；`Git(repo).run("stash")`；`Git(repo).run("restore", "f")`；`Git(repo).run("switch", "-f", "main")`；`Git(repo).run("-C", "x", "worktree", "add", "y")`；`argv = ["git", "-C", d, "reset", "--soft", "HEAD~1"]`；GITFORM-OK 表：`Git(repo).run("apply", "--numstat", "-z", p)`、`Git(repo).run("-c", "core.autocrlf=false", "archive", "--format=tar", b)`、`Git(repo).run("rev-parse", "HEAD")`、`Git(repo).run("grep", "-n", "stash")`（子命令字面是 `grep`，`stash` 只是搜尋詞）；`R` 與兩個已凍結已核准的 PROP `P`、`Q`；`<HOME>/sandbox/<P>/stale.txt` 與 `<HOME>/sandbox/<Q>/canary.txt` 事先各放一個檔（前一輪遺留的目錄）；`mq0＝<HOME>/sandbox/<Q>` 的樹 manifest；`surf0＝surface(R)`
  When 對兩張表逐列呼叫 `scan_git_forms`；以記錄器包住 `subprocess.run` 後呼叫 `M(R, "sandbox", P)`（遺留的舊目錄被重建）
  Then BAD 八列各回至少一筆命中且點名子命令；OK 四列回空；`sandbox` rc 為 `0`，重建期間記錄到的 `git` argv 子命令集合 ⊆ {`apply`、`archive`、`status`、`rev-parse`、`log`、`show`、`grep`、`merge-base`}（清理沒有走 git）
  And `stale.txt` 不存在、`<HOME>/sandbox/<P>` 的樹等於 base 的獨立副本（舊目錄被新樹取代）；`<HOME>/sandbox/<Q>` 的 manifest 等於 `mq0`、`canary.txt` 仍在（兄弟目錄不受影響）；`surface(R)` 等於 `surf0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_2_E_1]"
```

```gherkin
# AT-215-4-1
# 對應 AC: AC-215-4（PRD AC-SI-15-4；R69、R85 (d)(e)(f)、R86）沙盒失敗仍寫 `app.sandbox`：patch 套不上、`touched` 超集、回滾乾跑不過、`git apply` 逾時——欄位如實、PROP 進 `sandboxed`、rc 0、`applied=false` 者印 OBS 草稿列
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）；替身 `sandbox.apply_patch`、`sandbox.reverse_apply`、`subprocess.run`
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_4_1_ -q -p no:xdist -o addopts=

Feature: sandbox 套用階段的失敗

Scenario: 四種套用階段失敗各自如實入帳
  Given 四份獨立複本 `R1`～`R4`，各有一個已凍結已核准的 PROP：`R1` 的 patch 上下文與 base 不合（`drive_to(…, patch=bad-context)`，§5.2）；`R2` 以替身包住 `sandbox.apply_patch`（先呼叫真實函式、回傳集合再加上字面 `stray.txt`）；`R3` 以替身包住 `sandbox.reverse_apply`（先呼叫真實函式、再於沙盒根寫一個檔 `left_over.txt`）；`R4` 的 `params.json` 把 `probe_timeout_seconds` 設為 2，並以替身令 `subprocess.run` 在 argv 含 `apply` 時拋 `subprocess.TimeoutExpired`（其餘 argv 轉呼叫真實函式；替身記錄各 argv 收到的 `timeout` 值）
  When 各呼叫 `M(R, "sandbox", P)` 與 `MJ(R, "sandbox", P)`（各在另一份複本上）
  Then 四次 rc 皆為 `0`；`R1`：`applied` 為 `false`、`touched_ok` 與 `rollback_ok` 為 `null`、`fail_code` 為 `null`、`sandbox_sha256` 非 `null`；`R2`：`applied` 與 `rollback_ok` 為 `true`、`touched_ok` 為 `false`、`fail_code` 為 `null`；`R3`：`applied` 與 `touched_ok` 為 `true`、`rollback_ok` 為 `false`、`fail_code` 為 `null`；`R4`：`applied` 為 `false`、`touched_ok` 與 `rollback_ok` 為 `null`、`fail_code` 為 `SANDBOX-APPLY-TIMEOUT`、`sandbox_sha256` 非 `null`
  And 每份複本：`app.sandbox` 恰一筆、PROP 態為 `sandboxed`（不卡在 `approved`）、`events.transitions` 為 `PASS`；`applied` 為 `false` 的 `R1`、`R4` 其 stdout 末尾為 `obs-draft:` 加恰一行草稿列（症狀以 `si sandbox` 起頭並含 `applied=false`，`draft_ok` 成立）；`R2`、`R3` 的 stdout 無 `obs-draft:`；`--json` 形態的鍵序為 `ok`、`kind`、`seq`、`id`、`applied`、`touched_ok`、`rollback_ok`、`fail_code`
  And `R4` 替身記錄的 `apply` 子行程 `timeout` 值為 2（牆鐘上界取自 `probe_timeout_seconds`）；同一替身對 P1 既有的 `git` 呼叫（例如 `rev-parse`）記錄的 `timeout` 值仍為 60（預設不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_4_1]"
```

```gherkin
# AT-215-4-E-1
# 對應 AC: AC-215-4（PRD AC-SI-15-4；R86、R71）失敗之後的收尾：不可靜默重試、無半成品與暫名目錄、兄弟沙盒不受影響、匯出失敗沒有沙盒目錄而套用失敗有（逐位元為 base）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_4_E_1_ -q -p no:xdist -o addopts=

Feature: sandbox 失敗後的零殘留

Scenario: 失敗後的狀態、目錄與重試
  Given `R`；PROP `P`（`drive_to(R, frozen, patch=bad-context)`，patch 的上下文與 base 不合而套不上）與另一個 PROP `Q`（已正常 `sandbox`，其沙盒樹 manifest 記為 `mq0`）；另一份複本 `Rb` 的 PROP `Pb`（匯出失敗：以替身令 `subprocess.run` 在 argv 含 `archive` 時回 rc 128）
  When 對 `P` 與 `Pb` 各呼叫 `sandbox` 一次（rc 0），再各呼叫第二次；列舉 `<HOME>/sandbox/` 與 `<HOME>/`
  Then 第二次 rc 皆為 `1`、碼 `STATE-NOT-APPROVED`（失敗後不可靜默重試；唯一的後續是 `verify` 收 NE 之後由掌舵者 `return`）；各 PROP 的 `app.sandbox` 恆為一筆；`MJ(status)` 顯示兩者為 `sandboxed`
  And `P`（套用失敗）的 `<HOME>/sandbox/<P>` 存在且其樹 manifest 等於事件的 `sandbox_sha256`（樹仍是 base，patch 沒有半套進去）；`Pb`（匯出失敗）的 `<HOME>/sandbox/<Pb>` 不存在；兩者皆無暫名目錄與殘留的 tar 檔（`<HOME>/sandbox/` 與其同層只有預期的目錄）；`Q` 的沙盒樹 manifest 等於 `mq0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_4_E_1]"
```

```gherkin
# AT-215-4-E-2
# 對應 AC: AC-215-4（PRD AC-SI-15-4；R85 (b)(c)(g)）匯出階段的四種失敗與成因碼：git 失敗、匯出逾時、成員被拒（真 git 的符號連結成員）、`Git.run` 逾時上界取自參數
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）；替身 `subprocess.run`
# 判定指令: python -m pytest tools/tests/test_selfimproving_sandbox.py -k AT_215_4_E_2_ -q -p no:xdist -o addopts=

Feature: sandbox 匯出階段的失敗

Scenario: 匯出失敗一律 `SANDBOX-EXPORT-FAILED`，成因碼在 stderr
  Given 四份獨立複本，各有已凍結已核准的 PROP：(a) 以替身令 `subprocess.run` 在 argv 含 `archive` 時回 `CompletedProcess` 的 rc 128 與 stderr `fatal: not a valid object name`；(b) `probe_timeout_seconds` 為 2，替身在 argv 含 `archive` 時拋 `subprocess.TimeoutExpired`；(c) 真 git：複本的 base commit 含一個由 `git update-index --add --cacheinfo 120000,<blob>,docs/notes/link.md` 建出的符號連結項（複本 `core.symlinks` 設為 `false`、工作樹放同內容的一般檔使 `git status` 乾淨；PROP 在此 commit 之後 `prop-new`，故 base 即此 commit）；(d) `git` 執行檔不可用（以替身令 `subprocess.run` 對 `git` 拋 `FileNotFoundError`）
  When 各呼叫 `M(R, "sandbox", P)`
  Then 四次 rc 皆為 `0`；事件 `applied` 為 `false`、`touched_ok` 與 `rollback_ok` 為 `null`、`sandbox_sha256` 為 `null`、`fail_code` 為 `SANDBOX-EXPORT-FAILED`；stderr 含成因碼，依序為 (a) `SANDBOX-GIT-FAILED`、(b) `SANDBOX-EXPORT-TIMEOUT`、(c) `SANDBOX-MEMBER-REJECTED`（detail 含成員名 `docs/notes/link.md`）、(d) `SANDBOX-GIT-FAILED`
  And 每份：`<HOME>/sandbox/<P>` 不存在、無殘留 tar 檔、stdout 末尾 `obs-draft:` 加恰一行草稿列；PROP 態為 `sandboxed`；替身記錄的匯出子行程 `timeout` 值為 `probe_timeout_seconds`（(b) 為 2、其餘為 600）；(c) 的 `surface(R)` 於呼叫前後相同
  And 這四份的後續 `verify` 走 ⓪ 路徑（不跑探針、verdict 為 NE、碼 `SANDBOX-EXPORT-FAILED`），由 `verify` 側的負控釘住
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_4_E_2]"
```


**D. 驗證、三態判定與證據（VF）**

```gherkin
# AT-217-1-1
# 對應 AC: AC-217-1（PRD AC-SI-17-1；R87 (c)、R88）驗證在上限內完成的正控：探針在 `probe_timeout_seconds` 內結束不被誤殺；複驗到 `verify_runs_max` 次為止仍受理（上限含端點）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_217_1_1_ -q -p no:xdist -o addopts=

Feature: verify 在上限內

Scenario: 慢探針在上限內完成，複驗到上限次仍受理
  Given `R` 的 `params.json`：`probe_timeout_seconds` 為 4、`verify_runs_max` 為 2；`P`＝`drive_to(R, sandboxed, heldout=make_heldout(dir, probes=slow, delay=1))`（探針 `probe_slow.py` 先等 1 秒再依症狀有無回 rc；其餘同 `count`；held-out 已凍結、沙盒已建）
  When 依序呼叫 `MJ(R, verify, P)` 兩次（第二次為複驗邊），並以牆鐘量測每次
  Then 兩次 rc 皆為 `0`、`verdict` 皆為 `PASS`、`reasons` 皆為空清單；每次整體小於 15 秒；兩個驗證檔 `verify1.json`、`verify2.json` 各自存在、其內每個 `rec` 的 `timed_out` 為 `false`（耗時約 1 秒、在 4 秒上限內，沒有被殺）、`rc` 依序為 `1`、`0`、`1`
  And 兩筆 `app.verify` 事件的 `verify_sha256` 各等於對應檔位元組的 `sha256:`；PROP 態維持 `verified`、`Prop.verdict` 為 `PASS`；`MJ(R, check)` 的 `events.transitions`、`events.prop_files`、`events.verdict` 皆為 `PASS`
  And 第三次呼叫的拒收由次數上限的負控釘住（本 AT 只斷言端點：恰 `verify_runs_max` 次受理）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_217_1_1]"
```

```gherkin
# AT-217-1-E-1
# 對應 AC: AC-217-1（PRD AC-SI-17-1；R88、R74 (e)）`app.verify` 超過 `verify_runs_max`：rc 1、須升級人工、零殘留；上限取自參數、以 `(prop, rev)` 計；手寫帳本超限被 `check` 標紅
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_217_1_E_1_ -q -p no:xdist -o addopts=

Feature: verify 次數上限

Scenario: 第 `verify_runs_max` 加 1 次不受理，上限來自參數與 (prop, rev)
  Given `R`（`verify_runs_max` 為 2）與 `P`＝`drive_to(R, sandboxed)` 後已 `verify` 兩次（`verify1.json`、`verify2.json` 在）；`snap0＝snap(R)`、`home0＝tree_files(HOME)`；`Rb`（`verify_runs_max` 為 1）已 `verify` 一次；手寫帳本 `L`（同一 PROP：rev 1 有兩筆 `app.verify`〔第二筆為複驗邊〕、其後 `dec(return)` 與 rev 2 重核准、重沙盒、一筆 `app.verify`）與 `L2`（同一 PROP 的 rev 1 有三筆 `app.verify`、`verify_runs_max` 為 2）
  When 對 `P` 呼叫第三次 `verify`（外層以記錄器包住 `runner` 的探針入口）；對 `Rb` 呼叫第二次；對 `L`、`L2` 各 `MJ(check)`
  Then `P` 的第三次 rc 為 `1`、碼恰為 `VERIFY-RUNS-EXCEEDED`，stdout 依序為 `reject verify …`（detail 含字樣`升級人工`）、碼行、`obs-draft:` 與恰一行草稿列且 `draft_ok` 成立；`snap(R)` 等於 `snap0`（沒有 `verify3.json`、事件帳本位元組不變）、`tree_files(HOME)` 等於 `home0`；記錄器的探針呼叫數為 `0`（超限前不跑任何子行程）
  And `Rb` 的第二次同樣 rc 為 `1`、碼 `VERIFY-RUNS-EXCEEDED`（上限讀自 `params.json`，不是寫死的 2）；`L` 的 `events.transitions` 為 `PASS`（rev 2 的第一次不受 rev 1 兩次影響）；`L2` 為 `FAIL`、碼 `VERIFY-RUNS-EXCEEDED`、subject 為該 PROP
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_217_1_E_1]"
```

```gherkin
# AT-217-1-E-2
# 對應 AC: AC-217-1（PRD AC-SI-17-1、§9.4；R87 (c)、R88、R89）探針逾時：殺行程樹、收 NE（不收 FAIL）、其後步驟不執行、`PROBE-TIMEOUT` 記入、孫行程不殘留、整體有界
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程（含孫行程）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_217_1_E_2_ -q -p no:xdist -o addopts=

Feature: verify 探針逾時

Scenario: 三個步驟各自逾時一次，皆收 NE 並且行程樹被殺
  Given `R` 的 `probe_timeout_seconds` 為 2；三份獨立複本各有 `P＝drive_to(R, sandboxed)`，其 held-out 的探針依序為：(a) `probe_hang.py`（永遠不結束：啟動一個每 0.1 秒對 `<tmp>/hb.txt` 追加一個位元組的孫行程，自己再等 600 秒）；(b) `probe_hang_fixed.py`（症狀在時 rc 為 1、症狀不在〔已套用〕時如 (a) 般掛住）；(c) `probe_hang_mutated.py`（只在突變後的樹掛住：基線 rc 1、套用後 rc 0、突變後掛住）；孫行程啟動時把自己的 pid 寫進 `<tmp>/pid.txt`，測試以 `addCleanup` 對該 pid 做保底清理（`os.kill` 加 `signal.SIGTERM`，只在被測行為失效、行程殘留時才有東西可清；子行程夾具必回收，NFR-P2-4）
  When 各呼叫 `MJ(R, verify, P)`，以牆鐘量測整次呼叫；呼叫返回後取 `hb.txt` 的位元組數 `s0`、等候 1.5 秒再取 `s1`
  Then 三次 rc 皆為 `0`、整次小於 15 秒；`verdict` 皆為 `NE`、`reasons` 恰為 `[PROBE-TIMEOUT]`（不是 `FAIL`、不含 `BASELINE-NOT-RED` 或 `PATCHED-NOT-GREEN`）；`s1` 等於 `s0`（行程樹包括孫行程已被殺，心跳不再增長；`s0` 大於 `0` 證明孫行程確實啟動過）
  And 逾時步驟的 `rec`：`timed_out` 為 `true`、`rc` 為 `null`；步驟欄位：(a) `baseline_red` 為 `null`、`steps.patched` 為空清單、`steps.mutated` 為 `null`；(b) `baseline_red` 為 `true`、`patched_green` 為 `null`、`steps.mutated` 為 `null`；(c) 前兩者為 `true`、`mutated_red` 為 `null`、`steps.mutated` 內含該筆逾時 `rec`；`verify_sha256` 非 `null`（有探針執行過就有驗證檔）
  And 沙盒樹於返回後等於 `sandbox_sha256`（逾時之後仍反向套用還原到 base）；PROP 態為 `verified`；stdout 末尾為 `obs-draft:` 加恰一行草稿列、症狀含 `si verify` 與 `PROBE-TIMEOUT`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_217_1_E_2]"
```

```gherkin
# AT-219-1-1
# 對應 AC: AC-219-1（PRD AC-SI-19-1；R69、R88、R89、R90）三步對照的正控：基線重現症狀（RED）、套用後消失（GREEN）、突變後回來（RED）→ PASS；證據檔與事件欄位齊備；每個探針每步恰執行一次；沙盒樹還原
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_1_1_ -q -p no:xdist -o addopts=

Feature: verify 三步對照正控

Scenario: RED、GREEN、突變 RED 皆成立時判 PASS
  Given `R`、`P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=count, mutation=True, counter=<tmp>/cnt.txt))`（探針 `probe_count.py` 讀沙盒內 `docs/notes/demo.md`，含字面 `FIXED-LINE` 則 rc 為 0、否則 rc 為 1，並於 `cnt.txt` 追加一行；patch 為在 `demo.md` 加入 `FIXED-LINE` 的一行；manifest 的 `mutation` 為移除該行的 `mutation.patch`）；`sb0＝沙盒樹 manifest`、`s0＝snap(R)`
  When 呼叫 `MJ(R, verify, P, --by, VF1)`
  Then rc 為 `0`；JSON 鍵序為 `ok`、`kind`、`seq`、`id`、`verdict`、`probes_n`、`reasons`、`baseline_red`、`patched_green`、`mutated_red`、`carrier_proof`；`verdict` 為 `PASS`、`probes_n` 為 `1`、`reasons` 為 `[]`、四個布林皆為 `true`（manifest 沒有宣告 `module`，`carrier_proof` 依 R88 為 `true`）；文字形態（另一份複本）為單行 `ok app.verify seq=<n> id=APP-SI-<NNN> verdict=PASS probes_n=1 reasons=-`
  And 事件鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`prop`、`rev`、`verdict`、`baseline_red`、`patched_green`、`mutated_red`、`carrier_proof`、`probes_n`、`verify_sha256`、`heldout_digest`、`reasons`；`by` 為 `VF1`；`heldout_digest` 等於該 PROP `heldout.freeze` 的 `digest`；`verify_sha256` 等於 `verify1.json` 位元組的 `sha256:`
  And `verify1.json`：無 BOM、無 CR、以單一 LF 結尾；頂層鍵序為 `schema_rev`、`prop`、`rev`、`k`、`base`、`heldout_digest`、`carrier`、`steps`；`k` 為 `1`、`carrier` 為空物件；`steps.baseline`、`steps.patched`、`steps.mutated` 各一筆 `rec`，`rc` 依序為 `1`、`0`、`1`；每筆 `rec` 的 `cmd` 為未展開的 argv（第 0 項為字面 `{python}`，含字面 `{heldout}`、`{sandbox}`）、`timed_out` 為 `false`、`n_pop` 為 manifest 宣告值
  And `cnt.txt` 恰 3 行（每個探針每步只執行一次，不重試至通過）；`MJ(R, status)` 的 PROP 態為 `verified`；沙盒樹 manifest 等於 `sb0`（三步結束後已反向套用還原）；`snap(R)` 相對 `s0` 只多 `verify1.json`、事件帳本只被追加
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_1_1]"
```

```gherkin
# AT-219-1-E-1
# 對應 AC: AC-219-1（PRD AC-SI-19-1、§9.4〈三態判定表〉；R88、R89）三步缺一的負控：基線不紅、套用不綠、突變不紅、無突變、突變來源重複；三步不因早失敗而略過
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_1_E_1_ -q -p no:xdist -o addopts=

Feature: verify 三步缺一

Scenario: 每個缺口收到規定的 verdict 與 reasons，且欄位如實記錄
  Given §5.4 的 VF-STEPS 表（每列＝一份獨立複本的 held-out 設定、預期欄位）：(a) 探針 `probe_always_ok.py`（永遠 rc 0）＋有效突變；(b) 探針 `probe_always_red.py`（永遠 rc 1）＋有效突變；(c) 探針 `probe_count.py` 加一個無效突變（`mutation.patch` 改的是 `demo.md` 的另一行，不移除 `FIXED-LINE`）；(d) 探針 `probe_count.py`、manifest 無 `mutation` 且不給旗標；(e) 同 (d) 但 manifest 有 `mutation` 又給 `--mutation <檔>`；(f) 同 (d) 但給 `--mutation <有效突變檔>`（manifest 無 `mutation`）；每個複本的 `P＝drive_to(R, sandboxed, …)`
  When 各呼叫 `MJ(R, verify, P)`（(e) 加 `--mutation`、(f) 加 `--mutation`）
  Then (a) `verdict` 為 `NE`、`reasons` 為 `[BASELINE-NOT-RED]`，欄位 `baseline_red` 為 `false`、`patched_green` 為 `true`、`mutated_red` 為 `false`；(b) `verdict` 為 `FAIL`、`reasons` 為 `[PATCHED-NOT-GREEN]`，欄位 `baseline_red` 為 `true`、`patched_green` 為 `false`、`mutated_red` 為 `true`；(c) `verdict` 為 `NE`、`reasons` 為 `[MUTATION-NOT-RED]`、`mutated_red` 為 `false`；(d) `verdict` 為 `NE`、`reasons` 為 `[MUTATION-ABSENT]`、`mutated_red` 為 `null`、`steps.mutated` 為 `null`；(f) `verdict` 為 `PASS`、`mutated_red` 為 `true`（旗標形態的突變有效）；(a)～(d)(f) 的 rc 皆為 `0`；(e) rc 為 `3`、stderr 含 `selfimproving:` 與`突變來源二擇一`字樣、零寫入（事件帳本位元組不變、無新驗證檔）
  And 前述各列的三個步驟在非逾時的情況下全部執行（(b) 的 `steps.mutated` 非 `null`；證據齊備，不因 `patched_green` 為 `false` 而略過突變步）；每個非 `PASS` 的 verdict 其 stdout 末尾為 `obs-draft:` 加恰一行草稿列且 `draft_ok` 成立
  And `MJ(check)` 對 (a)～(d)(f) 的 `events.verdict` 為 `PASS`（記錄欄位與重算一致）、`events.prop_files` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_1_E_1]"
```

```gherkin
# AT-219-1-E-2
# 對應 AC: AC-219-1（PRD AC-SI-19-1；R87 (a)(b)、R88）載具自證：模組在沙盒內才算數；上層 `PYTHONPATH` 不洩入；不帶 `-I`；未宣告 `module` 時自證為真（空集合語意）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_1_E_2_ -q -p no:xdist -o addopts=

Feature: verify 載具自證

Scenario: 被測模組必須從沙盒載入，否則收 NE
  Given 四份獨立複本（`make_p2_repo` 基線含追蹤檔 `demo_pkg/__init__.py` 與 `demo_pkg/core.py`），各有 `P＝drive_to(R, sandboxed, …)`：(a) 探針宣告 `module` 為 `json`（標準庫，載入路徑在直譯器安裝目錄、不在沙盒）；(b) 探針宣告 `module` 為 `demo_pkg.core`（沙盒內有，且測試環境的 `PYTHONPATH` 設為另一個含同名替身 `demo_pkg/core.py` 的 `decoy/` 目錄）；(c) manifest 沒有任何探針宣告 `module`；(d) 探針 `probe_flags.py`（印出 `isolated=<sys.flags.isolated>` 與 `safe_path=<sys.flags.safe_path>`），宣告 `module` 為 `demo_pkg.core`
  When 各呼叫 `MJ(R, verify, P)`
  Then (a) `carrier_proof` 為 `false`、`verdict` 為 `NE`、`reasons` 為 `[CARRIER-PROOF-FAILED]`（三步仍執行、欄位如實）；(b) `carrier_proof` 為 `true`、`verdict` 為 `PASS`，`verify1.json` 的 `carrier` 為 `{demo_pkg.core: demo_pkg/core.py}` 形（值為沙盒相對 posix 路徑，不是 `decoy/` 內路徑）；(c) `carrier_proof` 為 `true`、`carrier` 為空物件、`verdict` 為 `PASS`
  And (d) 探針輸出的 `tail` 顯示 `isolated=0` 與 `safe_path=False`（子行程不帶 `-I`／`-P`，否則 `PYTHONPATH` 被忽略而自證失效）；(a) 對照：把同一探針的 `module` 改為 `demo_pkg.core` 後 `carrier_proof` 為 `true`（證明 (a) 的 NE 是自證判準在動，不是探針壞了）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_1_E_2]"
```

```gherkin
# AT-219-1-E-3
# 對應 AC: AC-219-1（PRD AC-SI-19-1、§9.3 `verify` 列；R88、R71、R70）`verify` 的前置與用法負控：態、凍結、無人值守、不存在、參數鍵、旗標、沙盒樹漂移與重新匯出、鎖內重驗競態；全部零殘留
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_1_E_3_ -q -p no:xdist -o addopts=

Feature: verify 前置與用法

Scenario: 前置不符 rc 1 或 rc 3，沙盒樹漂移可重新匯出，競態不留驗證檔
  Given §5.4 的 VF-PRE 表（每列＝一份獨立複本情境）：(a) PROP 為 `approved`（尚無沙盒）；(b) PROP 為 `promoted`；(c) `P＝drive_to(R, sandboxed)` 之後以 `drop_events(R, heldout.freeze)` 刪掉該 PROP 的凍結事件（`sandboxed` 而全無 `heldout.freeze`）；(d) `AUTOSDD_UNATTENDED` 設為 `1`；(e) 位置參數為不存在的 PROP 號（執行期組出）；rc 3 組：(f) `probe_timeout_seconds` 為 `0`；(g) `verify_runs_max` 為 `true`；(h) `AUTOSDD_SI_DIR` 指向一個一般檔；(i) 未知旗標 `--override`；(j) 缺位置參數；漂移組：(k) 已 `sandbox` 的 PROP，沙盒樹被整個刪除；(l) 沙盒樹內多了一個檔 `stray.txt`；(m) 以測試輔助改寫該 PROP `app.sandbox` 事件的 `sandbox_sha256` 為另一個合法雜湊（重新匯出的真樹不可能等於它）；競態組：(n) 以替身包住 `runner` 的探針入口，於第一次探針呼叫時手寫追加兩筆 `app.verify` 事件（使鎖內重驗時次數已達上限）
  When 各呼叫 `MJ(R, verify, P)` 或對應的 `M`（rc 3 組取文字形態）
  Then (a)(b) rc 為 `1`、碼 `STATE-NOT-VERIFIABLE`；(c) rc 為 `1`、碼 `HELDOUT-NOT-FROZEN`；(d) rc 為 `1`、碼 `UNATTENDED-REFUSED`（先於其餘判，零寫入）；(e) rc 為 `1`、碼 `PROP-NOT-FOUND`；(f)(g)(h)(j) rc 為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭，(f)(g) 並點名該鍵、不以預設值頂替，(h) 的碼 `HOME-UNWRITABLE`；(i) rc 為 `3`；(m) rc 為 `1`、碼 `SANDBOX-TREE-DRIFT`；(n) rc 為 `1`、碼 `STATE-CHANGED`
  And (k)(l) rc 皆為 `0`：重新匯出後樹 manifest 等於 `sandbox_sha256`、verdict 與同 PROP 在乾淨沙盒上相同（`stray.txt` 不在、被刪的樹被重建）；(m)(n) 與全部 rc 為 `1` 或 `3` 的情境：事件帳本與 OBS 帳本位元組不變、無新驗證檔（(n) 剛落地的 `verify1.json` 被刪除）、`snap(R)` 不變
  And rc 為 `1` 的呼叫其 stdout 依序為 `reject verify …`、碼行、`obs-draft:`、恰一行草稿列且 `draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_1_E_3]"
```

```gherkin
# AT-219-2-1
# 對應 AC: AC-219-2（PRD AC-SI-19-2、§9.4〈三態判定表〉；R89）三態判定表的正控：`verdict_of` 純函式逐列、決定層全部成立碼；M／D 類無確定性探針預設 NE（`NO-PROBES`）
# 測試類型: Unit
# 自動化工具: pytest（純函式；加一個 `probes` 為空的 `verify` 實跑）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_2_1_ -q -p no:xdist -o addopts=

Feature: 三態判定表

Scenario: 每一列輸入得到規定的 (verdict, reasons)，只有 PASS 的 reasons 為空
  Given §5.4 的 VERDICT-TABLE（每列＝`verdict_of` 的輸入物件與預期 `(verdict, reasons)`；基準輸入 `B`：沙盒 `applied` 真、`touched_ok` 真、`rollback_ok` 真、`fail_code` 為 `null`；驗證 `probes_n` 1、`carrier_proof` 真、`baseline_red` 真、`patched_green` 真、`mutated_red` 真、`heldout_digest` 等於凍結 `digest`、記錄的 `reasons` 為空；凍結 `n` 為 5、`min_heldout` 為 5）：`B` ⇒ PASS、空；`probes_n` 為 0（其餘欄位為 `null`）⇒ NE、`[NO-PROBES]`；`carrier_proof` 假 ⇒ NE、`[CARRIER-PROOF-FAILED]`；`heldout_digest` 不同 ⇒ NE、`[HELDOUT-DIGEST-MISMATCH]`；`n` 為 4 ⇒ NE、`[HELDOUT-TOO-SMALL]`；`carrier_proof` 假且 `n` 為 4 ⇒ NE、`[CARRIER-PROOF-FAILED, HELDOUT-TOO-SMALL]`（決定層全部成立碼，依 R89 的列出序）；記錄的 `reasons` 含 `HELDOUT-EXPOSED` ⇒ NE、同；含 `EXPOSURE-UNKNOWN` ⇒ NE、同；含 `PROBE-TIMEOUT`（`baseline_red` 為 `null`）⇒ NE、`[PROBE-TIMEOUT]`；`baseline_red` 假 ⇒ NE、`[BASELINE-NOT-RED]`；`patched_green` 假 ⇒ FAIL、`[PATCHED-NOT-GREEN]`；`mutated_red` 假 ⇒ NE、`[MUTATION-NOT-RED]`；`mutated_red` 為 `null` ⇒ NE、`[MUTATION-ABSENT]`；`baseline_red` 假且 `patched_green` 假 ⇒ NE、`[BASELINE-NOT-RED]`（先中層定案、③ 不列）；`applied` 假、`fail_code` 為 `null` ⇒ NE、`[SANDBOX-NOT-APPLIED]`；`applied` 假、`fail_code` 為 `SANDBOX-APPLY-TIMEOUT` ⇒ NE、同碼；`applied` 假、`fail_code` 為 `SANDBOX-EXPORT-FAILED` ⇒ NE、同碼；`touched_ok` 假 ⇒ NE、`[TOUCHED-SUPERSET]`；`rollback_ok` 假 ⇒ FAIL、`[ROLLBACK-DRYRUN-FAILED]`；`touched_ok` 與 `rollback_ok` 皆假 ⇒ NE、`[TOUCHED-SUPERSET, ROLLBACK-DRYRUN-FAILED]`（verdict 取第一個成立者、碼全列）
  When 對每列呼叫 `verdict.verdict_of`；另以 `make_heldout(dir, probes=none)`（`probes` 為空陣列，M／D 類無確定性探針的形態）凍結後對 `P＝drive_to(R, sandboxed)` 實跑 `MJ(R, verify, P)`，並以記錄器記錄 `runner` 的探針呼叫數
  Then 每列回傳與預期逐一相等（verdict 與 `reasons` 的內容及次序）；`verdict` 值域只有 `PASS`、`FAIL`、`NE`；`reasons` 為空若且唯若 `PASS`；`FAIL` 只出現在 `PATCHED-NOT-GREEN` 與 `ROLLBACK-DRYRUN-FAILED` 兩列（其餘無論缺資料或逾時一律 NE）
  And 實跑：rc 為 `0`、`verdict` 為 `NE`、`reasons` 為 `[NO-PROBES]`、`probes_n` 為 `0`、`verify_sha256` 為 `null`（不產生驗證檔）、四個步驟欄位皆為 `null`、探針呼叫數為 `0`；PROP 態為 `verified`；`MJ(check)` 的 `events.verdict` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_2_1]"
```

```gherkin
# AT-219-2-E-1
# 對應 AC: AC-219-2（PRD AC-SI-19-2；R88 ⓪、R89）沙盒失敗先於預檢：`verify` 不跑探針、直接收 NE（或 FAIL）；`check` 的 `events.verdict` 認得它並偵測欄位不自洽
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_2_E_1_ -q -p no:xdist -o addopts=

Feature: verify 的沙盒失敗路徑

Scenario: 五種沙盒失敗各自收規定的 verdict，探針一個都不跑
  Given 五份獨立複本，各有已凍結已核准的 PROP 且 `sandbox` 已以 §5.4 的 SBX-FAIL 手法落成：(a) 匯出失敗（`SANDBOX-EXPORT-FAILED`）；(b) patch 套不上（`applied` 假、`fail_code` 為 `null`）；(c) 套用逾時（`SANDBOX-APPLY-TIMEOUT`）；(d) `touched_ok` 為 `false`；(e) `rollback_ok` 為 `false`；一個記錄器包住 `runner` 的探針入口；`s0＝snap(R)`
  When 各呼叫 `MJ(R, verify, P)`
  Then 五次 rc 皆為 `0`；`probes_n` 皆為 `0`、`verify_sha256` 與 `heldout_digest` 皆為 `null`、`baseline_red`／`patched_green`／`mutated_red`／`carrier_proof` 皆為 `null`；記錄器的探針呼叫數皆為 `0`；`verdict` 與 `reasons` 依序為 (a) `NE`、`[SANDBOX-EXPORT-FAILED]`；(b) `NE`、`[SANDBOX-NOT-APPLIED]`；(c) `NE`、`[SANDBOX-APPLY-TIMEOUT]`；(d) `NE`、`[TOUCHED-SUPERSET]`；(e) `FAIL`、`[ROLLBACK-DRYRUN-FAILED]`
  And 五份皆沒有 `verify1.json`（⓪ 路徑不產生驗證檔）、PROP 態為 `verified`；stdout 末尾為 `obs-draft:` 加恰一行草稿列；`MJ(check)` 的 `events.verdict` 為 `PASS`、`events.prop_files` 為 `PASS`
  And 對 (a) 的 `app.verify` 事件以 `rewrite_event` 把 `probes_n` 改為 `2`（⓪ 成立而 `probes_n` 不為 0）後 `MJ(check)`：`events.verdict` 為 `FAIL`、碼 `VERDICT-MISMATCH`；把 (e) 的 `verdict` 改為 `NE`（與重算不符）亦然
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_2_E_1]"
```

```gherkin
# AT-219-3-1
# 對應 AC: AC-219-3（PRD AC-SI-19-3；R88）命中率只是證據、不得據此自動核准：`verify` 不寫 `dec`、不改 PROP 於核准或晉升的態、事件與驗證檔沒有命中率欄位；R 類（SDD 規則草案）走轉交、進不了沙盒與驗證
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_3_1_ -q -p no:xdist -o addopts=

Feature: 驗證結果不自動核准

Scenario: PASS 之後什麼都不會自動發生
  Given `R` 與 `P＝drive_to(R, sandboxed)`，held-out 的探針宣告 `n_pop` 為 100（母體數，模擬「命中率高」的重放證據）；R 類 PROP `PR`（以 `write_events` 手寫 `prop_ev` 的 `cls` 為 `R`、`route` 為 `handoff:R`、態為 `proposed`；R 類只轉交，不經 `prop-new` 的 patch 流程）；`dec0＝事件帳本中 dec 事件的數量`
  When 呼叫 `MJ(R, verify, P)`；再呼叫 `M(R, promote, P)`；對 `PR` 呼叫 `sandbox`、`heldout-freeze`、`verify`
  Then `verify` 的 verdict 為 `PASS` 而事件帳本的 `dec` 事件數仍等於 `dec0`（`verify` 不寫 DEC）、PROP 態為 `verified`（不是 `promoted`）；`promote` rc 為 `1`、碼 `NO-PROMOTE-DEC`（沒有掌舵者的晉升決定就不會合入）、正式面 `surface(R)` 不變
  And `app.verify` 事件與 `verify1.json` 的鍵集合不含任何以 `hit`、`rate`、`score`、`confidence` 命名的鍵（`events.validate` 對加了 `hit_rate` 鍵的同事件回 `EVENT-KEY-UNKNOWN`）；`rec` 的 `n_pop` 只是母體數、不是比率
  And `PR`（碼以`含`判，階段二全部收集）：`sandbox` rc 為 `1`、碼含 `STATE-NOT-APPROVED`；`heldout-freeze`（`--from` 為合法目錄）rc 為 `1`、碼含 `ROUTE-HANDOFF`；`verify` rc 為 `1`、碼含 `STATE-NOT-VERIFIABLE`（R 類只轉交，驗證與命中率屬 SDD 側）；三者皆零寫入
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_3_1]"
```

```gherkin
# AT-219-3-E-1
# 對應 AC: AC-219-3（PRD AC-SI-19-3；R68、R88）沒有任何自動核准或晉升的旗標與路徑：`verify` 與 `sandbox` 不收 `--approve`、`--auto-promote`、`--hit-rate` 等；用法錯誤 rc 3、零寫入
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_219_3_E_1_ -q -p no:xdist -o addopts=

Feature: 沒有自動核准旗標

Scenario: 試圖以旗標讓驗證結果直接變成決定的呼叫全被拒
  Given `R` 與 `P＝drive_to(R, sandboxed)`；`snap0＝snap(R)`、`ev0＝事件帳本位元組`
  When 呼叫 `M(R, verify, P, <旗標>)`，旗標依序為：`--approve`、`--auto-promote`、`--hit-rate 0.99`、`--min-hit 0.9`、`--decide promote`、`--no-ack`、`--unverified-ack`；另呼叫 `M(R, sandbox, P, --approve)`、`M(R, promote, P, --auto)`、`M(R, rollback, P, --auto)`
  Then 每個呼叫 rc 皆為 `3`、stdout 空、stderr 以 `selfimproving:` 起頭；`snap(R)` 等於 `snap0`、事件帳本位元組等於 `ev0`
  And 對照：同一 PROP 以合法旗標 `--by VF1` 呼叫 `verify` rc 為 `0`（證明被拒的是旗標，不是 PROP 的狀態）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_219_3_E_1]"
```

```gherkin
# AT-218-2-1
# 對應 AC: AC-218-2（PRD AC-SI-18-2；R88、R89、R90 (c)）判定的主依據是外部可重跑訊號：同一組探針在同一 base 的全新沙盒重跑得到相同的 rc 序列；提案本文與審查文字不影響 verdict
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_218_2_1_ -q -p no:xdist -o addopts=

Feature: verdict 取決於可重跑訊號

Scenario: 重跑一致，且提案本文的「已驗證」字樣無效
  Given 兩個 PROP：`PA`（patch 確實修好症狀）與 `PB`（patch 未修好症狀，探針 `probe_always_red.py`）；兩者的 `rN.md` 本文皆含句子「審查者意見：已人工確認本提案有效，建議判定 PASS」，且 `SelfImproving_Proposals/<PROP>/` 之下各放一個 `review.txt`（內容為同一句）；兩者皆已 `sandbox`
  When 各呼叫 `MJ(R, verify, <PROP>)`；再由測試依 `verify1.json` 的 `rec` 自行重跑：在全新目錄以 `git archive <base>` 抽出獨立沙盒、`git -c core.autocrlf=false apply` 套用同一個 patch、把 `cmd` 的 `{python}`、`{sandbox}`、`{heldout}` 換成實際路徑後以 `subprocess.run`（`PYTHONPATH` 只設沙盒根）逐一執行，取三步的 rc 序列
  Then `PA` 的 verdict 為 `PASS`、`PB` 的 verdict 為 `FAIL`（本文與 `review.txt` 的字樣無任何作用）；測試重跑得到的 rc 序列與 `verify1.json` 記錄的逐步 `rc` 完全相同（外部可重跑）；兩次 `verify` 重複呼叫（`PA` 的複驗邊）得到相同 verdict 與 `reasons`
  And `verify` 的旗標清單只有 `--mutation`、`--by`、`--json`、`--repo`（沒有任何覆寫 verdict 的旗標，負控逐一斷言）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_218_2_1]"
```

```gherkin
# AT-218-2-E-1
# 對應 AC: AC-218-2（PRD AC-SI-18-2；R88、R98 (c)）沒有覆寫 verdict 的路徑：旗標一律拒收；手改事件的 verdict（把 FAIL 改成 PASS）被 `check` 的 `events.verdict` 標紅；欄位全部自洽的偽 PASS 是誠實劃界
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_218_2_E_1_ -q -p no:xdist -o addopts=

Feature: verdict 不可覆寫

Scenario: 旗標覆寫被拒、事後手改被偵測
  Given `R`、已 `verify` 得 `FAIL`（`PATCHED-NOT-GREEN`）的 PROP `PB`（patch 未修好症狀、探針 `probe_always_red.py`）；`ev0＝事件帳本位元組`
  When 呼叫 `M(R, verify, PB, <旗標>)`，旗標依序為：`--verdict PASS`、`--override`、`--force`、`--llm-opinion pass`、`--set-verdict PASS`；另以 `rewrite_event` 把 `PB` 最近一筆 `app.verify` 的 `verdict` 改成 `PASS`（`reasons` 同步改為空清單，使單事件欄位表仍合規）後 `MJ(R, check)`；另一份複本把 `PASS` 的事件改成 `FAIL`
  Then 五個旗標呼叫 rc 皆為 `3`、stdout 空、事件帳本位元組等於 `ev0`；手改成 `PASS` 後 `events.verdict` 為 `FAIL`、碼 `VERDICT-MISMATCH`（`PB` 的 `patched_green` 仍記為 `false`，重算為 `FAIL`）；改成 `FAIL` 的複本同樣 `VERDICT-MISMATCH`
  And 誠實劃界（PRD §9.4）：把 `PB` 的欄位一併改成`全部自洽的偽 PASS`（`baseline_red`、`patched_green`、`mutated_red` 全 `true`、`reasons` 空、`verdict` 為 `PASS`）後，`events.verdict` 為 `PASS`（`check` 的重算只驗欄位自洽，偵測不到欄位與真實探針結果不符；稽核靠 QA 以同指令重跑，R90 (c)）——本 AT 以此斷言釘住邊界，避免誤以為 `check` 能擋住偽造
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_218_2_E_1]"
```

```gherkin
# AT-220-2-1
# 對應 AC: AC-220-2（PRD AC-SI-20-2；R88、R89）評估集規模達 `min_heldout` 時不因小樣本判 NE：案例數恰等於下限放行；下限取自參數
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_220_2_1_ -q -p no:xdist -o addopts=

Feature: held-out 規模下限

Scenario: n 等於 min_heldout 放行，下限隨參數移動
  Given `R`（`min_heldout` 為 5）；`P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=count, mutation=True))`；另一份 `Rb`（`min_heldout` 改為 3）的 `Pb`，其 held-out 為 `cases=3`
  When 各呼叫 `MJ(R, verify, P)`
  Then `P` 的 `verdict` 為 `PASS`、`reasons` 為空（`n` 為 5 恰等於下限，不是`小於`）；`Pb` 同為 `PASS`（下限讀自 `params.json`，不是寫死的 5）
  And `MJ(check)` 的 `events.verdict` 為 `PASS`（以 `heldout.freeze.n` 與 `min_heldout` 重算一致）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_2_1]"
```

```gherkin
# AT-220-2-E-1
# 對應 AC: AC-220-2（PRD AC-SI-20-2；R88、R89、R91）小樣本不得宣稱有效：`n` 小於 `min_heldout` ⇒ NE，即使三步全成立；NE 不能以前式晉升
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_220_2_E_1_ -q -p no:xdist -o addopts=

Feature: held-out 規模不足

Scenario: 案例數 4 與 1 皆判 NE，探針仍照常執行
  Given `R`（`min_heldout` 為 5）；`P4`＝`drive_to(R, sandboxed, heldout=make_heldout(dir, cases=4, probes=count, mutation=True))`、`P1`＝同上 `cases=1`；一個記錄器記錄探針呼叫數
  When 各呼叫 `MJ(R, verify, <PROP>)`；再對 `P4` 以 `write_events` 補一筆前式 `dec(promote)`（無 `flags`）並呼叫 `promote`
  Then 兩者 `verdict` 皆為 `NE`、`reasons` 皆為 `[HELDOUT-TOO-SMALL]`；三步欄位 `baseline_red`、`patched_green`、`mutated_red` 皆為 `true`（探針照常執行，證據齊備）、探針呼叫數各為 `3`；`probes_n` 為 `1`；stdout 末尾為 `obs-draft:` 加恰一行草稿列
  And `P4` 的 `promote` rc 為 `1`、碼含 `PROMOTE-FORM-MISMATCH`（NE 配前式不收；晉升須以`未驗採納`式，由掌舵者另打；手寫的 DEC 無逐字稿，故另含回查碼，以`含`判）；正式面不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_2_E_1]"
```

```gherkin
# AT-220-4-1
# 對應 AC: AC-220-4（PRD AC-SI-20-4；R88、R90 (b)）預檢正控：held-out 目錄 digest 重算相符；暴露掃描在可評估且未命中時不產生 NE；掃描範圍只含子代理逐字稿中凍結時刻之後的工具呼叫（含針但早於凍結者不計）
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_220_4_1_ -q -p no:xdist -o addopts=

Feature: 預檢正控

Scenario: 沒有命中時 verdict 不受預檢影響
  Given `R`、`P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=count, mutation=True))`；合成逐字稿目錄 `<CLAUDE_CONFIG_DIR>/projects/<slug>/`（`<slug>` 依 R77 (a)）內：`subagents/agent-1.jsonl`（一筆 `assistant` 的 `tool_use`，`input` 為 `{file_path: docs/notes/demo.md}`；一筆 `assistant` 的 `text` 區塊，內文逐字含 held-out 目錄絕對路徑；一筆 `user` 記錄，內文含字面 `SelfImproving_Protocol/params.json`）；頂層主控逐字稿 `<sid>.jsonl`（`tool_use` 的 `input` 含 held-out 目錄絕對路徑）；另一個 PROP 的 held-out 路徑出現在子代理的 `tool_use` 內（路徑不以本 PROP 的路徑為前綴）；(e) 另一檔 `subagents/agent-2.jsonl`：一筆 `assistant` 的 `tool_use`（`Read`，`input.file_path` 為 `docs/06_quality/SelfImproving_Protocol/params.json`），頂層 `timestamp` 為本 PROP 的 `heldout.freeze` 事件時刻 `t`（於執行期自事件帳本讀取）減 1 小時——含針、但早於凍結；該檔的 mtime 亦設為早於 `t`；(e2) 再一檔 `subagents/agent-3.jsonl`：先一筆含針的 `assistant` `tool_use`（同 (e) 的 `Read`，`input.file_path` 為 `docs/06_quality/SelfImproving_Protocol/params.json`），頂層 `timestamp` 為 `t` 減 1 小時，其後一筆良性 `assistant` `tool_use`（`Read`，`input.file_path` 為 `docs/notes/demo.md`），頂層 `timestamp` 為 `t` 加 1 分鐘；該檔的 mtime 設為不早於 `t`（釘住記錄層過濾：只做 mtime 略過、不做記錄層時間戳過濾的實作會在此檔計入含針記錄而誤判）。除 (e)(e2) 之外，子代理逐字稿各記錄的頂層 `timestamp` 皆為 `t` 加 1 分鐘
  When 呼叫 `MJ(R, verify, P)`
  Then `verdict` 為 `PASS`、`reasons` 為空；`heldout_digest` 等於凍結的 `digest`（預檢重算相符）；assistant 的 `text` 區塊、`user` 記錄、主控逐字稿、他 PROP 的路徑皆不計入（只量子代理的 `tool_use` 工具呼叫字串）；(e)(e2) 含針但時間戳早於 `t` 的記錄不計入（凍結之前的工具呼叫取不到凍結之後才存在的 held-out 內容）；(e2) 的檔 mtime 不早於 `t` 仍為 `PASS`（記錄層過濾生效，不只靠 mtime 略過）
  And 對照：`projects/<slug>/` 存在而完全沒有 `subagents/` 目錄時，同一 PROP 的 `verdict` 仍為 `PASS`（可評估且未命中，不是 `EXPOSURE-UNKNOWN`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_4_1]"
```

```gherkin
# AT-220-4-E-1
# 對應 AC: AC-220-4（PRD AC-SI-20-4；R88、R89、R90 (b)）預檢負控：held-out 被改動、子代理逐字稿在凍結時刻之後的工具呼叫命中凍結目錄、`params.json`、量測腳本（缺或不可解析的時間戳視為窗口內）——皆 NE、探針照常跑、只量不阻擋
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_220_4_E_1_ -q -p no:xdist -o addopts=

Feature: 預檢負控

Scenario: 每個命中形態各收 NE 與對應碼，並且證據照常產生
  Given `R` 與 `P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=count, mutation=True))`、合成逐字稿目錄依 §5.3 的 TRANSCRIPT-DIR 建法；九個獨立複本情境（除 (g)(h)(i) 另有說明外，子代理逐字稿各記錄的頂層 `timestamp` 皆為該 PROP 的 `heldout.freeze` 事件時刻 `t`〔於執行期自事件帳本讀取〕加 1 分鐘）：(a) 凍結之後在 `<HOME>/heldout/<P>/probe_count.py` 檔尾追加一個 `#` 字元（腳本仍可執行、檔案 digest 改變）；(b) 子代理逐字稿一筆 `tool_use`（`Bash`）的 `input.command` 含 held-out 凍結目錄的絕對路徑；(c) 另一筆 `tool_use`（`Read`）的 `input.file_path` 為以反斜線寫成的 `docs\06_quality\SelfImproving_Protocol\params.json`（大小寫混用）；(d) `tool_use`（`Grep`）的巢狀 `input`（物件內陣列內字串）含 `tools/probe/selfimproving_measure.py`；(e) 同時 (a) 與 (b)；(f) 子代理逐字稿放在 `subagents/` 之下兩層子目錄（遞迴）內；(g) 子代理逐字稿一筆 `tool_use`（`Read`）的 `input.file_path` 為 `docs/06_quality/SelfImproving_Protocol/params.json`，頂層 `timestamp` 為 `t` 加 1 分鐘（凍結之後，窗口內）；(h) 同 (g) 的含針 `tool_use`，但該筆記錄缺頂層 `timestamp`（另一份複本為值 `not-a-time`，不可解析）；(i) 同 (g) 的含針 `tool_use`，頂層 `timestamp` 恰等於 `t`（不早於 `t`＝窗口內，邊界值）
  When 各呼叫 `MJ(R, verify, P)`
  Then (a) `verdict` 為 `NE`、`reasons` 為 `[HELDOUT-DIGEST-MISMATCH]`、`heldout_digest` 為重算值（不等於凍結 `digest`）；(b)(c)(d)(f)(g) `verdict` 為 `NE`、`reasons` 為 `[HELDOUT-EXPOSED]`；(h) 兩份複本皆 `verdict` 為 `NE`、`reasons` 為 `[HELDOUT-EXPOSED]`（缺或不可解析的時間戳一律視為落在窗口內，保守計入）；(i) `verdict` 為 `NE`、`reasons` 為 `[HELDOUT-EXPOSED]`（時間戳恰等於 `t`＝不早於 `t`，計入窗口內）；(e) `reasons` 為 `[HELDOUT-DIGEST-MISMATCH, HELDOUT-EXPOSED]`（依 R89 的列出序）；全部 rc 為 `0`（只量不阻擋）
  And 全部情境三步照常執行、`baseline_red`、`patched_green`、`mutated_red` 皆為 `true`、`verify1.json` 在（證據齊備，由 R89 ① 判 NE）；沒有任何命中時（對照組）同一 PROP 為 `PASS`
  And `MJ(check)` 對這些事件的 `events.verdict` 為 `PASS`（`HELDOUT-DIGEST-MISMATCH` 可由 `heldout_digest` 欄位重算；`HELDOUT-EXPOSED` 屬無法由欄位導出的記錄碼，只驗其在 `reasons` 內的一致性）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_4_E_1]"
```

```gherkin
# AT-220-4-E-2
# 對應 AC: AC-220-4（PRD AC-SI-20-4；NFR-P2-11；R90 (b)）暴露掃描的量不到與範圍邊界：逐字稿目錄不存在 ⇒ `EXPOSURE-UNKNOWN`（不是未命中）；壞行不使掃描失敗；只掃 `subagents/**` 的 assistant `tool_use`
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_220_4_E_2_ -q -p no:xdist -o addopts=

Feature: 暴露掃描量不到

Scenario: 量不到記為 NE 而不是通過；範圍外的字串不計
  Given `R` 與 `P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=count, mutation=True))`、合成逐字稿目錄依 §5.3 的 TRANSCRIPT-DIR 建法；情境：(a) `CLAUDE_CONFIG_DIR` 指向不存在的目錄；(b) `projects/<slug>/` 目錄不存在（`CLAUDE_CONFIG_DIR` 存在但其下無 `projects`）；(c) `subagents/agent-1.jsonl` 內有一行非 JSON 的壞行與一行 JSON 但為陣列，其餘為良性記錄；(d) 凍結目錄的絕對路徑只出現在子代理 `tool_result` 區塊的內文與 `user` 記錄；(e) 凍結目錄絕對路徑只出現在**主控**逐字稿（頂層 `<sid>.jsonl`）的 `tool_use`
  When 各呼叫 `MJ(R, verify, P)`
  Then (a)(b) `verdict` 為 `NE`、`reasons` 為 `[EXPOSURE-UNKNOWN]`、rc 為 `0`、三步照常執行；(c)(d)(e) `verdict` 為 `PASS`（壞行被略過、範圍外字串不計；主控本就持有 held-out 路徑與 `params.json`，其逐字稿不掃）
  And (a)(b) 的 stdout 末尾有 `obs-draft:` 與恰一行草稿列，症狀含 `EXPOSURE-UNKNOWN`；`MJ(check)` 的 `events.verdict` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_4_E_2]"
```

```gherkin
# AT-221-1-1
# 對應 AC: AC-221-1（PRD AC-SI-21-1；R87 (d)、R90 (a)(c)）證據入帳正控：每筆 `rec` 含指令、rc、輸出摘錄座標、母體數；`out_sha256` 與 `out_bytes` 可獨立重算；`tail` 不超過 300 位元組且不切半個字元；原始輸出全文不落任何檔
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_221_1_1_ -q -p no:xdist -o addopts=

Feature: 證據逐字入帳

Scenario: 摘要欄位與獨立重算相符，原文不入任何檔
  Given `R`、`P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=noisy, mutation=True))`（探針 `probe_noisy.py`：先在 stdout 印一行 `MIDDLE-MARKER-<執行期亂數>` 與 1,500 個位元組的填充，再於 stderr 印一行，最後在 stdout 印一段 400 個位元組的中文字串使 300 位元組的截斷點落在多位元組字元之中；症狀有無仍以 `FIXED-LINE` 決定 rc）
  When 呼叫 `MJ(R, verify, P, --by, VF1)`；測試以 `subprocess.run` 在相同沙盒、相同環境下自行執行同一探針三步，取得原始 stdout 與 stderr 位元組（合併序：stdout 在前）
  Then 每步每筆 `rec` 的 `out_sha256` 等於測試自算的合併位元組 `sha256:`、`out_bytes` 等於其完整長度、`rc` 等於測試取得的 rc、`n_pop` 等於 manifest 宣告值、`id` 等於探針 `id`；`tail` 的 UTF-8 位元組數小於等於 `300`、能無損解碼（不含 U+FFFD）、且是合併輸出（遮蔽後）的後綴
  And 事件的 `by` 為 `VF1`、`t` 帶 offset 且秒精度；`verify1.json` 與事件之外，repo 工作樹與 `HOME` 內沒有任何檔含字面 `MIDDLE-MARKER-` 之後的亂數（`tail` 之外的輸出不落地）；`git grep` 與逐檔掃描皆為零命中
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_221_1_1]"
```

```gherkin
# AT-221-1-E-1
# 對應 AC: AC-221-1（PRD AC-SI-21-1；R87 (b)(d)；NFR-P2-12）機密與環境的負控：遮蔽四型、環境白名單（不繼承 `AUTOSDD_*`、金鑰環與上層 `PYTHONPATH`）、輸出極大時摘要仍有界、CLI 輸出不含金鑰子字串
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_221_1_E_1_ -q -p no:xdist -o addopts=

Feature: 證據的機密與環境衛生

Scenario: 探針看不到機密，輸出裡的機密被遮蔽，摘要有界
  Given 父行程環境：`AUTOSDD_SI_AUDIT_KEY` 為執行期組出的 40 字元金鑰、`AUTOSDD_X_TEST` 為 `1`、`MY_SECRET_TOKEN` 為 `abc123secret`、`PYTHONPATH` 為 `decoy/`；三個獨立複本，其 held-out 探針依序為：(a) `probe_env.py`（印出 `PYTHONPATH`、以逗號列出所有 `AUTOSDD_` 起頭的環境變數名、`MY_SECRET_TOKEN` 是否存在、`PYTHONUTF8`、`PYTHONDONTWRITEBYTECODE` 的值）；(b) `probe_secrets.py`（在輸出末段依序印 `Authorization: Bearer abcdef0123456789abcdef`、`key=` 接 SK-KEY（openai 形態金鑰：由 `sk`、連字號與 22 字元後綴 `ABCDEF0123456789abcdef` 於執行期相加組出；本檔不寫連續字面，避免被機密掃描擋下 commit，§5.5）、`Authorization: Basic dXNlcjpwYXNzd29yZA==`、`postgres://admin:s3cr3tpw@db.example/x`）；(c) `probe_big.py`（只向 stdout 寫恰 2,000,000 位元組、不寫 stderr，rc 仍依症狀有無）
  When 各呼叫 `MJ(R, verify, P)`
  Then (a) 輸出 `tail` 顯示：`PYTHONPATH` 恰為沙盒根（單一元素、不含 `decoy/`）、`AUTOSDD_` 名單為空、`MY_SECRET_TOKEN` 不存在、`PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`；(b) `tail` 內四型各被換成 `[REDACTED]`，且 `abcdef0123456789abcdef`、SK-KEY、`dXNlcjpwYXNzd29yZA==`、`s3cr3tpw` 四個字串皆不出現在 `tail`、事件、`verify1.json`、stdout、stderr 的任何位置，而 `out_sha256` 仍等於**未遮蔽**原始位元組的雜湊（遮蔽只作用於 `tail`）；(c) 每步每筆 `rec` 的 `out_bytes` 為 `2000000`、`tail` 仍小於等於 300 位元組、`verify1.json` 小於 8 KB
  And 三次呼叫的 stdout、stderr、事件、驗證檔與 OBS 草稿列都不含父行程金鑰的任何 8 字元子字串（滑動視窗逐一檢查）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_221_1_E_1]"
```

```gherkin
# AT-221-1-E-2
# 對應 AC: AC-221-1（PRD AC-SI-21-1；R90 (a)；PRD §9.7 #75）驗證檔完整性的負控：`verify<K>.json` 被改一個字元、被刪、被多加一個換行，或事件的 `verify_sha256` 被手改，`check` 的 `events.prop_files` 各回對應碼；未動時為綠；無探針的驗證不產生驗證檔、也不被要求有
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_verify.py -k AT_221_1_E_2_ -q -p no:xdist -o addopts=

Feature: 驗證檔完整性

Scenario: 事件只存雜湊，驗證檔或雜湊的任何變動都被 check 抓到
  Given `R` 與 `P＝drive_to(R, sandboxed, heldout=make_heldout(dir, cases=5, probes=count, mutation=True))`；呼叫 `MJ(R, verify, P)` 一次，得 `verify1.json` 與一筆 `app.verify` 事件（其 `seq` 記為 `s`）；自 `R` 複製四份（`shutil.copytree`，含 `.git`）`C1`～`C4`；另備 `R0` 與 `P0＝drive_to(R0, sandboxed, heldout=make_heldout(dir, cases=5, probes=none))`，對它呼叫 `MJ(R0, verify, P0)` 一次（`probes` 為空陣列，不產生驗證檔）
  When 依序變異並各呼叫 `MJ(Ck, check)`：`C1` 把 `verify1.json` 內某個 `tail` 字元換成另一個同位元組長度的字元；`C2` 刪除 `verify1.json`；`C3` 在 `verify1.json` 末尾多加一個換行；`C4` 不動驗證檔，以 `rewrite_event(C4, s, verify_sha256=<另一個合法形態的 sha256 值>)` 改掉事件的雜湊；另對未變異的 `R` 與對 `R0` 各呼叫 `MJ(check)` 一次
  Then 未變異的 `R` 的 `events.prop_files` 為 `PASS`；`C1`、`C3`、`C4` 的 `events.prop_files` 為 `FAIL`，`F(events.prop_files)` 含 `(<P> verify1, PROP-VERIFY-SHA-MISMATCH)`；`C2` 為 `FAIL`，`F(events.prop_files)` 含 `(<P> verify1, PROP-FILE-MISSING)`；四份變異複本 `check` 的 rc 皆為 `1`
  And `R0` 的 `events.prop_files` 與 `events.verdict` 皆為 `PASS`（無探針的驗證沒有驗證檔、也不被要求有）；四份變異複本的 `events.verdict` 與 `events.transitions` 不因驗證檔或雜湊的變動而變紅（`C4` 的 `events.verdict` 仍為 `PASS`，因它只比對記錄欄位與重算值，不讀雜湊）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_221_1_E_2]"
```


**E. 晉升、回滾、SUSPENDED 與可進化面重驗（PM）**

```gherkin
# AT-216-1-1
# 對應 AC: AC-216-1（PRD AC-SI-16-1；R69、R91、R75）晉升正控：PASS 配前式、NE 配「未驗採納」後式；patch 合入正式面工作樹、不 commit、HEAD 與 `git log` 與暫存區不變、PROP 態為 `promoted`
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_1_1_ -q -p no:xdist -o addopts=

Feature: promote 正控

Scenario: 兩種式各晉升一個 PROP，只動 touched 路徑且不 commit
  Given `R`；`PA＝drive_to(R, verified)`（D 類、`verify` 得 `PASS`；`dec(approve)` 經真逐字稿受理）；`PN＝drive_to(R, verified, target=docs/notes/other.md, heldout=make_heldout(dir, probes=none))`（`verify` 得 `NE`、`reasons` 為 `[NO-PROBES]`；目標檔不同於 `PA`，兩個 patch 不互相衝突）；`head0＝git rev-parse HEAD`、`log0＝git rev-list --count HEAD`、`st0＝git status --porcelain`、`snap0＝snap(R)`
  When 以 `decide_say(R, PA, 「晉升 <PA>」)`（`decide_say` 先 `card --issue`、把卡面核心區放進 assistant 訊息、再放 human 的決定記錄，最後呼叫 `decide`，§5.2）取得 `dec(promote)`；呼叫 `M(R, promote, PA, --by, PR1)`；再對 `PN` 做 `decide_say(R, PN, 「晉升 <PN> 未驗採納」)` 與 `M(R, promote, PN, --by, PR1)`
  Then 兩個 `decide_say` 與兩個 `promote` 的 rc 皆為 `0`；`PA` 的 `promote` stdout 單行 `ok app.promote seq=<n> id=APP-SI-<NNN> prop=<PA> unverified_ack=false head_sha=<40 位 hex>`，`PN` 的為 `unverified_ack=true`；事件鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`prop`、`rev`、`head_sha`、`pre_sha256`、`post_sha256`、`unverified_ack`，`by` 為 `PR1`
  And 正式面：`HEAD` 等於 `head0`、`git rev-list --count HEAD` 等於 `log0`（未 commit）；`git diff --cached` 為空（未暫存）；`git status --porcelain` 相對 `st0` 恰多 touched 路徑對應的修改行（`PA` 與 `PN` 的 patch 各改 `docs/notes/demo.md` 與 `docs/notes/other.md`，故多兩行 ` M`），其餘不變；`docs/notes/demo.md` 含 `FIXED-LINE`；`snap(R)` 相對 `snap0` 的變動檔案恰為 touched 路徑加事件帳本
  And `MJ(R, status)` 兩個 PROP 皆為 `promoted`；`MJ(R, check)` 的 `events.transitions`、`events.dec_quote`、`events.verdict`、`events.prop_files` 皆為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_1_1]"
```

```gherkin
# AT-216-1-E-1
# 對應 AC: AC-216-1（PRD AC-SI-16-1；R91、R70）`promote` 的前置負控：態、無決定、式與 verdict 不符（含 FAIL）、digest 被改、無人值守、不存在、M 類記憶目錄與前像、主工作樹已漂移、用法；全部零變更
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_1_E_1_ -q -p no:xdist -o addopts=

Feature: promote 前置負控

Scenario: 每個前置不符 rc 1 或 rc 3、碼與表一致、正式面與帳本逐位元不變
  Given §5.4 的 PRM-PRE 表（每列＝一份獨立複本、預期 rc 與碼；`forge_dec(R, P, 引言, flags)` 手寫追加一筆引言可回查、欄位合法的 `dec`，略過 `decide` 的狀態層前提，§5.2）：(a) `approved` 態；(b) `sandboxed` 態；(c) `verified` 且 PASS 而沒有任何 `dec(promote)`；(d) PASS 的 `verified`，以 `forge_dec` 追加後式 `晉升 <P> 未驗採納`；(e) NE 的 `verified`，追加前式 `晉升 <P>`；(f) FAIL 的 `verified`（以 `PATCHED-NOT-GREEN` 達成），追加前式 `晉升 <P>`；(g) PASS 的 `verified` 並 `decide_say` 前式受理之後，把 `SelfImproving_Proposals/<P>/r1.patch` 改一個位元組；(h) `AUTOSDD_UNATTENDED` 設為 `1`（其餘條件皆成立）；(i) 不存在的 PROP 號（執行期組出）；(j) M 類 PROP 未給 `--memory-dir`；(k) M 類 PROP 給了記憶目錄、但其目標檔已被改得與 patch 前像不符；(l) D 類 PROP 經 `decide_say` 受理後，主工作樹的 `docs/notes/demo.md` 被另行修改（patch 不再套得上）；rc 3 組：(m) 缺位置參數；(n) 未知旗標 `--force`；(o) 未知旗標 `--commit`
  When 各呼叫 `M(R, promote, …)`；每個情境前記 `snap0＝snap(R)`、`ev0＝事件帳本位元組`、`mem0＝記憶目錄各檔位元組雜湊`
  Then 依序 rc 與碼為：(a)(b) rc 1、`STATE-NOT-VERIFIED`；(c) rc 1、`NO-PROMOTE-DEC`；(d)(e)(f) rc 1、`PROMOTE-FORM-MISMATCH`（`FAIL` 一律不收；R91 以事件掃描判式，不依重放合法與否）；(g) rc 1、`DIGEST-MISMATCH`；(h) rc 1、`UNATTENDED-REFUSED`（先於其餘判）；(i) rc 1、`PROP-NOT-FOUND`；(j) rc 1、`MEMORY-DIR-MISSING`；(k) rc 1、`PREIMAGE-MISMATCH`（stdout 含可貼入的 OBS 草稿列，並要求重新上卡）；(l) rc 1、`APPLY-FAILED`；(m)(n)(o) rc 3、stdout 空、stderr 以 `selfimproving:` 起頭
  And 全部情境：`snap(R)` 等於 `snap0`（主工作樹無任何變更、無 `.orig`／`.rej` 檔、`HEAD` 不變）、事件帳本位元組等於 `ev0`、記憶目錄位元組等於 `mem0`；rc 1 的呼叫 stdout 依序為 `reject promote …`、碼行、`obs-draft:`、恰一行草稿列且 `draft_ok` 成立
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_1_E_1]"
```

```gherkin
# AT-216-1-E-2
# 對應 AC: AC-216-1（PRD AC-SI-16-1；R91、R79、R95）DEC 回查 fail-closed：對 `approve` 與 `promote` 兩筆 DEC 以同一函式回查；逐字稿取不到、引言不符、出處非真人、卡面未送達、Console 稽核檔缺或金鑰缺，一律拒絕、不降為通過
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_1_E_2_ -q -p no:xdist -o addopts=

Feature: promote 的 DEC 回查

Scenario: 任何一筆 DEC 回查不過，`promote` 都不動主工作樹
  Given PASS 的 `P＝drive_to(R, verified)` 且 `dec(promote)` 已經 `decide_say` 受理（兩筆 DEC 的逐字稿在 `CLAUDE_CONFIG_DIR` 內）；八個獨立複本情境：(a) 刪除 `approve` 那份逐字稿檔；(b) 刪除 `promote` 那份逐字稿檔；(c) `CLAUDE_CONFIG_DIR` 指向空目錄（他機）；(d) `approve` 的逐字稿被改寫：human 決定記錄的 `origin.kind` 改為 `sdk`；(e) `promote` 的逐字稿被改寫：卡面核心區那則 assistant 文字改掉一個字；(f) `promote` 那筆 `dec` 的 `quote` 被 `rewrite_event` 改成與逐字稿該行不同；(g) 以 Console 載體重做：`approve` 與 `promote` 皆經 `decide --carrier console`（稽核檔與金鑰環就位），再刪除 `promote` 的稽核檔；(h) 同 (g) 但清掉 `AUTOSDD_SI_AUDIT_KEY`；`snap0＝snap(R)`
  When 各呼叫 `M(R, promote, P)`
  Then (a)(b)(c) rc 1、碼 `TRANSCRIPT-UNAVAILABLE`（逐字稿檔或目錄取不到 ⇒ 拒絕，不是略過；晉升須在持有該逐字稿的機器上進行）；(d) rc 1、碼 `DEC-VERIFY-FAILED`（detail 含 `NOT-HUMAN-UTTERANCE`）；(e) rc 1、碼 `DEC-VERIFY-FAILED`（detail 含 `CARD-NOT-DELIVERED`）；(f) rc 1、碼 `DEC-VERIFY-FAILED`（detail 含 `QUOTE-MISMATCH`）；(g) rc 1、碼 `CONSOLE-AUDIT-MISSING`；(h) rc 1、碼 `CONSOLE-KEY-MISSING`
  And 全部情境 `snap(R)` 等於 `snap0`、事件帳本位元組不變；對照組：還原各情境的破壞（逐字稿、稽核檔與金鑰就位）後同一 PROP 的 `promote` rc 為 `0`（證明拒絕來自回查、不是其他前置）
  And `MJ(check)` 於 (b)(c)：`events.dec_quote` 為 `NE`、nonblocking、`TRANSCRIPT-UNAVAILABLE`（`check` 量不到不判紅，而 `promote` 量不到就不晉升——兩者語意不同、各自釘住）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_1_E_2]"
```

```gherkin
# AT-216-2-1
# 對應 AC: AC-216-2（PRD AC-SI-16-2；R85 (e)(f)、R80 (e)、R91）回滾配方乾跑通過才可晉升：`rollback_ok` 與 `touched_ok` 皆 `true` 時 `decide --kind promote` 受理、`promote` 再驗通過；乾跑結果可由獨立實作重算
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_2_1_ -q -p no:xdist -o addopts=

Feature: 回滾乾跑為晉升前提

Scenario: 乾跑通過的 PROP 可晉升，且「正向再反向等於 base」由獨立實作重算相同
  Given `R`；D 類 `PD＝drive_to(R, verified)`、M 類 `PM＝drive_to(R, verified, cls=M, memory=memdir)`（兩者 `app.sandbox` 的 `rollback_ok` 與 `touched_ok` 皆為 `true`）；測試自寫的獨立乾跑：在全新目錄 `git archive <base>` 抽出、`git -c core.autocrlf=false apply <rN.patch>`、再 `apply -R`，比對樹 manifest 與 base 副本
  When 對 `PD`、`PM` 各 `decide_say(…, 「晉升 <PROP>」)` 與 `M(R, promote, <PROP>[, --memory-dir, memdir])`
  Then 獨立乾跑的結果為`與 base 逐位元相同`，與兩個 PROP 的 `rollback_ok` 為 `true` 一致；`decide` 與 `promote` 的 rc 皆為 `0`；晉升前提取自最近一筆 `app.sandbox`（`MJ(status)` 與 `fold` 的 `Prop.rollback_ok`、`Prop.touched_ok` 皆為 `true`）
  And 兩個 PROP 態為 `promoted`；`PM` 只改 `memdir` 內被 touched 的記憶檔、其餘記憶檔位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_2_1]"
```

```gherkin
# AT-216-2-E-1
# 對應 AC: AC-216-2（PRD AC-SI-16-2；R80 (e)、R91）乾跑未通過或 touched 超集時晉升前提不成立：記 DEC 時就擋，繞過 `decide` 的手寫 DEC 也被 `promote` 在寫主工作樹前再驗一次擋下
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_2_E_1_ -q -p no:xdist -o addopts=

Feature: 晉升前提負控

Scenario: 前提在兩個站點各被擋一次
  Given 三份獨立複本，`P＝drive_to(R, verified)`（PASS）後以 `rewrite_event` 改 `app.sandbox` 事件：(a) `rollback_ok` 為 `false`；(b) `touched_ok` 為 `false`；(c) 兩者皆 `false`；另三份複本 (a2)(b2)(c2)：先以 `decide_say` 受理 `dec(promote)`（前提當時成立），**之後**才做同樣的 `rewrite_event` 改動（模擬記 DEC 之後前提被破壞，或手寫 DEC 繞過）；每個情境 `snap0＝snap(R)`
  When (a)(b)(c) 各呼叫 `decide_say(R, P, 「晉升 <P>」)`；(a2)(b2)(c2) 各呼叫 `M(R, promote, P)`
  Then (a) rc 為 `1`、碼 `PROMOTE-PREMISE-ROLLBACK`；(b) rc 為 `1`、碼 `PROMOTE-PREMISE-TOUCHED`；(c) rc 為 `1`、碼恰為這兩碼的集合；(a2)(b2)(c2) rc 為 `1`、碼依序同 (a)(b)(c)；全部零 DEC（(a)(b)(c)）、零 `app.promote`（(a2)(b2)(c2)）
  And `snap(R)` 於 (a2)(b2)(c2) 等於 `snap0`（主工作樹未被寫）；`MJ(check)` 對被 `rewrite_event` 改動的帳本：`events.verdict` 為 `FAIL`、碼 `VERDICT-MISMATCH`（verdict 為 PASS 而沙盒欄位已使 ⓪ 成立，重算與記錄不符）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_2_E_1]"
```

```gherkin
# AT-216-3-1
# 對應 AC: AC-216-3（PRD AC-SI-16-3；R91、R84）晉升記錄的內容：晉升者、時間帶 offset、`head_sha`、前後 manifest 快照座標可由獨立實作重算；沒有 `commit_sha`；新增檔的 `absent` 語意
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_3_1_ -q -p no:xdist -o addopts=

Feature: 晉升記錄內容

Scenario: 事件的雜湊與座標逐欄等於獨立重算
  Given `R`；`PD＝drive_to(R, verified)`（改既有檔 `docs/notes/demo.md`）；`PA＝drive_to(R, verified, action=add)`（patch 新增檔 `docs/notes/new_note.md`，原本不存在）；測試自寫的 `manifest_lf(root, paths)`（R84 的 LF 正規化式：每檔 CRLF 換 LF 後取 `sha256`、缺檔記 `absent`、依路徑 UTF-8 位元組序、整體取 `sha256:`）；`pre＝manifest_lf(R, touched)` 於 `promote` 之前
  When 兩個 PROP 各 `decide_say` 前式晉升與 `M(R, promote, <PROP>, --by, PR1)`；其後 `post＝manifest_lf(R, touched)`
  Then 事件 `pre_sha256` 等於 `pre`、`post_sha256` 等於 `post`（`PD`、`PA` 各自成立；`PA` 的 `pre` 內該路徑為 `absent`）；`head_sha` 等於 `git rev-parse HEAD`；`by` 為 `PR1`；`t` 帶 offset、秒精度；事件沒有 `commit_sha` 鍵
  And `dec(promote)` 的 `decider` 為字串`掌舵者`、`decided_at` 帶 offset 且等於被引記錄的 `timestamp` 的同一時刻、`digest` 等於 PROP 事件的 `digest`
  And 單元：以 `manifest.paths_manifest` 對同一檔的 LF 版與 CRLF 版內容（寫在 tmp 內兩個目錄、同相對路徑）各算一次，值相同；`absent` 與空檔的值不同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_3_1]"
```

```gherkin
# AT-216-3-E-1
# 對應 AC: AC-216-3（PRD AC-SI-16-3；R72、R91）晉升與回滾不 commit：事件沒有 `commit_sha`、`head_sha` 形態受檢；`HEAD`、`git log`、暫存區皆不變
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_216_3_E_1_ -q -p no:xdist -o addopts=

Feature: 晉升不 commit

Scenario: 帶 commit_sha 的事件不合規，真實晉升與回滾不留任何 commit 或暫存
  Given 手寫事件：`app.promote` 多一個 `commit_sha` 鍵；`app.promote` 的 `head_sha` 為 7 位 hex；`app.rollback` 多 `commit_sha`；`app.promote` 缺 `post_sha256`；`R` 與 `P＝drive_to(R, promoted, via=cli)`、其後再 `decide_say` 回滾與 `M(R, rollback, P)`；`head0＝git rev-parse HEAD`、`log0＝git rev-list --count HEAD`（皆於晉升前取）
  When 對手寫事件各呼叫 `events.validate`；對真實流程取 `git rev-parse HEAD`、`git rev-list --count HEAD`、`git diff --cached`、`git stash list`、`.git/index.lock` 是否存在
  Then 四個手寫事件依序回 `EVENT-KEY-UNKNOWN`、`EVENT-TYPE`、`EVENT-KEY-UNKNOWN`、`EVENT-KEY-MISSING`；真實流程中 `HEAD` 等於 `head0`、`rev-list --count` 等於 `log0`、`git diff --cached` 為空、`git stash list` 為空、`.git/index.lock` 不存在（`promote` 與 `rollback` 都只改工作樹，commit 由主控走一般流程）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_216_3_E_1]"
```

```gherkin
# AT-240-7-1
# 對應 AC: AC-240-7（本檔自增；PRD §9.3 `rollback` 列；R92）回滾正控：`touched` 路徑現況等於晉升後 manifest 時，反向套用逐位元還原為晉升前、記 `app.rollback`、PROP 態不變、不 commit
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_240_7_1_ -q -p no:xdist -o addopts=

Feature: rollback 正控

Scenario: 晉升後回滾，樹還原到晉升前
  Given `R`；`PD＝drive_to(R, promoted)`（改既有檔）、`PA＝drive_to(R, promoted, action=add)`（新增檔）、`PM＝drive_to(R, promoted, cls=M, memory=memdir)`（M 類）；每個 PROP 晉升前的 `pre＝manifest_lf(…)`；`head0＝HEAD`、`log0`；對每個 PROP 以 `decide_say(…, 「回滾 <PROP> 太慢」)` 取得 `dec(rollback)`
  When 各呼叫 `M(R, rollback, <PROP>[, --memory-dir, memdir], --by, RB1)`
  Then rc 皆為 `0`；stdout 單行 `ok app.rollback seq=<n> id=APP-SI-<NNN> prop=<PROP>`；事件鍵集合恰為 `seq`、`t`、`kind`、`by`、`id`、`prop`、`rev`、`pre_sha256`、`post_sha256`；`pre_sha256` 等於該 PROP 最近一筆 `app.promote` 的 `post_sha256`、`post_sha256` 等於其 `pre_sha256`、也等於測試於晉升前取的 `pre`
  And 樹：`PD` 的 `docs/notes/demo.md` 回到晉升前位元組、`PA` 的新增檔被移除、`PM` 的記憶檔回到晉升前位元組；`HEAD` 等於 `head0`、`git rev-list --count HEAD` 等於 `log0`；PROP 態仍為 `promoted`（回滾不改態）；`MJ(check)` 的 `events.transitions` 為 `PASS`（`ROLLBACK-MANIFEST-MISMATCH` 不成立）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_7_1]"
```

```gherkin
# AT-240-7-E-1
# 對應 AC: AC-240-7（本檔自增；R92、R70）回滾負控：態不是已晉升、無回滾決定、DEC 回查失敗、晉升後樹被他處改動、反向結果不等於晉升前、記憶目錄缺；全部零變更
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_240_7_E_1_ -q -p no:xdist -o addopts=

Feature: rollback 負控

Scenario: 每個前置或結果不符都 rc 1、碼與表一致、樹不變
  Given §5.4 的 RBK-PRE 表（每列＝一份獨立複本）：(a) `verified` 態（未晉升）；(b) `promoted` 而沒有任何 `dec(rollback)`；(c) 已有 `dec(rollback)` 而其逐字稿被刪（取不到）；(d) 已有 `dec(rollback)` 而 `CLAUDE_CONFIG_DIR` 指向空目錄；(e) 晉升後 `touched` 路徑被他處再改一行；(f) 以 `rewrite_event` 把最近一筆 `app.promote` 的 `pre_sha256` 改為另一個合法雜湊（使反向套用的結果不等於它）；(g) M 類 PROP 未給 `--memory-dir`；(h) `AUTOSDD_UNATTENDED` 設為 `1`；(i) 不存在的 PROP；rc 3：(j) 未知旗標 `--commit`；每列前記 `snap0＝snap(R)`、`ev0`、`mem0`
  When 各呼叫 `M(R, rollback, …)`
  Then 依序 rc 與碼：(a) rc 1、`STATE-NOT-PROMOTED`；(b) `NO-ROLLBACK-DEC`；(c) `TRANSCRIPT-UNAVAILABLE`；(d) `TRANSCRIPT-UNAVAILABLE`；(e) `TREE-CHANGED`（現況 manifest 不等於 `post_sha256`）；(f) `ROLLBACK-NOT-EXACT`（剛套用的反向 patch 被還原回去，樹仍為晉升後）；(g) `MEMORY-DIR-MISSING`；(h) `UNATTENDED-REFUSED`；(i) `PROP-NOT-FOUND`；(j) rc 3、stdout 空
  And 全部情境 `snap(R)` 等於 `snap0`（(f) 亦然：零變更）、事件帳本位元組等於 `ev0`、記憶目錄位元組等於 `mem0`；rc 1 的呼叫其 stdout 依序為 `reject rollback …`、碼行、`obs-draft:`、恰一行草稿列
  And 對照組：(e) 把多改的一行還原後同一呼叫 rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_7_E_1]"
```

```gherkin
# AT-217-2-1
# 對應 AC: AC-217-2（PRD AC-SI-17-2；R93、R80 (e)）SUSPENDED 與恢復正控：只有掌舵者的 `dec(resume)`（綁折疊出的運轉）能恢復；SUSPENDED 期間 `prop-new` 與 `prop-revise` 拒收、恢復後受理；本迴圈不碰 FSM
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_217_2_1_ -q -p no:xdist -o addopts=

Feature: SUSPENDED 與 resume

Scenario: 兩個連續壞窗使迴圈 SUSPENDED，`dec(resume)` 恢復
  Given §5.2 的 SC-SUSP-RESUME：`R`＝以 P1 夾具情境 `sc_susp()`（兩個已晉升 PROP 的度量窗依序為 `recurred`、`rolled-back`；運轉 1 已關閉、運轉 2 與 3 已開、運轉 3 有研究事件）寫成的帳本，`MJ(R, status)` 的 `suspended` 為運轉 1；§5.3 的 PC-03 逐字稿（只含 human 的決定記錄 `恢復 <運轉 1> 兩個壞窗已人工檢視`，無卡面——`resume` 不驗卡面送達）
  When 先對運轉 3 呼叫 `prop-new`（沿 P1 夾具 `good_prop_args`）；再呼叫 `decide <運轉 1> --kind resume --sid … --line …`；再呼叫 `prop-new`
  Then 第一次 `prop-new` rc 為 `1`、碼 `SUSPENDED`；`decide` rc 為 `0`、stdout 單行 `ok dec seq=<n> id=DEC-SI-<NNN> run=<運轉 1> dkind=resume`（無 `digest8`）、事件 `dec` 無 `prop`、有 `run`、`reason` 為`兩個壞窗已人工檢視`、無 `digest` 與 `card_seq`、`decider` 為字串`掌舵者`；第二次 `prop-new` rc 為 `0`；`MJ(R, status)` 的 `suspended` 為 `null`
  And `prop-revise` 於 SUSPENDED 期間同樣 rc 為 `1`、碼 `SUSPENDED`（以另一份複本、`returned` 的 PROP 驗證）；恢復後同一呼叫 rc 為 `0`
  And 靜態掃描：`tools/lib/selfimproving/*.py` 全部原始碼不含字面 `FSM-STATE`、`fsm_runtime`、`resume-from-escalation`（本迴圈不讀寫 FSM 狀態檔、不恢復任何 FSM 鍵）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_217_2_1]"
```

```gherkin
# AT-217-2-E-1
# 對應 AC: AC-217-2（PRD AC-SI-17-2；R93、R80 (e)、R70）沒有任何其他路徑恢復 SUSPENDED：其他寫入動詞不解除、RUN 不符與未 SUSPENDED 被拒、舊回覆重播被拒、無人值守與引言文法負控
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_217_2_E_1_ -q -p no:xdist -o addopts=

Feature: resume 負控

Scenario: 只有綁對運轉、有理由、有真人引言的 resume 才解除
  Given §5.2 的 SC-SUSP-RESUME（以 P1 夾具情境 `sc_susp()` 寫成的 SUSPENDED 帳本 `R`，`suspended` 為運轉 1）與 §5.3 的 PC-03 逐字稿；`snap0＝snap(R)`
  When (a) 依序執行 P1 的寫入動詞 `run-open`（新運轉）與 `research --skip`（對該新運轉）；(b) `decide <運轉 2> --kind resume`（引言 `恢復 <運轉 2> 理由`，RUN 不是折疊出的 SUSPENDED 所在運轉）；(c) 引言 `恢復 <運轉 1>`（缺理由）；(d) `AUTOSDD_UNATTENDED` 設為 `1` 後呼叫合法的 `decide`；(e) 合法 `decide` 一次成功之後，以**同一份逐字稿與行號**再呼叫一次；(f) 在未 SUSPENDED 的另一份帳本呼叫合法引言的 `decide`
  Then (a) 兩個動詞 rc 皆為 `0`（R93：SUSPENDED 只擋 `prop-new` 與 `prop-revise`），但事件帳本的新事件不含任何 `dec(resume)`、`MJ(status)` 的 `suspended` 仍為運轉 1；(b) rc 為 `1`、碼 `RUN-MISMATCH`；(c) rc 為 `1`、碼 `GRAMMAR-REASON-MISSING`；(d) rc 為 `1`、碼 `UNATTENDED-REFUSED`、零寫入；(e) 第二次 rc 為 `1`、碼 `NOT-SUSPENDED`（舊回覆重播不改任何狀態）；(f) rc 為 `1`、碼 `NOT-SUSPENDED`
  And (b)(c)(d)(f) 的事件帳本位元組不變；(b) 之後 `MJ(status)` 的 `suspended` 仍為運轉 1；(e) 的第一次成功之後 `suspended` 為 `null`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_217_2_E_1]"
```

```gherkin
# AT-220-3-1
# 對應 AC: AC-220-3（PRD AC-SI-20-3；P1 R52、R91）合法 PROP 的晉升重驗通過：以當下參數與當下 LATEST 重新解析 patch 全部路徑，未命中不可進化面時放行
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_220_3_1_ -q -p no:xdist -o addopts=

Feature: NON-EVOLVABLE-NOW 正控

Scenario: 路徑合法且參數與 LATEST 未變時，晉升放行
  Given `R`；`PD＝drive_to(R, verified)`（D 類、`docs/notes/demo.md`）；`PL＝drive_to(R, verified, action=add, target=<LATEST 版目錄>/agent/x.md)`（沿 P1 夾具 `VNEW`：LATEST 版目錄，`AISDLC_SDD/scripts/sdd_version.py` 在場、解析得出）；兩者皆已 `decide_say` 受理前式 `晉升`
  When 各呼叫 `M(R, promote, <PROP>)`
  Then 兩者 rc 皆為 `0`、`app.promote` 各一筆；`PL` 的新增檔存在於 LATEST 版目錄之下
  And 同一組參數下，另一個以 `docs/06_quality/SelfImproving_Protocol/params.json` 為目標的 PROP（P1 判為 `evaluator-change`、route 為 `handoff:T1`）於 `decide approve` 被拒：rc 為 `1`、碼 `ROUTE-HANDOFF`（不進採納流程；只能 `ack-handoff`，由掌舵者經 T1 處理）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_3_1]"
```

```gherkin
# AT-220-3-E-1
# 對應 AC: AC-220-3（PRD AC-SI-20-3；R91 `NON-EVOLVABLE-NOW`、P1 R52）可進化面在核准之後縮小：當下重驗命中即拒絕並改走轉交、不寫事件、不動主工作樹
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_promote.py -k AT_220_3_E_1_ -q -p no:xdist -o addopts=

Feature: NON-EVOLVABLE-NOW 負控

Scenario: 核准之後不可進化面擴大或 LATEST 失效，晉升被當下重驗擋下
  Given 四份獨立複本，各有已 `decide_say` 受理前式 `晉升` 的 PASS 的 PROP：(a) D 類，其後把 `docs/notes/demo.md` 加進 `params.json` 的 `non_evolvable_globs`；(b) D 類，其後把 `docs/notes/*.md` 加進 `non_evolvable_globs`（glob 形態）；(c) 目標為 LATEST 版目錄之下檔案的 PROP，其後刪除 `AISDLC_SDD/scripts/sdd_version.py`（LATEST 解析失敗 ⇒ 整個 `AISDLC_SDD_v*/**` 視為凍結）；(d) 目標為 LATEST 版目錄之下檔案的 PROP，其後建立一個更新的版目錄使 LATEST 移動（原版目錄變成歷史版）；每份 `snap0＝snap(R)`、`ev0`
  When 各呼叫 `M(R, promote, P)`
  Then 四個 rc 皆為 `1`、碼含 `NON-EVOLVABLE-NOW`（detail 點名命中的路徑與 glob）；不寫事件（事件帳本位元組等於 `ev0`）、`snap(R)` 等於 `snap0`（主工作樹未動）
  And 對照：各情境還原（移除新增的 glob、還原 `sdd_version.py`、移除新版目錄）後 `promote` rc 為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_220_3_E_1]"
```


**F. Console 載體的根層半：`decide --carrier console`、`obs-add`、`obs-close`、`check`／`status`／`export` 擴充（CN）**

```gherkin
# AT-233-1-1
# 對應 AC: AC-233-1（PRD AC-SI-33-1 的根層半；R94、R95）`decide --carrier console` 九個動詞（晉升兩式）正控：稽核檔經 HMAC 驗證、與逐字稿載體同一組前提，`dec` 帶 `carrier=console` 與稽核座標；不要求卡面送達
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_1_1_ -q -p no:xdist -o addopts=

Feature: decide 的 Console 載體正控

Scenario: 十個合法決定各受理一筆，欄位逐一等於稽核檔
  Given 十份獨立複本 `R1`～`R10`，各備一個決定的前提態（以 `write_events` 與 `drive_to(…, via=events)`；取 §5.2 的 DEC-STATES 表的十列：核准、否決、退回、晉升前式、晉升後式、不晉升、轉交、解除、回滾、恢復）；環境 `AUTOSDD_SI_AUDIT_KEY` 為 §5.5 的測試金鑰；每份複本以 `write_audit`（§5.5）寫入 `<HOME>/console_audit/<UUID>.json`，`body` 依 R94（`user` 為 `ops_admin`、`role` 為 `ADMIN`、`time` 為 `2026-10-21T09:15:30+08:00`）；**全程沒有呼叫 `card --issue`、沒有任何逐字稿**；每份複本呼叫前 `status` 的 `console_pending` 的 `count` 為 `1`、其 `items` 為該 `audit_ref` 與 `kind` 為 `decide`
  When 對每份複本呼叫 `M(R, decide, <ID>, --carrier, console, --audit-ref, <UUID>, --by, ops1)`
  Then 十次 rc 皆為 `0`，stdout 單行 `ok dec seq=<n> id=DEC-SI-<NNN> prop=<ID> dkind=<k> digest8=<8 碼>`（`resume` 為 `run=<RUN>` 且無 `digest8`）；事件 `dec` 的 `carrier` 為 `console`、`audit_ref` 等於稽核檔的 UUID、`audit_sha256` 等於該檔位元組的 `sha256:`、`key_id` 等於金鑰位元組之 `sha256` 的前 8 碼、`decider` 為 `ops_admin`、`decided_at` 逐字等於 `2026-10-21T09:15:30+08:00`、`by` 為 `ops1`
  And 每筆 `dec` 沒有 `quote`、`sid`、`line`、`card_seq` 鍵；綁卡面的六個 dkind 有 `digest` 且等於 PROP 事件的 `digest`；`reason`、`reason_class`、`flags` 取自 `body`（後式晉升的 `flags` 為只含 `unverified_ack` 的清單、前式無 `flags`）；`events.validate` 對每筆回空清單
  And 每份複本呼叫後 `MJ(R, check)` 的 `events.dec_console` 與 `events.transitions` 為 `PASS`；`MJ(R, status)` 的 `console_pending` 之 `count` 為 `0`（稽核檔已有對應事件）；CLI 沒有寫入 `<HOME>/console_audit/`（目錄清單與各檔位元組逐一不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_1_1]"
```

```gherkin
# AT-233-1-2
# 對應 AC: AC-233-1（PRD AC-SI-33-1 的根層半；R94；§5.5）跨語言測試向量：以標準庫 `hmac` 加 `hashlib` 重算須與本檔逐字列出的 `body` 字串、`mac`、`key_id` 完全相同，且 `consoleaudit` 對四組向量驗證通過
# 測試類型: Unit
# 自動化工具: pytest（純標準庫）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_1_2_ -q -p no:xdist -o addopts=

Feature: HMAC 測試向量

Scenario: 四組向量逐字相同，`consoleaudit` 驗證通過
  Given §5.5 逐字列出的向量（固定金鑰、`key_id`、四個 `body` 字串、四個預期 `mac`；測試把它們逐字抄為常數，並自行以 `json.dumps` 加 `ensure_ascii=False` 與緊湊分隔符號重建每個 `body`）；`write_audit` 依向量寫出四個稽核檔（`kind` 依序為 `decide`、`decide`、`obs-add`、`obs-close`）
  When 以 `hmac.new(金鑰位元組, body 的 UTF-8 位元組, hashlib.sha256).hexdigest()` 重算四個 `mac`；以 `hashlib.sha256(金鑰位元組).hexdigest()[:8]` 算 `key_id`；對四個稽核檔呼叫 `consoleaudit.verify(path, key_ring)`
  Then 重建的 `body` 字串、重算的 `mac`、`key_id` 皆與 §5.5 逐字相同；`verify` 對四組皆回成功（無碼）；`audit_sha256` 等於各稽核檔位元組的 `sha256:`
  And 向量的 `body` 字串含非 ASCII 字元（中文）而簽章對象為其 UTF-8 位元組（不重新序列化、不做 Unicode 正規化）：把同一 `body` 以 `ensure_ascii=True` 重新序列化後算出的 `mac` 與向量的 `mac` 不同（證明簽章對象是原字串位元組）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_1_2]"
```

```gherkin
# AT-233-1-E-1
# 對應 AC: AC-233-1（PRD AC-SI-33-1 的根層半；R94、R95）稽核檔驗證失敗表：每個違規恰一個碼、rc 1、零寫入、CLI 不寫 `console_audit/`
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_1_E_1_ -q -p no:xdist -o addopts=

Feature: 稽核檔驗證碼

Scenario: 每個稽核檔缺陷被規定的碼擋下，且一次只有一個缺陷
  Given `R` 與 `proposed` 的 PROP `P`；§5.5 的 AUDIT-BAD 表（每列＝一個獨立稽核檔：以 `write_audit` 寫出一份合法的 `decide` 核准稽核檔後只改一處；除 `mac` 列外，`mac` 皆依改後的 `body` 重算，使 HMAC 本身有效）：(a) 檔案不存在；(b) 外層多一個鍵 `x`；外層缺 `mac`；`schema_rev` 為 `2`；`kind` 為數字；`body` 為物件而非字串；(c) 檔名的 UUID 與外層 `audit_ref` 不同；外層與 `body` 的 `audit_ref` 不同；(d) `body` 為字串 `not json`；為 JSON 陣列；為 JSON 字串；(e) 外層 `kind` 為 `decide` 而 `body.kind` 為 `obs-add`；兩者皆為 `purge`（不在三值內）；稽核檔 `kind` 為 `obs-add` 卻被 `decide` 使用；(f) `user` 為 `a;b`、`x=y`、`a b`、`管理者`、`a|b`、空字串、65 個字元；缺 `user`；(g) `role` 為 `USER`、`admin`、空字串；缺 `role`；(h) `time` 為 `2026-10-21T09:15:30Z`、`2026-10-21T09:15:30`、`2026-10-21T09:15:30.5+08:00`、`2026-10-21`、`2026-13-40T25:61:61+08:00`；缺 `time`；(i) 外層 `subject` 與 `body.prop` 不同；位置參數與外層 `subject` 不同；(j) 環境變數 `AUTOSDD_SI_AUDIT_KEY` 未設；為空字串；為只含空白與逗號；(k) 外層 `key_id` 不在金鑰環內；(l) `mac` 翻轉一個 hex 字元
  When 各呼叫 `M(R, decide, P, --carrier, console, --audit-ref, <UUID>)`
  Then 依序 rc 皆為 `1`，碼恰為：(a) `AUDIT-FILE-MISSING`；(b) 五列皆 `AUDIT-SCHEMA`；(c) 兩列皆 `AUDIT-REF-MISMATCH`；(d) 三列皆 `AUDIT-BODY-INVALID`；(e) 三列皆 `AUDIT-KIND-MISMATCH`；(f) 八列皆 `AUDIT-USER-FORMAT`；(g) 四列皆 `ROLE-NOT-ADMIN`；(h) 六列皆 `AUDIT-TIME-FORMAT`；(i) 兩列皆 `AUDIT-SUBJECT-MISMATCH`；(j) 三列皆 `AUDIT-KEY-MISSING`（入帳不是回查，不得降為 NE）；(k) `AUDIT-KEY-UNKNOWN`；(l) `AUDIT-MAC-MISMATCH`
  And 全部情境：事件帳本位元組不變、`snap(R)` 不變、`<HOME>/console_audit/` 的目錄清單與各檔位元組不變；stdout 依序為 `reject decide …`、碼行、`obs-draft:`、恰一行草稿列且 `draft_ok` 成立；缺 `user`、缺 `role`、缺 `time` 的視同值不合（分別為 `AUDIT-USER-FORMAT`、`ROLE-NOT-ADMIN`、`AUDIT-TIME-FORMAT`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_1_E_1]"
```

```gherkin
# AT-233-1-E-2
# 對應 AC: AC-233-1（PRD AC-SI-33-1 的根層半；R70、R95）重複入帳、無人值守、用法與狀態層前提：同一 `audit_ref` 不得二次入帳（跨 kind 計）；與逐字稿載體同一組前提；`STALE-CARD` 取自 `body.digest`
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_1_E_2_ -q -p no:xdist -o addopts=

Feature: Console 決定的前提與重複

Scenario: 重複、用法、無人值守與前提不符皆被擋
  Given 金鑰環在位；§5.5 的 CONSOLE-PRE 表（每列一份獨立複本與一個稽核檔、預期 rc 與碼；除列內指明者外，PROP `P` 為 `proposed` 的 loop 路由）：(a) 對 `P` 核准成功一次之後，以同一個 `audit_ref` 再呼叫一次；(b) 事件帳本已有 `obs.add`（`audit_ref` 為 X）而另有一個 `decide` 稽核檔檔名也是 X；(c) OBS 帳本有一列標記 `audit_ref=Y` 但無任何事件，而另有 `decide` 稽核檔為 Y；(d) 用法 rc 3：`--carrier console` 並用 `--kind approve`、並用 `--sid`、並用 `--line 3`、並用 `--reason-class 證據不足`；`--carrier web`；缺 `--audit-ref`；`--audit-ref` 為 `12345`；(e) `AUTOSDD_UNATTENDED` 設為 `1`；(f) `body.digest` 不等於 PROP 當下 digest；(g) 對 `rejected` 態核准；(h) 對 `route` 為 `handoff:T1` 的 PROP 核准；(i) 晉升：PASS 的 `verified` 而 `flags` 為 `[unverified_ack]`；(j) NE 的 `verified` 而 `flags` 為 `[]`；(k) PASS 的 `verified` 而沙盒 `rollback_ok` 為 `false`；(l) 否決而 `reason_class` 缺；(m) 否決而 `reason_class` 為 `隨便`；(n) 解除而 PROP 不在冷卻；(o) 恢復而 RUN 不是折疊出的 SUSPENDED 所在運轉
  When 各呼叫 `M(R, decide, <ID>, --carrier, console, --audit-ref, <UUID>)`（(d) 用其旗標組合）
  Then 依序：(a)(b)(c) rc 為 `1`、碼 `AUDIT-REF-REUSED`；(d) 七個呼叫 rc 皆為 `3`、stdout 空；(e) rc 為 `1`、碼 `UNATTENDED-REFUSED`、零寫入；(f) `STALE-CARD`；(g) `PRECONDITION-STATE`；(h) `ROUTE-HANDOFF`；(i)(j) `PROMOTE-FORM-MISMATCH`；(k) `PROMOTE-PREMISE-ROLLBACK`；(l) `REASON-CLASS-MISSING`；(m) `REASON-CLASS-INVALID`；(n) `NOT-IN-COOLDOWN`；(o) `RUN-MISMATCH`；全部 rc 為 `1` 的碼以`恰`判
  And rc 為 `1` 與 `3` 的呼叫事件帳本位元組不變；`CARD-NOT-ISSUED` 與 `CARD-NOT-DELIVERED` 在 Console 路徑**不**出現（Console 路徑的合法決定不需要 `card --issue`，由本 AC 的正控釘住；卡面由 Console 頁逐字顯示 `si card` 輸出）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_1_E_2]"
```

```gherkin
# AT-233-1-E-3
# 對應 AC: AC-233-1（PRD AC-SI-33-1 的根層半；R94；NFR-P2-12）向量負控與金鑰衛生：body 改一字、換金鑰、`time` 改 `Z` 各自轉紅；金鑰環選用依 `key_id`；任何輸出不含金鑰的 8 字元子字串
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_1_E_3_ -q -p no:xdist -o addopts=

Feature: 向量負控與金鑰衛生

Scenario: 三個向量變形各自轉紅，輸出不洩金鑰
  Given §5.5 的向量 V1（`decide` 核准）；三個變形：(a) V1 的 `body` 把 `approve` 換成 `reject`（`mac` 仍為 V1 原值，兩者不同）；(b) V1 以另一把金鑰（原金鑰接一個 `x`）簽出的 `mac`，外層 `key_id` 仍為原金鑰的；(c) V1 的 `body` 把 `+08:00` 換成 `Z`（`mac` 為原值）；金鑰環情境：(d) 環為兩把金鑰以逗號連接（含前後空白），稽核檔以第二把簽；(e) 環只有第一把而稽核檔以第二把簽（`key_id` 為第二把）；金鑰衛生：每次呼叫的 stdout、stderr、OBS 草稿列與寫入的事件、OBS 列皆納入檢查
  When 各以對應的稽核檔呼叫 `M(R, decide, <PROP>, --carrier, console, --audit-ref, <UUID>)`
  Then (a) rc 為 `1`、碼 `AUDIT-MAC-MISMATCH`；(b) rc 為 `1`、碼 `AUDIT-MAC-MISMATCH`（`key_id` 在環內而位元組不同，`mac` 不符）；(c) rc 為 `1`、碼 `AUDIT-TIME-FORMAT`（`Z` 不收，先於 MAC 判）；(d) rc 為 `0`（依 `key_id` 選第二把、環內各金鑰去前後空白）；(e) rc 為 `1`、碼 `AUDIT-KEY-UNKNOWN`
  And 對這五個呼叫的全部輸出與寫入內容，以滑動視窗檢查金鑰環字串與每把金鑰位元組的任何 8 字元子字串皆不出現；`key_id`（金鑰雜湊的前 8 碼）可以出現
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_1_E_3]"
```

```gherkin
# AT-233-2-1
# 對應 AC: AC-233-2（PRD AC-SI-33-2 的根層半；R95、R98 (b)）Console 決定與稽核檔對帳正控：逐欄相符、HMAC 相符時 `events.dec_console` 為 `PASS`
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_2_1_ -q -p no:xdist -o addopts=

Feature: Console 決定對帳

Scenario: 稽核檔在場、金鑰在位時，五個欄位逐欄相符
  Given 三份獨立複本 `R1`～`R3`，依 §5.2 的 DEC-STATES 取核准、否決（附 `reason_class` 與 `reason`）、晉升後式（NE，`flags` 為只含 `unverified_ack` 的清單）三列，各以 Console 載體入帳一筆 `dec`（稽核檔在場、金鑰環在位）；另一份 `R4` 只有逐字稿載體的 `dec`（沒有任何 Console 載體事件）
  When 對 `R1`、`R2`、`R3`、`R4` 各 `MJ(check)`
  Then `R1`～`R3` 的 `events.dec_console` 為 `PASS`、無 findings（PROP 或 RUN、digest、動詞、決定者、時間、理由、理由類、旗標逐欄相符，`audit_sha256` 等於檔位元組雜湊，HMAC 相符）；`R4` 的 `events.dec_console` 為 `PASS`（無 Console 載體事件）
  And 四份的整體 rc 皆為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_2_1]"
```

```gherkin
# AT-233-2-E-1
# 對應 AC: AC-233-2（PRD AC-SI-33-2 的根層半；R95、R98 (b)、NFR-P2-11）對帳負控：欄位不符、雜湊與 HMAC 不符＝FAIL；稽核檔或金鑰不在場＝nonblocking NE（不是零筆通過）
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_233_2_E_1_ -q -p no:xdist -o addopts=

Feature: Console 決定對帳負控

Scenario: 每個不符形態收到規定的狀態與碼
  Given 十三份獨立複本，各有一筆已入帳的 Console 載體 `dec`（稽核檔與金鑰環在位）：(a)～(g) 的基底為一筆 `reject`（附 `reason_class` 與 `reason`），以 `rewrite_event` 把事件的 `prop`〔改成另一個存在的 PROP〕、`digest`、`dkind`〔改成 `return`，仍為欄位合法〕、`decider`、`decided_at`、`reason`、`reason_class` 各改成另一個合法值（七份）；(h) 的基底為一筆 NE 的 `promote`（`flags` 為只含 `unverified_ack` 的清單），把事件的 `flags` 改為前式（不帶 `flags`，欄位仍合法）；(i) 稽核檔以新 `body` 重簽（MAC 有效）使檔位元組雜湊不同於事件的 `audit_sha256`；(j) 稽核檔 `mac` 翻轉一個 hex 字元；(k) 刪除稽核檔；(l) 清掉 `AUTOSDD_SI_AUDIT_KEY`；(m) 金鑰環只含另一把金鑰（`key_id` 不在環內）
  When 各 `MJ(R, check)`
  Then (a)～(j) `events.dec_console` 為 `FAIL`、碼 `CONSOLE-AUDIT-MISMATCH`、整體 rc 為 `1`；(k) 為 `NE`、nonblocking、碼 `CONSOLE-AUDIT-MISSING`、整體 rc 為 `0`；(l)(m) 為 `NE`、nonblocking、碼 `CONSOLE-KEY-MISSING`、整體 rc 為 `0`；(k)(l)(m) 的 `overall` 為 `PASS` 而 `events.dec_console` 的狀態不是 `PASS`（量不到不被印成零筆通過）
  And 對照：還原各情境的破壞後該項為 `PASS`；`promote` 對稽核檔或金鑰不在場的 Console 載體 DEC 拒絕（fail-closed）屬晉升的 DEC 回查，另有晉升負控釘住，本 AT 只釘 `check` 側
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_233_2_E_1]"
```

```gherkin
# AT-235-1-1
# 對應 AC: AC-235-1（PRD AC-SI-35-1；R96）`obs-add` 正控：驗簽、組列、於寫入鎖內先列後事件，列的九欄與標記逐字等於預期，其餘帳本位元組不變、不 commit
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_1_1_ -q -p no:xdist -o addopts=

Feature: obs-add 正控

Scenario: 一個 Console 表單提交變成帳本的一列加一筆事件
  Given `R`（OBS 帳本九欄表後另有一段說明散文；原有資料列 OBS 編號最大者記為 `n`）；金鑰環在位；稽核檔 `kind` 為 `obs-add`、`body` 取向量 V3（`context`、`symptom`、`evidence`、`category` 為 `bug`、`severity` 為 `P3`、`face` 為 `產品`、`external_derived` 為 `false`、`time` 為 `2026-10-21T09:15:30+08:00`、`user` 為 `admin`）；`L0＝OBS 帳本位元組`、`head0＝HEAD`、`status` 的 `console_pending` 含該 `audit_ref`
  When 呼叫 `M(R, obs-add, --carrier, console, --audit-ref, <UUID3>, --by, ops1)`
  Then rc 為 `0`；stdout 單行 `ok obs.add seq=<n> id=OBS-SI-<n 加 1，至少三位> audit_ref=<UUID3>`；帳本相對 `L0` 恰多一行（插在最後一個資料列之後、說明散文之前），其餘位元組逐字不變；新列逐字等於 `| OBS-SI-<ID> | 2026-10-21 09:15 +08:00 | <context> | <symptom> | <evidence> | bug | P3 | open | 面=產品;來源=人;回報者=admin;carrier=console;audit_ref=<UUID3> |`（`時間` 保留 offset 並丟秒；處置固定 `open`）
  And 事件 `obs.add` 鍵集合恰為 `seq`、`t`、`kind`、`by`、`obs`、`audit_ref`、`audit_sha256`、`key_id`、`decider`、`carrier`；`obs` 為新列 ID、`decider` 為 `admin`、`carrier` 為字面 `console`、`by` 為 `ops1`；事件的 `seq` 大於列寫入之前最後一筆事件
  And 新列位元組數小於等於 700；`MJ(R, check)` 的每個 `row.*` 與 `obs.console_audit` 為 `PASS`、`overall` 為 `PASS`；`HEAD` 等於 `head0`（不 commit）；`MJ(R, status)` 的 `console_pending` 不再含該 `audit_ref`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_1_1]"
```

```gherkin
# AT-235-1-2
# 對應 AC: AC-235-1（PRD AC-SI-35-1；R96 (d)）`obs-add --dry-run` 唯讀預檢：預覽的列與實寫逐字相同、零寫入、不需家目錄與金鑰、`--json` 形態與 Bridge 驗證端點同形
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 子行程 `-X importtime`
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_1_2_ -q -p no:xdist -o addopts=

Feature: obs-add 預檢

Scenario: 預覽等於實寫，且什麼都沒寫
  Given `R`；body 檔 `body.json`（V3 的 `body`，含 `time`）；一個環境：不設 `AUTOSDD_SI_AUDIT_KEY`、`AUTOSDD_SI_DIR` 指向不存在的目錄（家目錄不可用）；`snap0＝snap(R)`
  When 呼叫 `M(R, obs-add, --dry-run, --body-file, body.json)`；`MJ(R, obs-add, --dry-run, --body-file, body.json)`；經 stdin 以 `--body-file -` 傳入同一 JSON；以子行程 `python -X importtime tools/selfimproving.py obs-add --dry-run …` 取 stderr 的 import 時間表；另在金鑰與稽核檔就位的複本上實寫同一 body 的 `obs-add` 取其新列
  Then 三個呼叫 rc 皆為 `0`；文字形態含 `dry-run ok`、`row: <列>`、`row_bytes=<n> row_max_bytes=700`；`--json` 的 stdout 鍵序為 `ok`、`row`、`row_bytes`、`row_max_bytes`、`findings`，`ok` 為 `true`、`findings` 為 `[]`；`row` 的 ID 欄為 `OBS-SI-<最大號加 1>`、其餘八欄與實寫的新列逐字相同
  And `snap(R)` 等於 `snap0`；家目錄不被建立；沒有鎖檔；子行程的 import 時間表不含模組 `obswrite`、`runner`、`fetch`、`research`（只走 `ro` 模組；動態純度另有負控對全部唯讀動詞統一釘住）
  And `time` 缺席的 body：預覽仍成功，`row` 的 `時間` 欄為現在時刻（帶本機 offset、分鐘精度）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_1_2]"
```

```gherkin
# AT-235-1-E-1
# 對應 AC: AC-235-1（PRD AC-SI-35-1；R96 (a)）`obs-add` 本文規則負控：每個違規一個碼、組列後自驗（`evaluate_rows`）、列位元組 700 放行 701 拒收；任一不符零變動
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_1_E_1_ -q -p no:xdist -o addopts=

Feature: obs-add 本文規則

Scenario: 欄位規則與自驗各被規定的碼擋下
  Given `R`（`row_max_bytes` 為 700）與金鑰環；§5.5 的 OBSADD-BAD 表（每列＝V3 的 `body` 改一處；每列一個獨立稽核檔，`mac` 依改後 `body` 重算）：(a) `symptom` 含 `|`；(b) `context` 為空字串；為只含空白；(c) `category` 為 `defect`；(d) `severity` 為 `P5`；(e) `face` 為 `前端`；(f) `face` 為 `守衛` 而無 `exposure`；(g) `face` 為 `產品` 而有 `exposure` 為 `a`；(h) `marks_extra` 含 `src`；含未知鍵 `x`；(i) 有 `corrects`（既有的 OBS ID）而 `marks_extra` 又含 `rel`；(j) `corrects` 為不存在的 OBS ID（執行期組出）；(k) `evidence` 為無座標的一句話；(l) `symptom` 含 Tab 字元（控制字元）；(m) `face` 為 `守衛`、`exposure` 為 `無`、`severity` 為 `P2`；(n) 列位元組恰為 700（自我校準：先預檢取 `row_bytes`，調整 `symptom` 長度）；(o) 列位元組為 701；(p) 稽核檔 `kind` 為 `decide`；(q) 同一 `audit_ref` 入帳成功一次後再呼叫；(r) `AUTOSDD_UNATTENDED` 設為 `1`
  When 各呼叫 `M(R, obs-add, --carrier, console, --audit-ref, <UUID>)`；(n)(o) 另以 `--dry-run` 預檢
  Then 依序 rc 與碼：(a) rc 1、`PIPE-IN-FIELD`；(b) `FIELD-EMPTY`（兩列）；(c) `ENUM-CATEGORY`；(d) `ENUM-SEVERITY`；(e) `FACE-INVALID`；(f) `EXPOSURE-REQUIRED`；(g) `EXPOSURE-UNEXPECTED`；(h) `MARKS-EXTRA-KEY`（兩列）；(i) `REL-CONFLICT`；(j) `CORRECTS-NOT-FOUND`；(k) `COORD-NONE`；(l) `CTRL-CHAR`；(m) `GUARD-P12-NO-EXPOSURE`；(n) rc 0（700 放行）；(o) rc 1、`ROW-BYTES-OVER`；(p) `AUDIT-KIND-MISMATCH`；(q) `AUDIT-REF-REUSED`；(r) `UNATTENDED-REFUSED`
  And 全部 rc 為 `1` 的情境：OBS 帳本與事件帳本位元組不變（零變動）；`--dry-run` 對 (o) 回 rc 1 且 `findings` 含 `ROW-BYTES-OVER`、對 (n) 回 rc 0；(k)(l)(m)(o) 的碼來自組列後自驗（`evaluate_rows` 對僅含該列的合成帳本）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_1_E_1]"
```

```gherkin
# AT-235-1-E-2
# 對應 AC: AC-235-1（PRD AC-SI-35-1；R96 (c)）寫入順序與回退：先列後事件；事件追加失敗時回退列、帳本已被他人動過則不動並印 `OBS-ORPHAN`；ID 於鎖內重讀帳本後配號、並行不重號
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）+ 執行緒
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_1_E_2_ -q -p no:xdist -o addopts=

Feature: obs-add 寫入順序與回退

Scenario: 失敗回退、孤列可偵測、ID 不重號
  Given `R`、金鑰環與三份 `obs-add` 稽核檔；情境：(a) 以替身 `evwrite.PAUSE_HOOK` 拋 `OSError`（事件追加之前，列已寫入）；(b) 同 (a) 但替身先於拋錯前把 OBS 帳本尾端追加一行別的內容（帳本長度已不等於追加後長度）；(c) 兩個執行緒同時呼叫 `obswrite` 的函式級入口（§5.6 的 `add_console_row`，避免 `redirect_stdout` 的行程級衝突；兩份不同 `audit_ref`），以替身 `PAUSE_HOOK` 讓兩者在鎖內重讀帳本之間交錯；(d) 預檢之後、寫入之前，另一個行程在帳本追加一個新 OBS 列（模擬並行手編或另一個動詞）
  When 各執行
  Then (a) rc 不為 `0`、OBS 帳本位元組還原為呼叫前（截回追加前位元組）、事件帳本不變；(b) rc 不為 `0`、帳本**不被截回**（保留別人的內容與孤列）、stderr 含碼 `OBS-ORPHAN`，其後 `MJ(check)` 的 `obs.console_audit` 為 `FAIL`、碼 `CONSOLE-EVENT-MISSING`（孤列由 `check` 承接標紅）；(c) 兩個呼叫皆 `0`、新列 ID 為連續兩個不同號、兩筆 `obs.add` 的 `obs` 各對應其列、帳本無重號；(d) 新列的 ID 為鎖內重讀後的最大號加 1（不是預檢時的），事件的 `obs` 與之一致
  And 全部情境結束後 `MJ(check)` 對 (a)(c)(d) 的帳本為 `PASS`；鎖檔已釋放（`<HOME>/locks/` 無殘留）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_1_E_2]"
```

```gherkin
# AT-235-1-E-3
# 對應 AC: AC-235-1（PRD AC-SI-35-1；NFR-P2-1；R96 (d)、R105）動態純度：唯讀動詞與 `obs-add --dry-run` 的行程不載入寫入類、`exec`、`net` 模組；以子行程的 import 時間表判，並以寫入動詞自證判準有牙
# 測試類型: Integration
# 自動化工具: pytest + 子行程 `python -X importtime`
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_1_E_3_ -q -p no:xdist -o addopts=

Feature: 唯讀動詞的動態純度

Scenario: 唯讀動詞不載入寫入類模組，寫入動詞會載入
  Given 禁用模組集合＝`obswrite`、`decwrite`、`sandbox`、`promote`、`runner`、`verify`、`fetch`、`research`、`writeverbs`（`tools/lib/selfimproving/` 之下的模組名；`evwrite` 不在其列）；`R`（合成 repo）與測試自寫的 `imported_modules(argv)`（以子行程 `python -X importtime tools/selfimproving.py <argv>` 執行，自 stderr 的 import 時間表取出全部 import 項、保留其最後兩段為 `selfimproving.<名>` 者的 `<名>`）
  When 對唯讀動詞 `check`、`status`、`scan`、`export`（五種 `--kind` 各一）、`card <PROP>`（不帶 `--issue`）與 `obs-add --dry-run --body-file <檔>` 各取 `imported_modules`；對寫入動詞 `obs-close`（金鑰與稽核檔就位）、`obs-add --carrier console`、`run-open` 各取一次作為自證
  Then 每個唯讀呼叫的模組集合與禁用集合的交集為空；每個寫入呼叫的集合含其對應模組（`obs-close` 與 `obs-add` 含 `obswrite`、`run-open` 含 `writeverbs`），證明判準不是空轉
  And 每個唯讀呼叫的檔案摘要與 `git status --porcelain` 於呼叫前後相同（P0 R8 的動態純度涵蓋 `check` 的四個追加項）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_1_E_3]"
```

```gherkin
# AT-235-2-1
# 對應 AC: AC-235-2（PRD AC-SI-35-2；R97）`obs-close` 正控：只有 `open` 變終值一次；只動該列第 8 欄、其餘位元組逐字不變；原子改寫；同鎖內追加 `obs.close`；七種終值形態皆可
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_2_1_ -q -p no:xdist -o addopts=

Feature: obs-close 正控

Scenario: 七種終值各關一列，位元組差只在處置欄
  Given `R` 的 OBS 帳本含七個處置為 `open` 的列（`OBS-SI-<a1>`～`<a7>`；列內含中文字與連續空白的症狀文字，使「其餘位元組逐字不變」有牙）；`R` 的事件帳本含一個 PROP（`write_events`：`run.open` 與 `prop`，供 `proposed@` 引用，`ref.carrier_families` 的 PROP 族存在性判成立）；七個 `obs-close` 稽核檔，`disposition` 依序為 `fixed@<存在的 commit 前 12 碼>`、`DEF-<執行期組出而存在於缺陷帳本的號>`、`deferred：等 P3 輪`、`retired：docs/notes/old.md:3`、`decided：掌舵者裁決不修`、`merged@<另一個存在的 OBS ID>`、`proposed@<存在的 PROP ID>`；金鑰環在位；`L0＝OBS 帳本位元組`
  When 依序對每個列呼叫 `M(R, obs-close, --carrier, console, --audit-ref, <UUID>, --by, ops1)`，每次之後取帳本位元組 `Lk`
  Then 每次 rc 為 `0`；stdout 單行 `ok obs.close seq=<n> id=OBS-SI-<該列> audit_ref=<UUID>`；`Lk` 相對 `Lk-1` 的位元組差只在被關列的第 8 欄（處置，由 `open` 換成 `disposition`），列內其他欄、其他列、檔頭、行尾（含 CRLF 與行尾空白）逐位元組不變
  And 事件 `obs.close` 鍵集合恰為 `seq`、`t`、`kind`、`by`、`obs`、`audit_ref`、`audit_sha256`、`key_id`、`decider`、`carrier`、`disposition`；`disposition` 逐字等於稽核檔的值；`MJ(R, check)` 的 `history.row_mutated` 為 `PASS`（`open` 轉終值是 P0 既有的合法改動）、`obs.console_audit` 為 `PASS`、`overall` 為 `PASS`
  And 原子改寫：以替身記錄 `os.replace` 的呼叫，每次 `obs-close` 恰一次、來源為與帳本同目錄的暫名檔；呼叫後同目錄無暫名檔；不 commit
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_2_1]"
```

```gherkin
# AT-235-2-E-1
# 對應 AC: AC-235-2（PRD AC-SI-35-2；R97）`obs-close` 前置負控：不存在、只在封存檔、非 `open`、終值不合、缺附加文字、含 `|`、改寫後超列長、帳本在預檢後被改動
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_2_E_1_ -q -p no:xdist -o addopts=

Feature: obs-close 前置負控

Scenario: 每個前置不符一個碼、帳本位元組不變
  Given `R`（OBS 主帳本與其封存檔）；金鑰環；§5.5 的 OBSCLOSE-BAD 表（每列一個獨立稽核檔）：(a) `obs_id` 不存在於主帳本與封存檔（執行期組出）；(b) `obs_id` 只在封存檔；(c) 該列處置已是 `fixed@<sha>`；(d) 該列處置為 `deferred：x`（非恰為 `open`）；(e) `disposition` 為 `open`；為 `finished`（首詞不屬終值枚舉）；`fixed@zzzz`（參照文法不符）；(f) `deferred` 缺附加文字；`retired：沒有座標`；(g) `disposition` 含 `|`；(h) 改寫後該列位元組超過 `row_max_bytes`（自我校準：先算出恰使列長為 701 的處置）；剛好 700 者放行；(i) 稽核檔 `kind` 為 `obs-add`；(j) 同一 `audit_ref` 入帳成功一次後再呼叫；(k) `AUTOSDD_UNATTENDED` 設為 `1`；競態 (l)：以替身 `obswrite.PAUSE_HOOK`（預檢之後、鎖內重讀之前）把帳本另一列改動一個位元組
  When 各呼叫 `M(R, obs-close, --carrier, console, --audit-ref, <UUID>)`
  Then 依序 rc 與碼：(a) `OBS-NOT-FOUND`；(b) `OBS-ARCHIVED`；(c)(d) `NOT-OPEN`；(e) 三列皆 `DISPOSITION-INVALID`；(f) 兩列皆 `DISPOSITION-TEXT-MISSING`；(g) `PIPE-IN-FIELD`；(h) 701 為 rc 1、`ROW-BYTES-OVER`，700 為 rc 0；(i) `AUDIT-KIND-MISMATCH`；(j) `AUDIT-REF-REUSED`；(k) `UNATTENDED-REFUSED`；(l) `LEDGER-CHANGED`；rc 為 `1` 者以`恰`判
  And rc 為 `1` 的情境：OBS 帳本、封存檔與事件帳本位元組不變、無暫名檔殘留；(l) 的鎖已釋放
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_2_E_1]"
```

```gherkin
# AT-235-2-E-2
# 對應 AC: AC-235-2（PRD AC-SI-35-2；R97）原子改寫的失敗路徑：寫暫名檔或 `os.replace` 失敗＝rc 1、帳本未變、暫名檔清掉、單次嘗試不重試、不追加 `obs.close`
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_2_E_2_ -q -p no:xdist -o addopts=

Feature: obs-close 失敗路徑

Scenario: 改寫失敗不留痕跡
  Given `R` 與一個 `obs-close` 稽核檔；三個替身情境：(a) 寫暫名檔時 `os.fsync` 拋 `OSError`；(b) `os.replace` 拋 `PermissionError`（模擬 Windows 共享違規）；(c) `os.replace` 拋 `OSError`；一個計數器記錄 `os.replace` 的呼叫次數；`L0＝帳本位元組`、`ev0＝事件帳本位元組`
  When 各呼叫 `M(R, obs-close, --carrier, console, --audit-ref, <UUID>)`
  Then 三者 rc 皆為 `1`；(b)(c) 的 `os.replace` 恰被呼叫 `1` 次（不重試）；帳本位元組等於 `L0`、事件帳本位元組等於 `ev0`（未追加 `obs.close`）；與帳本同目錄無任何暫名檔殘留（`finally` 已刪）；鎖檔已釋放
  And 對照：撤掉替身後同一呼叫 rc 為 `0`（證明失敗來自注入）；`tools/lib/selfimproving/` 全部原始碼不含 `time.sleep`、`while True`（單次嘗試不重試由結構保證，套件靜態掃描另有負控釘住）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_2_E_2]"
```

```gherkin
# AT-235-3-1
# 對應 AC: AC-235-3（PRD AC-SI-35-3；R68、R97）CLI 的全部介面沒有刪除或改號能力：OBS 寫入動詞恰 `obs-add` 與 `obs-close`；任何名為刪除、改號、編輯的動詞一律 rc 3；退場只能是處置終值 `retired：<座標>`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_3_1_ -q -p no:xdist -o addopts=

Feature: 沒有刪除與改號

Scenario: 退場只能走處置終值
  Given `R`；動詞表（R68 的 21 個）；`snap0＝snap(R)`、`L0＝OBS 帳本位元組`；一個 `obs-close` 稽核檔，`disposition` 為 `retired：docs/notes/old.md:3`
  When 對下列名稱各呼叫 `M(R, <名稱>, --repo …)`：`obs-delete`、`obs-remove`、`obs-rm`、`obs-edit`、`obs-update`、`obs-renumber`、`obs-retire`、`obs-purge`、`obs-set`；再呼叫 `obs-close` 取終值 `retired`
  Then 九個非動詞名稱 rc 皆為 `3`、stdout 空、stderr 至少一行；`snap(R)` 等於 `snap0`；動詞表中的 OBS 寫入動詞恰為 `obs-add` 與 `obs-close`（其餘 19 個動詞的名稱不含 `obs`）；`obs-close` 取終值 `retired` 後：帳本列數不變、該列 ID 不變、處置為 `retired：docs/notes/old.md:3`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_3_1]"
```

```gherkin
# AT-235-3-E-1
# 對應 AC: AC-235-3（PRD AC-SI-35-3；R96、R97）改寫不變量：任意序列的 `obs-add` 與 `obs-close` 之後列數只增不減、ID 序列嚴格遞增且不重號、既有列的第 1～7、9 欄位元組不變；更正走新列
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_3_E_1_ -q -p no:xdist -o addopts=

Feature: 帳本只增不刪

Scenario: 八步固定序列後的不變量
  Given `R`；金鑰環；固定序列（兩個 `obs-add`、一個帶 `corrects` 指向第一列的 `obs-add`、三個 `obs-close`〔關不同列〕、一個被拒的 `obs-close`〔`NOT-OPEN`〕、一個被拒的 `obs-add`〔`PIPE-IN-FIELD`〕）；每步之後取帳本快照 `S_k`（列的九欄陣列與列號）
  When 依序執行
  Then 每步之後：列數大於等於上一步（被拒的步驟不變）；全部 ID 嚴格遞增且無重複；對於每個在 `S_(k-1)` 已存在的列，在 `S_k` 中其第 1～7 欄與第 9 欄逐字相同、第 8 欄僅可由 `open` 變成終值一次（其後不再改變）；帶 `corrects` 的新列不改動被更正列的任何欄位
  And 沒有任何步驟使 `MJ(check)` 的 `history.row_mutated` 為 `FAIL`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_3_E_1]"
```

```gherkin
# AT-235-4-1
# 對應 AC: AC-235-4（PRD AC-SI-35-4 的根層半；R94）資格正控：`role` 為 `ADMIN`、帳號名合 `^[A-Za-z0-9_.-]{1,64}$` 時受理，帳號名進 `回報者` 與事件 `decider`
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_4_1_ -q -p no:xdist -o addopts=

Feature: Console 帳號資格

Scenario: 邊界上的合法帳號名受理
  Given `R`、金鑰環；四份 `obs-add` 稽核檔，`user` 依序為 `a`（1 字元）、`Admin.Ops-01_x`、64 個合法字元、`0123456789`；`role` 皆為 `ADMIN`
  When 各呼叫 `M(R, obs-add, --carrier, console, --audit-ref, <UUID>)`
  Then 四次 rc 皆為 `0`；各新列的標記含 `回報者=<user>` 且標記欄內 `;` 恰分出五個鍵值（`面`、`來源`、`回報者`、`carrier`、`audit_ref`；body 沒有 `exposure`、`external_derived` 為 `false`、無 `marks_extra`，故無多餘鍵）；事件的 `decider` 等於 `user`
  And `MJ(check)` 的 `row.markers`、`row.provenance` 為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_4_1]"
```

```gherkin
# AT-235-4-E-1
# 對應 AC: AC-235-4（PRD AC-SI-35-4 的根層半；R94）資格負控：非 ADMIN、帳號名含會破壞標記欄的字元、過長、缺鍵；標記注入無從得逞
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_4_E_1_ -q -p no:xdist -o addopts=

Feature: Console 帳號資格負控

Scenario: 注入與越權被擋
  Given `R`、金鑰環；稽核檔 `user` 依序為 `a;面=守衛`（試圖偽造標記）、`a=b`、`a b`、`a|b`、65 個合法字元、`管理者`、空字串；另有 `role` 為 `OPERATOR`、`VIEWER`、小寫 `admin`、缺 `role` 各一份（`user` 合法）
  When 各呼叫 `M(R, obs-add, --carrier, console, --audit-ref, <UUID>)`
  Then 帳號名七列 rc 皆為 `1`、碼 `AUDIT-USER-FORMAT`；角色四列 rc 皆為 `1`、碼 `ROLE-NOT-ADMIN`；OBS 帳本與事件帳本位元組不變
  And 注入檢查：任何被受理的新列，其標記欄以 `;` 切開後 `回報者`、`carrier`、`audit_ref` 各恰一個（`parse_marks` 無語法問題）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_4_E_1]"
```

```gherkin
# AT-235-5-1
# 對應 AC: AC-235-5（PRD AC-SI-35-5 的根層半；R98 (d)、R99 (a)、R76）`check` 與 `status` 正控：帶 `carrier=console` 的列有 `obs.add` 且稽核檔逐欄相符、HMAC 相符；`status` 列出尚未入帳的稽核檔
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_5_1_ -q -p no:xdist -o addopts=

Feature: Console 寫入的對帳與待入帳

Scenario: 入帳前列在 `console_pending`，入帳後 `check` 綠
  Given `R`、金鑰環；三份稽核檔：`obs-add`（UUID3）、`obs-close`（針對一個 `open` 列）、`decide`（核准某 PROP）；檔名為 `<uuid>.json`，另放一個檔名不合 UUID 形態的 `notes.json` 與一個內容無法解析的 `<uuid>.json`
  When 入帳前 `MJ(R, status)`；依序入帳三者；入帳後 `MJ(R, status)` 與 `MJ(R, check)`
  Then 入帳前 `console_pending` 為 `{status: read, count: 4, items: […]}`（三份合法與一份無法解析者；`items` 依 `audit_ref` 的字串序，元素鍵為 `audit_ref`、`kind`；無法解析者 `kind` 為 `null` 而仍列出；`notes.json` 不列）；入帳後 `count` 為 `1`（只剩無法解析者）
  And 入帳後 `check` 的 `obs.console_audit` 與 `events.dec_console` 為 `PASS`（每個 `carrier=console` 的列有 `obs.add`；`audit_sha256`、列與事件逐欄相符；HMAC 相符；`obs.close` 指向的列處置已非 `open`）；`status` 的其餘 13 鍵次序與值不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_5_1]"
```

```gherkin
# AT-235-5-E-1
# 對應 AC: AC-235-5（PRD AC-SI-35-5 的根層半；R98 (d)、R76、NFR-P2-11）對帳負控：缺事件、處置未改、欄位不符、稽核檔或金鑰不在場＝NE 而非零筆通過、標記值域與成對與唯一
# 測試類型: Integration
# 自動化工具: pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_235_5_E_1_ -q -p no:xdist -o addopts=

Feature: Console 寫入對帳負控

Scenario: 每個缺口收到規定的狀態與碼
  Given 以 `write_events` 與手改 OBS 帳本構成的獨立複本：(a) 一列帶 `carrier=console;audit_ref=X` 而無任何 `obs.add`；(b) 一筆 `obs.close` 指向處置仍為 `open` 的列；(c) 合法的 `obs.add` 與列，稽核檔在場但 `body.symptom` 與列的症狀不同；(d) 同 (c) 而 `body.user` 與事件的 `decider` 不同；(e) 稽核檔不存在；(f) 金鑰環未設；(g) 金鑰環不含 `key_id`；(h) 稽核檔 `mac` 被翻轉；(i) 一列帶 `carrier=console` 而無 `audit_ref`；(j) 一列帶 `audit_ref` 而無 `carrier`；(k) 兩列有相同的 `audit_ref`；(l) 一列 `carrier=web;audit_ref=<UUID>`；(m) 一列 `carrier=console;audit_ref=not-a-uuid`；(n) 一個 `obs-close` 事件的稽核檔 `disposition` 與列的處置不逐字相等
  When 各 `MJ(R, check)`
  Then (a) `obs.console_audit` 為 `FAIL`、`CONSOLE-EVENT-MISSING`；(b) `FAIL`、`CONSOLE-CLOSE-NOT-APPLIED`；(c)(d)(h)(n) `FAIL`、`CONSOLE-AUDIT-MISMATCH`；(e) `NE`、nonblocking、`CONSOLE-AUDIT-MISSING`；(f)(g) `NE`、nonblocking、`CONSOLE-KEY-MISSING`；(i)(j) `row.markers` 為 `FAIL`、`CONSOLE-MARK-PAIR`；(k) `row.markers` 為 `FAIL`、`CONSOLE-AUDIT-DUP`（主語為後出現的列）；(l)(m) `row.markers` 為 `FAIL`、`MARK-VALUE`
  And (e)(f)(g) 的整體 `overall` 為 `PASS`、rc 為 `0`，而 `obs.console_audit` 的狀態不是 `PASS`（不是零筆通過）；`status` 於家目錄不存在時 `console_pending` 為 `{status: NOT-EVALUABLE, reason: home-unavailable}`（不印成空清單）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_235_5_E_1]"
```

```gherkin
# AT-240-12-1
# 對應 AC: AC-240-12（本檔自增；PRD §9.2 `export --json` 輸出、AC-SI-31-4 與 AC-SI-32-1 的 `buckets[]`、OBS-SI-237；R99）`export` 的 observations 項加 `buckets[]`（不 casefold、同一個 `scan.bucket_of`）；`status` 加 `console_pending`；`export --kind status` 的同鍵量不到
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_240_12_1_ -q -p no:xdist -o addopts=

Feature: export 與 status 的 P2 擴充

Scenario: buckets 逐列等於歸桶函式，鍵序與既有欄位不變
  Given `R` 的 OBS 帳本含九欄列：證據座標依序為 `tools/lib/selfimproving/fold.py:10`（SelfImproving）、`AutoClaude/tests/a.py:3`（AutoClaude）、`AISDLC_SDD/x/y.md:1`（AISDLC_SDD）、`AgentConsole/frontend/z.tsx:9`（AgentConsole）、`docs/notes/demo.md:2`（根層）、兩個桶的混合 `AutoClaude/a.py:1、AgentConsole/b.ts:2`、無路徑片段的 `` `git status` rc=0 ``（第八種座標形態）、大小寫不同的 `autoclaude/tests/a.py:3`；另一個欄數非 9 的壞列
  When 呼叫 `MJ(R, export, --kind, observations)` 與 `MJ(R, status)` 與 `MJ(R, export, --kind, status)`
  Then 每個九欄項的末鍵為 `buckets`（置於 `marks_kv` 與 `line` 之後），值依次為 `[SelfImproving]`、`[AutoClaude]`、`[AISDLC_SDD]`、`[AgentConsole]`、`[根層]`、`[AutoClaude, AgentConsole]`（依 `scan.BUCKETS` 次序去重）、`[未分類]`（零個路徑片段）、`[根層]`（`autoclaude/…` 小寫形態**不被 casefold 成** `AutoClaude`：`bucket_of` 對原文大小寫敏感）；壞列 `{line, raw, valid: false}` 無 `buckets`；`schema_rev` 仍為 `1`
  And 測試以 `scan.bucket_of` 對相同片段逐一重算，與 `buckets` 逐項相等（同一函式，前端不重算）
  And `status` 的鍵序為既有 13 鍵（次序與值不變）之後附加 `console_pending`；`export --kind status` 的 `items[0]` 同樣末鍵為 `console_pending`，值恆為 `{status: NOT-EVALUABLE, reason: export-reads-no-home}`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_12_1]"
```

```gherkin
# AT-240-12-E-1
# 對應 AC: AC-240-12（本檔自增；R99；P1 R61）`export` 不讀家目錄任何檔：以哨兵字串釘住；`status` 只列稽核檔目錄清單、不讀其內容；缺家目錄時 NOT-EVALUABLE 而非空清單
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_console_obs.py -k AT_240_12_E_1_ -q -p no:xdist -o addopts=

Feature: export 不讀家目錄

Scenario: 哨兵字串不出現在任何輸出，且檔案存取不觸及家目錄
  Given `R` 與家目錄 `<HOME>`：其下 `console_audit/<uuid>.json`（內容含哨兵字串 `SENTINEL-HOME-<執行期亂數>` 的合法稽核檔）、`heldout/`、`sandbox/`、`research/` 各放一個含哨兵的檔；一個替身記錄 `builtins.open`、`io.open`、`os.scandir`、`os.listdir` 的路徑參數（涵蓋 `Path.read_bytes`、`read_text`、`iterdir` 的底層呼叫），分別包住 `export` 呼叫與 `status` 呼叫
  When 呼叫 `M(R, export, --kind, <五種 kind>)`（文字與 `--json`）；呼叫 `MJ(R, status)`
  Then 五種 `export` 的輸出皆不含哨兵字串；`export` 呼叫期間替身記錄的任何路徑都不在 `<HOME>` 之下（`export` 的檔案存取不觸及家目錄）；`status` 呼叫期間記錄到的 `<HOME>` 之下路徑只落在 `console_audit/`（目錄清單與各 `<uuid>.json` 的 `kind` 欄，不碰 `heldout/`、`sandbox/`、`research/`）；`status` 的 `console_pending` 只含 `audit_ref` 與 `kind`，輸出不含哨兵字串（只取 `kind`，其餘內容不輸出）
  And `<HOME>` 不存在時：`export` 照常 rc 為 `0`；`status` 的 `console_pending` 為 `{status: NOT-EVALUABLE, reason: home-unavailable}`（不是 `count` 為 `0`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_12_E_1]"
```


**G. `apply_lock` 的 Windows 刪除待決修法（AL）**

```gherkin
# AT-240-8-1
# 對應 AC: AC-240-8（本檔自增；DEF-200-559、OBS-SI-210；R100 (1)）取鎖：`os.open` 遇 `PermissionError`（Windows 刪除待決）視同忙碌、納入有界重試，之後取鎖成功
# 測試類型: Unit
# 自動化工具: pytest／unittest + `mock.patch`（任一平台可重現，不靠真實競態）
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_1_ -q -p no:xdist -o addopts=

Feature: apply_lock 取鎖遇 PermissionError

Scenario: 前三次被拒、第四次成功
  Given tmp 內的鎖檔路徑 `lp`；`mock.patch.object` 把 `os.open` 包成：對路徑等於 `lp` 的呼叫，前三次拋 `PermissionError(13, 'denied')`、其後轉呼叫真實的 `os.open`（其他路徑一律轉呼叫）；一個 `time.sleep` 的記錄替身（轉呼叫真實函式並記下引數）
  When 執行 `with apply_lock.acquire(lp, 5, 60, poll_interval=0.01):`，區塊內讀 `lp` 的內容
  Then 不拋任何例外（不是 `LockBusyError`、也不是 `PermissionError`）；`os.open` 對 `lp` 恰被呼叫 4 次；區塊內 `lp` 存在、內容符合 `<pid>` 換行 `<ISO 8601>` 換行；離開區塊後 `lp` 不存在
  And 重試的等待取自 `poll_interval`（`time.sleep` 的記錄為三筆、各為 `0.01`）；整段牆鐘遠小於 `timeout`（有界重試，不是等滿上限）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_1]"
```

```gherkin
# AT-240-8-2
# 對應 AC: AC-240-8（本檔自增；R100 (2)）陳舊鎖回收：`unlink` 遇 `PermissionError` 視為「這輪沒收成」，與 `FileNotFoundError` 同樣不是錯誤，下一輪有界重試後回收成功
# 測試類型: Unit
# 自動化工具: pytest／unittest + `mock.patch`
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_2_ -q -p no:xdist -o addopts=

Feature: apply_lock 回收遇 PermissionError

Scenario: 第一次回收被拒、第二次成功並取得鎖
  Given tmp 內的鎖檔 `lp`，內容為另一個行程的資訊、mtime 設為一小時前（`os.utime`）；`mock.patch.object(Path, unlink, autospec=True)` 的包裝函式：對 `lp` 的第一次 `unlink` 拋 `PermissionError(13, 'denied')`、之後轉呼叫真實函式，並記錄對 `lp` 的呼叫次數
  When 執行 `with apply_lock.acquire(lp, 5, 60, poll_interval=0.01):`
  Then 不拋例外；對 `lp` 的 `unlink` 於取鎖階段至少被呼叫 2 次（第一次被拒、第二次回收成功），取得鎖之後區塊內 `lp` 的內容是**本行程**的 pid 而不是舊持有者的
  And 對照：把被拒的 `PermissionError` 換成 `FileNotFoundError` 時行為相同（既有語意不變）；`stale_after` 內的新鮮鎖不被回收（`unlink` 呼叫數為 0，並在 `timeout` 後拋 `LockBusyError`，既有測試語意）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_2]"
```

```gherkin
# AT-240-8-3
# 對應 AC: AC-240-8（本檔自增；R100 (3)）釋放：`unlink` 遇 `PermissionError` 為有界重試，初次嘗試之後最多再重試 `RELEASE_RETRIES` 次；邊界值成功時鎖檔被刪除、不印警告
# 測試類型: Unit
# 自動化工具: pytest／unittest + `mock.patch`
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_3_ -q -p no:xdist -o addopts=

Feature: apply_lock 釋放重試

Scenario: 前 RELEASE_RETRIES 次被拒、第 RELEASE_RETRIES 加 1 次成功
  Given tmp 內的鎖檔路徑 `lp`；`k＝apply_lock.RELEASE_RETRIES`（讀常數，不寫死 5）；`mock.patch.object(Path, unlink, autospec=True)` 的包裝函式：對 `lp` 的前 `k` 次 `unlink` 拋 `PermissionError(13, 'denied')`、第 `k` 加 1 次起轉呼叫真實函式；`time.sleep` 與標準錯誤輸出的記錄替身
  When 執行 `with apply_lock.acquire(lp, 5, 60, poll_interval=0.01): pass`（區塊本身正常離開）
  Then 不拋例外；離開後 `lp` 不存在；對 `lp` 於釋放階段的 `unlink` 共被呼叫 `k` 加 1 次；釋放期間的 `time.sleep` 記錄為 `k` 筆、各為 `0.01`（間隔沿 `poll_interval`）
  And 標準錯誤沒有任何輸出（邊界成功不印警告）；`apply_lock.RELEASE_RETRIES` 為正整數（常數存在、有界）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_3]"
```

```gherkin
# AT-240-8-E-1
# 對應 AC: AC-240-8（本檔自增；R100 (1)、(4)）取鎖逾時的例外型別：最後一次失敗是 `PermissionError` ⇒ 逾時拋原始 `PermissionError`（不誤報成別的行程持有）；最後一次是 `FileExistsError` ⇒ 仍是 `LockBusyError` 加持鎖者資訊；其他 `OSError` 立即穿出、不納入重試
# 測試類型: Unit
# 自動化工具: pytest／unittest + `mock.patch`
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_E_1_ -q -p no:xdist -o addopts=

Feature: apply_lock 取鎖逾時的例外型別

Scenario: 三種失敗各被如實回報，公開面不變
  Given tmp 內鎖檔路徑 `lp`；情境：(a) `os.open` 對 `lp` 永遠拋 `PermissionError(13, 'denied')`；(b) `lp` 已存在且新鮮（另一個持有者；內容含其 pid），`os.open` 照常回 `FileExistsError`；(c) 先拋兩次 `PermissionError`，其後 `lp` 被建立（模擬另一個行程搶到）而 `os.open` 回 `FileExistsError` 直到逾時；(d) `lp` 的父目錄不存在（真實 `FileNotFoundError`）；(e) `os.open` 拋 `OSError(5, 'EIO')`
  When 各執行 `apply_lock.acquire(lp, 0.4, 60, poll_interval=0.02)` 的 `with` 區塊，量測牆鐘
  Then (a) 拋 `PermissionError`（`errno` 為 13、不是 `LockBusyError`），牆鐘在 `0.4` 秒到 `0.4` 加寬鬆餘裕之間（有界重試，總時限仍受 `timeout` 管）；(b) 拋 `LockBusyError`、訊息含持鎖者的 pid 與字樣`持鎖者資訊`（既有語意不變）；(c) 拋 `LockBusyError`（最後一次失敗為 `FileExistsError`）；(d) 立即拋 `FileNotFoundError`（牆鐘遠小於 `0.4` 秒）；(e) 立即拋 `OSError`、`errno` 為 5（其他 `OSError` 不被吞）
  And 簽名不變：`inspect.signature(apply_lock.acquire)` 的參數依序為 `lock_path`、`timeout`、`stale_after`、`poll_interval`（預設 `0.2`）；`apply_lock.LockBusyError` 仍是 `RuntimeError` 的子類
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_E_1]"
```

```gherkin
# AT-240-8-E-2
# 對應 AC: AC-240-8（本檔自增；R100 (2)）回收的負控：回收一直被拒時整體仍有界（以 `LockBusyError` 逾時）；回收時其他 `OSError` 不被吞；新鮮鎖永不回收
# 測試類型: Unit
# 自動化工具: pytest／unittest + `mock.patch`
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_E_2_ -q -p no:xdist -o addopts=

Feature: apply_lock 回收的負控

Scenario: 永遠回收不掉時有界逾時，其他 OSError 穿出
  Given tmp 內的陳舊鎖檔 `lp`（mtime 為一小時前）；情境：(a) `Path.unlink` 對 `lp` 永遠拋 `PermissionError`；(b) `Path.unlink` 對 `lp` 拋 `OSError(5, 'EIO')`；(c) `lp` 新鮮（mtime 為現在）而 `stale_after` 為 60
  When 各執行 `apply_lock.acquire(lp, 0.4, 1, poll_interval=0.02)`（(c) 的 `stale_after` 為 60）
  Then (a) 於約 `0.4` 秒後拋 `LockBusyError`（最後一次失敗為 `FileExistsError`），沒有無界迴圈（牆鐘小於 `0.4` 加寬鬆餘裕）、`unlink` 被呼叫多次；(b) 立即拋 `OSError`、`errno` 為 5（回收只吞 `FileNotFoundError` 與 `PermissionError`）；(c) 於 `0.4` 秒後拋 `LockBusyError`、對 `lp` 的 `unlink` 呼叫數為 `0`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_E_2]"
```

```gherkin
# AT-240-8-E-3
# 對應 AC: AC-240-8（本檔自增；R100 (3)）釋放用盡後不改 rc、不拋例外：印警告到標準錯誤、鎖檔殘留交陳舊回收；區塊本身的例外不被遮蔽；殘留鎖在 `stale_after` 之後被下一個取鎖者回收
# 測試類型: Unit
# 自動化工具: pytest／unittest + `mock.patch`
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_E_3_ -q -p no:xdist -o addopts=

Feature: apply_lock 釋放用盡

Scenario: 釋放一直被拒時不拋、不吞區塊例外、殘留可回收
  Given tmp 內鎖檔路徑 `lp`；`k＝apply_lock.RELEASE_RETRIES`；`mock.patch.object(Path, unlink, autospec=True)` 的包裝函式：對 `lp` 的釋放階段永遠拋 `PermissionError(13, 'denied')`（取鎖階段無 `unlink`）；標準錯誤的記錄替身
  When 情境 (a)：`with apply_lock.acquire(lp, 5, 60, poll_interval=0.01): pass`；情境 (b)：區塊內拋 `ValueError('body')`；情境 (c)：(a) 之後撤掉替身、把 `lp` 的 mtime 設為一小時前，再 `acquire(lp, 5, 60, poll_interval=0.01)`
  Then (a) 不拋例外；對 `lp` 的釋放 `unlink` 恰被呼叫 `k` 加 1 次（有界）；`lp` 仍存在；標準錯誤含 `lp` 的路徑字串與 `PermissionError` 字樣（一則警告）；(b) 拋出的例外是 `ValueError`（不被釋放失敗遮蔽），其餘同 (a)；(c) 取鎖成功（殘留鎖被當陳舊鎖回收）且不拋例外
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_E_3]"
```

```gherkin
# AT-240-8-E-4
# 對應 AC: AC-240-8（本檔自增；R100 (6)、P1 R30）`evwrite` 層：釋放用盡時事件已追加、呼叫端回 rc 0 而非 rc 3、輸出不含「帳本未變動」；取鎖階段的 `PermissionError` 逾時仍是 rc 3 且該句為真；`FileExistsError` 逾時仍是 rc 1 的 `LOCK-BUSY`
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ `mock.patch`
# 判定指令: python -m pytest tools/tests/test_apply_lock.py -k AT_240_8_E_4_ -q -p no:xdist -o addopts=

Feature: 寫入動詞對 apply_lock 修法的承接

Scenario: 釋放失敗不再讓已寫入的事件被回報成「帳本未變動」
  Given `R`（`make_p2_repo`）與 `AUTOSDD_SI_DIR` 指向 tmp；三個情境：(a) `mock.patch.object(Path, unlink, autospec=True)` 對家目錄 `locks/<hash>.lock` 的 `unlink` 永遠拋 `PermissionError`；(b) `os.open` 對該鎖檔路徑永遠拋 `PermissionError`，且 `evwrite.LOCK_TIMEOUT_SECONDS` 以 `mock.patch.object` 改為 `0.3`；(c) 該鎖檔已存在且新鮮（`os.utime` 設為現在）、`LOCK_TIMEOUT_SECONDS` 為 `0.3`
  When (a) 呼叫 `M(R, run-open, --trigger, a, --coord, tools/a.py:1, --by, main)`，其後撤掉替身、把殘留鎖檔 mtime 設為一小時前並再呼叫一次同樣的動詞（`LOCK_STALE_SECONDS` 為 `60`）；(b)(c) 各呼叫同一個動詞一次
  Then (a) 第一次 rc 為 `0`、stdout 為 `ok run.open seq=<n> id=RUN-SI-<NNN> …`、事件帳本多一行該事件、標準錯誤含警告（鎖檔路徑與 `PermissionError`）、stdout 與標準錯誤皆不含`帳本未變動`；殘留鎖檔存在；第二次 rc 為 `0`、事件的 `seq` 為 `2`（殘留鎖被回收、配號連續）
  And (b) rc 為 `3`、標準錯誤含`事件追加失敗（PermissionError），帳本未變動`（此句為真：取鎖階段就失敗，事件帳本位元組不變）；(c) rc 為 `1`、碼 `LOCK-BUSY`、detail 含持鎖者資訊（既有語意不變）、事件帳本位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_8_E_4]"
```


**H. 來源表 host 僅限 ASCII 與 `scan` 的資訊型草稿列（RS）**

```gherkin
# AT-230-2-1
# 對應 AC: AC-230-2（PRD AC-SI-30-2 的 P2 收口；R101）來源表 host 僅限 ASCII 的正控：合規的 ASCII host（含大寫、帶埠、`xn--` 只出現在 label 中段、單連字號的 `xn-`）不被新規則誤判；真來源表仍 PASS
# 測試類型: Unit
# 自動化工具: pytest（純函式加唯讀真來源表）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_230_2_1_ -q -p no:xdist -o addopts=

Feature: 來源表 host 的 ASCII 判準

Scenario: ASCII host 不誤判
  Given 沿 P1 夾具 `table_bytes` 建出的來源表位元組（每列一個來源，`url` 依序為 `https://example.org/a`、`https://docs.example.co.uk/b`、`https://a-b.example.net/c`、`https://example.org:8443/d`、`https://axn--b.example/e`（`xn--` 在 label 中段）、`https://xn-b.example/f`（單連字號）、`https://EXAMPLE.ORG/g`）；標準 `Policy`（不放寬私網）；真 repo 的 `docs/06_quality/SelfImproving_Protocol/research_sources.json`（唯讀）
  When 對該位元組呼叫 `sources.validate_table(raw, policy)`；對真來源表呼叫同一函式；對真 repo 呼叫 `python tools/selfimproving.py check --json` 取 `research.sources` 項（子行程，rc 先存變數）
  Then 對七個 ASCII host 的回傳不含任何碼 `SRC-URL-HOST`（subject 為這七列者）；真來源表回傳為空清單；真 repo 的 `research.sources` 狀態為 `PASS`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_230_2_1]"
```

```gherkin
# AT-230-2-E-1
# 對應 AC: AC-230-2（PRD AC-SI-30-2 的 P2 收口；R101；P1 TCS 勘誤三、四）非 ASCII 與 IDNA 形態的 host 一律拒收：全形數字與字母、表意句號、中文、任一 label 以 `xn--`（不分大小寫）起頭；不做正規化後比對
# 測試類型: Unit
# 自動化工具: pytest（純函式；替身 `socket.getaddrinfo`）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_230_2_E_1_ -q -p no:xdist -o addopts=

Feature: 來源表 host 的非 ASCII 拒收

Scenario: 每個非 ASCII 或 IDNA host 被 `SRC-URL-HOST` 擋下
  Given §5.4 的 HOST-BAD 表（每列一個來源，`url`）：`https://１２７.0.0.1/x`（全形數字）；`https://ｅｘａｍｐｌｅ.org/`（全形字母）；`https://example。org/x`（U+3002 表意句號）；`https://例え.jp/`（中日文）；`https://xn--e1afmkfd.xn--p1ai/`；`https://XN--abc.example/`；`https://a.Xn--b.example/`（第二個 label 混大小寫）；`https://sub.xn--x.example.org/`；每個列另有一個合規對照列；`socket.getaddrinfo` 與 `socket.create_connection` 以替身包住（被呼叫即記錄並使測試失敗）
  When 對含該列的來源表位元組呼叫 `sources.validate_table(raw, policy)`；再對一份只含 `https://１２７.0.0.1/x` 的表在 repo 內寫成來源表後 `MJ(check)`
  Then 每個壞列回傳恰含碼 `SRC-URL-HOST`、subject 為該列、detail 含字樣`非 ASCII 或 IDNA 形態`；合規對照列無此碼；`MJ(check)` 的 `research.sources` 為 `FAIL`、碼 `SRC-URL-HOST`、整體 rc 為 `1`
  And `getaddrinfo` 與 `create_connection` 的替身一次都沒被呼叫（判準只看 host 字串：`https://１２７.0.0.1/x` 是因 ASCII 規則被拒、不是因它會解析到 loopback；也沒有任何正規化後再比對）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_230_2_E_1]"
```

```gherkin
# AT-230-2-E-2
# 對應 AC: AC-230-2（PRD AC-SI-30-2 的 P2 收口；R101）`research --fetch` 在發出任何請求之前先過表驗證：含非 ASCII host 的表使整次 rc 1、不抓、不寫事件、零連線（即使表內另有合規的 loopback 來源）
# 測試類型: Integration
# 自動化工具: pytest + 本機 HTTP 夾具（只綁 loopback）+ tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_230_2_E_2_ -q -p no:xdist -o addopts=

Feature: research --fetch 的前置驗證

Scenario: 壞 host 使整批不抓，零連線
  Given `R` 與已 `run-open` 的運轉；P1 夾具 `serve` 起的 loopback 夾具 `srv`（路由 `/ok` 回 200 與一段文字）；來源表兩列：合規的 loopback 來源（`srv` 的 `/ok`，在 P1 夾具 `relaxed()` 放寬私網下合規）與壞列 `https://１２７.0.0.1/x`；`ev0＝事件帳本位元組`、`snap0＝snap(R)`
  When 呼叫 `M(R, research, --fetch, --run, <RUN>)`；再把壞列拿掉後同一呼叫（對照組）
  Then 第一次 rc 為 `1`、碼含 `SRC-URL-HOST`；`srv.requests` 的長度為 `0`（零連線，包含合規列也沒被抓）；事件帳本位元組等於 `ev0`、`snap(R)` 等於 `snap0`；stdout 末尾為 `obs-draft:` 加恰一行草稿列
  And 對照組 rc 為 `0`、`srv.requests` 的長度大於 `0`、事件帳本多一筆 `research.scan`（證明拒收來自壞列、不是夾具壞了）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_230_2_E_2]"
```

```gherkin
# AT-240-10-1
# 對應 AC: AC-240-10（本檔自增；OBS-SI-218；R103）`scan` 的資訊型草稿列與來源行：模組桶候選列為 `process`／`P4`／`decided：僅計數`、缺陷候選列維持 `bug`／`P3`／`open`、三個計數來源的來源行改「計 N 筆（未解析內容）」、JSON 不變
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_240_10_1_ -q -p no:xdist -o addopts=

Feature: scan 的資訊型草稿列

Scenario: 兩種候選各用規定的分類，來源行文字依來源而異
  Given `R`：起算點由 `--since <commit>` 指定；窗內有兩個模組桶被 commit 觸及（`AutoClaude/x.py` 與 `docs/notes/demo.md`）；缺陷帳本新立一個 P2 未結列；`build/reports/r.xml` 與 `misstep_attribution_1.jsonl` 各一個；OBS 帳本在窗內有列；事件帳本不存在
  When 呼叫 `M(R, scan, --since, <commit>)` 與 `MJ(R, scan, --since, <commit>)`；把全部候選列附加到 OBS 帳本副本後 `MJ(check)`
  Then 文字形態：`observations`、`build_reports`、`probe_outputs` 三行為 `source <id> 計 <N> 筆（未解析內容）`，`defects` 為 `source defects 讀到 <N> 筆`，`event_ledger` 為 `source event_ledger 量不到：carrier-not-established`；`candidates:` 之下：兩個模組桶候選列的分類欄為 `process`、嚴重度欄為 `P4`、處置欄為 `decided：僅計數`，標記為 `面=流程;來源=工具;回報者=scan`；缺陷候選列的分類、嚴重度、處置為 `bug`、`P3`、`open`
  And `--json`：`sources[]` 的鍵集合與值與 P1 相同（只有文字形態改，沒有新鍵）、`candidates[]` 每筆為 `{bucket, row}`、`status` 為 `candidates`；所有候選列附加到帳本副本後 `check` 對這些列零 finding（`decided：僅計數` 滿足 P0 的處置附加文字規則），每列位元組數小於等於 `row_max_bytes`
  And 沒有任何模組桶候選列的處置為 `open`（資訊不再冒充待辦缺陷）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_10_1]"
```

```gherkin
# AT-240-10-E-1
# 對應 AC: AC-240-10（本檔自增；R103；P1 R28 (d)、R59 (e)）P1 的拒收草稿列與 `check` 草稿列維持 `bug`／`P3`／`open`；`status` 的候選與桶計數、零候選規則不變；失敗草稿列不被資訊型規則波及
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_research_scan.py -k AT_240_10_E_1_ -q -p no:xdist -o addopts=

Feature: 草稿列的預設值不變

Scenario: 只有資訊型候選改類，其餘草稿列照舊
  Given `R`；一個被拒收的 `prop-new`（任一 P1 拒收碼）；一個被拒收的 `sandbox`（`STATE-NOT-APPROVED`）；`check` 在某條 FAIL 時的草稿列；一份零候選的 `scan` 情境（窗內無 commit、無 P≤2 缺陷）與一份來源量不到的情境
  When 取各拒收輸出的草稿列；呼叫 `scan`（零候選、量不到各一）；`MJ(status)` 於有資訊型候選的情境取 `candidates` 與 `buckets`
  Then 所有拒收與 `check` 草稿列的分類、嚴重度、處置為 `bug`、`P3`、`open`（`rows.draft_row` 的預設值未變）；零候選時文字末行為 `無事件`、JSON 的 `status` 為 `no-event`；任一來源量不到時末行為 `無事件（<K> 個來源量不到）`（不印成通過）
  And 有資訊型候選時，`status` 的 `candidates` 與 `buckets` 計數與 P1 相同（資訊型草稿列仍是候選、照常計入；只改其分類）；來源行的 `量不到：<原因>` 文字不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_10_E_1]"
```


**I. 能力登記、AT 錨定規則、SOP 流程型條文與零退化（CP、MT）**

```gherkin
# AT-240-5-1
# 對應 AC: AC-240-5（本檔自增；PRD §9.4〈能力登記與純度判準〉P2 擴充；R105）能力登記正控：40 鍵四類（29 `ro`／7 `rw`／2 `net`／2 `exec`）、`exec` 恰兩檔、`subprocess` 字樣只在 `git.py` 與 `runner.py`、import `runner` 者為 `exec`、唯讀動詞閉包全 `ro`、平台守衛站點
# 測試類型: Unit
# 自動化工具: pytest／unittest + `ast` 掃描真套件（唯讀）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_240_5_1_ -q -p no:xdist -o addopts=

Feature: 能力登記第四類 exec

Scenario: 真套件通過 R105 的全部判準
  Given 真 repo 的 `tools/lib/selfimproving/*.py`（唯讀）與測試檔內的 `CAPABILITY` 登記表；判準函式 `capability_problems(pkg_root, registry)`（R105 的 ①②②′③④ 與平台守衛站點，§5.6）
  When 對真套件呼叫 `capability_problems`；計 `CAPABILITY` 的鍵數與各類計數；列舉各類成員；以 `ast` 取 `check.py`、`status.py`、`scan.py`、`export.py`、`card.py` 的相對 import 閉包；掃描 `subprocess` 字樣、`taskkill` 與 `os.killpg` 站點、四個禁字樣
  Then 問題清單為空；`CAPABILITY` 恰 40 鍵、四類計數為 29、7、2、2；`exec` 成員恰為 `runner.py` 與 `verify.py`；P2 十六個新模組的登記依序為：`ro`＝`transcript`、`decgrammar`、`decverify`、`cooldown`、`heldout`、`manifest`、`verdict`、`consoleaudit`、`obsrows`、`decheck`；`rw`＝`decwrite`、`sandbox`、`promote`、`obswrite`；`exec`＝`runner`、`verify`
  And 五支唯讀入口檔的相對 import 閉包 ⊆ `ro` 類；出現字樣 `subprocess` 的檔恰為 `git.py` 與 `runner.py`；相對 import `runner` 的檔恰為 `verify.py` 且其登記為 `exec`；`runner.py` 與全部其他檔皆無字樣 `time.sleep`、`while True`、`os.fork`、`signal.alarm`
  And `runner.py` 內每個 `taskkill` 字面與每個 `os.killpg` 呼叫都落在 `sys.platform` 守衛作用域內（`if` 條件含 `sys.platform`）；Windows 的 `creationflags` 以 `getattr(subprocess, 常數名, 0)` 兜底傳入、不直接取用 `subprocess.CREATE_NEW_PROCESS_GROUP` 屬性
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_5_1]"
```

```gherkin
# AT-240-5-E-1
# 對應 AC: AC-240-5（本檔自增；R105）能力登記判準有牙：對真套件的 tmp 副本逐項注入違規，`capability_problems` 各回對應問題；未動的副本為空
# 測試類型: Unit
# 自動化工具: pytest／unittest（tmp 內的套件副本 + `ast`）
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_240_5_E_1_ -q -p no:xdist -o addopts=

Feature: 能力登記的自證

Scenario: 十一個違規注入各被命中，未注入的副本通過
  Given tmp 內以 `shutil.copytree` 複製的真套件（十一份獨立副本與一份未動的對照副本）與同一份 `CAPABILITY`；注入表：(a) 新增未登記的 `newmod.py`；(b) 在 `manifest.py`（`ro`）加入 `import subprocess`；(c) 在 `decverify.py`（`ro`）加入對 `runner` 的相對 import；(d) 在 `promote.py`（`rw`）加入對 `runner` 的相對 import；(e) 在 `check.py` 加入對 `sandbox`（`rw`）的相對 import；(f) 在 `runner.py`（`exec`）加入 `import urllib.request`；(g) 在 `runner.py` 加入 `time.sleep(1)`；(h) 在 `verify.py` 加入 `while True:`；(i) 把 `runner.py` 的 `taskkill` 呼叫移出 `sys.platform` 守衛（改為無條件）；(j) 把 `os.killpg` 呼叫移出守衛；(k) 把 `CAPABILITY` 的 `verify.py` 改登記為 `rw`（原始碼不動）
  When 對各副本呼叫 `capability_problems`
  Then 對照副本回空清單；(a) 回一筆點名 `newmod.py` 的`未登記`問題；(b) 回 `manifest.py` 的`ro` 檔不得 import `subprocess`；(c)(d) 各回import `runner` 者須為 `exec`並點名檔案；(e) 回 `check.py` 的 import 閉包含非 `ro` 模組；(f) 回 `runner.py` 的`exec` 檔不得 import 網路模組；(g)(h) 各回禁字樣並點名檔案與字樣；(i)(j) 各回平台專屬呼叫須在 `sys.platform` 守衛內並點名站點；(k) 回 `verify.py` 的import `runner` 者須為 `exec`
  And 每個問題的回傳都含檔名與違反的判準編號（①～④ 或 ②′）；每個注入至少被其預期的判準命中（連帶命中其他相關判準者不視為錯，例如 (c) 因 `decverify` 在 `check.py` 的 import 閉包內而同時違反 ②′ 與 ③）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_5_E_1]"
```

```gherkin
# AT-240-5-E-2
# 對應 AC: AC-240-5（本檔自增；R87 (a)(c)(e)、R105；NFR-P2-3）子行程出口的靜態不變量與根層平台守衛：`shell=False`、`communicate(timeout=…)`、不帶 `-I`／`-P`、無禁字樣；根層三個平台守衛測試類別與兩張債表不因 P2 新增任何項目
# 測試類型: Integration
# 自動化工具: pytest／unittest + `ast` + 程式化載入根層測試類別
# 判定指令: python -m pytest tools/tests/test_selfimproving_capability.py -k AT_240_5_E_2_ -q -p no:xdist -o addopts=

Feature: 子行程出口的靜態不變量

Scenario: runner 的結構與根層平台守衛皆維持綠
  Given 真套件的 `runner.py` 與 `verify.py`（唯讀）；根層 `tools/tests/test_platform_neutral_paths.py` 的三個類別 `TestForeignExecutableArgvIsGuarded`、`TestForeignPlatformApiIsGuarded`、`TestForeignApiVocabularyOnlyGrows` 與兩張債表 `_FOREIGN_EXE_ARGV_DEBT`、`_FOREIGN_API_SCOPE_DEBT`
  When 以 `ast` 檢查 `runner.py`：所有 `subprocess.Popen` 呼叫的 `shell` 關鍵字、`communicate` 呼叫的 `timeout` 關鍵字、全部字串字面；以 `unittest.TestLoader().loadTestsFromName` 載入根層三個類別並以 `TextTestRunner` 執行；讀兩張債表的鍵
  Then `runner.py` 中每個 `Popen` 的 `shell` 為 `False`（或未給且預設為 `False`）、至少一處 `communicate` 帶 `timeout` 關鍵字；`runner.py` 與 `verify.py` 的字串字面不含獨立的 `-I` 與 `-P` 引數（`PYTHONPATH` 遮蔽須生效，R87 (a)）；環境白名單建構不含 `os.environ` 的整體複製（無 `dict(os.environ)`、`os.environ.copy()`）
  And 根層三個類別的結果 `wasSuccessful()` 為真；兩張債表的鍵中沒有含 `selfimproving` 的條目（P2 沒有新增存量債）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_5_E_2]"
```

```gherkin
# AT-240-9-1
# 對應 AC: AC-240-9（本檔自增；P1 TCS 勘誤四殘留；R102）AT 序號與 `-k` 錨定規則的可重跑檢查正控：本檔每個 AT 的 `-k` 以節點 id 子字串比對恰命中一個測試函式
# 測試類型: Integration
# 自動化工具: pytest + 子行程 `pytest --collect-only`（唯讀）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_9_1_ -q -p no:xdist -o addopts=

Feature: AT 錨定規則的可重跑檢查

Scenario: 全部 AT 的判定指令各命中恰一個函式
  Given 真 repo 的 `docs/03_testing/contracts/TCS-SelfImproving-P2-*.md`（以 glob 取唯一一份，唯讀）；解析器 `parse_at_headers(tcs_text)`（取 §2 每個 AT 標頭的 AT id 與判定指令中的測試檔、`-k` 值）；`anchor_problems(ats, collected)`（R102 (c)(d)(e)，§5.6）；對判定指令涉及的每個測試檔跑一次 `python -m pytest --collect-only -q -p no:xdist -o addopts=` 取節點 id 全集
  When 解析本檔並收集；對每個 AT 以「節點 id 全字串的不分大小寫子字串」數命中（沿 pytest `-k` 對檔名、類別名、函式名的比對）
  Then 解析出的 AT 數等於 §1 映射表的 AT 數（解析器沒有漏掉任何 AT）；`anchor_problems` 回空清單：每個 AT 的 `-k` 值恰命中 1 個節點、以 `_` 結尾、去掉結尾底線後等於其 AT 底線形；同一 AC 的兩位序號 AT 與其個位前綴 AT 互不命中
  And 每個測試函式名的形態為 `test_<AT 底線形>_<slug>`，slug 為非空的小寫英數底線字串；沒有任何一個函式被兩個 AT 命中
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_9_1]"
```

```gherkin
# AT-240-9-E-1
# 對應 AC: AC-240-9（本檔自增；R102 (f)）錨定檢查有牙：以合成測試檔證明「非錨定 `-k` 命中兩個」「無結尾底線」「值與 AT id 不符」「零命中」「重複命中」「缺 slug」各被判紅，錨定形判綠
# 測試類型: Integration
# 自動化工具: pytest + tmp 內的合成測試檔 + 子行程 `pytest --collect-only`
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_9_E_1_ -q -p no:xdist -o addopts=

Feature: 錨定檢查的自證

Scenario: 合成情境中每個違規被判紅
  Given tmp 內的合成測試檔，其測試函式名為 `test_AT_999_1_E_1_alpha`、`test_AT_999_1_E_10_beta`、`test_AT_999_2_1_gamma`、`test_AT_999_3_1`（缺 slug）；合成 AT 清單：(a) `AT_999_1_E_1`（-k 為 `AT_999_1_E_1`，無結尾底線）；(b) 同 AT 的 -k 為 `AT_999_1_E_1_`（錨定）；(c) `AT_999_1_E_10` 的 -k 為 `AT_999_1_E_10_`；(d) `AT_999_2_1` 的 -k 為 `AT_999_2_2_`（與 AT id 不符）；(e) `AT_999_4_1` 的 -k 為 `AT_999_4_1_`（零命中）；(f) 兩個 AT 的 -k 同為 `AT_999_2_1_`（兩 AT 命中同一函式）；(g) `AT_999_3_1` 的 -k 為 `AT_999_3_1_`（函式缺 slug，錨定形零命中）
  When 對合成測試檔執行 `pytest --collect-only` 取節點 id；對各列呼叫 `anchor_problems`
  Then (a) 命中 2 個節點（`E_1` 與 `E_10`）、被判紅且指出`非錨定`；(b)(c) 各命中恰 1 個、判綠；(d) 判紅（-k 去底線後不等於 AT 底線形）；(e) 判紅（零命中）；(f) 判紅（同一函式被兩個 AT 命中）；(g) 判紅（零命中並指出函式名缺 slug）
  And 同一組函式名以非錨定 `-k` 值 `AT_999_1_E_1` 直接對 pytest 執行 `--collect-only -k`，收到 2 個節點（證明錨定規則所防的碰撞確實存在，不是假想）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_9_E_1]"
```

```gherkin
# AT-240-13-1
# 對應 AC: AC-240-13（本檔自增；PRD §8.1 P2 出口 (g)、C.2 #20 (k)、OBS-SI-214；R108）Operations SOP〈P2 動詞〉定稿的正控：標題無「待補」、rc 契約表九列、最小序列、Console 載體、審查者、R-9.6、證據條文、流程摩擦時點
# 測試類型: Unit
# 自動化工具: pytest／unittest（讀 SOP 文字；沿 P1 夾具的切段與圍欄外取行函式）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_13_1_ -q -p no:xdist -o addopts=

Feature: SOP 的 P2 動詞節

Scenario: 真 SOP 滿足 §5.6 的必備片段清單
  Given 真 repo 的 `docs/05_development/SelfImproving_Operations_SOP.md`（唯讀）；§5.6 的 SOP-P2-REQ 清單（逐項＝（所在節關鍵詞、同一行必含的片段集合）；沿 P1 夾具的 `sop_sections`、`sop_section`、`lines_outside_fences`、`line_has_all`）；判準函式 `sop_p2_problems(text)`
  When 對真 SOP 呼叫 `sop_p2_problems`
  Then 回空清單，即：〈P2 動詞〉節存在且標題與內文不含`待補`字樣、不含`呼叫它們一律 rc 3`一句；rc 契約表含 `decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`card --issue`、`obs-add`、`obs-close` 九列且各列含 rc 0、rc 1、rc 3 與下一步；`verify` 列含`rc 0 不論 verdict``讀 verdict 不讀 rc``VERIFY-RUNS-EXCEEDED``升級人工`；`sandbox` 列含`rc 0 涵蓋 applied=false`
  And 最小序列依序含 `card --issue`、`decide`、`heldout-freeze`、`sandbox`、`verify`、`decide --kind promote`、`promote`、commit 訊息引 DEC-ID，並註明不寫引言、不寫 `--reason``凍結者≠提案者``PASS 用前式、NE 用未驗採納式`；回滾僅在掌舵者打字`回滾`後以 `decide --kind rollback` 與 `rollback` 執行；PowerShell 與 bash 兩形態各有；Console 條文含 `decide --carrier console`、`obs-add`、`obs-close`、`主機端``單窗口`、`AUTOSDD_UNATTENDED`；流程摩擦時點含`SCG-4 收尾前`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_13_1]"
```

```gherkin
# AT-240-13-E-1
# 對應 AC: AC-240-13（本檔自增；R108）SOP 判準有牙：對真 SOP 的副本逐項刪去必備片段，`sop_p2_problems` 各點名該項；條文只放在程式碼圍欄內不算數；序列順序對調被判紅；「待補」復現被判紅
# 測試類型: Unit
# 自動化工具: pytest／unittest（SOP 文字的副本編修）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_13_E_1_ -q -p no:xdist -o addopts=

Feature: SOP 判準的自證

Scenario: 逐項刪去與變形各被判紅，且只點名該項
  Given 真 SOP 文字 `T`（唯讀）與 §5.6 SOP-P2-REQ 清單的每一項；變形：(a) 對每個必備片段，以 `remove_in_section` 自 `T` 的副本刪去該片段；(b) 把〈審查者〉條文整段移入程式碼圍欄；(c) 對調最小序列中 `heldout-freeze` 與 `sandbox` 的先後；(d) 在標題補回「（待補）」；(e) 補回「呼叫它們一律 rc 3」一句；(f) 把「SCG-4 收尾前」改回「SCG-4 前」；(g) 把 `verify` 列的「rc 0 不論 verdict」改為「rc 0 表示通過」
  When 對 `T` 與各副本呼叫 `sop_p2_problems`
  Then `T` 回空清單；(a) 每個副本回非空清單且點名被刪的那一項（一項一個問題，不連帶其他項）；(b) 回〈審查者〉項問題；(c) 回序列順序問題；(d)(e) 各回對應問題；(f) 回流程摩擦時點項問題；(g) 回 `verify` 列問題
  And 刪去的項數等於 SOP-P2-REQ 的項數（判準逐項有牙，沒有空轉的項目）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_13_E_1]"
```

```gherkin
# AT-218-1-1
# 對應 AC: AC-218-1（PRD AC-SI-18-1；R108 (d)；流程型 P，以 SOP 條文代位）審查者條文正控：SOP〈審查者〉節含四項流程條文；機器能守的那一半（審查者≠提案者、凍結者≠提案者）在合法分工下受理
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_218_1_1_ -q -p no:xdist -o addopts=

Feature: 審查者與提案者分離

Scenario: SOP 條文在場，合法分工被受理
  Given 真 SOP（唯讀）；`R` 與已 `run-open` 的運轉；合法的 `prop-new` 參數：`--proposer SA --reviewer RV`；一個已核准的 PROP 與 `FZ` 為凍結者
  When 對真 SOP 以 §5.6 的〈審查者〉項判準取片段；呼叫 `prop-new`（提案者 `SA`、審查者 `RV`）；呼叫 `heldout-freeze --by FZ`
  Then SOP〈審查者〉節（圍欄外）含：`審查者≠提案者`且`不同代理實例與不同 context`、`全程唯讀`、`不自起背景長任務`、`主依據為外部可重跑訊號`且`LLM 意見不得單獨把 FAIL 改成 PASS`；`prop-new` rc 為 `0`、事件 `reviewer` 為 `RV`、`proposer` 為 `SA`；`heldout-freeze` rc 為 `0`、`frozen_by` 為 `FZ`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_218_1_1]"
```

```gherkin
# AT-218-1-E-1
# 對應 AC: AC-218-1（PRD AC-SI-18-1；R108 (d)；P1 `REVIEWER-IS-PROPOSER`、R83）審查者條文的負控：機器守的一半被擋（審查者等於提案者、凍結者等於提案者）；條文逐項刪去被判紅
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_218_1_E_1_ -q -p no:xdist -o addopts=

Feature: 審查者分離的負控

Scenario: 角色重疊被拒、條文缺項被判紅
  Given `R`、已 `run-open` 的運轉；`snap0＝snap(R)`；已核准的 PROP `P`（`proposer` 為 `SA`）；真 SOP 的副本與〈審查者〉節的五個必備片段
  When 呼叫 `prop-new`（`--proposer SA --reviewer SA`）；呼叫 `heldout-freeze P --from <目錄> --by SA`；對 SOP 副本逐一刪去五個片段並呼叫 `sop_p2_problems`
  Then 第一個呼叫 rc 為 `1`、碼含 `REVIEWER-IS-PROPOSER`；第二個 rc 為 `1`、碼含 `FROZEN-BY-PROPOSER`；兩者零寫入（`snap(R)` 等於 `snap0`）；SOP 副本每刪一個片段各得一個點名該片段的問題
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_218_1_E_1]"
```

```gherkin
# AT-215-3-1
# 對應 AC: AC-215-3（PRD AC-SI-15-3；R108 (e)；流程型 P，以 SOP 條文代位）遇 R-9.6 擋寫或 harness 分類器拒絕時不得繞過：SOP 條文在場；機器守的一半——觸及 `.claude/**` 的提案不進採納流程
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_215_3_1_ -q -p no:xdist -o addopts=

Feature: 不得繞過擋寫

Scenario: 條文在場，且觸及守衛面的 PROP 只能轉交
  Given 真 SOP（唯讀）；`R` 與一個 patch 觸及 `.claude/settings.json` 的 PROP `PG`（`prop-new` 時 P1 判為 `handoff:T1`；`--handoff T1`）
  When 對真 SOP 取〈P2 動詞〉節（圍欄外）；對 `PG` 呼叫 `decide`（逐字稿載體，引言 `核准 <PG>`）、`ack-handoff` 形態的 `decide`（引言 `轉交 <PG>`）
  Then SOP 含`遇 R-9.6 擋寫或 harness 分類器拒絕``不得以改派子代理或換路徑繞過``改由符合條件的視窗處理或走轉交`三個片段於同一條文；`PG` 的 `核准` rc 為 `1`、碼 `ROUTE-HANDOFF`；`轉交` rc 為 `0`（`PG` 態為 `handed-off`，由掌舵者經 T1 處理）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_3_1]"
```

```gherkin
# AT-215-3-E-1
# 對應 AC: AC-215-3（PRD AC-SI-15-3；R91 `NON-EVOLVABLE-NOW`、R108 (e)）即使核准當時的規則較寬而使提案走 loop 路由，`promote` 也以當下規則重驗而不寫守衛面（`.claude/**`）；SOP 條文逐項刪去被判紅
# 測試類型: Integration
# 自動化工具: pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_215_3_E_1_ -q -p no:xdist -o addopts=

Feature: 守衛面不被繞寫

Scenario: 較寬規則下核准的守衛面提案仍被晉升前的當下重驗擋下
  Given `R`；先把 `params.json` 的 `non_evolvable_globs` 暫時移除 `**/.claude/**`（模擬核准當時較寬的規則）；`PF＝drive_to(R, verified, action=add, target=.claude/hooks/new_guard.py)`（此時 `prop-new` 導出 `route` 為 `loop`，其後 `approve`、`heldout-freeze`、`sandbox`、`verify` 皆以真動作完成，並以 `decide_say` 受理前式 `晉升`）；其後還原 `params.json`（`**/.claude/**` 回到清單）；`snap0＝snap(R)`
  When 呼叫 `M(R, promote, PF)`；對 SOP 副本逐一刪去三個條文片段並呼叫 `sop_p2_problems`
  Then `promote` rc 為 `1`、碼含 `NON-EVOLVABLE-NOW`（detail 點名 `.claude/hooks/new_guard.py` 與 glob `**/.claude/**`）；`snap(R)` 等於 `snap0`（守衛面檔案不被寫、不存在）；SOP 副本每刪一個片段各得一個點名該片段的問題
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_215_3_E_1]"
```

```gherkin
# AT-221-2-1
# 對應 AC: AC-221-2（PRD AC-SI-21-2；R108 (f)；流程型 P，以 SOP 條文代位）證據條文正控：SOP 含逐字入帳、轉述標記、親跑升格、貼不出改寫四項；機器守的一半——驗證證據含執行者與帶 offset 的時間
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_221_2_1_ -q -p no:xdist -o addopts=

Feature: 證據條文

Scenario: SOP 條文在場，驗證事件帶執行者與時間
  Given 真 SOP（唯讀）；`R` 與 `P＝drive_to(R, sandboxed)`
  When 對真 SOP 取〈P2 動詞〉節（圍欄外）；呼叫 `MJ(R, verify, P, --by, VF1)`
  Then SOP 含四個片段：`逐字入帳`且列出`指令``rc``out_sha256``out_bytes``遮蔽末段`；`[他包回報]`；`主控親跑後才升格為已驗證`；`貼不出輸出者改寫為未驗證`；`app.verify` 事件的 `by` 為 `VF1`、`t` 帶 offset 且秒精度；`verify1.json` 的每筆 `rec` 含 `cmd`、`rc`、`out_sha256`、`out_bytes`、`tail`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_221_2_1]"
```

```gherkin
# AT-221-2-E-1
# 對應 AC: AC-221-2（PRD AC-SI-21-2；R108 (f)）證據條文有牙：逐項刪去或移入圍欄被判紅；`verify` 的非 PASS 結果不被靜默吞掉（草稿列與 verdict 並列）
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_221_2_E_1_ -q -p no:xdist -o addopts=

Feature: 證據條文的負控

Scenario: 條文缺項被判紅，非 PASS 結果必有可入帳的草稿
  Given 真 SOP 的副本與四個證據條文片段；`R` 與 NE 的 PROP（held-out 的 `probes` 為空，`NO-PROBES`）
  When 對 SOP 副本逐一刪去四個片段、再把整段移入程式碼圍欄後呼叫 `sop_p2_problems`；呼叫 `MJ(R, verify, P)` 並讀其 stdout
  Then 每刪一個片段得一個點名該片段的問題；整段移入圍欄得`條文不在圍欄外`問題；`verify` 的 verdict 為 `NE`、stdout 末尾為 `obs-draft:` 加恰一行草稿列（NE 不是綠、不被吞掉）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_221_2_E_1]"
```

```gherkin
# AT-240-14-1
# 對應 AC: AC-240-14（本檔自增；PRD §8.1 P2 出口 (f)；R107、R109）零退化正控：升級後夾具重放全部 P1 情境表皆合規；P0 與 P1 的全部 AT 在測試檔中各有對應函式（P1 斷言值只於 R107 (c) 列出的站點同步，含 R104、R110 造成的兩處）；`params` 規格為 28 加 2 鍵
# 測試類型: Integration
# 自動化工具: pytest + tmp 目錄 + 真 git（hermetic）+ 唯讀解析 P0／P1 TCS
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_14_1_ -q -p no:xdist -o addopts=

Feature: 零退化

Scenario: P1 情境重放、AT 覆蓋與參數規格
  Given 升級後的 `_selfimproving_fixtures.py`；P1 情境建構器 `sc_close`、`sc_seq`、`sc_legal`、`sc_rev`、`sc_susp`；真 repo 的 P0 TCS 與 P1 TCS（唯讀；以 glob 取 `TCS-SelfImproving-P0-*.md`、`TCS-SelfImproving-P1-*.md`）；測試函式名的搜尋面＝`tools/tests/*.py` 加 `AutoClaude/tests/contract/test_evolution_propose_only.py`（P1 鍵 B 的 AT-128 系列住在後者）；`params` 規格 `PARAM_SPECS`
  When 對五個情境各 `write_events` 後呼叫 `MJ(check)` 與 `fold.fold`；自兩份 TCS 解析全部 AT id（P0 為 42 個、P1 為 163 個）；列舉 `PARAM_SPECS` 的鍵；取夾具 `params_dict()` 的 `non_evolvable_globs` 與 `spec_body_globs`
  Then 五個情境的 `events.structure` 皆為 `PASS`、`events.transitions` 皆無 `TRANSITION-ILLEGAL` 與 `TRANSITION-ORPHAN`、`fold` 的 `problems` 為空清單（`sc_susp` 另折出 `suspended`）；P0 與 P1 的 205 個 AT id 在搜尋面的測試函式名中各有至少一個以其底線形為子字串的函式（沒有任何 AT 被刪或被改名）
  And `PARAM_SPECS` 的鍵集合恰為 P1 的 28 鍵（§5.6 逐字列出）加 `probe_timeout_seconds` 與 `verify_runs_max`；夾具 `params_dict()` 的 `non_evolvable_globs` 與 `spec_body_globs` 逐項等於 §5.6 逐字列出的 P1 清單（18 項與 3 項；P2 不改這兩份清單，夾具被誤改即紅）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_14_1]"
```

```gherkin
# AT-240-14-E-1
# 對應 AC: AC-240-14（本檔自增；R107 (a)）夾具升級不吞掉違規：呼叫端明示的錯誤值不被預設值覆蓋，P1 的負控事件在升級後仍被同一個碼擋下
# 測試類型: Unit
# 自動化工具: pytest（純函式加夾具）
# 判定指令: python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_14_E_1_ -q -p no:xdist -o addopts=

Feature: 夾具升級的負控

Scenario: 明示的錯誤值保持錯誤
  Given 升級後的 `dec_ev`、`_verify`、`ev`、`compose`；負控呼叫（每列一個）：`dec_ev(n, approve, digest=壞值)`；`dec_ev(n, promote, flags=[x])`；`dec_ev(n, reject)` 且 `reason_class` 為 `隨便`；`ev(app.sandbox, main, prop=…, applied=True, touched_ok=None)`；`ev(app.verify, main, prop=…, verdict=PASS, reasons=[BASELINE-NOT-RED])`；`ev(card, main, prop=…, rev=0)`；`ev(app.promote, main, prop=…, commit_sha=<40 位 hex>)`；`ev(heldout.freeze, main, prop=…, n=0)`
  When 各經 `compose()` 取得事件後呼叫 `events.validate`
  Then 每個事件回傳至少一個碼，依序為 `EVENT-TYPE`、`EVENT-TYPE`（`flags` 元素不在 `unverified_ack`）、`EVENT-TYPE`、`EVENT-TYPE`（`applied` 真而 `touched_ok` 為 `null`）、`EVENT-TYPE`（PASS 而 `reasons` 非空）、`EVENT-TYPE`、`EVENT-KEY-UNKNOWN`、`EVENT-TYPE`；預設值只補呼叫端沒給的鍵（呼叫端給了的值逐位元保留）
  And 同一組鍵若呼叫端不給（只給最少欄位的 P1 形態，如 `dec_ev(n, approve)`），`validate` 回空清單（升級的目的：最少欄位的合法事件仍合法）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_240_14_E_1]"
```

---

## 3. AT 完整清單

> 本節是依測試類型的閱讀索引（AT 的權威清單是 §1；兩處清單由同一份登錄自動產生、不手工維護）。測試方法欄為測試函式名的樣式，函式名須含 AT 底線形（錨定規則見 R102）。

### 3.1 Unit Tests

| AT ID | 對應 AC | 測試檔 | 測試方法 | 自動化工具 |
|-------|---------|--------|---------|-----------|
| AT-212-1-3 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_3_* | pytest（純函式） |
| AT-212-1-E-1 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_E_1_* | pytest（純函式） |
| AT-215-1-E-4 | AC-215-1 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_1_E_4_* | pytest（合成 tar，不經 git） |
| AT-215-2-E-1 | AC-215-2 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_2_E_1_* | pytest（合成原始碼） |
| AT-219-2-1 | AC-219-2 | tools/tests/test_selfimproving_verify.py | test_AT_219_2_1_* | pytest（純函式；加一個 `probes` 為空的 `verify` 實跑） |
| AT-230-2-1 | AC-230-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_230_2_1_* | pytest（純函式加唯讀真來源表） |
| AT-230-2-E-1 | AC-230-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_230_2_E_1_* | pytest（純函式；替身 `socket.getaddrinfo`） |
| AT-233-1-2 | AC-233-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_1_2_* | pytest（純標準庫） |
| AT-240-1-1 | AC-240-1 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_1_1_* | pytest（純函式） |
| AT-240-1-E-1 | AC-240-1 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_1_E_1_* | pytest（純函式） |
| AT-240-5-1 | AC-240-5 | tools/tests/test_selfimproving_capability.py | test_AT_240_5_1_* | pytest／unittest + `ast` 掃描真套件（唯讀） |
| AT-240-5-E-1 | AC-240-5 | tools/tests/test_selfimproving_capability.py | test_AT_240_5_E_1_* | pytest／unittest（tmp 內的套件副本 + `ast`） |
| AT-240-8-1 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_1_* | pytest／unittest + `mock.patch`（任一平台可重現，不靠真實競態） |
| AT-240-8-2 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_2_* | pytest／unittest + `mock.patch` |
| AT-240-8-3 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_3_* | pytest／unittest + `mock.patch` |
| AT-240-8-E-1 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_E_1_* | pytest／unittest + `mock.patch` |
| AT-240-8-E-2 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_E_2_* | pytest／unittest + `mock.patch` |
| AT-240-8-E-3 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_E_3_* | pytest／unittest + `mock.patch` |
| AT-240-13-1 | AC-240-13 | tools/tests/test_selfimproving_p2_meta.py | test_AT_240_13_1_* | pytest／unittest（讀 SOP 文字；沿 P1 夾具的切段與圍欄外取行函式） |
| AT-240-13-E-1 | AC-240-13 | tools/tests/test_selfimproving_p2_meta.py | test_AT_240_13_E_1_* | pytest／unittest（SOP 文字的副本編修） |
| AT-240-14-E-1 | AC-240-14 | tools/tests/test_selfimproving_p2_meta.py | test_AT_240_14_E_1_* | pytest（純函式加夾具） |

### 3.2 Integration Tests

| AT ID | 對應 AC | 測試檔 | 測試方法 | 自動化工具 |
|-------|---------|--------|---------|-----------|
| AT-212-1-1 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-1-2 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-1-E-2 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_E_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-1-E-3 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_E_3_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-1-E-4 | AC-212-1 | tools/tests/test_selfimproving_decide.py | test_AT_212_1_E_4_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-2-1 | AC-212-2 | tools/tests/test_selfimproving_decide.py | test_AT_212_2_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-2-E-1 | AC-212-2 | tools/tests/test_selfimproving_decide.py | test_AT_212_2_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-3-1 | AC-212-3 | tools/tests/test_selfimproving_decide.py | test_AT_212_3_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-3-E-1 | AC-212-3 | tools/tests/test_selfimproving_decide.py | test_AT_212_3_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-4-1 | AC-212-4 | tools/tests/test_selfimproving_decide.py | test_AT_212_4_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-4-E-1 | AC-212-4 | tools/tests/test_selfimproving_decide.py | test_AT_212_4_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-4-E-2 | AC-212-4 | tools/tests/test_selfimproving_decide.py | test_AT_212_4_E_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-4-E-3 | AC-212-4 | tools/tests/test_selfimproving_decide.py | test_AT_212_4_E_3_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-212-4-E-4 | AC-212-4 | tools/tests/test_selfimproving_decide.py | test_AT_212_4_E_4_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-213-1-1 | AC-213-1 | tools/tests/test_selfimproving_decide.py | test_AT_213_1_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-213-1-E-1 | AC-213-1 | tools/tests/test_selfimproving_decide.py | test_AT_213_1_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-213-2-1 | AC-213-2 | tools/tests/test_selfimproving_events_p2.py | test_AT_213_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-213-2-E-1 | AC-213-2 | tools/tests/test_selfimproving_events_p2.py | test_AT_213_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-213-3-1 | AC-213-3 | tools/tests/test_selfimproving_events_p2.py | test_AT_213_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-213-3-E-1 | AC-213-3 | tools/tests/test_selfimproving_events_p2.py | test_AT_213_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-215-1-1 | AC-215-1 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-215-1-2 | AC-215-1 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_1_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-215-1-E-1 | AC-215-1 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-215-1-E-2 | AC-215-1 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_1_E_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-215-1-E-3 | AC-215-1 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_1_E_3_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-215-2-1 | AC-215-2 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_2_1_* | pytest + AST 掃描 + 子行程記錄器 + tmp 目錄 + 真 git（hermetic） |
| AT-215-3-1 | AC-215-3 | tools/tests/test_selfimproving_p2_meta.py | test_AT_215_3_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-215-3-E-1 | AC-215-3 | tools/tests/test_selfimproving_p2_meta.py | test_AT_215_3_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-215-4-1 | AC-215-4 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_4_1_* | pytest + tmp 目錄 + 真 git（hermetic）；替身 `sandbox.apply_patch`、`sandbox.reverse_apply`、`subprocess.run` |
| AT-215-4-E-1 | AC-215-4 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_4_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-215-4-E-2 | AC-215-4 | tools/tests/test_selfimproving_sandbox.py | test_AT_215_4_E_2_* | pytest + tmp 目錄 + 真 git（hermetic）；替身 `subprocess.run` |
| AT-216-1-1 | AC-216-1 | tools/tests/test_selfimproving_promote.py | test_AT_216_1_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-216-1-E-1 | AC-216-1 | tools/tests/test_selfimproving_promote.py | test_AT_216_1_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-216-1-E-2 | AC-216-1 | tools/tests/test_selfimproving_promote.py | test_AT_216_1_E_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-216-2-1 | AC-216-2 | tools/tests/test_selfimproving_promote.py | test_AT_216_2_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-216-2-E-1 | AC-216-2 | tools/tests/test_selfimproving_promote.py | test_AT_216_2_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-216-3-1 | AC-216-3 | tools/tests/test_selfimproving_promote.py | test_AT_216_3_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-216-3-E-1 | AC-216-3 | tools/tests/test_selfimproving_promote.py | test_AT_216_3_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-217-1-1 | AC-217-1 | tools/tests/test_selfimproving_verify.py | test_AT_217_1_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-217-1-E-1 | AC-217-1 | tools/tests/test_selfimproving_verify.py | test_AT_217_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-217-1-E-2 | AC-217-1 | tools/tests/test_selfimproving_verify.py | test_AT_217_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程（含孫行程） |
| AT-217-2-1 | AC-217-2 | tools/tests/test_selfimproving_promote.py | test_AT_217_2_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-217-2-E-1 | AC-217-2 | tools/tests/test_selfimproving_promote.py | test_AT_217_2_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-218-1-1 | AC-218-1 | tools/tests/test_selfimproving_p2_meta.py | test_AT_218_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-218-1-E-1 | AC-218-1 | tools/tests/test_selfimproving_p2_meta.py | test_AT_218_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-218-2-1 | AC-218-2 | tools/tests/test_selfimproving_verify.py | test_AT_218_2_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-218-2-E-1 | AC-218-2 | tools/tests/test_selfimproving_verify.py | test_AT_218_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-219-1-1 | AC-219-1 | tools/tests/test_selfimproving_verify.py | test_AT_219_1_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-219-1-E-1 | AC-219-1 | tools/tests/test_selfimproving_verify.py | test_AT_219_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-219-1-E-2 | AC-219-1 | tools/tests/test_selfimproving_verify.py | test_AT_219_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-219-1-E-3 | AC-219-1 | tools/tests/test_selfimproving_verify.py | test_AT_219_1_E_3_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-219-2-E-1 | AC-219-2 | tools/tests/test_selfimproving_verify.py | test_AT_219_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-219-3-1 | AC-219-3 | tools/tests/test_selfimproving_verify.py | test_AT_219_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-219-3-E-1 | AC-219-3 | tools/tests/test_selfimproving_verify.py | test_AT_219_3_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-220-1-1 | AC-220-1 | tools/tests/test_selfimproving_events_p2.py | test_AT_220_1_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-220-1-E-1 | AC-220-1 | tools/tests/test_selfimproving_events_p2.py | test_AT_220_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-220-1-E-2 | AC-220-1 | tools/tests/test_selfimproving_events_p2.py | test_AT_220_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-220-2-1 | AC-220-2 | tools/tests/test_selfimproving_verify.py | test_AT_220_2_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-220-2-E-1 | AC-220-2 | tools/tests/test_selfimproving_verify.py | test_AT_220_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-220-3-1 | AC-220-3 | tools/tests/test_selfimproving_promote.py | test_AT_220_3_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-220-3-E-1 | AC-220-3 | tools/tests/test_selfimproving_promote.py | test_AT_220_3_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-220-4-1 | AC-220-4 | tools/tests/test_selfimproving_verify.py | test_AT_220_4_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-220-4-E-1 | AC-220-4 | tools/tests/test_selfimproving_verify.py | test_AT_220_4_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-220-4-E-2 | AC-220-4 | tools/tests/test_selfimproving_verify.py | test_AT_220_4_E_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-221-1-1 | AC-221-1 | tools/tests/test_selfimproving_verify.py | test_AT_221_1_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-221-1-E-1 | AC-221-1 | tools/tests/test_selfimproving_verify.py | test_AT_221_1_E_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-221-1-E-2 | AC-221-1 | tools/tests/test_selfimproving_verify.py | test_AT_221_1_E_2_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-221-2-1 | AC-221-2 | tools/tests/test_selfimproving_p2_meta.py | test_AT_221_2_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 本機子行程 |
| AT-221-2-E-1 | AC-221-2 | tools/tests/test_selfimproving_p2_meta.py | test_AT_221_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-230-2-E-2 | AC-230-2 | tools/tests/test_selfimproving_research_scan.py | test_AT_230_2_E_2_* | pytest + 本機 HTTP 夾具（只綁 loopback）+ tmp 目錄 + 真 git（hermetic） |
| AT-233-1-1 | AC-233-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_1_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-233-1-E-1 | AC-233-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_1_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-233-1-E-2 | AC-233-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_1_E_2_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-233-1-E-3 | AC-233-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_1_E_3_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-233-2-1 | AC-233-2 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_2_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-233-2-E-1 | AC-233-2 | tools/tests/test_selfimproving_console_obs.py | test_AT_233_2_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-1-1 | AC-235-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_1_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-1-2 | AC-235-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_1_2_* | pytest + tmp 目錄 + 真 git（hermetic）+ 子行程 `-X importtime` |
| AT-235-1-E-1 | AC-235-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_1_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-1-E-2 | AC-235-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_1_E_2_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic）+ 執行緒 |
| AT-235-1-E-3 | AC-235-1 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_1_E_3_* | pytest + 子行程 `python -X importtime` |
| AT-235-2-1 | AC-235-2 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_2_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-2-E-1 | AC-235-2 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_2_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-2-E-2 | AC-235-2 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_2_E_2_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-3-1 | AC-235-3 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-235-3-E-1 | AC-235-3 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_3_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-4-1 | AC-235-4 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_4_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-4-E-1 | AC-235-4 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_4_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-5-1 | AC-235-5 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_5_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-235-5-E-1 | AC-235-5 | tools/tests/test_selfimproving_console_obs.py | test_AT_235_5_E_1_* | pytest + 合成稽核檔 + tmp 目錄 + 真 git（hermetic） |
| AT-240-1-E-2 | AC-240-1 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_1_E_2_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-240-2-1 | AC-240-2 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_2_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-2-E-1 | AC-240-2 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_2_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-2-E-2 | AC-240-2 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_2_E_2_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-2-E-3 | AC-240-2 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_2_E_3_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-240-3-1 | AC-240-3 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_3_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-3-E-1 | AC-240-3 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_3_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-240-4-1 | AC-240-4 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_4_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-4-E-1 | AC-240-4 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_4_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-5-E-2 | AC-240-5 | tools/tests/test_selfimproving_capability.py | test_AT_240_5_E_2_* | pytest／unittest + `ast` + 程式化載入根層測試類別 |
| AT-240-6-1 | AC-240-6 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_6_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-6-E-1 | AC-240-6 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_6_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-7-1 | AC-240-7 | tools/tests/test_selfimproving_promote.py | test_AT_240_7_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-240-7-E-1 | AC-240-7 | tools/tests/test_selfimproving_promote.py | test_AT_240_7_E_1_* | pytest + 合成逐字稿 + tmp 目錄 + 真 git（hermetic） |
| AT-240-8-E-4 | AC-240-8 | tools/tests/test_apply_lock.py | test_AT_240_8_E_4_* | pytest + tmp 目錄 + 真 git（hermetic）+ `mock.patch` |
| AT-240-9-1 | AC-240-9 | tools/tests/test_selfimproving_p2_meta.py | test_AT_240_9_1_* | pytest + 子行程 `pytest --collect-only`（唯讀） |
| AT-240-9-E-1 | AC-240-9 | tools/tests/test_selfimproving_p2_meta.py | test_AT_240_9_E_1_* | pytest + tmp 內的合成測試檔 + 子行程 `pytest --collect-only` |
| AT-240-10-1 | AC-240-10 | tools/tests/test_selfimproving_research_scan.py | test_AT_240_10_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-10-E-1 | AC-240-10 | tools/tests/test_selfimproving_research_scan.py | test_AT_240_10_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-11-1 | AC-240-11 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_11_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-11-E-1 | AC-240-11 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_11_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-12-1 | AC-240-12 | tools/tests/test_selfimproving_console_obs.py | test_AT_240_12_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-12-E-1 | AC-240-12 | tools/tests/test_selfimproving_console_obs.py | test_AT_240_12_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-14-1 | AC-240-14 | tools/tests/test_selfimproving_p2_meta.py | test_AT_240_14_1_* | pytest + tmp 目錄 + 真 git（hermetic）+ 唯讀解析 P0／P1 TCS |
| AT-240-15-1 | AC-240-15 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_15_1_* | pytest + tmp 目錄 + 真 git（hermetic） |
| AT-240-15-E-1 | AC-240-15 | tools/tests/test_selfimproving_events_p2.py | test_AT_240_15_E_1_* | pytest + tmp 目錄 + 真 git（hermetic） |

### 3.3 Contract Tests

（無；P2 沒有鍵 B 的 AutoClaude 契約測試。）

### 3.4 E2E Tests

（無；P2 出口 (a)(b)(c)(d)(e) 的真實運轉與 (g) 的真機煙霧屬實跑檢核 V8、V9、V10、V15，不入 AT，因為 AT 不碰真帳本與外網。）

---

## 4. 邊界與錯誤測試規格

邊界與錯誤情境以 `AT-<NNN>-<Y>-E-<n>` 命名並已列入 §1；下表是依場景類型的索引（第一欄為場景類型、不是 AC ID）。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|----------|
| 用法錯誤（格式類） | AT-212-1-E-4、AT-233-1-E-2、AT-219-1-E-3、AT-219-3-E-1、AT-216-1-E-1、AT-240-7-E-1、AT-215-1-E-2、AT-235-3-1 | 旗標缺漏、枚舉值不在集合、UUID 與行號形態不合、位置參數不合或兩個、未知旗標與未知動詞、不收的旗標（`--reason`、`--quote`、`--unverified-ack`、`--force`、`--commit`、`--approve`）、`--carrier console` 與 `--kind` 並用 | 見各 AT | rc 3、stdout 空、stderr 以 `selfimproving:` 起頭、零寫入 |
| 狀態類拒收 | AT-212-1-E-3、AT-233-1-E-2、AT-215-1-E-2、AT-219-1-E-3、AT-216-1-E-1、AT-240-7-E-1、AT-220-1-E-1、AT-240-6-E-1、AT-217-2-E-1、AT-213-2-E-1、AT-240-15-E-1 | 態不合、路由不配、式與 verdict 不符、未凍結、未晉升、冷卻中、RUN 不符、`--reopens` 目標為 `open` 列或不存在 | 手寫事件帳本或 CLI 序列 | rc 1、`reject <verb> <碼>`、OBS 草稿列、零殘留 |
| 無人值守 | AT-212-1-E-4、AT-215-1-E-2、AT-219-1-E-3、AT-216-1-E-1、AT-240-7-E-1、AT-220-1-E-1、AT-240-6-E-1、AT-217-2-E-1、AT-233-1-E-2、AT-235-1-E-1、AT-235-2-E-1 | `AUTOSDD_UNATTENDED` 設為 `0` 或 `1`（值非空即算有設） | 環境變數 | rc 1、`UNATTENDED-REFUSED`、先於其餘前置判、零寫入；移除環境變數後同一呼叫成功 |
| 邊界值（事件行位元組） | AT-240-1-E-2 | `event_max_bytes` 恰等於一行 `dec` 的位元組數 L 與 L－1；寫入端與 `check` 端各一 | 自我校準 | L 放行、L－1 `EVENT-BYTES-OVER` |
| 邊界值（OBS 列位元組） | AT-235-1-E-1、AT-235-2-E-1 | 列位元組恰 700 與 701（`row_max_bytes` 為 700） | 自我校準 | 700 放行、701 `ROW-BYTES-OVER` |
| 邊界值（held-out 規模） | AT-220-2-1、AT-220-2-E-1 | `n` 為 5、4、1；`min_heldout` 為 5 與 3 | `make_heldout` 的案例數與 `params.json` | `n` 等於下限放行；小於下限 NE `HELDOUT-TOO-SMALL`；下限隨參數移動 |
| 邊界值（複驗次數） | AT-217-1-1、AT-217-1-E-1 | 同 `(prop, rev)` 的 `app.verify` 第 2 次（`verify_runs_max` 為 2）與第 3 次；`verify_runs_max` 為 1；rev 2 重新計數 | `verify` 與手寫帳本 | 第 2 次受理、第 3 次 `VERIFY-RUNS-EXCEEDED` 且零殘留；`check` 對超限帳本 FAIL |
| 邊界值（探針逾時） | AT-217-1-1、AT-217-1-E-2 | 探針耗時約 1 秒（上限 4 秒）與永遠不結束（上限 2 秒）；掛住發生於基線、套用後、突變後三個步驟 | `probe_slow.py`、`probe_hang*.py` | 上限內完成不被殺；逾時殺行程樹、NE、其後步驟不執行、孫行程不殘留 |
| 邊界值（輸出摘要） | AT-221-1-1、AT-221-1-E-1 | `tail` 恰 300 位元組處落在多位元組字元中；輸出 2,000,000 位元組 | `probe_noisy.py`、`probe_big.py` | `tail` 不超過 300 位元組且無損解碼；`out_bytes` 精確；驗證檔小於 8 KB |
| 邊界值（暴露掃描時間窗） | AT-220-4-1、AT-220-4-E-1 | 含針記錄的頂層時間戳為凍結時刻 `t` 減 1 小時（含同檔 mtime 不早於 `t` 的混合檔）、恰等於 `t`、`t` 加 1 分鐘、缺、值不可解析 | 合成逐字稿（記錄時間戳相對 `t` 於執行期組出） | 早於 `t` 的不計入（PASS，且不依賴檔案 mtime）；恰等於 `t`、晚於 `t`、缺、不可解析一律 `HELDOUT-EXPOSED`（保守） |
| 邊界值（路徑長度） | AT-215-1-E-4 | 模擬 Windows：`len(根)` 加 1 加成員長度恰 259 與 260；模擬 Linux：260 | 合成 tar 與替身 `sys.platform` | 259 通過、260 `SANDBOX-PATH-TOO-LONG`；POSIX 不判 |
| 邊界值（釋放重試） | AT-240-8-3、AT-240-8-E-3 | 釋放時 `unlink` 前 `RELEASE_RETRIES` 次被拒、第 `RELEASE_RETRIES` 加 1 次成功；永遠被拒 | `mock.patch` | 成功者鎖檔刪除且無警告；用盡者不拋、印警告、鎖檔殘留交陳舊回收 |
| 邊界值（附件時序） | AT-212-4-E-1、AT-212-1-2 | 附件打出時刻早於、等於、晚於卡面送達 1 秒；時間戳缺或不可解析 | 合成逐字稿 | 嚴格晚於才受理；等於與早於 `CARD-NOT-DELIVERED`；缺與不可解析 `ATTACHMENT-TIME-UNKNOWN` |
| 邊界值（帳號名） | AT-235-4-1、AT-235-4-E-1 | `user` 為 1、64、65 字元；含 `;`、`=`、空白、`\|`、中文、空字串 | 稽核檔 `body` | 合 `^[A-Za-z0-9_.-]{1,64}$` 者受理；其餘 `AUDIT-USER-FORMAT` |
| 行尾與 BOM | AT-212-4-E-4、AT-215-1-E-3、AT-216-3-1 | 逐字稿的 BOM 與 CRLF；全域 `core.autocrlf` 為真；manifest 的 LF 與 CRLF 版 | 位元組、`GIT_CONFIG_GLOBAL` | 逐字稿容忍；沙盒得 LF 且回滾逐位元還原；LF 正規化式 manifest 兩版相同 |
| 時間（offset） | AT-233-1-E-1、AT-235-1-1、AT-216-3-1、AT-212-1-1 | 稽核檔 `time` 為 `Z`、無 offset、帶小數秒；列的 `時間` 保留 offset 丟秒；事件 `t`、`decided_at` 帶 offset | 稽核檔、CLI 輸出 | 不帶明示 offset 者 `AUDIT-TIME-FORMAT`；寫入側零 naive |
| 併發與競態 | AT-235-1-E-2、AT-240-8-1、AT-240-8-2、AT-240-8-E-1、AT-240-8-E-2、AT-240-8-E-3、AT-240-8-E-4、AT-215-1-E-2、AT-219-1-E-3、AT-235-2-E-1 | 取鎖與回收與釋放遇 `PermissionError`；沙盒與驗證在鎖外組裝、鎖內重驗；`obs-close` 預檢後帳本被改；兩執行緒同時 `obs-add` | `mock.patch`、`PAUSE_HOOK`、執行緒 | `STATE-CHANGED`、`LEDGER-CHANGED`、ID 不重號、有界重試、逾時例外型別如實 |
| 失敗的外部工具 | AT-215-4-1、AT-215-4-E-2、AT-215-1-E-4 | `git archive` 失敗、逾時、成員被拒、`git apply` 套不上與逾時、`git` 執行檔不可用、`tarfile.data_filter` 缺席 | 替身 `subprocess.run`、合成 tar | `applied` 與 `fail_code` 如實、成因碼在 stderr、PROP 進 `sandboxed`；`TARFILE-FILTER-MISSING` rc 3 不降級 |
| 載體缺席與量不到 | AT-240-3-1、AT-233-2-E-1、AT-235-5-E-1、AT-212-4-1、AT-212-4-E-3、AT-220-4-E-2、AT-240-12-E-1、AT-216-1-E-2 | 無事件帳本、逐字稿取不到、稽核檔不在場、金鑰環缺、逐字稿目錄不存在、家目錄不存在 | 檔案不存在、環境變數 | nonblocking NE 或 NOT-EVALUABLE；不是零筆通過；`promote` 對量不到一律拒收（fail-closed） |
| 純度與能力登記 | AT-240-5-1、AT-240-5-E-1、AT-240-5-E-2、AT-235-1-E-3、AT-215-2-1、AT-215-2-E-1 | 40 鍵四類、判準自證、動態載入面、鐵律五形態、平台守衛 | 靜態掃描與 `-X importtime` | 見各 AT |
| 跨語言測試向量 | AT-233-1-2、AT-233-1-E-3 | 固定金鑰與固定 `body` 字串的 HMAC；改一字、換金鑰、`time` 改 `Z` | 標準庫重算 | 與 §5.5 逐字相同；三種變形各自轉紅 |
| 差分（寫入端與重放端） | AT-240-2-E-3 | 13 個態乘 9 個決定形態 | `decwrite.preconditions` 與 `fold` | 格點逐格一致；CLI 抽樣一致 |
| 差分（獨立實作） | AT-215-1-1、AT-216-3-1、AT-221-1-1、AT-218-2-1 | `sandbox_sha256`、`pre_sha256`／`post_sha256`、`out_sha256`、重跑 rc 序列 | 測試自寫的 manifest、雜湊與重跑 | 與被測碼的輸出逐值相同 |
| 非 ASCII host | AT-230-2-1、AT-230-2-E-1、AT-230-2-E-2 | 全形數字與字母、表意句號、中日文、`xn--` 起頭 label（不分大小寫）；`axn--b`、`xn-b` 為對照 | 來源表位元組 | 非 ASCII 與 IDNA 形態 `SRC-URL-HOST`、零連線、不做正規化後比對；對照放行 |
| 偽造、重播與竄改 | AT-212-4-E-2、AT-212-4-E-3、AT-233-1-E-2、AT-217-2-E-1、AT-216-1-E-2、AT-218-2-E-1、AT-221-1-E-2 | 引言不在逐字稿、非真人載體、卡面被改寫、稽核檔重複入帳、舊回覆重播、手改 verdict、驗證檔被改或被刪或事件雜湊被改 | 合成逐字稿與稽核檔、`rewrite_event`、複本上改驗證檔 | 寫入端拒收；`check` 的回查標紅（`PROP-VERIFY-SHA-MISMATCH`、`PROP-FILE-MISSING`）；`promote` 拒收 |
| 機密與環境衛生 | AT-221-1-E-1、AT-233-1-E-3 | 金鑰環與 `AUTOSDD_*` 不入探針環境；遮蔽四型；輸出不含金鑰的 8 字元子字串 | 父行程環境、`probe_env.py`、`probe_secrets.py` | 白名單環境；`[REDACTED]`；滑動視窗檢查為零 |
| 欄位型別與值域（手寫事件） | AT-240-1-1、AT-240-1-E-1、AT-240-2-E-1、AT-240-2-E-2、AT-240-14-E-1 | 九種 P2 事件缺鍵、表外鍵、型別、null 規則、載體互斥；帳本不變式八條 | 手寫事件帳本與 `EV-NEG`、`TRANS-BAD`、`INVAR` | `events.validate` 與 `check` 回規定碼；夾具升級不吞掉明示的錯誤值 |
| 流程型 AC（SOP 條文） | AT-240-13-1、AT-240-13-E-1、AT-218-1-1、AT-218-1-E-1、AT-215-3-1、AT-215-3-E-1、AT-221-2-1、AT-221-2-E-1 | 必備片段逐項刪去、移入程式碼圍欄、序列順序對調、「待補」復現 | 真 SOP 的副本 | 各被判不合格且只點名該項；機器守的一半另有負控 |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| `capacity`、`mea.*` 事件的寫入、M1～M5 與退役、冷卻的 M4 計數與自動入 OBS | 屬 P3（PRD §9.6）；P2 的 `status` 對容量仍印 NOT-EVALUABLE、`mea.*` 仍只有被消費鍵的型別檢查；`capacity` 於 P2 仍 rc 3 | P3 開工，或事件帳本出現 `mea.*` 而 P2 的折疊未承接 |
| AgentConsole 的 Bridge、backend、frontend、Flyway（含 Console DB 稽核表對帳、帳號白名單 `console.si.deciders`、403） | 屬 P2b／P1b 的另一份 TCS（AgentConsole 子專案流程，其鐵律 7：該專案開發 agent 不動根層 `tools/`）；本檔只承擔根層半，並以 §5.5 的向量與稽核檔形態為共同契約 | P2b 開工，或 Bridge 與 CLI 對同一稽核檔的判定不一致 |
| 沙盒對探針的作業系統層隔離（檔案系統隔離、網路隔離、行程限制） | PRD §9.4 劃界：沙盒是「樹外副本加 `PYTHONPATH` 遮蔽加環境白名單」，探針內容是凍結者的指令（信任邊界＝凍結者角色，P）；`runner` 不聲稱防止探針自行讀寫主樹 | 出現探針改寫主樹或讀走 held-out 的事件，或掌舵者要求探針網路隔離 |
| 欄位全部自洽的偽 PASS 的偵測 | `check` 的 `events.verdict` 只驗欄位自洽（PRD §9.4 誠實劃界）；稽核靠 QA 以同指令於同 base 重跑（R90 (c)） | 出現 `verify1.json` 與同指令重跑結果不符而 `check` 全綠 |
| LLM 意見的任何形態的採信 | 刻意沒有：`verify` 無覆寫旗標、verdict 只取外部可重跑訊號 | 掌舵者要求加入人工覆寫（應走 `dec`，不走 verdict） |
| `promote` 之後自動 commit | 晉升是掌舵者下達的人工動作、不 commit（PRD AC-SI-16-1）；commit 由主控走一般流程並引 DEC-ID | 掌舵者要求晉升即 commit |
| 跨機器 `promote` 與回滾 | 逐字稿與 Console 稽核檔在本機；`promote` 對量不到一律 fail-closed（R91、R92） | 掌舵者要求在無逐字稿的機器上晉升 |
| 逐字稿檔本身被改寫的偵測 | `decide` 信任 `claude_home()` 下的逐字稿檔（harness 寫入）；改寫逐字稿屬檔案系統層的偽造，不在引言回查的射程（PRD 誠實劃界） | 出現逐字稿內容與 harness 實際對話不符的事件 |
| 來源表 host 的 IDNA 語意判準與 DNS 可達性 | R101 只判「非 ASCII 或 `xn--` 起頭」字串形態；IDNA 2003／2008 的語意與可達性不在驗證端（P1 §7.1 ⚖ 37 的留待項至此收口為「host 僅限 ASCII」） | 來源表出現 ASCII 但 IDNA 無效或不可達的 host 手誤 |
| macOS 與 Linux 的實跑 | 未驗（NFR-SI-06-5）；報告標「未驗」；POSIX 守衛分支以替身模擬平台覆蓋（`os.killpg`、路徑長度） | macOS 上 `killpg`、`git apply` 或行尾行為與 Windows 不同 |
| 沙盒的並行（多個 PROP 同時驗證） | `sandbox` 與 `verify` 每 PROP 一個目錄、鎖內重驗，P2 不做跨 PROP 的資源調度（PRD 的 pace 屬 session 層） | 兩個 PROP 的驗證互相拖慢到逾時 |
| SOP 條文的語意判定 | 機械只判關鍵片段是否存在、位置與順序；語意由實跑檢核 V12 對照 PRD | 條文被改成含關鍵字而語意相反 |
| 在 CI 或 hook 接 `decide`、`sandbox`、`verify`、`promote` | 全部是人工閘上的動詞，`AUTOSDD_UNATTENDED` 下 rc 1；P2 不新增 hook、排程或 CI 步驟（PRD §9.7 不新增守衛碼） | 想讓無人視窗自動套用提案 |

**需同步的既有測試**：R107 (c) 列出的站點（以函式名定位）——`test_selfimproving_events.py` 的 `test_AT_142_1_1_p1_items_on_p0_baseline_and_after_a_round`、`test_AT_142_2_E_1_p0_negatives_unchanged`、`test_AT_140_1_E_1_unimplemented_verbs_and_reject_grammar`、`test_AT_108_4_E_3_weird_events_are_event_type_only`、`TestDecFlagsAndConsumedKeys.check_case` 與 `test_AT_106_2_E_1_link_rejections`（R110 的一個案例移出負控集合）；`test_AT_142_1_1_…` 後半的 `ref.carrier_families` 由 `NE` 改 `PASS`（R104）；`test_selfimproving_check.py` 的 `test_AT_001_1_1_baseline_is_green`、`test_AT_003_1_1_no_resident_mechanism`、`test_AT_030_1_E_1_usage_errors`；`test_selfimproving_capability.py` 的 `test_AT_143_1_E_2_dynamic_purity_and_forbidden_words` 與 `CAPABILITY` 登記表及計數；P1 的 `export`／`status`／`scan` 測試中對 `status` 13 鍵、`QUOTE-VERIFIER-NOT-ESTABLISHED`、`讀到 N 筆` 與 `bug`／`P3`／`open`、`cooldowns[]` 元素鍵集的斷言——其餘一字不動；根層護欄的重釘由主控收尾（NFR-P2-8、NFR-P2-9）。

---


## 5. 測試資料規格

共用夾具住 `tools/tests/_selfimproving_fixtures.py`（P1 既有；依 R107 升級，**既有呼叫形態不變**）與 `tools/tests/_selfimproving_p2_fixtures.py`（新增；底線開頭、不被收集；§5.7）。夾具模組**自行定義**判準函式與建構器，不 import 被測模組的內部私有符號（被測的公開函式級入口見 §5.6）。合成編號（PROP、RUN、ATT、DEC、APP、OBS）一律於執行期以字串相加組出（先例 P1 的 `pid()`、`rid()`、`obs_id()`）；本檔與測試原始碼不寫不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>`（NFR-P2-7；P1 R18 (a) 與 R104 的 `git grep` 會掃整個 repo 的非忽略檔）。**例外**：§5.5 的向量逐字列出的 `PROP-SI-<數字>` 與 `OBS-SI-<數字>` 皆為真帳本已存在的編號。

### 5.1 基線 repo（`make_p2_repo`）、環境與 `params.json`

`make_p2_repo(dest, *, events=None, sources=None, extra_obs=(), defs=(), prm=None, rows=10, commit=True) -> Path`：包裝 P1 的 `make_p1_repo`——**C1、C2、C3 的全部內容沿 P1 §5.1 逐字不變**（OBS 列 001～010、缺陷帳本家族、`AISDLC_SDD/` 的 `<VOLD>`／`<VNEW>` 版本目錄與 `sdd_version.py`、`playbooks/demo.yaml`、`docs/notes/demo.md`（100 行）、`other.md`（50 行）、`f1.md`～`f9.md`、`tiny.md`、`build/reports/pytest.log`、`docs/06_quality/misstep_attribution_demo.jsonl`、`.gitignore`），再於 C3 追加：

| 路徑（相對 `R`） | 內容 |
|------------------|------|
| `demo_pkg/__init__.py`、`demo_pkg/core.py` | 各一行（`"""demo"""`、`VALUE = 1`）；供載具自證的「模組在沙盒內」案例（AT-219-1-E-2），**不是任何 PROP 的 touched 路徑** |
| `docs/06_quality/SelfImproving_Protocol/params.json` | **30 鍵**（下表）；`prm` 參數覆寫個別鍵 |
| `CLAUDE.md`、`docs/01_requirements/SelfImproving_PRD.md` | 沿 P1 的迷你版 |

`params.json` 的 30 鍵＝P1 §5.1 的 28 鍵（夾具值逐字沿用：`row_max_bytes` 700、`w_n` 20、`w_min` 5、`w_evt` 2、`w_opp` 5、`max_proposals_per_run` 3、`max_revisions` 2、`churn_max` 2、`min_heldout` 5、`max_touch_ratio` 0.2、`max_new_entries` 3、`stop_after_bad` 2、`cap_frac` 0.9、`max_archive_entries_per_card` 50、`card_line_max` 100、`event_max_bytes` 2000、`metrics_rev` 1、`min_obs_rows` 10、`ledger_warn_bytes` 245760、`ledger_fail_bytes` 262144、`migration_base_sha` null、`spec_body_globs` 三項、`non_evolvable_globs` 十八項〔§5.6〕、`research_fetch_max` 8、`research_bytes_max` 262144、`research_timeout_seconds` 20、`min_events` 1、`export_limit_max` 500）加 **`probe_timeout_seconds`＝600** 與 **`verify_runs_max`＝2**。需要較短逾時的 AT 以 `set_params(R, probe_timeout_seconds=…)` 覆寫（AT 明文寫出覆寫值）。

**環境（hermetic）**：沿 P1 §5.5 (a)～(g)，並增列：(h) `CLAUDE_CONFIG_DIR` 指向 tmp 內的 `cfg/`（逐字稿與子代理逐字稿的根，§5.3；每個測試各自一個、預設為空目錄）；(i) `AUTOSDD_SI_AUDIT_KEY` 預設**不設**，只有 Console 相關 AT 依 §5.5 設定；(j) `GIT_CONFIG_GLOBAL` 預設指向空檔、`GIT_CONFIG_NOSYSTEM=1`（P1 既有）——需要重現 Windows 預設行尾轉換的 AT 明文覆寫為含 `[core]` 節與縮排一個 Tab 的 `autocrlf = true` 的設定檔；(k) `AUTOSDD_UNATTENDED` 預設不設，需要的 AT 以 `mock.patch.dict(os.environ, …)` 設為 `0` 或 `1`；(l) 子行程夾具（探針、孫行程、`-X importtime`）必回收，保底清理以 `addCleanup` 註冊；(m) 凡 AT 要求「以替身模擬平台」者，以 `mock.patch.object(sys, "platform", …)` 在被測呼叫期間生效，被測碼的平台分支以 `sys.platform` 判（R105）。

### 5.2 事件、PROP 與流程建構器；情境表

**事件建構器（P1 既有，依 R107 升級）**：`ev(kind, by="main", **fields)`、`write_events(R, events, *, commit=False, seqs=None)`、`append_events(R, events)`、`EV(R)`、`compose(events, repo_head, seqs=None)`、`H(n)` 同 P1 §5.2；**升級**＝對九種 P2 kind 與 `heldout.freeze` 以確定性預設補齊 R72 的必備鍵，**呼叫端明示的鍵與值一律優先、逐位元保留（明示的錯誤值保持錯誤）**：

| kind | 預設補齊（呼叫端沒給時） |
|------|--------------------------|
| `card` | `rev` 1、`digest` `H(4)`（同 `prop` 的預設 digest）、`card_sha256` `H(5)` |
| `dec` | `id`＝`DEC-SI-` 接 `seq` 三位零補；`decider` 為字面「掌舵者」（`transcript` 載體）；`quote`＝依 `dkind` 與 `prop` 組出的標準引言（例 `核准 <PROP>`）；`sid`＝固定的合法 UUID；`line` 1；`card_seq` 1（`resume` 無）；`decided_at`＝事件 `t`；`digest` `H(4)`（六個綁卡面的 `dkind`）；`reason`「夾具理由」與 `reason_class`「未說明」（需要者）；`flags` 不補。`carrier` 為 `console` 者改補 `audit_ref`（固定 UUID）、`audit_sha256` `H(6)`、`key_id` `00000000`、`decider` `ops_admin`，不補 `quote`、`sid`、`line`、`card_seq` |
| `heldout.freeze` | `digest` `H(7)`、`n` 5、`frozen_by` `FZ` |
| `app.sandbox` | `id`＝`APP-SI-` 接 `seq` 三位零補、`rev` 1、`base`＝`R` 的 HEAD、`sandbox_sha256` `H(8)`、`applied` 真、`touched_ok` 真、`rollback_ok` 真、`fail_code` 為 null |
| `app.verify` | `id`、`rev` 1；依 `verdict`：`PASS`＝`probes_n` 1、四個布林皆真、`verify_sha256` `H(9)`、`heldout_digest` 同 `heldout.freeze` 預設、`reasons` 為空；`NE`＝`probes_n` 0、四個布林為 null、`verify_sha256` 與 `heldout_digest` 為 null、`reasons` 為 `["NO-PROBES"]`；`FAIL`＝同 `PASS` 但 `patched_green` 假、`reasons` 為 `["PATCHED-NOT-GREEN"]` |
| `app.promote` | `id`、`rev` 1、`head_sha`＝`R` 的 HEAD、`pre_sha256` `H(10)`、`post_sha256` `H(11)`、`unverified_ack` 假 |
| `app.rollback` | `id`、`rev` 1、`pre_sha256` `H(11)`、`post_sha256` `H(10)` |
| `obs.add`／`obs.close` | `obs`（執行期組出的 OBS 號）、`audit_ref`、`audit_sha256`、`key_id`、`decider`、`carrier` 為字面 `console`；`obs.close` 另 `disposition` 為 `decided：夾具` |

升級後 P1 的 `dec_ev(n, dkind)`、`_verify(n, verdict)`、`ev("app.sandbox", "main", prop=…)`、`ev("card", "main", prop=…)`、`ev("app.promote", …)`、`ev("app.rollback", …)`、`ev("heldout.freeze", …)` 的**既有呼叫形態不變**；`prop_ev` 的預設 digest `H(4)` 即 `dec` 的預設 digest（使 R74 (h) 不誤報）。

**流程建構器（`_selfimproving_p2_fixtures.py`）**：

- **`drive_to(R, 狀態, *, cls="D", action="modify", target=None, patch="ok", memory=None, heldout=None, route="loop", via="cli", proposer="SA")`**：把 `R` 內一個新 PROP 推進到指定狀態並回傳 PROP 號；狀態鏈＝`proposed`→`carried`→`approved`→`frozen`→`sandboxed`→`verified`→`promoted`。`via="cli"`（預設）以真動詞逐步執行：`proposed`＝`run-open`（觸發 `a`）、`research --skip`（`offline`）與 `prop-new`（本文 `body_md`、`proposer` 為 `SA`）；`carried`＝`card --issue`；`approved`＝`decide_say` 受理 `核准`；`frozen`＝`heldout-freeze --by FZ`（`heldout` 參數給了就用它，否則依 patch 種類自動建 `make_heldout`，`cases=5`、`mutation=True`）；`sandboxed`＝`sandbox`（M 類加 `--memory-dir`）；`verified`＝`verify`；`promoted`＝`decide_say` 受理 `晉升`（NE 者用後式）加 `promote`。`via="events"` 以 `write_events` 手寫同一鏈的事件（不建內容檔、不呼叫 git、不寫沙盒；供只需帳本狀態的 AT）。**patch 種類**（`patch` 與 `action` 參數）：`modify`（預設）＝於 `target`（預設 `docs/notes/demo.md`）第 50 行之後插入一行字面 `FIXED-LINE`；`add`（`action="add"`）＝新增檔 `target`（預設 `docs/notes/new_note.md`），內容一行 `FIXED-LINE`；`mem`（`cls="M"`）＝對記憶目錄內 `feedback_demo.md` 與 `MEMORY.md` 的逐行 patch，加入字面 `FIXED-MEM`；`bad-context`＝與 `modify` 同形但上下文行與 base 不合（`git apply` 必失敗）。各種類的 patch 與本文都經 P1 的 `prop-new` 全部前置檢查（`touched`、觸及比例、新增條目、來源）。自動 held-out：`modify`→`probes=count`、`add`→`probes=exists`、`mem`→`probes=mem`，三者的探針皆「症狀在（未套用）時 rc 1、不在時 rc 0」，突變 patch 為移除該行。同一 `R` 內多個 `drive_to` 使用不同 `target`（避免同型去重與 patch 互相衝突）、且每運轉至多 3 個新 PROP（`max_proposals_per_run`）。
- **`decide_say(R, ID, 引言, *, kind=None, reason_class=None, shape="PC-01", by="main")`**：(1) 若 `ID` 是 PROP 且動詞需要卡面（核准、否決、退回、晉升、轉交、不轉交、回滾、解除之外的綁卡面者；`恢復` 免）：先 `card --issue` 並取其 stdout 的核心區；(2) 依 `shape` 以 `make_transcript` 建合成逐字稿（卡面核心區放進 assistant 文字、`引言` 為 human 的決定記錄）；(3) 呼叫 `decide <ID> --kind <導出的 dkind> --sid <SID> --line <決定記錄的實體行號>`（需理由者附 `--reason-class`）；回傳 `(rc, stdout, stderr, sid, line)`。`kind` 給了就覆寫導出值（供 `KIND-MISMATCH` 情境）。
- **`forge_dec(R, PROP, 引言, *, flags=None)`**：為 `引言` 建 PC-01 逐字稿，並以 `append_events` 手寫追加一筆欄位完整、引言可回查的 `dec`（`quote`、`sid`、`line`、`card_seq`＝最近一筆 `card` 的 `seq`、`digest`、依需要的 `reason`、`reason_class`、`flags`），**略過 `decide` 的狀態層前提**；回傳該事件。
- **`rewrite_event(R, seq, **changes)`**：只改事件帳本第 `seq` 行的指定鍵（保留鍵序與其餘各行位元組）；**`drop_events(R, kind, prop=None)`**：刪除該種類（與 PROP）的事件行（保留其餘行位元組，`seq` 不重編）。
- **`snap_diff(a, b)`**：兩份 `snap` 的差異，回 `(新增路徑集合, 移除路徑集合, 內容變更路徑集合)`；**`surface(R)`**、**`tree_files(路徑)`**、**`manifest_raw(目錄)`**、**`manifest_lf(根, 路徑集合)`**（R84 兩式的獨立實作；不 import 被測的 `manifest.py`）、**`heartbeat_alive(檔)`**（讀心跳檔位元組數、等候後再讀、比較是否仍在增長）。
- **`DEC-STATES`**（十一列；`AT-212-1-1` 與 Console 的十列〔不含「不轉交」〕共用；每列一份獨立複本）：

| # | 動詞與引言 | `dkind` | 前提態（於該列複本內備妥） |
|---|-----------|---------|--------------------------|
| 1 | `核准 <P>` | `approve` | `proposed`，route 為 `loop` |
| 2 | `否決 <P> 證據座標不足` | `reject` | `proposed`，route 為 `loop`；`reason_class` 為 `證據不足` |
| 3 | `否決 <P> 風險太高` | `decline-promote` | `verified`（PASS）；`reason_class` 為 `風險過高` |
| 4 | `退回 <P> 改用 M 類` | `return` | `proposed`；`reason_class` 為 `工件類別錯` |
| 5 | `晉升 <P>` | `promote`（無 `flags`） | `verified`（PASS）、最近一筆 `app.sandbox` 的 `rollback_ok` 與 `touched_ok` 皆真 |
| 6 | `晉升 <P> 未驗採納` | `promote`（`flags` 為 `[unverified_ack]`） | `verified`（NE，`reasons` 為 `[NO-PROBES]`）、沙盒兩欄皆真 |
| 7 | `轉交 <P>` | `ack-handoff` | `proposed`，route 為 `handoff:T1` |
| 8 | `不轉交 <P> 本迴圈不處理` | `reject` | `proposed`，route 為 `handoff:T1`；`reason_class` 為 `範圍外`（**Console 載體不用此列**） |
| 9 | `回滾 <P> 太慢` | `rollback` | `promoted` |
| 10 | `解除 <P>` | `unblock` | `rejected` 且冷卻中（未被 `unblock`） |
| 11 | `恢復 <RUN> 兩個壞窗已人工檢視` | `resume` | 折疊出 SUSPENDED，所在運轉為 `<RUN>`（沿 `SC-SUSP-RESUME`） |

- **`COOL-BASE`**：`R`；OBS 帳本於基線之外有列 `O1`、`O2`（證據座標皆為 `docs/notes/demo.md:12`）、`O3`（證據座標 `docs/notes/other.md:7`，欄位其餘依 §5.1 的列形態）；事件帳本：`run.open`、`research.skip`、`attr`（root，`obs` 為 `O1`，`root_cause` 為 `docs/stale-note`）與其 `attr.confirm`（`by` 為 `QA`）、`attr`（root，`obs` 為 `O3`，同根因鍵）與其 `attr.confirm`、`prop` `A`（`cls` 為 `D`、`target` 為 `docs/notes/demo.md`、`sources` 為 `O1`）、`dec`（`reject`，`reason_class` 為 `證據不足`）。`A` 的內容檔（`r1.md`、`r1.patch`）依 §5.2 `modify` 種類在場，使 `prop-new` 的同型判定可讀取其證據座標。新列 `O4`～`O8`（各 AT 指明的 `時間`、座標、`attr` 狀況）由 AT 現場附加。
- **`SC-SUSP-RESUME`**：`make_p2_repo(events=sc_susp())`（P1 夾具情境；運轉 1 關閉、運轉 2 與 3 已開、運轉 3 有 `research.skip`；折疊結果 `suspended` 為運轉 1）。
- **`EV-OK`**（`AT-240-1-1` 的合規代表事件；每列＝基底事件，欄位值為上表預設，括號內為覆寫）：`card`；`dec`〔`transcript` 載體九個 `dkind` 各一，`console` 載體九個 `dkind` 各一〕；`heldout.freeze`；`app.sandbox`（`applied` 真）、（`applied` 假、`fail_code` 為 `SANDBOX-EXPORT-FAILED`、`sandbox_sha256` 為 null、`touched_ok` 與 `rollback_ok` 為 null）、（`applied` 假、`fail_code` 為 `SANDBOX-APPLY-TIMEOUT`、`sandbox_sha256` 非 null）、（`applied` 假、`fail_code` 為 null、`sandbox_sha256` 非 null）；`app.verify`（`PASS`）、（`FAIL`）、（`NE`，`probes_n` 為 0）、（`NE`，`probes_n` 為 1、`reasons` 為 `[BASELINE-NOT-RED]`、`baseline_red` 假）；`app.promote`；`app.rollback`；`obs.add`；`obs.close`。`EV-NEG` 與 `TRANS-BAD`、`INVAR`、`PARITY` 的各列已逐列寫在對應 AT 的 `Given` 欄。
- **`SC-P2-LEGAL`**（`AT-240-2-1`；運轉 `RUN` 全程 open、含研究事件；各 PROP 的 `target` 互異；事件鏈依序）：**A**＝`prop`、`card`、`dec approve`、`heldout.freeze`、`app.sandbox`（applied 真）、`app.verify`（PASS）、`dec promote`、`app.promote`、`dec rollback`、`app.rollback`（終態 `promoted`）；**B**＝`prop`、`card`、`dec approve`、`heldout.freeze`、`app.sandbox`、`app.verify`（NE，`NO-PROBES`）、`dec promote`（`flags` 為 `[unverified_ack]`）、`app.promote`（`unverified_ack` 真）（終態 `promoted`）；**C**＝`prop`(rev 1)、`dec approve`、`heldout.freeze`、`app.sandbox`（`applied` 真、`touched_ok` 假）、`app.verify`（NE，`reasons` 為 `[TOUCHED-SUPERSET]`）、`dec return`、`prop`(rev 2)（rev 1 終態 `returned`、rev 2 為 `proposed`）；**D**＝`prop`、`dec approve`、`heldout.freeze`、`app.sandbox`、`app.verify`（NE，`[MUTATION-ABSENT]`）、`app.verify`（PASS，複驗邊）（終態 `verified`、`verdict` 為 PASS）；**E**＝`prop`、`dec approve`、`heldout.freeze`、`app.sandbox`、`app.verify`（PASS）、`dec decline-promote`（`reason_class` 為 `風險過高`）（終態 `rejected`，冷卻欄 `reason_class` 為該值）。
- **`PARITY` 格點**（`AT-240-2-E-3`）：13 態＝`proposed`〔loop〕、`proposed`〔handoff〕、`approved`、`sandboxed`、`verified`〔PASS〕、`verified`〔NE `NO-PROBES`〕、`verified`〔NE `TOUCHED-SUPERSET`〕、`verified`〔FAIL〕、`verified`〔PASS 而 `rollback_ok` 假〕、`verified`〔PASS 而 `touched_ok` 假〕、`rejected`〔冷卻中〕、`rejected`〔已解除〕、`promoted`；9 形態＝`approve`、`reject`、`return`、`ack-handoff`、`decline-promote`、`unblock`、`promote`〔前式〕、`promote`〔後式〕、`rollback`。

### 5.3 逐字稿與決定語法夾具

- **逐字稿位置**：`<CLAUDE_CONFIG_DIR>/projects/<slug>/<sid>.jsonl`；`<slug>`＝`re.sub(r"[^A-Za-z0-9]", "-", <R 的 realpath>)`（R77 (a)）；子代理逐字稿在 `<CLAUDE_CONFIG_DIR>/projects/<slug>/subagents/**/*.jsonl`（可多層子目錄）。`make_transcript(R, sid, records, *, bom=False, crlf=False)` 寫檔並回傳路徑（UTF-8；`bom` 真＝檔首 BOM；`crlf` 真＝行尾 CRLF）；`records` 為下列記錄建構器的輸出（每筆一行 JSON）。**TRANSCRIPT-DIR**＝上述目錄的空殼建法（`cfg/projects/<slug>/` 存在、無 `subagents/` 或有 `subagents/`，依 AT 指定）。
- **記錄建構器**（形態取自真逐字稿的結構觀察，非官方契約）：`rec_assistant_text(text, ts)`＝`{"type":"assistant","timestamp":ts,"message":{"role":"assistant","content":[{"type":"text","text":text}]}}`；`rec_assistant_tool_use(ts, input)`＝`content` 為 `[{"type":"tool_use","id":…,"name":…,"input":input}]`；`rec_assistant_thinking(ts)`＝`content` 為 `[{"type":"thinking","thinking":…}]`；`rec_user_human(text, ts)`＝`{"type":"user","origin":{"kind":"human"},"timestamp":ts,"message":{"role":"user","content":text}}`（`content` 另有清單形態 `[{"type":"text","text":…}…]`）；`rec_user_sdk`（`origin.kind` 為 `sdk`）、`rec_user_meta`（頂層 `isMeta` 為真）、`rec_user_tool_result(text, ts)`（無 `origin`，`content` 為 `[{"type":"tool_result","tool_use_id":…,"content":text}]`）、`rec_attachment(prompt, typed_ts, origin_kind, write_ts)`＝`{"type":"attachment","timestamp":write_ts,"attachment":{"type":"queued_command","prompt":prompt,"origin":{"kind":origin_kind},"timestamp":typed_ts}}`。`ts` 為帶 offset 或 `Z` 的 ISO 8601；錨點 `T0`＝執行期的固定時刻，後續記錄各加 10 秒。
- **`card_core(stdout)`**：自 `card --issue` 的 stdout 取「卡面核心區」＝`--- 以下不計入核心區 ---` 之前的各行，以 LF 連接。
- **PC-01**（user 載體）：行 1 `rec_assistant_text(<card_core>, T0)`；其後依 AT 指定插入 0 至 3 則只含 `tool_use` 或只含 `thinking` 的 assistant 訊息；最後一行 `rec_user_human(<引言>, T0 加 20 秒)`。**PC-02**（附件載體）：行 1 `rec_assistant_text(<card_core>, T0)`、行 2 `rec_attachment(<引言>, typed_ts=T0 加 10 秒, "human", write_ts=T0 加 40 秒)`、行 3 只含 `tool_use` 的 assistant 訊息（頂層 `timestamp` 為 T0 加 30 秒）。**PC-03**：只含一則 `rec_user_human(<引言>, T0)`（`resume` 專用，無卡面）。
- **GRAMMAR-OK／GRAMMAR-BAD 表**：每列＝一則訊息整體文字與預期（`Parsed` 或碼），已逐列寫在 `AT-212-1-3`、`AT-212-1-E-1` 的 `Given` 欄；測試以 `decgrammar.parse(text)` 直接餵入。
- **NC 目錄**（負控情境編號；本檔各 AT 標頭以 NC 號引用）：

| 編號 | 情境 | 預期碼 | 住處 |
|------|------|--------|------|
| NC-01 | `user` 記錄 `origin.kind` 為 `sdk`，文字為 `核准 <P>` | `NOT-HUMAN-UTTERANCE` | AT-212-1-E-2 |
| NC-02 | human 說 `核准 <P2>`（另一個存在的 PROP）而位置參數為 `<P>` | `ID-MISMATCH` | AT-212-1-E-2 |
| NC-03 | `card --issue` 之後 PROP 被退回修訂為 rev 2（digest 改變），human 對舊卡說 `核准 <P>` | `STALE-CARD` | AT-212-2-E-1 |
| NC-04 | assistant 文字的卡面第二行改掉一個字 | `CARD-NOT-DELIVERED` | AT-212-4-E-2 |
| NC-05 | 否定句與前綴字：`不核准 <P>`、`請核准 <P>`、`OK 核准 <P>` | `GRAMMAR-NO-DECISION` | AT-212-1-E-1 |
| NC-06 | 疑問式與尾隨：`核准 <P>？先等一下`、`核准 <P> 謝謝` | `GRAMMAR-TRAILING` | AT-212-1-E-1 |
| NC-07 | 引用卡面的整則訊息（含分界線、含 `[PROP-SI-…｜digest：…` 行、含 `決定：核准 ／`） | `GRAMMAR-CARD-QUOTED` | AT-212-1-E-1 |
| NC-08 | 同一則訊息兩個決定行（異 PROP、同 PROP、動詞不同） | `GRAMMAR-MULTI` | AT-212-1-E-1 |
| NC-09 | `tool_result` 的文字含字面 `"origin":{"kind":"human"}` 與 `核准 <P>` | `NOT-HUMAN-UTTERANCE` | AT-212-1-E-2 |
| NC-10 | 無尾隨規則的動詞後有字：`解除 <P> 謝謝`、`轉交 <P> 好`、`核准 <P> 。` | `GRAMMAR-TRAILING` | AT-212-1-E-1 |
| NC-11 | ID 形態不配：`恢復 先試試`、`恢復 <P> 理由`、`核准 RUN-SI-<非 3 位以上數字>` | `GRAMMAR-ID-FORMAT` | AT-212-1-E-1、AT-212-1-E-3 |
| NC-12 | `回滾 <P> 太慢` 而 PROP 為 `verified`（未晉升） | `PRECONDITION-STATE` | AT-212-1-E-3 |
| NC-13 | 晉升的式與 verdict 不符（PASS 配後式、NE 配前式） | `PROMOTE-FORM-MISMATCH` | AT-212-1-E-3 |
| NC-14 | handoff 路由的核准與晉升、動詞與路由不配（否決對 handoff、不轉交對 loop） | `ROUTE-HANDOFF`、`ROUTE-VERB-MISMATCH` | AT-212-1-E-3 |
| NC-15 | 附件的打出時刻早於卡面送達，但記錄物理上注入在其後 | `CARD-NOT-DELIVERED` | AT-212-4-E-1 |
| NC-16 | 偽造的 `dec`（格式合法、引言不在逐字稿該行） | `QUOTE-MISMATCH` | AT-212-4-E-3 |
| NC-17 | 卡面只在較早的 assistant 文字，其後另有含 text 的 assistant 訊息 | `CARD-NOT-DELIVERED` | AT-212-4-E-2 |
| NC-18 | `user` 記錄的 `origin` 是字串而非物件；頂層 `isMeta` 為真 | `NOT-HUMAN-UTTERANCE` | AT-212-1-E-2 |
| NC-19 | `user` 記錄完全沒有 `origin` 欄位 | `ORIGIN-MISSING`（NOT-EVALUABLE） | AT-212-1-E-2 |
| NC-20 | `恢復 <舊 RUN> 理由`，而折疊出的 SUSPENDED 所在運轉為另一個 RUN（RUN 號過期、舊回覆重播） | `RUN-MISMATCH` | AT-212-1-E-3 |

### 5.4 held-out、探針、沙盒與驗證夾具

- **`make_heldout(dir, *, cases=5, probes="count", mutation=True, target="docs/notes/demo.md", counter=None, delay=1, module=None)`**：在 `dir`（tmp 內、`HOME` 之外）寫一個 held-out 目錄：`manifest.json`（`schema_rev` 1；`cases` 為 `cases` 個 `{"id": "c<k>", "ref": <基線 OBS 列的 ID>}`；`probes` 依 `probes` 參數；`mutation` 依參數）、探針腳本與 `mutation.patch`、一個子目錄 `data/` 內的一個檔（供「遞迴複製」斷言）。`probes` 取值與探針腳本（皆 UTF-8、純標準庫、確定性；「症狀」＝目標檔不含字面 `FIXED-LINE`〔`add` 種類為目標檔不存在；`mem` 種類為記憶檔不含字面 `FIXED-MEM`〕；rc 0＝症狀不在、rc 1＝症狀在）：

| `probes` | 腳本與 argv（`{python}`、`{heldout}`、`{sandbox}` 為佔位） | 行為 |
|----------|-----------------------------------------------------------|------|
| `count`（預設） | `{python} {heldout}/probe_count.py {sandbox} <target> [<counter>]` | 讀 `<sandbox>/<target>` 判症狀；有 `<counter>` 時追加一行；stdout 一行 `symptom=present` 或 `symptom=absent` |
| `exists` | `probe_exists.py {sandbox} <target> [<counter>]` | `<sandbox>/<target>` 存在 ⇒ rc 0 |
| `mem` | `probe_mem.py {sandbox} [<counter>]` | `<sandbox>/memory/feedback_demo.md` 含 `FIXED-MEM` ⇒ rc 0 |
| `none` | （`probes` 為空陣列） | M／D 類無確定性探針的形態 |
| `always_ok`、`always_red` | `probe_always_ok.py`、`probe_always_red.py` | 恆 rc 0、恆 rc 1 |
| `slow` | `probe_slow.py {sandbox} <target> <delay>` | 先等 `delay` 秒再同 `count` |
| `hang` | `probe_hang.py {sandbox} <hb> <pidfile>` | 啟動每 0.1 秒對 `<hb>` 追加一個位元組的孫行程、把其 pid 寫入 `<pidfile>`，自己再等 600 秒 |
| `hang_fixed` | `probe_hang_fixed.py …` | 症狀在時同 `count`；症狀不在（已套用）時同 `hang` |
| `hang_mutated` | `probe_hang_mutated.py …` | 檔含字面 `MUTATED-MARK` 時同 `hang`；含 `FIXED-LINE` 時 rc 0；否則 rc 1（此型的 `mutation.patch` 移除 `FIXED-LINE` 並加入 `MUTATED-MARK`） |
| `flags` | `probe_flags.py {sandbox} <target>` | 印 `isolated=<sys.flags.isolated> safe_path=<sys.flags.safe_path>`，rc 同 `count` |
| `env` | `probe_env.py {sandbox} <target>` | 印 `PYTHONPATH=<值>`、`AUTOSDD_NAMES=<以逗號列出 AUTOSDD_ 起頭的環境變數名>`、`HAS_SECRET=<MY_SECRET_TOKEN 是否存在>`、`PYTHONUTF8=…`、`PYTHONDONTWRITEBYTECODE=…`，rc 同 `count` |
| `secrets` | `probe_secrets.py {sandbox} <target>` | 輸出末段依序印 `Authorization: Bearer abcdef0123456789abcdef`、`key=` 接 SK-KEY（執行期相加組出的 openai 形態金鑰，後綴 `ABCDEF0123456789abcdef`；本檔不寫連續字面，§5.5）、`Authorization: Basic dXNlcjpwYXNzd29yZA==`、`postgres://admin:s3cr3tpw@db.example/x`，rc 同 `count` |
| `noisy` | `probe_noisy.py {sandbox} <target>` | 先印一行 `MIDDLE-MARKER-<亂數>` 與 1,500 位元組填充（stdout）、一行 stderr、最後 400 位元組的中文字串（使 300 位元組截斷落在多位元組字元中），rc 同 `count` |
| `big` | `probe_big.py {sandbox} <target>` | 只向 stdout 寫恰 2,000,000 位元組、不寫 stderr，rc 同 `count` |

  `mutation` 取值：`True`＝`mutation.patch` 為「移除 `FIXED-LINE` 的反向 diff」（有效突變）；`"noop"`＝改 `target` 的另一行（不移除 `FIXED-LINE`）；`None`＝manifest 無 `mutation`。`module` 給了＝該探針加 `"module": <值>`（`json` 為標準庫、`demo_pkg.core` 為 §5.1 的追蹤檔）。`counter` 給了＝探針 argv 末加該絕對路徑。**held-out 摘要的獨立算法**：`manifest_raw(dir)`（R84 原始位元組式）。
- **`HELDOUT-BAD` 表**：每列＝對一份合規 `make_heldout` 目錄的一個變異，已逐列寫在 `AT-220-1-E-1` 的 `Given` 欄。
- **沙盒失敗情境 `SBX-FAIL`**（`AT-215-4-1`、`AT-215-4-E-2`、`AT-219-2-E-1`）：(a) 套不上＝`drive_to(…, patch="bad-context")`；(b) `touched` 超集＝以 `mock.patch.object` 包住 `sandbox.apply_patch`（呼叫真實函式後在回傳集合加字面 `stray.txt`）；(c) 回滾乾跑不過＝包住 `sandbox.reverse_apply`（呼叫真實函式後於沙盒根多寫 `left_over.txt`）；(d) 套用逾時＝`probe_timeout_seconds` 設 2，包住 `subprocess.run`，對 argv 含 `apply` 者拋 `subprocess.TimeoutExpired`；(e) 匯出失敗四型＝包住 `subprocess.run`：argv 含 `archive` 時回 `CompletedProcess`（rc 128、stderr `fatal: not a valid object name`）／拋 `TimeoutExpired`／真 git 的符號連結成員（base commit 以 `git update-index --add --cacheinfo 120000,<blob>,docs/notes/link.md` 建，複本 `core.symlinks` 設為 `false`、工作樹放同內容的一般檔）／對 `git` 拋 `FileNotFoundError`。替身一律轉呼叫真實函式處理其餘 argv，並記錄每個 argv 收到的 `timeout` 值。
- **`git_subcommands(argv)`**：取 `git` 之後、略過 `-C <目錄>` 與 `-c <鍵=值>` 後的第一個非旗標位置詞；**`scan_git_forms(source_text)`**：以 `ast` 掃合成或真原始碼，對每個 `Git(…).run(…)`／`<x>.run(…)` 呼叫的字面引數序列與每個以字面 `"git"` 起頭的 argv 清單取子命令，回傳命中禁用集合（`stash`、`reset`、`checkout`、`clean`、`restore`、`switch`、`worktree`）的問題清單（每筆含子命令與行號）；允許集合為 `apply`、`archive`、`status`、`rev-parse`、`log`、`show`、`grep`、`merge-base`。
- **`VF-STEPS`、`VERDICT-TABLE`、`PRM-PRE`、`RBK-PRE`、`SBX-PRE`、`VF-PRE`、`TAR-BAD`、`GITFORM-BAD／OK`、`HOST-BAD`**：每列已逐列寫在對應 AT 的 `Given` 欄（本節不重複，避免兩處清單漂移）。

### 5.5 Console 稽核檔、金鑰與跨語言測試向量

- **`write_audit(home, *, kind, ref, subject, body, key=AUDIT_KEY, key_id=None, mac=None, name=None, outer=None)`**：把 `body`（dict 或已序列化的字串）序列化為緊湊 JSON 字串（`json.dumps(…, ensure_ascii=False, separators=(",", ":"))`，鍵序依 R94 的 `body` 欄位表），組外層 `{"schema_rev":1,"kind":kind,"audit_ref":ref,"subject":subject,"body":<body 字串>,"key_id":<金鑰位元組 sha256 前 8 碼>,"mac":<HMAC-SHA256(key, body 字串的 UTF-8 位元組) 小寫 hex>}`（UTF-8 無 BOM、緊湊、LF 結尾），寫入 `<home>/console_audit/<name 或 ref>.json`，回傳 `(路徑, audit_sha256)`。`key_id`、`mac`、`name`、`outer`（外層鍵的覆寫或增刪）供負控列單點變異用；**除 `mac` 列外，`mac` 一律依（變異後的）`body` 重算，使一次只有一個缺陷**。
- **`body_decide(prop_or_run, digest, dkind, *, user="ops_admin", time="2026-10-21T09:15:30+08:00", reason_class=None, reason=None, flags=())`**、**`body_obs_add(…)`**、**`body_obs_close(obs_id, disposition, …)`**：依 R94 的欄位表組 `body`；共通鍵 `schema_rev`、`audit_ref`、`kind`、`user`、`role`（`ADMIN`）、`time`。
- **環境**：`AUTOSDD_SI_AUDIT_KEY` 為金鑰環（逗號分隔）；測試金鑰＝下列向量的固定金鑰（公開的測試用金鑰，不是任何環境的真金鑰）。AUDIT-BAD、CONSOLE-PRE、OBSADD-BAD、OBSCLOSE-BAD 各表的每一列已逐列寫在對應 AT 的 `Given` 欄。
- **金鑰字面刻意不用 `sk-` 前綴（機密掃描）**：下表的 HMAC 金鑰是公開的測試金鑰；`tools/lib/secret_scan.py` 的 openai 形態規則會把 `sk-` 接 20 個以上英數字判為機密、使 pre-commit 擋下 commit（本檔作者以該掃描器對本檔實跑核對）。同理本檔不連續寫出 `sk-` 形態的字串：AT-221-1-E-1 與 §5.4 `secrets` 探針所用的 openai 形態金鑰（記為 SK-KEY）由測試與探針於執行期以 `sk`、連字號與 22 字元後綴 `ABCDEF0123456789abcdef` 相加組出；測試原始碼同樣不得寫出連續的該形態字面（確屬合成樣本者才於行尾加 `# secret-scan-ok: <WHY>`）。
- **跨語言測試向量**（R94；Java 側 P2b 以同一組逐字相同；Python 側由 `AT-233-1-2` 以標準庫重算並逐字比對；本表由向量產生腳本輸出、不手抄）：

| 項目 | 值（逐字） |
|------|-----------|
| 金鑰（UTF-8 字串，不做 base64 解碼；公開的測試金鑰） | `si-p2-vector-key-0123456789-abcdefghijklmnopqrstuvwxyz` |
| `key_id`（金鑰位元組 `sha256` 的前 8 碼小寫 hex） | `f076edf0` |
| 簽章 | `mac`＝`HMAC-SHA256(金鑰位元組, body 字串的 UTF-8 位元組)` 的小寫 hex；**不重新序列化 `body`** |
| 向量共用的 PROP digest | `sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe` |
| `body` 序列化 | `json.dumps(…, ensure_ascii=False, separators=(",", ":"))`，鍵序如下列 `body`（Java 側以同樣字串逐字輸出） |
| V1（`kind` 為 `decide`，核准）`audit_ref` | `6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b` |
| V1 `body`（281 位元組） | `{"schema_rev":1,"audit_ref":"6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","prop":"PROP-SI-004","digest":"sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe","dkind":"approve","flags":[]}` |
| V1 `mac` | `a23f62da5cc2b8668a05570632b60700316350667c2fef600beda100c4bf3c21` |
| V2（`kind` 為 `decide`，否決附理由）`audit_ref` | `0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d` |
| V2 `body`（355 位元組） | `{"schema_rev":1,"audit_ref":"0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","prop":"PROP-SI-004","digest":"sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe","dkind":"reject","reason_class":"證據不足","reason":"證據座標不足，無法判定","flags":[]}` |
| V2 `mac` | `830722c9fcfccc37861f9fe62498aa0074822595e85578e48c8a04298de0ce9b` |
| V3（`kind` 為 `obs-add`）`audit_ref` | `b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e` |
| V3 `body`（380 位元組） | `{"schema_rev":1,"audit_ref":"b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e","kind":"obs-add","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示","evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88","category":"bug","severity":"P3","face":"產品","external_derived":false}` |
| V3 `mac` | `0e67b0e0be050c07dc3b539fed87b3f53f88856446d2468b0e9f1da71cb94f35` |
| V4（`kind` 為 `obs-close`）`audit_ref` | `c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f` |
| V4 `body`（227 位元組） | `{"schema_rev":1,"audit_ref":"c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f","kind":"obs-close","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","obs_id":"OBS-SI-247","disposition":"decided：掌舵者裁決，已修復"}` |
| V4 `mac` | `f299d74dd7c261072b69a4c14a79999cda39716b5a9851b65fce8b6da016f6bc` |
| 負控一：V1 的 `body` 把 `"dkind":"approve"` 換成 `"dkind":"reject"`，`mac` 沿用 V1 原值；該變形 `body` 的正確 `mac`（≠ V1 原值） | `7801839b8fd4d641711b8a982ae18526bc8ae9857f5c5fdc3df19e1b4d5c6b2b` |
| 負控二：V1 的 `body`，以金鑰接一個 `x` 簽出的 `mac`（外層 `key_id` 仍為原金鑰的） | `e4a88cff0a4a932fc930efa4d3b1caeda3f4ad64ebfa82dfedffc1358a61e967` |
| 負控三：V1 的 `body` 把 `+08:00` 換成 `Z`（`mac` 沿用 V1 原值；應先於 MAC 判 `AUDIT-TIME-FORMAT`） | `{"schema_rev":1,"audit_ref":"6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b","kind":"decide","user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30Z","prop":"PROP-SI-004","digest":"sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe","dkind":"approve","flags":[]}` |

### 5.6 測試 seam、函式級入口、判準函式與逐字清單

**被測碼的函式級入口與 seam**（名稱為本檔契約；Developer 欲改名須走勘誤節並同步 R 規則與 AT，否則測試與規格漂移）：

| 名稱 | 住處 | 契約 |
|------|------|------|
| `decgrammar.parse(text)` | `decgrammar.py`（ro） | 回 `Parsed(verb, id, kind_candidates, trailing, flags, line_no)`；拒絕時拋 `GrammarError`（屬性 `code` 為 R78 的 `GRAMMAR-*` 碼） |
| `decverify.verify_dec(event, ctx)` | `decverify.py`（ro） | R79；回 `Verdict(status, code, detail)` |
| `decwrite.preconditions(folded, prop, dkind, flags)` | `decwrite.py`（rw） | R75 末段；回碼清單（空＝前提成立） |
| `transcript.load(path)`、`transcript.find_enclosing(…)` | `transcript.py`（ro） | R77 的解析與「發言之前最近一則含 text 的 assistant 訊息」 |
| `consoleaudit.verify(path, key_ring)` | `consoleaudit.py`（ro） | R94；回成功或拋帶 `code` 的例外 |
| `manifest.tree_manifest(root)`、`manifest.paths_manifest(root, paths, *, lf=True)` | `manifest.py`（ro） | R84 的原始位元組式與 LF 正規化式 |
| `sandbox.precheck_members(tar, root)`、`sandbox.extract_checked(tar_path, root)`、`sandbox.apply_patch(root, patch_path)`、`sandbox.reverse_apply(root, patch_path)`、`SandboxError` | `sandbox.py`（rw） | R85 |
| `runner.run_probe(argv, *, cwd, sandbox_root, timeout)`、`ProbeResult` | `runner.py`（exec） | R87 (f) |
| `verdict.verdict_of(sandbox, verify, freeze, min_heldout)` | `verdict.py`（ro） | R89；輸入為對應事件的 dict（`sandbox`＝`app.sandbox`、`verify`＝`app.verify`、`freeze`＝`heldout.freeze`），回 `(verdict, reasons)` |
| `obswrite.add_console_row(repo, audit_ref, by)`、`obswrite.close_console_row(repo, audit_ref, by)`、`obswrite.PAUSE_HOOK` | `obswrite.py`（rw） | R96 (c)、R97 |
| `evwrite.PAUSE_HOOK` | `evwrite.py`（P1 既有） | 讀末行並配號之後、單次追加之前的測試鉤子 |
| `apply_lock.RELEASE_RETRIES`、`apply_lock.acquire` | `tools/lib/apply_lock.py` | R100 |
| `sources.validate_table(raw, policy)` | `sources.py`（P1 既有） | R101 |
| `refs.reopenable_rows(repo, obs_text)`（與既有的 `refs.closed_rows(repo, obs_text)` 同簽名） | `refs.py`（ro） | R110；回 `ID → 證據路徑集合`＝`closed_rows` 加處置首詞為 `deferred` 的 OBS 列；`closed_rows` 不改 |

**測試端判準函式**（住 `_selfimproving_p2_fixtures.py` 或對應測試檔；不 import 被測模組的私有符號）：`capability_problems(pkg_root, registry)`（R105 的 ①②②′③④、平台守衛站點與禁字樣，回問題清單〔檔名、判準編號、說明〕）；`parse_at_headers(tcs_text)`、`anchor_problems(ats, collected)`（R102）；`sop_p2_problems(text)`（下列 SOP-P2-REQ）；`p1_items(R)`（下列 P1 28 項常數表）；`imported_modules(argv)`（以子行程 `python -X importtime tools/selfimproving.py <argv>` 取 import 項）；`git_subcommands`、`scan_git_forms`（§5.4）。

**SOP-P2-REQ**（R108 的必備片段清單；`sop_p2_problems` 逐項判，每項只在自己的片段缺失時被點名；片段須在程式碼圍欄之外，除非該項標「含圍欄」）：

| 項 | 所在節 | 必備片段 |
|----|--------|---------|
| REQ-01 | 標題 `P2 動詞` 的節 | 該節存在；標題與內文皆不含「待補」 |
| REQ-02 | 同上 | 不含「呼叫它們一律 rc 3」 |
| REQ-03～REQ-11 | 同上，rc 契約表 | 九列各一項（依序 `decide`、`heldout-freeze`、`sandbox`、`verify`、`promote`、`rollback`、`card --issue`、`obs-add`、`obs-close`）：同一行含該動詞名與 `rc 0`、`rc 1`、`rc 3` |
| REQ-12 | 同上，`verify` 列 | 「rc 0 不論 verdict」與「讀 verdict 不讀 rc」 |
| REQ-13 | 同上，`verify` 列 | `VERIFY-RUNS-EXCEEDED` 與「升級人工」 |
| REQ-14 | 同上，`sandbox` 列 | 「rc 0 涵蓋 applied=false」 |
| REQ-15 | 同上，最小序列（含圍欄） | 依序出現 `card --issue`、`decide`、`heldout-freeze`、`sandbox`、`verify`、`decide --kind promote`、`promote` |
| REQ-16 | 同上 | 「不寫引言」與「不寫 `--reason`」 |
| REQ-17 | 同上 | 「凍結者≠提案者」、「`prop-new` 之後」、「`sandbox` 之前」 |
| REQ-18 | 同上 | 「PASS 用前式」與「NE 用未驗採納式」 |
| REQ-19 | 同上 | 「主控 commit」與「DEC-ID」 |
| REQ-20 | 同上 | 「回滾」、`decide --kind rollback`、`rollback` 於同一條文 |
| REQ-21 | 同上（含圍欄） | 同時有 `PowerShell` 與 `bash` 兩形態 |
| REQ-22 | 同上 | `decide --carrier console`、`obs-add`、`obs-close`、「主機端」、「單窗口」 |
| REQ-23 | 同上 | `AUTOSDD_UNATTENDED`、`rc 1`、「入帳期間」、「不手編 OBS 帳本」 |
| REQ-24～REQ-28 | 標題 `審查者` 的節 | 五項各一：「審查者≠提案者」與「不同代理實例與不同 context」；「全程唯讀」；「不自起背景長任務」；「主依據為外部可重跑訊號」；「LLM 意見不得單獨把 FAIL 改成 PASS」 |
| REQ-29～REQ-31 | 標題 `P2 動詞` 的節 | 三項各一：「遇 R-9.6 擋寫或 harness 分類器拒絕」；「不得以改派子代理或換路徑繞過」；「改由符合條件的視窗處理或走轉交」 |
| REQ-32～REQ-35 | 標題 `P2 動詞` 的節 | 四項各一：「逐字入帳」與「指令」「rc」「out_sha256」「out_bytes」「遮蔽末段」；「[他包回報]」；「主控親跑後才升格為已驗證」；「貼不出輸出者改寫為未驗證」 |
| REQ-36 | 全檔 | 「SCG-4 收尾前」 |

**`p1_items(R)` 與 P1 28 項的 ground truth（`AT-240-3-1`）**：`p1_items(R)`＝取 `MJ(R, check)` 的前 28 項，逐項回 `(id, status, blocking, 排序後的 findings 碼清單)`（自被測輸出取值；P1 沒有同名夾具函式）。下表是本檔作者以 P1 現碼與 P1 夾具 `make_p1_repo` 的 baseline 實測、再逐字寫入的常數：欄 R0＝`P1_ITEMS_R0`、欄 R1＝`P1_ITEMS_R1`（`commit` 與否兩形態逐項相同）。`R0`＝`make_p2_repo(commit=True)`（P0 基線、無事件帳本）；`R1`＝`R0` 的複本加一次 `run-open --trigger a --coord tools/a.py:1 --by main` 並 commit（唯一一筆 `run.open`）。儲存格格式為 `status／blocking／碼`：`否`＝`false`（56 格全為否），`—`＝空碼清單，CNE＝`CARRIER-NOT-ESTABLISHED`，FRD＝`FAMILY-REF-DANGLING`（level `warn`）。**R1 欄只有一格與 P1 現碼不同：第 14 項 `ref.carrier_families`，P1 為 `NE／否／CNE`，P2 依 R104 為 `PASS／否／FRD`**（事件帳本在場、無 DEC／APP／MEA 提及，baseline 第 8 列的合成 `proposed@` 指標懸空只印 warn）；其餘 55 格與 P1 現碼逐格相同——「P0 21 項與 P1 7 項原樣」因此是可判定的：`AT-240-3-1` 斷言 `p1_items(R0)` 等於 `P1_ITEMS_R0`、`p1_items(R1)` 等於 `P1_ITEMS_R1`。

| 序 | id | R0 | R1 |
|----|----|----|----|
| 1 | `ledger.structure` | PASS／否／— | PASS／否／— |
| 2 | `ledger.time_tz` | PASS／否／— | PASS／否／— |
| 3 | `row.required` | PASS／否／— | PASS／否／— |
| 4 | `row.enums` | PASS／否／— | PASS／否／— |
| 5 | `row.markers` | PASS／否／— | PASS／否／— |
| 6 | `row.provenance` | PASS／否／— | PASS／否／— |
| 7 | `row.coordinates` | PASS／否／— | PASS／否／— |
| 8 | `row.bytes` | PASS／否／— | PASS／否／— |
| 9 | `row.control_chars` | PASS／否／— | PASS／否／— |
| 10 | `row.fixed_sha` | PASS／否／— | PASS／否／— |
| 11 | `ref.def` | PASS／否／— | PASS／否／— |
| 12 | `ref.obs` | PASS／否／— | PASS／否／— |
| 13 | `ref.orig_notes` | PASS／否／— | PASS／否／— |
| 14 | `ref.carrier_families` | NE／否／CNE | PASS／否／FRD |
| 15 | `history.migration` | PASS／否／— | PASS／否／— |
| 16 | `history.row_mutated` | PASS／否／— | PASS／否／— |
| 17 | `params.keys` | PASS／否／— | PASS／否／— |
| 18 | `params.globs` | PASS／否／— | PASS／否／— |
| 19 | `params.coupling` | PASS／否／— | PASS／否／— |
| 20 | `ledger.volume` | PASS／否／— | PASS／否／— |
| 21 | `ledger.vacuity` | PASS／否／— | PASS／否／— |
| 22 | `events.structure` | NE／否／CNE | PASS／否／— |
| 23 | `events.transitions` | NE／否／CNE | PASS／否／— |
| 24 | `events.mutated` | NE／否／CNE | PASS／否／— |
| 25 | `events.vacuity` | NE／否／CNE | PASS／否／— |
| 26 | `events.prop_files` | NE／否／CNE | PASS／否／— |
| 27 | `events.research` | NE／否／CNE | PASS／否／— |
| 28 | `research.sources` | NE／否／CNE | NE／否／CNE |

**P1 夾具清單的逐字副本**（`AT-240-14-1` 以它們判夾具未被誤改）：`PARAM_SPECS` 的 P1 鍵（28 個，依位元組序）：`cap_frac`、`card_line_max`、`churn_max`、`event_max_bytes`、`export_limit_max`、`ledger_fail_bytes`、`ledger_warn_bytes`、`max_archive_entries_per_card`、`max_new_entries`、`max_proposals_per_run`、`max_revisions`、`max_touch_ratio`、`metrics_rev`、`migration_base_sha`、`min_events`、`min_heldout`、`min_obs_rows`、`non_evolvable_globs`、`research_bytes_max`、`research_fetch_max`、`research_timeout_seconds`、`row_max_bytes`、`spec_body_globs`、`stop_after_bad`、`w_evt`、`w_min`、`w_n`、`w_opp`。夾具 `non_evolvable_globs` 十八項：`**/.claude/**`、`**/CLAUDE.md`、`**/docs_template/**`、`AISDLC_SDD/*/governance/rules/R-*.yaml`、`AISDLC_SDD/AISDLC_SDD_v*/**`、`docs/01_requirements/SelfImproving_PRD.md`、`docs/05_development/SelfImproving_*.md`、`docs/06_quality/SelfImproving_Event_Ledger.jsonl`、`docs/06_quality/SelfImproving_Observation_Ledger.md`、`docs/06_quality/SelfImproving_Proposals/**`、`docs/06_quality/SelfImproving_Protocol/**`、`tools/guard.py`、`tools/lib/aa.py`、`tools/lib/bb.py`、`tools/lib/cc.py`、`tools/lib/selfimproving/**`、`tools/probe/selfimproving_measure.py`、`tools/selfimproving.py`；夾具 `spec_body_globs` 三項：`**/docs/01_requirements/**`、`**/docs/02_architecture/**`、`**/docs/03_testing/**`。

### 5.7 允許變更的檔案集合（與 PRD §9.1〈C4 套件檔案表（P2）〉及模組落點表逐格一致）

**Developer 棒新增**：
- `tools/lib/selfimproving/{transcript,decgrammar,decverify,cooldown,heldout,manifest,verdict,consoleaudit,obsrows,decheck}.py`（10 檔，能力類別 `ro`）、`{decwrite,sandbox,promote,obswrite}.py`（4 檔，`rw`）、`{runner,verify}.py`（2 檔，`exec`）——合計 16 檔，與登記表 `CAPABILITY` 的 40 個鍵（既有 24 檔加新 16 檔）逐一對應；`events.py` 為守 LOC 而須拆出 `evspec`（`ro`）時，走勘誤節同步 R105 與本檔的 40 鍵計數。
- `tools/tests/test_selfimproving_decide.py`、`test_selfimproving_events_p2.py`、`test_selfimproving_sandbox.py`、`test_selfimproving_verify.py`、`test_selfimproving_promote.py`、`test_selfimproving_console_obs.py`、`test_selfimproving_p2_meta.py`，與共用夾具模組 `tools/tests/_selfimproving_p2_fixtures.py`。

**Developer 棒修改**：
- `tools/selfimproving.py`（只增八個動詞與 `card --issue` 的 argparse 子命令與 handler；除 `ro` 以外的模組一律在 handler 內延遲 import）。
- `tools/lib/selfimproving/{events,fold,rows,card,props,status,export,scan,refs,sources,check,evcheck,params,git,propfiles,writeverbs}.py`（既有檔，限 R72～R76、R81、R82、R99～R104、R106、R110 所需；`writeverbs.py` 只改 `attr` link 一處以改用 `refs.reopenable_rows`〔R110；本檔類推增列、不在 PRD C4 表內，§7.1 ⚖ 39〕；`ledger.py`、`__init__.py`、`paths.py`、`defs.py`、`history.py`、`evwrite.py`、`fetch.py`、`research.py` 不動，若須動則於交卷說明並登勘誤；`git.py` 只增 `Git.run` 的選用 `timeout` 參數，預設仍 60 秒）。
- `tools/lib/apply_lock.py`（R100）與 `tools/tests/test_apply_lock.py`（增補 AC-240-8 的替身測試，既有測試不動）。
- `docs/06_quality/SelfImproving_Protocol/params.json`（加兩鍵；**由主控與 `PARAM_SPECS` 同 commit 加入**，Developer 棒於 tmp 夾具內驗證）、`docs/05_development/SelfImproving_Operations_SOP.md`（〈P2 動詞〉定稿與〈審查者〉補條）。
- `tools/tests/_selfimproving_fixtures.py`（R107 (a) 的升級）、`tools/tests/test_selfimproving_events.py`、`test_selfimproving_check.py`、`test_selfimproving_capability.py`、`test_selfimproving_research_scan.py`、`test_selfimproving_export_status.py`（只改 R107 (c) 列出的站點並新增本檔指名的 AT 函式，其餘一字不動）。

**主控收尾另動**：根層鎖檔與棘輪重釘（護欄層行數、`tools/tests` 檔數下限與 E501、兩站點 guard-total、`_REPIN_APPROVED_ROUND_OVERAGE` 具名一次性例外，NFR-P2-9；`tools/tests/test_selfimproving_*` 與 `AutoClaude/tests` 的 `_TREE_FILE_FLOORS` 等）；SSOT `docs/02_architecture/Root_Layout_and_Module_Placement.md` §3 登記列同步（落點鎖會讀它）；`docs/06_quality/RTM-SelfImproving-P2-<日期>.md`；真帳本、真事件帳本與真 `SelfImproving_Proposals/` 的實跑與入帳；OBS-SI-213 的決定（重釘時評估接鏈列允許 OBS-SI ID）。**其餘一律不動**：尤其不動 PRD、研究方法 SOP、P0 與 P1 TCS、`.claude/**`、`AutoClaude/autoclaude/` 引擎原始碼、`AgentConsole/**`；真帳本與真事件帳本只由主控寫（Developer 棒不得碰）。

---


## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| PRD FR-SI-12、13、15～21，加 AC-SI-30-2，加 FR-SI-33、35 的根層半 → F-003 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-003 → US-201～US-206 | ☑ 已映射 |
| US-201～US-206 → 本檔 50 個 AC | ☑ 已映射（FRD-lite） |
| PRD 的 35 個 P2 AC → 本檔 `AC-212-1`～`AC-235-5` 與 `AC-230-2` | ☑ 已映射（編號規則見 FRD-lite 與 §7.1 ⚖ 1） |
| 本檔自增的 15 個 AC（`AC-240-1`～`AC-240-15`）→ AT | ☑ 已映射 |
| 本檔 AC（50 個）→ AT（137 個：正控 57、負控 80） | ☑ 已映射（本檔 §1，覆蓋率 100%；每個 AC 至少一個正控與一個負控） |
| PRD §8.1 P2 出口 (a) 至少一筆真實提案走完「閘→沙盒→驗證→晉升或否決」、DEC 紀錄齊全 → 閘 AT-212-1-1、AT-212-1-2、AT-212-2-1、AT-212-3-1、AT-212-4-1；沙盒 AT-215-1-1、AT-215-1-2、AT-215-4-1；驗證 AT-219-1-1、AT-219-2-1；晉升 AT-216-1-1、AT-216-2-1、AT-216-3-1；與實跑檢核 V8、V15 | ☑ 機制面；真實面待 V8、V15 |
| PRD §8.1 P2 出口 (b) 該筆驗證含對照與突變、突變確實使驗證轉紅＝`app.verify` 三步 → AT-219-1-1、AT-219-1-E-1、AT-219-1-E-2、AT-219-2-1、AT-219-2-E-1、AT-217-1-E-2、AT-220-1-1、AT-220-4-1 與實跑檢核 V15（V8 的 M 類無探針、判 NE，不計入 (b)） | ☑ 機制面；真實面待 V15 |
| PRD §8.1 P2 出口 (c) 同型再提被擋＝冷卻折疊 → AT-213-2-1、AT-213-2-E-1、AT-213-3-1、AT-213-3-E-1 與實跑檢核 V9（真實證據需要一筆真實被否決的 PROP，見 §7.1 ⚖ 40） | ☑ 機制面；真實面待 V9 |
| PRD §8.1 P2 出口 (d) 正式面零未經閘變更＝git 歷史對 DEC 對帳 → AT-212-1-1、AT-212-2-1、AT-212-2-E-1、AT-216-1-1、AT-216-1-E-1、AT-216-1-E-2、AT-215-1-1 與實跑檢核 V9 | ☑ |
| PRD §8.1 P2 出口 (e) 回滾乾跑通過（`app.sandbox.rollback_ok`） → AT-215-1-1、AT-215-4-1、AT-216-2-1、AT-216-2-E-1、AT-240-7-1、AT-240-7-E-1 與實跑檢核 V8、V15 | ☑ |
| PRD §8.1 P2 出口 (f) 承接項已結（DEF-200-559；P1 TCS 兩項殘留各有可重跑檢查且綠） → AT-240-8-1～AT-240-8-E-4、AT-230-2-1、AT-230-2-E-1、AT-230-2-E-2、AT-240-9-1、AT-240-9-E-1 與實跑檢核 V6、V7 | ☑ |
| 主控 2026-10-21 對 ⚖ 39 的裁決（`attr link` 的 `--reopens` 目標＝已結列加 `deferred` 列；AC-240-15） → AT-240-15-1、AT-240-15-E-1 與實跑檢核 V8 (4) | ☑ |
| PRD §8.1 P2 出口 (g) 根層半 AT 綠且 SOP 補入 P2 配方 → AT-233-1-1～AT-233-2-E-1、AT-235-1-1～AT-235-5-E-1、AT-240-12-1、AT-240-12-E-1、AT-240-13-1、AT-240-13-E-1 與實跑檢核 V10、V12 | ☑ |
| PRD §8.1 P2b 出口（真實 Console 決定、新增觀察、處置終值） | ☒ 不在本檔：屬 P2b 鍵 `agentconsole-si-decide` 與另一份 TCS；本檔以 §5.5 向量與稽核檔形態為共同契約 |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由根層 unittest 閘門一併執行；`tools/lib/apply_lock.py` 的 compat-ci `paths` 覆蓋現查 NFR-P2-9；根層重釘由主控收尾） |

**PRD §9.7 Architect 定案 #64～#81 落點表**（任務書要求「逐條落 AT」；每列一個定案，列出本檔條文與承擔它的 AT，不在本檔範圍者明寫原因）：

| §9.7 定案 | 定案內容（摘要） | 本檔條文 | 承擔的 AT，或不在本檔的原因 |
|-----------|------------------|----------|-----------------------------|
| #64 | T1 修訂 v0.10 的研究參數與來源表：`research_fetch_max` 10、`research_bytes_max` 524288、現役來源 9 筆、`event_max_bytes` 4,096 | P1 R46、R58 不變；R72、R106 | AT-240-1-E-2（行長邊界）、AT-240-4-1、AT-240-14-1（`params.json` 為 28 鍵加 2 鍵、既有值不動）；真實 `research --fetch` 於實跑檢核 V8 |
| #65 | 導覽登記表（frontend `registry.ts`、Architecture §5.4） | 無 | 不在本檔：AgentConsole frontend 屬 P1b 鍵 `agentconsole-si-mirror` 與其 TCS（R109：本檔不動 `AgentConsole/**`） |
| #66 | `si_console_writes` 稽核表與 `SecurityConfig` 帳號白名單 | R94（稽核 JSON 欄位與 HMAC，即該表 `body`、`key_id`、`mac` 欄的來源）、R95 | AT-233-1-2（跨語言向量）、AT-233-1-E-1（稽核檔驗證碼表）；資料表、Flyway、白名單與 403 不在本檔：屬 P2b 鍵 `agentconsole-si-decide` 與其 TCS |
| #67 | 稽核回查載體：`obs.add`／`obs.close`（詞彙 19→21）、同一把寫入鎖內先列後事件且僅在長度未變時回退、`MARK_KEYS` 加兩鍵、`check` 的 `obs.console_audit`、`--dry-run --body-file -` 只走 `ro` 模組、`status.console_pending`、`obs-close` 以暫名檔加 `os.replace` 原子改寫 | R72、R76、R96、R97、R98 (d)、R99 (a) | AT-235-1-1、AT-235-1-2、AT-235-1-E-2、AT-235-1-E-3、AT-235-2-1、AT-235-2-E-2、AT-235-5-1、AT-235-5-E-1、AT-240-12-1；Bridge 側同一 `audit_ref` 重送的 409 `si_audit_exists` 屬 P2b，根層半的對應碼是 `AUDIT-REF-REUSED`（AT-233-1-E-2、AT-235-1-E-1、AT-235-2-E-1） |
| #68 | FSM 鍵分割：根層半歸 P2 鍵、AgentConsole 三層歸 P2b 鍵 | 文件資訊「FSM 功能鍵」、FRD-lite〈本檔不含〉、R109 | 範圍型、無 AT：以實跑檢核 V1 判（`AgentConsole/**` 無變動） |
| #69 | `export` 的 `buckets[]` 由 `scan.bucket_of` 導出、路徑片段不 `casefold` | R99 (c) | AT-240-12-1（含大小寫不同的路徑案例）、AT-240-12-E-1 |
| #70 | (2) Console 載體 OBS 列時間取 `body.time`（秒精度、`±HH:MM`、不用 `Z`）；(4) 來源表 host 僅限 ASCII；(9) 帳號名值域 | R94、R96 (b)、R101 | AT-233-1-E-3（`time` 改 `Z` 轉紅）、AT-235-1-1（時間保留 offset）、AT-230-2-1、AT-230-2-E-1、AT-230-2-E-2、AT-235-4-1、AT-235-4-E-1 |
| #71 | 能力登記第四類 `exec`（24→40 鍵；29／7／2／2） | R105 | AT-240-5-1、AT-240-5-E-1、AT-240-5-E-2 |
| #72 | `decverify.verify_dec` 住 `ro`；真人發言判準自寫、不 import hook 的 `_is_genuine_user_turn` | R77、R79、R105 ③ | AT-212-1-E-2（出處負控）、AT-212-4-E-3（`check` 回查已存 `dec`）、AT-240-5-1（唯讀動詞閉包全 `ro`） |
| #73 | `app.promote`、`app.rollback`、`app.sandbox` 欄位定稿：`head_sha`、前後 manifest、`rollback_ok`、`touched_ok`；不存 `commit_sha` | R72、R74 (f)(g)、R91、R92 | AT-240-1-1、AT-240-1-E-1、AT-240-2-E-2、AT-216-3-1、AT-216-3-E-1、AT-240-7-1 |
| #74 | `decide` 不收 `--reason`、`--unverified-ack`；`unverified_ack` 住 `dec.flags` 並於 `app.promote` 留副本 | R78、R80 (a)、R74 (f) | AT-212-1-1（晉升兩式）、AT-212-1-E-4（不收旗標）、AT-216-1-1、AT-240-2-E-2（副本不符） |
| #75 | 逐探針記錄住 `verifyK.json`（只新建）、事件只存 `verify_sha256` 與 `probes_n` | R90 (a) | AT-219-1-1、AT-221-1-1、AT-221-1-E-2（驗證檔被改、被刪、事件雜湊被改） |
| #76 | 沙盒失敗仍寫 `app.sandbox`；`app.verify` 複驗邊 | R75、R85 (g)、R86、R88、R89 ⓪ | AT-215-4-1、AT-215-4-E-1、AT-215-4-E-2、AT-219-2-E-1、AT-217-1-1、AT-240-2-1、AT-240-2-E-1 |
| #77 | `apply_lock` 三站點對 `PermissionError`、逾時拋原始例外；函式名用 `_try_acquire` | R100 | AT-240-8-1、AT-240-8-2、AT-240-8-3、AT-240-8-E-1、AT-240-8-E-2、AT-240-8-E-3、AT-240-8-E-4 |
| #78 | `heldout.freeze` 以 `prop` 為鍵；凍結者≠提案者、先於沙盒、每 PROP 一筆 | R74 (a)(b)(c)、R83 | AT-220-1-1、AT-220-1-E-1、AT-220-1-E-2、AT-240-2-E-2 |
| #79 | `verify_runs_max`＝同 `(prop, rev)` 的 `app.verify` 事件數上限；探針不重試；逾時一律 NE | R74 (e)、R87 (c)、R88、R106 | AT-217-1-1、AT-217-1-E-1、AT-217-1-E-2、AT-240-4-1、AT-240-4-E-1 |
| #80 | ADR-SI-04 三處訂正：`git archive --output`、`filter="data"`、成員型別 fail-closed；無 `.git` 的 `git apply` 由本檔先釘 | R85 (b)(c)(d)；§7.1 ⚖ 2、3、4 | AT-215-1-1、AT-215-1-E-3、AT-215-1-E-4、AT-215-4-E-2 |
| #81 | Architecture 連動（AgentConsole 設計文件回寫） | 無 | 不在本檔：`AgentConsole/docs/02_architecture/Architecture.md` 的回寫屬 P1b、P2b 的文件持有面（R109） |

**R 規則覆蓋表**（R68～R110 各至少由一個 AT 引用；本表由 §2 各 AT 的標頭與本文所引用的 R 編號自動產生，不手工維護；R1～R26 屬 P0、R27～R67 屬 P1，P2 對它們的重定見〈P2 行為規則〉開頭）：

| 規則 | 主題 | 引用該規則的 AT |
|------|------|-----------------|
| R68 | 21 個動詞與旗標 | AT-219-3-E-1、AT-235-3-1 |
| R69 | 成功輸出文法與 `--json` | AT-215-4-1、AT-216-1-1、AT-219-1-1 |
| R70 | 無人值守與家目錄 | AT-212-1-E-4、AT-215-1-E-2、AT-216-1-E-1、AT-217-2-E-1、AT-219-1-E-3、AT-233-1-E-2、AT-240-6-E-1、AT-240-7-E-1 |
| R71 | P2 拒收碼與零殘留 | AT-212-1-E-4、AT-215-1-E-2、AT-215-4-E-1、AT-219-1-E-3 |
| R72 | 詞彙與九種 P2 事件欄位表 | AT-212-1-1、AT-212-3-1、AT-216-3-E-1、AT-240-1-1、AT-240-1-E-1、AT-240-1-E-2 |
| R73 | `by` 與時間 | AT-240-1-1 |
| R74 | 帳本不變式（`events.transitions`） | AT-217-1-E-1、AT-220-1-E-2、AT-240-2-E-1、AT-240-2-E-2、AT-240-3-E-1 |
| R75 | 狀態機轉移表 | AT-212-1-1、AT-216-1-1、AT-240-2-1、AT-240-2-E-1、AT-240-2-E-3 |
| R76 | OBS 標記鍵 `carrier`、`audit_ref` | AT-235-5-1、AT-235-5-E-1 |
| R77 | 逐字稿載體 | AT-212-1-1、AT-212-1-2、AT-212-1-E-2、AT-212-4-1、AT-212-4-E-1、AT-212-4-E-4、AT-220-4-1 |
| R78 | 決定語法解析 | AT-212-1-1、AT-212-1-3、AT-212-1-E-1、AT-212-3-E-1 |
| R79 | 引言驗證 `verify_dec` | AT-212-1-E-2、AT-212-4-1、AT-212-4-E-2、AT-212-4-E-3、AT-216-1-E-2 |
| R80 | `decide`（逐字稿載體）流程與前提 | AT-212-1-1、AT-212-1-E-3、AT-212-1-E-4、AT-212-2-1、AT-212-2-E-1、AT-212-3-1、AT-212-3-E-1、AT-213-1-1、AT-213-1-E-1、AT-216-2-1、AT-216-2-E-1、AT-217-2-1、AT-217-2-E-1 |
| R81 | `card --issue` | AT-240-6-1、AT-240-6-E-1 |
| R82 | 拒絕紀錄與同型冷卻 | AT-213-1-1、AT-213-1-E-1、AT-213-2-1、AT-213-2-E-1、AT-213-3-1、AT-213-3-E-1 |
| R83 | held-out 目錄格式與 `heldout-freeze` | AT-218-1-E-1、AT-220-1-1、AT-220-1-E-1 |
| R84 | manifest | AT-215-1-1、AT-215-1-E-4、AT-216-3-1、AT-220-1-1 |
| R85 | 沙盒匯出、抽取預檢、套用與回滾乾跑 | AT-215-1-1、AT-215-1-2、AT-215-1-E-1、AT-215-1-E-3、AT-215-1-E-4、AT-215-2-E-1、AT-215-4-1、AT-215-4-E-2、AT-216-2-1 |
| R86 | `sandbox` 動詞 | AT-212-2-E-1、AT-215-1-1、AT-215-1-2、AT-215-1-E-1、AT-215-1-E-2、AT-215-4-1、AT-215-4-E-1、AT-220-1-E-2 |
| R87 | 子行程出口 `runner` | AT-217-1-1、AT-217-1-E-2、AT-219-1-E-2、AT-221-1-1、AT-221-1-E-1、AT-240-5-E-2 |
| R88 | `verify` 動詞與三步編排 | AT-217-1-1、AT-217-1-E-1、AT-217-1-E-2、AT-218-2-1、AT-218-2-E-1、AT-219-1-1、AT-219-1-E-1、AT-219-1-E-2、AT-219-1-E-3、AT-219-2-E-1、AT-219-3-1、AT-219-3-E-1、AT-220-2-1、AT-220-2-E-1、AT-220-4-1、AT-220-4-E-1 |
| R89 | 三態判定 `verdict_of` | AT-217-1-E-2、AT-218-2-1、AT-219-1-1、AT-219-1-E-1、AT-219-2-1、AT-219-2-E-1、AT-220-2-1、AT-220-2-E-1、AT-220-4-E-1 |
| R90 | `verifyK.json`、暴露掃描與證據入帳 | AT-218-2-1、AT-218-2-E-1、AT-219-1-1、AT-220-4-1、AT-220-4-E-1、AT-220-4-E-2、AT-221-1-1、AT-221-1-E-2 |
| R91 | `promote` | AT-212-2-E-1、AT-215-3-E-1、AT-216-1-1、AT-216-1-E-1、AT-216-1-E-2、AT-216-2-1、AT-216-2-E-1、AT-216-3-1、AT-216-3-E-1、AT-220-2-E-1、AT-220-3-1、AT-220-3-E-1 |
| R92 | `rollback` | AT-240-7-1、AT-240-7-E-1 |
| R93 | SUSPENDED 與 `resume` | AT-217-2-1、AT-217-2-E-1 |
| R94 | Console 稽核檔與 HMAC | AT-233-1-1、AT-233-1-2、AT-233-1-E-1、AT-233-1-E-3、AT-235-4-1、AT-235-4-E-1 |
| R95 | `decide --carrier console` | AT-216-1-E-2、AT-233-1-1、AT-233-1-E-1、AT-233-1-E-2、AT-233-2-1、AT-233-2-E-1 |
| R96 | `obs-add` | AT-235-1-1、AT-235-1-2、AT-235-1-E-1、AT-235-1-E-2、AT-235-1-E-3、AT-235-3-E-1 |
| R97 | `obs-close` | AT-235-2-1、AT-235-2-E-1、AT-235-2-E-2、AT-235-3-1、AT-235-3-E-1 |
| R98 | `check` 的 P2 追加項 | AT-212-4-1、AT-212-4-E-3、AT-218-2-E-1、AT-233-2-1、AT-233-2-E-1、AT-235-5-1、AT-235-5-E-1、AT-240-3-1、AT-240-3-E-1 |
| R99 | `status` 與 `export` 的 P2 擴充 | AT-235-5-1、AT-240-12-1、AT-240-12-E-1 |
| R100 | `apply_lock` 的 Windows 刪除待決 | AT-240-8-1、AT-240-8-2、AT-240-8-3、AT-240-8-E-1、AT-240-8-E-2、AT-240-8-E-3、AT-240-8-E-4 |
| R101 | 來源表 host 僅限 ASCII | AT-230-2-1、AT-230-2-E-1、AT-230-2-E-2 |
| R102 | AT 序號與 `-k` 錨定規則檢查 | AT-240-9-1、AT-240-9-E-1 |
| R103 | `scan` 資訊型草稿列與來源行 | AT-240-10-1、AT-240-10-E-1 |
| R104 | `ref.carrier_families` 存在性判 | AT-240-3-1、AT-240-11-1、AT-240-11-E-1、AT-240-14-1 |
| R105 | 能力登記第四類 `exec` | AT-215-2-1、AT-215-2-E-1、AT-235-1-E-3、AT-240-5-1、AT-240-5-E-1、AT-240-5-E-2 |
| R106 | `params.json` 兩新鍵 | AT-240-4-1、AT-240-4-E-1 |
| R107 | 夾具升級與既有測試同步 | AT-240-1-1、AT-240-14-1、AT-240-14-E-1 |
| R108 | SOP〈P2 動詞〉與流程型條文 | AT-215-3-1、AT-215-3-E-1、AT-218-1-1、AT-218-1-E-1、AT-221-2-1、AT-221-2-E-1、AT-240-13-1、AT-240-13-E-1 |
| R109 | 範圍與持有面 | AT-240-14-1 |
| R110 | `attr link` 的 `--reopens` 目標 | AT-240-14-1、AT-240-15-1、AT-240-15-E-1 |

---


## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（⚖ 1～⚖ 42）

> 本表的「實測」皆為本檔作者於 2026-10-21 在 Windows 11、Python 3.11.9、Git for Windows 的 tmp 目錄內以唯讀探針現查（腳本不入庫、不連網、不碰真帳本）；輸出逐字節錄。**與任務書或 PRD 字面不一致者標「⚠ 不一致」**，凍結檔不改，需修訂處列於本表末的〈PRD 修訂建議〉。

| 編號 | 問題（PRD 內部矛盾或不可測處） | 本檔已採用的預設 | 替代與再開症狀 |
|------|--------------------------------|------------------|----------------|
| ⚖ 1 | AC 編號：PRD 的 `AC-SI-NN-Y` 與 §5〈編號注意〉的階段前綴形皆含字母，不合 ADR-XPLAT-016 §8.1 的 `AC-[\d\-]+`；P1 TCS 勘誤四留下的「每個 AC 內序號不超過 9」使 P1 的 `AC-130-2` 不能再加 AT | 百位 `2` 承載階段前綴：`AC-SI-NN-Y`＝`AC-2NN-Y`；自增 AC 自 FR 號位 40 起（`AC-240-1`…）；序號 >9 改開兩位序號並規定判定指令的 `-k` 一律用錨定名（AT 底線形接結尾底線），以 R102 的可重跑檢查釘住 | 替代：保留 PRD 全名並加編譯前置轉換（框架改動）。再開症狀：`sdd_compile` 對本檔回報 `unmapped_at_ids` 非空，或 RTM 對不上 PRD AC。建議：PRD 下次修訂把 AC 編號文法與 ADR-XPLAT-016 §8.1 對齊 |
| ⚖ 2 | ⚠ 不一致：任務書前提「本機 Python 沒有 `tarfile.data_filter`」與實測不符；且 `data_filter` 對絕對路徑成員**不拋例外、靜默改名**。實測：`python 3.11.9 platform win32`；`hasattr(tarfile,'data_filter') = True`；`dotdot -> blocked: OutsideDestinationError`；`absolute -> NOT blocked by data_filter; files: ['abs_evil.txt']`（成員 `/abs_evil.txt` 被剝掉前導斜線後寫入）；`symlink -> blocked: LinkOutsideDestinationError` | R85 (c)：自寫預檢**必備**（`..`、絕對路徑、反斜線起頭、磁碟機代號與任何 `:`、控制字元、尾端點或空白、非一般檔與目錄型別、同名重複），先於任何寫入；通過後才 `extractall(…, filter="data")`；`tarfile` 無 `data_filter` 屬性＝rc 3、`TARFILE-FILTER-MISSING`、不降級、不寫事件（沿 PRD §9.3）。AT-215-1-E-4 以合成 tar 與替身釘住兩者 | 替代：只靠 `filter="data"`（會讓絕對路徑成員被靜默改名而不是匯出失敗，且依賴直譯器版本）。再開症狀：直譯器升級後 `data_filter` 行為改變（例如對絕對路徑改拋例外），預檢仍是縱深防禦、不需撤 |
| ⚖ 3 | ⚠ 不一致：PRD §9.4 與 Q16 沒有提到行尾轉換。實測（無 `.git` 的目錄內 `git apply` 正向再反向，`fwdCRLF`＝正向套用後結果檔是否含 CR、`revEqualsBase`＝反向後是否逐位元等於 base）：`A_default fwd_rc=0 rev_rc=0 fwdCRLF=True revEqualsBase=False`；`B_autocrlf_false_cflag fwd_rc=0 rev_rc=0 fwdCRLF=False revEqualsBase=True`；`C_nosystem_env`、`D_global_system_empty`、`E_count_env`、`F_autocrlf_input_cflag` 皆 `fwdCRLF=False revEqualsBase=True`；`G_in_repo default fwd_rc 0 CRLF? True`。Git for Windows 的系統層設定 `core.autocrlf=true` 使沙盒內 `git apply` 把被改的檔整個寫成 CRLF，回滾乾跑必失敗；P1 夾具的 hermetic 環境把全域與系統設定清空，看不到此危害 | R85 (d)：全部 `git apply` 與 `git archive`（沙盒、`promote`、`rollback`、M 類記憶目錄）一律帶 `-c core.autocrlf=false`；AT-215-1-E-3 以含 `autocrlf = true` 的 `GIT_CONFIG_GLOBAL` 重現 Windows 預設並記錄危害見證；記錄器斷言每個 `apply`／`archive` 的 argv 含該旗標（AT-215-2-1） | 替代：`GIT_CONFIG_NOSYSTEM=1` 加空的 `GIT_CONFIG_GLOBAL`（實測同樣有效，但改的是子行程環境，且擋不住倉庫層 `.git/config`）。再開症狀：出現第三個影響 `git apply` 結果的設定（例 `apply.whitespace=fix`）使正向反向不對稱——屆時再加旗標或改以 `--whitespace=nowarn` 固定 |
| ⚖ 4 | PRD Q16「無 `.git` 的沙盒樹內 `git apply` 是否可用」未實測。實測：`sandbox inside git work tree? rc= 128 fatal: not a git repository`（沙盒在樹外）；`archive rc 0 size 10240`、`members: ['a.txt', 'sub', 'sub/b.txt']`、`.git in sandbox? False`；`numstat rc 0 '1\t1\ta.txt\x00'`；`apply (no .git) rc 0`；`apply -R rc 0` | 可用：沙盒樹**不含 `.git`**，`git apply`（含 `--numstat` 與 `-R`）在其內執行；R85 (d)(f) 據此編排 | 替代：沙盒內 `git init` 再套用（多一個 `.git` 污染 manifest）。再開症狀：某 git 版本在無 `.git` 的樹內拒絕 `apply`（屆時 `applied` 為假、`fail_code` 為 null，`verify` 收 NE，可偵測） |
| ⚖ 5 | PRD AC-SI-12-4 ③ 要求「卡面於發言之前最近一則含 text 的 assistant 訊息送達」，未說：卡面文字從哪取、如何比對、`dec` 如何指向掌舵者看到的那張卡 | R79 ③：`dec` 帶 `card_seq` 指向同 PROP 的 `card` 事件（`card --issue` 寫入，記 `card_sha256`）；以事件帳本在該事件之前的前綴折疊、用 `card.build` 同一函式重建當時卡面，雜湊須等於 `card_sha256`（否則 `CARD-SHA-MISMATCH`）；**核心區**（分界線之前各行）須整段（逐字、行序）出現在「最近一則含 text 區塊的 assistant 訊息」內（否則 `CARD-NOT-DELIVERED`） | 替代：只比 digest 前 8 碼字樣；或整張卡含分界線之後。再開症狀：卡面渲染規則改版使舊 `card` 事件無法重建（`CARD-SHA-MISMATCH` 成片）——屆時須讓 `card.build` 版本化 |
| ⚖ 6 | 逐字稿的 `queued_command` 附件有兩個時間戳：記錄頂層的 `timestamp`（寫入時刻）與 `attachment.timestamp`（入列＝打字時刻）；實測附件記錄物理上可能落在卡面訊息之前或之後 | R77 (c)(e)：附件載體的時序一律用 `attachment.timestamp`，不用實體行序、不用記錄頂層時間；嚴格晚於卡面訊息才算看過；缺或不可解析＝NOT-EVALUABLE（`ATTACHMENT-TIME-UNKNOWN`） | 替代：用記錄頂層時間（會把「打字在前、寫入在後」的合法核准判成未看卡）。再開症狀：harness 改版移除 `attachment.timestamp`（屆時附件載體一律 NE，`decide` 對它 fail-closed，只剩 user 載體可用） |
| ⚖ 7 | PRD §7.2 未說「理由一句」的邊界，也未說理由句內出現另一個 PROP ID 算不算第二個決定 | R78：理由句＝ID 之後那一個空格之後的同一行全部文字（不剖析標點，「一句」＝同一行）；理由句內的 `PROP-SI-N`／`RUN-SI-N` 字樣不構成第二個決定；決定行之間恰一個 ASCII 空格 | 替代：以標點切句。再開症狀：掌舵者以多行理由或在理由內寫另一張卡的 ID 而被誤拒或誤受 |
| ⚖ 8 | 主控可能把整張卡（含「決定：核准 ／ …」範例行）貼在回覆中，掌舵者的引用會被誤判成決定 | R78 (e)：整則訊息含分界線字面、或某行以 `[PROP-SI-` 起頭且含 `｜digest：`、或含字面 `決定：核准 ／` ⇒ `GRAMMAR-CARD-QUOTED`，整則不受理（先於其餘碼判） | 替代：只拒引用部分。再開症狀：掌舵者合法回覆因引用卡面片段而被整則拒收（屆時改為只拒含範例行的訊息） |
| ⚖ 9 | PRD FR-SI-13 未說「未說明」這個理由類的冷卻強度 | R82 (a)：「未說明」採最嚴冷卻，只有 (b-1)「解除」能結束，(b-2) 新證據不適用 | 替代：與其他理由類同。再開症狀：掌舵者以「未說明」否決後同根因的新證據確實出現卻無法再提 |
| ⚖ 10 | 冷卻的 (b-2)「新證據」未定義何者算、DEF 列有無根因鍵；「再提案須附逐項回應」未定欄位 | R82 (d)：只認 OBS 列（根因鍵經 `attr.confirm` 確認），三條件皆須（時間不早於否決、根因鍵相同、證據座標集合與原提案不相交）；DEF 列不構成 (b-2)；存在同型 `rejected` PROP（含已解除）時新提案本文須有非空 `reject_response`，否則 `REJECT-RESPONSE-MISSING` | 替代：DEF 列也算新證據（須先給 DEF 列根因鍵）。再開症狀：新缺陷帳本列確實是同一問題的新證據卻無法解除冷卻 |
| ⚖ 11 | `dec.decided_at` 取哪個時刻：CLI 執行時刻、或掌舵者發言時刻？PRD §9.2 只說帶 offset | R73：取被引逐字稿記錄的 `timestamp`（附件載體取 `attachment.timestamp`）轉本機 offset、秒精度；`t`（事件寫入時刻）另記 | 替代：用 CLI 執行時刻（會讓 `decided_at` 晚於實際發言數分鐘到數小時）。再開症狀：事後稽核需要「發言到入帳的延遲」（可由 `t` 減 `decided_at`） |
| ⚖ 12 | AC-SI-20-4 ② 要求「掃提案者逐字稿的工具呼叫」，未定範圍、針與時間窗 | R90 (b)：只掃 `claude_home()/projects/<slug>/` 下 `subagents/**/*.jsonl` 中 `assistant` 記錄的 `tool_use` 區塊 `input` 的全部字串值（正規化後含 held-out 凍結目錄絕對路徑、字面 `selfimproving_protocol/params.json`、字面 `tools/probe/selfimproving_measure.py`），**且只計入頂層 `timestamp` 不早於該 PROP 的 `heldout.freeze` 事件時刻 `t` 的記錄；缺頂層 `timestamp` 或值不可解析的記錄視為窗口內（保守計入）、不新增狀態；檔案 mtime 早於 `t` 者可直接略過**；主控逐字稿與 assistant 文字、user 記錄不計；目錄不存在＝`EXPOSURE-UNKNOWN`；只量不阻擋 | 替代：(甲) 不限窗——QA 一審現查真實語料（410 個逐字稿檔中 19 檔已含針；本檔作者以同一支唯讀探針複跑，為 411 檔中 21 檔，`params.json` 針 20 檔、量測腳本針 10 檔：凍結之前就有子代理讀過它們），不限窗則每個真實 PROP 必判 NE、P2 出口 (b) 恆不可達；(乙) 掃全部逐字稿（主控本就持有這些路徑，必然假紅）。再開症狀：(1) 窗口內的並行子代理合法地讀 `params.json`（無關任務）使真實 PROP 判 NE——V8、V15 的前置要求窗口內不並行派讀取 `params.json` 的子代理，並於驗證前以唯讀探針現查窗口內無命中；(2) 提案者子代理以其他形態（如 base64、環境變數間接）取得 held-out 而未被偵測——誠實劃界，屬任務書約束（P）；(3) 逐字稿 `timestamp` 與事件 `t` 的時鐘偏差使邊界記錄誤分（保守規則只對缺或不可解析者生效，邊界偏差不在其內） |
| ⚖ 13 | 載具自證（PRD §9.4）對「探針不 import 被測模組」的情形未定義 | R88：manifest 沒有任何探針宣告 `module` 時 `carrier_proof` 為 `true`（探針以 `{sandbox}` 路徑定址）；宣告者逐一以 `{python} -c` 在沙盒環境取 `__file__` 驗在沙盒內；不聲稱防止探針自行讀主樹 | 替代：空集合視為 NE（M／D 類全部 NE，過嚴）。再開症狀：探針其實 import 了被測模組卻沒宣告 `module`，自證被繞過 |
| ⚖ 14 | 探針的 rc 慣例、重試與步驟順序 PRD 未定 | R88：rc 0＝症狀不在、非 0＝症狀在（與 pytest、ruff 同向）；每步每個探針恰執行一次、不重試至通過（Goodhart 路徑，禁令 4）；順序為基線（未套用）→套用後→突變；非逾時的失敗不略過其後步驟（證據齊備）；逾時使其後步驟不執行 | 替代：早失敗即停（省時間，但證據不齊）。再開症狀：探針本身不穩（間歇失敗）使 NE 率過高 |
| ⚖ 15 | `verify` 時沙盒樹被刪或被改（他處清理、或換機器）怎麼辦 | R88：樹不在或 manifest 不等於 `sandbox_sha256` 時自 `base` 重新匯出，重算後仍不等於記錄值＝`SANDBOX-TREE-DRIFT`（rc 1，他機或 git 版本差異） | 替代：不重新匯出直接拒（人工重做 `sandbox` 不可，PROP 已是 `sandboxed`）。再開症狀：`git archive` 在不同機器對同一 commit 產出不同位元組（`export-subst` 屬性等） |
| ⚖ 16 | ⚠ 不一致：PRD §9.2 要求 `export` 不讀、不印家目錄任何檔（哨兵測試），§9.3 又要求 `export --kind status` 的 `items[0]` 帶與 `status` 同一欄 `console_pending`（其值需讀 `console_audit/` 目錄） | R99 (b)：`export --kind status` 的 `console_pending` 鍵仍在、值恆為 `{"status":"NOT-EVALUABLE","reason":"export-reads-no-home"}`；Console 以 `si_console_writes` 自行對帳 | 替代：`export` 也讀 `console_audit/`（破壞哨兵不變量）。再開症狀：Console 需要 `export` 提供待入帳清單（屆時改由 `status` 的 CLI 呼叫取得） |
| ⚖ 17 | OBS-SI-217：`ref.carrier_families` 對 ATT／PROP／RUN 三族改判存在性，但真帳本與規格文件有大量以示意或前向引用寫出的編號（PRD 卡面範例、OBS 列的前向引用），全判會假紅。⚠ 不一致：PRD AC-SI-04-1 字面「引用不存在的 ID＝不合規」（載體建立後）；PRD §9.2 配號規則「配號＝max(事件帳本, OBS 帳本內既有 PROP-SI- 引用)＋1…（001～003 已被 OBS 處置文字佔用）」承認 OBS 側的 PROP 號可無事件帳本對應 | R104：只判指標形態的引用（OBS 處置欄的 `proposed@PROP-SI-N`、事件帳本內事件的 ID 型欄位、提案目錄名）；不判散文提及與規格、報告類文件；DEC／APP／MEA 三族與載體缺席維持 NE。**OBS 處置欄的懸空 `proposed@` 指標＝歷史列或保留號（PRD §9.2 的 001～003 先例），只到 warn（項目狀態不變）；事件帳本內與提案目錄的懸空仍 FAIL**。改夾具第 8 列不可行——它錨定 P1 配號測試（首個 `prop-new` 為 124）與 P0 測試的取列（`set_cell(repo, 8, …)`）；該列處置即 `proposed@` 接一個永遠不在事件帳本的合成 PROP 號（本檔作者以 P1 夾具實測），判 FAIL 會使 P1 的全部 AT 在事件帳本在場時整批轉紅，違反零退化（AC-240-14） | 替代：判全部提及。再開症狀：指標形態以外的引用（例 OBS 列文字內的 `PROP-SI-N`）指向不存在者而未被發現；OBS 列的 `proposed@` 手誤指向不存在的 PROP 而只印 warn、未被審查者發現，掌舵者要求升為 FAIL |
| ⚖ 18 | M 類（記憶檔）PROP 的沙盒：記憶檔在 repo 外，`git archive` 不含它 | R85 (b)：M 類把 `--memory-dir` 內被 `touched` 觸及的記憶檔複製到沙盒的 `memory/` 之下，`base` 仍記 PROP 的 base（記憶檔的前像另由 `prop-new` 的 `preimage` 欄位守住，`promote` 先 `apply --check`） | 替代：把整個記憶目錄複製進沙盒（含不相干檔、體積大）。再開症狀：記憶檔間有交叉引用而被觸及者單獨驗證不足 |
| ⚖ 19 | held-out 的 `manifest.json` 格式 PRD §9.2 只給目錄形態，未給探針 argv 的約束 | R83：探針 `argv[0]` 必為字面 `{python}`（不得是任意可執行檔），其餘項可含 `{sandbox}`、`{heldout}`；`module` 合識別字正規式；`mutation` 為目錄內無分隔符號的相對檔名；`cases[].ref` 須可解析；`probes` 可為空（M／D 類） | 替代：允許任意可執行檔（擴大凍結者的攻擊面）。再開症狀：合法探針需要非 Python 工具（例 `ruff`），屆時以 `{python} -m ruff` 形態表達 |
| ⚖ 20 | held-out 目錄內含符號連結（Windows 上需特權、POSIX 上可指向目錄外）會使「複製進家目錄」變成讀取任意檔 | R83 (b)：`--from` 目錄內含任何符號連結或 junction ⇒ `HELDOUT-LINK`（本檔類推）；AT 以替身 `os.scandir` 回報連結型條目（平台無法建連結時不跳過） | 替代：複製時跟隨連結（洩漏）。再開症狀：凍結者合法需要連結（極少） |
| ⚖ 21 | PRD §9.3 只給 P2 動詞的表，未給旗標細部、輸出文法與草稿列欄位 | R68～R71 的定義（本檔類推）：位置參數與旗標見 R68 表；成功單行 `ok <kind> seq=<N> …`、拒收 `reject <verb> <碼>` 加 `obs-draft:`；`card --issue` 的 stdout 與不帶旗標相同、`ok` 行走 stderr | 替代：掌舵者逐項裁決。再開症狀：SOP 角色任務書或 Console 需要不同旗標名或輸出行文法 |
| ⚖ 22 | `verifyK.json` 的 K 如何配、`verify_sha256` 量什麼、`events.prop_files` 如何擴充 | R90 (a)：K＝該 PROP 已有 `app.verify` 事件數加 1（自 1 起）；只新建不改寫；`verify_sha256` 取該檔位元組的 `sha256:`（不做 CRLF 正規化）；`check` 重算 | 替代：K 取檔案計數（與事件數可能分歧）。再開症狀：驗證檔被誤刪使 `PROP-FILE-MISSING` |
| ⚖ 23 | M 類晉升時 patch 的路徑 `memory/<檔>` 如何對映到 `--memory-dir` | R91：以 `memory/` 為邏輯根，patch 路徑 `memory/<檔>` 對映 `<memory-dir>/<檔>`；manifest 取 `memory/<檔>` 邏輯名；以逐行 patch 套用、不整檔還原（harness 可能併發自寫索引） | 替代：整檔覆寫（會吃掉併發寫入）。再開症狀：記憶目錄結構含子目錄時對映歧義 |
| ⚖ 24 | `dec.card_seq` 的連結檢查（指向的 `card` 事件存在、digest 相同）放在 `events.transitions` 會使 P1 夾具大量搬動 | R74：`card_seq` 只驗型別與小於本筆 `seq`；連結檢查由 `events.dec_quote` ③ 在逐字稿在場時做，離線不驗 | 替代：離線也驗連結（夾具成本高）。再開症狀：偽造的 `card_seq` 在逐字稿不在場的機器上無法被偵測 |
| ⚖ 25 | `verify --mutation <檔>` 與 manifest 的 `mutation` 並存時何者優先，PRD 未定 | R88：並存＝rc 3、stderr「突變來源二擇一」、零寫入——突變來源不得由驗證者與凍結者各給一份而事後擇優 | 替代：manifest 優先或旗標優先。再開症狀：合法流程需要以旗標覆寫凍結的突變 |
| ⚖ 26 | `promote` 如何認定「有沒有 `dec(promote)`」與「式對不對」：依重放（fold）或依事件掃描？手寫的 FAIL 態 DEC 在重放為非法、不會成為 `last_dec` | R91：`NO-PROMOTE-DEC` 與 `PROMOTE-FORM-MISMATCH` 一律以事件掃描判（不依重放合法與否）；故手寫的 FAIL 態或式不符的 DEC 回報 `PROMOTE-FORM-MISMATCH`，而不是 `NO-PROMOTE-DEC` | 替代：依重放判（FAIL 態得 `NO-PROMOTE-DEC`）。再開症狀：QA 要求手寫事件情境得到不同碼 |
| ⚖ 27 | R100 (3)「次數常數 `RELEASE_RETRIES`＝5」的語意：總嘗試次數或重試次數？ | 初次嘗試之後最多再重試 `RELEASE_RETRIES` 次（共最多 6 次嘗試），每次重試前等待 `poll_interval`；用盡後不改 rc、不拋、印警告、鎖檔殘留交陳舊回收；邊界由 AT-240-8-3 與 AT-240-8-E-3 以常數本身參數化釘住（初值未校準） | 替代：總次數 5。再開症狀：Windows 上釋放刪除待決持續超過約 1 秒使警告與殘留鎖常態化（屆時校準常數，不動結構） |
| ⚖ 28 | `check` 的項目數與判準版本 | R98：P2 追加四項（`events.dec_quote`、`events.dec_console`、`events.verdict`、`obs.console_audit`）共 32 項；`CHECK_RULES_REV` 由 2 增為 3（指紋的 `check_rules_rev` 部分隨之改變）；`_NONBLOCKING` 加三碼 | 替代：把四項併入既有項（破壞 P0／P1 項目順序）。再開症狀：下游以項目數 28 硬編碼 |
| ⚖ 29 | `obs-add --dry-run` 與 Bridge `POST /si/observations:validate` 的 200 回應必須同形，否則 Console 表單預覽與入帳不一致 | R96 (d)：`--json` 的 stdout 為 `{"ok","row","row_bytes","row_max_bytes","findings"}`，與 Bridge 回應同形；只走 `ro` 模組、零寫入、不需家目錄與金鑰 | 替代：Bridge 自行組列（兩份實作漂移）。再開症狀：P2b 的 Bridge 測試與 CLI 預覽對同一 body 的列不逐字相同 |
| ⚖ 30 | Console 入帳的 OBS 列組成：`時間` 如何轉、標記含哪些鍵 | R96 (b)：`時間`＝`body.time` 轉 `YYYY-MM-DD HH:MM ±HH:MM`（保留 offset、丟秒）；標記含 `面`、（`暴露`）、（`外部衍生`）、（`rel`）、`marks_extra`、`來源=人`、`回報者=<user>`、`carrier=console`、`audit_ref`；處置固定 `open`；ID 於鎖內配號 | 替代：CLI 執行時刻作 `時間`。再開症狀：帳本時間與 Console 表單提交時間不一致 |
| ⚖ 31 | 稽核檔 `time` 是否收 `Z`；金鑰環語意 | R94：`time` 須秒精度且明示 offset、**不收 `Z`**（與 Java 側序列化的共同契約）；金鑰環為逗號分隔字串、依 `key_id` 選用、空項略過、全空＝`AUDIT-KEY-MISSING`（入帳不降為 NE；`check`／`promote` 回查才降為 NE） | 替代：收 `Z` 並正規化。再開症狀：Java 側 `OffsetDateTime` 序列化在某些時區輸出 `Z`（P2b 以向量先釘住） |
| ⚖ 32 | 探針行程的環境：繼承全部環境對機密與可重現性都不妥 | R87 (b)：環境白名單（`PATH`、`SYSTEMROOT`、`TEMP`、`TMP`、`HOME`、`USERPROFILE`、`LANG`、`LC_ALL`）加固定的 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1` 與只含沙盒根的 `PYTHONPATH`；不帶 `-I`／`-P`（它們忽略 `PYTHONPATH`，載具自證會失效） | 替代：繼承環境（洩漏 `AUTOSDD_*` 與金鑰環）。再開症狀：合法探針需要其他環境變數（屆時以 manifest 的 `env` 白名單鍵擴充，須走 TCS 修訂） |
| ⚖ 33 | `恢復`（`dec(resume)`）綁定哪個運轉：PRD 說「折疊出的 SUSPENDED 所在運轉」，而 P1 折疊的 `suspended.run` 是最後一個壞窗關閉之前最近開啟的運轉 | R93：沿 P1 折疊，`RUN-MISMATCH` 比對 `fold.suspended.run`（防舊回覆重播；`NOT-SUSPENDED` 防未暫停時的恢復） | 替代：綁目前開著的最新運轉。再開症狀：掌舵者以為要恢復的是最新運轉而被 `RUN-MISMATCH` 擋下（訊息已列出應恢復的運轉號） |
| ⚖ 34 | OBS-SI-218：`scan` 把「窗內有 k 個 commit 觸及」這類只是計數的資訊列草稿成 `bug`／`P3`／`open`，入帳後冒充待辦缺陷 | R103：模組桶候選列的草稿改 `process`／`P4`／`decided：僅計數`（`defects` 來源的候選列維持 `bug`／`P3`／`open`）；三個只計數的來源行改「計 N 筆（未解析內容）」；JSON 不變 | 替代：資訊列不產生草稿。再開症狀：掌舵者要求零候選與資訊列同樣印 `無事件` |
| ⚖ 35 | P1 TCS 的 ⚖ 34 與 ⚖ 37 留下的二擇一：host 的非 ASCII 與 IDNA 形態（`https://１２７.0.0.1/x` 通過 `validate_table`）要「僅限 ASCII」或「正規化後再比對」 | 主控 2026-10-21 定案為拒收：R101：host 含任何非 ASCII 字元、或任一 label 以 `xn--`（不分大小寫）起頭 ⇒ `SRC-URL-HOST`；不做正規化後比對；`research --fetch` 發出請求前先過驗證；IDNA 語意判準（雙點、前導點、label 長度）不做（已由連線端 fail-closed） | 替代：正規化後再比對（須決定 IDNA 2003 或 2008）。再開症狀：來源表出現 ASCII 但 IDNA 無效的 host 手誤 |
| ⚖ 36 | SOP 條文是流程型 AC 的載體，機械只能判關鍵片段存在，不能判語意 | R108 與 §5.6 SOP-P2-REQ：逐項判片段存在、位置（圍欄外）與順序，並以逐項刪去的副本自證判準有牙；語意由實跑檢核 V12 對照 PRD | 替代：不判 SOP。再開症狀：條文被改成含關鍵字而語意相反 |
| ⚖ 37 | AT-240-9-1 要對全部測試檔跑 `pytest --collect-only`，是子行程、依賴 pytest 的節點 id 輸出格式，且耗時 | R102 (c)：以節點 id 全字串的不分大小寫子字串數命中（含檔名與類別名）；每個測試檔收集一次、不對每個 AT 各跑一次；檢查置於 `test_selfimproving_p2_meta.py`，其單檔時間預算含此項（NFR-P2-2） | 替代：只靜態解析函式名（會漏掉 pytest 對檔名與類別名的子字串比對）。再開症狀：pytest 升版改變 `--collect-only -q` 輸出格式 |
| ⚖ 38 | PRD §9.1〈C4 套件檔案表（P2）〉未預留 `events.py` 逼近 400 斷言行時的拆分檔 | NFR-P2-5：`events.py` 逼近上限時先拆 `evspec`（`ro`），不調 tier；`CAPABILITY` 鍵數與 `ro` 計數各加 1 須走勘誤節並同步 R105 與 AT-240-5-1 | 替代：調 LOC tier（違反根層護欄棘輪）。再開症狀：Developer 於實作中真的需要拆檔 |
| ⚖ 39 | ⚠ 不一致（任務書的實跑序列與 P1 現碼）：任務書要求實跑對 OBS-SI-047、060、078、016 各做 `attr --type link --reopens`（新列依序為 OBS-SI-212、213、214、221）。P1 的 `attr --type link` 依 R48 (b) 只收**已結列**（R45：OBS 處置首詞屬 `fixed@…`、`DEF-…`、`merged@…`、`retired`、`decided`），而該四列的處置首詞是 `deferred`（047、060、078）與 `open`（016）。實測（本檔作者以 `python -I` 對真碼 `tools/lib/selfimproving/refs.py` 的 `closed_rows` 唯讀現查，不寫任何帳本）：`OBS-SI-047 in closed_rows: False`、`OBS-SI-060 in closed_rows: False`、`OBS-SI-078 in closed_rows: False`、`OBS-SI-016 in closed_rows: False`；作為 `--from` 的 `OBS-SI-212`、`OBS-SI-213`、`OBS-SI-214`、`OBS-SI-221` 皆為 `True`（處置為 `decided`）；`_CLOSED_OBS: ('fixed@', 'DEF-', 'merged@')` | **採甲（主控 2026-10-21 裁決）**：P2 擴充 `attr --type link` 的 `--reopens` 目標＝R45 已結列 ∪ OBS 處置首詞為 `deferred` 的列（`deferred` 必附再開症狀，被再開即其語意）；處置首詞 `open` 者仍 `REOPENS-NOT-CLOSED`。以獨立函式 `refs.reopenable_rows` 實作、R45 的 `REOPEN-CANDIDATE` 判準不變（R110；AC-240-15；AT-240-15-1、AT-240-15-E-1）；P1 的 `test_AT_106_2_E_1_link_rejections` 同步一個案例（R107 (c)）；V8 (4) 改為三成一拒：212←047、213←060、214←078 各 rc 0 後由審查者 `attr-confirm`，221←016 一次 rc 1 `REOPENS-NOT-CLOSED` 逐字貼入；**016 的關聯只在報告標註，不走 `attr`，也不改已定稿的 OBS 列**（主控二擇一已定） | 替代：(乙) 不擴充判準、改走標記路徑——新列標記寫 `reopens=<舊列>`（P0 標記鍵，P1 只用它抑制復發候選提示、不驗目標），代價是這些復發連結不會成為經審查者確認的 `attr` 事件、不進 `status` 的觸發 (b)。再開症狀：`deferred` 列的再開被審查者質疑時（審查者 `attr-reject` 或要求把 `deferred` 排除出可再開集合）。屬 P1 語意修訂，PRD 修訂建議 6 |
| ⚖ 40 | ⚠ 任務書的實跑序列與 PRD §8.1 P2 出口 (c)：出口 (c)「至少一次同型再提被冷卻擋下」需要一筆真實被否決（`rejected`）的 PROP；任務書實跑序列的兩筆提案（PROP-SI-004 與 D 類 OBS-SI-201）皆走核准與晉升，沒有被否決者，冷卻無從啟動 | 掌舵者於本運轉自行決定是否否決某真實候選；無真實否決則 V9 (c) 標「未驗」，並列為 P2 出口 (c) 的未達成項，不以構造 PROP 充當（沿 P1 出口 (f)「不得以構造候選充當」的口徑）；冷卻的機制面由 AT-213-2-1、AT-213-2-E-1、AT-213-3-1、AT-213-3-E-1 在合成 repo 承擔，不替代真實證據 | 替代：以合成 repo 的 AT 結果充當 (c)（違反出口的真實性要求）；或由主控預先選定一筆候選請掌舵者否決（把裁量權交給主控，違反 K=1 人工閘的原意）；或對 V15 的 D 類提案改打字否決再重提（使 D 類不能晉升、破壞出口 (b)）。再開症狀：SCG-4 時 (c) 仍為「未驗」而掌舵者要求階段收輪 |
| ⚖ 41 | ⚠ 不一致：PRD AC-SI-20-4 ② 的字面是「掃提案者逐字稿（含 `subagents/`）的工具呼叫，命中 held-out 目錄、`params.json` 或量測腳本者標 `exposed`＝NE」，**沒有時間窗**；本檔 R90 (b) 加了「凍結時刻 `t` 之後」的窗口 | 採窗口：held-out 目錄在凍結後才存在，凍結之前的工具呼叫不可能取得它；而 `params.json` 與量測腳本兩種針在真實語料早已被讀過（410 檔中 19 檔命中，QA 一審現查；本檔作者複跑為 411 檔中 21 檔），無窗口則 AC-SI-20-4 在真實運轉下恆為 NE、使 P2 出口 (b)（驗證含對照與突變並判 PASS）結構上不可達；窗口只限縮「何時」、不改「掃什麼」與「命中即 NE、只量不阻擋」 | 替代：照 PRD 字面不限窗（出口 (b) 恆不可達，須先改 PRD 出口）；或改以「凍結時刻之後新建的子代理」為界（需要子代理建立時間，逐字稿不載）。再開症狀：掌舵者認為凍結之前的讀取也應計為暴露。PRD 修訂建議 7 |
| ⚖ 42 | PRD §9.4〈三態判定表〉寫「依序判，先中者定案，`reasons` 列出所有成立的碼」，「所有」是只指決定層（先中的那一層）內全部成立者、或跨層（⓪～④）全部成立者，字面未定 | R89：**`reasons`＝決定層內全部成立碼**（⓪ 三條各自判全列；① 內各碼全列；② 以後各層單碼）；後層的成立碼不列（先中者定案，且 ⓪ 成立時後層欄位為 `null`、本就無從判）；`events.verdict` 的重算同口徑 | 替代：跨層全列（每一層的成立碼都列入 `reasons`；代價：⓪ 成立時後層欄位為 `null` 須另定、`NO-PROBES` 與其餘互斥碼須另定，重算與既有 AT 的 `reasons` 斷言整批改寫）。再開症狀：`events.verdict` 的重算與 PRD 實作對不上（例如 PRD 實作回跨層全列而本檔 AT 斷言只含決定層碼） |

**〈PRD 修訂建議〉**（凍結檔不改；走掌舵者 T1 或 SPEC_REGRESSION_CHECK，由主控決定是否立案）：

1. PRD §8.1 P2 列與附錄 C.2 #19 的 `_try_create` 應訂正為碼內真名 `_try_acquire`（PRD §9.4 已訂正；OBS-SI-210）。
2. PRD §9.2 的「`export` 不讀家目錄」與 §9.3 的「`export --kind status` 的 `items[0]` 同一欄」字面衝突，建議明寫採 ⚖ 16 的取捨。
3. PRD §9.4 與 Q16 應補記 ⚖ 3 的行尾轉換實測與 `-c core.autocrlf=false` 的必備性，及 ⚖ 2 的 `data_filter` 靜默改名實測。
4. PRD AC-SI-12-4 ③ 應補記 ⚖ 5 的卡面送達機制（`card_seq`、`card_sha256`、核心區整段比對）。
5. （**P1 TCS 勘誤事項，非 PRD**）P1 TCS 的 V7 寫「SCG-4 前」入帳流程摩擦，對 SCG-4 的 QA 本身不可能；P1 TCS 為凍結檔、本檔不改它，自本檔起讀「收尾前」（OBS-SI-214；R108 (g)）；由主控決定是否另立 P1 TCS 勘誤。
6. PRD AC-SI-06-2、§9.2〈Attribution〉的「`reopens` 為已結列」字面，附錄 C.2 #3，與 P1 TCS 的 R45、R48 (b)、AT-106-2-E-1：`attr --type link` 的 `--reopens` 目標改為「已結列或處置首詞為 `deferred` 的列」（主控 2026-10-21 裁決，⚖ 39；AC-240-15）；`deferred` 必附再開症狀、被再開即其語意；`open` 仍須先結案；復發候選提示（R45）仍只認已結列。
7. PRD AC-SI-20-4 ②：明寫暴露掃描的時間窗為「凍結時刻之後的 assistant 記錄」，缺或不可解析的時間戳視為窗口內（⚖ 41、⚖ 12）。
8. PRD AC-SI-04-1：明寫 OBS 處置 `proposed@PROP-SI-N` 的指標，載體建立後若無對應 `prop` 事件＝warn（歷史列與保留號，見 §9.2 配號規則），事件帳本內與提案目錄的懸空指標＝不合規（FAIL）（⚖ 17；R104 (b)(i)）。

### 7.2 預審登記

（預審與審查的發現登記於此，只登記、不改規格，凍結後的訂正走下方勘誤節；本檔尚無已登記項。）

| 編號 | 預審所述 | 本檔處置 | 再開症狀 |
|------|----------|----------|----------|

---


## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 50 個 AC 無未映射者（§1） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 有判定指令與驗收字樣；判定指令的 `-k` 字串等於 AT 底線形接結尾底線（錨定名，R102） | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（E 類；流程型 AC 的負向＝對 SOP 條文逐一刪去的副本須判不合格）；全檔負控數（80）不少於正控數（57） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試（見 §4 的邊界值各列：事件行位元組 L 與 L－1、列位元組 700 與 701、held-out 規模 5／4／1 與下限隨參數移動、複驗次數第 2 與第 3 次、探針逾時上下、`tail` 300 位元組的字元邊界與 2,000,000 位元組輸出、路徑長度 259 與 260、釋放重試 `RELEASE_RETRIES` 與其加 1、附件時序早於等於晚於、帳號名 1／64／65 字元、`mac` 與 `time` 與 `key_id` 各一碼的單點變異） | □ |
| 併發負控 | 取鎖與回收與釋放遇 `PermissionError`、沙盒與驗證的鎖外組裝與鎖內重驗競態、`obs-close` 預檢後帳本被改、兩執行緒同時 `obs-add`（AT-240-8-1～AT-240-8-E-4、AT-215-1-E-2、AT-219-1-E-3、AT-235-1-E-2、AT-235-2-E-1） | □ |
| 純度與能力登記 | 40 鍵四類登記表與其合成樹自證、動態載入面（`-X importtime`）、鐵律五形態掃描與合成自證、平台守衛（AT-240-5-1、AT-240-5-E-1、AT-240-5-E-2、AT-235-1-E-3、AT-215-2-1、AT-215-2-E-1） | □ |
| 跨語言契約 | HMAC 向量逐字相同與三種負控變形（AT-233-1-2、AT-233-1-E-3），向量表為 P2b 的共同契約 | □ |
| 測試資料規格完整 | 資料來源明確定義（§5；建構器、情境表、NC 目錄、探針腳本表、向量表） | □ |
| 實跑檢核 V1～V15 全部有逐字輸出證據 | 見下表；沒貼輸出＝未驗證 | □ |

**實跑檢核（非 AT；QA 於 SCG-4 親跑，輸出逐字貼入證據；AT 不碰真帳本與外網，真帳本與真來源的驗收全在這裡；讀 rc 先存變數再讀，不接管線）**

| 編號 | 檢核 | 指令與證據 | 判斷標準 |
|------|------|-----------|---------|
| V1 | 範圍守衛 | `git diff --name-only <Developer 棒起點>..HEAD`；`git diff --stat -- .claude`；`git status --porcelain` | 只含 §5.7 的集合與主控收尾檔；`.claude/**`、PRD、研究方法 SOP、P0 與 P1 TCS、`autoclaude/` 引擎原始碼、`AgentConsole/**` 無變動；真事件帳本與真 `SelfImproving_Proposals/` 不在 Developer 棒的 diff 內；`params.json` 只多兩鍵 |
| V2 | 真 repo `check` | `python tools/selfimproving.py check --json`（讀 rc 先存變數）；貼 JSON | rc 0；`items` 為 32 項；`research.sources` 為 PASS；`events.*` 各項為 PASS 或 nonblocking NE；`ref.obs` 與 `ref.carrier_families` 為 PASS 或 nonblocking NE（不為 FAIL；字面反例 ID 一律以文字描述，不得寫成會被 `ref.obs` 抓到的字面編號）；牆鐘小於 30 秒（取 3 次最大值） |
| V3 | P0 與 P1 回歸與同步範圍 | `python -m pytest tools/tests/test_selfimproving_check.py tools/tests/test_selfimproving_events.py tools/tests/test_selfimproving_props.py tools/tests/test_selfimproving_research_scan.py tools/tests/test_selfimproving_export_status.py tools/tests/test_selfimproving_capability.py tools/tests/test_root_module_layout.py -q -p no:xdist -o addopts=`（逐字貼末行）；`git diff -U0 -- tools/tests/` 與 `git diff -U0 -- tools/tests/_selfimproving_fixtures.py` | 全綠；P0 與 P1 既有測試函式的 diff hunk 只落在 R107 (c) 列出的站點（斷言值同步），其餘位元組不動；P0 的 42 個與 P1 的 163 個 AT 各至少有一個對應函式（AT-240-14-1 同判） |
| V4 | P2 新 AT 全套 | 對七個新測試檔與 CP、RS、AL 三個既有檔各跑 `python -m pytest tools/tests/<檔> -q -p no:xdist -o addopts=`；另對 §2 的每個 AT 以其判定指令（`-k <底線形>_`）各跑一次 | 全綠；每個 `-k` 恰收一個測試；每個 AT 的驗收字樣已在交卷逐項列出；腳本模式 `python tools/tests/<檔> -k <該檔任一 AT 的底線形>_` 收到至少 1 個測試、不是 `Ran 0 tests`（NFR-P2-10 (14)） |
| V5 | 護欄與零退化 | `ruff check` 對新增與改動的每個 `.py`；`python AutoClaude/tools/check_loc_budget.py --json`；`python tools/sync_onboarding_baselines.py --check-snapshot`；官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）；`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`（主控）；`tools/tests/test_defect_id_reference_integrity.py`；compat-ci `paths` 覆蓋現查（NFR-P2-9）；`git grep` 本檔、測試與程式碼的字面 ID | 皆 rc 0；護欄層重釘後淨差額 +0；根層全套 unittest 通過數以實跑為準；無不存在於真帳本的字面 `OBS-SI-<數字>`、`DEF-<數字>`、`PROP-SI-<數字>`、`RUN-SI-<數字>`、`ATT-SI-<數字>` |
| V6 | params、能力登記與 DEF-200-559 | 逐鍵對照 PRD C5 與 §5.1：`params.json` 為 30 鍵、`probe_timeout_seconds` 為 600、`verify_runs_max` 為 2；`CAPABILITY` 為 40 鍵（29／7／2／2）；取修復 commit 之前的 `tools/lib/apply_lock.py`（`git show <修復 commit>^:tools/lib/apply_lock.py`）置於 tmp 並以 `PYTHONPATH` 遮蔽後重跑 AT-240-8-1～AT-240-8-E-4；缺陷帳本 DEF-200-559 列 | `check` 對 `params.keys` 為 PASS；修前版本使 AC-240-8 的各個 AT 各自轉紅、修後綠；DEF-200-559 為 `fixed@<sha>`（由主控收尾以真 sha 入帳，且該 sha 可達） |
| V7 | `apply_lock` 真機壓力與全套 | 官方 `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`）連跑三次，各貼末段；`git log` 中最近的 pre-push 全套是否仍偶發 `PermissionError`（現查帳本 OBS 與缺陷帳本的未結列） | 三次皆 rc 0；標準錯誤無來自 `apply_lock` 的 Traceback；若出現釋放警告，記下次數（初值未校準，R100 (3)） |
| V8 | P2 出口 (a)(e) 與 P1 出口 (b) 補證：運轉層與 M 類真實運轉（主控執行；非構造；掌舵者真人打字；互動視窗、`AUTOSDD_UNATTENDED` 未設） | **前置（暴露窗口；R90 (b)、§7.1 ⚖ 12、⚖ 41）**：`heldout-freeze` 之後、`verify` 之前，以唯讀探針（scratchpad 內的唯讀腳本：不入 repo、不落任何檔、只輸出計數；輸出逐字貼入證據）現查凍結時刻 `t` 之後的窗口內子代理逐字稿（`<claude_home>/projects/<slug>/subagents/**/*.jsonl` 中頂層 `timestamp` 不早於 `t` 的 `assistant` 記錄的 `tool_use` 字串）沒有任何一根針（held-out 目錄路徑、`selfimproving_protocol/params.json`、`tools/probe/selfimproving_measure.py`）；窗口內不得並行派讀取 `params.json` 的子代理；有命中則如實記 NE 並標出口 (b) 未驗，不重跑遮掩。在真實樹依序：(1) `python tools/selfimproving.py run-open`，記下本運轉的運轉號（本檔一律稱「本運轉」、不寫字面：事件帳本尚無該運轉）；(2) `research --fetch`（新來源表；rc 0 或 2，rc 2＝部分來源失敗且事件已寫，沿 P1 R58）；(3) 現查體檢候選已入帳：OBS 主帳本含 OBS-SI-191～222 每一列（`export --kind observations --json` 逐 id 對照）；(4) 復發連結（⚖ 39 採甲，R110）：`attr --type link --by <標籤> --from <新列> --reopens <舊列>`，三成一拒——（OBS-SI-212，OBS-SI-047）、（OBS-SI-213，OBS-SI-060）、（OBS-SI-214，OBS-SI-078）各 rc 0 並寫入一筆 `attr`，其後由審查者 `attr-confirm`；（OBS-SI-221，OBS-SI-016）一次 rc 1 `REOPENS-NOT-CLOSED`（016 的處置首詞為 `open`）逐字貼入，**016 的關聯只在報告標註，不走 `attr`，也不改已定稿的 OBS 列**；(5) PROP-SI-004（事件帳本：`cls` 為 `M`、`route` 為 `loop`、`proposer` 為 `主控`、目標 `memory/guard-ratchet-repin-ritual.md`）：`card --issue`；主控在回覆**逐字印出該卡面**；掌舵者**打字**「核准 PROP-SI-004」；`decide PROP-SI-004 --kind approve --sid <該視窗 sid> --line <該則行號>`；`heldout-freeze`（凍結者標籤不得為 `主控`，否則 `FROZEN-BY-PROPOSER`；`cases` 取真實 OBS 或 DEF 參照、`probes` 為空陣列）；`sandbox --memory-dir <真記憶目錄>`；`verify`（M 類無確定性探針）；掌舵者**打字**「晉升 PROP-SI-004 未驗採納」；`decide --kind promote`；`promote --memory-dir <真記憶目錄>`；(6) 回滾乾跑＝(5) 的 `app.sandbox.rollback_ok`（晉升前提）；晉升後的 `rollback` 只在掌舵者打字回滾時才對真樹執行，其餘以 tmp 複本演練；(7) 自 `prop-new` 之後至 `promote` 之前的每一步前後，各貼 `git status --porcelain`、`git rev-parse HEAD`、`git worktree list` 逐字；另貼各步輸出、`check --json`、`status --json` | (5) PROP-SI-004 的 `app.verify` verdict 為 `NE`、`reasons` 含 `NO-PROBES`（M 類預期，不是 PASS；`cases` 不少於 `min_heldout` 且暴露掃描可評估而未命中時恰為 `[NO-PROBES]`）；`dec(promote)` 的 `flags` 含 `unverified_ack`、`app.promote.unverified_ack` 為 `true`；`app.sandbox` 的 `applied`、`touched_ok`、`rollback_ok` 為 `true`（記憶檔自 `prop-new` 以來漂移而使 patch 套不上時，`applied` 為 `false` 是如實結果：貼證據、依 R75 退回重提，不以構造替代）；每筆 `dec` 的 `quote`、`sid`、`line` 能在真逐字稿以 Read 取回為掌舵者的真人發言（`origin.kind` 為 `human`），且 `check --json` 的 `events.dec_quote` 為 `PASS`；(7) 正式面三項輸出逐字相同（P1 出口 (b) 補證：零提案觸及正式面）；(4) 三筆 `attr` 各寫入且 `status` 的 `reopen_candidates.unsettled` 隨 `attr-confirm` 遞減、221←016 的拒收輸出在證據內；暴露窗口：窗口內無命中，有命中則如實記錄（verdict 為 NE、`reasons` 含 `HELDOUT-EXPOSED`）；`check` rc 0 |
| V9 | P2 出口 (c)(d) 冷卻與 DEC 對帳（主控執行） | (c) 掌舵者於本運轉自行決定是否否決某真實候選（⚖ 40）：V8 與 V15 的兩筆提案皆走核准與晉升、無被否決者；掌舵者若打字否決（或不轉交）某真實候選，再對同型提案執行 `prop-new` 並貼拒收輸出；(d) `python tools/selfimproving.py export --kind events --json` 取全部 `app.promote` 事件，對每個 `touched` 路徑以 `git log --follow --format=%H%n%s -- <路徑>` 取其自 P2 開工起的變更，逐一對上 DEC 事件 | (c) 同型再提被 `COOLDOWN` 擋下（輸出含 `COOLDOWN`、rc 1、零寫入）；本運轉沒有真實否決時，(c) 標「未驗」並列為 P2 出口 (c) 的未達成項，不以構造 PROP 充當；(d) 正式面對 P2 範圍內的每一次變更皆有對應 `dec`（掌舵者經逐字稿或 Console 載體）與 `app.promote`，無未經閘的變更（記憶檔等 repo 外路徑不在 git 歷史內，另以 `app.promote` 的前後 manifest 對帳） |
| V10 | P2 出口 (g) 根層半的真機煙霧 | 在真 repo 上：`python tools/selfimproving.py obs-add --dry-run --body-file <§5.5 V3 body 檔> --json`（唯讀，零寫入）；對 tmp 複本與測試金鑰跑 `decide --carrier console`、`obs-add`、`obs-close` 各一次並貼輸出；`python tools/selfimproving.py status --json` 取 `console_pending`；`python tools/selfimproving.py export --kind observations --json` 取 `buckets[]` | 預檢 rc 0 且 `row` 合 P0 規則；入帳三動詞 rc 0；`console_pending` 與 `buckets[]` 鍵在；真 repo 無新增 OBS 列或事件（煙霧只在 tmp 複本寫入）；真實 Console 決定屬 P2b |
| V11 | 效能與 CI 時間 | 真 repo 上 `check` 三次取最大；每個新測試檔在 CI 上的單檔時間；`sandbox`、`verify` 逾時案例的牆鐘（AT 內有不等式上界） | 真 repo `check` 小於 30 秒；每個新測試檔小於 300 秒；`sandbox` 於合成 repo 小於 30 秒；逾時案例整體小於 15 秒 |
| V12 | SOP、流程型 AC 與流程摩擦 | QA 逐項對照 PRD AC-SI-15-3、18-1、21-2 與 SOP〈P2 動詞〉〈審查者〉條文語意（不只關鍵字在）；Developer 與 QA 的文字交卷 | SOP 條文語意與 PRD 一致；Developer 棒與 QA 棒的交卷都含「流程摩擦」節，節內項目於 **SCG-4 收尾前**由主控入帳為 OBS 列（OBS-SI-214：P1 TCS 寫「SCG-4 前」，對 SCG-4 的 QA 本身不可能），入帳後 V2 仍為綠 |
| V13 | 跨平台實跑與未驗標示 | Windows 真機上 AT-217-1-E-2（行程樹被殺）與 AT-215-1-E-3（行尾）的輸出；報告對 macOS 與 Linux 的實跑標「未驗」（NFR-SI-06-5） | Windows 全綠；未實跑的平台在報告明列「未驗」及其依賴的替身（`sys.platform` 模擬）；不以替身綠燈宣稱 POSIX 行為已驗 |
| V14 | 本檔的編譯與錨定檢查 | 以 `SddToPlaybookAdapter` 的 `_parse_contracts` 與 `_unmapped_at_ids` 對本檔（凍結前無需 FSM 狀態）計 AT 數與 `unmapped_at_ids`；`python -m pytest tools/tests/test_selfimproving_p2_meta.py -k AT_240_9_ -q -p no:xdist -o addopts=` | `unmapped_at_ids` 為空；解析出的 AT 數等於 §1 的 AT 數；AT-240-9-1 與 AT-240-9-E-1 綠 |
| V15 | P2 出口 (a)(b)(e)：D 類真實提案含確定性探針（主控執行；非構造；掌舵者真人打字） | **前置（暴露窗口；R90 (b)、§7.1 ⚖ 12、⚖ 41）**：`heldout-freeze` 之後、`verify` 之前，以唯讀探針（scratchpad 內的唯讀腳本：不入 repo、不落任何檔、只輸出計數；輸出逐字貼入證據）現查凍結時刻 `t` 之後的窗口內子代理逐字稿（`<claude_home>/projects/<slug>/subagents/**/*.jsonl` 中頂層 `timestamp` 不早於 `t` 的 `assistant` 記錄的 `tool_use` 字串）沒有任何一根針（held-out 目錄路徑、`selfimproving_protocol/params.json`、`tools/probe/selfimproving_measure.py`）；窗口內不得並行派讀取 `params.json` 的子代理；有命中則如實記 NE 並標出口 (b) 未驗，不重跑遮掩。來源列 OBS-SI-201：`AgentConsole/docs/04_planning/Implementation_Plan.md` §5.2 的最後一筆 RTM 快照其總列數停在 374，RTM 現查為 392（現查指令＝`AgentConsole/docs/06_quality/RTM.md` §3.4：以 US、API、BR、NFR、INF、UI 六個前綴各加連字號、位於行首的表格列計數）。與 V8 同為本運轉：`attr --type root`（根因鍵由審查者 `attr-confirm`）→ `prop-new`（D 類；patch 只動該檔，於 §5.2 加一列快照總列數 392；提案者標籤≠凍結者標籤）→ `card --issue` → 回覆逐字印卡面 → 掌舵者**打字**「核准 PROP-SI-NNN」→ `decide` → `heldout-freeze`（`cases` 至少 `min_heldout` 筆，現查 `params.json`、目前 5，取真實 OBS 或 DEF 參照；探針 `{python} <腳本> {sandbox}`，腳本由凍結者撰寫：數沙盒內 `AgentConsole/docs/06_quality/RTM.md` 的資料列、讀沙盒內 `Implementation_Plan.md` §5.2 最後一列的總列數，相等 rc 0、不等 rc 非 0；`mutation` 為把該最後一列總列數改成不等於 RTM 列數的值的 patch）→ `sandbox` → `verify`（含突變）→ 掌舵者**打字**「晉升 PROP-SI-NNN」（前式）→ `decide --kind promote` → `promote` → 主控 commit（訊息引 DEC-ID）；`sandbox` 與 `verify` 前後各貼 `git status --porcelain`、`git rev-parse HEAD`、`git worktree list` 逐字；貼 `verify1.json` 摘要與各步輸出 | `app.verify` verdict 為 `PASS`；`baseline_red`、`patched_green`、`mutated_red`、`carrier_proof` 皆為 `true`，`verify1.json` 內基線 `rc` 非 0、套用後 `rc` 為 0、突變 `rc` 非 0（突變確實使驗證轉紅＝驗證有鑑別力，P2 出口 (b)）；`reasons` 不含 `HELDOUT-EXPOSED`、`EXPOSURE-UNKNOWN`（有命中則 verdict 為 NE，如實記錄、出口 (b) 標未驗，不重跑遮掩）；`app.sandbox` 的 `rollback_ok`、`touched_ok` 為 `true`（P2 出口 (e)）；`dec(promote)` 為前式（`flags` 空）、`app.promote.unverified_ack` 為 `false`；掌舵者兩則發言的逐字稿座標（sid 加 line）可取回且 `events.dec_quote` 為 `PASS`；`sandbox` 與 `verify` 前後正式面三項輸出逐字相同；晉升後正式面只多 `Implementation_Plan.md` 一個變更；探針於晉升後的主樹 rc 為 0（加驗，不計入 verdict）；不以構造候選或替身充當 |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（無。凍結後若有 SCG-4 審查發現或實作中須改名的 seam，依 P1 TCS 勘誤節的體例逐次登記：事由、被改的 R 與 AT、既有 AT 的 id 與判定碼名稱一字未改、一個 AT 也未刪。）
