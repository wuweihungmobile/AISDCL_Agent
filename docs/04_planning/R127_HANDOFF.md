# R127 交棒書（落地輪；技術債總清償循環令 v2 第二投）

- **輪籤**：R127（2026-09-04，Windows 11；下一個窗口＝mac）
- **輪型**：**落地輪**——R126 交棒書點名的落地候選中挑三筆真的動手（`DEF-200-206` 裁決已在、
  `DEF-200-133` P1 新判準、`DEF-200-260` 與護欄層搬遷同檔合併），並兌現款(11)「本輪淨額必須 ≤ 0」
  （以回歸鎖軌分流＋散文搬遷抵銷達成功能軌淨額 0）。
- **帳本**：未結列 **36 → 34**（結 3、新立 1：`DEF-200-264`；`--unresolved-count` 實跑見〈已驗證〉）。
- **護欄層**：<!-- guard-total:R127 --> 行數 `92306→92268`（淨額 −38）。主表淨額 ≤ 0 ⇒ 款(11)
  連續上升 streak（R123／R126）歸零；回歸鎖軌 R127 列另申報 `DEF-200-133` 新增 159（記帳誠實度）；
  款(10) 上限 555 未撞；款(12) 到期輪 128／目標 552 未到。逐檔、對帳與落地時被自己鎖抓到的一次
  （分軌對真表測試無效）＝`docs/06_quality/CrossPlatform_R127_Scan_Findings.md` §1。
- **commit／push／雲端 CI**：本檔刻意**不寫死** commit sha／push_rc／雲端結論（寫死就得再開一個
  docs-only commit，而那個 commit 又讓本行過期）。現查：`git log -3 --oneline`、
  `gh run list --branch main --limit 6 --json headSha,name,status,conclusion`；本輪結案回覆已逐支列出。
- **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；所有數字皆本 session 親跑。

## 本輪方法

1. 三包唯讀勘查（`model: sonnet`）兩支 `tools/tests/` 鎖檔與三支 `tools/lib/` 生產護欄檔的可搬散文；
   結論＝兩支鎖檔剩零星（cbg 約 57 行、quota_policy 約 25 行），`hook_wiring.py` 敘事全住 `#` 註解
   ⇒ docstring 搬遷對舊尺零效益（U9 因此只能具名展延，見〈守衛線〉）。主表要真的 ≤ 0 得再搬
   `test_doc_loc_baseline_freshness_r60.py`（本輪親讀十四段，−165）。
2. `DEF-200-206` 動碼前寫五題設計卡，派 Architect／SA／SD 三鏡唯讀複審；三方條件全數落地
   （Q1 出廠值採 PRD 的 5、Q2 前綴、Q3 ABORT 補進 PRD 條文、Q4 非法值併入 hold、Q5 §5／§9 附證偽錨）。
3. 全部程式碼與帳本編修由本單一窗口序列完成；`Workflow` 工具在 weekly_scoped converge 帶被
   `context_budget_guard` 整支擋下 ⇒ 全程逐一 `Agent`（每 300s ≤3）。
4. 實作 diff 過定點程式碼複審（Architect／SA／SD 一審全查），結論見證據檔 §E。

## 本輪結案 3 筆＋新立 1 筆（逐筆取證在證據檔同名 §）

| ID | 一句話 | 針對驗證（親跑） |
|---|---|---|
| `DEF-200-206` | PRD v2.1.15：§6 三鍵前綴對齊、`CONFLICT_POLICY` 三值對齊＋ABORT＝拒絕啟動、兩鍵補 env 讀取路徑、出廠值 2→5；④ F5／§7 綠、§5／§9 查無具名文字 | 四支測試檔 `111 passed` |
| `DEF-200-133` | tracked `.py` 的靜態 import 指向「在磁碟、不在 index、未被 ignore」的檔即紅（AST，四支純函式＋測試類別） | `-k Def200133` 5 passed／7 subtests；真倉庫突變抓到 2 筆 |
| `DEF-200-260` | cbg 全檔 `mkdtemp` 改走 `_tmpdir()` helper（既有 addCleanup 行併入）＋AST 鎖 | cbg＋quota_policy `805 passed, 602 subtests` |
| `DEF-200-264`（新立） | `main.run_boot_self_check` 呼叫 `estimate_freeze_bytes` 未傳 `state_bytes`／`retain_versions` ⇒ PRD R-6.2-3 ② 從未計入 | 三方複審 SD 鏡發現；open |

## 已驗證（本 session 實測；rc 皆自成一句讀取）

- 三本帳：`check_defect_log_crossref.py` rc=0（未結存量 **34** 列、193 筆有效狀態紀錄、逐列 ≤700 bytes
  ——過程中三列超標（含一列既有豁免列被改長 219 bytes），依 R124 體例瘦身、原文逐字保全於
  `CrossPlatform_R127_Debt_Closure.md` 同名 §）；`check_archive_required.py` rc=0。
- AutoClaude 針對測試：`pytest tests/test_r100_boot_self_check.py tests/test_r100_dirty_worktree_rescue.py
  tests/integration/test_def_200_205_production_wiring.py tests/test_r100_power_loss_protection.py -q`
  → `111 passed`；ruff 對全部改動檔 `All checks passed!`（不帶 `--config`）；`check_loc_budget.py` rc=0
  （`hook_wiring.py` 398／400 為既有 warn，本輪未動它）。
- 根層針對測試：`-k Def200133` → `5 passed, 272 deselected, 7 subtests passed`；
  `pytest tools/tests/test_context_budget_guard.py tools/tests/test_quota_policy.py -q` → `805 passed, 602 subtests passed`。
- 守衛線：`--print-guard-lines` 重釘後 `92306→92268 (-38)`、逐檔漂移 0；落地當回合被自己的鎖抓到兩次：
  ① 只搬兩檔時主表 +127，真表測試 `test_the_real_repin_log_stays_inside_the_cost_envelope` 不吃分軌 ⇒
  `[只升不降]` 三連紅；② 分軌宣告 159 > 主表 127 觸發「子項不得大於母項」。解法＝再搬第三支鎖檔讓
  主表真的 ≤ 0（Scan_Findings §1／§2 第 7 點）。
- ONBOARDING 表①②：以乾淨 venv `autoclaude_cleanvenv_20260904` `--write --with-slow` 回填（AutoClaude
  測試樹因新增測試而指紋變動）；結果與全套 `python tools/run_root_unittests.py` 的 `rc=` 一併寫在本輪
  結案回覆（背景執行、親讀 log 尾端）。

## 守衛線（款(10)(11)(12)＋U9）

- 主表 R127 列 `92306→92268（−38）`＝`DEF-200-133` 回歸鎖 +159 與同檔沿革散文搬出 −165
  （`test_doc_loc_baseline_freshness_r60.py` 7131→7125）＋散文搬遷與 `DEF-200-260` helper 合併
  （cbg 9902→9860、quota_policy 3406→3396）＋鎖檔自身重釘與 U9 展延（7278→7298）。回歸鎖軌列申報
  實際 159（主表 ≤ 0 時「子項不得大於母項」不判）；款(11) streak 歸零。
- **U9（四支 `[ROOT-TOOLS]` 檔舊尺債）到期輪 127 → 130 具名展延**：本輪舊尺親量 over_by＝quota_gate 90／
  quota_meter 67／hook_wiring 28／planner 0；勘查證實 `hook_wiring.py` 零段 docstring 敘事，搬遷手法對它
  零效益，28 行只能靠真拆。理由逐字寫在 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 旁；勘查座標＝
  Scan_Findings §3（真拆窗口可直接消費）。

## 還沒做（不塗綠；每筆帶現查指令）

1. **U9 真拆尚未執行**（到期輪 R130）：`quota_gate.py`／`quota_meter.py` 的 docstring 敘事可搬約 76／66 行
   （座標見 Scan_Findings §3），`hook_wiring.py` 28 行需抽共用模組。現查
   `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` 與舊尺量法（空行與行首 `#` 免費）。
   <!-- absent-if: _ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED = True -->
2. **`DEF-200-264` 尚未接線**：`main.run_boot_self_check` 對 `estimate_freeze_bytes` 仍未傳
   `state_bytes`／`retain_versions`。現查 `Select-String -Path AutoClaude/autoclaude/main.py -Pattern "estimate_freeze_bytes"`。
   <!-- absent-if: retain_versions=STATE_RETAIN_VERSIONS -->
3. **R121 呈報單檔頭狀態仍未改為 Adopted**（`docs/04_planning/AutoSDD_Adjudication_Packet_R121.md:3` 仍是
   Proposed），其推薦已被採用並逐筆結案（R121 8 筆、R126 13 筆、本輪 3 筆皆引用它）——屬呈報單項①。
   現查 `Select-String -Path docs/04_planning/AutoSDD_Adjudication_Packet_R121.md -Pattern "Status"`。
   <!-- absent-if: **Status**: Adopted（R121 -->
4. **剩餘 34 筆未結列還沒動工**（現查 `python tools/check_defect_log_crossref.py --unresolved-count`），分類：
   - 需掌舵者拍板（呈報單②～⑦）：`DEF-200-259`／`DEF-200-182`／`DEF-200-256`／`DEF-200-255`／
     `DEF-101-736`／`DEF-101-856`。
   - mac 真機或雙平台：`DEF-200-252`／`DEF-101-675`／`DEF-200-231`（mac 側 User 層值）／`DEF-200-165`。
   - 落地輪候選（裁決已在、只差實作）：`DEF-200-124`（M，prose 分桶棘輪 chunk 歸類；需四方）、
     `DEF-200-118`（M，PRD 層先定門檻）、`DEF-101-938`（M，shellcheck 接線）、`DEF-200-242`（M，先量
     `quota_burn.jsonl` 翻頁後第一拍扇出；本機該檔現查僅 64 列）、`DEF-200-253`（S；🔴 與 `DEF-200-183`
     生產者側 pgextras 軸綁定，183 未修前 re-key 會讓 AutoClaude 天花板整批退回 advisory）、
     `DEF-200-264`（S）。
   - 結構性／多子項：`DEF-200-207`（U1~U4 四方審查）、`DEF-200-197`／`198`／`199`／`203`／`193`
     （配速修憲 Adopted 待落地批）、`DEF-101-887`／`796`／`974`／`981`／`DEF-200-086`／`129`／`134`／
     `183`／`188`／`246`／`251`／`234`。
5. **側軌現況**（不計入分母）：外部阻塞軌 6 筆（`DEF-101-518`／`693`／`703`／`DEF-200-075`／`174`／`186`）、
   結構性長債軌 7 筆（`DEF-101-018`／`398`／`701`／`702`／`886`／`960`／`980`）。本輪尚未複查兩側軌
   （落地輪射程外）；現查 `python tools/check_defect_log_crossref.py` 輸出末兩行。
   <!-- absent-if: 側軌複查日 2026-09-04 -->

## 呈報單（需掌舵者拍板；白話分析見本輪結案回覆）

1. **R121 呈報單檔頭 `Status: Proposed` → 建議改 `Adopted`**（同 R126 ①，未變）。
2. **`DEF-200-259`（歷史列漂移座標）三選一**：(a) 明文豁免 append-only 就地訂正；(b) advisory 掃描器；(c) wontfix。
3. **`DEF-200-182` ①**：驗證清單「須涵蓋哪幾套閘門」判準的 SSOT 家（建議 `check_handoff_carriers.py`）。
4. **`DEF-200-256`**：LATEST `hub-push.yml` 兩處 `git diff --name-only` 缺 quotepath 旗標——現查該 workflow 只住
   `AISDLC_SDD/AISDLC_SDD_v0.*/.github/`（根層 `.github/workflows/` 無此檔，GitHub 不會執行子目錄 workflow），
   `_GIT_QUOTEPATH_DEBT` 已登記其為可見欠債；問題是要不要打破「各版此檔同一 blob」不變量只改 LATEST。
5. **`DEF-200-255`**：pgvector recall p95 門檻 50ms 壓在量測中位（實測 51.7ms），重訂或明文 opt-in 終態。
6. **`DEF-101-736`**：子項 560 wontfix 是否落款；649 待 macOS；880 待以新尺重算。
7. **`DEF-101-856` ⑥**：本機 Docker pgvector（pg18、alembic head）算不算「staging」等價替代；不算則遷外部阻塞軌。

## 證據位置

- 落地取證＋三方設計複審條件承接＋定點複審結論：`docs/06_quality/CrossPlatform_R127_Debt_Closure.md`。
- 護欄層淨額承認＋回歸鎖軌對帳＋途中發現＋U9 勘查座標：`docs/06_quality/CrossPlatform_R127_Scan_Findings.md`。
- 散文逐字保全：`docs/06_quality/CrossPlatform_R127_Guard_Prose_Migration.md`。
- PRD 施工圖：`docs/04_planning/PRD_Amendment_R127_EnvKeyAlignment.md`。
- 設計卡與複審 JSON（本機 session 暫存，不隨 repo 走）：
  `C:\Users\wuwei\AppData\Local\Temp\claude\d--CursorProject-AISDCL-Agent\f8f9fbfd-dbc2-4213-9518-84cbdade30fe\scratchpad\`
  （`R127_206_design_card.md`、`r127_code.diff`、`old_ruler.py`、`mkdtemp_refactor.py`、`mut133.py`）。
- 乾淨 venv：`C:\Users\wuwei\AppData\Local\Temp\autoclaude_cleanvenv_20260904`（表② 回填用）。

## 下一步（下一個窗口＝mac）

- mac 專屬列（`DEF-200-252`／`DEF-101-675`／`DEF-200-231` mac 側）在 mac 真機結案；Windows 實測值不外推。
- 款(11) 本輪已歸零 ⇒ 下一輪可承受一輪正淨額（連續上升第 1 輪），但仍建議先做尚未搬過的鎖檔搬遷
  （`test_platform_neutral_paths.py`／`test_check_defect_log_crossref.py`）；🔴 真表測試不吃分軌
  （Scan_Findings §2 第 7 點），別把回歸鎖軌當成款(11) 的出口。
- U9 真拆到期 R130：從 `quota_gate.py`／`quota_meter.py` 的 docstring 搬遷開始（Scan_Findings §3 座標），
  `hook_wiring.py` 另議抽模組。
- 每筆動碼前先重跑帳本原文比對現況；裁決卡引用的座標也要現查（本輪 R121 裁決指向的 §DEF-200-206 不存在）。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、push 不帶 `AUTOSDD_NET_RATCHET_OFF`。
- 不准把〈還沒做〉④ 的 34 筆順手改成已結——皆逐筆核實仍需動工、裁決或 mac 真機。
- 不准同時派多個 agent 平行編修帳本或同一鎖持有面（鐵律七檢查表）。
- 全套 `tools/run_root_unittests.py` 一律親讀 log 尾端 `rc=`；push 一律背景執行並讀 `push_rc=`；
  逾時（rc=143）先 `git fetch` ＋ `git log origin/main..HEAD` 判斷是否已送達。
- ONBOARDING 表② 回填一律乾淨 venv，禁 `--allow-pg-extras`。
