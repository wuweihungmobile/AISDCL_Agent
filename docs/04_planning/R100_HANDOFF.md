# R100 交棒書（收尾單人窗口 → R101）

<!-- guard-total:R100 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 86097 → 86452（+355）**
——逐檔清單見 [`CrossPlatform_R100_Scan_Findings.md`](../06_quality/CrossPlatform_R100_Scan_Findings.md) §B。
🔴 **磁碟現值不等於這個數字**：磁碟 87544（+1092 未重釘），死結見本檔 §2 與 `DEF-200-208`。

> 🔴 **本載體形態自 R90 後靜默消失**：`docs/04_planning/R*_HANDOFF.md` 是
> `test_adr_xplat001_c1c2_lock.py::_GUARD_TOTAL_DOC_GLOBS` 的三個掃描面之一，
> 而 R91~R99 九輪**一份都沒產**。它不會轉紅（款(5) 只在「檔存在」時對帳），
> 所以「不寫」是零成本的——這正是 `DEF-200-188` 記載的「交接項只寫在散文裡就沒有機械
> 承接單位」在交棒書本身上的同型實例。**本輪恢復它，並把這件事寫在開頭當作立案。**

- **輪次**：R100（收尾單人窗口，所有並行包已停工）
- **性質**：🔴 **發現輪**（掌舵者裁定）。帳本淨額為正是預期結果，不是失控
- **Session ID**：`6e6569e0-919a-4435-953d-40efcd58a865`
- **重啟指令**：`claude -r 6e6569e0-919a-4435-953d-40efcd58a865`

---

## §1 已驗證什麼（逐字實測輸出 ＋ rc；**不採信任何未附輸出的宣稱**）

全部為本收尾窗口當回合親跑，非轉述。

### 1.1 根層閘門 — `python tools/run_root_unittests.py`

```
Ran 3631 tests in 641.034s

FAILED (failures=7, skipped=44)
ROOT_GATE_RC=1
```

**7 支紅逐筆歸因**（全部歸屬既立帳本列，無孤兒）：

| # | 測試 | 根因 | 承接列 |
|---|------|------|--------|
| 1 | `TestGuardBucketRatchet.test_shrink_only_buckets_did_not_grow` | `prose` 桶 4119 → 4182（+63），成長源是真判準 | `DEF-200-208` |
| 2 | `TestGuardLayerRatchet.test_a_net_zero_swap_is_red` | 護欄層 86452 → 87544（+1092）未重釘 ＋ 6 檔漂移 | `DEF-200-208` |
| 3 | `TestGuardLayerRatchet.test_the_line_ratchet_took_over_and_has_teeth` | 同上 | `DEF-200-208` |
| 4 | `TestPricingChangeExemptionExpiresOnItsOwn.test_the_next_round_cannot_reuse_the_exemption` | 🔴 **前提反轉**，非到期：`17032 not greater than 17079`（baseline ≤ total） | `DEF-200-207` |
| 5 | `TestShrinkOnlyRatchet.test_ratchet_is_independent_of_git_state` | 同 #2 的 +1092 | `DEF-200-208` |
| 6 | `TestEarlyExitAnnouncesUnrunChecks.test_the_real_gate_still_reaches_the_late_checks` | crossref 淨額棘輪 rc=1（發現輪，逃生口未設） | 見 §4 逃生口 |
| 7 | `TestMain.test_main_against_real_repo_is_clean` | 同 #6 | 見 §4 逃生口 |

🔴 **#4 的歸因訂正**：它**不是**因為 `_PRICING_CHANGE_EXEMPT_ROUND` 到期。
`live_repin_round()` 當回合實測 **100**，`100 > 100` 為 `False` ⇒ 到期那一側還沒到。
真因是 AutoClaude `total` 在本輪長過了 `baseline`（詳見 §D-12）。

### 1.2 AutoClaude — `python -m pytest tests/ -q`（在 `AutoClaude/` 下）

```
4732 passed, 62 skipped in 136.38s (0:02:16)
AC_PYTEST_RC=0
```

🔴 **由 4730 → 4732**：收尾窗口修 §1.7 那支 blocker 時補了 2 支回歸測試進**既有**檔
`AutoClaude/tests/test_r100_power_loss_protection.py`（未新開測試檔）。零退化。

### 1.3 LOC 分級 — `python AutoClaude/tools/check_loc_budget.py --json`

```
total = 17079
baseline = 17032
cap = 20438
headroom (cap-total) = 3359
violations = {}
```

🔴 `baseline (17032) < total (17079)` ⇒ 這正是 §1.1 #4 那支紅的成因。
（17070 → 17079＝本窗口修 §1.7 blocker 的 9 行斷言；`baseline`／`cap` 未動、`violations` 仍全空、rc=0。）
**未跑 `--update`**（cap = baseline×1.2，重釘 baseline 會抬高 cap ＝ 放寬判準）。

### 1.4 帳本 crossref — `python tools/check_defect_log_crossref.py`

```
CROSSREF_RC=1
❌ 帳本體積與逐列位元組上限（1 筆）：
  - 淨額棘輪違反：本輪新增未結 27 筆 > 結案 2 筆 ⇒ 淨增 25 筆（帳本正在變胖，不是變瘦）。
```

同時輸出三筆 warn：主檔 250524 bytes 逼近 262144／未結列 **97** 筆距 fail 線 98 僅 **1 筆**／
已結列殘留待辦 18 筆。**閘門未早退，跑到最後一道**。

🔴 **收尾窗口最後一次改帳本之後重跑，紅的內容一字未變**（淨額 27 新增／2 結案／淨增 25）。
新增未結列＝**0**：可用容量實測是 **0 格**不是 1 格，理由見 §1.8。

### 1.5 交接載體 — `python tools/check_handoff_carriers.py`

```
✅ 每一筆前瞻延後宣稱都有帳本承接載體
HANDOFF_CARRIERS_RC=0
```

（第一次跑是 rc=1／3 筆紅——本窗口自己寫的 §D 散文有三行延後到下一輪卻沒指名 DEF-ID〔承接列＝`DEF-200-208`／`DEF-200-213`〕，
已就地補上承接列 ID 後轉綠。**判準抓到的是真違規，不是假紅**。）

### 1.6 import-linter — `PYTHONUTF8=1 lint-imports`（在 `AutoClaude/` 下）

```
Contracts: 9 kept, 0 broken.
LINT_IMPORTS_RC=0
```

### 1.7 🔴 blocker 已修：checkpoint 保留版本的輪替早於 `os.replace`

SD 的取證**複驗成立**（座標與方向皆對）：修前 `file_state_repository.py` 的順序是
`_rotate_retained(p, keep)` → `tmp_p.replace(p)`，且該函式的註解逐字自陳
「在 tmp → p 的原子換名**之前**跑」。兩個換名之間存在一個**主檔目錄項不存在**的視窗
⇒ `load_latest_by_playbook()` 走 `not p.exists()` 回 `None`＝「沒有 checkpoint」，
呼叫端靜默從 step 0 重跑，而旁邊那份剛被推過去的**有效** `.v1` 一個字都不會被讀到。
🔴 它打掉的正是同輪 §8-4 ② 剛修好的「CORRUPT ≠ None」。

**修法**：`tmp → fsync → os.replace(tmp, 主檔)` →（**成功之後**）才輪替舊版本
（`_retain_previous()`）。舊主檔的內容改為在 replace 前讀進記憶體、事後另寫一份，
代價是峰值多一份檔的空間——刻意的交換，理由寫在該函式 docstring。
輪替**自己**失敗時只降級＋出聲（`except OSError`，含 ENOSPC 與 Windows WinError 5），
不讓一次已 fsync 成功的落盤變成例外。

**紅綠自證（兩段皆當回合真跑）**——把順序退回修前：

```
FAILED tests/test_r100_power_loss_protection.py::test_a_failed_main_swap_never_makes_the_checkpoint_look_absent
FAILED tests/test_r100_power_loss_protection.py::test_a_failed_retention_degrades_loudly_instead_of_failing_the_save
2 failed, 14 passed in 0.50s
rc=1
```

```
E       AssertionError: 主檔在換名失敗後消失了 ⇒ 呼叫端會靜默從 step 0 重跑
E       assert None is not None
```

修法就位後：

```
16 passed in 0.59s
rc=0
```

### 1.8 🔴 帳本容量硬牆的判準是 `>=`，不是 `>`（本窗口實測，訂正任務書的推導）

`unresolved_ceiling_problems()` 的條件逐字 `if n >= UNRESOLVED_ROWS_FAIL`
⇒ 未結列 97 時**可用容量是 0 格**。實測（先插入索引列 `DEF-200-217` 再量）：

```
未結列數＝98／全部 292 列｜warn=86 fail=98
❌ 未結列 98 筆（…）≥ fail 線 98。🔴 **不要調高本門檻**（那是砸溫度計）
```

該列已退出（未結列回 97、只剩 warn），四方審查五筆新發現全文落
[`CrossPlatform_R100_Scan_Findings.md`](../06_quality/CrossPlatform_R100_Scan_Findings.md) **§E**，
ledger 側改掛同主題既有未結列（`DEF-200-207` 尾＝E1/E3/E4、`DEF-200-209` 尾＝E2；
兩列改後實測 691／667 bytes，皆 ≤ `ROW_MAX_BYTES`）。**未動任何門檻、未假結案。**

---

## §2 還沒做什麼（指向帳本列，**不在此重複內容**）

本輪落盤 **21 列**：`DEF-200-196` ~ `DEF-200-216`（全部 `open（承接輪次：R101）`）。
逐筆證據住 [`CrossPlatform_R100_Scan_Findings.md`](../06_quality/CrossPlatform_R100_Scan_Findings.md) §D。

🔴 **本節每一項都是量測值，一律現查、不得採信本檔字面**：
`python tools/check_defect_log_crossref.py --unresolved-count`（未結列與 fail 線距離）、
`python tools/run_root_unittests.py`（哪幾支還紅）、
`python AutoClaude/tools/check_loc_budget.py --json`（LOC 現況）。

| 軸 | 帳本列 | 一句話 |
|---|---|---|
| 配速／額度 | `DEF-200-196`~`203` | 429 路徑（196 純 bug／197 修憲級）、cap 從未致動、`recommended` 反向、`resets_at` 四層誤判、落款缺欄、`pace_index` 零影響、Fable 軸零煞車、量測值當常數 |
| PRD v2.1 未完成 | `DEF-200-204`~`206` | §4.2.4 D 段遲滯未實作、兩支模組零生產呼叫端、七項 PRD↔實作歧異待裁決 |
| 護欄層／治理 | `DEF-200-207`~`213` | ADR-013 仍 Proposed ＋豁免鎖前提反轉、**護欄層兩鎖死結**、缺口⑥、ONBOARDING mac 欄、Phase 2 (b)(c)、carriers 判準②、帳本體例三筆 |
| 主控自身失誤 | `DEF-200-214`~`216` | 假陰性、任務書給了跑不起來的指令、自造 429 並誤稱活體驗證 |

🔴 **最高優先＝`DEF-200-208`（護欄層兩鎖互為死結）**：不重釘則 4 支測試紅；一重釘則
淨額 `355+1092=1447 > cap 850` 轉紅。**在不動任何常數的前提下沒有不紅的路**，
三個候選處置見 §D-13，需裁決。

🔴 **第二順位＝未結列只剩 1 格**（97／fail 98，`DEF-200-213` 承接）。fail 線無逃生口，
其訊息逐字「不要調高本門檻（那是砸溫度計）」⇒ 下一輪**必須先結案再發現**。

🔴 **`--reconcile` 紅綠自證未落地**（掌舵者原裁決為落地）：四個實測理由否決，見 §D-14，
`DEF-200-213` ④ 承接。最硬的一條是**它的受測對象 `tools/lib/quota_reconcile.py` 未進版控**，
而本窗口禁止 git 寫入 ⇒ 只有主控能解。現查 `git ls-files --error-unmatch tools/lib/quota_reconcile.py`。
<!-- absent-if: def test_reconcile -->（`tools/tests/` 全庫現查 0 筆以 test_reconcile
開頭的測試函式；`--reconcile` 的紅綠自證真的落地時，這個字面才會現身）

### 2.1 四方審查（唯讀）的五筆新發現 — 全文＝`Scan_Findings.md` §E，本節只列處置

- **E1〔blocker〕換尺是本輪 LOC 閘門變綠的原因，ADR-XPLAT-013 沒揭露**。四方票**仍未**重投；
  依 `ADR-XPLAT-013:209` 只有主控能開複審 ⇒ 本窗口做不到。舊尺／新尺對照現查
  `python AutoClaude/tools/check_loc_budget.py --json`（新尺）＋ §E-1 的舊尺實跑表。
  承接列＝`DEF-200-207`（狀態欄尾已指名「續報 §E-1/3/4」）。
- **E2〔blocker〕第三道套利門 `exec(__doc__)` 200→1**：AST 判準**尚未**新增，因它必落
  `tools/tests/` 而該面已死結（`DEF-200-208`）。門是否還開著現查
  `python -c "import sys;sys.path.insert(0,'AutoClaude/tools');import check_loc_budget as m,pathlib;print(m.count_loc(pathlib.Path('<合成檔>')))"`；
  ruff 那一面現查 `ruff check --isolated --select S102 <檔>`。承接列＝`DEF-200-209`。
- **E3〔blocker〕豁免到期鎖已永久靜音、且紅字歸因錯**：provenance 判準**尚未**改寫。
  靜音現查 `python -c "import sys;sys.path.insert(0,'tools/tests');import test_adr_xplat001_c1c2_lock as t;print(t.pricing_exemption_problems(latest_round=120,baseline=17032,total=17079))"`（回 `[]` 即仍靜音）；
  baseline 是否真被動過現查 `git log -1 -- AutoClaude/.loc_baseline`。承接列＝`DEF-200-207`。
- **E4〔major〕`--update` 的語意反轉（cap 20438 → 20494）＝修憲**：ADR 條文**尚未**修改。
  現查 `python -c "print(int(17032*1.2), int(17079*1.2))"`。承接列＝`DEF-200-207`。
- **E5〔major〕Rule 9 第三種洗白形態（`sys.path.insert` ＋裸模組名）無人守**：
  兩道守衛都**仍未**看得到它，且帳本內零同主題未結列 ⇒ 🔴 **本筆沒有 ledger 承接列**，
  只由 §E-5 與本節承接（不硬塞進不相干的列——那正是 `DEF-200-213` ① 在治的體例違反）。
  現查 `python -c "import sys;sys.path.insert(0,'AutoClaude/tests');from test_r82_quota_axis_and_shipped_defaults import _harness_imports as f;print(f)"` 後餵兩份合成檔（見 §E-5）。

### 2.2 備好的索引列原文（R101 結掉 1 列後原封貼進帳本表尾；承接列＝`DEF-200-213`）

實測 **699 bytes** ≤ `ROW_MAX_BYTES`（700）。落地前先跑
`python tools/check_defect_log_crossref.py --unresolved-count` 確認未結列 ≤ 96。

```
| DEF-200-217 | 2026-08-24 | R100 收尾窗口（四方審查唯讀交件 5 筆，索引列） | 逐字憑證／座標＝`docs/06_quality/CrossPlatform_R100_Scan_Findings.md` **§E**（含 3 筆訂正）：E1 **換尺是本輪 LOC 閘門變綠的原因**（舊尺 4 支破線、新尺 0；四支在 HEAD 皆貼線＝本輪推破），ADR-XPLAT-013 未揭露；E2 第三道套利門 `exec(__doc__)` 200→1；E3 豁免到期鎖永久靜音＋歸因錯；E4 `--update` 反轉（cap +56）；E5 Rule 9 第三形態無人守 | P1 | 🔴 E1 須主控重投四方票（ADR:209）；E3/E4 修憲；E2/E5 受 DEF-200-208 死結阻擋 | open（承接輪次：**R101**）：索引列，全文見 §E-1~§E-6 |
```

---

## §3 下一步的確切指令

### 3.1 主控在 commit 那一刻（本窗口做不到的事）

🔴 **最高風險項＝本輪有 14 支未追蹤檔，其中多支是閘門與帳本指針的目標。**
漏 `git add` 的後果不是「少一個檔」，是**本檔 §1 的綠全部變成新 clone 上的紅**：
`CrossPlatform_R100_Scan_Findings.md` 是 21 列新帳本列的 §D 指針目標、
也是 `_GUARD_LINES_REPIN_LOG` 兩列 R100 逐字指名的「逐檔清單的家」；
`tools/check_handoff_carriers.py` 是 §1.5 剛跑綠的那道閘門本身；
`ADR-XPLAT-013-...md` 是 `DEF-200-207` 與計價豁免鎖的依據。

```bash
git status --porcelain -uall     # 🔴 先看清單，勿盲目 git add -A（可能夾帶機器本地產物）
```

當回合實測的未追蹤清單（14 支，逐支判斷後再 add）：

```
AutoClaude/autoclaude/execution/boot_self_check.py
AutoClaude/autoclaude/infra/adapters/dirty_worktree_rescue.py
AutoClaude/autoclaude/utils/disk_space.py
AutoClaude/autoclaude/utils/verified_cli_versions.py
AutoClaude/tests/helpers/static_vocab.py
AutoClaude/tests/test_r100_boot_self_check.py
AutoClaude/tests/test_r100_dirty_worktree_rescue.py
AutoClaude/tests/test_r100_power_loss_protection.py
AutoClaude/tests/test_r100_quota_refusal_false_positive.py
docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md
docs/04_planning/R100_HANDOFF.md
docs/06_quality/CrossPlatform_R100_Scan_Findings.md
tools/check_handoff_carriers.py
tools/lib/quota_reconcile.py
```

🔴 `tools/lib/quota_reconcile.py` 是 `DEF-200-213` ④ 的落地前置條件（見 §D-14）。

```bash
# 發現輪的淨額逃生口——只能在 commit 那一刻設，且必須在 commit 訊息寫明理由
AUTOSDD_NET_RATCHET_OFF=1 git commit    # 理由：R100 為發現輪，新增未結 27／結案 2
```

### 3.2 R101 開工第一件事（**重驗，不採信本檔任何「已通過」宣稱**）

```bash
python tools/run_root_unittests.py                       # 預期 failures=7（見 §1.1）
cd AutoClaude && python -m pytest tests/ -q               # 預期 4732 passed, 62 skipped
python AutoClaude/tools/check_loc_budget.py --json        # 預期 total 17079 / baseline 17032
python tools/check_defect_log_crossref.py --unresolved-count   # 預期 97（距 fail 98 僅 1）
python tools/session_resume_planner.py --pace             # 派工前現查，不得沿用本檔數字
```

### 3.3 `DEF-200-208` 死結的裁決入口（不要自己選，帶去四方）

```bash
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines   # 重釘草稿
python -m unittest tools.tests.test_adr_xplat001_c1c2_lock              # 現況 5 紅
```

---

## §4 禁止事項（違反即停機）

1. ❌ **不准 `--no-verify`**、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
2. ❌ **不准跑 `AutoClaude/tools/check_loc_budget.py --update`**——cap = baseline×1.2，
   重釘 baseline 會抬高 cap，那是**放寬判準**而不是修復。
3. ❌ **不准調任何棘輪常數**：`net_cap_for_round`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`／
   `_PRICING_CHANGE_EXEMPT_ROUND`／`_PHASE2_DUE_ROUND`／`ROW_MAX_BYTES`／
   `UNRESOLVED_ROWS_WARN`／`UNRESOLVED_ROWS_FAIL`／任何 `*_WARN_MARGIN`／任何棘輪比例。
   🔴 判準紅的時候正解是修事實，不是改尺。
4. ❌ **不准假結案**——不准為了讓淨額棘輪變綠而結掉沒真修好的列。
5. ❌ **不准用裸「改派」或去粗體來湊 700 bytes**。合法縮列方式只有一種：
   把詳情搬進具名證據檔，列上留一句話 ＋ 檔名指針。
6. ❌ **不准設 `*_GUARD_OFF`／`AUTOSDD_NET_RATCHET_OFF` 以外的逃生口**；
   `AUTOSDD_NET_RATCHET_OFF` 只能由**主控在 commit 那一刻**設（見 §3.1）。
7. ❌ **不准跳過或註解掉失敗測試**。
8. ❌ 不准宣稱「已驗證／已達標／零損失」而不附當回合真跑的輸出含 rc（鐵律四）。
   轉述別包一律標 `〔他包回報，未複驗〕`。
9. ❌ 讀 rc 不接管線（mac 工具殼是 zsh：要用 `${pipestatus[1]}`，`${PIPESTATUS[0]}` 回空字串）。
10. ❌ 等背景工作不准用裸 `pgrep -f`（兄弟互匹 ⇒ `until !` 永不退出）；
    改記下自己的 PID 用 `until ! kill -0 <PID>`，或 `run_in_background` ＋阻塞到真做完的指令。

---

## §5 誠實劃界（本檔自己的不足）

1. **§1 的數字是 2026-08-23~24 收輪當回合的量測值，不是常數**。`DEF-200-203` 記載的正是
   「把量測值當常數引用」這個機制缺口 ⇒ R101 必須自己重跑，不得引用本檔數字做裁決。
2. **標 `〔他包回報，未複驗〕` 的項目本窗口沒有重量**：`DEF-200-198`（15 個取樣點）、
   `DEF-200-199`（4%/283 分 與 53%/6 分 兩組讀數）、`DEF-200-202`（68 筆落款、69.0pp、
   12.18 pp/hr）、`DEF-200-203`（22 分鐘內移動 20~73%）。這些數字若成為裁決依據須先複驗。
3. **本輪未做重釘、未做淨減法**：護欄層磁碟面 +1092 原封不動留著（`DEF-200-208`）。
4. **21 列這個數字是被 fail 線逼出來的，不是根因數**：原始發現 30+ 項，合併粒度與
   逐項對應表見 §D-1。**合併不等於已解決**，R101 展開任一列時要回讀 §D-1 確認範圍。

---

## §6 🔴 為什麼不 push（四方綜合裁決）

**裁決逐字**：**可以 commit、不可以 push**。

**理由**（本窗口複驗成立）：`prose` 桶 **+63**（4119 → 4182）是 shrink-only 桶，
**今晚沒有合法的清除路徑**——

| 路 | 為什麼走不通（當回合實測） |
|---|---|
| 重釘護欄層基線 | 淨額 `355 + 1092 = 1447 > cap 850`，另一把鎖當場轉紅（`DEF-200-208` 的死結本體） |
| 把 `prose` 搬進允許成長那一組 | `test_the_classifier_discriminates_prose_growth_from_code_growth` 逐字釘住 `"prose" in SHRINK_ONLY_BUCKETS`，改它＝為了讓紅變綠而改判準 |
| 調任何棘輪常數 | §4 禁令 3，且本輪任務書明文禁止 |
| 刪掉本輪新增的真判準 | 那是把已交付的守備能力退回去換綠燈 |

⇒ pre-push 會被上述 4 支測試擋下（`tools/git-hooks/pre-push` 驗的是**工作樹**而非 commit），
**被擋者無法自救**。commit 保全成果、push 留給有裁決權的人。

**重投票要求（不 push 的第二個理由）**：§E-1 已證明「換尺與本輪四支破線是同一次 commit 的兩件事」，
而先前的四方票是在**不知道**這件事的前提下投的。依 `ADR-XPLAT-013:209`（明禁承辦包自行開複審），
🔴 **主控必須重開四方複審**，題目逐字包含 §E-1，且在票未重投之前不得 push。

**主控在 commit 那一刻仍須做的**：見 §3.1（14 支未追蹤檔 ＋ `AUTOSDD_NET_RATCHET_OFF=1` 的理由書寫）。
