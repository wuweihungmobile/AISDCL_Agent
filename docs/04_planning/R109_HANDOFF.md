# R109 交接書 — Gap C 接線輪（ONBOARDING §7 表② 指紋檢查接進 dev_start [6/7]）

<!-- guard-total:R109 --> **本輪護欄層累積淨額（稽核痕跡合計，同輪多列合併）＝ 89314 → 89467（+153）** —— ①Gap C 接線（`test_dev_start.py` 6910→7007：TestOnboardingSnapshotProbe 六支＋既有三支 step_platform 測試補 mock 隔離）＋tools/lib 掃描面下限帶重釘（`test_platform_neutral_paths.py` 5717→5720）＋鎖檔自身稽核列、凍結前綴延伸與 (109, 610) 到期義務兌現（`test_adr_xplat001_c1c2_lock.py` 6309→6325）；②F2 三次量測矛盾修復（`test_context_budget_guard.py` 8157→8178：兩處活體隔離夾具）＋鎖檔自身第二列稽核列與 rewrite ledger 追加（`test_adr_xplat001_c1c2_lock.py` 6325→6341）。逐檔清單見 `CrossPlatform_R106_Scan_Findings.md` 的 R109 標記行。

> 本檔由收尾單人窗口補完。量測值皆為寫下當回合的實測；讀者的第一動作是重量，不是採信。

---

## 一、`R110` 排程約束（Architect blocking 主體）

- 重釘淨額三輪走勢：`R107`＝−1、`R108`＝+190、`R109`＝+153 ⇒ 連續上升 streak＝2，**恰等於**上限
  `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2`（`tools/tests/test_adr_xplat001_c1c2_lock.py:1284`）。
- 後果：下一輪任何對 `tools/tests/*.py` 的**正淨額**重釘——哪怕 +1——會使款(11) 當場紅、
  pre-push 被擋；合法出口只有「該輪淨額 ≤ 0」。⇒ **瘦身／結案要排在動 `tools/tests` 之前**，
  先湊出負額度再進場（史料搬遷抵銷判例見根層 MEMORY「護欄層成長用搬史料抵銷」）。
- 到期義務：`(109, 610)` 已於本輪兌現，並重武裝為 `(111, 595)`
  （`_REPIN_NET_CAP_DUE_ROUND=111`／`_REPIN_NET_CAP_DUE_TARGET=595`）——`R111` 前 cap 須降到
  595 以下。
- 本節數字的現查：`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。

## 二、已驗證什麼（皆本輪當回合實測）

> 🔴 本節是**本輪工作中**的實測紀錄；收尾書記**最後**一次全套的 rc 依 `R108` 慣例不寫進本檔
> （本檔是閘門的判準輸入之一，寫回來就得再改一次文件、使那次量測失效），**收尾最後全套 rc
> 見交件回報**。

- 根層全套：`python tools/run_root_unittests.py` → `Ran 3711 tests in 553.690s`／
  `OK (skipped=44)`，rc=0。
- AutoClaude 閘門：7 道全 PASS；pytest 段 `4739 passed, 62 skipped in 145.08s`，rc=0。
- §7 表② 指紋：`python tools/sync_onboarding_baselines.py --check-snapshot` rc=0（macOS 欄相符）。
- 帳本交叉：`python tools/check_defect_log_crossref.py` rc=0（未結 64）；
  `python tools/check_handoff_carriers.py` rc=0。
- LOC 分級：`python AutoClaude/tools/check_loc_budget.py --json` violations 全空
  （`tools/dev_start.py` 1952 行持平）。
- Quota 測試 hermetic 修復後（F2，`test_context_budget_guard.py` 兩處活體隔離夾具）：
  兩 runner 各 3 連跑綠；全檔 `458 passed, 8 skipped`，rc=0。
- 四方審查：2 筆 REJECT（blocking）均已修復——SA blocking＝useMacWin.md Windows 段 [6/7]
  清單補哨兵條目（四件事→五件事）；Architect blocking＝本檔補完（本檔即修復之一）。

## 三、還沒做／已知風險（每項附可查載體或現查指令；本節不新增帳本列、不佔分母）

1. **收尾 commit/push 尚未執行**：本輪改動已全數落盤且窄範圍驗證全綠，但**尚未** commit/push。
   工作樹現況現查：`git status --porcelain --untracked-files=all`；push 前全套根層閘門照
   `python tools/run_root_unittests.py` 重驗。
2. **Q7 Windows 執行面**（載體＝DEF-200-231）：清 `AUTOSDD_RESUME_OFF` User 層值只能在
   Windows 本機做；指令與兩件憑證＝ADR-XPLAT-014 §3.5 Q7 訂正注。現查：
   `git grep -n "DEF-200-231" docs/06_quality/AutoSDD_Defect_Log.md`。
3. **env 污染源側未修**：`tools/session_resume_planner.py::main()`（:1460）開頭呼叫
   `tools/lib/quota_gate.py::apply_env_defaults()`（:242），把真 `.env` 值**永久灌進行程
   `os.environ`**——本輪只修了受害測試側（hermetic 夾具），污染源側原樣，對其餘測試仍是
   潛在污染向量。現查：`git grep -n "apply_env_defaults" tools/session_resume_planner.py`。
4. **AutoClaude nightly 剖面 `darwin+nopg+solo` 未登記 skip 天花板**：02:00 PG 容器不在時
   nightly 的 autoclaude_gate 必紅。修法＝把實測值登記進 `tools/lib/skip_group_policy.py` 的
   `_RUNTIME_SKIP_CEILING`（:274）；判準入口＝`AutoClaude/tools/local_ci_gate.py::check_skip_census`。
   現查：`git grep -n "_RUNTIME_SKIP_CEILING" tools/lib/skip_group_policy.py`。
5. **`TestOnboardingSnapshotProbe` 六支全 mock、無 call_args 斷言**
   （`tools/tests/test_dev_start.py:2732`）：argv 打錯會靜默降級恆綠（DEF-200-044 同型）。
   候選修法＝補 call_args 斷言或 e2e 冒煙。現查：
   `git grep -n "class TestOnboardingSnapshotProbe" tools/tests/test_dev_start.py`。
6. **裁決題堆疊原樣**（載體＝DEF-200-232 維持 open，解鎖條件寫在該列狀態欄）。現查：
   `git grep -n "DEF-200-232" docs/06_quality/AutoSDD_Defect_Log.md`。
7. **`onboarding_snapshot_note` rc=1 語意混疊**（SD 鏡發現，advisory 影響有界）：rc=1 無法
   區分「stale 判決」與「工具未捕捉例外崩潰」；邏輯本體＝`tools/lib/onboarding_snapshot_note.py`。
   現查：`git grep -n "onboarding_snapshot_note" tools/dev_start.py`。

## 四、下一步的確切指令（開場量測四件套）

```bash
python tools/session_resume_planner.py --pace
python tools/check_defect_log_crossref.py --unresolved-count
python AutoClaude/tools/check_loc_budget.py --json
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
```

- 皆於 repo 根目錄執行（Windows 載具對照見 `R108_HANDOFF.md` §三：同四條、絕對路徑形態）。
- 讀 rc 一律不接管線（先接變數，或用 Python `subprocess.run(...).returncode`）。
- 動 `tools/tests/*.py` 前先讀本檔〈一〉：正淨額重釘在下一輪是紅，先做瘦身／結案湊出 ≤0
  再進場。
- 帳本歸檔壓力現查：`python tools/archive_defect_log.py --check`（本輪未跑，無宣稱）。

## 五、禁止事項

- 不准 `--no-verify`；不准 `AUTOCLAUDE_SKIP_HOOKS=1`；不准 `AUTOSDD_QUOTA_GUARD_OFF=1`
  （額度閘門攔下時等視窗，不關守衛）。
- 四份 Proposed（`PRD_Amendment_R108_Pacing.md`／ADR-XPLAT-014／
  `PRD_Amendment_R108_BurnDown_Addendum.md`／`ADR-XPLAT-013_Phase2_Proposal_R108.md`）
  未裁決**不得落款生效**。
- 重啟後第一件事是重驗，不採信本檔任何「已驗證」宣稱（zero-trust 對自己上一段亦然）。
- 最後一次全套閘門必須在**最後一次寫文件之後**（`R96` 教訓：寫帳本會改變閘門判準的輸入）。
