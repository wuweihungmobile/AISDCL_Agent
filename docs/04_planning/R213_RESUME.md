# R213 第三窗 可重啟點任務書（2026-10-14 00:5x +08:00；sid `7c51b538-5625-45f6-86e6-c47912d6a93f`；額度五小時窗撞線前寫）

> 重啟後第一件事＝重驗，不採信本檔任何「已通過」宣稱。重啟指令：`claude -r 7c51b538-5625-45f6-86e6-c47912d6a93f`。
> 工作樹保全：`git stash create` ＋ tag `r213-w3-wip-preserved`（工作樹本身未動、18 M＋1 新檔 `tools/lib/pytest_skip_census.py` 已 `git add`）。scratchpad 全部報告備份在 `~/.autosdd/r213_window3_scratch/`（關鍵：`helmsman_decisions_wave2.md`、`evid_11_draft.md`、`plan_P1_design.md`、`review_{ARCH,SA,SD,QA}.md`、各包 `*_report.md`、`ppin1_verify_nightly.py`）。

## 已驗證（本窗本場實跑；數字附座標）
- 真 launchd nightly RunId `20261014_000025`（`AutoClaude/logs/nightly_mac_20261014_000025.log`）：Docker 自開→PG→測試→收容器→關 Docker 全鏈成功（:335-347、:619、:641-644）；census 三條（:619／:786／:330-331）與 `tools/lib/skip_group_policy.py` 登記逐格相同；彙總 PASS=4 FAIL=1（stage 2 根層全套 3 項失敗／2 模組，皆為本窗編修自造、已修：workflow :2037 訊息字串、`skip_group_policy.py` provenance 兩行；修後 `test_skip_ceiling_ratchet_direction`＋`test_extras_quoting_zsh_safety`＋`test_check_pytest_baseline_sites` 48 項 OK、`check_pytest_baseline_sites` rc=0（114）、`test_doc_loc_baseline_freshness_r60` 281 OK）。
- 四方審查：ARCH CONDITIONAL（P2=1：ARCH-01）、SA APPROVE、SD CONDITIONAL（P2=0）、QA CONDITIONAL（P2=0）；全部 P3／P4 已彙整在 `helmsman_decisions_wave2.md` 末段。
- PRD E2E 矩陣（QA-A／QA-B）：56 座標 FAIL 0（功能座標 51 PASS／3 JUDGED；⏸ 2 列另計）。

## 還沒做（依序）
1. 派 FIX-DEV（Sonnet；任務書全文已在本窗對話，要點＝ARCH-01 census 腿天花板突破改 throw＋`skip_group_policy.py:823` 敘述；F1／SD-02 AC4-5 target 改指 `test_pgvector_real_recall.py`；`run_local_nightly.ps1:1396-1410`／`ac4_nightly_collector.py:86` 過期註解；F4 aisdlc-sdd-ci paths 補遞移 import；F5 靜態鎖恆真句；G2／G3 一行靜態鎖；ARCH-09 provenance 改引真夜跑 :619／:786）。
2. 主控親改：證據檔〈十一〉（草稿 `evid_11_draft.md`＋SA-01～11／ARCH-02／04／08／10／F3／F6 訂正；P4 理論洞獨立節，每條附再開症狀）；三本帳：DEF-101-856 closed-by-decision｜退役、DEF-200-075 fixed（但書）——結案文採 `review_SA.md`〈三〉草稿；其餘四列等雲端；PRD §8 列 12 落款「823 項」勘誤以修訂表 v2.1.22 追加註記；ONBOARDING §8 補「nightly 自動開收 Docker」一句。
3. 收尾單人窗口：`python tools/run_root_unittests.py` 全套 rc=0 → `skip_id_ledger.json` measured-at 重釘為該次（揭露前次 stage 2 FAIL）→ `python AutoClaude/tools/local_ci_gate.py` → `python tools/lib/clean_venv_carrier.py`（表②指紋）→ `sync_onboarding_baselines.py --check-snapshot` → commit A（訊息引掌舵者原文）→ `git push`（背景、timeout 長）→ `gh run list --commit <完整 sha>` 五支 → `gh workflow run windows-compat-ci.yml`（nightly-full 六步 #9～#14；判準在 `pci_report.md`〈三〉）。
4. P-PIN-2（`ppin1_report.md`〈五〉）：SDD@win32（＋linux 無條件）入表、刪 `_UNMEASURED_RUNNER_PROFILES` 該鍵、`test_local_ci_gate.py:1628`／:1817 畢業版、`AutoClaude/tests@win32+nopg+nested+pgext` 重釘＋`_FROZEN_CEILING_MAX` env-disabled 上修、`_COMPLEMENTARY_PROFILE`、M6 再 touch → commit B → push → 再 dispatch 證明 census 腿收緊仍綠 → 結 693／313／253／960（結案文草稿 `review_SA.md`〈三〉）→ `DEF200274` 證據檔〈第十一輪〉③ 史料追註 → 最終回覆（守則：雲端未綠不得宣稱 0／0／0、不得宣稱 Windows 已驗）。

## 禁止事項
不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准 `git stash`／`checkout --`／`reset --hard`（保全只用 `stash create`）、不跑 `wakechain_e2e.py --run`、不打真 usage 端點、子代理一律 `model: sonnet`、Agent 被額度守衛擋下時只做收斂工作等 reset。
