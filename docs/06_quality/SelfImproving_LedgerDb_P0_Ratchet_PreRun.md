# SelfImproving 帳本改 DB P0：棘輪預演證據檔（AC-LD-13-7；D7）

- 性質：唯讀預演證據；P0 不改任何鎖檔、不重釘、不 commit。
- HEAD：`fdd9a738fbcca6c5abf25c31dca638648697e6ae`（預演於此 HEAD 實跑；基準值與 TCS §5.5 於 P0 起點的實跑相同）。
- 鍵：`monorepo-si-ledgerdb-p0`；規格：`docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md` §5.5、契約節 C6。
- 唯讀聲明：下方腳本只 import `tools/tests/test_adr_xplat001_c1c2_lock.py`，於記憶體附加預估列與模擬名冊後呼叫
  `repin_growth_problems()`、`repin_cost_ratchet_problems()`，不寫任何檔、不呼叫 git、不開網路。
- 增量來源：PRD §8.3 的量級（無實測）；低＝P0 +420、P1 +1,500、P2 +515、P3a +1,500、P3b +515、P4 -4,228；
  高＝+515、+2,500、+515、+3,000、+515、-4,228。實作棒收尾時以 `--print-guard-lines` 的真實淨額為準並重跑本腳本。

## 預演腳本

於 repo 根執行 `python <腳本檔>`（建議在 `git archive <base>` 含 `.git` 的副本內跑；輸出須與下節逐列相同）。

```python
"""P0 棘輪預演（AC-LD-13-7）：唯讀——只 import 鎖檔、在記憶體附加預估列與模擬名冊，不寫檔、不呼叫 git、不開網路。

用法（repo 根；建議在 `git archive <base>` 副本內跑）：  python <本腳本>
S-B 逐輪計入款(12) 的到期義務：稽核痕跡一走到 `_REPIN_NET_CAP_DUE_ROUND` 就須往上限表追加更小的一列並重新武裝
（到期輪＝兌現輪＋2、目標＝新上限－1），所以輪號前進後「該輪上限」逐輪遞減（記憶體內模擬）。
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools" / "tests")]
SPEC = importlib.util.spec_from_file_location("c1c2", ROOT / "tools/tests/test_adr_xplat001_c1c2_lock.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

LOG = list(M._GUARD_LINES_REPIN_LOG)
LANE = list(M._REGRESSION_LANE_LOG)
ROSTER = dict(M._REPIN_APPROVED_ROUND_OVERAGE)
MAX_ENTRIES = M._REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES
LIVE = M.live_repin_round(LOG)
BASE_TOTAL = LOG[-1][2]
BASE_SCHEDULE = tuple(M._REPIN_NET_CAP_SCHEDULE)
DUE0, TGT0 = M._REPIN_NET_CAP_DUE_ROUND, M._REPIN_NET_CAP_DUE_TARGET
PHASES = ("P0", "P1", "P2", "P3a", "P3b", "P4")
PLANS = {"低": (420, 1500, 515, 1500, 515, -4228), "高": (515, 2500, 515, 3000, 515, -4228)}
REASON = "預演用名冊理由：只為判準演算，長度需超過最短理由門檻二十字元"


def tags(problems):
    return "、".join(p.split("]")[0] + "]" for p in problems) or "空"


def run(rows, roster, schedule):
    out, cur = list(LOG), BASE_TOTAL
    for label, delta in rows:
        out.append((label, cur, cur + delta, delta, "預演列"))
        cur += delta
    M._REPIN_NET_CAP_SCHEDULE = schedule
    try:
        return M.repin_growth_problems(out, regression_lane=LANE, approved_overage=roster)
    finally:
        M._REPIN_NET_CAP_SCHEDULE = BASE_SCHEDULE


print(f"基準：log {len(LOG)} 列、當前輪 R{LIVE}、名冊 {len(ROSTER)}／{MAX_ENTRIES}、"
      f"R{LIVE} 名冊精確淨額 {ROSTER[f'R{LIVE}'][0]}、上限 {M.net_cap_for_round(LIVE)}、"
      f"到期輪 R{DUE0}／目標 {TGT0}、回歸鎖軌上限 {M._REGRESSION_LANE_ROUND_CAP}；"
      f"基準回傳 {tags(M.repin_growth_problems(LOG, regression_lane=LANE))}")

print("\n### S-A　同標籤續列（標籤＝當前輪；到期輪未到，款(12) 不觸發）\n")
print("| 方案 | 階段（增量） | 名冊未重登 | 名冊精確淨額須改為 | 重登後 | 名冊筆數／上限 | 款(12) |")
print("|---|---|---|---|---|---|---|")
for name, plan in PLANS.items():
    rows, acc = [], 0
    for ph, d in zip(PHASES, plan):
        rows.append((f"R{LIVE}", d))
        acc += d
        need = ROSTER[f"R{LIVE}"][0] + acc
        stale = run(rows, ROSTER, BASE_SCHEDULE)
        fresh = run(rows, {**ROSTER, f"R{LIVE}": (need, ROSTER[f"R{LIVE}"][1])}, BASE_SCHEDULE)
        cost = M.repin_cost_ratchet_problems(latest_round=LIVE)
        print(f"| {name} | {ph}（{d:+d}） | {tags(stale)} | {need} | {tags(fresh)} | "
              f"{len(ROSTER)}／{MAX_ENTRIES} | {tags(cost)} |")

print("\n### S-B　輪號前進（每階段新標籤；逐輪兌現款(12) 到期義務）\n")
print("| 方案 | 階段（標籤，增量） | 該輪上限 | 款(12) 未兌現回傳 | 兌現動作 | 無名冊項 | 加名冊項後 | 名冊累計／上限 |")
print("|---|---|---|---|---|---|---|---|")
for name, plan in PLANS.items():
    rows, extra, label = [], {}, LIVE
    sched, cap, due, tgt = BASE_SCHEDULE, M.net_cap_for_round(LIVE), DUE0, TGT0
    for ph, d in zip(PHASES, plan):
        label += 1
        rows.append((f"R{label}", d))
        # 款(12)：未兌現態
        unfulfilled = M.repin_cost_ratchet_problems(latest_round=label, current_cap=cap,
                                                    due_round=due, due_target=tgt)
        action = "—"
        if label >= due and cap > tgt:
            sched = sched + ((label, tgt),)
            cap_here = tgt
            action = f"上限表追加 (R{label}, {tgt})；重新武裝到期輪 R{label + 2}／目標 {tgt - 1}"
            cap, due, tgt = tgt, label + 2, tgt - 1
            after = M.repin_cost_ratchet_problems(latest_round=label, current_cap=cap_here,
                                                  due_round=due, due_target=tgt)
        else:
            cap_here = cap
            after = unfulfilled
        # 款(10)(11)
        bare = run(rows, {**ROSTER, **extra}, sched)
        needs = d > cap_here
        if needs:
            extra[f"R{label}"] = (d, REASON)
        fixed = run(rows, {**ROSTER, **extra}, sched) if needs else None
        total = len(ROSTER) + len(extra)
        print(f"| {name} | {ph}（R{label}，{d:+d}） | {cap_here} | {tags(unfulfilled)}→兌現後{tags(after)} | "
              f"{action} | {tags(bare)} | {tags(fixed) if needs else '（不需）'} | {total}／{MAX_ENTRIES} |")
```

## 輸出表

下列為上述腳本於 HEAD `fdd9a738fbcca6c5abf25c31dca638648697e6ae` 的實際輸出（rc 0，逐字貼上；「名冊筆數／上限」的上限是現行常數，S-B 的累計欄超過它表示該階段須可見上修）。

```text
基準：log 358 列、當前輪 R214、名冊 6／6、R214 名冊精確淨額 15220、上限 515、到期輪 R216／目標 514、回歸鎖軌上限 309；基準回傳 空

### S-A　同標籤續列（標籤＝當前輪；到期輪未到，款(12) 不觸發）

| 方案 | 階段（增量） | 名冊未重登 | 名冊精確淨額須改為 | 重登後 | 名冊筆數／上限 | 款(12) |
|---|---|---|---|---|---|---|
| 低 | P0（+420） | [超出每輪上限] | 15640 | 空 | 6／6 | 空 |
| 低 | P1（+1500） | [超出每輪上限] | 17140 | 空 | 6／6 | 空 |
| 低 | P2（+515） | [超出每輪上限] | 17655 | 空 | 6／6 | 空 |
| 低 | P3a（+1500） | [超出每輪上限] | 19155 | 空 | 6／6 | 空 |
| 低 | P3b（+515） | [超出每輪上限] | 19670 | 空 | 6／6 | 空 |
| 低 | P4（-4228） | [超出每輪上限] | 15442 | 空 | 6／6 | 空 |
| 高 | P0（+515） | [超出每輪上限] | 15735 | 空 | 6／6 | 空 |
| 高 | P1（+2500） | [超出每輪上限] | 18235 | 空 | 6／6 | 空 |
| 高 | P2（+515） | [超出每輪上限] | 18750 | 空 | 6／6 | 空 |
| 高 | P3a（+3000） | [超出每輪上限] | 21750 | 空 | 6／6 | 空 |
| 高 | P3b（+515） | [超出每輪上限] | 22265 | 空 | 6／6 | 空 |
| 高 | P4（-4228） | [超出每輪上限] | 18037 | 空 | 6／6 | 空 |

### S-B　輪號前進（每階段新標籤；逐輪兌現款(12) 到期義務）

| 方案 | 階段（標籤，增量） | 該輪上限 | 款(12) 未兌現回傳 | 兌現動作 | 無名冊項 | 加名冊項後 | 名冊累計／上限 |
|---|---|---|---|---|---|---|---|
| 低 | P0（R215，+420） | 515 | 空→兌現後空 | — | 空 | （不需） | 6／6 |
| 低 | P1（R216，+1500） | 514 | [到期未下修]→兌現後空 | 上限表追加 (R216, 514)；重新武裝到期輪 R218／目標 513 | [超出每輪上限] | 空 | 7／6 |
| 低 | P2（R217，+515） | 514 | 空→兌現後空 | — | [超出每輪上限] | 空 | 8／6 |
| 低 | P3a（R218，+1500） | 513 | [到期未下修]→兌現後空 | 上限表追加 (R218, 513)；重新武裝到期輪 R220／目標 512 | [超出每輪上限] | 空 | 9／6 |
| 低 | P3b（R219，+515） | 513 | 空→兌現後空 | — | [超出每輪上限] | 空 | 10／6 |
| 低 | P4（R220，-4228） | 512 | [到期未下修]→兌現後空 | 上限表追加 (R220, 512)；重新武裝到期輪 R222／目標 511 | 空 | （不需） | 10／6 |
| 高 | P0（R215，+515） | 515 | 空→兌現後空 | — | 空 | （不需） | 6／6 |
| 高 | P1（R216，+2500） | 514 | [到期未下修]→兌現後空 | 上限表追加 (R216, 514)；重新武裝到期輪 R218／目標 513 | [超出每輪上限] | 空 | 7／6 |
| 高 | P2（R217，+515） | 514 | 空→兌現後空 | — | [超出每輪上限] | 空 | 8／6 |
| 高 | P3a（R218，+3000） | 513 | [到期未下修]→兌現後空 | 上限表追加 (R218, 513)；重新武裝到期輪 R220／目標 512 | [超出每輪上限] | 空 | 9／6 |
| 高 | P3b（R219，+515） | 513 | 空→兌現後空 | — | [超出每輪上限] | 空 | 10／6 |
| 高 | P4（R220，-4228） | 512 | [到期未下修]→兌現後空 | 上限表追加 (R220, 512)；重新武裝到期輪 R222／目標 511 | 空 | （不需） | 10／6 |
```

## 標籤規則

- 重釘標籤不得超前帳本當前輪：`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`（`tools/tests/test_check_defect_log_crossref.py`，掃已追蹤程式碼檔）；當前輪＝`python tools/check_handoff_carriers.py` 首行 `[census] 當前輪＝R<N>`。
- 因此產品輪沒有自己的 R 系列證據檔時，一律走 S-A（同標籤續列，標籤＝當前輪）；S-B（輪號前進）僅在當前輪因其他工作前進之後才可用，且每階段須用新輪號。
- 標籤集合以 `repin_growth_problems()` 的回傳前綴表示：`[超出每輪上限]`、`[只升不降]` 等；款(12) 以 `repin_cost_ratchet_problems()` 的 `[到期未下修]` 表示。「空」＝回傳空清單。
- 名冊（`_REPIN_APPROVED_ROUND_OVERAGE`）內已核准輪次不計入連續上升計數；名冊筆數上限由 `_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES` 釘住，上修是可見決定。

## 結論

1. 預設路徑是 S-A。名冊筆數不動（維持現行筆數），但 R214 精確淨額須在每一個有測試行變動的階段（P0、P1、P2、P3a、P3b、P4）各重登一次，含 P0 的 +420 至 +515、P2 與 P3b 的 +515，以及 P4 的淨減（淨額減到 15,442 至 18,037 仍遠高於每輪上限，名冊項不能退場、只能改值）。PRD §8.3 的「P2、P3b 各 ≤ +515」在 S-A 下不是約束。
2. 名冊上限上修量：S-A 為 0；S-B 需四次可見上修（`_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES` 6→7→8→9→10，P1、P2、P3a、P3b 各入一列），且 P2、P3b 須壓到 ≤ +514、≤ +513 才免入名冊。
3. 款(12) 兌現動作（僅 S-B）：稽核痕跡走到到期輪 R216 時往上限表追加 (R216, 514) 並重新武裝為 R218／513；R218 追加 (R218, 513)、重新武裝 R220／512；R220 追加 (R220, 512)、重新武裝 R222／511。即 P1、P3a、P4 各多一次鎖檔改動；S-A 在到期輪 R216 未到前不觸發。
4. 「R214 精確淨額」須重登的次數：S-A 為 6 次（P0、P1、P2、P3a、P3b、P4 各一次）；S-B 為 0 次（各階段改用新標籤列）。
5. 不入名冊又 >0 的相鄰輪須確保連續不超過 2 輪或其間有淨減輪；低高兩方案 P4 皆為淨減。
6. 預演函式有鑑別力：「名冊未重登」每格回 `[超出每輪上限]`、重登後回空；S-B 的「無名冊項」於 P1、P2、P3a、P3b 回 `[超出每輪上限]`、加名冊項後回空；款(12) 未兌現態於 P1、P3a、P4 回 `[到期未下修]`、兌現後回空。

## 乾跑選檔名單

D2 證據（TCS §5.3.2）：選檔規則第一輪＝`git grep -l -E 'tools/tests|_TESTS_DIR|rglob\(|ls_files|iterdir\(|\.glob\(|os\.walk' <HEAD> -- 'tools/tests/test_*.py'`（於 HEAD 現查 90 檔），加 `test_ntfs_trailing_space_device_name`、`test_root_infra_parity`，共 92 檔。TCS 起草時實跑並驗過的是其中涵蓋各掃描器族別的 50 檔子集；本名單為規則的完整輸出（超集），QA 重跑可擴充、不可縮減。第二輪另加棘輪類 8 檔：`test_adr_xplat001_c1c2_lock`、`test_root_module_layout`、`test_subprocess_encoding_hygiene`、`test_skip_ceiling_ratchet_direction`、`test_run_root_unittests`、`test_selfimproving_capability`、`test_selfimproving_p2_meta`、`test_selfimproving_p3_meta`。

1. `test_adr_xplat001_c1c2_lock.py`
2. `test_apply_lock.py`
3. `test_archive_apply_locked.py`
4. `test_archive_defect_log.py`
5. `test_bash32_compat.py`
6. `test_bash_probe_spec_contract.py`
7. `test_block_destructive_git_r83.py`
8. `test_bootstrap_core.py`
9. `test_bootstrap_ps1.py`
10. `test_check_archive_required.py`
11. `test_check_defect_log_crossref.py`
12. `test_check_hooks_liveness.py`
13. `test_check_pytest_baseline_sites.py`
14. `test_check_script_parity.py`
15. `test_check_wrapper_thinness.py`
16. `test_ci_gate_xdist_allowlist.py`
17. `test_clean_venv_carrier.py`
18. `test_component_sanitizer_shared_layer_lock.py`
19. `test_context_budget_guard.py`
20. `test_cpu_budget.py`
21. `test_defect_id_reference_integrity.py`
22. `test_dev_platform_provenance.py`
23. `test_dev_start.py`
24. `test_dev_start_ps1_lastexitcode.py`
25. `test_doc_env_prefix_platform_parity_r60.py`
26. `test_doc_loc_baseline_freshness_r60.py`
27. `test_extras_quoting_zsh_safety.py`
28. `test_find_git_bash_parity.py`
29. `test_gha_action_versions.py`
30. `test_git_hooks_install_common.py`
31. `test_guard_line_taxonomy_r99.py`
32. `test_install_statusline.py`
33. `test_install_windows_nightly.py`
34. `test_mac_endurance_r83.py`
35. `test_mac_readiness_r82.py`
36. `test_macos_smoke_skip_honesty.py`
37. `test_maturity_criteria_r79.py`
38. `test_negative_existence_claims_r82.py`
39. `test_no_invalid_escape_sequences.py`
40. `test_ntfs_trailing_space_device_name.py`
41. `test_onboarding_parity_interlock.py`
42. `test_platform_neutral_paths.py`
43. `test_platform_utils_dedup.py`
44. `test_pre_commit_dispatcher_sigpipe.py`
45. `test_pre_push_dispatcher.py`
46. `test_ps1_bom.py`
47. `test_ps51_compat.py`
48. `test_ps_engine_ssot.py`
49. `test_python_c_percent_shim.py`
50. `test_quota_env_layers.py`
51. `test_quota_policy.py`
52. `test_recovery_hint_passes_ps_lint.py`
53. `test_refresh_nightly_anchor.py`
54. `test_root_infra_parity.py`
55. `test_root_module_layout.py`
56. `test_run_root_unittests.py`
57. `test_sanitize_component_frozen_sdd_versions_lock.py`
58. `test_schedule_capability_parity.py`
59. `test_script_scan_surface_ssot.py`
60. `test_selfimproving_capability.py`
61. `test_selfimproving_capacity_retire.py`
62. `test_selfimproving_check.py`
63. `test_selfimproving_console_obs.py`
64. `test_selfimproving_events.py`
65. `test_selfimproving_events_p2.py`
66. `test_selfimproving_issues.py`
67. `test_selfimproving_measure.py`
68. `test_selfimproving_measure_probe.py`
69. `test_selfimproving_measure_verb.py`
70. `test_selfimproving_p2_meta.py`
71. `test_selfimproving_p3_meta.py`
72. `test_selfimproving_promote.py`
73. `test_selfimproving_props.py`
74. `test_selfimproving_research_scan.py`
75. `test_selfimproving_sandbox.py`
76. `test_selfimproving_verify.py`
77. `test_session_brief.py`
78. `test_single_venv_identity.py`
79. `test_skip_ceiling_ratchet_direction.py`
80. `test_skip_discoverability_r83.py`
81. `test_smoke_ci_sync.py`
82. `test_statusline_context_feed.py`
83. `test_stdio_utf8.py`
84. `test_subprocess_encoding_hygiene.py`
85. `test_wake_chain_halt_r278.py`
86. `test_windows_forbidden_filename_parity.py`
87. `test_windows_smoke_heartbeat_doc_sync.py`
88. `test_windowsapps_guard_bash_parity.py`
89. `test_windowsapps_guard_cross_consistency.py`
90. `test_workflow_permission_concurrency_lock.py`
91. `test_workflow_schedule_sync.py`
92. `test_workflow_timeout_coverage.py`
