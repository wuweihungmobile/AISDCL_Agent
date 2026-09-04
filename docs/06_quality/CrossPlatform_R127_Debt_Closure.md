# R127 落地輪 — 缺陷結案存證

> **性質**：技術債總清償循環令 v2 第二投（2026-09-04，Windows 11）。R126 交棒書點名的落地候選中
> 挑 `DEF-200-206`（裁決已在、只差實作）、`DEF-200-133`（P1、新判準）、`DEF-200-260`（同檔可與
> 護欄層搬遷合併）三筆真的動手；帳本另立一筆本輪三方複審抓到的接線缺口（`DEF-200-264`）。
> **帳本未結列**：起 36 → 訖見 `R127_HANDOFF.md`（本檔逐節記各筆的落地取證；帳本列只放索引）。
> **護欄層**：本輪主表淨額為負（三支鎖檔散文搬遷抵銷 ＞ 回歸鎖新增），款(11) 連續上升 streak
> 歸零；回歸鎖軌另申報 `DEF-200-133` 的新增量。對帳與自我抓包見 `CrossPlatform_R127_Scan_Findings.md` §1。
> **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；轉述並行包交件一律標
> `[他包回報]`，主控親跑者不標。所有數字皆為本 session 親跑 tool_result。

---

## §0 方法與防互踩

1. 唯讀勘查三包（`model: sonnet`）：兩支 `tools/tests/` 鎖檔與三支 `tools/lib/` 生產護欄檔的可搬
   散文（含「別處是否逐字比對」的風險標記）。結論＝前幾輪已把大段沿革搬走，鎖檔剩零星段落；
   `hook_wiring.py` 的敘事全住 `#` 註解、docstring 搬遷手法對舊尺零效益（見 §U9）。
2. `DEF-200-206` 動碼前寫設計卡（五題），派 Architect／SA／SD 三鏡唯讀複審；條件全數落地後才
   結案（§DEF-200-206 表）。
3. 全部程式碼與帳本編修由本單一窗口序列完成；並行包只做唯讀。
4. 實作 diff 過定點程式碼複審，結論見 §E。

---

## §DEF-200-206 PRD v2.1 ↔ 實作三處歧異（R121 方向 A ＋ R127 三方定案）

**原文逐字保全（本輪帳本列瘦身前的「現象與證據」欄）**：「**PRD↔實作歧異批，依憲法須逐項裁決
「修實作」或「修憲」**：① `STATE_RETAIN_VERSIONS`（PRD §8-4 無前綴／值 5 vs `file_state_repository.py:37-38`
帶 `AUTOCLAUDE_`／值 2）；② `CONFLICT_POLICY`（PRD 三值 vs `boot_self_check.py:36` 兩值，互有對方沒有的值）；
③ 該兩鍵與 `DIRTY_SAVE_RETRIES` **零 env 讀取路徑** ⇒ 改設定不生效；④ §4.1.5 F5／§5／§7／§9 見§D-11」；
狀態欄原文為 open、載明承接輪號一〇一並註「①②③ 已複驗」（本檔依體例不逐字重現前瞻輪號句型）。

**裁決鏈**：掌舵者 2026-09-02 採 R121 呈報單方向 A（③②修實作、①修憲、預設值 2 vs 5 留四方定案、
④ 留待下一結案窗口複驗）。R121 裁決卡指向的「`CrossPlatform_R121_Debt_Closure.md §DEF-200-206`」
現查**不存在**（該檔對 `206` 零命中），設計依據改以本輪設計卡與三方複審結論為準（§4 表）。

**落地**：
- ② `execution/boot_self_check.py`：`CONFLICT_POLICIES = ("ABORT", "RETRY_WITH_AGENT", "HUMAN_REVIEW")`
  ＋具名常數 `POLICY_*`；`scan_queue()` 新增 `ABORT` 分支（有殘留項 ⇒ `problems` 非空＝拒絕啟動、
  清單照列為 `listed_only`、零重排；置於 band／DRY_RUN hold 之前——拒絕啟動不派工、不寫 worktree，
  與 G3／G5 相容）；非法字面併入 hold（只登記，不落預設重排——SD 定點複審抓到「problem 與
  『重排：X』同時印出」的矛盾）。
- ③ `CONFLICT_POLICY_ENV = "AUTOCLAUDE_CONFLICT_POLICY"`／`conflict_policy_from_env()`（非法值原樣回傳，
  交既有不變式 11 報紅）；`main.run_boot_self_check` 餵進 `boot_self_check(..., conflict_policy=…)`。
  `infra/adapters/dirty_worktree_rescue.py`：`DIRTY_SAVE_RETRIES_ENV = "AUTOCLAUDE_DIRTY_SAVE_RETRIES"`／
  `dirty_save_retries_from_env()`（非整數 ⇒ WARNING＋出廠值；超界 ⇒ WARNING＋既有夾取）；
  `core/wiring.build_worktree_rescue` 傳 `retries=`。
- ① 修憲 PRD v2.1.15（施工圖 `docs/04_planning/PRD_Amendment_R127_EnvKeyAlignment.md`）：§6 區塊 11／12
  三鍵加 `AUTOCLAUDE_` 前綴、§8 列 4 同步；出廠值**採 5**（三方 Q1：SA 條件「除非提出空間論證，
  否則回 PRD 的 5」；SD 條件「兩邊同值」），`file_state_repository.py` 出廠值 `"2"→"5"`。
  R-6.2-1 補述三值各一種行為、G1 驗收表加控制組 (iii)(iv)、§8 列 11 補 `ABORT`（SA blocking 條件）。
- `.env.example` 登記三鍵（皆有讀者；平常留註解）。

**④ 複驗**（帳本與 R121 裁決皆寫「見 §D-11」，現查 `CrossPlatform_R100_Scan_Findings.md:183-195` 的 §D-11
只有 ①②③ 三列，無 F5／§5／§7／§9 展開內容）：
- **§4.1.5 F5**（`TELEMETRY_UNMEASURED_CAP` ↔ `Policy.degraded_cap` 機械登記、出廠值在
  `1 ≤ degraded_cap ≤ cap_prepare`、`ENV_SPEC` 中治同一數字的鍵恰一項）：✅ `tools/tests/test_context_budget_guard.py`
  `UnmeasuredConvergesToThePrepareBandTest._DECLARED = ("TELEMETRY_UNMEASURED_CAP", "degraded_cap")`
  ＋ `test_f1_unmeasured_converges_to_at_most_the_prepare_cap`（含 F3 下界）＋紅綠自證
  `test_red_the_shipped_unclamped_form_did_exceed_that_bound`；`tools/lib/quota_policy_env.py:95` 為
  `ENV_SPEC` 內唯一 `attr == "degraded_cap"` 的項（全檔 `degraded_cap` 命中僅 :92 註解與 :95 該項）。
- **§7 schema 枚舉**：✅ PRD `:1941` 逐字 `PENDING_VERIFY|CONFLICT|VERIFY_FAILED|MERGED` ＝
  `boot_self_check.QUEUE_STATUSES`；`test_g1_the_injected_literal_comes_from_the_schema_enum_not_the_test` 鎖住。
- **§5／§9**：查無可複驗的具名發現文字。證偽錨（SA 條件；一旦出現就代表本結論失效）：全 repo
  `*.md` 對 `B4|B5|B6` 的非模板命中只有 `docs/06_quality/AutoSDD_Defect_Log.md:211`（`DEF-200-206`
  主列自己的「B4／B5／B6 併列」）與 `docs/06_quality/CrossPlatform_R100_Scan_Findings.md:114`（同一批次
  標籤表），兩處皆為「把七項打包成本列」的標籤，無任何一處展開 §5／§9 的內容；
  `docs/06_quality/CrossPlatform_R100_*.md` 對 `F5`／`§4.1.5` 零命中（Grep 當回合實跑）。定點複審 SA 鏡
  抓到本段初稿多寫了一個不存在的座標（帳本 :114 實為別列），已訂正——證偽錨自己的座標也要現查。
  <!-- absent-if: §D-11 §5 -->

**驗證**：`pytest tests/test_r100_boot_self_check.py tests/test_r100_dirty_worktree_rescue.py
tests/integration/test_def_200_205_production_wiring.py tests/test_r100_power_loss_protection.py -q`
→ `111 passed`，rc=0（含新增：PRD 鏡射鎖 `test_def_200_206_the_policy_enum_mirrors_the_prd_literal`
讀 PRD §6 那一行的枚舉字面與出廠值；`ABORT` 三支；env 讀取；非法值＋非空佇列不重排；`main` 接線鎖；
`dirty_save_retries_from_env` caplog；wiring `retries` 注入）；ruff 對全部改動檔 `All checks passed!`；
`check_loc_budget.py` rc=0。

**三方設計複審條件承接**（Architect／SA／SD，`model: sonnet`，唯讀；全文摘要在施工圖 §4）：
Architect blocking「三處（程式 2／PRD 5／`.env.example` 引用不存在的 v2.1.15）不一致」→ 同批收斂為 5
＋ v2.1.15 列真的落在修訂表；SA blocking「PRD 條文未收錄 ABORT」→ R-6.2-1／§8 列 11／G1 (iii)(iv)；
SA blocking「§5／§9 查無具名項須附證偽錨」→ 上段；SD blocking「PRD 三行仍舊字面」→ 已改；
SD non-blocking「非法值＋非空佇列落預設重排」→ 併入 hold ＋測試；SD non-blocking「`listed_only` 同時承載
ABORT 與只登記兩種語意」→ 記途中發現（`CrossPlatform_R127_Scan_Findings.md` §2），不另立列；
SD Q1「`retain_versions` 未接進 `main.py` 的 `estimate_freeze_bytes` 呼叫」→ 新立 `DEF-200-264`。
Architect non-blocking「測試檔無讀 PRD 文字的比對」與現況不符（`_prd_conflict_policy_literals()` 讀 PRD），
判為該鏡讀到編修前快照，不採。

## §DEF-200-133 「已追蹤檔引用未追蹤檔」的 Python import 判準

**原文逐字保全（本輪帳本列瘦身前的「現象與證據」欄）**：「**「已追蹤檔引用未追蹤檔」這一向零判準**。
實例＝`AutoClaude/tests/helpers/fake_pty.py` 未追蹤，被已追蹤的 `tests/test_gap014_020.py:41`／
`tests/test_gap039_049.py:27` 於 module 層 import ⇒ 漏 `git add` 時 CI 收集期 ImportError，實測波及 **83 支**
（57+26，非僅 fixture 那 11 支），本機恆綠。既有 `TestR81GhostPathClaims` 只在檔真的不在時才說話（問磁碟＋
gitignore，不問 `git ls-files`），射程亦不含 import」；分流去向原文：「判準＝「解析得到、但標的既非 tracked
亦非 gitignored」；材料 `repo_known_paths()` 已在同模組內」；狀態欄原文為 open、先後載明承接輪號九五與一〇一
（本檔依體例不逐字重現前瞻輪號句型）。

**落地**（`tools/tests/test_doc_loc_baseline_freshness_r60.py`，不新增鎖檔）：
- `python_import_targets(source, rel)`：AST 解析 `import a.b`／`from a.b import c`（含相對 import），候選＝
  每個解析基準（該檔所在目錄的每一層祖先直到 repo 根，對應 pytest rootdir／`sys.path` 注入面）下的
  `a/b.py`／`a/b/__init__.py`／`a/b/c.py`。動態 import 不在射程（誠實劃界寫在 docstring）。
- `collect_import_claims(repo_root)`：掃描面 `AutoClaude/`、`tools/`、`.claude/hooks/`、`AISDLC_SDD/scripts/`
  的 tracked `.py`（刻意不含三十個版本樹）。
- `files_on_disk(repo_root)`：`os.walk` 逐字大小寫的磁碟存在集（不用 `Path.exists()`——Windows 不分大小寫，
  同 `TestR81GhostPathClaims` 的跨平台牙）。
- `untracked_import_problems(claims, tracked, present, ignored)`：候選在磁碟、不在 index、未被 `.gitignore`
  排除 ⇒ 紅。純函式，紅綠合成自證。
- `TestDef200133TrackedImportsDoNotPointAtUntrackedFiles`：真倉庫綠／擷取器非空（>500 筆候選且含本檔自己
  的 `from lib import git_paths` 解析）／合成注入紅／tracked・ignored・absent 三對照組綠／相對與絕對
  import 展開座標（含語法錯誤檔回空）。

**驗證**：`pytest tools/tests/test_doc_loc_baseline_freshness_r60.py -k Def200133 -q` → `5 passed, 7 subtests passed`，
rc=0。**真倉庫突變**（scratch 探針 `mut133.py`，可重現指令：以本檔判準函式對真倉庫算一次
`collect_import_claims`／`files_on_disk`／`tracked_files`，再把 tracked 集合減去
`AutoClaude/tests/helpers/static_vocab.py` 重算 `untracked_import_problems`）：`claims=53053 present=794`，
基準 `problems=0`，突變後 `problems=2`（兩支 import 它的 tracked 測試各一筆）⇒ 判準對真實資料有牙、
非只對合成語料。探針原檔住 session scratchpad（見 `R127_HANDOFF.md`〈證據位置〉），不隨 repo 走。

**同檔同輪散文搬遷**：為讓主表淨額 ≤ 0（款(11)），本檔另搬出十四段沿革散文（模組 docstring WHY、
R69 ADR 量測 token 立案、鐵律三分子／分母 floor 的逐格沿革、幽靈符號掃描器三面擴張與 grandfather
理由、第三態立案等）逐字保全於 `CrossPlatform_R127_Guard_Prose_Migration.md`〈test_doc_loc_baseline_freshness_r60.py〉節；
該檔 7131→7125（回歸鎖新增 159 行、散文搬出 165 行）。

## §DEF-200-260 `mkdtemp` 站點的清理改走 helper

**落地**（`tools/tests/test_context_budget_guard.py`）：新增 `_tmpdir(case, prefix)`（`mkdtemp`＋
`addCleanup(shutil.rmtree, path, True)`）；全檔 `Path(tempfile.mkdtemp(...))` 站點改走 helper（含兩處住模組層
helper `_cred_kwargs(test, …)` 的站點，以既有 `test` 參數承接），既有的 `self.addCleanup(shutil.rmtree, …, True)`
行併入 helper 後刪除。`TmpdirHygieneTest`：AST 鎖「`tempfile.mkdtemp` 只准出現在 `_tmpdir` 內」＋行為驗
（掛在另一個 `TestCase` 上，`doCleanups()` 後目錄不在）。R96 §F-⑤ 的「哪些站點需要保留殘留供取證」問題：
本檔全是測試暫存，`DEF-200-153` 取證的是生產側殘留，兩者不同面，無需保留。

**驗證**：`pytest tools/tests/test_context_budget_guard.py tools/tests/test_quota_policy.py -q` →
`805 passed, 602 subtests passed`，rc=0（含新增 hygiene 兩支）。

## §DEF-200-264 `retain_versions` 未接進生產空間預估（新立）

SD 鏡於 `DEF-200-206` Q1 複審中發現：`autoclaude/main.py::run_boot_self_check` 呼叫
`estimate_freeze_bytes([Path.cwd()])` 未傳 `state_bytes`／`retain_versions` ⇒ PRD §6.2 R-6.2-3 ② 的
「state.json 與其保留版本份數的大小」從未計入可用空間預估；本輪把出廠值 2→5 對該預估零效果。
不併入 206 結案（206 三項皆已落地、本項是另一半接線缺口），另立列以免失承接。
解鎖＝接線（checkpoint 檔大小 × `STATE_RETAIN_VERSIONS`）＋接線鎖並附紅綠。

## §U9 四支 `[ROOT-TOOLS]` 檔舊尺技術債：到期輪 127 → 130（具名展延，附新事實）

`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=127` 在本輪重釘後即到期。本輪以舊尺（空行與行首 `#` 免費、其餘計價；
ADR-XPLAT-013 §9.3 逐字）實測：`quota_meter.py` over 67（old 467／400）、`session_resume_planner.py` over 0
（old 744／750 tier）、`hook_wiring.py` over 28（old 428／400）、`quota_gate.py` over 90（old 590／500）；合計 185
（R116 記 187）。唯讀勘查 `[他包回報]`：`quota_gate.py` docstring 敘事約 84 行（含一段與
`test_quota_policy.py:1525` 逐字重疊的 high risk）、`quota_meter.py` 約 111 行（六段與 `test_context_budget_guard.py`
／`test_claim_provenance_r86.py`／`check_claim_provenance.py` 有逐字或欄位名重疊）、**`hook_wiring.py` 零段**
——全檔 docstring 皆單行、敘事全住 `#` 註解 ⇒ 「docstring 搬證據檔」手法對它零效益，28 行只能靠真拆。
真拆屬獨立重構持有面（鐵律七），本輪主軸為款(11) 護欄層淨額義務與結案 ⇒ 依 `root_tools_debt_due_problems()`
出口②具名展延至 R130（≤ 現查輪 127＋lookahead 5），理由逐字寫在常數旁（非沿用 R116 那段）。
逐檔勘查座標見 `CrossPlatform_R127_Scan_Findings.md` §3。

---

## §E 實作 diff 的定點程式碼複審（Architect／SA／SD 一審全查 ＋ QA 對最終工作樹終審；`model: sonnet`，唯讀）

| 職能 | verdict | blocking 發現 → 處置 |
|---|---|---|
| Architect | APPROVE | 零 blocking。核實：枚舉更名全庫無殘留活碼引用；兩條 env 讀取路徑真的接線（非蓋好沒接電）；ABORT 分支先於 hold、問題正確傳播到 `BootReport.ok`；PRD v2.1.15 五處條文；搬遷逐字相符；回歸鎖軌 159 與 diff 新增行精確相符；U9 展延理由為本輪新量測。non-blocking：133 判準的絕對 import 基準展開偏寬（`claims=53053`）、`listed_only` 雙語意（已記 Scan_Findings §2）、`DEF-200-264` 已獨立立列 |
| SA | AWC → 已修 | blocking：§DEF-200-206 ④ 的證偽錨多寫一個不存在的座標（帳本 `:114` 實為 `DEF-101-803` 列）⇒ 刪除該座標、保留 `:211` 與 R100 Scan `:114`，並在該段記下「證偽錨自己的座標也要現查」。non-blocking：133 突變數字缺可貼上重跑的指令（本節下方已補最小腳本）；`DEF-200-264` 列 ≈572 bytes、零輪號 ✓；PRD 修訂表非嚴格時間序為 R126 既有狀態 |
| SD | AWC → 時間差＋已修 | blocking：帳本／棘輪表宣稱 `test_doc_loc_baseline_freshness_r60.py` 7290 而工作樹實為 7126 ⇒ 該鏡讀的是 diff 快照，工作樹當時已完成第三支鎖檔搬遷（7125）並重釘；最終值 7125 與 `_FROZEN_GUARD_LINES`／兩張表一致（QA 終審再核）。non-blocking：軌列「靳」錯字（已隨改寫消失）；`DirtyWorktreeRescueAdapter._retries` 是原始值須經夾取——已加註解；133 基準展開的理論假紅面（stdlib 同名未追蹤 `.py`）與 hygiene 鎖只認 `xxx.mkdtemp` 形態——皆為可接受劃界，記於此 |
| QA（最終工作樹） | APPROVE | 零 blocking。逐字核對 cbg 八段＋quota_policy 三段＋doc_loc 至少八段搬遷；指標行 `round-label-ok` 只在真提及 R101+ 時出現且同物理行；四支檔行數（9860／3396／7125／7298）Read 檔尾一致；主表 −38＝四檔差量加總；sha 與指紋鏈 12 碼一致；兩處 `guard-total:R127` 一致；交棒書三鎖（DEF 編號無方括號縮寫、無舊符號反引號、還沒做節 list item＋stale 詞＋code span、四個 `absent-if` 錨全庫搜不到）；帳本四列首詞與 bytes；`_BARE_COUNT_RE` 零命中。non-blocking：diff 快照落後工作樹（E501 四行縮短與 sha 重釘在快照之後）；133 突變探針應把最小腳本貼進證據檔（下方已補） |

**複審流程自我抓包**：三鏡一審讀的是 diff 快照，之後主控又改了工作樹（第三支鎖檔搬遷、E501 縮短、sha 重釘）
⇒ SD 的 blocking 與 QA 的 non-blocking 都是「快照落後」；下輪複審前先定稿，或在任務書明說「以工作樹為準」。

**133 突變探針最小腳本（QA／SA 條件；與 session scratchpad `mut133.py` 同邏輯）**：

```python
import sys
from pathlib import Path
ROOT = Path(r"<repo>")
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools" / "tests"))
import test_doc_loc_baseline_freshness_r60 as T
claims = T.collect_import_claims(ROOT); present = T.files_on_disk(ROOT); tracked = T.tracked_files(ROOT)
victim = "AutoClaude/tests/helpers/static_vocab.py"
mutated = frozenset(tracked - {victim})
suspects = sorted({c for _s, c in claims if c in present and c not in mutated})
problems = T.untracked_import_problems(
    claims, tracked=mutated, present=present, ignored=T._check_ignore(ROOT, suspects))
print(len(claims), len(present), len(problems))   # 本輪實跑：53053 794 2（基準 tracked 不減 ⇒ 0）
```
