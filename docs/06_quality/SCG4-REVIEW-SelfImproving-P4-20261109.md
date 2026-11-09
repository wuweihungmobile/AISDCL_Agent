# SCG-4 獨立審查：SelfImproving P4 根層鍵 monorepo-si-p4-schedule（Sonnet QA 鏡，2026-11-09）

審查基準：HEAD 起點 8bffdde2（審查中途主控推進到 835037ed，為文件 commit）。Oracle＝TCS-SelfImproving-P4-20261109（105 AT）。

## A 判定

**二審判定（HEAD 40d894bd，以二審為準）：PASS**（P1 0、P2 0、P3 0、P4 3：B-2、B-4 與二審新增的 B-5；B-3 已修）。詳見 H 節。

以下為一審判定（保留作紀錄）：**FAIL**（P1 0、P2 1、P3 0、P4 3）。

- P2-1：AT-439-1-1「依 audit time 升冪入帳」的測試無牙（見 B-1、F 的 M09b）。
- 其餘 104 個 AT 的測試各自有牙；105 個 AT 逐個親跑皆綠（C 節）。
- 修好 P2-1（讓測試的 time 與 audit_ref 順序相反）即可轉 PASS；不需改生產碼。

## B 發現表

| 編號 | 嚴重度 | 座標 | 症狀 | 重現 | 建議修法 |
|---|---|---|---|---|---|
| B-1（已修，commit 56d88de1；二審：AT-439-1-1 綠，M09b 重放轉紅，見 H 節） | P2→關閉 | AT-439-1-1；R149 入帳依 time 升冪、同 time 依 audit_ref；`tools/tests/test_selfimproving_schedule_advance.py` 約 500～534 行；`tools/tests/_selfimproving_p2_fixtures.py::new_uuid`（單調遞增計數） | 測試的 5 個稽核檔 time 與 audit_ref 同向遞增（new_uuid 單調），所以「只依 audit_ref 排序、完全不看 time」的突變（`tools/lib/selfimproving/patrol.py` 入帳 sorted 的 key 換成 `i["audit_ref"]`）通過全部 105 個 AT（四個測試檔 104 綠，唯一紅是突變本身讓 AT-440-8-1 範圍守衛變紅，與入帳順序無關）。同 time 的子案例用 sorted 後的兩個 uuid，同樣與預期同向 | 在 patrol.py 把 key 改為 `lambda i: i["audit_ref"]`，跑 `pytest tools/tests/test_selfimproving_schedule_advance.py -k AT_439_1_1_`＝綠 | 夾具讓 time 順序與 audit_ref 順序**相反**：例如 5 個檔的 audit_ref 取遞減、time 取遞增，斷言入帳序仍依 time；再補一個「同 time、audit_ref 取遞減」的反向案例 |
| B-2 | P4 | R153；`tools/lib/selfimproving/unattended.py` `gate` 的 `carrier == "console"` | 我的第一版突變（放行字串 "transcript"）存活，原因是 CLI 的 `--carrier` 只有 console 一個選項，逐字稿載體在實作裡是 `carrier=None`，字串 "transcript" 永不出現；改用真實形態（放行 None）後 AT-438-3-2 與 AT-438-4-1 皆紅。非缺陷，只記錄判準 | 同 F 的 M05／M05 修正版 | 無 |
| B-3（已修，commit 56d88de1；二審：5.1 假 python 寫 stderr 並 exit 3，tick.log 落檔且 rc=3 透傳，見 H 節） | P4→關閉 | `tools/si_patrol_tick.ps1` 第 14、49 行 | `$ErrorActionPreference='Stop'` 加 `& $Python $Entry patrol 2>&1`：Windows PowerShell 5.1 下原生指令寫 stderr（例如 python 例外或用法錯誤）會被當成終止錯誤，`tick.log` 這次不會被寫入。正常路徑 patrol 只寫 stdout，不影響；屬診斷強度建議 | 讀碼 | 在呼叫前後暫設 `$ErrorActionPreference='Continue'`，或用 `Start-Process` 重導向；不屬本鍵驗收 |
| B-4 | P4 | `AUTOSDD_SI_PATROL_RUN` 的授權是行程自述 | 已在 `unattended.py` 檔頭與 TCS 誠實劃界寫明（偵測靠 `check` 的 `run.trigger_f_has_patrol_by` 與 git 對帳）；列出只為完整 | 無 | 無 |

## C 逐 AT 親跑表

指令：`.venv\Scripts\python.exe -m pytest tools/tests/test_selfimproving_schedule_<model|patrol|gate|advance>.py -k <AT 底線形>_ -q -p no:xdist -o addopts=`（每個 AT 一次、cwd＝repo 根；驅動腳本 scratchpad `si\qa\run_at.py`，原始結果 `at_results.json`）。

總結（當回合輸出）：從 TCS §1 表抓到 105 個 AT（不重複 105）；`--collect-only` 收到 105 個測試（SM 32、SP 21、SG 31、SA 21）；每個 AT 的 `-k` 恰收 1 個測試、rc 0、摘要皆為「1 passed」（含子測試），無一紅、無一 skip。

另跑：`python -m unittest discover -s tools/tests -p "test_selfimproving_schedule_*.py"`＝`Ran 105 tests in 224.381s`、`OK`、rc 0（discover 與 pytest 收到同數量）。

逐項表（AT、檔、測試函式、rc、摘要）：

| AT | 檔 | 測試函式（-k 錨定唯一） | rc | 摘要 |
|---|---|---|---|---|
| AT-436-1-1 | SM | test_AT_436_1_1_cell_start_inclusive_end_exclusive | 0 | 1 passed, 31 deselected, 4 subtests passed in 0.34s |
| AT-436-1-2 | SM | test_AT_436_1_2_ran_this_cell_counts_only_trigger_f_in_cell | 0 | 1 passed, 31 deselected in 0.30s |
| AT-436-1-3 | SM | test_AT_436_1_3_origin_resets_only_on_enable_or_period_change | 0 | 1 passed, 31 deselected in 0.39s |
| AT-436-1-4 | SM | test_AT_436_1_4_run_open_f_positive | 0 | 1 passed, 31 deselected in 9.81s |
| AT-436-1-E-1 | SM | test_AT_436_1_E_1_now_must_be_aware_and_not_before_origin | 0 | 1 passed, 31 deselected in 0.38s |
| AT-436-1-E-2 | SM | test_AT_436_1_E_2_absent_ledger_is_null_not_disabled | 0 | 1 passed, 31 deselected in 0.37s |
| AT-436-1-E-3 | SM | test_AT_436_1_E_3_run_open_f_rejections_leave_no_residue | 0 | 1 passed, 31 deselected in 20.85s |
| AT-436-1-E-4 | SM | test_AT_436_1_E_4_schedule_adds_no_detected_event | 0 | 1 passed, 31 deselected in 8.94s |
| AT-436-2-1 | SM | test_AT_436_2_1_skip_order | 0 | 1 passed, 31 deselected in 0.38s |
| AT-436-2-2 | SM | test_AT_436_2_2_blackout_half_open_midnight_and_ranges | 0 | 1 passed, 31 deselected in 0.40s |
| AT-436-2-3 | SM | test_AT_436_2_3_quota_band_verdict | 0 | 1 passed, 31 deselected in 0.38s |
| AT-436-2-4 | SM | test_AT_436_2_4_other_driver_by_conversation_record_not_mtime | 0 | 1 passed, 31 deselected in 4.55s |
| AT-436-2-5 | SM | test_AT_436_2_5_dirty_tree_boundary | 0 | 1 passed, 31 deselected in 6.40s |
| AT-436-2-6 | SM | test_AT_436_2_6_open_run_and_spawn_precheck | 0 | 1 passed, 31 deselected in 4.56s |
| AT-436-2-7 | SM | test_AT_436_2_7_one_skip_per_cell_and_reason | 0 | 1 passed, 31 deselected in 0.41s |
| AT-436-2-E-1 | SP | test_AT_436_2_E_1_blackout_does_not_become_a_permanent_skip | 0 | 1 passed, 20 deselected in 10.64s |
| AT-436-2-E-2 | SM | test_AT_436_2_E_2_disabled_never_attempts | 0 | 1 passed, 31 deselected in 0.28s |
| AT-436-2-E-3 | SM | test_AT_436_2_E_3_skip_does_not_advance_the_grid | 0 | 1 passed, 31 deselected in 12.44s |
| AT-436-3-1 | SP | test_AT_436_3_1_single_heartbeat_steps_and_detached_spawn | 0 | 1 passed, 20 deselected in 6.67s |
| AT-436-3-2 | SP | test_AT_436_3_2_dry_run_writes_nothing | 0 | 1 passed, 20 deselected in 6.05s |
| AT-436-3-E-1 | SP | test_AT_436_3_E_1_usage_errors_are_rc3_before_anything | 0 | 1 passed, 20 deselected, 3 subtests passed in 6.35s |
| AT-436-3-E-2 | SP | test_AT_436_3_E_2_lock_unattended_and_exception_do_not_retry | 0 | 1 passed, 20 deselected in 6.01s |
| AT-436-4-1 | SG | test_AT_436_4_1_three_tasks_and_per_task_locks | 0 | 1 passed, 30 deselected, 4 subtests passed in 0.85s |
| AT-436-4-2 | SG | test_AT_436_4_2_trigger_action_and_whatif | 0 | 1 passed, 30 deselected in 5.26s |
| AT-436-4-3 | SG | test_AT_436_4_3_wrapper_script_key_surface | 0 | 1 passed, 30 deselected in 1.50s |
| AT-436-4-E-1 | SG | test_AT_436_4_E_1_no_credential_no_claim | 0 | 1 passed, 30 deselected in 4.59s |
| AT-436-4-E-2 | SG | test_AT_436_4_E_2_os_task_and_enable_flag_are_independent | 0 | 1 passed, 30 deselected in 4.66s |
| AT-436-5-1 | SM | test_AT_436_5_1_disable_needs_no_quote | 0 | 1 passed, 31 deselected in 5.81s |
| AT-436-5-2 | SG | test_AT_436_5_2_disarm_verifies_the_task_is_gone | 0 | 1 passed, 30 deselected in 4.26s |
| AT-436-5-E-1 | SP | test_AT_436_5_E_1_patrol_off_is_a_whole_no_op | 0 | 1 passed, 20 deselected, 2 subtests passed in 9.30s |
| AT-436-5-E-2 | SM | test_AT_436_5_E_2_enable_needs_quote_and_unattended_refused | 0 | 1 passed, 31 deselected in 6.05s |
| AT-436-6-1 | SP | test_AT_436_6_1_at_most_one_f_run_per_cell | 0 | 1 passed, 20 deselected in 13.78s |
| AT-436-6-E-1 | SP | test_AT_436_6_E_1_prepare_band_skips_and_no_event_runs_are_not_results | 0 | 1 passed, 20 deselected in 9.78s |
| AT-437-1-1 | SM | test_AT_437_1_1_sched_set_body_bounds_and_types | 0 | 1 passed, 31 deselected in 7.45s |
| AT-437-1-2 | SM | test_AT_437_1_2_run_request_body_and_subject | 0 | 1 passed, 31 deselected in 14.92s |
| AT-437-1-3 | SM | test_AT_437_1_3_real_cli_accepts_console_golden_files | 0 | 1 passed, 31 deselected in 31.65s |
| AT-437-1-E-1 | SM | test_AT_437_1_E_1_no_card_digest_keys | 0 | 1 passed, 31 deselected in 5.96s |
| AT-437-1-E-2 | SM | test_AT_437_1_E_2_text_rules_are_shared_by_reason_and_note | 0 | 1 passed, 31 deselected, 24 subtests passed in 1.02s |
| AT-437-2-1 | SM | test_AT_437_2_1_sched_set_ingest | 0 | 1 passed, 31 deselected in 5.54s |
| AT-437-2-2 | SM | test_AT_437_2_2_run_request_opens_trigger_a | 0 | 1 passed, 31 deselected in 8.04s |
| AT-437-2-3 | SM | test_AT_437_2_3_open_run_turns_request_into_skip | 0 | 1 passed, 31 deselected in 18.21s |
| AT-437-2-E-1 | SM | test_AT_437_2_E_1_unattended_refuses_both_verbs | 0 | 1 passed, 31 deselected in 6.83s |
| AT-437-2-E-2 | SM | test_AT_437_2_E_2_preconditions | 0 | 1 passed, 31 deselected in 7.91s |
| AT-437-3-1 | SM | test_AT_437_3_1_schedule_object_and_export_difference | 0 | 1 passed, 31 deselected in 4.00s |
| AT-437-3-2 | SM | test_AT_437_3_2_armed_credential_is_a_value | 0 | 1 passed, 31 deselected in 5.01s |
| AT-437-3-E-1 | SM | test_AT_437_3_E_1_overdue_is_strictly_greater_than_two_heartbeats | 0 | 1 passed, 31 deselected in 4.10s |
| AT-437-5-1 | SG | test_AT_437_5_1_new_kinds_appear_then_vanish | 0 | 1 passed, 30 deselected in 7.30s |
| AT-437-5-2 | SG | test_AT_437_5_2_check_has_35_items_and_rules_rev_5 | 0 | 1 passed, 30 deselected in 63.81s (0:01:03) |
| AT-437-5-E-1 | SG | test_AT_437_5_E_1_sched_events_four_codes | 0 | 1 passed, 30 deselected, 7 subtests passed in 51.46s |
| AT-437-5-E-2 | SG | test_AT_437_5_E_2_trigger_f_three_codes | 0 | 1 passed, 30 deselected, 5 subtests passed in 44.54s |
| AT-437-5-E-3 | SG | test_AT_437_5_E_3_absent_carrier_and_empty_sets | 0 | 1 passed, 30 deselected in 10.91s |
| AT-438-1-1 | SP | test_AT_438_1_1_spawn_argv_env_and_spawn_json | 0 | 1 passed, 20 deselected, 2 subtests passed in 8.90s |
| AT-438-1-2 | SP | test_AT_438_1_2_research_branches_and_scan_only_in_log | 0 | 1 passed, 20 deselected in 9.33s |
| AT-438-1-E-1 | SP | test_AT_438_1_E_1_missing_claude_is_a_skip_before_any_run | 0 | 1 passed, 20 deselected in 6.03s |
| AT-438-1-E-2 | SP | test_AT_438_1_E_2_child_environment_is_a_whitelist | 0 | 1 passed, 20 deselected in 5.39s |
| AT-438-1-E-3 | SP | test_AT_438_1_E_3_denied_breakaway_fails_closed | 0 | 1 passed, 20 deselected in 12.31s |
| AT-438-2-1 | SP | test_AT_438_2_1_render_fills_uppercase_and_keeps_field_placeholders | 0 | 1 passed, 20 deselected, 3 subtests passed in 1.06s |
| AT-438-2-E-1 | SP | test_AT_438_2_E_1_template_defects_refuse_spawn | 0 | 1 passed, 20 deselected in 11.21s |
| AT-438-3-1 | SP | test_AT_438_3_1_a_class_truth_table_32_cells | 0 | 1 passed, 20 deselected, 32 subtests passed in 49.04s |
| AT-438-3-2 | SP | test_AT_438_3_2_c_class_always_refused_readonly_unaffected | 0 | 1 passed, 20 deselected, 22 subtests passed in 17.80s |
| AT-438-3-E-1 | SP | test_AT_438_3_E_1_cross_run_writes_are_still_refused | 0 | 1 passed, 20 deselected, 12 subtests passed in 13.82s |
| AT-438-3-E-2 | SP | test_AT_438_3_E_2_env_value_edges_and_single_implementation | 0 | 1 passed, 20 deselected, 3 subtests passed in 10.31s |
| AT-438-4-1 | SP | test_AT_438_4_1_decide_accepts_only_console_carrier | 0 | 1 passed, 20 deselected in 7.68s |
| AT-438-4-E-1 | SP | test_AT_438_4_E_1_no_dec_means_no_motion | 0 | 1 passed, 20 deselected in 7.35s |
| AT-438-5-1 | SA | test_AT_438_5_1_promote_then_a_local_commit_of_touched_paths_only | 0 | 1 passed, 20 deselected in 9.68s |
| AT-438-5-E-1 | SA | test_AT_438_5_E_1_dirty_tree_is_a_log_line_not_a_skip | 0 | 1 passed, 20 deselected, 2 subtests passed in 18.88s |
| AT-438-5-E-2 | SA | test_AT_438_5_E_2_stray_files_are_never_added | 0 | 1 passed, 20 deselected in 9.51s |
| AT-438-5-E-3 | SA | test_AT_438_5_E_3_hook_rejection_and_auto_commit_off | 0 | 1 passed, 20 deselected in 15.61s |
| AT-438-6-1 | SA | test_AT_438_6_1_close_follows_the_event_ledger_not_the_self_report | 0 | 1 passed, 20 deselected in 6.67s |
| AT-438-6-2 | SA | test_AT_438_6_2_one_unattended_run_at_a_time | 0 | 1 passed, 20 deselected in 3.09s |
| AT-438-6-E-1 | SA | test_AT_438_6_E_1_incomplete_handback_harness_kill_and_overdue | 0 | 1 passed, 20 deselected, 3 subtests passed in 6.24s |
| AT-438-7-1 | SG | test_AT_438_7_1_patrol_sources_stay_inside_the_allowed_call_set | 0 | 1 passed, 30 deselected, 6 subtests passed in 0.33s |
| AT-438-7-E-1 | SA | test_AT_438_7_E_1_non_evolvable_touch_is_refused_by_the_existing_gate | 0 | 1 passed, 20 deselected in 6.55s |
| AT-438-8-1 | SA | test_AT_438_8_1_console_run_request_runs_in_the_same_heartbeat | 0 | 1 passed, 20 deselected in 1.95s |
| AT-438-8-E-1 | SA | test_AT_438_8_E_1_blocked_console_run_stays_open_and_logs_only | 0 | 1 passed, 20 deselected, 4 subtests passed in 8.05s |
| AT-439-1-1 | SA | test_AT_439_1_1_five_kinds_in_audit_time_order | 0 | 1 passed, 20 deselected in 5.16s |
| AT-439-1-E-1 | SA | test_AT_439_1_E_1_key_never_reaches_any_output | 0 | 1 passed, 20 deselected in 2.37s |
| AT-439-2-1 | SA | test_AT_439_2_1_rejected_file_kept_logged_once_and_lock_busy_retried | 0 | 1 passed, 20 deselected in 1.91s |
| AT-439-2-E-1 | SA | test_AT_439_2_E_1_each_refusal_keeps_the_file_and_logs_one_line | 0 | 1 passed, 20 deselected in 1.06s |
| AT-439-3-1 | SA | test_AT_439_3_1_approve_runs_sandbox_verify_card_verbatim | 0 | 1 passed, 20 deselected in 9.03s |
| AT-439-3-2 | SA | test_AT_439_3_2_promote_rollback_then_run_close | 0 | 1 passed, 20 deselected in 9.92s |
| AT-439-3-E-1 | SA | test_AT_439_3_E_1_only_approve_moves_sandbox | 0 | 1 passed, 20 deselected in 7.35s |
| AT-439-4-1 | SA | test_AT_439_4_1_no_dec_no_motion_and_forged_dec_is_refused | 0 | 1 passed, 20 deselected in 5.92s |
| AT-439-4-E-1 | SA | test_AT_439_4_E_1_missing_freeze_skips_without_a_sched_skip | 0 | 1 passed, 20 deselected in 5.51s |
| AT-439-5-1 | SA | test_AT_439_5_1_log_format_and_steps_are_independent | 0 | 1 passed, 20 deselected in 4.06s |
| AT-439-5-E-1 | SA | test_AT_439_5_E_1_every_line_is_one_line_and_free_of_the_key | 0 | 1 passed, 20 deselected in 1.43s |
| AT-440-1-1 | SG | test_AT_440_1_1_vocabulary_23_and_legal_events | 0 | 1 passed, 30 deselected in 0.21s |
| AT-440-1-E-1 | SG | test_AT_440_1_E_1_each_deformation_gets_exactly_one_code | 0 | 1 passed, 30 deselected, 16 subtests passed in 0.23s |
| AT-440-1-E-2 | SG | test_AT_440_1_E_2_old_events_unchanged_and_message_counts | 0 | 1 passed, 30 deselected in 0.21s |
| AT-440-2-1 | SG | test_AT_440_2_1_41_keys_defaults_and_real_check_green | 0 | 1 passed, 30 deselected in 0.25s |
| AT-440-2-E-1 | SG | test_AT_440_2_E_1_types_ranges_and_cross_keys | 0 | 1 passed, 30 deselected, 10 subtests passed in 0.21s |
| AT-440-2-E-2 | SG | test_AT_440_2_E_2_blackout_covers_triggers_fingerprint_and_baseline | 0 | 1 passed, 30 deselected in 0.24s |
| AT-440-3-1 | SG | test_AT_440_3_1_registry_counts_classes_and_runner_users | 0 | 1 passed, 30 deselected in 1.34s |
| AT-440-3-2 | SG | test_AT_440_3_2_runner_static_invariants_and_forbidden_words | 0 | 1 passed, 30 deselected in 14.49s |
| AT-440-3-E-1 | SG | test_AT_440_3_E_1_injections_are_caught | 0 | 1 passed, 30 deselected, 5 subtests passed in 6.27s |
| AT-440-3-3 | SG | test_AT_440_3_3_foreign_argv_lives_inside_platform_guards | 0 | 1 passed, 30 deselected in 13.20s |
| AT-440-4-1 | SG | test_AT_440_4_1_real_sop_passes | 0 | 1 passed, 30 deselected in 0.20s |
| AT-440-4-E-1 | SG | test_AT_440_4_E_1_deletions_fence_moves_and_injections_are_caught | 0 | 1 passed, 30 deselected, 15 subtests passed in 0.24s |
| AT-440-5-1 | SG | test_AT_440_5_1_old_scenario_tables_replay_on_the_p4_fixture | 0 | 1 passed, 30 deselected, 5 subtests passed in 7.69s |
| AT-440-5-E-1 | SG | test_AT_440_5_E_1_every_sync_site_holds_its_new_value | 0 | 1 passed, 30 deselected in 1.06s |
| AT-440-6-1 | SG | test_AT_440_6_1_every_at_anchors_exactly_one_function | 0 | 1 passed, 30 deselected in 2.25s |
| AT-440-6-E-1 | SG | test_AT_440_6_E_1_anchor_check_has_teeth | 0 | 1 passed, 30 deselected, 4 subtests passed in 0.20s |
| AT-440-7-1 | SG | test_AT_440_7_1_twenty_six_verbs_and_new_flags | 0 | 1 passed, 30 deselected in 2.56s |
| AT-440-7-E-1 | SG | test_AT_440_7_E_1_usage_errors_are_rc3 | 0 | 1 passed, 30 deselected, 8 subtests passed in 1.23s |
| AT-440-8-1 | SG | test_AT_440_8_1_changes_stay_inside_the_allowed_set | 0 | 1 passed, 30 deselected in 0.46s |

## D 覆蓋對帳

- 規格有、測試無：0。105 個 AT 在測試檔各恰一個函式（`-k` 錨定唯一，C 表「測試函式」欄一一對應）。
- 測試有、規格無：0（collect 出 105 個、與表 105 個一一相配）。
- AT-437-1-3：黃金檔來自 `AgentConsole/backend/src/test/resources/si/audit`，測試斷言 sched-set 2 份、run-request 2 份（缺即紅、不 skip）；真 CLI 收下後比對 `audit_sha256` 等於原始位元組的 sha256；負控把原位元組的 `admin` 改成 `admiN`，先斷言「確實改到位元組」再斷言 rc 1 與 `AUDIT-MAC-MISMATCH`。判準有牙。
- 每個測試檔的 AT 數量：SM 32、SP 21、SG 31、SA 21，皆符合 TCS §3.1。

## E 規則對帳（讀碼）

| 規則 | 結論 |
|---|---|
| R142～R145 日曆格 | `sched.walk`：重置＝false（或尚無設定）轉 true，或 enabled 為 true 而週期與前一筆不同；值不變重送不重置，停用不重置。`cell_bounds`：停用／無 origin／now 早於 origin＝None，格為 [起, 終)。`skip_plan`：去重鍵＝(格, reason)，只看非 Console 載體；`overdue`＝啟用且本格無 run.open(f) 且無任何 sched.skip 且 now−格起點嚴格大於 2×心跳。與 TCS 字面一致。突變 M01～M03 證實有牙 |
| R153 run-scoped 授權 | `unattended.gate`：未設 UNATTENDED 全放行；decide 只准 console；A 類須 PATROL_RUN 等於所屬運轉；唯讀放行；C 類（13 個）與未登記動詞一律拒。`check` 先解析所屬運轉（`--run`、PROP 的 run、ATT 當下開著的運轉）。單一實作。M04、M05 證實有牙 |
| R148 一次性心跳 | `patrol.run`：先過 `gate("patrol")`（UNATTENDED 有設 rc 1）；OFF 非空整次 no-op（字面 0 算有設，由 `os.environ.get` 真值決定，空字串視為未設）；鎖 `apply_lock.acquire(…, 0, 7200)`，忙碌回「已有巡邏在跑」；dry-run 不取鎖、`ctx.log` 不寫、不 spawn。M08 證實有牙 |
| R167 脫離式 spawn 與步 0′ | `runner.spawn_detached`：Windows 旗標 `CREATE_BREAKAWAY_FROM_JOB|CREATE_NEW_PROCESS_GROUP|DETACHED_PROCESS` 以 getattr 兜底，POSIX `start_new_session`；`launch` 對 OSError 回 `breakaway-denied`（fail-closed）且不寫 spawn.json；`watch` 以 pid 加啟動時刻判存活、逾牆殺行程樹；同時至多一個（busy 延後）。`spawn.json` 寫入在 spawn 之後 |
| R166 Console (a) 運轉 | `_pending` 納入 `trigger a` 加 `carrier console` 的未 spawn 運轉；被擋只寫日誌、不寫 skip；無 prop 時 `_finish` 以事件帳本為憑 `run-close`。M14 證實有牙 |
| R160 能力登記 | 讀碼：`subprocess` 只出現在 `git.py`、`runner.py`；`runner` 匯入者為 `patrol`、`patrolrun`、`schedarm`、`verify` 四個 exec 檔；`FORBIDDEN_EXEMPT` 只有 `{"schedarm.py": ("schtasks","launchctl","Register-ScheduledTask")}`（`tools/tests/test_selfimproving_capability.py` 113 行，且 SG 的 AT-440-3-E-1 斷言它）。AT-440-3-1／3-2／3-3／3-E-1 皆綠 |
| R161 OS 任務 | 安裝器第三支任務：不帶 `-WakeToRun`、`ExecutionTimeLimit` 為 PT1H、`MultipleInstances IgnoreNew`、同一個 principal（S4U）、Register 共三次；期望表三層鎖逐任務逐值（`installer_problems`）。M13 證實有牙。包裝腳本只取第一個命中行的第一把金鑰、只設行程環境、不印不寫 |
| R162 SOP 判準 | AT-440-4-1／4-E-1 綠；`spawn_problem` 與 `compose` 兩處都檢查 `template_problems`（M11：只拿掉 compose 一處存活＝重複防線的等價突變；M11b：拿掉 `spawn_problem` 那處則紅） |
| 金鑰不入 spawn 環境 | `patrolrun.child_env`：白名單加四個必含鍵，`_SECRET_RE` 剔除含 KEY／TOKEN／SECRET／PASSWORD 的名稱；`spawn_env`（harness 上限）加 `AUTOSDD_UNATTENDED=1` 與 `AUTOSDD_SI_PATROL_RUN`。M10 證實有牙 |
| 自動 commit | `_commit`：只 add 該 PROP 的 touched 與 SI 自有路徑中真有改動者、不用 `-A`、不 push、不帶旁路旗標、失敗寫 obs-draft 不重試、受 `sched_auto_commit` 控制。M12（髒樹仍 promote）證實有牙 |

全套閘門（當回合輸出）：`python tools/selfimproving.py check`＝`overall=PASS rc=0`（35 項，含 `sched.events`、`run.trigger_f_has_patrol_by` 兩項 PASS）；`ruff check`（SI 入口、`tools/lib/selfimproving`、四個新測試檔，`--no-cache`）＝`All checks passed!` rc 0。`check_loc_budget.py --json` rc 1，唯一的 special 違規是 `tools/check_script_parity.py`（loc 1629 對門檻 1618）；該檔是主控在共用樹上未提交的修改，與本鍵無關（本鍵的 SI 檔無違規，檔案列在 `tier_violations`／`absolute_violations` 皆空）。events.py 實體行 506、斷言行數由 AT 守（綠）。

## F 突變表

做法：驅動腳本 `si\qa\mutate.py` 對生產檔做單點字串取代、跑對應測試檔、以位元組備份還原並核 sha256（`restored=true`）。**環境註記**：

- 共用樹上跑的（結果需註記「與主控並行、可能受干擾」）：M01、M02、M03、M04、M05（第一版，存活）、M05 修正版、M06（第一版）、M07（第一版，被我手動中止於進行中並以 Edit 還原）。主控通知後，之後全部在 repo 外 `git worktree`（`C:\Users\wuwei\AppData\Local\Temp\si_qa_wt`，已 `git worktree remove`）跑：M06、M07、M08～M14、M09b、M11b、M06b、M07b。
- 在 worktree 跑的 M06／M07／M13 等結果裡的 `AT-440-8-1` 紅，是突變本身讓 P4 面出現未提交差異而觸發範圍守衛，不計入該突變的「抓到者」。

| 編號 | 突變 | 預期 | 實際（紅的測試） | 結論 |
|---|---|---|---|---|
| M01 | `_in` 格右界含終點 | AT-436-1-2 紅 | AT-436-1-2（共用樹，`1 failed, 1 passed`） | 抓到 |
| M02 | 同格同因重複寫 skip（去重失效） | AT-436-2-7 紅 | AT-436-2-7（共用樹） | 抓到 |
| M03 | overdue 忽略 skip | AT-436-2-E-3 紅 | AT-436-2-E-3（共用樹） | 抓到 |
| M04 | gate 對 PATROL_RUN 不比對運轉（只要有設就放行） | AT-438-3 系列紅 | SP 檔 14 紅（含子測試，共用樹與 worktree 兩次皆紅） | 抓到 |
| M05 | decide 放行 carrier 為字串 "transcript" | AT-438-3-2／4-1 紅 | 存活（`21 passed`）；**不是缺陷**：CLI 的逐字稿載體是 `None`，此突變不可達（B-2） | 等價突變 |
| M05 修正版 | decide 放行 carrier 為 `None`（真實的逐字稿載體） | 同上 | AT-438-3-2、AT-438-4-1 紅（共用樹） | 抓到 |
| M06 | `sched_auto_push=true` 不紅 | AT-440-2-E-1 紅 | worktree：AT-440-2-E-1 子測試 `push-true` 紅（M06b 指名） | 抓到 |
| M07 | trigger f 缺 due_at 仍收 | AT-440-1-E-1 紅 | worktree：AT-440-1-E-1 子測試 `f 缺 due_at` 紅（M07b 指名） | 抓到 |
| M08 | lock 取不到仍跑 | AT-436-3-E-2 紅 | AT-436-3-E-2（worktree） | 抓到 |
| M09 | 入帳依 audit_ref 反轉字串排序 | AT-439-1-1 紅 | **存活**（`21 passed`，worktree） | 見 M09b |
| M09b | 入帳排序鍵只剩 audit_ref（完全不看 time） | AT-439-1-1 紅 | **存活**：四個測試檔 `1 failed, 104 passed`，唯一紅是範圍守衛 AT-440-8-1（突變本身造成） | **無牙＝B-1 P2** |
| M10 | spawn 環境帶入 `AUTOSDD_SI_AUDIT_KEY` | AT-438-1-E-2 紅 | AT-438-1-E-2（worktree） | 抓到 |
| M11 | `compose` 不檢查 template_problems | AT-438-2-E-1 紅 | 存活（`21 passed`）：`spawn_problem` 在到期判定時已先擋，屬重複防線的等價突變 | 等價突變 |
| M11b | `spawn_problem` 不回報範本問題 | AT-438-2-E-1 紅 | AT-438-2-E-1（worktree） | 抓到 |
| M12 | 髒樹仍 promote | AT-438-5-E-1 紅 | SA 檔 2 紅（含 AT-438-5-E-1 子測試，worktree） | 抓到 |
| M13 | `MultipleInstances` 寫成 StopExisting | AT-436-4-1／4-2 紅 | AT-436-4-1、AT-436-4-2（worktree） | 抓到 |
| M14 | 無 prop 不 run-close | AT-438-6-1 紅 | AT-438-6-1、AT-438-6-2、AT-438-8-1 紅（worktree） | 抓到 |

合計：不同設計的有效突變 14 個（M01～M04、M05 修正版、M06、M07、M08、M09b、M10、M11b、M12、M13、M14），抓到 13 個、存活 1 個真缺口（M09b）；另有 2 個等價突變（M05 第一版、M11）不計入。

## G 誠實劃界

- 已知真機紅：`test_install_windows_nightly.py::…::test_live_detector_agreeing_with_the_record_forbids_the_exemption`（本機未以系統管理員 `sched arm` 註冊 `AutoSDD_SI_Patrol`）。本審查沒有跑它、也沒有註冊任務，不計為缺陷。
- 根層全套 `run_root_unittests.py` 由主控跑，我沒跑；我只跑了任務書指名的逐 AT 與 `unittest discover`。
- OS 任務真機註冊、`claude -p` 真 spawn 存活（V30）、Console 端到端均未做；我只審替身與判準。macOS plist 路徑只審判準與 AT，未在 macOS 實測。
- AT-440-8-1（D-IMP-5 常駐形態）：在乾淨 worktree（HEAD 835037ed）上：不設 `SI_P4_BASE_SHA`＝`base=HEAD~1 … guard-not-triggered`、`1 passed`；`SI_P4_BASE_SHA=4445d8dd`＝`guard-not-triggered`、`1 passed`；`SI_P4_BASE_SHA=3e5e472a`＝`1 failed`，列出 outside 檔（`.github/workflows/macos-compat-ci.yml` 等；基準到 HEAD 含棘輪 commit）。三種都與任務書預期一致，守衛有牙。
- 審查期間主控在共用樹上同時修改多個檔（測試、CI workflow、安裝器 `-Argument` 順序等），我早期的共用樹結果可能受其影響；已在 F 註記。AT 親跑與 `unittest discover` 都在共用樹上跑，期間所有 105 個 AT 皆綠，與主控修改的時序無衝突證據，但無法排除。
- 共用樹收尾狀態（`git status --short`，當回合輸出）：只剩主控自己的修改——`.github/workflows/macos-compat-ci.yml`、`.github/workflows/windows-compat-ci.yml`、`docs/03_testing/contracts/TCS-SelfImproving-P4-20261109.md`、`docs/04_planning/AutoSDD_improving_112.md`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`、`tools/check_script_parity.py`、`tools/install_windows_nightly.ps1`、`tools/tests/_selfimproving_p4_fixtures.py`、`tools/tests/test_adr_xplat001_c1c2_lock.py`、`tools/tests/test_check_hooks_liveness.py`、`tools/tests/test_check_script_parity.py`、`tools/tests/test_selfimproving_schedule_advance.py`、`tools/tests/test_selfimproving_schedule_gate.py`、`tools/tests/test_selfimproving_schedule_patrol.py`、`tools/tests/test_windowsapps_guard_cross_consistency.py`；`tools/lib/selfimproving/` 下無任何未提交修改（突變已全數還原並核 hash）；`git worktree list` 只剩主 worktree。

## H 二審（HEAD 40d894bd）

做法：全部在 repo 外 worktree（`C:\Users\wuwei\AppData\Local\Temp\si_qa_wt2`，`git worktree add … 40d894bd`，做完 `git worktree remove`，rc 0）；共用樹未碰。

**1(a) 親跑**（cwd＝worktree，指令 `python -m pytest tools/tests/test_selfimproving_schedule_advance.py tools/tests/test_selfimproving_schedule_gate.py -k <錨> -q -p no:xdist -o addopts=`，rc 先存變數）：
- `AT_439_1_1_`：rc 0，`1 passed, 51 deselected in 3.46s`。
- `AT_436_4_3_`：rc 0，`1 passed, 51 deselected in 0.83s`。
- 結論：兩個受影響 AT 在 40d894bd 皆綠。

**1(b) 突變重放**（驅動 `si\qa\mutate.py`，對 `tools/lib/selfimproving/patrol.py` 入帳 sorted 的 key 單點取代，跑整個 advance 測試檔，位元組備份還原且核 sha256，`restored=true`）：
- M09b（key 只剩 `audit_ref`）：rc 1，`1 failed, 20 passed, 9 subtests passed`，紅的是 `test_AT_439_1_1_five_kinds_in_audit_time_order`。一審存活的缺口已補上，現在有牙。
- M09c（反向：key 只剩 `time`、忽略 `audit_ref` 平手序）：rc 0，`21 passed, 9 subtests passed`，**存活**。原因（讀碼確認）：`status.console_pending` 在 `status.py` 第 77 行已先 `items.sort(key=audit_ref)`，Python 排序穩定，所以入帳排序的第二鍵永遠是冗餘防線；同 time 子案例不可能把它判紅。屬等價突變，記為 B-5（P4，建議：要嘛在入帳端保留此冗餘並接受不可測，要嘛在測試直接餵亂序 items 呼叫 `ingest`），不影響判定。
- 結論：B-1 修復有效（時間排序有牙）；平手序因上游已排序而不可測。

**1(c) B-3 驗收**（`si\qa\tick_check.py`：複製 `si_patrol_tick.ps1` 到暫存樹，照 AT-436-4-3 手法把 `Join-Path $RepoRoot '.venv\Scripts\python.exe'` 換成真 python 路徑，假 `selfimproving.py` 先寫 stderr `FAKE-STDERR boom` 再 `sys.exit(3)`，以 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`（Windows PowerShell 5.1，`C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe`）執行）：
- 輸出：`tick rc = 3`、`tick.log exists: True`；tick.log 內容含 `rc=3`、`fake-out`、`FAKE-STDERR boom`。
- 結論：stderr 不再讓腳本以終止錯誤中斷，tick.log 有落且 rc 3 透傳，B-3 修復有效。

**共用樹**：本輪未動；`git worktree list` 只剩主 worktree，`git status --short` 為空（當回合輸出）。

**B-5（P4，新增）**：入帳排序的 `audit_ref` 平手序因 `console_pending` 已排序而不可測（M09c 存活）；非缺陷。
