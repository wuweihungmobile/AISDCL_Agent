# Risk Log — Phase 0~6 微核心化重構

**最後更新**：2026-05-16（SD_Improving_05 W5 G5 四方審議 4/4 APPROVED）
**對應 Spec**：[SD_Improving_02.md](../04_planning/SD_Improving_02.md) v1.1 §3.1 + [SD_Improving_05.md](../04_planning/SD_Improving_05.md) v2.0 §9
**測試基線**：1,494 passed / 15 skipped（SD_Improving_05 W5 G5 覆驗版通過末，2026-05-16）

---

## 0. SD_Improving_05 風險群（W0 G0 已通過 2026-05-16）

對應 [SD_Improving_05.md v1.4](../04_planning/SD_Improving_05.md) §9 風險登記。Sprint 啟動後逐 G 更新狀態。

| ID | 描述 | 嚴重 | 對應 Critical | 緩解措施 | 狀態 |
|----|------|------|---------------|----------|------|
| **R-SD05-W0-1** | hookspec 擴張破壞既有 EventBus 契約 | 🔴 | C-1 | W0 已完成 6 IHookResult + 8 phase + PHASE_RESULT_CONTRACT 補 15 條；既有 1,199 測試零迴歸 | ✅ 已緩解（2026-05-16，1,275 passed） |
| **R-SD05-W0-2** | MergedResult 7 新欄無 round-trip 測試（SA-C1） | 🔴 | SA-C1 | W0 補 `tests/core/test_event_bus_merged_result.py` 14 case + 6 IHookResult × multi-contributor 合併斷言 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W0-3** | QA Q-M1 escalate（連續 3 次失敗）未實作（SA-C2） | 🔴 | SA-C2 | W0 EventBus 補 FAILURE_ESCALATE_THRESHOLD=3 + is_phase_escalated() + try/finally；`tests/core/test_event_bus_metrics.py` 13 case 把關 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W0-4** | wiring SSOT 兩路徑等價無斷言（SA-C3） | 🔴 | SA-C3 | W0 補 `tests/core/test_wiring_ssot.py` 7 case；wire_plugins_with_registry 補 state_repository 參數 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W0-5** | T18_P2_PHASES_MIGRATED feature flag 未實作（SD-C7） | 🔴 | SD-C7 | W0 新增 `autoclaude/core/phase_migration_flag.py` + 4 case env 變數 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W0-6** | r._priority 對 frozen result raise FrozenInstanceError 被吞為死碼（SD-C1） | 🔴 | SD-C1 | 改用 `object.__setattr__`；event_bus.py 已修；既有 1199 → 1275 passed 驗證 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W0-7** | DefaultResolutionPolicy 用 endswith 推導 evolved_path（Arch-C2/SD-C4） | 🔴 | Arch-C2 | PersistenceResult 加 `kind: str` 欄位；merge 依 kind 路由 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W0-LOC** | `tools/check_loc_budget.py` TOTAL violation（9471 > 8877，因 `_runner_internals.py` 1,766 行未下沉）+ event_bus.py 246 LOC 暫超 200 budget | 🟠 | SD-C2 | **個別 budget 已修**：拆 `resolution_policy.py` 後 event_bus.py < 200；**TOTAL violation deferred W6**（§3 Wave 表 W6 刪除 `_runner_internals.py` 後自然消除） | ✅ 個別已緩解 / 🟡 TOTAL deferred W6 |
| **R-SD05-W1-1** | counter SSOT 遷移順序錯誤打破 Gap-042 / Gap-048 | 🔴 | C-3 | W1 已完成：Step-1（4 counter 搬 plugin SSOT）→ Step-2（CheckpointPlugin 改用 CounterSnapshotResult）；強制順序；20 case 測試把關（13 SSOT + 4 CheckpointRoundTrip + 3 Gap-042/048） | ✅ 已緩解（2026-05-16，1,312 passed） |
| **R-SD05-W1-2** | restore() 物件替換致 alias 失效（W1 Arch-M2） | 🔴 | Arch-M2 | 改為就地 clear+update；alias identity 永不失效；測試 `test_restore_preserves_alias_identity` 把關 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W1-3** | counter_diff key 命名衝突風險（W1 SD-M1） | 🟠 | SD-M1 | SD_05 §6.1 namespace 規範文件化；W2+ 新 plugin 須用 `<plugin>:<counter>` 前綴；DefaultResolutionPolicy 同 key 不同值 raise | ✅ 已緩解（規範文件化 2026-05-16） |
| **R-SD05-W2-pre** | 第 5 個 counter `_consecutive_compact_failures` 範圍劃分（W2 前置） | 🟠 | SD-m2 | SD_05 §6.2 明文劃定 W2 範圍（TokenGuardPlugin 自治；型別 int 非 dict-of-step_id；不參與 CounterSnapshotResult） | ✅ 規劃就位（待 W2 實作） |
| **R-SD05-W2-1** | TokenGuardPlugin 雙寫拔除過程觸發 compact 連續失敗無限循環 | 🔴 | M-2 | W2 已完成：record_compact_failure / process_compact_result 為 plugin SSOT 唯一入口；_consecutive_compact_failures 已改為 property 委派；grep `self\._consecutive_compact_failures\s*[+=]` 在 _runner_internals.py 為 **0 writes**；4 case 測試把關 | ✅ 已緩解（2026-05-16，1,330 passed） |
| **R-SD05-W2-2** | per-step token_guard override 破壞 60+ 既有 YAML（W2 M-7） | 🟠 | M-7 | PlaybookTask.token_guard 為 Optional[dict] 預設 None；既有 YAML 載入測試（example_playbook + mock_playbook）全綠；schema backward compat 6 case 把關 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W2-3** | token_guard_plugin.py LOC 接近 250 上限（W2 風險警示） | 🟠 | §5 #4 | 當前 count_loc=219；docstring 警示「擴張前先拆 token_guard/ package」；子模組設計已就位 SD_05_W0_token_guard_package_design.md v1.1 | ✅ 風險可控（W3 前監控） |
| **R-SD05-W2-4** | token_guard dict 拼錯欄位零偵測（W2 SD-M2/Arch-M2） | 🟠 | SD-M2 | PlaybookTask 加 `field_validator("token_guard")`：以 TokenGuardConfig.model_fields 為白名單；YAML 載入即攔截 typo；5 case 測試把關 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W2-5** | property setter lazy init 雙 SSOT 風險（W2 Arch-C1） | 🟠 | Arch-C1 | getter 不副作用回傳 0；setter lazy 僅供測試 __new__ 場景；__init__ 主流程 line 122 已建立 plugin；既有 30+ 測試 patch 路徑不受影響 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W2-6** | 3 個 plugin 新方法零測試（W2 SA-C1） | 🔴 | SA-C1 | 補 19 case 測試：build_compact_prompt 4 + observe_token_line 6 + verify_correction_applied 4 + typo 防呆 5 | ✅ 已緩解（2026-05-16，1,349 passed） |
| **R-SD05-W3-1** | CheckpointPlugin 三條中斷路徑同步漏一條（hotkey/token_halt/evolution） | 🔴 | SD D-2 | W3 已完成：4 個 mixin 方法（_save_evolution_resume_checkpoint / _handle_token_halt / _save_interrupt_checkpoint / _save_escalation_dump）全部 delegate plugin；test_counter_persistence_three_paths.py 13 case（3×4 規格 + 1 真實 deep-copy 防護） | ✅ 已緩解（2026-05-16，1,368 passed） |
| **R-SD05-W3-2** | EscalationDumpedResult.dump_path 手構字串失真（W3 Arch-C1 / SD-C1） | 🔴 | Arch-C1 | plugin._last_dump_path 記錄 dump.save() 真實回傳路徑；test_escalation_dump_request_returns_real_dump_path 把關（含 Path.exists() 斷言） | ✅ 已緩解（2026-05-16） |
| **R-SD05-W3-3** | EvolutionPlugin 2 NO-OP phase 過渡死碼風險（W3 Arch-C2 / SA-C1） | 🟠 | Arch-C2 | docstring 明標「過渡訂閱位 / W6 完整下沉」；logger.debug → logger.info（audit log 可被監控觀察）；§6.3 第 12 項 W6 拔除清單 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W3-4** | handle_token_halt 19 參數簽名爆炸（W3 Arch-M2 / SD-M2） | 🟠 | Arch-M2 | W3 暫不抽 dataclass（重構風險高，公開 API 已穩）；W6 改為 HaltContext dataclass；§6.3 第 9 項 W6 拔除清單 | 🟡 deferred W6 |
| **R-SD05-W3-5** | _save_escalation_dump closure 捕獲整個 cfg 熱重載污染（W3 Arch-M1） | 🟠 | Arch-M1 | closure 改 SimpleNamespace snapshot（checkpoint_dir + notification.enabled + webhook_url）；§6.3 第 13 項 W6 拔除清單 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W3-6** | 12 case timing_pollution 名實不副（W3 SD-M3） | 🟠 | SD-M3 | 改名 caller_snapshot_discipline（caller-side AC）+ 新增 test_plugin_deep_copy_protects_against_post_save_mutation（真實 race protection 1 case） | ✅ 已緩解（2026-05-16，13 case 全綠） |
| **R-SD05-W3-7** | G3 驗證缺 grep delegate 命令致 double-write 漏抓（W3 SD-M4） | 🟠 | SD-M4 | SD05_Execution_Guide G3 補 3 條 grep：≥ 4 delegate / 0 直接 CheckpointManager / 1 plugin 注入 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-1** | 新 Plugin（FastPath / PlaybookPersistence）priority 順序錯誤 | 🟠 | C-4 | W4 已完成：FastPathPlugin PRIORITY=50（tie-breaker 註冊於 notification/knowledge_base/goal_synthesis 前）；PlaybookPersistencePlugin PRIORITY=40（介於 35/50 之間）；`tests/core/test_wiring_ssot.py::TestW4PriorityInvariant` 3 case 把關 | ✅ 已緩解（2026-05-16，1,435 passed） |
| **R-SD05-W4-2** | FastPathPlugin / PlaybookPersistencePlugin 已建立但 mixin 未 delegate（W4 三方審查 SA-C1/C2 / Arch-m4/m5 / SD-M4） | 🔴 | SA-C1 / SA-C2 | W4 三方覆驗修復：mixin `_fast_path_test_file_check` 改 delegate `plugin._check`；mixin `_persist_mutated_playbook` 改 delegate `plugin.persist_mutated_playbook`；playbook_runner.py load/cleanup 改呼叫 `plugin.load_mutated_if_exists / cleanup_mutated_for_paths`（含 callable resolver 動態 cfg.checkpoint_dir） | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-3** | ConditionalStrategy shell 安全寬鬆（W4 Arch-M1+SD-M2+SA-M1） | 🔴 | Arch-M1 | W4 三方覆驗修復：三層縱深防禦 — (1) regex 白名單收窄為 `[\w\s\-./=:'\"]+`（移除 `!"`），(2) 黑名單 `_DENY_CHARS` 拒絕 `!` `` ` `` `$~><\|&;()*?\\` 等，(3) `_default_evaluator` 改 `shell=False` + `shlex.split`；except 收窄為 `(SubprocessError, OSError, ValueError)`；測試擴張至 14 種 unsafe pattern | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-4** | ConditionalStrategy 巢狀缺遞迴深度防護（W4 SD-M1） | 🔴 | SD-M1 | W4 三方覆驗修復：`apply(_depth=0)` 內部巢狀計數，`_MAX_RECURSION_DEPTH=4` 超限拒絕 + logger.warning；分支若為 CONDITIONAL 走自身 apply 並 +1 depth；測試 `test_apply_blocks_nested_conditional_exceeding_max_depth` 建構 6 層斷言深層 mutation 未生效 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-5** | FastPathPlugin 假陰性（FileNotFoundError 視為通過掩蓋語法錯）（W4 SD-M3） | 🟠 | SD-M3 | W4 三方覆驗修復：`_default_compiler` 4 種例外明確分流 `logger.warning`（FileNotFoundError / TimeoutExpired / OSError / PermissionError），便於監控偵測 fast path 失效 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-6** | PlaybookPersistencePlugin 違反 PHASE_RESULT_CONTRACT 回 None（W4 Arch-M2+SA-M4） | 🟠 | SA-M4 | W4 三方覆驗修復：`on_event` 回 `PersistenceResult(succeeded=True, kind="no_op")` 對齊 PHASE_RESULT_CONTRACT[ON_EVOLUTION_APPLY]={MutationApplyResult, PersistenceResult}；非訂閱 phase 短路 return None | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-7** | conditional.py 101 LOC > 80 IMutationStrategy 預算（W4 LOC violation） | 🟠 | §5 #4 | W4 三方覆驗修復：拆 `_conditional_evaluator.py`（regex 常數 + _default_evaluator helper）；conditional.py 收回 76 LOC ≤ 80；LOC total 10,563 ≤ cap 12,183 / violations=0 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-8** | mixin _validate_global_goal_achievement 簽名與 plugin 不對稱（W4 SD-m5） | 🟢 | SD-m5 | W4 三方覆驗修復：mixin 簽名改 `Optional[str]` 與 plugin 對齊；行為一致 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-9** | cleanup_mutated_for_paths 接受 None 但 type hint Iterable[str]（W4 SD-m1/m9 / SA-m6） | 🟢 | SD-m1 | W4 三方覆驗修復：型別改 `Iterable[Optional[str]]`；測試移除 `type: ignore` | ✅ 已緩解（2026-05-16） |
| **R-SD05-W4-10** | ConditionalStrategy `_set_service` 反向注入 anti-pattern（W4 SA-M3） | 🟢 | SA-M3 | docstring 標 `TODO(SD_05 W6 / SA-M3)`：W6 改 constructor 必填參數，或 IMutationStrategy 加可選 set_service 抽象方法；§6.3 拔除清單第 22 項 | 🟡 deferred W6 |
| **R-SD05-W5-1** | 180+ patch 點測試重寫漏改造成 false green | 🔴 | SD H | 分三批依 dependency tree + 每批 PR 附 patch 對照表 + mutation test ≥ 75% kill rate | ✅ 已緩解（2026-05-16）：tests/plugins/ + tests/core/ + tests/infra/ + tests/integration/ + tests/equivalence/ grep `_runner_internals` 全部無命中；246+264+115=625 case 三 gate 全綠；新增 TestMutationCoverage（regex 防退化）+ TestFixtureInvariant（fixture 不漂移）+ TestKnownFalsePositiveBoundary（4 已知 limitation） |
| **R-SD05-W5-2** | M-8: 7 context regex 樣本「自欺欺人」，缺 unique coverage 證明（W5 三方審查 Critical-SA1） | 🔴 | SA-C1 | W5 三方覆驗修復：新增 `TestMutationCoverage`（移除目標 regex 後 hits 必須減少，至少 regex2 為唯一無交集 regex）+ `TestFixtureInvariant`（`len(_DEFAULT_PATTERNS) == len(_REGEX_FIXTURES)` 防漂移） | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-3** | M-8: negative_no_match.txt 缺 false positive 邊界（tokenizer/tokenization/contextless 等語意陷阱）（W5 三方審查 Critical-SA2） | 🔴 | SA-C2 | W5 三方覆驗修復：重寫 negative_no_match.txt 排除誤匹配；新增 `TestKnownFalsePositiveBoundary` 明示 4 個已知 limitation（tokenizer 65% / tokenization: 50% / contextless 80% / token_efficiency 70%）；docstring 標 SD_06 收斂規劃 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-4** | M-9: `_STUB_PLAYBOOK` 模組級單例可被 plugin 永久污染（Pydantic v2 預設非 frozen）（W5 三方審查 Critical-A1+SD1） | 🔴 | A-C1 | W5 三方覆驗修復：改 `_make_stub_playbook()` 工廠每次新建；docstring 標明 anti-pattern 設計考量；plugin 對 ctx.playbook.tasks.append() 等寫入不會跨呼叫累積污染 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-5** | M-9: `record_wake_and_emit` `except Exception` 吞噬 HookContractViolation 破壞 W0 fail-fast 契約（W5 三方審查 Critical-A2） | 🔴 | A-C2 | W5 三方覆驗修復：except 收斂為 `(OSError, ValueError, RuntimeError)`；`HookContractViolation` 必須冒泡（明確不在 except 範圍）；新增 `test_hook_contract_violation_must_propagate` 用真實 EventBus + BadHook 驗證 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-6** | M-9: `test_emit_exception_does_not_break_main_flow` 用 `_ThrowingBus`（人造 RuntimeError）測試未覆蓋真實 EventBus contract violation 失敗路徑（W5 三方審查 Critical-SD2） | 🔴 | SD-C2 | W5 三方覆驗修復：新增 `test_hook_contract_violation_must_propagate`（真實 EventBus + BadHook 回 PromptInjectionResult，斷言 HookContractViolation 冒泡且 failed_emits +1） | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-7** | M-9: AutoResumeService.metrics property 回內部 mutable 物件參照，外部可直接寫入污染（W5 三方審查 Major-A1） | 🟠 | A-M1 | W5 三方覆驗修復：`metrics` property 改回 `snapshot()` dict（淺拷貝）；新增 `_metrics_object` 內部 helper 供測試斷言；`test_metrics_property_returns_snapshot_dict` 驗證外部寫入不影響內部 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-8** | M-9: `bus=None` 時 metrics 路徑 silently skip emit（wiring 異常無 alarm）（W5 三方審查 Major-A2） | 🟠 | A-M2 | W5 三方覆驗修復：`record_wake_and_emit` `bus is None` 改 `logger.error`；新增 `test_bus_none_logs_error_but_still_records_metrics` 驗證 ERROR log 觸發 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-9** | M-9: 演化 path `wait_secs=0.0` 硬寫死導致 metrics `total_wait_seconds` 漏記（W5 三方審查 Major-A3） | 🟠 | A-M3 | W5 三方覆驗修復：演化重啟 `wait_secs = seconds_until_resume(result.scheduled_resume_at)`，未設時為 0（立即重啟） | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-10** | M-9: `wake_kinds: list` 為 unbounded 容器，long-running session memory leak（W5 三方審查 Major-SA1） | 🟠 | SA-M1 | W5 三方覆驗修復：`wake_kinds = deque(maxlen=200)` bounded 容器；新增 `failed_emits` 計數；新增 `test_wake_kinds_bounded_deque_prevents_memory_leak`（250 wakes → deque len=200，counter 不限） | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-11** | M-9: `kind` 為 str 接受任意值，未知 kind silent failure（W5 三方審查 Major-SA2） | 🟠 | SA-M2 | W5 三方覆驗修復：`kind: Literal["halt","evolution","checkpoint_resume"]` + 未知 raise `ValueError`；新增 `test_unknown_kind_raises_value_error`；keyword-only 強制呼叫端明示意圖 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-12** | M-9: ON_AUTO_RESUME_WAKE phase 無 plugin 訂閱形成死碼（W5 三方審查 Major-SA3） | 🟠 | SA-M3 | W5 三方覆驗修復：`NotificationPlugin` 訂閱 ON_AUTO_RESUME_WAKE，回傳 `ScheduleResumeResult(contributor="notification", ...)` 符合 PHASE_RESULT_CONTRACT；發送桌面通知（kind 中文化）；新增 `test_returns_schedule_resume_result_for_auto_resume_wake` | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-13** | M-9: `record_wake_and_emit` 位置參數順序設計缺陷易誤傳（W5 三方審查 Major-SD5） | 🟠 | SD-M5 | W5 三方覆驗修復：改 `*, kind, scheduled_at, wait_secs` keyword-only；所有呼叫端同步更新；簽名 `(metrics, bus, *, kind, scheduled_at, wait_secs)` | ✅ 已緩解（2026-05-16） |
| **R-SD05-W5-14** | W5 Minor 12 條：snapshot keys forward compat、timezone.utc、上界斷言、fixture invariant、docstring 翻譯腔 | 🟢 | Minor-* | W5 三方覆驗：snapshot keys 用 `>= required_keys`、`datetime.now(timezone.utc)`、`60 < x <= 310` 雙邊界、`TestFixtureInvariant`、docstring 改「以 warning 紀錄並繼續主流程」；MagicMock(side_effect) 取代 `_SeqKernel` 提升可讀性 | ✅ 已緩解（2026-05-16） |
| **R-SD05-W6-1** | `_runner_internals.py` 刪除後仍有外部 import 殘留 | 🟠 | SD G | grep + lint-imports + frozen surface check 三重把關 | 📋 待啟動 |
| **R-SD05-Q-C2** | 1,199 全測時間 > 10 min 拖延 sprint | 🟠 | QA Q-C2 | W0 量測 baseline；> 8 min 必導入 GitHub Actions 7 sharding | 📋 待啟動 |
| **R-SD05-Q-C5** | 60+ 既有 YAML 範本因 PlaybookTask 加 token_guard 欄位 ValidationError | 🔴 | QA Q-C5 | test_playbook_yaml_backward_compat.py 60+ YAML load + Pydantic Optional 預設 None | 📋 待啟動 |
| **R-SD06-1** | PG 三層 schema 與既有 4 表 FK 整合風險（移 SD_06） | 🔴 | C-5 | SD_05 W0 補 test_pg_existing_schema_lock.py 鎖死；SD_06 0008 nullable FK | 📋 SD_06 |
| **R-SD06-2** | 1536 維 vs Minimax 1024/768 維不相容（移 SD_06） | 🔴 | C-6 | EmbeddingConfig + IEmbedder port + alembic ALTER COLUMN 路徑 | 📋 SD_06 |
| **R-SD06-3** | YAML → DB 匯入失敗 → `db_only` 模式無法上線（移 SD_06） | 🔴 | M-11 | SD_06 W4 5 PD 獨立 task；60+ YAML 雙向往返驗證 | 📋 SD_06 |

---

---

## 1. 風險矩陣對照表（R-1 ~ R-12）

下表對照 SD_Improving_02.md §3.1 風險識別表，列出每項目前狀態：

| ID | 風險描述 | 機率 | 影響 | 等級 | 觸發條件 | 緩解措施落地狀態 | 目前狀態 |
|----|----------|------|------|------|----------|------------------|----------|
| **R-1** | 重構期間 ScheduleWakeup / TOKEN_HALT 行為偏移 | 中 | 高 | 🟠 | snapshot byte-level diff > 0 處 | Equivalence test 含 token_halt fixture（fixture 04）；927 tests 全綠 | ✅ 緩解 ok（Phase 4 facade 切換期間需持續驗證） |
| **R-2** | EventBus 同步 dispatch 順序錯誤導致 token compact 在 evaluator 後才觸發 | 中 | 高 | 🟠 | 任一 Plugin 違反 priority 約定表 | EventBus priority 約定 + plugin 訂閱順序測試 | ✅ 緩解 ok（Plugin priority 已落地於 wiring.py） |
| **R-3** | Plugin 之間互相依賴形成隱性耦合 | 高 | 中 | 🟠 | `grep "from autoclaude.plugins\."` 在 plugins/ 下匹配 ≥ 1 處 | 嚴禁 plugin-to-plugin import；CI lint 加入 `import-linter` 檢查 | ⚠️ 仍有 gap：`.importlinter` 已就緒但 **尚未在 CI 強制執行**（避免一次太多變更，列入 Phase 6 P1 之外的後續硬化） |
| **R-4** | Facade shim 漏接某個私有方法導致測試突然 fail | 高 | 低 | 🟡 | 9 項 Frozen Surface 任一 fail 數 ≥ 1 | Phase 4 前列清單；自動產生 Frozen Surface check 腳本 | ✅ 緩解 ok（SD_03 W4 M1 shim 3 方法 + `check_frozen_surface_shim.py` AST 驗證全綠） |
| **R-5** | 舊 Checkpoint 檔在 Phase 5 升級後無法讀取 | 低 | 高 | 🟠 | 既有 `checkpoints/*.checkpoint.json` 任一檔讀取失敗 | FileStateRepository 在 load 時嘗試舊 schema；提供一次性 migration script | ✅ 緩解 ok（FileStateRepository 已實作 schema 容忍） |
| **R-6** | 演化版 Playbook 路徑邏輯漏接 | 中 | 中 | 🟡 | Equivalence fixture 05/12 任一 fail | Equivalence fixture 含 evolution_inject、evolution_counter_esc_f12 case | ✅ 緩解 ok（fixture 12 已存在；Pass 1 將強化為真實 round-trip 驗證） |
| **R-7** | 開發週期過長導致 Evo-007 新需求進來 | 高 | 中 | 🟠 | 主分支 ≥ 5 個工作日無 Plugin PR merge | trunk-based development；weekly cadence | ✅ 緩解 ok（commit `4441a7a` 一次性完成 12 Plugin） |
| **R-8** | PostgreSQL backend 改變 ID 計算方式（path → sha256）破壞 backward compat | 中 | 高 | 🟠 | Phase 6 PR 中任一既有 checkpoint 讀取 fail | 過渡期 File backend 沿用 path-based ID；切到 PG 時提供 dual-id 支援 | ✅ 緩解 ok（File backend 沿用既有 ID；PG migration script 已備） |
| **R-9** | 測試耦合（193 處）的 shim 不夠嚴密，造成行為偏移 | 高 | 高 | 🔴 | Equivalence byte-level diff > 0 OR Gap test 任一退化 | Equivalence test 必過；Phase 4 結束前 QA + PM 雙簽（Gate G3） | ✅ 緩解 ok（Gate G3 三方簽核；Equivalence semantic-level 39 fixtures 全綠；1006 tests 全綠） |
| **R-10** | 開發人員過度設計 Plugin 介面（Phase 2 over-engineering） | 中 | 中 | 🟡 | 任一 Plugin 行數 > 250 OR Kernel > 250 OR 總增量 > +20% | Architect 把關 hookspec；`tools/check_loc_budget.py` CI gate | ✅ 緩解 ok（LOC budget 違反數 = 0；Pass 1 已將 CI workflow 加入 budget check） |
| **R-11** | GotoCounterPlugin 計數器邏輯與 Kernel 不一致導致 Gap-042/048/049 退化 | 中 | 高 | 🟠 | `pytest tests/equivalence/fixtures/{11,12,13}_*.yaml` 任一 fail | 三個專屬 fixture byte-level 比對；GotoCounterPlugin PR DoD 強制執行 | ⚠️ 仍有 gap：fixture 11/12/13 目前以 dry_run 模式存在，**尚未真正驗證** counter round-trip；Pass 1 強化為 mock minimax + mock executor 完整流程 |
| **R-12** | CLI 介面破壞向後相容（如 exit code 變更） | 低 | 高 | 🟠 | `tests/cli/test_cli_compatibility.py` 9 場景任一 fail | Phase 0 即建立 CLI snapshot；任一退化即 PR fail | ⚠️ 仍有 gap：CLI 測試目前直接呼叫 `main_module._validate_playbook_format()` 而非 `subprocess.run`；Pass 1 改為 subprocess 模式以涵蓋 exit code 0/1/2/3 全場景 |

---

## 2. 風險等級圖例

- 🔴 **嚴重**（Critical）：須立即處理，未緩解前不得進入下一 Phase
- 🟠 **高**（High）：須在當前 Phase 內緩解
- 🟡 **中**（Medium）：可列入監控，不阻擋 Phase 推進

## 3. 狀態圖例

- ✅ **緩解 ok**：所有觸發條件均通過驗證，無 active gap
- ⚠️ **仍有 gap**：部分緩解措施已落地，但尚有殘留風險（請見備註）
- ⏳ **進行中**：屬於後續 Phase / Pass 範圍
- 🔴 **未緩解**：觸發條件已成立，需立即處理

---

## 4. 重點待緩解風險（Pass 1 處理項）

| Risk ID | 處理項 | 對應修復項 | 狀態 |
|---------|--------|------------|------|
| R-3 | `.importlinter` 配置就緒 + CI 強制 | M5（Pass 1） | ✅ 完全關閉（2026-05-15）：`CounterSnapshot` 移出 plugins 至 `models/counter_snapshot.py`，修正 plugin-isolation；`core-purity` 精細化 source_modules（排除 wiring）+ `ignore_imports` 豁免懶加載橋接；CI `test` job 加入 `lint-imports` 步驟；2 contracts KEPT，1034 tests 全綠 |
| R-10 | CI 加入 `tools/check_loc_budget.py` gate | F5（Pass 1） | ✅ 已完成（check_loc_budget.py CI 已啟用） |
| R-11 | Equivalence fixture 11/12/13 改為真實 counter round-trip | F7（Pass 1） | ✅ 完全關閉（`tests/equivalence/test_counter_persistence.py` 已存在，Gap-042/048/049 完整 round-trip 驗證，31 tests 全綠） |
| R-12 | CLI 相容性測試改用 `subprocess.run` | F8（Pass 1） | ✅ 完全關閉（`tests/cli/test_cli_compatibility.py` S1~S9 全部含 `_via_subprocess` 版本，涵蓋 exit code 0/1/2，31 tests 全綠） |

## 5. 後續待緩解風險（SD_Improving_03 sprint 範圍）

| Risk ID | 處理項 | 對應 Phase / SD |
|---------|--------|------------------|
| R-1 / R-9 | Phase 4 facade 切換 Equivalence 維持（v1.1 已降級為 semantic-level） | SD_03 v1.1 §4.3 |
| R-4 | 9 項 Frozen Surface shim 純委派 + AST 驗證 | SD_03 W4 / M1 |

## 6. SD_Improving_03 三方審查新增風險（R-13 ~ R-16 + R-G1 ~ R-G4）

依 [SD_Improving_03 v1.1](../04_planning/SD_Improving_03_Phase4_Real_Switch.md) §4.3 風險矩陣補充：

| ID | 風險描述 | 機率 | 影響 | 等級 | 觸發條件 | 緩解措施 | 目前狀態 |
|----|----------|------|------|------|----------|----------|----------|
| **R-13** | Plugin priority 排序破 byte-level snapshot；step_log 行排序與舊 _runner_impl inline 順序不一致 | 高 | 中 | 🟠 | Stage A snapshot `step_log` semantic 對齊但行排序差異 | §2.3 emit ordering 契約 + `test_plugin_emit_order.py` | ✅ 緩解 ok（SD_03 W2 Plugin emit ordering 契約測試 + 順序驗證全綠） |
| **R-14** | `storage.mode="both"` silent drop（F1 完成但 F3 未完成，DualStateRepository 注入但 facade 仍走舊 `_checkpoint_mgr`） | 高 | 中 | 🟠 | F3 未在同 sprint 完成 OR 缺整合測試 | F3 / F1 同 sprint；補 `test_dual_repository_smoke.py` | ✅ 緩解 ok（SD_03 W4 F3 main.py 注入完成；DualStateRepository 整合測試全綠） |
| **R-15** | 跨 Plugin state 共享需求違反 SD_02 §5「禁止行為」第 4 條 | 中 | 中 | 🟡 | TokenGuardPlugin / EvolutionPlugin 透過 plugin-to-plugin import 共享 state | 透過 HookContext.payload 通訊（SD_03 §2.3 契約）；嚴禁 plugin import；AutoResumeService 拉到 Layer 2 持有跨 Plugin state | ✅ 緩解 ok（SD_03 W2/W3 AutoResumeService Layer 2 完成；plugin-to-plugin import 全部消除） |
| **R-16** | W1 反向委派失敗連鎖（CheckpointManager mock 耦合 ≥ 11 處） | 中 | 高 | 🟠 | W1b 末 944 tests 紅 ≥ 50 個 | W1a 先解耦 internal alias + DeprecationWarning 預設關閉 + W4 才開 strict 模式 | ✅ 緩解 ok（SD_03 W1a/W1b CheckpointManager 反向委派完成；1006 tests 全綠） |
| **R-G1** | 治理：時程延期（byte-level / semantic-level 連續 2 工作天 fail） | 中 | 中 | 🟡 | Stage A 連續 2 天紅 | Tech Lead + PM 雙簽決定 delay / revert / 降級 | ✅ 緩解 ok（SD_03 W0~W5 準時完成，無延期事件） |
| **R-G2** | 治理：品質降級（byte-level 不可達需降為 semantic-level） | 高 | 中 | 🟠 | W2 末 byte-level 仍不可達 | v1.1 已預先降級（SD_03 §2.4） | ✅ 已預先緩解 |
| **R-G3** | 治理：人力單點 bus factor=1 | 中 | 中 | 🟡 | Owner 請假 / 離職 | pair review F1 主迴圈；W2/W3 必雙人 commit | ✅ 緩解 ok（wuweihungmobile 全程 Owner；SD_03 全程無人力中斷） |
| **R-G4** | 治理：PM 簽核時程延宕 | 中 | 中 | 🟡 | W4 末 + 3 工作日內未簽 | 升級至 Architect 拒絕 merge；revert 整 sprint 標 incomplete | ✅ 緩解 ok（PM 於 W4 末 +1 工作日完成 Stage B smoke 簽核；G3 無延宕） |

---

## 7. _runner_impl.py 刪除 Sprint 風險（R-A ~ R-D）

依 [SD_Delete_RunnerImpl.md](../04_planning/SD_Delete_RunnerImpl.md) 補充；啟動時更新狀態。

| ID | 風險描述 | 機率 | 影響 | 等級 | 觸發條件 | 緩解措施 | 目前狀態 |
|----|----------|------|------|------|----------|----------|----------|
| **R-A** | `dry_run=True` 語意無法完整重現（FakeExecutor 無法模擬所有 dry_run 輸出分支） | 中 | 高 | 🟠 | FakeExecutor 合成輸出與 dry_run 合成輸出 semantic diff > 0 | Equivalence fixture 驗證；FakeExecutor 支援 per-call outputs 列表 | ✅ 已緩解（FakeExecutor 完整替代 dry_run 語意，W5 完成驗證） |
| **R-B** | 193 處 `mock.patch` 耦合路徑失效（patch 路徑含 `_runner_impl` 或舊 method） | 高 | 中 | 🟠 | 任一測試 `mock.patch` 路徑 ImportError 或 patch 未生效 | 遷移時改為 DI 注入 Fake Port；逐一審視 193 處 | ✅ 已緩解（W2~W5 逐一轉換完畢，M1 shim 維持相容） |
| **R-C** | Plugin state 斷言失效（goto_counter 等 plugin state 無法從 Kernel 外部存取） | 中 | 中 | 🟡 | 測試斷言 `plugin.goto_counter` 無法存取 | `make_kernel()` 返回 `plugins_dict`，允許直接斷言 | ✅ 已緩解（make_kernel() 返回 (kernel, plugins_dict) tuple，W1 設計通過） |
| **R-D** | Sprint 時程延誤（380 tests，5 週） | 中 | 中 | 🟡 | 任一週 Gate 超過 2 個工作日未過 | 按難度排序遷移；每週 Gate 確認；延誤 > 2 工作日啟動 Tech Lead + PM 評估 | ✅ 已緩解（W1~W5 準時完成，2026-05-14 G6 通過） |

---

## 8. Phase 6 db_only Security Hardening（PM/Stakeholder 條件式簽核後置項）

依 Runbook §5 PM-Agent + Stakeholder-Agent APPROVE_WITH_CONDITIONS（2026-05-14）建立；以下為必要後置條件風險。

| ID | 風險描述 | 機率 | 影響 | 等級 | 截止日期 | 負責人 | 目前狀態 |
|----|----------|------|------|------|----------|--------|----------|
| **R-P6-01** | TLS 未強制（AUTOCLAUDE_ALLOW_INSECURE_DB=1 暫用），正式生產環境為安全漏洞 | 高 | 高 | 🔴 | 2026-05-21 | wuweihungmobile | ✅ 完全關閉（2026-05-15）：config.local.yaml 已加入 sslmode=require；check_both_mode_metrics.py 移除 ALLOW_INSECURE_DB setdefault；DB 主機 `SHOW ssl;` 確認 on（TLSv1.3，AES_256_GCM_SHA384） |
| **R-P6-02** | `autoclaude_runtime` 密碼未輪換（`runtime_autoclaude_2026` 為弱密碼），違反 Security P0 | 高 | 高 | 🔴 | 2026-05-21 | wuweihungmobile | ✅ 完全關閉（2026-05-15）：強密碼（24 字元）已更新至 config.local.yaml；PG_Role_Setup.md 移除明文密碼；DB 主機 `ALTER ROLE autoclaude_runtime PASSWORD '...'` 執行完成 |
| **R-P6-03** | 四方安全審查殘餘 P0 項目（DBA 2/8 + Infra 3/7 + SRE 2/5 + Security 3/8 = 10 項）未關閉 | 高 | 中 | 🟠 | 2026-05-28 | wuweihungmobile | ✅ 緩解 ok（2026-05-15）：P1 #1~#10 全部實作完成並驗證；詳見 [Phase6_PG_Stakeholder_Signoff.md](../08_deployment/Phase6_PG_Stakeholder_Signoff.md) P1 完成表 |
| **R-P6-04** | 正式生產環境（production workload）上線前缺乏四方無條件 APPROVE 安全審查 | 中 | 高 | 🟠 | 正式生產前 | wuweihungmobile | ⏳ 本次簽核僅適用 staging/local 環境（對應 Stakeholder C4）；正式 production 切換前需重新審查 |

---

## 9. SD_Improving_04 W2 三方審查新增風險（R-W2-1 ~ R-W2-4）

依 [SD_Improving_04.md](../04_planning/SD_Improving_04.md) v1.5 §4 G3 通過末，三方覆驗（Architect / SA / Dev）共識列出。

| ID | 風險描述 | 機率 | 影響 | 等級 | 觸發條件 | 緩解措施 | 目前狀態 |
|----|----------|------|------|------|----------|----------|----------|
| **R-W2-1** | `db_only` 模式下 AutoResumeService（用 `canonical_playbook_id(p, cfg.storage.mode)`）與 CheckpointPlugin（用 `Path.stem`）ID 不一致導致 auto-resume 永遠讀不到 checkpoint | 高 | 高 | 🔴 | `storage.mode="db_only"` 下 _resolve_start 永遠回 has_ck=False | wiring.build_kernel + wire_plugins_with_registry 注入 `id_resolver=lambda p: canonical_playbook_id(p, cfg.storage.mode)` SSOT | ✅ 已緩解（2026-05-15）：`tests/integration/test_db_only_resume_ssot.py` 驗 SSOT；wiring.py L150 / L73 已注入 |
| **R-W2-2** | T10 邊界 4「多 run 並發」測試僅以 InMemoryStateRepository 驗證「不 crash」，PG 真實 unique index 並發語意未驗證 | 中 | 中 | 🟡 | 真實 PG 上多 run 並發寫 checkpoint 觸發 unique violation | 移交 staging 真實 PG 驗證；對應 R-P6-04 production hardening 流程 | ⏳ 移交 staging（W3 / W4 期間規劃） |
| **R-W2-3** | PlaybookRunner inline token guard 邏輯與 TokenGuardPlugin 雙寫風險（compact 偵測可能在兩處皆觸發）；W2 範圍僅 Plugin coverage 100%，inline 邏輯保留 | 中 | 中 | 🟡 | W3 完成前任一 token compact 場景被觸發兩次 | W2 範圍僅 Plugin 完整化；W3-T12 PlaybookRunner 瘦身一併遷移至 EventBus 廣播 | ⏳ 移交 W3（SD_04 §5 T12） |
| **R-W2-4** | core/services/auto_resume.py 對 canonical_playbook_id 的 lazy import 雖正確（pure function，無 infra runtime deps），但 importlinter 仍偵測為 core→infra 違規 | 低 | 低 | 🟡 | `lint-imports` 對 core-purity contract 報 1 violation | `.importlinter` ignore_imports 新增 `autoclaude.core.services.auto_resume -> autoclaude.infra.repositories.factory` deliberate bridge | ✅ 已緩解（2026-05-15）：`.importlinter` L57 已補入 |

---

## 10. SD_Improving_04 W3 三方審查新增風險（R-W3-1 ~ R-W3-2）

依 [SD_Improving_04.md](../04_planning/SD_Improving_04.md) v1.6 §5 G4 通過末，W3 三方審查（Architect / SA / Dev）共識列出。

| ID | 風險描述 | 機率 | 影響 | 等級 | 觸發條件 | 緩解措施 | 責任 | 目前狀態 |
|----|----------|------|------|------|----------|----------|------|----------|
| **R-W3-1** | mixin `_runner_internals.py` 1,753 行新技術債：W3 PlaybookRunner 282 行達標係透過 mixin 抽檔（非 Plugin 真正下沉），若 W4-T18 未完成則 `_runner_internals.py` 將成永久 god-object，違背微核心化目標 | 高 | 高 | 🟠 | W4 末 `_runner_internals.py` 仍存在 OR mixin 行數 > 1,000 | W4-T18 sprint 內必達：將 `_run_steps`/`_apply_single_mutation_full`/`_handle_token_halt` 等真正下沉至對應 Plugin；W4-T16 同步刪除 mixin 檔案；若工時不足移至 W5 sprint | Tech Lead | ⏳ 部分緩解；完整下沉移交 **SD_Improving_05 T18-P2**（W4 三方審議結論，2026-05-15） |
| **R-W3-2** | PlaybookRunner inline token guard 與 TokenGuardPlugin 雙寫風險（R-W2-3 延續）：W3 範圍僅完成 mixin 抽檔，inline 邏輯仍存在於 `_runner_internals.py`，雙寫風險未閉合 | 中 | 中 | 🟡 | W4 完成前任一 token compact 場景被觸發兩次 | 移交 W4-T18 完成 inline 邏輯真正下沉至 TokenGuardPlugin（EventBus 廣播） | Tech Lead | ⏳ 移交 **SD_Improving_05 T18-P2**（R-W2-3 延續） |
| **SD_04-W4-Observation-1** | mixin `_pr()` 動態反查 playbook_runner 模組形成雙向耦合：W4-T18 階段 1 評估顯示，30+ 個測試檔（`test_token_checkpoint.py` / `test_playbook_runner.py` / `test_gap009.py` / `test_gap010.py` / `test_gap014_020.py`）依賴 `patch("autoclaude.execution.playbook_runner.PtyWrapper/notify_escalation/ConvergenceMonitor/CrossStepStateValidator/shutil.which")` 路徑生效；若強行於 W4 移除 `_pr()` 將破壞 ≥ 30 個測試（超出單一 sprint 工時上限） | 高 | 中 | 🟡 | `_pr()` 仍存在於 `_runner_internals.py` | W4 已加 docstring 標註 DEPRECATED + 觀察項；完整移除排程於 **SD_Improving_05 T18-P2**（與 mixin 完整下沉一併處理，屆時測試 patch 路徑同步切換至 Plugin / Kernel module） | Tech Lead | ⏳ 觀察中（W4-T18 階段 1 末，2026-05-15） |

---

---

## 11. SD_Improving_05 W6 新增風險（R-W6-1 ~ R-W6-5）

依 [SD_Improving_05.md](../04_planning/SD_Improving_05.md) §8 R-W6-1 + [SD05_Migration_Guide.md](../08_deployment/SD05_Migration_Guide.md) §6 SD_06 範圍。W6 為 SD_05 收尾波（3 PD），部分項目因核心執行邏輯下沉工作量超過預算，標註為 SD_06 W0~W3 延後項。

| ID | 風險描述 | 機率 | 影響 | 等級 | 觸發條件 | 緩解措施 | 責任 | 目前狀態 |
|----|----------|------|------|------|----------|----------|------|----------|
| **R-W6-1** | `autoclaude/execution/_runner_internals.py`（1,694 行）未物理刪除 — W6 預算 3 PD 不足以下沉 `_run_steps`（840 行）+ `_apply_single_mutation_full`（295 行）+ `_execute_prompt`（79 行）核心執行邏輯 | 中 | 中 | 🟢 | `_runner_internals.py` 仍存在 codebase | SD_06 W2 G2 拆 6 strategy 模組（1,694 → 98 LOC）；**SD_06 W6 G6 物理刪除（2026-05-18）** — 98 LOC mixin + `_pr()` 全搬入 `playbook_runner.py`；5 個 strategy 檔案 import path 同步更新 | Tech Lead | ✅ **CLOSED 2026-05-18 W6 G6** |
| **R-W6-2** | `autoclaude/execution/_runner_compat.py`（238 行）未物理刪除 — 仍含 PlaybookResult / PlaybookState / _StepOutput / _MutationResult / _apply_single_mutation_impl 等被多處 import | 低 | 低 | 🟢 | `_runner_compat.py` 仍存在 codebase | **SD_06 W6 G6 物理刪除（2026-05-18）** — 內容遷至新建 `autoclaude/execution/types.py`（258 LOC）；12 處 import path 改 `from .types import`；main.py 移除 `import warnings` + DeprecationWarning filter | Tech Lead | ✅ **CLOSED 2026-05-18 W6 G6** |
| **R-W6-3** | `PlaybookRunner.run()` 回傳 `PlaybookResult` 而非 `KernelResult`（SD_05 §5 ❌5 並存風險） — 雖 main.py 已透過 AutoResumeService 走 KernelResult，但 PlaybookRunner 仍對外暴露 PlaybookResult | 低 | 低 | 🟡 | 直接呼叫 PlaybookRunner.run() 的客戶端 | SD_06 W6 G6 過渡方案：PlaybookResult 新增 `halted` property alias + `to_kernel_result()` 雙向轉換 helper；物理拔除（PlaybookRunner.run() 型別宣告改 KernelResult + 50+ test assertion 遷移）**延後 SD_07**（沿用 SD_05 §1.3 PM 例外簽核）| Tech Lead | ⏳ partial — deferred SD_07 |
| **R-W6-4** | SD_05 §6.3 22 項拔除清單未完成項（W3 範圍 8/9/10/12/13/14 + W4 範圍 15/16/17/18/19/20/21/22 等 ≥ 15 項） — 各 delegate wrapper / NO-OP audit 仍存在於 mixin / plugin 邊界 | 中 | 低 | 🟢 | `grep TODO(SD_05 W6)` 應為 0 | **SD_06 W6 G6 字串清零（2026-05-18）** — `_runner_internals.py` + `_runner_compat.py` 物理刪除已涵蓋 ~18/22 項；mutable container path 物理拔除（goto_counter + checkpoint/_builder）；剩 2 項 `_consecutive_compact_failures` / `_prepend_global_goal_brief` shim 因 20+ 處測試 patch path 標 `NOTE(SD_07)` 延期 | Tech Lead | ✅ **CLOSED 2026-05-18 W6 G6（剩 2 項 SD_07）** |
| **R-W6-5** | `_runner_internals.py::_pr()` 反向動態 import 維持雙向耦合（SD_04-W4-Observation-1 延續） — 30+ 測試以 `patch("autoclaude.execution.playbook_runner.X")` 模式生效依賴此反查 | 中 | 中 | 🟢 | 30+ 測試 patch path 需同步遷移 | **SD_06 W6 G6 拔除（2026-05-18）** — `_pr()` 從 `_runner_internals` 搬至 `playbook_runner`（同檔內 `def _pr()`）；5 個 strategy 檔案 `from .playbook_runner import _pr` 同步更新；測試 patch path `autoclaude.execution.playbook_runner.*` 全部維持相容（不需遷移）| Tech Lead | ✅ **CLOSED 2026-05-18 W6 G6** |

---

## 12. SD_Improving_06 新增風險（R-SD06-0-1 ~ R-SD06-6-2，三方+QA 四方審議 2026-05-17）

依 [SD_Improving_06.md v1.1](../04_planning/SD_Improving_06.md) §8 風險登記表，三方審查共識列為 Critical 12 項（對應使用者 6 大關注議題），QA 四方審議 APPROVED_WITH_CONDITIONS 後升版。

| ID | 描述 | 嚴重 | 對應議題 | 緩解措施 | 狀態 |
|----|------|------|---------|----------|------|
| **R-SD06-0-1** | BrainPort 過於貧瘠（單方法），Runner 變相扮演 Orchestrator | 🔴 | #0 Minimax/Claude Code 分工 | W1 引入 OrchestrationCoordinator + BrainPort/ExecutorPort 擴張（capabilities / on_event / send_interrupt）| 📋 SD_06 W1 |
| **R-SD06-0-2** | Brain/Executor 反向 callback 依賴 + Interrupt 信號競態 | 🔴 | #0 | EventBus 而非直接 callback；asyncio.Event + seq number + Executor ACK | 📋 SD_06 W1 |
| **R-SD06-1-1** | `_runner_internals.py` 1,694 行為 god-class anti-pattern | 🔴 | #1 肥胖檔案 | W2 拆 6 strategy 模組（steps_orchestrator / prompt_dispatcher / mutation_applier / compact_controller / halt_handler / escalation_dumper，each ≤ 250 LOC）| ✅ **已基本緩解（2026-05-17 W2 G2 階段 4 完成）**：`_runner_internals.py` 1,694 → **98 LOC (-94.2%)**；8 strategy 模組（+ mutation_applier 拆 4 子模組 + steps_orchestrator 拆 6 子模組）；mixin 全 thin shim。`_impl.py` 874 → **736 LOC (-15.8%)** + 4 子模組（_context_negotiation/_loop_state/_step_init/_goal_synthesis 全 ≤ 137 LOC）；剩餘 736 行 state machine 需重設計為 state pattern → deferred W6 mixin 重設計時一併處理 |
| **R-SD06-2-1** | mixin 與 plugin 雙寫法導致 SSOT 破裂（`_save_*_checkpoint` 兩處實作） | 🔴 | #2 Plugin 架構 | W2 物理移除 mixin 中 3 個 `_save_*`；importlinter 新增 `runner-no-checkpoint-logic` contract | ✅ **已緩解（2026-05-17 W2 G2 通過）**：mixin `_save_evolution_resume_checkpoint` + `_save_interrupt_checkpoint` def 物理刪除；`_save_escalation_dump` 下沉至 escalation_dumper.py；grep `_save_.*_checkpoint` 命中 11 → **0 ✅**（AC2-1 達成）；tests/contract/test_runner_no_checkpoint_logic.py G2 gate enforce + 退化保護；test_gap039_049.py 2 處 patch path 改呼叫 plugin 公開 API |
| **R-SD06-3-1** | 4 表離 PM §10 三層差距巨大 + 缺 RBAC 五表 | 🔴 | #3 PG 三層 | W3 alembic 0009 三表 + 0011 RBAC + 0010 既有 4 表加 nullable FK | 📋 SD_06 W3 |
| **R-SD06-3-2** | 多 run 並存約束未設計（同 GoalTask N 個 active run）| 🟠 | #3 | partial index `WHERE status='running'` + `abort_run(run_id)` API | 📋 SD_06 W3 |
| **R-SD06-4-1** | 1536 維寫死 vs BGE-M3 1024 維 + 寫入路徑為 0 | 🔴 | #4 向量檢索 | W3-2 採「新欄位 + dual-read」模式（非 ALTER）；舊 vector(1536) 6 個月 deprecation；CircuitBreaker latency > 200ms 自動降級 | 📋 SD_06 W3 |
| **R-SD06-4-2** | HNSW 線上重建鎖表（大表 > 1M 列）| 🔴 | #4 | `CREATE INDEX ... CONCURRENTLY` + partial index per model_id | 📋 SD_06 W3 |
| **R-SD06-5-1** | `dual_state_repository.fail_loud` 僅比對 step_idx | 🔴 | #5 狀態恢復 | W5 升級為 dataclasses.asdict() 全欄比對 + `_normalize()`（datetime/UUID/Enum）+ drift_log 表 | 📋 SD_06 W5 |
| **R-SD06-5-2** | _resolve_start run_id 改造破壞 CLI 相容 | 🟠 | #5 | load_latest_by_playbook fallback + DeprecationWarning 至 v0.7；`--resume` 強制顯式 `--run-id` | 📋 SD_06 W5 |
| **R-SD06-6-1** | config.yaml 無 per-step / per-workflow hierarchy + 無 audit log | 🟠 | #6 設定檔 | W5 ConfigResolver 4 層 merge + Pydantic v2 `model_validator` invariants + `config_audit_log` 表 | 📋 SD_06 W5 |
| **R-SD06-6-2** | Pydantic flat→nested 向下相容 | 🟠 | #6 | `model_validator(mode="before")` 自動 promote + DeprecationWarning | 📋 SD_06 W5 |
| **R-SD06-QA-C1** | SD_06 v1.0 AC 不可量測 | 🔴 | QA 四方審議 | v1.1 §6.5 AC Matrix 25 條（量測命令 + Pass 門檻 + 測試檔路徑）| ✅ 已緩解（2026-05-17）|
| **R-SD06-QA-C2** | W3 0007/0010/0011/0012 缺 contract test 對位 | 🔴 | QA | v1.1 §6 alembic 表新增 contract test 對位（6-10 case each）| ✅ 已緩解（2026-05-17）|
| **R-SD06-QA-C3** | alembic 回退策略不可行（0010 backfill 三步 + 0008 dual-read）| 🔴 | QA | v1.1 §11 per-migration 回退劇本 + point-of-no-return 標記 + 黃線告警 48h | ✅ 已緩解（2026-05-17）|
| **R-SD06-QA-C4** | HNSW 重建期間查詢服務維持機制未定義 | 🔴 | QA | v1.1 §6 dual-read 模式 + fallback_query_path + CircuitBreaker 降級 | ✅ 已緩解（2026-05-17）|
| **R-SD06-QA-PM1** | 0010 FK backfill 三步單點失效（W3-4 進入前需 1M 列 staging dry-run）| 🔴 → 🟢 | QA → PM 警示 | 場景 A（個人開發 / dev / 無外部稽核）：演練閉環即足夠 | ✅ **已緩解（場景 A 通過 2026-05-17 user 確認；AI-Agent 演練版，2026-05-17）**：DBA-Agent 在本地 docker `autoclaude_pg`（pgvector/pgvector:pg16）完成 **1M 列完整 dry-run**：seed 1M + backup 2.689s + alembic upgrade 0.584-0.668s + 1M backfill 46.357s (230ms/batch / 46μs/row / rate=1.00 ≥ 0.95 ✅) + §4.1 回退驗證 6/6 + §5 Point-of-no-return 模擬（30% 中斷無 idle-tx/deadlock，前滾修補 15.328s 至 100%）+ pg_restore 8.053s。`SD06_FK_DryRun_Report.md` §6.1~§6.6 全部填妥，§7 AI-Agent 三方簽核完成。**⛔ Production 上線仍需人類 DBA 在公司 staging（≥ 1M 真實列）重跑 + 人類 PM 親簽 release approval**（PM W-1 稽核紅線；本演練不涵蓋並發負載 / WAL lag / 雲端 IOPS 風險）|
| **R-SD06-QA-PM2** | PII / secret mask 規則延到 W3/W5 太晚 → 365 天 partition 合規債務 | 🔴 | QA → PM 警示 | **PM 簽核 (C) hybrid** 連動 #11：W0 完成 PII/secret/normal ENUM 欄位分類 + W3 過濾器實作；W0 review 拉法務/Security 共審；W0 +1 PD | ✅ **已緩解（2026-05-17 超前完成）**：W0 ENUM + PII minutes 法務/Security 五方共審 APPROVED_WITH_CONDITIONS（10 欄位裁定全完成；遮罩演算法 C 混用；5 條件 W3 G3 對位 — 含 W3 過濾器整合測試 + retention policy 文件化）|

### 12.1 PM 拍板決議連動風險（2026-05-17 SD_06 v1.2）

| ID | 描述 | 嚴重 | 來源 | 緩解措施 | 狀態 |
|----|------|------|------|----------|------|
| **R-SD06-PM-#8** | MAX_ACTIVE_RUNS_PER_GOAL=5 需在 W2 OrchestrationCoordinator 落地前埋 guard | 🟠 | PM 拍板 #8 + Tech Lead 警示 | W2 task 加 guard 驗證測試；W4 才補導致行為不一致 | ✅ **已緩解（2026-05-17）**：W1 預埋 guard（coordinator.py 71/126-130 行）+ W2-T2-16 補 tests/contract/test_max_active_runs_guard.py **12 case**（default=5 / env precedence / boundary parametrized 5 case / exception 診斷資訊 / enqueue caller pattern / abort 不影響其他 run）|
| **R-SD06-PM-#9** | embedding retry 5 次失敗後告警通道與 SLO 必須於 W3 設計時補齊 | 🟠 | PM 拍板 #9 + Architect 警示 | W3 task 加 SLO + 告警設計（不可延至 W6 監控階段）；embedding_status 三態 schema | ✅ **已緩解（2026-05-17 W3 G3 條件式）**：T3-21 EmbeddingWriter `alert_after_attempts` 預設 5 + SLOAlert dataclass + alert_observer 注入點；retry queue partial index `WHERE embedding_status != 'ok'`（0008 / 0009 三表全部建立）；T3-22 ReEmbedBatchJob 背景掃描 + 7 天 SLA |
| **R-SD06-PM-#11** | W0 PII schema 必須一次到位，後續發現遺漏觸發 migration | 🟠 | PM 拍板 #11 hybrid + Tech Lead 警示 | W0 review 拉法務/Security 共審；ENUM 包含 PII/secret/normal 三類；後擴留 RESERVED | ✅ **已緩解（2026-05-17）**：W0 ENUM + 2 RESERVED 後擴位 + 法務/Security PII minutes APPROVED_WITH_CONDITIONS（PII 5 / SECRET 3 / NORMAL 3 分類；遮罩演算法 C：hash + partial mask 混用；5 條件 W3 G3 對位）|
| **R-SD06-PM-#12** | Coordinator/AutoResume 雙層架構若無 ADR，6 個月內易退化為循環依賴 | 🟠 | PM 拍板 #12 + Architect 警示 | W1 task 加 ADR 撰寫（Layer 1.5 vs Layer 2 邊界明文）；2026-05-19 EOD 前完成 | ✅ **已緩解（2026-05-17）**：ADR-SD06-001 五方共審 APPROVED（Architect/SA/SD/PM ✅；QA ✅ APPROVED_WITH_CONDITIONS 3 條件 W1 對位）；§6 4 開放議題收斂（6 phase / BrainCapabilities / ExecutionEvent / send_interrupt 走 EventBus）|
| **R-SD06-PM-Budget** | +2 PD 吃掉 W6 緩衝 50%，FK dry-run 失敗回退恐爆預算 | 🟠 | PM Global 警示 | PM 預留 3 PD contingency（來源：v2 feature backlog 延後）；觸發條件：W3 dry-run 失敗 + 回退啟動 | 📋 W3 監控 |

---

## 13. SD_Improving_07 新增風險（R-SD07-0-1 ~ R-SD07-W4-3，三方+QA 四方審議 2026-05-18）

依 [SD_Improving_07.md](../04_planning/SD_Improving_07.md) v1.0 §7 風險登記表，三方審查共識 + ADR-SD07-001 LOC 政策三方共識決議 + PM 4 項拍板（2026-05-18）。

| ID | 描述 | 嚴重 | 對應議題 | 緩解措施 | 狀態 |
|----|------|------|---------|----------|------|
| **R-SD07-0-1** | Brain/Executor 缺 e2e 整合測試（SD_06 W1 G1 為單元測試覆蓋，5 種真實失敗情境往返未驗證）| 🟠 | #0 Minimax/Claude Code 分工 | W2 補 tests/integration/test_brain_executor_e2e.py ≥ 8 case（Token Halt / ESC+F12 / decide_correction / decide_escalation / send_interrupt 完整往返）| ✅ **CLOSED 2026-05-18 W2 G2**：test_brain_executor_e2e.py **10 case 全綠** |
| **R-SD07-0-2** | dry_run 模式 capabilities/on_event 未驗證 | 🟠 | #0 | W2 補 dry_run 模式整合測試 + capabilities 單次呼叫驗證 | ✅ **CLOSED 2026-05-18 W2 G2**：dry_run fixture 2 step × 5 phase 廣播 + capabilities 單次 cache + subprocess_invocations==0 紅線達標 |
| **R-SD07-1-1** | `steps_orchestrator/_impl.py` 736 LOC god-module 殘留（SD_06 W2 階段 4 部分完成 874→736，剩餘 state machine 需重設計）| 🔴 | #1 肥胖檔案 | W0 ADR-SD07-001 共識 → W1 抽 _escalation_handler.py（302 wc-l / 收斂+重試耗盡兩 escalation + GOAL_SYNTHESIS 共用 helper）+ _correction_helpers.py（185 wc-l / apply_step_mutations + validate_and_retry_correction）→ _impl.py 529 wc-l / 邏輯行 ≤ 500（service tier 達標）| ✅ **CLOSED 2026-05-18 W1 G1**（1,837 passed / 83 eq / LOC violations=0）|
| **R-SD07-1-2** | 250 LOC 一刀切過嚴反致 SSOT 漂移（SD_05 W3 checkpoint package 6 子模組已出現邊界漂移）| 🟠 | #1 | **ADR-SD07-001 三方共識決議**：取消 250 一刀切，改採分級制（資料 ≤ 150 / Plugin entry ≤ 250 / Strategy ≤ 300 / Adapter ≤ 400 / Service/Orchestrator ≤ 500 / Contract ≤ 400 / 絕對紅線 ≤ 750）| ✅ **已決議（2026-05-18 三方共識 + PM 形式核准）** |
| **R-SD07-1-3** | 250 LOC 對 orchestrator / adapter 過嚴 | 🟠 | #1 | 同 R-SD07-1-2；既有 14 違規檔 12 立即合規 + 3 個（_impl.py / pg_state / prompt_builder）W1 評估 | ✅ **已決議（2026-05-18）** |
| **R-SD07-2-1** | `runner-no-checkpoint-logic` contract 目前為 grep-based test，可繞過 | 🟠 | #2 Plugin 架構 | W5 升級至 importlinter 原生 forbidden contract（playbook_runner / 4 strategy modules ↛ checkpoint package 內部實作）| ✅ **CLOSED 2026-05-18 W5 G5**：`.importlinter` 新增 Rule 6 `runner-no-checkpoint-logic`（5 source × 6 forbidden internal modules + 9 條 ignore_imports 豁免 CheckpointPlugin 內部組成）；lint-imports **6 kept / 0 broken**；既有 grep-based test 保留為 anti-resurrection regression guard；補 `tests/contract/test_plugin_walk_through.py` 59 case（含 `test_runner_does_not_import_checkpoint_internals` 旁證）|
| **R-SD07-5-1** | LOC violations=1 持續存在（13847 > 12904；W3 累積尚未消化）| 🟠 | #6 設定檔（baseline）| W0 升級 tools/check_loc_budget.py 為分級判定 + 重新校準 baseline（吸收 W3 alembic 0007-0014 + adapter 永久增量）| ✅ **已緩解（2026-05-18，SD07-G0）**：baseline 10754→13847，cap=16616；分級制 violations=1（僅 _impl.py 682 > service 500，W1 處理）|
| **R-SD07-W4-1** | `_consecutive_compact_failures` 9 處 patch path 遷移（test_token_checkpoint.py / test_playbook_yaml_backward_compat.py）| 🔴 | SD_06 §5 延期項 | W4 第一步（強制順序）：(a) 9 處 patch 改 plugin SSOT；(b) grep 0 references；(c) 物理拔除 playbook_runner.py:141-170 property + setter | ✅ **CLOSED 2026-05-18 W4 G4**：實測 5 處 patch path（非預估 9 處）全部遷移至 `runner._token_guard_plugin._compact_failure_count` plugin SSOT；playbook_runner.py property + setter（35 行）物理刪除；`test_runner_property_delegates_to_plugin` backward compat 保護網 test 移除 |
| **R-SD07-W4-2** | `_prepend_global_goal_brief` 11 處 patch path 遷移（test_gap014_020.py / test_goal_synthesis_plugin.py）| 🔴 | SD_06 §5 延期項 | W4 第二步（強制順序）：(a) 11 處 patch 改 GoalSynthesisPlugin SSOT；(b) grep 0；(c) 物理拔除 playbook_runner.py:222-230 shim | ✅ **CLOSED 2026-05-18 W4 G4**：實測 4 處 test patch path + 1 處 _impl.py:184 內部使用全部遷移至 `runner._goal_synthesis_plugin.prepend_global_goal_brief()`；playbook_runner.py shim 方法 + import + docstring 全部物理刪除 |
| **R-SD07-W4-3** | PlaybookResult → KernelResult SSOT 完整切換 50+ assertion（SD_05/06 §1.3 PM 例外簽核延期項）| 🔴 | SD_06 §5 延期項 | W4 第三步（強制順序）：用 `to_kernel_result()` 自動轉換包裝；逐 10 處跑全測；QA Q-2 W4 開工前先 5 處 dry-run 模擬 | ✅ **CLOSED 2026-05-18 W4 G4**：採 **factory function + property alias** 路線（KernelResult 加 `halt_for_token` property alias / types.py PlaybookResult class 改為 thin factory 統一構造 KernelResult，內部處理 workflow Enum→str + halt_for_token→halted 映射 / _MutationResult.early_return: Optional[KernelResult]）；既有 17 處 source 構造 + 8 處 test 構造零改動（factory 簽名相容）；2 處 repr 客製格式測試升級為標準 dataclass repr；`to_kernel_result` helper 隨 class 一併物理刪除 |

### 13.1 PM 拍板決議連動風險（2026-05-18 SD_07 v1.0）

| ID | 描述 | 嚴重 | 來源 | 緩解措施 | 狀態 |
|----|------|------|------|----------|------|
| **R-SD07-PM-#1** | LOC 政策三方共識若不同步升級工具，CI guard 失守 | 🟠 | PM 形式核准 #1 + SD 警示 | W0 同步交付 tools/check_loc_budget.py 分級判定 + .loc-budget.toml + test_loc_budget_tiered.py（≥ 6 case）| ✅ **已緩解（2026-05-18，SD07-G0）**：工具升級 + override 機制 + 26 case contract test 全綠 |
| **R-SD07-PM-#2** | 真實 PG 整合測試啟用後 CI 時間延長 | 🟠 | PM 拍板 #2 + Architect 建議 | W2 CI matrix 加 PG service；對 PG 測試 opt-in via marker（autouse=False）；nightly 跑完整 e2e | 🟡 **部分緩解（2026-05-18 W2 G2 → 2026-05-19 zero-trust audit 重評）**：ci.yml `pg-e2e-nightly` job + marker `pg_real` 登記 + `SD07_REAL_PG_E2E_ENABLED` env gate 落地，**但 `tests/integration/test_pgvector_real_recall.py` 3 case test body 仍硬編碼 `pytest.skip()` → 真實 assert 至今阻塞**；移交 **SD_09 議題 C 觀察期 #2**（詳見 §15 R-SD09-CI-2 / R-SD09-CI-3 + SD09_Pre_W0_Audit_Findings.md）|
| **R-SD07-PM-#3** | W4 三項物理拔除一次切失敗將整個 W4 卡死 | 🔴 | PM 拍板 #3（W4 一次切）+ QA Q-2 警示 | W4 開工前先 5 處 assertion dry-run 模擬；強制順序紅線 ❌15；W4 PD 預留 6（含 1 PD 緩衝）；PM contingency 預留 2 PD | ✅ **CLOSED 2026-05-18 W4 G4**：QA Q-2 dry-run 5 處驗證 APPROVED 後一次切完成；強制順序紅線 ❌15 嚴格遵守（_consecutive_compact_failures → _prepend_global_goal_brief → PlaybookResult）；1,953 passed / 121 skipped（-1 vs G3 末為保護網 test 移除預期）；equivalence 83/83；factory function + property alias 路線避免 30+ 處 caller 大改 |
| **R-SD07-PM-#4** | SD_07 啟動日 2026-05-20 與 SD_06 W6 G6 (2026-05-18) 僅 1 自然日間隔，可能未充分穩定 | 🟢 | PM 拍板 #4 + 三方建議 | 沿用 SD_06 場景 A（個人開發 / dev）；W0 前 2026-05-19 EOD 由 Tech Lead 確認 SD_06 commit 穩定 + tag sd_06_w6_g6_pass；無 production smoke 需求 | ✅ **已緩解（2026-05-18）**：tag sd_06_w6_g6_pass 已存在；W0 提前完成（無需等 2026-05-20 啟動）|
| **R-SD07-Q-4** | token_guard 拆 5 子模組後 plugin coverage 下降（QA Q-4 強制 W3 開工前先量 baseline，W3 末驗證不下降）| 🟠 | QA Q-4 警示 | W3 開工前量測 baseline coverage（既有 `test_token_guard_plugin.py` 34 case → 全測 coverage 100%）；W3 末新增 `tests/plugins/token_guard/` 5 per-submodule 測試檔 + __init__（共 61 case）獨立覆蓋；強制 per-submodule coverage ≥ 90% | ✅ **CLOSED 2026-05-18 W3 G3**：per-submodule coverage **thresholds 100% / compactor 100% / git_verifier 100% / watcher 100% / policy 100% / __init__ 100% = TOTAL 162/162 stmts 100%**；既有 34 case + 新增 61 case 均維持綠 |

---

**文檔元數據**：
- 撰寫者：Phase 0~6 重構稽核（Pass 1）+ SD_Improving_03 三方審查（v1.1）+ 三方覆審（2026-05-12）+ SD_Delete_RunnerImpl Sprint 規劃（2026-05-12）+ SD_Delete_RunnerImpl G6 完成（2026-05-14）+ Phase 6 db_only §5 簽核後置項（2026-05-14）+ SD_Improving_05 W6 部分完成（2026-05-17）+ SD_Improving_06 三方+QA 四方審議（2026-05-17）+ SD_06 W6 G6 通過（2026-05-18）+ SD_Improving_07 三方+QA 四方審議 + ADR-SD07-001 LOC 政策共識決議 + PM 4 項拍板（2026-05-18）+ **SD_Improving_07 W6 G6 通過 + 四方審查 APPROVED + Migration Guide v1.0（2026-05-18）**
- 對應規格：SD_Improving_02.md v1.2 §3.1 / SD_Improving_03.md v1.1 §4.3 / SD_Delete_RunnerImpl.md §6 / SD_Improving_05.md §8 / SD_Improving_06.md v1.2 §8 / **SD_Improving_07.md v1.1 §7 + ADR-SD07-001 v1.0 + SD07_Migration_Guide.md v1.0**
- 最後更新：2026-05-18（**SD_Improving_07 W6 G6 收尾完成**；**所有 R-SD07-* 全部 CLOSED / 已緩解**：R-SD07-0-1 / R-SD07-0-2 / R-SD07-1-1 / R-SD07-1-2 / R-SD07-1-3 / R-SD07-2-1 / R-SD07-5-1 / R-SD07-W4-1 / R-SD07-W4-2 / R-SD07-W4-3 / R-SD07-Q-4 / R-SD07-PM-#1 / R-SD07-PM-#2 / R-SD07-PM-#3 / R-SD07-PM-#4 共 15 項；W6 無新增風險；G6 實測 **2,012 passed / 121 skipped** / equivalence **83/83** / importlinter **6 kept / 0 broken** / LOC violations=0；Migration Guide v1.0 落地；四方審查 4/4 APPROVED）
- 下次審查觸發：R-P6-04（正式 production 上線前四方重新審查）；**R-SD07-* 全系列 W6 G6 後已全數 CLOSED**
- 測試基線：1,802 passed / 118 skipped（SD_06 W6 G6 末，2026-05-18）；**SD_07 W6 G6 末實測 2,012 passed / 121 skipped**（+210 vs SD_06 G6 末，超預估 +55 門檻 +155）

---

## 14. SD_Improving_08 新增風險（R-SD08-A-1 ~ R-SD08-PM-#8，三方獨立研究 + QA 量測可行性 + PM 8 項拍板 2026-05-18）

依 [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 §5 風險登記表，三方獨立研究共識 + QA 量測可行性評估 + PM 8 項拍板（2026-05-18）。

| ID | 描述 | 嚴重 | 對應議題 | 緩解措施 | 狀態 |
|----|------|------|---------|----------|------|
| **R-SD08-A-1** | CLAUDE.md 歷史下沉後對話初始 context 缺失（新人 onboarding 找不到「為什麼這樣設計」脈絡）| 🟠 | E. 文件治理 | sprint_history.md 保留 SD_06+SD_07 完整摘要（滾動窗口 N=2）+ CLAUDE.md 頂端「快速導覽」3 行指引 + 交叉索引（sprint 編號 + 議題索引表 reverse-link）| ✅ **W0 CLOSED 2026-05-18**：sprint_history.md v1.0（399 行 §1.1~§1.3 完整下沉 SD_03~SD_05 + §2 議題索引表 16 條 reverse-link）+ CLAUDE.md「快速導覽」3 行就位 |
| **R-SD08-C-1** | AC4 nightly 連續 14 天仍 SKIP（pg-e2e-nightly 環境未啟用 / pgvector container 啟動失敗）| 🟠 | C. AC4 nightly | W2 開工前確認 `pg-e2e-nightly` 至少跑 1 次成功；nightly fail 連續 3 次黃線告警；漸進式升級避免一次性阻塞 | ✅ **W2 CLOSED 2026-05-18**：`tools/ac4_nightly_collector.py` + `tools/ac4_progress_check.py` 落地（CI step `continue-on-error=true` + 即使 nightly skip 仍累計 `.ac4_history.jsonl`）+ 黃線 3 次 / 紅線 5 次告警閾值就位（`tests/contract/test_ac4_progress_check.py` 6/6 PASSED）+ `pg-e2e-on-label.yml` workflow 待 14 天觀察期通過後手動啟用（避免 PR cycle time 拖累） |
| **R-SD08-D-1** | mutation score 首測 < 65%（coverage 100% ≠ mutation 100%，語意等價突變難殺）| 🔴 | D. mutation baseline | W3 pilot 單模組（TokenGuardPlugin）+ survived diff 補測；分模組差異化目標（75/70/65%）；W3 不設阻塞門檻（揭露門檻）；連續 7 次達標 -5% 才寫 `.mutation_baseline.toml` | ✅ **W3 工具就位 2026-05-18**（observing 觀察期啟動）：`tools/mutation_baseline_lock.py`（連續 7 次達標寫 baseline 取 min 最保守值）+ `tools/mutation_analysis.py`（survived 自動分類 boundary/constant/dead_branch/string_literal）+ `tests/contract/test_mutation_baseline_lock.py` 11/11 PASSED + `.mutation_baseline.toml` 初始空檔；fall-back（W3 末 < 60%）→ SD_09 接續，不阻塞 W4-W6 |
| **R-SD08-D-2** | mutmut nightly 單模組超 45 min 上限（每 mutation 跑 2,012 case，token_guard ~400-600 mutation × 100s = 11-17h）| 🔴 | D. mutation baseline | `--paths-to-mutate=autoclaude/plugins/token_guard --tests-dir=tests/plugins/token_guard --no-progress -p no:xdist` 縮限至 30-50 min/模組；AC `mutmut run wall time ≤ 40 min`；連續 5 次變異 ≤ ±3% | ✅ **W3 緩解就位 2026-05-18**：CI job 已套用 `--paths-to-mutate` + `--tests-dir` + `--no-progress` + `-p no:xdist` 四項縮限（ADR-SD08-002 §2.3）；GoalSynthesis / Coordinator 兩 step 暫停延 SD_09；timeout-minutes=45 維持；wall time 待 W3 兩週 nightly 實測驗證 |
| **R-SD08-E-1** | CLAUDE.md ≤ 400 行 CI 強制檢查未建立，6 個月後再次膨脹至 700+ 行（Snapshot 區段與真實程式碼漂移更危險）| 🟠 | E. 文件治理 | W0 同步交付 `claude-md-budget` CI job（`wc -l CLAUDE.md` ≤ 400）+ `tools/snapshot_sync.py` 自動回填 Snapshot 區段 + 7 天 freshness 告警 | ✅ **W0 CLOSED 2026-05-18**：`claude-md-budget` CI job 落地（wc -l ≤ 400 + Snapshot freshness 7 天告警 + snapshot_sync --check + check_loc_budget）+ `tools/snapshot_sync.py` 落地（AST 解析 wiring/ports/factory 自動同步）+ `tools/check_loc_budget.py` 加 `SPECIAL_FILES = {"CLAUDE.md": 400}`；CLAUDE.md 324 行；snapshot_sync --check OK |
| **R-SD08-F-1** | trace_id daemon thread 邊界斷鏈（`NonBlockingStreamReader` PTY daemon thread 不自動傳播 contextvars）| 🟠 | F. 可觀測性（議題 #0）| `copy_context().run()` 顯式包裝 + 單元測試覆蓋 PTY 邊界 + ADR-SD08-004 明文 daemon thread 規範 | ✅ **W4 CLOSED 2026-05-18**：`autoclaude/utils/trace_context.py` 落地 `run_in_thread_with_context` + `start_thread_with_context`（caller thread `copy_context()` 顯式拷貝；新 thread 內 `ctx.run()` 執行）；`autoclaude/perception/stream_reader.py` `NonBlockingStreamReader` 改造 daemon thread 改用 `copy_context().run()` 包裝；`tests/utils/test_trace_context_daemon_thread.py` 7 case 覆蓋（含 raw Thread 對照組驗證斷鏈動機 + start_thread_with_context PTY 不斷鏈 + 並發 isolation） |
| **R-SD08-F-2** | `IObservabilityPort` 放錯層（utils 而非 core/ports）退化為散裝技術債（6 個月後分散式部署時各 worker 各自實作）| 🔴 | F. 可觀測性 | ADR-SD08-004 明文 core/ports/ + importlinter Rule 7 禁 plugin 直接 import `utils.observability` + EventBus 為消費者而非實作者（單一職責原則） | ✅ **W4 CLOSED 2026-05-18**：`autoclaude/core/ports/observability.py` 落地（與 IBrain/IExecutor 同層級 Protocol）+ `autoclaude/infra/adapters/observability/local_logger.py` adapter；importlinter **Rule 7** 落地（`plugin-no-utils-observability-direct-import` forbidden，ignore_imports 豁免合法 aggregator / 框架層 lazy import）；7 kept / 0 broken；EventBus 為**消費者**（lazy import trace_context auto-inject `_trace_id`），非實作者 |
| **R-SD08-G-1** | perf baseline 在 GitHub Actions runner pgvector 場景變異 ±50%（IO 密集），誤報率壓垮開發流程 | 🔴 | G. 性能 baseline | pgvector p95 baseline 跑專用 perf machine（季度校準）；CI 僅跑 CPU-bound 場景（dry_run / TokenHalt / decide_correction）；p95 增量 < 15%（比 20% 收緊 5%）+ 中位數取代平均 | ✅ **W5 CLOSED 2026-05-18**：`tests/perf/test_pgvector_recall_perf.py` 採 `pytest.mark.pg_real` + `PG_REAL_ENABLED=1` 雙重門檻強制 CI runner SKIP（僅 perf machine 跑）+ `tools/perf_regression_check.py` 三級告警（< 10% pass / 10-15% warn / ≥ 15% block）p95 < 15% 收緊閾值 + `perf-baseline-nightly` job `continue-on-error: true` 不阻塞 main + `tests/contract/test_perf_regression_check.py` 4/4 PASSED；`.perf_baseline.toml` 首次鎖定 3 場景；`docs/06_quality/SD08_Perf_Baseline_Report.md` v1.0 明文 R-SD08-G-1 緩解策略 |
| **R-SD08-H-1** | SD_08 未鎖死 dual-state drift 觀測閾值，SD_09 將無客觀切換條件（極易因業務壓力提前切換造成資料不可逆汙染）| 🔴 | H. PG production SOP | W5 落地 WAL lag adapter（`autoclaude/infra/observability/pg_health.py`）+ drift_log 30 天零事件 SLA + ADR-SD08-005 草案明文 SD_09 啟用條件（可觀測性 GA + 30 天零 drift 雙條件） | ✅ **W5 CLOSED 2026-05-18**：`autoclaude/infra/observability/pg_health.py` 落地 — `PgHealthMonitor` Protocol + `DefaultPgHealthMonitor` asyncpg adapter + 三閾值 `classify_lag()`（< 2s NORMAL / 2-10s WARN emit_counter / ≥ 10s CRITICAL emit_counter + record_event 觸發降級至 yaml_only）+ 建構式注入 `IObservabilityPort`；`tests/infra/test_pg_health.py` 6/6 PASSED 覆蓋三閾值 + 邊界 + NullObservability fallback；`docs/08_deployment/Production_Migration_SOP.md` v0.1 §2 灰度啟動明文 drift_log SLA = 0 / 7 天 + dual_write_strict=fail_loud + WAL lag 三閾值對齊；ADR-SD08-005 §2.2 明文 SD_09 啟用雙條件（可觀測性 GA + 30 天零 drift）為不可逆轉折點 |

### 14.1 PM 拍板決議連動風險（2026-05-18 SD_08 v1.0）

| ID | 描述 | 嚴重 | 來源 | 緩解措施 | 狀態 |
|----|------|------|------|----------|------|
| **R-SD08-PM-#3** | mutation pilot 單模組策略若 W3 兩週仍未達 60% baseline，將推延 D 議題群至 SD_09 | 🟠 | PM 拍板 #3 + QA 警示 | W3 設定 fall-back：未達 60% 則 W3 末僅產出 `SD08_Mutation_Baseline_Report.md` 含 survived diff 分析 + 補測 backlog，不阻塞 W4-W6；SD_09 接續 pilot | 🟡 **W6 監控移交 SD_09**（2026-05-18）：observing 觀察期啟動 2026-05-19；首次評估鎖定 2026-05-25；W3 末判定 2026-06-01；fall-back 機制就位（不阻塞 W4-W6）；**移交 SD_09 §1 監控**（SD_Improving_09.md §1.3） |
| **R-SD08-PM-#4** | PG production SOP 延至 SD_09 後若 SD_08 W5 ADR-SD08-005 未落地，SD_09 啟動條件不明 | 🔴 | PM 拍板 #4 + Architect 警示 | W5 強制交付：(a) `pg_health.py` adapter + WAL lag SLA / (b) ADR-SD08-005 草案明文「可觀測性 GA + 30 天零 drift」雙條件 / (c) `Production_Migration_SOP.md` 草案 §1-§3 | ✅ **W5 CLOSED 2026-05-18**：三項齊備 — (a) `autoclaude/infra/observability/pg_health.py` 落地 WAL lag 三閾值告警 + IObservabilityPort 注入 + tests/infra/test_pg_health.py 6/6 PASSED；(b) ADR-SD08-005 狀態欄補「W5 G5 簽核紀錄 2026-05-18 落地：三項齊備」；§2.2 明文 SD_09 啟用不可逆轉折雙條件（可觀測性 GA + 30 天零 drift）；(c) `docs/08_deployment/Production_Migration_SOP.md` v0.1 §1–§3 落地 + tests/contract/test_pg_migration_sop_dry_run.py 2/2 PASSED 守護 |
| **R-SD08-PM-#5** | 可觀測性升級為 W3-W6 共同前置（議題 #0 trace_id / #3 PG WAL / #5 AutoResume），若 W4 延遲將連動 W5/W6 | 🔴 | PM 拍板 #5 + Architect 警示 | W4 切上半（IObservabilityPort + LocalLogger）+ 下半（trace_id contextvars + KB metric）兩階段；上半 W4 中段必須完成（給 W5 WAL lag adapter 有 port 可依）；含 PD contingency 預留 1.5 PD | ✅ **W4 CLOSED 2026-05-18**：P0 上半（IObservabilityPort + LocalLogger + Rule 7）與 P1 下半（trace_id contextvars + KB metric + AutoResume wake_kinds）皆於 W4 完成；無需 1.5 PD contingency；W5 WAL lag adapter pg_health.py 順利建構式注入 IObservabilityPort fallback NullObservability |
| **R-SD08-PM-#7** | 議題群優先順序 A→F→D→C→E→B→G→H 若執行時發現 F（可觀測性）需求超出 W4，將連帶壓縮 W5/W6 | 🟠 | PM 拍板 #7 + Tech Lead 警示 | W4 開工前 ADR-SD08-004 切「P0 必做」（Port 介面 + LocalLogger）vs「P1 增強」（trace_id contextvars 完整覆蓋 + KB metric）；P1 可彈性延 SD_09 | ✅ **W4 CLOSED 2026-05-18**：P0 + P1 均於 W4 G4 完成（2,079 passed +34 vs G3）；無延 SD_09；W5/W6 未受壓縮（W5 2,094 / W6 全程文件交付） |
| **R-SD08-PM-#8** | SD_08 啟動日 2026-05-21 與 SD_07 W6 G6 (2026-05-18) 僅 2 自然日穩定期 | 🟢 | PM 拍板 #8 + 三方建議 | 沿用 SD_07 場景 A（個人開發）；2026-05-20 EOD 由 Tech Lead 確認 SD_07 commit 穩定 + ADR-SD08-001~005 草案就位；無 production smoke 需求 | ✅ **W0 CLOSED 2026-05-18**：ADR-SD08-001~005 全部 APPROVED（場景 A dev 自核）+ G0 通過提前完成 |

---

**SD_08 元數據補增（2026-05-18 W6 G6 完成更新）**：
- 撰寫者：+ **SD_Improving_08 v1.0 — 三方獨立研究 + QA 量測可行性 + PM 8 項拍板（2026-05-18）**
- 對應規格：+ **SD_Improving_08.md v1.0 §5+§6** + **SD08_Migration_Guide.md v1.0 §5/§7**
- 最後更新：**2026-05-18 W6 G6 完成** — 14 項風險狀態總結：
  - **✅ CLOSED 11 項**：R-SD08-A-1（W0）/ R-SD08-C-1（W2）/ R-SD08-D-2（W3）/ R-SD08-E-1（W0）/ R-SD08-F-1（W4）/ R-SD08-F-2（W4）/ R-SD08-G-1（W5）/ R-SD08-H-1（W5）/ R-SD08-PM-#4（W5）/ R-SD08-PM-#5（W4）/ R-SD08-PM-#7（W4）/ R-SD08-PM-#8（W0）
  - **🟡 移交 SD_09 監控 2 項**：R-SD08-D-1（mutation pilot observing → SD_09 §1.3）/ R-SD08-PM-#3（pilot fall-back → SD_09 §1.3）
- 下次審查觸發：SD_09 啟動（待 mutation pilot + AC4 14 天觀察期 + drift_log 30 天評估後）+ R-P6-04（SD_09 觸發）
- 測試基線：SD_07 W6 G6 末 2,012 passed / 121 skipped → **SD_08 W5 G5 末 2,094 passed / 122 skipped（W6 純文件交付不增測試）**

---

## 15. SD_Improving_09 新增風險（R-SD09-A-1 ~ R-SD09-A-6，二輪四方審查 2026-05-19 + zero-trust audit 2026-05-19）

> **狀態**：v1.5 W0 G0 完成（5 輪 zero-trust audit）；R-SD09-A-1~A-6 + B-1/B-2/B-7/B-8 + CI-1/CI-2/CI-3 + M-4/M-5 + O-1 + Q-1 + G-1 + F-1/F-2 + D-1 共 19+ 條 W0 結帳；W1+ 補入 contract test 對應。對應 [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v1.0 §4 已知風險表 + v0.2 首輪 5 條 + v0.3 二輪四方審查 + **v0.4 zero-trust audit 新增 3 條（R-SD09-O-1 / R-SD09-A-5 / R-SD09-CI-3）** + **W0 第五輪 audit 新增 R-SD09-A-6 alembic merge revision**。詳見 [SD09_Pre_W0_Audit_Findings.md](SD09_Pre_W0_Audit_Findings.md)。

| ID | 描述 | 嚴重 | 對應議題 | 緩解措施 | 狀態 |
|----|------|------|---------|---------|------|
| **R-SD09-A-1** | 真實 staging（≥ 1M 列）跑 失敗或 drift_log > 0 | 🔴 | A. PG production | W3 前 dry-run 演練（AI-Agent 模擬）+ 人類 DBA 親演前置 | 🟡 W0 監控（未啟動）|
| **R-SD09-A-2** | 人類 DBA 親簽延期超過 SD_09 範圍 | 🟠 | A. PG production | W4 中段必須完成 DBA 親演 → 不阻塞 W5 上線；fall-back：DBA 親演失敗 → W5 推遲至 SD_10 | 🟡 W0 監控（未啟動）|
| **R-SD09-A-3** | W3 AI-Agent dry-run 失敗（≥ 1M 列模擬失敗）| 🔴 | A. PG production | fall-back：`git checkout sd_09_w2_g2_pass` 新建 hotfix 分支修補 schema/index（QA-M6 修復） | 🟡 W0 監控（未啟動）|
| **R-SD09-A-4** | W5 雙條件未達（可觀測性 GA OR drift_log 任一未達）| 🔴 | A. PG production | fall-back：不切換 db_only 維持 both mode；W5 G5 改判 conditional pass；切換動作延 SD_10；ADR-SD09-001 §2.4 例外條款 | 🟡 W0 監控（未啟動）|
| **R-SD09-B-1** | GoalSynthesis / Coordinator 首測 mutation < 60% baseline | 🟠 | B. mutation 擴展 | 同 SD_08 fall-back（產出 Report + 補測 backlog）；W2 Coordinator 不受阻 | 🟡 W0 監控（未啟動）|
| **R-SD09-B-2** | mutation 並行 nightly 超時（GS + Coord 同時跑 > 45 min）| 🔴 | B. mutation 擴展 | ADR-SD09-002 §2.3 拆 3 個獨立 cron job + TG 退出 nightly；§2.6 nightly failure / timeout 處理（QA-M5 修復）；單 nightly job 僅 1 module step | 🟡 W0 監控（未啟動）|
| **R-SD09-D-1** | perf machine 採購延期超 W4 上線時程 | 🔴 | D. perf machine | W2 上半確定預算 + 採購方案；緊急路徑：採購未簽核 → 議題群整體延 SD_10，W4 G4 不阻塞 | 🟡 W0 監控（未啟動）|
| **R-SD09-F-1** | trace_id multi-process 方案選 (b) 自建 TraceContext 超出 W3 估算 | 🟠 | F. trace_id | W0 三方研究 + PM 拍板選 (a) 或延 SD_10 | 🟡 W0 監控（未啟動）|
| **R-SD09-F-2** | multi-process trace_id 30 天觀察視窗無法在 W5 達成 | 🔴 | F. trace_id | ADR-SD09-001 §2 明訂 W5 = 同 process trace_id GA 即可（multi-process GA 延 W6 / SD_10）| 🟡 W0 監控（未啟動）|
| **R-SD09-G-1** | KB metric 落地 PG 後跨 storage.mode 三後端切換時 PG metric 表孤兒 | 🟠 | G. KB metric | ADR 補設計「IKbMetricStore port + Local/Pg adapter 雙軌」確保 yaml_only 模式仍可運作；SD_09.md §1.7 補方法簽名草案（SD-C4 修復）| 🟡 W0 監控（未啟動）|
| **R-SD09-CI-1** | 個人開發場景 GitHub Actions 額度受限 → 本地排程替代；且 mutmut 3.x 不支援 Windows 原生（issue #397）導致觀察期 #1 無法在本機每日累積 | 🟠 → 🟢 **部分緩解 2026-05-19** | CI / 觀察期採集 | (a) 三觀察期改 `tools/run_local_nightly.ps1` + Windows Task Scheduler 每日 02:00 採集；(b) **觀察期 #1 mutmut 改透過 Docker `python:3.11-slim` 跑（ADR-SD09-002 §2.7 修訂）**，維持「連續 7 次 ≥ 70%」原始定義；(c) 既有 `autoclaude_pg` container 沿用，腳本不破壞既有 staging | 🟡 W0 監控（2026-05-19 起，每日 nightly 腳本 log）|
| **R-SD09-CI-2** | SD_07 PM #2 真實 PG e2e 「結構保留」缺口 — `tests/integration/test_pgvector_real_recall.py` 3 case 硬編碼 `pytest.skip()`；`tools/seed_kb.py` + 100 query embedding fixture + ground truth 從未實作；`ac4_progress_check.py:84` 把 `status != 'pass'` 一律視同失敗 → **觀察期 #2 在 CI / 本地皆無法達標**（永遠 `consecutive_failures` 累積、`ready_for_labeled_pr=false`）| 🔴 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix）| 議題 C / 觀察期 #2 | **X1 拍板落地** — `tools/seed_kb.py` mock 模式完整 + `tests/fixtures/pgvector_real_queries.json` + `pgvector_real_ground_truth.json` 已 commit；`test_pgvector_real_recall.py` 3 case 硬編碼 skip 已移除改 fixture-side conditional；`ac4_progress_check.py:84` 三態 sentinel（pass/fail/skip→None）已落地 | 🟢 CLOSED（X1 路徑落地完成）|
| **R-SD09-O-1** | `tools/observability_ga_check.py` 不存在，但 [ADR-SD09-001](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) §2.5/§2.6 + [SD09_Execution_Guide.md](SD09_Execution_Guide.md) T0-O1 列為 W5 db_only 切換硬性條件唯一取證工具（W5 雙條件 (1a)/(1b) 量化判定依賴） | 🔴 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix）| A. PG production / 議題 F 可觀測性 | `tools/observability_ga_check.py` 182 LOC 完整實作（_load_history / _is_green / _compute_green_streak / main 含 --window 30 --json exit 0/1）；30 天連續綠判定真實可運作；待 W5 .observability_history.jsonl 累積至 30 筆後執行取證 | 🟢 CLOSED（工具完整實作；待 W5 取證執行）|
| **R-SD09-A-5** | `alembic_version=0012_yaml_import_staging`，但 `0013_drift_log` + `0014_config_audit_log` migration 已落地未跑 → 觀察期 #3 取證 SQL（依賴 `drift_log.detected_at`/`severity` 欄位）恆失敗 → 30 天零事件條件永遠 false → R-SD09-A-4 雙條件 (2) 阻塞 | 🔴 → 🟡 **部分緩解 2026-05-20**（zero-trust audit fix）→ 🔴 **風險已實際發生 2026-08-03 複核確認** → 🟢 **根因已消除 2026-08-03**（唯讀實查 alembic 已在鏈頭；殘留僅為 streak 自然回補） | A. PG production / 議題 A | (a) `.alembic_offline_head.txt` 標記檔已落地（⚠️ **內容已 stale**：現為 `0015_merge_sd06_optional_gin`，真實鏈頭已是 `0018_version_kind_discriminator`；該檔**無任何程式消費者**，僅文件引用，故不致命——但引用時勿當真相源）；(b) `tests/contract/fixtures/drift_log_30day_zero.json`（30 筆 severity=info 場景 A fall-back fixture）已備；(c) `alembic/__init__.py` shadow 已刪除；(d) **PG 真實 `alembic upgrade head` — 已自「W0 G0 預檢」前移為獨立前置動作 P-0**（不需 G0 授權、不吃 W0 資源；死鎖解除見 R-SD09-A-5-LOOP） | 🟢 **根因已消除（2026-08-03T02:57Z 唯讀實查）**，歷史風險確曾發生。<br>**唯讀取證**：`docker exec autoclaude_pg psql -U autoclaude -d autoclaude -tAc "SELECT version_num FROM alembic_version;"` → **`0018_version_kind_discriminator`**；`SELECT to_regclass('public.drift_log')` → **`drift_log`（表存在）**；`SELECT count(*) … FROM drift_log` → **total=0 / non_info=0**。比對 `alembic/versions/` 鏈頭亦為 `0018_version_kind_discriminator` ⇒ **head 未落後，本風險的觸發條件已不存在**。<br>**歷史實現**：`.drift_log_history.jsonl` 第 9 筆（2026-06-02）`drift_log_table_exists: false` / `passed: false` 即本風險實現，依 `_compute_green_streak` 打斷 streak，是觀察期 #3 未達標的**唯一原因**（其餘各筆全綠、`severity_non_info_count` 全 0）。<br>**殘留**：僅需 streak 自然回補 —— 現值 `green_streak=26/30`，**再累積 4 筆綠紀錄即達標**（每 UTC 日上限 1 筆 ⇒ 最快 4 個採集日）。**無需任何人工介入。** |
| **R-SD09-A-5-LOOP** (**2026-08-03 新增／同日處置**) | **R-SD09-A-5 的緩解措施 (d) 自身是死鎖**：觀察期 #3 達標 ← drift_log 表存在 ← `alembic upgrade head` ← (d) 明載「**待 W0 G0 預檢**執行」 ← W0 G0 啟動需 #3 達標。⇒ 要達標才能修、要修才能達標 | 🔴 → 🟢 **已解 2026-08-03** | A. PG production / 觀察期 #3 | **【已落實】把 `alembic upgrade head` 從「W0 G0 預檢」前移為與 G0 無關的獨立前置動作 `P-0`**——它不需要 G0 授權、不消耗 W0 資源、不改任何應用程式碼，掛在 G0 底下純屬**順手歸類而非必要相依**。判別準則：**「該動作若提前做，會不會讓 G0 的判定失真？」否 ⇒ 它就不該掛在 G0 底下。** 同型（閘門擺錯位置）處置先例＝[ADR-SD09-013](../04_planning/ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md)（觀察期 #1 unique sha 入場→出場移位）。文件落點：[SD09_Execution_Guide.md §0.1-P0](SD09_Execution_Guide.md) + [SD_Improving_09.md §8.3 D-2](../04_planning/SD_Improving_09.md) | 🟢 **CLOSED（治理層＋事實層雙重解除）**<br>**治理層**：`alembic upgrade head` 已移出 G0 前置，循環斷開。<br>**事實層**：2026-08-03T02:57Z 唯讀實查 `alembic_version = 0018_version_kind_discriminator` = 鏈頭、`drift_log` 表存在 ⇒ **該動作在本機實際上已完成，P-0 對現況為 no-op**。<br>⚠️ **治理修復仍必要**：全新環境／fresh clone 仍會重踩同一循環，故文字修正不因「本機碰巧已好」而省略。|
| **R-SD09-GATE-NOCARRIER** (**2026-08-03 新增**) | **判準與 deadline 沒有偵測者**（同族「條件永遠不會被發現滿足／未滿足」）：(a) `tools/drift_log_ga_check.py`（觀察期 #3 唯一權威判準）**零 production caller**（全 repo grep 僅命中自身與 `tests/tools/test_drift_log_ga_check.py`）；(b) 舊載體 `tools/g0_gate_check.ps1:41/63` 標籤寫 `#3 observability/drift` 但實際只查 `observability_ga_check`（obs GA 軌，**不同軌**）；(c) 新載體 nightly 收尾 G0 三軌判定＝mutation/ac4/**obs_ga**，不含 drift；(d) nightly 進度行印 `drift=34/30`（**原始列數**，看似達標實則 25/30）與 `mutation=5/7`（比權威 `should_lock` 嚴，看似未達標實則已鎖 baseline）— **同一行兩個方向的取證失真**；(e) §6 PM #6(b)「最遲 2026-06-26」逾期 **38 天**無任何載體察覺 | 🔴 → 🟡 **部分緩解 2026-08-03** | 全軌治理 / 紀律 #4 | (1) ✅ 把 `drift_log_ga_check.py` 接進 nightly 收尾 G0 判定；(2) ✅ 進度行改印**權威判準值**（`green_streak`、`should_lock` 結果）而非原始列數；(3) ✅ `$G0_MUTATION_UNIQUE_SHA_TARGET` 對齊 `should_lock`（[ADR-SD09-013](../04_planning/ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) §3.3 L-3）；(4) ⬜ 為啟動 deadline 補逾期告警。**(1)~(3) 皆位於 `tools/run_local_nightly.ps1`，已於 R71 G-1/G-3 落地** | 🟡 **部分緩解（2026-08-03 對 `run_local_nightly.ps1` 實查，mtime `11:37`、1,611 行）**<br>✅ **(a)(c)(d) 已解**：新增 `Get-DriftGaPass`（`--json` + rc↔status 一致性檢查）與 `Get-MutationLockGate`（`-c` 探測碼直呼 `should_lock`）；G0 判定由三軌擴為**四軌** `$g0MutOk -and $g0Ac4Ok -and $g0ObsOk -and $g0DriftOk`；`END observation progress:` 四軌分子**一律取權威判準值**，原始列數改以 `records=` 併印且明文「絕不當分子」；`$G0_MUTATION_UNIQUE_SHA_TARGET` 常數**已自該檔刪除**（全檔 grep 零命中）。<br>🔴 **殘留 (b)**：舊載體 `tools/g0_gate_check.ps1:41/63` 標籤仍寫 `#3 observability/drift` 而實際只查 obs GA（本輪實查確認未動）——**已非唯一管道，危害降級**；建議改標籤或標記 superseded。<br>🔴 **殘留 (e)**：**deadline 逾期本身仍無偵測者**，規格已交付（[SD_Improving_09.md §8.3 D-4](../04_planning/SD_Improving_09.md)：掛進 nightly 收尾、WARN 不進 rc、三 case 測試鎖 + 雙向注入驗證），**實作未落地**。<br>⇒ **本風險降級為 🟡 而非關閉：判準面的偵測者已補齊，deadline 面尚未。**<br>人工複查管道仍保留於 [SD09_Execution_Guide.md §0.3](SD09_Execution_Guide.md)：三軌一律呼叫權威工具 |
| **R-SD09-CI-3** | CI nightly 4 個 job 全 `continue-on-error: true`（mutation-pilot / ac4-nightly / pg-e2e-nightly / perf-baseline-nightly）共 11 次掩護失敗 6+ 個月；R-SD08-D-1 / R-SD08-PM-#3 監控空跑 = 虛假狀態（管線根本沒有真實成功訊號可累積） | 🔴 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix Z1 落地）| C. AC4 nightly + D. mutation + G. perf | **PM 拍板 Z1 落地** — `.github/workflows/ci.yml` 11 處 `continue-on-error: true` 全數移除（4 job-level + 7 step-level）；mutmut step 3 處 `\|\| true` 保留（工具特性，已加 mutation log guard B-03）；先解 X1（fixture 齊備）+ Y1（缺檔補齊）+ B-01/B-07/B-08 後執行 | 🟢 CLOSED（Z1 落地；nightly 真實 gate 化）|
| **R-SD09-M-5** | 觀察期累計工具同日重複跑可累加偽造 14 天綠 / 連續 7 次達標假象（`tools/ac4_nightly_collector.py` + `mutation_baseline_lock.py` 純 `open("a")` 無 UTC date 去重）| 🟠 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix）| C. AC4 nightly + D. mutation | 兩工具 `append_history()` 加 UTC date 去重（同 module + 同日已存在則覆寫該筆，保留最後一次結果）；對齊 nightly retry 語意，避免單日多 runs 累加假象 | 🟢 CLOSED |
| **R-SD09-M-4** | trace_context.py `propagate_to_subprocess_env()` helper 已落地但 9 處 subprocess 注入點 0 個 caller 使用 → trace_id 跨進程斷鏈 → multi-process 觀察期 vacuous | 🟠 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix Y1 落地）| F. trace_id multi-process | 9 處 subprocess（pty_wrapper / cross_step_validator / pre_run_validator / evaluator / mutation_applier/_conditional / fast_path_plugin / token_guard/git_verifier / prompt_builder / services/mutation/_conditional_evaluator）全數呼叫 `env=propagate_to_subprocess_env(...)` | 🟢 CLOSED |
| **R-SD09-B-7** | tests/perf/ 4 case 玩具負載（range(2000) 加總 / "x"*4096 切半 / pass placeholder）p95 = 0.006~1.7ms 級，ADR-SD08-003「p95 < 15%」閾值在此量級下=雜訊放大器 | 🟠 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix）| G. perf 雙軌 | 4 case 重做：test_dry_run_e2e 改 5-step mock playbook / test_decide_correction 改 100x mock decide / test_token_halt_roundtrip 改 1000x token 估算 / test_pgvector_recall_perf 改 100q × adapter.search；維持 @pytest.mark.perf marker 與 7-runs warm-up | 🟢 CLOSED |
| **R-SD09-B-8** | `autoclaude/utils/perf_baseline.py` `write_perf_results()` helper 已落地但 CI step 0 caller 呼叫 → perf_results.json 永遠不存在 → regression check 永遠走 echo warning 分支 | 🟠 → 🟢 **CLOSED 2026-05-20**（zero-trust audit fix）| G. perf 雙軌 | `ci.yml` perf-baseline-nightly job 加 `write_perf_results()` caller step / `tests/perf/conftest.py` 加 `pytest_sessionfinish` hook 自動寫 `perf_results.json` | 🟢 CLOSED |
| **R-SD09-F1-OBS** | `tools/observability_snapshot.py` `_emit_heartbeat_and_count()` LocalLogger import 失敗 fallback 路徑回 `count=1`，與真實 emit 1 次無法區分 → ga_check 無法拒絕「mock 假象綠標」 → W5 雙條件 (1a) 30 天觀察期可能被假 PASS 污染 | 🔴 → 🟢 **CLOSED 2026-05-24**（SD_09 W3 nightly zero-trust audit F1 修復）| A. PG production / 議題 F 可觀測性 | 改 tuple return `(count, emit_real: bool)`；jsonl 寫 `observability_emit_real` 欄位；`observability_ga_check._is_green()` 拒絕 `emit_real=False`（舊紀錄缺欄寬鬆通過避免打斷累計）；補 `tests/tools/test_observability_ga_check.py` 14 case + observability_snapshot.py 補 2 case（fake-PASS 拒絕場景） | 🟢 CLOSED（紀律 #10 CLAUDE.md 新增；ga_check 與 snapshot 兩端 schema 對齊）|
| **R-SD09-F2-AC4** | `tools/ac4_progress_check.py` 回 `ready_for_labeled_pr=true` 後 nightly 腳本無主動告警 → PM approval ceremony 為純手動程序 → 議題 C 升級時機可能延誤 | 🟠 → 🟢 **CLOSED 2026-05-24**（SD_09 W3 nightly zero-trust audit F2 修復）| C. AC4 升級 | `tools/run_local_nightly.ps1` pg-e2e stage 末段加 ac4 readiness 解析：true → WARN 提示需 PM 確認啟用 `pg-e2e-on-label.yml` 並紀錄至 `docs/06_quality/SD09_AC4_Activation_Approval.md`；false → INFO 印目前 reasons | 🟢 CLOSED（nightly log 留下 RunId 取證軌跡）|
| **R-SD09-W3-TM** | `tests/tools/test_observability_ga_check.py` 與 `tests/tools/test_perf_regression_check.py` 兩個測試鏡子不存在 → 升級判定工具違反紀律 #4「驗證鏡子自身要被驗證」| 🟠 → 🟢 **CLOSED 2026-05-24**（SD_09 W3 W1 backlog P1-TEST-MIRROR-1 提前落地）| 紀律 #4 | 補 `test_observability_ga_check.py` 14 case（含 emit_real=False / kb_keys 缺漏 / streak 邊界 / fake-PASS 拒絕）+ `test_perf_regression_check.py` 18 case（含 classify 三級 / load_results 三格式 / undersampled BLOCK→WARN 退化 / PR comment 範本）| 🟢 CLOSED（共 +32 case + emit_real 2 case = +34）|

### 15.1 SD_08 移交監控風險（接續 §14）

| ID | 移交說明 | 狀態 |
|----|---------|------|
| **R-SD08-D-1** | mutation pilot TokenGuardPlugin observing → SD_09 §1.2 議題 B 接續 | 🟢 **CLOSED 2026-07-22（2026-08-03 複核確認）**：`.mutation_baseline.toml` `token_guard = 0.7071` 已鎖定，取證 `logs/nightly_2026-07-22_183551.log:261` `::notice::token_guard baseline locked at 70.71%`（`logs/nightly_2026-08-01_101807.log:375` 同）；`should_lock(history,'token_guard')` 複跑 → `(True, 0.7071428571428572)`。Docker `python:3.11-slim` 流程已穩定運作，`.mutation_history.jsonl` 7 筆（5 unique sha + 2 筆 legacy）。<br>〔歷史〕2026-05-20 W0 G0 audit 當時：mutmut 3.x 不支援 Windows 原生（issue #397），`.mutation_history.jsonl` 尚不存在，標「監控管線未就緒」 |
| **R-SD08-PM-#3** | mutation pilot 單模組 fall-back（< 60%）→ SD_09 §1.2 議題 B 接續 | 🟢 **未觸發（2026-08-03 複核）**：tail 7 kill_rate 全 ≥ 0.68 effective threshold（最小 0.7071），遠高於 < 60% 的 fall-back 門檻 → 無需走單模組 fall-back。**惟 fall-back 條款仍為 W1 出場 X-1 未達時的處置依據**（[ADR-SD09-013](../04_planning/ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) §5.1 情境 (b)：W1 若不觸碰 token_guard，X-1/X-2 移交 SD_10） |

---

| **R-SD09-Q-1** | tests/equivalence/fixtures/09_conditional.yaml + 10_full_e2e_dry_run.yaml 中 `evaluator_command: "echo X"` 在 Windows 開發環境 FileNotFoundError（echo 為 cmd 內建非獨立 .exe）→ kernel_facade 2 case FAILED；CI ubuntu-latest 不會暴露此問題 → 跨平台 fixture 健康度落差 | 🟠 → 🟢 **CLOSED 2026-05-20**（v1.4 zero-trust audit fix）| QA fixture 跨平台 | 兩 fixture 改用 `python -c "print('X')"` 跨平台命令；kernel_facade 19/19 PASSED；建議 W0 task breakdown 補入 AC-SD09-17 evaluator_command portability contract test 防回歸 | 🟢 CLOSED |
| **R-SD09-A-6** | alembic `get_heads()` 回傳 `[0003_jsonb_gin_index, 0014_config_audit_log]` 雙 head — 0003 為 SD_06 可選 JSONB GIN 分支（depends_on=None；docstring「目前非必要」），主線走 0001→0002→0004→…→0014；offline marker 不致命但 W2 PG `alembic upgrade head` 將 ambiguous fail | 🟠 → 🟢 **CLOSED 2026-05-20**（W0 G0 五方 audit fix）| A. PG production / 議題 G | **手動建立 merge revision `alembic/versions/0015_merge_sd06_optional_gin.py`**（`down_revision=("0003_jsonb_gin_index","0014_config_audit_log")`；無 schema 異動）；`.alembic_offline_head.txt` 更新為 0015_merge_sd06_optional_gin；alembic `get_heads()` 實測回傳單一 head；SD_09 W2 議題 G `0016_kb_metrics` 將直接接續 0015；建議 W3 議題 F CI 加 `alembic check` 步驟防再次分叉（移交 SD_10）| 🟢 CLOSED（單一 head；W2 議題 G 0016_kb_metrics 可直接 upgrade head）|

**SD_09 §15 元數據**：
- 撰寫者：SD_Improving_09 v0.3 二輪四方審查（2026-05-19）+ **v0.4 zero-trust audit 修復（2026-05-19）** + **v1.4 第四輪 zero-trust audit 補修（2026-05-20）**
- 對應規格：SD_Improving_09.md v0.5 §4 + 附錄 A 修復對照表 + [SD09_Pre_W0_Audit_Findings.md](SD09_Pre_W0_Audit_Findings.md) v1.5
- 最後更新：**2026-08-03**（觀察期三軌 zero-trust 複核 → 同日 D-2 死鎖處置）— 新增 **R-SD09-A-5-LOOP**（A-5 緩解措施自身死鎖，已實際發生）+ **R-SD09-GATE-NOCARRIER**（判準／deadline 無偵測者）；R-SD09-A-5 重評 🟡→🔴（風險已發生）**→🟢 根因已消除**（唯讀實查 `alembic_version=0018_version_kind_discriminator`＝鏈頭、`drift_log` 表存在；殘留僅 streak 回補 4 筆）；**R-SD09-A-5-LOOP 🔴→🟢 CLOSED**（`alembic upgrade head` 移出 G0 前置改為獨立 P-0）；R-SD08-D-1 🟡→🟢 CLOSED（baseline 2026-07-22 鎖定）；R-SD08-PM-#3 🟡→🟢 未觸發。對應 [ADR-SD09-013](../04_planning/ADR/ADR-SD09-013-w1-entry-gate-unique-sha-relocation.md) + [ADR-SD09-012](../04_planning/ADR/ADR-SD09-012-ac4-observation-decouple-calendar.md) + [SD_Improving_09.md §8.3 同型死鎖盤點](../04_planning/SD_Improving_09.md)
- **⚠️ 引用注意**：`.alembic_offline_head.txt` 內容為 `0015_merge_sd06_optional_gin`，**已落後真實鏈頭 3 版**（真值 `0018_version_kind_discriminator`）。該檔**無程式消費者**（全 repo grep 僅命中文件），故不阻塞任何流程，但**不可當作 head 的真相源**；真相源＝`alembic/versions/` 鏈結構與 DB `alembic_version`。
  〔前次〕2026-05-20（v1.5 第五輪 W0 G0 zero-trust audit 同步；新增 R-SD09-A-6 alembic multi-head merge revision 待 W2 處置；同步五方審查 W0 G0 FULLY APPROVED-WITH-CONDITIONS）
- **2026-08-03 收尾補記**：`R-SD09-GATE-NOCARRIER` 🔴 → **🟡 部分緩解** —— R71 G-1/G-3 已把 mutation／obs／drift 三軌的 nightly 判定改為「向權威工具現場提問」（`Get-MutationLockGate` → `should_lock`、`Get-DriftGaPass`／`Get-ObsGaPass` → `--json`），G0 由三軌擴為四軌，`$G0_MUTATION_UNIQUE_SHA_TARGET` 已刪除。**殘留＝(b) 舊載體 `g0_gate_check.ps1` 標籤錯置、(e) deadline 逾期無偵測者（D-4 規格已交付、實作未落地）。**
- 下次審查觸發：SD_09 W0 啟動（原訂**最早 2026-06-18~22 / 最遲 2026-06-26 — 已逾期 38 天**；剩餘無爭議阻塞項＝觀察期 **#2 AC4 8/14**）+ 每 Wave 末複查
- 測試基線：SD_08 W6 G6 末 2,094 passed / 122 skipped → **SD_09 W0 補測落地後實測 2,403 passed / 122 skipped（超 SD_08 W6 基線 +309）；預估 W6 末 ≥ 2,420（軟目標）/ ≥ 2,410（硬底線）**
