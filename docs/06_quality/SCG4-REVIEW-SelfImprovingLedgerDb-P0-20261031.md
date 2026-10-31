# SCG-4 PR Review 報告 — 帳本改 DB P0（SelfImproving LedgerDb；鍵 `monorepo-si-ledgerdb-p0`；PRD `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` P0、TCS `docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md`）

**日期**: 2026-10-31　**受審**: 本鍵四個 commit `e3723880`（Root_Layout §1／§2）、`d3d751d6`（八份 ADR-SIDB-001～008、Architecture 草稿、案文／基準／預演三份證據檔）、`781700bc`（新 DT 檔 `tools/tests/test_selfimproving_ledgerdb_p0.py`、Root_Layout §3、compat-ci paths、檔數下限、分桶與 c1c2 重釘）、`d4aeab5b`（基準檔 G-P0-10 三列）；受審樹＝repo 外 worktree（HEAD `d4aeab5b`）。**審查者**: 獨立 QA 鏡（Sonnet，未參與開發；12:07 開工、約 75 分鐘）。**主控親驗**: 本檔 §D「主控補跑」列與 §H。

### 審查歷程

| 審次 | 日期 | 結論 | 摘要 |
|------|------|------|------|
| 一審 | 2026-10-31 12:07～13:2x | **PASS** | P1 0、P2 0、P3 9（F-01～F-09）、P4 6（F-10～F-15）；DT 14 全綠；worktree 全套 6010 rc 0；74 個突變 DT 殺 54、閘門殺 14、全門存活 6（皆 TCS 未要求）；G-P0-1～13 實跑達標；附帶條件 F-14（G-P0-8 的 FSM 半由主控在主 repo 補跑——已補，見 §D）。規格 digest 開工與交卷皆同 Stage-2 |

### A. 一審站得住的部分（審查者數字）

- DT 14／14 ok（逐 AT `-k <id>_` 各 rc 0、ran=1）；worktree 全套 rc 0（12:09→12:17；6010 個測試、下限 5996；skip census 46＝platform 42／env-disabled 4；M6 集合成立；TEMP 圍籬綠；孤兒 console 0／0）。
- 突變 74：DT 殺 54（八份 ADR 各一、案文五種、基準檔四種、預演檔四種、Root_Layout 三種、裸 M 三處、協定三檔位元組翻轉、CHECK_RULES_REV、CRLF、BOM、九個判準函式 WEAKEN）；DT 存活 20 中 G-P0-13 殺 11、落點鎖殺 2、G-P0-8 殺 1、全門存活 6（M09c、M13、M13b、M20、M20b、M50 → F-06～F-08、F-10）。TCS 其餘 MU 09～56 皆 killed；R-LD0-01～32 每條皆有 killed，唯 R-LD0-18（MU-31）NE（F-14）。§5.9 重釘面突變：逐檔表、名冊淨額、歷史 sha、prose 桶、doc-total、檔數下限皆 killed；compat paths 見 F-01。
- 閘門：G-P0-3 落點鎖 9 OK；G-P0-4 三副本 92 檔 base／probe 逐檔同、ctrl 新增紅＝c1c2 三項＋E501 棘輪＋F-12 一項（兄弟目錄不反應是目錄選擇造成）；G-P0-5 普查三表 ⊆ 允許集合、帳本盲實驗非空轉；G-P0-6 預演腳本 rc 0 且 35 行逐列相同；G-P0-7 一次性 PG18 容器：單 session 套用 rc 0、14／14 表 owner=si_owner、正控 3 組、負控 9 個皆 rc 3 且訊息含物件名、去觸發器變體使負控 (ii) 成功（烟測有牙）、容器與角色清除驗證；G-P0-9／10 稀疏 clone `si check` rc 0、指紋等於基準、items=33 十個釘座標成立；G-P0-11 isolated E501 與全規則 ruff 皆綠、import 集合合規；G-P0-12 `--print-guard-lines` +0、檔數 113／下限 90、prose 5234＝凍結、十個鎖檔各 rc 0、ruff／compileall／baseline_sites／ntfs／loc_budget 皆 rc 0；G-P0-13 `p0_acceptance_problems` 回 `[]`、secret_scan 20 檔 rc 0。
- 人讀：八份 ADR 六節齊、引用座標逐一現查成立、14 支 dal 檔數與 PRD §9.4 相符、Errata E-1～E-7 與 AC-LD-02-2／04-2／08-4／09-1／09-3 不衝突、TCS §6.1 機械核對 AT 37（正 28／反 9；DT 14／GT 23）、PRD 58＝5＋53。

### B. 發現清單（一審；P3＝文件不一致／可讀性／規格未要求的偵測力缺口；P4＝備註）

| # | 級別 | 座標 | 問題與證據 | 建議修法 |
|---|------|------|------------|----------|
| F-01 | P3 | TCS §5.9#9、`781700bc` 兩支 compat-ci paths | 「漏列即 ci-gate 紅」不成立：拿掉 ADR glob／草稿／證據檔 glob 共 6 種變體，`test_ci_paths_cover_root_consumers` 仍 49 passed；只有單邊拿掉才被 `test_push_and_pr_paths_symmetric` 殺。消費者偵測看不到 DT 以 f-string 組出的 docs 路徑 | P1 起登記 `_KNOWN_LITERAL_PATH_CONSUMERS`（屬 AISDLC_SDD，非 P0 可動）或 TCS 改述為人工義務 |
| F-02 | P3 | TCS G-P0-9／AT-LD-02-6-2 稀疏集 | 原配方缺 `/CLAUDE.md` ⇒ `si check` rc 2、overall=NE（SOURCE-UNAVAILABLE）；加 `/CLAUDE.md` 後 rc 0、指紋等於基準 | 配方加 `/CLAUDE.md`（TCS 勘誤） |
| F-03 | P3 | TCS G-P0-2 的 `<base>` | `e847ee48` 之後四個非 P0 commit 動過 Architecture.md／docker README；P0 四個 commit 都不動這兩檔；以 fdd9a738 為 base 兩檔 rc 0，以 e847ee48 則非零；si-decide／mirror 兩列必 DIFF，與 P0 無關 | 判準改「本鍵 commit 集合不動這兩檔」，MATCH 只在 P0 起點成立 |
| F-04 | P3 | TCS G-P0-1／D9-1／02-6-E-2 的 `<base>..<tip>` | 共用線性 main 夾雜他鍵 commit，字面區間不可算；改用四個本鍵 commit 逐 commit diff 聯集：21 檔全 ⊆ §5.7.1、§5.7.2 零命中 | TCS 寫明用逐 commit 聯集 |
| F-05 | P3 | TCS §5.1.3 E-4 | 寫「AC-SI-35-1 ⑤」，PRD:491 該句在 ③；案文寫 ③ 正確，TCS 筆誤 | TCS 勘誤 ⑤→③ |
| F-06 | P3 | Architecture 草稿與 `draft_problems` | 四塊「生效階段：」值改成 P9、或 §7.2 由 P3 改 P1：DT、G-P0-13、落點鎖全不紅（M13／M13b）；R-LD0-14 寫「P1／P2／P3 之一」但 D4-1 只驗行首字樣在 | `draft_problems` 加值域與塊對階段檢查 |
| F-07 | P3 | `test_selfimproving_ledgerdb_p0.py` `errata_problems` | WEAKEN 成 `return []` 全門存活（M50）：D5 無反向 AT、無合成紅綠自證（其餘判準函式皆有） | 補一個合成反例測試 |
| F-08 | P3 | 基準檔 `d4aeab5b` 新列 | 新三列並存、C 欄標「取代」、DT 取最後列，符合 C5／G-P0-10；唯 SKIP-M6 列漏抄 live 行的 `✅ `；si check 列的 rc／items 文字無機器核對（M20／M20b 存活） | 補抄或 TCS 改「去標籤與 emoji」 |
| F-09 | P3 | ADR-SIDB-003 SQL 草稿標題「三個區塊依序餵 psql」 | 單一 session（串成一檔）→14/14 表由 si_owner 擁有；三區塊各一個 session→rc 0 但 0/14 由 si_owner 擁有；字面有歧義 | 改「串成同一個 psql session（SET ROLE 跨區塊）」 |
| F-10 | P4 | ADR-003 草稿硬化備忘 | `GRANT INSERT ON ALL TABLES` 使 si_writer 對 meta、schema_migrations、import_runs 有 INSERT；PG 層只保證同交易 audit 列且雜湊欄相等，row_sha256 與內容一致靠 Python `state.replay` | P1 TCS 定稿時收斂 |
| F-11 | P4 | `781700bc` `guard_bucket_policy.py` | prose 5060→5234（+174）＝本審 census exclusive 5234、guard_self 3250 不動，理由在常數註解；裁決先於本審發生 | 維持（本審 PASS） |
| F-12 | P4 | TCS §5.3.1 A4／§5.3.2 | `skip_tag_policy.py:424` 關鍵字 `"tools/tests": 89` 於 tip 因重釘為 90 而消失；ctrl 對照另多 `test_schedule_capability_parity.test_scan_surface_is_not_silently_empty` | TCS 勘誤 |
| F-13 | P4 | 環境 | worktree 上 `si check` 多一個非阻塞 NE `events.dec_quote`（專案 slug 不同找不到逐字稿；主路徑存在）；P0 淨增 +563 高於 TCS 預演估量 +420／+515（S-A 結論不變，名冊 15220→15783 已重登） | TCS §5.5 估量勘誤 |
| F-14 | P4（NE） | G-P0-8 FSM 半、G-P0-2(b)、MU-LD0-31 | FSM 狀態檔在主 repo 未追蹤的 `build/`，任務書禁讀；去 FSM 迴圈版對 fdd9a738 與 d4aeab5b 皆 rc 0 全 OK | 主控補跑完整 `errata_check.py`（見 §D） |
| F-15 | P4 | Errata E-4 核准座標 sid c61e3847 line 4437 | 該行是 AskUserQuestion 的作答（type=user 的 tool_result）；內容「L-1～L-6 全部採建議值」，與 PRD §13.2 L-6＝OQ-3、PRD 勘誤一標頭同座標，一致 | 無 |

### C. ⚖ 裁決（審查者對證據；主控採納）

- 結論 PASS 採納；無修復棒、無二審。P3 九項處置：F-06／F-07 以 DT 補強本輪結案（`PATCH_STAGES` 值域與塊對階段、`test_AT_LD_00_D5_E_1` 六變體反例；c1c2 同 commit 重釘）；F-08 基準檔列補 `✅ `、F-09 ADR-SIDB-003 兩處改「串成同一個 psql session」（同 commit）；F-01～F-05、F-12、F-13 入 TCS〈勘誤一〉1-1～1-12（只動勘誤節，正文不改）；F-10 留 P1 TCS 定稿；F-11 維持；F-14 主控補跑（§D）；F-15 一致、無事。
- F-01 的結構解（`_KNOWN_LITERAL_PATH_CONSUMERS` 登記）屬 AISDLC_SDD/scripts，不在 P0 允許集合，P1 立案；本輪 TCS 勘誤先把「漏列即紅」改述為「對稱鎖守兩邊同步」。

### D. 閘門 rc（審查者於 worktree／副本自跑；主控補跑另列）

| 閘門 | 結果 |
|---|---|
| 全套（worktree） | rc 0；6010 個測試；skip 46；M6 成立；TEMP／console 圍籬綠 |
| DT 全檔 | 14 OK；逐 AT 14 個 rc 0 |
| G-P0-1（逐 commit 聯集） | rc 0；21 檔 ⊆ §5.7.1 |
| G-P0-2(a) | rc 0（base fdd9a738）；(b) 見主控補跑 |
| G-P0-3 | `test_root_module_layout` 9 OK |
| G-P0-4 | base／probe 92／92 同；ctrl 新增紅＝c1c2 三項＋E501 棘輪＋F-12 |
| G-P0-5 | 普查三表 ⊆ 允許集合；帳本盲實驗：新增失敗只在 A.4 的 8 檔＋5.4.2b 的 1 項 |
| G-P0-6 | rc 0；35 行逐列相同；腳本未寫檔 |
| G-P0-7 | PG18 容器 rc 0；14／14 owner=si_owner；負控 9／9 rc 3；清除驗證 |
| G-P0-8（去 FSM 版） | fdd9a738 與 d4aeab5b 皆全 OK |
| G-P0-9／10 | `si check` rc 0、rows=338 items=33、指紋等於基準；十個釘座標成立 |
| G-P0-11 | isolated E501 與全規則 ruff 皆 All checks passed；import 合規 |
| G-P0-12 | `--print-guard-lines` +0；十個鎖檔各 rc 0；ruff／compileall／baseline_sites／ntfs／loc_budget rc 0 |
| G-P0-13 | `[]`；secret_scan 20 檔 rc 0 |
| **主控補跑 G-P0-8（含 FSM 狀態檔，主 repo，base fdd9a738）** | `errata_check` rc 1，逐列：六鍵 PRD／TCS／SOP 列與議題中心兩鍵 PRD／TCS 列全 MATCH；DIFF 僅 `agentconsole-si-decide`／`-mirror` 的 `Architecture.md` 與 `ADR-002-Frontend-Design-System.md`（他鍵漂移，F-03；P0 四 commit 不動該兩檔）與 `monorepo-selfimproving`（已知，案文載明）⇒ 依勘誤一 1-3 判準為 PASS |
| **主控 DT（本輪補強後）** | `python -B -m unittest discover -s tools/tests -p test_selfimproving_ledgerdb_p0.py -v`：15 個皆 ok，rc 0；`ruff --isolated --select E501` 與全規則皆 All checks passed |

### E. TCS／文件勘誤（主控處置）

TCS〈勘誤一〉1-1～1-12（對應 F-05、F-04、F-03、F-02、F-01、F-12、F-06、F-07、F-08、F-13、F-09、F-14；全文見 TCS 檔尾）；PRD 無勘誤。ADR-SIDB-003 §SQL 草稿標題與執行方式第 1 條、基準檔 SKIP-M6 列同 commit 修正。

### F. 環境事實與摩擦（審查者；主控處置）

1. harness 拒寫報告類檔名（「Subagents should return findings as text」）⇒ 報告由主控落檔（本檔）；原始資料與腳本在主控 scratchpad `qa\p0\`。
2. 安全檢查把含 `\t3\` 的 `Remove-Item` 誤判為刪系統路徑 ⇒ 鏡改用 Python 刪除副本；worktree 由主控收。
3. bsdtar 解 `git archive` 遇中文檔名報 Invalid empty pathname ⇒ 改 Python tarfile（1184／1184 檔）。
4. 突變 harness 第一版因同秒改寫＋同大小使 `.pyc` 沿用舊碼（M40 起受污染，被 FINAL-CONTROL 紅抓到）⇒ `PYTHONDONTWRITEBYTECODE=1`＋清 `__pycache__` 重跑，§A 數字為乾淨重跑。
5. 前景 `Start-Sleep` 被擋 ⇒ `Process.WaitForExit` 有界等待。
6. 副本為部分樹 ⇒ G-P0-4 兩邊同紅 49 檔、G-P0-5 逐檔數字與起草值不同，結論性不變量皆成立。

### H. 凍結與放行紀錄

- 主控親驗（本機 Windows 11，2026-10-31）：DT 15 ok；G-P0-8 補跑（§D）；c1c2 重釘第十三列含本輪 DT 補強（`--print-guard-lines` 收斂 +0）；根層全套 rc 0 於收尾 commit 前重跑（見 commit 訊息）。
- 勘誤套用（主控，凍結後修訂路由第 4 點）：TCS 檔尾〈勘誤一〉1-1～1-12；PRD 不變。新 digest 由 `spec-refreeze` 記入（見下）。
- FSM 鍵 `monorepo-si-ledgerdb-p0`（主控依凍結常態規則執行）：IMPLEMENTATION → `transition --to PR_REVIEW` → `gate PR_REVIEW PASS`（→ RTM_VERIFY；報告＝本檔）→ RTM `docs/06_quality/RTM-SelfImprovingLedgerDb-P0-20261031.md`（AT 38／38）→ `gate RTM_VERIFY PASS`（→ RELEASE_READY）→ `spec-refreeze --doc PRD --doc TCS`（結果與 digest 填於下一行）。
- refreeze 結果（2026-10-31 14:0x，主控執行 `spec-refreeze --doc PRD --doc TCS` rc 0）：`refrozen: true`、`stage: Stage-2`、`supersedes: 2026-10-27T16:42:35+00:00`；記入 PRD `sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4`（不變）、TCS `sha256:3aadc7a78da88605d992a67a890ea3d9ceec02a818edd576411e8aa4de5b0119`（含〈勘誤一〉1-1～1-12；Stage-2 原值 `sha256:fec0a41a…a9364f`）。鍵狀態 RELEASE_READY。
- RELEASE：P0 交付全為文件與一支 DT 檔、無執行期面；RELEASE 轉移待掌舵者裁示（依本檔證據放行，或留至 P1 一併）。
