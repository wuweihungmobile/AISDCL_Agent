# CrossPlatform R137 — DEF-200-274 第五輪四方獨立複審收斂 round-label-ok

- **輪籤**：R137（2026-09-09，macOS；主控收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R136（DEF-200-274 第四輪第二次對抗式複審收斂，見
  `CrossPlatform_R136_Scan_Findings.md`）。本輪為掌舵者直接提問的獨立五輪四方
  複審（Architect／SA／SD／QA 各自獨立跑，無互相參照），針對現況重新核對「①
  帳本問題是否解決、②多CPU測試功能是否完備、③是否有頭重腳輕分配不均」三題。

---

## §1 護欄層淨額承認

<!-- guard-total:R137 --> 本輪護欄層行數 95843 → 95925（+82，全額功能軌，非
回歸鎖）——四方複審中 Architect 原僅點名 `test_platform_neutral_paths.py` 一處
TOCTOU 缺口，收尾單人窗口實作修復時逐一核對整棵 `tools/tests/` 樹的
`rglob("*.py")`／`glob("*.py")` 站點，另在以下檔案各找到同型缺口並一併補上
`_zzz_` 合成暫存模組排除：

- `test_subprocess_encoding_hygiene.py`（5 處呼叫點）
- `test_no_invalid_escape_sequences.py`（3 處呼叫點）
- `test_pre_push_dispatcher.py`、`test_adr_xplat001_c1c2_lock.py`、
  `test_ps_engine_ssot.py`（各 1～2 處）
- `test_dev_start.py`、`test_bash_probe_spec_contract.py`、
  `test_mac_endurance_r83.py`、`test_find_git_bash_parity.py`（各 1 處）

逐檔分解：
- `test_platform_neutral_paths.py`／`test_subprocess_encoding_hygiene.py`／
  `test_no_invalid_escape_sequences.py`／`test_pre_push_dispatcher.py`／
  `test_ps_engine_ssot.py`／`test_dev_start.py`／
  `test_bash_probe_spec_contract.py`／`test_mac_endurance_r83.py`／
  `test_find_git_bash_parity.py` 九檔合計 +64：各自新增一行過濾條件（`_zzz_`
  前綴排除）＋精簡註解，`tools/lib/parallel_shard.py` 補齊 Ctrl-C 孤兒行程清理
  （`stop_event`＋drain `pending`＋kill 已啟動子行程＋等 thread 真的結束才
  re-raise）與 per-module wall-clock 計時觀測（`_MergedResult.module_timings`
  ＋`run_root_unittests.py::report_module_timings()`），後者不進逐檔行數表。
- `test_adr_xplat001_c1c2_lock.py` 自身逐檔漂移 +18：本輪稽核列＋
  `_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列＋`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`
  展延註記＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列本身的行數。

## §2 分桶棘輪（guard_self）

`guard_self` 桶 3259 → 3261（+2）：九支檔的過濾條件新增行本身即歸屬該桶（散文
判準邏輯本身，非可移出的說明文字）；落地過程中已把原本較長的逐條調查敘述收斂
成單行註解，把散文成長壓到最低。見 `tools/lib/guard_bucket_policy.py` 該常數
旁註。

## §3 到期義務兌現與展延

- `_REPIN_NET_CAP_SCHEDULE` 到期義務兌現：cap 548 → 547
  （`_REPIN_NET_CAP_DUE_ROUND=137` 本輪剛好到期），同輪重新武裝下一段
  （`_REPIN_NET_CAP_DUE_ROUND=139`／`_REPIN_NET_CAP_DUE_TARGET=546`，步伐維持
  最小正整數 1）。
- `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 具名展延 137 → 142（真拆 ADR-XPLAT-013
  §9.3／U9 四支 [ROOT-TOOLS] 檔屬獨立重構持有面，非本輪主軸，鐵律七不得靜默
  沿用）。

## §4 四方複審逐條處理

四方獨立審查（各自不共享上下文，分別跑）：
- **Architect**：`VERDICT_LEDGER_RESOLVED=partial`／`VERDICT_FEATURE_COMPLETE=partial`
  ／`VERDICT_LOAD_BALANCED=partial`。找到 4 項發現，其中 finding 4（Ctrl-C 未清理
  孤兒行程）為本輪新發現，已修復。
- **SA**：三項驗證與 Architect 一致，額外指出 `ONBOARDING.md` 完全未提及
  `AUTOSDD_PARALLEL_TESTS` 開關（feature-complete 判 partial 的直接理由）。
- **SD**：逐條核實 Architect 四項發現皆屬實，並在 `tools/subprocess_encoding_hygiene.py`
  等檔獨立找到同一 TOCTOU 病灶的另外兩個呼叫點（NEW finding 2/3）。
- **QA**：實測序列 805.61s vs 平行(8w) 252.72s（3.19x，約 40% 理論效率）；找到
  `test_doc_loc_baseline_freshness_r60.py` 單一模組耗時 163.19s、占平行總耗時
  約 65%，是「頭重腳輕」問題的直接根因；現場複現 TOCTOU 崩潰 1/3 次。

收尾單人窗口據四方發現逐條修復（見 §1），未再另行複審，因每項修法皆為既有
`_read_text_or_none()`／`_zzz_` 排除慣例的機械延伸，風險低於重新走一輪複審的
時間成本。完整四方獨立審查逐字記錄與端到端重驗輸出見任務完成回覆；缺陷帳本索引
見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274；詳細證據見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`〈第五輪〉節。

## §5 誠實劃界（本輪仍未解決的項目）

- **Windows 真機驗證**：仍未解，本 session 全程 macOS-only，無法在此完成。
  `VERDICT_LEDGER_RESOLVED`／`VERDICT_FEATURE_COMPLETE` 因此維持 `partial`，
  不宣稱 `fixed`/`closed`。
- **run-to-run 失敗數變異**（序列 6F/0E、平行 8w 10F/0E、平行 4w 6F/1E）：QA
  懷疑與本機背景 nightly 自動化搶資源有關，未能在本輪內完全排除，誠實記載為
  未解問題，非本輪聲稱已修復的範圍。
- **本檔（`test_adr_xplat001_c1c2_lock.py`）掃描面排查非窮盡**：本輪掃過
  `tools/tests/` 下所有含 `rglob("*.py")`/`glob("*.py")` 的檔案並逐一核對是否
  觸及該目錄且讀取內容，但未對 `AutoClaude/tests/`／`AISDLC_SDD/` 等其他樹做
  同型排查——若那些樹底下也有平行測試合成暫存檔案的類似風險，仍可能有漏網。
