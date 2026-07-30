# Cross-Platform R62 Architect 收輪證據

> HEAD（動工前）`152f86a`（R61 最終 commit）；量測時點 2026-07-30，工作樹 `tools/tests/`
> 量測面乾淨（`git status --porcelain -- tools/tests/` 空輸出）。本輪**零生產邏輯變更**——
> 唯一的程式碼異動是 `tools/check_defect_log_crossref.py` 新增 3 行、把本檔登記進
> `_GOVERNANCE_DOCS`（純登記表新增，不改動任何判準/邏輯分支；四方複審皆已驗證安全）。
> 其餘全部異動落在治理文件（本檔、`ADR-XPLAT-002`、缺陷帳本）。完整裁決理由見
> `docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md`（R62 更新段）。

## 0. 本輪範圍決定（先講為什麼不是 Phase 1-C 全量）

任務書建議以 **Phase 2-E（BOM 正規化修復）** 為主軸。動工核實後發現：**Phase 2-E 早已
於 R60 round 3（commit `796c7a6`，該 commit 引入的程式碼註解／docstring 自述「P10-1」，
非 commit message 本身——已跑 `git log -1 --format=%B 796c7a6` 逐字核對，訊息全文不含
「P10-1」字樣）落地**——`tools/check_wrapper_thinness.py`
的 `_read_source()` 現況即為 `utf-8-sig`（見該檔 :320），5 支 `.ps1` hash 已重釘，且既有
`tools/tests/test_check_wrapper_thinness.py:382-504` 的 `TestBomIsNotContent` 類別已含五項
回歸鎖。`ADR-XPLAT-002` §5 Phase 2 表與 §8 交棒表把它列為「R62 待辦」是**過期宣稱**：本 ADR
撰寫於 R60（量測時點 HEAD `e3a5c53`），而 P10-1 是同輪稍晚由另一個平行修復包產出、隨
`796c7a6` 入庫，ADR 定案時未追蹤到；R61 沿用 ADR 舊文字、同樣未重新核實，於是這個「已解決」
狀態延續掛成兩輪的待辦。

原定主軸落空後，重新評估 Phase 1-C 全量（(a)(b)(d)：`_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT`
共 23 個條目升級為 `(tier, reason)` tuple + 4 組異名對等品字典化 + tier3/tier4 reason 關鍵詞
斷言）是否「風險可控、本輪可做」。判斷：**風險評估與 R61 相同、未因本輪其他發現而改變**——
仍是「23 個條目逐一指定 tier ＋ 至少 3 支既有測試檔（`test_check_script_parity.py:248`／
`test_onboarding_parity_interlock.py:105/114`）對字串型別的依賴須同步改寫」的多檔連動重構。
比對本輪待辦清單，任務書明訂的兩項**強制**產出——① 真跑 `windows_smoke_local.ps1` 補齊 R61
遺留的驗證缺口、② 全專案 Scan-A~H 複掃——本身就需要完整的時間與注意力投入，且都是「驗證
既有成果」而非「新增變動面」的低風險工作。在「訂正過期宣稱＋補齊驗證缺口＋全專案複掃」已經
是紮實產出的前提下，把 Phase 1-C 全量硬塞進同一輪會擠壓驗證品質，且不符合 R61 自己留下的
教訓（「做安全的那一半也算數，不必每輪都衝最大膽方案」）。**決定：本輪不做 Phase 1-C 全量，
改派 R63**（具體解除判準見 `ADR-XPLAT-002` §8 項目 4）。

本輪實際交付：①訂正 `ADR-XPLAT-002` 對 Phase 2-E 的過期宣稱；②以原生 PowerShell 真跑
`tools/windows_smoke_local.ps1`，補齊 R61 §5 1-B 列明文記載的「未跑」缺口；③全套既有回歸
測試重跑確認零回歸；④全專案 Scan-A~H 複掃確認零新缺陷。

## 1. 發現：Phase 2-E 已於 R60 round 3 完成（治理文件過期宣稱訂正）

```
$ git log -S"utf-8-sig" --oneline -- tools/check_wrapper_thinness.py
796c7a6 fix(cross-platform): Mac/Windows 11 相容性 R60 round 3 — 耐久性 checkpoint（四方複審 round 3 尚未執行）
```

`796c7a6` commit message 逐字（節錄）：

```
- **`check_wrapper_thinness._normalize()` 把 UTF-8 BOM 算成一行**（全庫 137 支 tracked `.ps1` 中 76 支帶 BOM，
  76/76 正規化行數受影響）。收斂為單一 `_read_source()`（utf-8-sig），5 支 `.ps1` hash 重釘，
  正當性以「新正規化文字 ≡ 舊文字刪掉那一行純 BOM 假行」機械驗證。
```

現況原始碼（`tools/check_wrapper_thinness.py:320`）：

```python
def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")
```

既有回歸鎖（`tools/tests/test_check_wrapper_thinness.py:382-504`，`TestBomIsNotContent` 類別，
五項斷言）：`test_bom_does_not_become_a_normalized_line`／`test_bom_presence_does_not_change_hash`／
`test_read_source_strips_bom_for_both_extensions`／`test_real_ps1_wrappers_really_carry_bom`
（反恆真前提檢查）／一支以 `ast` 斷言 `read_text(encoding=…)` 全檔僅一處且值為 `utf-8-sig` 的鎖
（docstring 逐字：「P10-1：三處各自 read_text 是本缺陷的根因」）。

**R62 複驗**：

```
$ python tools/check_wrapper_thinness.py
✅ wrapper 薄殼守門通過（14 支殼 hash 釘選 + 行數上限皆正常）
REAL_RC=0

$ python -m pytest tools/tests/test_check_wrapper_thinness.py -q -k "Bom or bom"
.....                                                                  [100%]
5 passed, 27 deselected, 2 subtests passed in 0.15s
```

`ADR-XPLAT-002` §5 Phase 2-E 列、§8 交棒表項目 5、§1 狀態列已同步訂正為「已於 R60 round 3
結案」，並註明本 ADR 原文未追蹤到同輪平行包產出的過期宣稱成因。

## 2. 補齊：windows_smoke_local.ps1 真實驗證（R61 §5 1-B 列明文遺留缺口）

R61 證據文件（`CrossPlatform_R61_Architect_Evidence.md` §3 第 2 點）就 Phase 1-B 明文自陳：

> 兩平台 smoke 的 install/uninstall 往返 + linked-worktree 拒絕三情境須全綠……**未跑**
> （本輪只驗證登記層／hash 層，未起 windows_smoke_local.ps1 真實安裝……）

本輪以**原生 PowerShell**（非 Git Bash，避免 DEF-101-511 載具假紅）真跑：

```
$ powershell -NoProfile -ExecutionPolicy Bypass -File tools\windows_smoke_local.ps1
repo 根：D:\CursorProject\AISDCL_Agent
PowerShell：5.1.26100.8875（Desktop）
git：git version 2.51.0.windows.1
python：Python 3.11.9

--- [1/9] Parser 解析檢查 --- ✅ PASS: Parser 解析全數通過（21 檔／四棵樹）
--- 建立 fake repo --- ✅ PASS: fake repo 建立完成
--- [2/9] AutoClaude/tools/install_git_hooks.ps1 安裝／解除往返 --- ✅ PASS
--- [3/9] install_git_hooks.ps1 於 linked worktree 應拒絕 --- ✅ PASS: rc=1 as expected
--- [4/9] AISDLC_SDD/scripts/install-hooks.ps1 往返 + worktree 拒絕 --- ✅ PASS（往返）✅ PASS（拒絕 rc=1）
--- [5/9] install_post_commit.ps1 worktree 實跑 + 移除後路徑斷言 --- ✅ PASS
--- [6/9] 非 ASCII 路徑防護抽驗（「煙霧測試」目錄）--- ✅ PASS
--- [7/9] install_git_hooks.ps1 於「-Command 非典型呼叫鏈」linked worktree 仍應拒絕 --- ✅ PASS: rc=1 as expected
--- [8/9] check_ntfs_paths.py + check_script_parity.py --- ✅ PASS ✅ PASS
--- [9/9] tools\install_windows_nightly.ps1 -WhatIf 預覽 --- ✅ PASS

===== 彙總：PASS=12 FAIL=0 =====
全部通過 ✅（Windows PowerShell 5.1 為本腳本的目標載體）
REAL_RC=0
```

**載具鑑別力確認**：執行前 `$env:MSYSTEM` 為空（原生 PowerShell 視窗，非 Git Bash 間接呼叫），
未觸發 DEF-101-511 的 MSYS 環境拒跑守門，符合 `windows_smoke_local.ps1` 檔頭「🔴 載具要求」。

**涵蓋情境對照任務書要求**：install/uninstall 往返（[2][4a]，含 R61 Phase 1-B 新收編的
`install_git_hooks.ps1`／`install-hooks.ps1` 兩對）＋ linked-worktree 拒絕（[3][4b][7]，含
一般呼叫鏈與「-Command 非典型呼叫鏈」兩種形態）**三情境皆真實驗證，非登記層/hash 層代理**。

## 3. 回歸複驗（Scan-F：全套既有測試重跑，確認治理文件異動零程式碼副作用）

```
$ python -m pytest tools/tests/ -q
1065 passed, 10 skipped, 1 warning, 368 subtests passed in 94.23s
REAL_RC=0
（368 subtests，較 R61 基線「1065 passed, 10 skipped, 367 subtests」多 1；以 `git stash push -u`
前後對照重跑同一指令〔A/B 測試〕確認：乾淨 R61 基線（HEAD `152f86a`，stash 掉本輪全部異動）
重跑得 367，restore 後回到 368——證實該 +1 確由本輪自身異動造成，非環境雜訊。逐檔二分定位
根因：僅還原 `docs/06_quality/AutoSDD_Defect_Log.md`（其餘 3 項改動保留）即回落 367；補回
該檔即回到 368。機械確認：`python -c "import archive_defect_log as ADL; p = ADL.plan();
print(len(p['movable']), 'DEF-101-615' in [v['id'] for v in p['movable']])"`（於 `tools/` 下執行）
印出 `2 True`——本輪新增的 `DEF-101-615`（狀態 `fixed@R62`、未被其他列宣告承接）落入
`archive_defect_log.plan()` 的「可搬遷」集合，使 `tools/tests/test_archive_defect_log.py::
TestPlanNeverProposesActiveRows::test_movable_rows_are_all_closed_and_unclaimed` 內
`for v in p["movable"]: with self.subTest(def_id=v["id"])` 迴圈多跑一輪，非測試環境/時序雜訊）

$ cd AutoClaude && python -m pytest tests/ -q
3767 passed, 208 skipped, 1 warning in 75.91s
REAL_RC=0
（與 R61 基線「3767 passed, 208 skipped」逐字相同）

$ python tools/run_root_unittests.py
REAL_RC=0
（既有 10 項 POSIX-only / symlink 權限 skip 清單不變，皆為既知平台劃界，非本輪新增）

$ cd AISDLC_SDD && bash scripts/ci-gate.sh
本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）
逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:1747 scripts/tests:249
REAL_RC=0
（與 R60 round 3 基線「1478 / 1747 / 249」逐字相同）

$ cd AutoClaude && PYTHONUTF8=1 lint-imports
Contracts: 8 kept, 0 broken.
REAL_RC=0

$ python AutoClaude/tools/check_loc_budget.py
[check_loc_budget v2-tiered] total=20361 baseline=17032 cap=20438 violations=0
REAL_RC=0
（total 與 R61 基線「20361」逐字相同——本輪零生產碼變更）

$ python tools/check_ntfs_paths.py
✅ NTFS 檔名檢查通過（27469 個 tracked 路徑，0 違規；最長 142 字元，warn>180/fail>200）
REAL_RC=0

$ python tools/check_defect_log_crossref.py
✅ 缺陷帳本跨文件狀態一致：帳本 99 筆有效狀態紀錄、4 份掃描目標皆無矛盾……
REAL_RC=0
（99＝寫入 `DEF-101-615` 之後、且 `check_defect_log_crossref.py` 已把本證據檔登記進
`_GOVERNANCE_DOCS` 之後的本輪最終狀態；寫入 `DEF-101-615` 之前的舊快照為 98 筆，
不是本輪最終數字，不可互換使用）

$ python tools/sync_onboarding_baselines.py --check
✅ [loc-baseline-live:] {'total': 20361, 'cap': 20438, 'violations': 0}
✅ [rootunit-baseline-live:] {'tests': 1069}
REAL_RC=0
```

**結論**：本輪治理文件異動（ADR + 本證據檔 + 缺陷帳本 + `tools/check_defect_log_crossref.py`
的 `_GOVERNANCE_DOCS` 登記表新增 3 行）對全部既有機械閘門**零生產邏輯副作用**——唯一的程式碼
異動是純登記表新增（不改動任何判準/邏輯分支，四方複審皆已驗證安全），故 `check_loc_budget`／
`lint-imports`／`ci-gate.sh` 三軌等數字仍與 R60 round 3／R61 基線逐字相同；`tools/tests/`
subtests 因本輪新增的 `DEF-101-615` 帳本列而 367→368（見 §3 首段機械定位），`check_defect_log_
crossref.py` 有效狀態列數因同一原因由 98→99，兩者皆已在上方逐項訂正並非「逐字相同」。

## 4. 全專案跨平台相容性掃描（Scan-A~H）

- **Scan-A（廣泛掃描）**：對 `subprocess.*bash` 硬編呼叫、`os.system(`、`/tmp/` 字面量三類
  pattern 做全庫 grep。`os.system(` 全庫零命中。`subprocess.run(["bash"...` 全庫零命中於生產碼
  （唯一命中是 `test_windows_forbidden_filename_parity.py` 註解引述 R60 已修復的 DEF-101-588
  史料，非活現病灶）。`/tmp/` 字面量全數落在測試 fixture／`bash_probe_spec.py` 探測規格常數，
  皆為平台中立的假路徑字串，非真實檔案 I/O，非新缺陷。
- **Scan-B（sanitizer／guard 覆蓋率）**：`test_windowsapps_guard_*`／`test_check_wrapper_thinness.py`
  等既有覆蓋測試隨全套通過（見 §3），本輪未新增任何 `.sh`/`.ps1`/guard 呼叫點，無新覆蓋缺口。
- **Scan-C（CI/排程基礎設施）**：`windows-compat-ci.yml`（6 個 `runs-on`）與 `macos-compat-ci.yml`
  （4 個 `runs-on`）的計數不對稱為既有已知劃界（`ADR-XPLAT-002` §6 邊界 6：`.github/workflows/`
  完全在 `check_script_parity` 射程外），非本輪新發現。
- **Scan-D（缺陷帳本／文件新鮮度）**：`check_defect_log_crossref.py`／`sync_onboarding_baselines.py
  --check` 皆 rc=0（見 §3）；帳本本輪新增 1 列（DEF-101-615）後體積見 §5。
- **Scan-E（Architect 架構複核）**：本輪最主要發現即 §1（Phase 2-E 過期宣稱）——本身就是一項
  Scan-E／Scan-D 型治理文件缺陷，已訂正。
- **Scan-F（Runtime／載具真跑）**：見 §2（windows_smoke_local.ps1）與 §3（全套回歸）。
- **Scan-G（backlog 接續稽核）**：核對 `ADR-XPLAT-002` §8 交棒表現存 open 項目（7/8/9/10/11）
  皆仍指向存在的承接條件（PM signoff／R62+／未指派），未發現孤兒 backlog；本輪把項目 5 由
  「R62」訂正為「R60 已交付」、項目 4 由「R62」改派「R63」，皆為具名改派而非留白。
- **Scan-H（護欄層自檢）**：本輪未新增任何機械鎖（僅訂正既有 ADR 文字＋新增 1 筆帳本列），
  無新鎖需要 bug-injection 驗證；既有鎖（`check_wrapper_thinness`／`check_script_parity`）
  的 rc 仍有既有閘門消費（見 §3），未退化為「可重跑但無人看」。

**結論：全專案掃描零新缺陷**（唯一「發現」是治理文件對已完成工作的過期宣稱，已於 §1 訂正）。

## 5. 缺陷帳本異動

- `DEF-101-615`（新增列，fixed@R62）：記錄本輪兩項發現——① Phase 2-E 過期宣稱訂正；
  ② windows_smoke_local.ps1 驗證缺口補齊。
- `DEF-101-610`（既有 open 列，就地補一句交叉引用，不變更其 open 狀態）：註記「同型失效模式
  於 R62 又發生一次，見 `DEF-101-615`」——本輪①項發現（同輪並行包使設計文件前提失效）正是
  `DEF-101-610` 描述的失效模式的又一次具體發生。
- 帳本主檔大小：本輪最終 **237,068 bytes**（`wc -c` 實測；硬閘 262,144 bytes，餘裕約
  24.5KB）。R61 基線（HEAD `152f86a`，`git show HEAD:docs/06_quality/AutoSDD_Defect_Log.md | wc -c`）為 231,815 bytes，本輪淨增
  5,253 bytes（1 筆新列 `DEF-101-615` ＋ `DEF-101-610` 就地補交叉引用 ＋ 本文件精確度修復
  對 `DEF-101-615` 內文的訂正擴寫），未逼近硬閘，本輪不需歸檔。

## 6. 未做的部分（留給 R63，非含糊「下輪再看」）

Phase 1-C 全量（(a)(b)(d)）：`_EXEMPT_PAIRS`/`_SINGLE_SIDED_EXEMPT` 值由字串升級為
`(tier, reason)` tuple、4 組異名對等品字典化、tier3/tier4 reason 關鍵詞斷言。**具體解除
判準**（與 R61 證據文件記載的判準相同，本輪未變更）：

1. 逐一走過 `_EXEMPT_PAIRS`（5 項）+ `_SINGLE_SIDED_EXEMPT`（18 項）共 23 個條目，
   為每項指定 tier ∈ {tier1_contract, tier1_adapter, tier2_spec, tier3_os_primitive,
   tier4_forbidden, unpinned}。
2. 同步改寫至少 3 支既有測試檔對字串型別的依賴：
   `tools/tests/test_check_script_parity.py:248`（`.strip()`）、
   `tools/tests/test_onboarding_parity_interlock.py:105/114`（`for key, why in
   ...items()` 字串比對）、`tools/tests/test_schedule_capability_parity.py`（提及
   `_EXEMPT_PAIRS` 語意的註解）。
3. 完成後 `--print-collapse` 才能印出逐對 tier/reason（本輪仍只印六張表的總量）。
4. UEP／AC 棘輪化（`python tools/check_script_parity.py` 的判準值不得被靜默調升）——
   照 `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet` 的形狀。

`ADR-XPLAT-002` Phase 2 其餘項目維持原判：2-A（run_tlc 薄殼化）候選但非阻塞、2-B（ci-gate
fallback 刪除）／2-F（LOC 預算）需使用者/PM signoff，本輪未觸碰。macOS 真機（Phase 3）
仍零覆蓋，本機無法解決。
