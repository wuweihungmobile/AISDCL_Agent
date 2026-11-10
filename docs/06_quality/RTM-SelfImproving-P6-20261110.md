# RTM - SelfImproving P6 研究來源單一化與歷史缺陷反事實回測（根層半：登記鏡像入帳、安全抓取與文章展開、回測）

**版本**: 1.1（2026-11-10 夜：真機 V-P6-1／V-P6-2 回填、勘誤 E-8／E-9 新增 AT 四列；1.0＝SCG-4 二審 PASS 後回填；表格形沿用 `docs/06_quality/RTM-SelfImproving-P4-20261109.md`；Console 半見 `AgentConsole/docs/06_quality/RTM-ResearchRegistry-20261110.md`）
**日期**: 2026-11-10
**狀態**: 根層半實作與自動測試完成。實作 commit `914e0adc`（研究來源登記與抓取，RR）、`0bea20e4`（回測 BT 與範圍守衛）、`11067dd1`（重釘）；SCG-4 修正 `12c93c65`（QA4R-01、QA4R-02）、`8bf9b648`（重釘二十三列）、`0f65773a`（非 UTF-8 XML 拒收 AT 改編號 AT-630-8-E-3）；勘誤 `0638fdd5`（TCS-P6 勘誤 E-1～E-7）。SCG-4 獨立審查報告 `docs/06_quality/SCG4-REVIEW-SelfImproving-P6-20261110.md`：一審 FAIL（P2 2、P3 1、P4 1）→ 修復 → 聚焦二審 PASS。根層全套 `tools/run_root_unittests.py` rc=0（發現 6295 個測試、下限 6207）；`0f65773a` 之後再改名一條，netfetch 單檔 27 條、c1c2 單檔 187 條皆綠。**真機項 V-P6-1（登記、入帳、實抓）與 V-P6-2（K=5 回測）尚未執行，一律標「真機待驗」，不得視為已驗。**（1.0 原文保留）**1.1 更新**：OBS-SI-383／384（回測洩漏稽核對齊真實 harness 逐字稿）修正 `924e0975`、`e298f324`、`89766d18`，勘誤 `3371129b`、`d6ba3e36`、`61d53f84`（PRD v0.15.1、TCS E-8／E-9），QA 聚焦複核 FAIL→修→PASS；V-P6-1 與 V-P6-2 已真機驗（見文末表），唯 AT-645-4-1 的巡邏自動入帳路徑仍待真機觸發。
**覆蓋率**: AT 100／100 有對應（測試函式以 AT 底線形於 `tools/tests/test_selfimproving_{registry,netfetch,backtest}.py` 現查；其中 NF 檔另有兩個規格外輔助測試 `AT_630_3_E_5`、`AT_630_3_E_6`，不計入 100）；AC 29 個（FR-SI-30 的 9 條、FR-SI-45 的 8 條、FR-SI-46 的 8 條、自增 4 條）。找不到測試函式的 AT：無。
**規格**: `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md`（鍵 `monorepo-si-p6-registry-backtest`，含勘誤 E-1～E-9；AT 共 100，正控 58、負控 42）；上游 `docs/01_requirements/SelfImproving_PRD.md` v0.15.1。
**FSM**: 本檔回填時 RELEASE 尚未執行；狀態以本檔 E2E 欄與 SCG-4 報告為準。（1.0 原文保留）**1.1**：2026-11-10 雲端 CI（`c3f43217` root-infra／macos-compat／windows-compat）全綠後 `gate RELEASE_READY PASS` ⇒ 鍵 `monorepo-si-p6-registry-backtest` 為 RELEASE（OBS-SI-372 規則：本鍵真機項 V-P6-1／V-P6-2 皆已驗）。

**表格約定**: 實作檔一律在 `tools/lib/selfimproving/` 之下，只寫檔名；測試檔一律在 `tools/tests/` 之下，`RG`＝`test_selfimproving_registry.py`、`NF`＝`test_selfimproving_netfetch.py`、`BT`＝`test_selfimproving_backtest.py`，欄內寫 `檔::函式`（函式全名現查）。

| ID | 來源 | 摘要 | 層 | Phase | 實作檔 | 自動測試 | E2E 驗證 | 狀態 |
|----|------|------|----|-------|--------|----------|----------|------|
| `AT-630-2-1` | `AC-SI-30-2` | 預檢讀鏡像、`research.scan` 綁 `registry_seq` 與 sha、無 `sources_sha256` | 根層 | P6 | `research.py`、`registry.py`、`evspec6.py` | `RG::test_AT_630_2_1_scan_binds_registry_event` | 真機 V-P6-1 ✅：seq 88～91（RUN-SI-008；`4ad444a1`、`1e9d8a8d`） | ✅ 實作+測試+真機 |
| `AT-630-2-E-1` | `AC-SI-30-2` | 預檢各拒收碼逐項、被拒時連線次數 0 | 根層 | P6 | `research.py`、`registry.py` | `RG::test_AT_630_2_E_1_precheck_rejections_send_no_request` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-2-E-2` | `AC-SI-30-2` | 鏡像未 commit 照樣通過、舊表不再被讀 | 根層 | P6 | `research.py` | `RG::test_AT_630_2_E_2_uncommitted_mirror_is_fine_and_old_table_not_read` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-2-E-3` | `AC-SI-30-2` | 啟用來源 host 不在 `hosts` ⇒ 該來源 `blocked`、連線 0 | 根層 | P6 | `research.py` | `RG::test_AT_630_2_E_3_host_outside_hosts_is_blocked` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-2-E-4` | `AC-SI-30-2` | 抓取期間鏡像被換 ⇒ 鎖內重驗 `REGISTRY-CHANGED`、零新事件 | 根層 | P6 | `research.py` | `RG::test_AT_630_2_E_4_registry_swapped_during_fetch` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-3-1` | `AC-SI-30-3` | `changed` 依 digest 判定、落地檔與 `latest`、`sources[]` 依 id 位元組序 | 根層 | P6 | `fetch.py`、`research.py` | `NF::test_AT_630_3_1_changed_flags_and_landing` | 真機 V-P6-1 ✅：seq 88～91（RUN-SI-008；`4ad444a1`、`1e9d8a8d`） | ✅ 實作+測試+真機 |
| `AT-630-3-E-1` | `AC-SI-30-3` | 七種單來源失敗矩陣：失敗不入 `sources[]`、全失敗 rc 1 | 根層 | P6 | `fetch.py`、`research.py` | `NF::test_AT_630_3_E_1_failure_matrix` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-3-E-2` | `AC-SI-30-3` | 總牆鐘逾時後其後來源與文章皆 `timeout` | 根層 | P6 | `research.py` | `NF::test_AT_630_3_E_2_scan_wall_clock` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-3-E-4` | `AC-SI-30-3` | 請求鏈牆鐘：多跳重導總耗時逾時、單一來源總耗時上界 | 根層 | P6 | `fetch.py`、`research.py` | `NF::test_AT_630_3_E_4_chain_wall_clock` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-3-E-3` | `AC-SI-30-3` | https 降級重導與 `http://` 來源拒收 | 根層 | P6 | `fetch.py`、`registry.py` | `NF::test_AT_630_3_E_3_redirect_downgrade_and_http_source` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-4-1` | `AC-SI-30-4` | OBS 的 `src=` 對鏡像（含停用 id）與凍結舊表解析，未知者 `SRC-UNKNOWN` | 根層 | P6 | `registry.py`、`check.py`、`fourqparse.py` | `RG::test_AT_630_4_1_src_resolves_against_mirror_and_old_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-5-1` | `AC-SI-30-5` | 只計啟用來源於 `research_fetch_max`、11 筆 `FETCH-MAX` | 根層 | P6 | `research.py`、`registry.py` | `RG::test_AT_630_5_1_only_enabled_sources_count_toward_the_limit` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-6-1` | `AC-SI-30-6` | `research_registry.json` 與舊表皆排除於指紋；`CHECK_RULES_REV` 為 6 | 根層 | P6 | `params.py` | `RG::test_AT_630_6_1_mirror_and_old_table_do_not_change_the_fingerprint` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-7-1` | `AC-SI-30-7` | `netguard.is_public_ip` 對附錄 A 位址表逐列 | 根層 | P6 | `netguard.py` | `NF::test_AT_630_7_1_public_ip_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-7-2` | `AC-SI-30-7` | 附錄 A 表自身 sha256 parity（與 Console 端同表） | 根層 | P6 | `netguard.py` | `NF::test_AT_630_7_2_parity_table_hash` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-7-E-1` | `AC-SI-30-7` | URL 字面判準先於 DNS，被拒時解析次數 0 | 根層 | P6 | `fetch.py`、`registry.py` | `NF::test_AT_630_7_E_1_literal_rules_precede_dns` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-7-E-2` | `AC-SI-30-7` | 每個解析位址都須為公網，單請求只解析一次 | 根層 | P6 | `fetch.py`、`netguard.py` | `NF::test_AT_630_7_E_2_every_address_must_be_public` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-7-3` | `AC-SI-30-7` | 釘 IP 連線、SNI 與 Host 為原主機名 | 根層 | P6 | `fetch.py` | `NF::test_AT_630_7_3_connects_to_validated_ip_with_original_name` | 真機 V-P6-1 ✅：seq 88～91（RUN-SI-008；`4ad444a1`、`1e9d8a8d`） | ✅ 實作+測試+真機 |
| `AT-630-7-E-3` | `AC-SI-30-7` | 重導目標逐跳重驗，拒收者不連線 | 根層 | P6 | `fetch.py` | `NF::test_AT_630_7_E_3_redirect_targets_are_rechecked` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-7-E-4` | `AC-SI-30-7` | AST：`netguard` 不 import `socket`，網路模組只有 `fetch.py` | 根層 | P6 | `netguard.py`、`fetch.py` | `NF::test_AT_630_7_E_4_only_fetch_imports_network_modules` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-1` | `AC-SI-30-8` | sitemap 選取：lastmod 新到舊、同 host、prefix、前 N | 根層 | P6 | `expand.py` | `NF::test_AT_630_8_1_sitemap_selection` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-2` | `AC-SI-30-8` | `links` 模式：基底解析、去 fragment、去重 | 根層 | P6 | `expand.py` | `NF::test_AT_630_8_2_links_mode` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-E-1` | `AC-SI-30-8` | DOCTYPE／ENTITY 在解析前拒收，`_parse_xml` 呼叫 0 次 | 根層 | P6 | `expand.py` | `NF::test_AT_630_8_E_1_doctype_never_reaches_the_parser` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-3` | `AC-SI-30-8` | 整合：文章落地、明細檔、事件不含文章 URL | 根層 | P6 | `expand.py`、`research.py` | `NF::test_AT_630_8_3_integration_articles_and_details` | 真機 V-P6-1 ✅：seq 88～91（RUN-SI-008；`4ad444a1`、`1e9d8a8d`） | ✅ 實作+測試+真機 |
| `AT-630-8-4` | `AC-SI-30-8` | 最壞行長 2119 bytes，不隨明細增長 | 根層 | P6 | `evspec6.py`、`research.py` | `NF::test_AT_630_8_4_event_size_does_not_grow_with_details` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-5` | `AC-SI-30-8` | 展開每次掃描都做，文章 `changed` 對上次明細判定 | 根層 | P6 | `research.py`、`expand.py` | `NF::test_AT_630_8_5_expansion_runs_on_every_scan` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-E-2` | `AC-SI-30-8` | `research.scan` 的 `articles_*` 欄位條件規則 | 根層 | P6 | `evspec6.py` | `NF::test_AT_630_8_E_2_article_keys_validation` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-8-E-3` | `AC-SI-30-8` | 非 UTF-8 系 XML（BOM、NUL、宣告編碼）解析前 `ExpandRefused`（QA4R-01；勘誤 E-6） | 根層 | P6 | `expand.py` | `NF::test_AT_630_8_E_3_non_utf8_xml_is_refused_before_parse` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-9-1` | `AC-SI-30-9` | `to_plain` 對 golden HTML 位元組相等 | 根層 | P6 | `htmltext.py` | `NF::test_AT_630_9_1_golden` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-9-2` | `AC-SI-30-9` | 跨 `PYTHONHASHSEED` 輸出雜湊相同 | 根層 | P6 | `htmltext.py` | `NF::test_AT_630_9_2_deterministic_across_hash_seeds` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-9-E-1` | `AC-SI-30-9` | 空輸入與只含 script 的輸入得空輸出 | 根層 | P6 | `htmltext.py` | `NF::test_AT_630_9_E_1_empty_and_script_only` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-10-1` | `AC-SI-30-10` | 無人運轉複製 `.plain.txt` 旁檔與 changed 文章 | 根層 | P6 | `patrolrun.py` | `NF::test_AT_630_10_1_stage_copies_sidecars_and_changed_articles` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-630-10-E-1` | `AC-SI-30-10` | 明細雜湊不符或複製失敗 ⇒ 不 spawn | 根層 | P6 | `patrolrun.py` | `NF::test_AT_630_10_E_1_mismatch_and_copy_failure_do_not_spawn` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-1` | `AC-SI-45-1` | `src-registry` 稽核檔 `registry-ingest` rc 0 | 根層 | P6 | `registry.py`、`regwrite.py`、`consoleaudit.py` | `RG::test_AT_645_1_1_golden_ingests` | 真機 V-P6-1 ✅：seq 88～91（RUN-SI-008；`4ad444a1`、`1e9d8a8d`） | ✅ 實作+測試+真機 |
| `AT-645-1-E-1` | `AC-SI-45-1` | 驗證碼序表驅動（缺檔至 `REG-*`） | 根層 | P6 | `regwrite.py`、`consoleaudit.py` | `RG::test_AT_645_1_E_1_code_order_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-2` | `AC-SI-45-1` | `registry.validate` 變體表，各回恰一個預期碼 | 根層 | P6 | `registry.py` | `RG::test_AT_645_1_2_validate_variant_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-3` | `AC-SI-45-1` | 附錄 B golden 位元組與 sha 對拍 | 根層 | P6 | `registry.py` | `RG::test_AT_645_1_3_golden_matches_appendix_b_bytes` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-6` | `AC-SI-45-1` | 附錄 D URL parity 表（Console 為 SI 的子集） | 根層 | P6 | `registry.py` | `RG::test_AT_645_1_6_url_parity_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-7` | `AC-SI-45-1` | 17 列種子 URL 全數合格 | 根層 | P6 | `registry.py` | `RG::test_AT_645_1_7_seed_urls_all_valid` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-8` | `AC-SI-45-1` | G-S1 黃金檔等於依附錄 C 重新產生者 | 根層 | P6 | `consoleaudit.py`、`tools/tests/fixtures/selfimproving/G-S1.audit.json` | `RG::test_AT_645_1_8_g_s1_matches_regenerated_bytes` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-9` | `AC-SI-45-1` | `audit_time` 單調性，`REG-STALE` | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_1_9_monotonic_audit_time` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-4` | `AC-SI-45-1` | 24576／65536 上限常數與邊界、超界不截斷 | 根層 | P6 | `registry.py`、`regwrite.py` | `RG::test_AT_645_1_4_size_constants_and_boundaries` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-1-5` | `AC-SI-45-1` | G-S1 入帳得附錄 B golden 鏡像 | 根層 | P6 | `regwrite.py`、`consoleaudit.py` | `RG::test_AT_645_1_5_g_s1_ingests_to_the_golden_mirror` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-2-1` | `AC-SI-45-2` | 入帳寫鏡像位元組與 `research.registry` 事件欄位 | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_2_1_event_fields` | 真機 V-P6-1 ✅：seq 88～91（RUN-SI-008；`4ad444a1`、`1e9d8a8d`） | ✅ 實作+測試+真機 |
| `AT-645-2-2` | `AC-SI-45-2` | 內容相同再入帳：`changed=false`、不換檔 | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_2_2_unchanged_content_does_not_rewrite` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-2-E-1` | `AC-SI-45-2` | 事件追加失敗還原鏡像 | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_2_E_1_event_failure_restores_mirror` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-2-E-2` | `AC-SI-45-2` | `os.replace` 失敗為乾淨拒收 | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_2_E_2_replace_failure_is_a_clean_reject` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-2-E-3` | `AC-SI-45-2` | 鎖內重驗 `audit_ref`，併發重用被擋 | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_2_E_3_ref_reused_inside_the_lock` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-2-E-4` | `AC-SI-45-2` | 崩潰窗口：鏡像已換事件未寫，重入帳自癒 | 根層 | P6 | `regwrite.py` | `RG::test_AT_645_2_E_4_crash_window_self_heals` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-3-1` | `AC-SI-45-3` | 入帳後 `check` 35 項皆綠 | 根層 | P6 | `check.py`、`registry.py` | `RG::test_AT_645_3_1_ingested_repo_checks_green` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-3-E-1` | `AC-SI-45-3` | 手改鏡像、有鏡像無事件、有事件無鏡像 ⇒ `REGISTRY-UNBOUND` | 根層 | P6 | `check.py` | `RG::test_AT_645_3_E_1_unbound_mirror_variants` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-3-E-2` | `AC-SI-45-3` | 新格式 `research.scan` 的 `registry_seq` 綁定與 `SRC-UNKNOWN` | 根層 | P6 | `check.py` | `RG::test_AT_645_3_E_2_new_scan_event_binding` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-3-2` | `AC-SI-45-3` | `known_ids` 於兩處呼叫面皆被使用 | 根層 | P6 | `check.py`、`fourqparse.py` | `RG::test_AT_645_3_2_known_ids_are_used_by_both_call_sites` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-4-1` | `AC-SI-45-4` | 巡邏 `_ingest_argv` 與 `console_pending` 入帳 | 根層 | P6 | `patrol.py`、`consoleaudit.py` | `RG::test_AT_645_4_1_ingest_argv_and_pending` | 手動 `registry-ingest` 已真機驗（V-P6-1 seq 88）；巡邏自動入帳路徑尚未真機觸發 | 🟡 實作+測試完成；巡邏路徑真機待驗 |
| `AT-645-4-E-1` | `AC-SI-45-4` | `registry-ingest` 屬 C 類，無人值守拒收 | 根層 | P6 | `unattended.py` | `RG::test_AT_645_4_E_1_registry_ingest_is_c_class` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-4-E-2` | `AC-SI-45-4` | MAC 被改時拒收草稿只記一次 | 根層 | P6 | `patrol.py` | `RG::test_AT_645_4_E_2_rejection_draft_is_logged_once` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-5-1` | `AC-SI-45-5` | 鏡像與回測結果帳本不列入 dirty-tree | 根層 | P6 | `sched.py` | `RG::test_AT_645_5_1_own_paths_are_not_dirty` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-6-1` | `AC-SI-45-6` | 舊表 sha256 與位元組數凍結 | 根層 | P6 | （`research_sources.json` 不變） | `RG::test_AT_645_6_1_old_table_is_frozen` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-6-2` | `AC-SI-45-6` | 活動路徑不讀舊表 | 根層 | P6 | `research.py`、`regwrite.py` | `RG::test_AT_645_6_2_active_paths_do_not_read_the_old_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-6-3` | `AC-SI-45-6` | 特性化：刪舊表後歷史檢查只剩 `SOURCE-UNAVAILABLE` | 根層 | P6 | `check.py` | `RG::test_AT_645_6_3_deleting_the_old_table_silences_history_checks` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-6-4` | `AC-SI-45-6` | 舊事件 `sources_sha256` 仍被檢查，新格式不觸發 | 根層 | P6 | `check.py` | `RG::test_AT_645_6_4_old_sha_is_still_checked_new_format_is_not` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-7-1` | `AC-SI-45-7` | `KINDS` 27、標籤齊備、三種合法事件 | 根層 | P6 | `evspec6.py`、`evspec.py`、`events.py`、`issuemap.py` | `RG::test_AT_645_7_1_vocabulary_and_valid_events` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-7-E-1` | `AC-SI-45-7` | 事件欄位負控變體各得 `EVENT-*` | 根層 | P6 | `evspec6.py` | `RG::test_AT_645_7_E_1_invalid_variants` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-7-2` | `AC-SI-45-7` | 最壞事件長度 2119／561／472 | 根層 | P6 | `evspec6.py` | `RG::test_AT_645_7_2_worst_case_line_lengths` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-8-1` | `AC-SI-45-8` | `status` 兩鍵 `research_fetch_max`、`research_registry` 與 export 同值 | 根層 | P6 | `status.py` | `RG::test_AT_645_8_1_registry_keys` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-645-8-E-1` | `AC-SI-45-8` | 參數無效時為 None、事件缺必備欄不採用 | 根層 | P6 | `status.py`、`evspec6.py` | `RG::test_AT_645_8_E_1_invalid_cap_and_incomplete_event` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-1-1` | `AC-SI-46-1` | `cases --build` 對 golden 的案例與排除 | 根層 | P6 | `btcases.py` | `BT::test_AT_646_1_1_build_matches_golden` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-1-E-1` | `AC-SI-46-1` | 七種排除原因各一例 | 根層 | P6 | `btcases.py` | `BT::test_AT_646_1_E_1_every_exclusion_reason_is_applied` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-1-2` | `AC-SI-46-1` | 確定性、版本遞增、不覆寫既有檔 | 根層 | P6 | `btcases.py` | `BT::test_AT_646_1_2_deterministic_versioned_and_never_overwritten` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-1-3` | `AC-SI-46-1` | 案例檔正規化序列化與 `--check` 偵測漂移 | 根層 | P6 | `btcases.py` | `BT::test_AT_646_1_3_file_is_normalized_and_check_detects_drift` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-2-1` | `AC-SI-46-2` | `prepare` 以 sha256 排序抽樣、snap 在 repo 外、任務書不洩漏答案 | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_2_1_reproducible_sampling_and_repo_outside_snapshots` | 真機 V-P6-2 ✅：BT-003（seq 95，`c3f43217`） | ✅ 實作+測試+真機 |
| `AT-646-2-E-1` | `AC-SI-46-2` | 拒收路徑整批回退；池子小於 K ⇒ `BT-POOL-TOO-SMALL` | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_2_E_1_refusals_leave_no_batch_no_worktree_no_event` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-2-2` | `AC-SI-46-2` | `worktree add` argv 含 `--detach`、無 `--force` | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_2_2_worktree_add_argv_and_no_force` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-3-1` | `AC-SI-46-3` | `answer` 原樣保存並綁 `agent_id` | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_3_1_answer_is_copied_verbatim_and_bound` | 真機 V-P6-2 ✅：BT-003（seq 95，`c3f43217`） | ✅ 實作+測試+真機 |
| `AT-646-3-E-1` | `AC-SI-46-3` | 格式錯誤、未知案、重複答案皆拒收且零變化 | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_3_E_1_malformed_answers_are_refused_and_change_nothing` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-4-1` | `AC-SI-46-4` | `score_case` golden 表（命中名次、去重、正規化、recall） | 根層 | P6 | `btscore.py` | `BT::test_AT_646_4_1_score_case_golden_table` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-4-E-1` | `AC-SI-46-4` | `aggregate` 精確算術與邊界；AST 無浮點 | 根層 | P6 | `btscore.py` | `BT::test_AT_646_4_E_1_aggregate_uses_exact_arithmetic` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-4-2` | `AC-SI-46-4` | 只有 ok 案例進分母 | 根層 | P6 | `btscore.py` | `BT::test_AT_646_4_2_only_ok_cases_enter_the_denominator` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-5-1` | `AC-SI-46-5` | 乾淨逐字稿判 ok | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_1_clean_transcript_is_ok` | 真機 V-P6-2 ✅：BT-003（seq 95，`c3f43217`） | ✅ 實作+測試+真機 |
| `AT-646-5-E-1` | `AC-SI-46-5` | 各種髒樣本各有原因碼；`inside` 對 ntpath／posixpath 各一組 | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_E_1_each_dirty_pattern_has_its_reason` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-5-E-2` | `AC-SI-46-5` | 逐字稿目錄缺或佈局改名 ⇒ fail-closed | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_E_2_missing_dir_or_renamed_layout_fails_closed` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-5-E-3` | `AC-SI-46-5` | 交卷工具 `SubagentHandback` 不算洩漏；越界 `Read`、`Bash` 照判（勘誤 E-8；固件為真實交卷形狀，E-9） | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_E_3_harness_handback_tool_is_not_a_leak` | 真機 BT-002 四案逐字稿重判皆乾淨；BT-003 contaminated 0 | ✅ 實作+測試（QA_384 PASS） |
| `AT-646-5-E-4` | `AC-SI-46-5` | 交卷收尾只認緊鄰 assistant 行交卷 id 的非錯誤 `tool_result`（勘誤 E-9） | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_E_4_handback_closure_needs_a_matching_ok_result` | 真機 BT-003 五案皆判已收尾 | ✅ 實作+測試（QA_384 PASS；突變 e 補殺 `89766d18`） |
| `AT-646-5-E-5` | `AC-SI-46-5` | 只交卷、零讀取＝`no-reads`（交卷不計讀取；勘誤 E-9） | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_E_5_handback_alone_is_not_a_read` | — | ✅ 實作+測試（QA_384 PASS） |
| `AT-646-5-E-6` | `AC-SI-46-5` | `Read` 目標 `file_path` 優先、非字串時取 `path`（勘誤 E-9） | 根層 | P6 | `btscore.py` | `BT::test_AT_646_5_E_6_read_target_falls_back_to_path_key` | 真機 BT-002 s4（被拒收的錯鍵 `Read`）重判乾淨 | ✅ 實作+測試（QA_384 PASS） |
| `AT-646-6-1` | `AC-SI-46-6` | `score` 追加結果列，事件與列數值一致 | 根層 | P6 | `btrecord.py` | `BT::test_AT_646_6_1_ledger_row_and_event_agree` | 真機 V-P6-2 ✅：BT-003（seq 95，`c3f43217`） | ✅ 實作+測試+真機 |
| `AT-646-6-E-1` | `AC-SI-46-6` | 同批重評拒收；事件追加失敗時結果帳本截回 | 根層 | P6 | `btrecord.py` | `BT::test_AT_646_6_E_1_rescore_and_failed_event_leave_ledger_intact` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-6-2` | `AC-SI-46-6` | `check` 綁定列、事件、案例檔 | 根層 | P6 | `check.py`、`btrecord.py` | `BT::test_AT_646_6_2_check_binds_rows_events_and_cases` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-7-1` | `AC-SI-46-7` | `cleanup` 用 `worktree remove` 再 `prune`，無 `--force` | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_7_1_cleanup_uses_worktree_remove_then_prune` | 真機 V-P6-2 ✅：BT-003（seq 95，`c3f43217`） | ✅ 實作+測試+真機 |
| `AT-646-7-E-1` | `AC-SI-46-7` | 髒快照保留、其餘照清、仍 `prune` | 根層 | P6 | `btwrite.py` | `BT::test_AT_646_7_E_1_dirty_snapshot_is_kept_and_others_cleaned` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-8-1` | `AC-SI-46-8` | `status.backtest` 鍵與同版本走勢 | 根層 | P6 | `status.py` | `BT::test_AT_646_8_1_status_key_and_trend_stays_within_one_cases_version` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-8-E-1` | `AC-SI-46-8` | `proof` 不得引用回測分數（`PROOF-BACKTEST`） | 根層 | P6 | `evcheck.py`、`evspec.py` | `BT::test_AT_646_8_E_1_proof_may_not_cite_backtest_scores` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-8-2` | `AC-SI-46-8` | 回測結果不入 M1～M5 指標與指紋 | 根層 | P6 | （指標不讀回測） | `BT::test_AT_646_8_2_measures_do_not_read_backtest_results` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-646-8-3` | `AC-SI-46-8` | 無人值守下 `backtest` 各子命令拒收、零網路 | 根層 | P6 | `unattended.py` | `BT::test_AT_646_8_3_unattended_refuses_every_subcommand_and_nothing_touches_the_network` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-690-1-1` | `AC-P6-090-1` | 能力登記 72 鍵＝(52,13,2,5)，新十檔類別 | 根層 | P6 | `tools/tests/test_selfimproving_capability.py` 登記表 | `BT::test_AT_690_1_1_capability_registry_is_72_with_the_new_ten` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-690-1-E-1` | `AC-P6-090-1` | 注入變體使登記判準各回對應問題 | 根層 | P6 | `tools/tests/test_selfimproving_capability.py` 登記表 | `BT::test_AT_690_1_E_1_registry_judgement_has_teeth_for_the_new_files` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-690-2-1` | `AC-P6-090-2` | `params.json` 位元組 sha、44 鍵、`CHECK_RULES_REV` 為 6 | 根層 | P6 | （`params.json` 不動） | `RG::test_AT_690_2_1_params_json_is_untouched` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-690-3-1` | `AC-P6-090-3` | 零退化：項目數、鍵數、`research --skip` 輸出 | 根層 | P6 | （既有行為不變） | `BT::test_AT_690_3_1_no_regression_on_counts_and_skip_output` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-690-3-2` | `AC-P6-090-3` | SOP 機械判準通過且有牙（新節位置） | 根層 | P6 | `docs/05_development/SelfImproving_Operations_SOP.md`（判準在測試） | `RG::test_AT_690_3_2_sop_criteria_pass_and_have_teeth` | — | ✅ 實作+測試（SCG-4 二審 PASS） |
| `AT-690-4-1` | `AC-P6-090-4` | 範圍守衛：差分 ⊆ 允許集合，逐 commit 以 `SI_SCOPE_BASE`／`SI_SCOPE_TIP` 驗 | 根層 | P6 | （範圍守衛；勘誤 E-6、E-7） | `BT::test_AT_690_4_1_scope_guard_needs_an_explicit_base` | 本鍵五個 commit 逐一驗全綠（二審；見 SCG-4 報告） | ✅ 實作+測試（SCG-4 二審 PASS） |

## 真機待驗項（TCS-P6 §1 末與運行期資料列；不入 AT）

| 編號 | 內容 | 前置 | 目前狀態 |
|------|------|------|----------|
| `V-P6-1` | 登記 → 入帳 → 實抓：Console 登記來源並簽章同步，根層巡邏或手動 `registry-ingest` 入帳，再 `research --fetch` 實抓（含釘 IP、文章展開、`.plain.txt` 旁檔），產生 `research_registry.json` 與 `research.scan` 事件 | 需 Console 半（`agentconsole-research-registry`）真棧 | ✅ 已驗：長駐棧重建（Flyway V24／V25）→ ADMIN 同步 201 → `registry-ingest` seq 88（鏡像 sha＝Console digest）→ RUN-SI-008 `research --fetch` 9／10 來源成功、網站地圖展開 3 篇文章全文含 `.plain.txt`（seq 89～91；`4ad444a1`、`1e9d8a8d`）；arxiv 外部限流登 OBS-SI-381（deferred）；巡邏自動入帳路徑尚未真機觸發 |
| `V-P6-2` | K=5 反事實回測：`backtest cases --build` → `prepare` → 子代理 `answer` → `score` → `cleanup`，產生 `docs/06_quality/SelfImproving_Backtest/**` 與 `backtest.result` 事件 | 需真實歷史缺陷案例與子代理逐字稿 | ✅ 已驗：BT-001／BT-002 皆 n=0，揭露 OBS-SI-382／383／384（修正 `3371129b`、`e298f324`、`89766d18`）；BT-003（seed 20261111，k 5）n=5、unanswered 0、contaminated 0、hit1/3/5=3/3/3、prec_pm 220、rec_pm 290（seq 95，`c3f43217`）；cleanup 後無殘留 worktree |
