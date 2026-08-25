# CrossPlatform R105 — 四方複審 REJECT 修復（DEF-200-202）

**本輪護欄層累積淨額（稽核痕跡合計，四批合併）＝ 88556 → 88656（+100）**
——逐檔清單見下方〈§A 逐檔清單〉。

- **輪次**：R105（四方複審對本輪 8 筆缺陷修復包的 REJECT 意見彙整，逐筆親自查證後
  修正；本檔只記錄本輪唯一需要真正動程式碼的一筆——DEF-200-202）。
- **背景**：Architect／SA／SD／QA 四方獨立複審一致指出，`docs/06_quality/
  AutoSDD_Defect_Log.md` 標記為本輪已修的 8 筆缺陷中，`DEF-200-202`
  （`tools/lib/quota_gate.py` 呼叫 `quota_policy.decide()` 不帶 `active_model`
  ⇒ `weekly_scoped`／`seven_day_opus`／`seven_day_sonnet` 等模型分軌軸結構上零
  煞車力）在工作樹 diff 中零改動（`git diff --stat -- tools/lib/quota_gate.py`
  無輸出），屬「宣稱已修但完全未動程式碼」。其餘 7 筆（DEF-101-402、
  DEF-200-012／015／043／158／173／196）經逐筆重新查證，程式碼修復皆屬實，
  複審意見在這 7 筆上要嘛已被生產程式碼證實成立，要嘛（DEF-200-015 新曝露的
  懸空引用）需要小幅追加修復，詳見本輪回報，不重複記錄於本檔。

## §A 逐檔清單

| 檔案 | 舊值 | 新值 | 淨額 | 說明 |
| :---- | ---: | ---: | ---: | :---- |
| `tools/lib/quota_gate.py` | (非護欄層檔，不計行數棘輪) | — | — | `quota_gate()` 新增 `active_model` 參數並接進 `quota_policy.decide(..., active_model=active_model)`；不影響任何既有呼叫端行為（缺席時逐字沿用 `None`） |
| `.claude/hooks/context_budget_guard.py` | (受 SPECIAL_FILES raw-line 棘輪管，非本表射程) | — | — | `main()` 把 `scan_transcript()` 提前到 `quota_gate.quota_gate()` 呼叫之前，取 `model_family(逐字稿 model 字串)` 傳入 `active_model`；context 與 quota 兩把尺共用同一次掃描結果，非重複 I/O |
| `tools/tests/test_context_budget_guard.py` | 8108 | 8157 | +49 | 新增 `QuotaGateIsWiredToTheBurnPathTest.test_the_model_scoped_axis_only_brakes_when_the_transcript_names_it`（DEF-200-202 端到端回歸：模型不符時仍正確排除、模型相符時真的 halt）；`_write_jsonl`／`_quota_cache` 兩個既有 fixture 各補一個可選參數（`model`／`scope_models`）；修正三支被本輪結構性改動撞到的既有測試——`QuotaDecisionEntryIsSingleTest` 的 `decide` spy 簽章補 `*args/**kwargs`，`QuotaGateIsIndependentOfContextTest`／`EnduranceWiringTest` 的錨點字面由 `transcript_path`（本輪合法新增的模型讀取使其不再唯一定位五道早退起點）改為 `if transcript is None:` |
| `tools/tests/_platform_helpers.py` | 403 | 407 | +4 | `strip_ps_comments()` docstring 三段過長行（East Asian Width > 100）折行，內容逐字未動（`test_e501_debt_only_shrinks` 存量債棘輪對本檔的既有連帶要求） |
| `tools/tests/test_defect_id_reference_integrity.py` | 262 | 274 | +12 | DEF-200-015 四方複審續：`ledger_primary_ids()`／`is_ledger_path()` 擴面納管姊妹帳本 `AutoSDD_External_Blocked_Log.md`（此前只掃 `AutoSDD_Defect_Log*.md`，拆過去的 DEF-200-185／186 結構上必為懸空引用）；`tools/check_handoff_carriers.py` 的自測合成 ID 比照同檔 `_syn()` 改執行期組字，避免被擴大後的掃描面誤命中 |
| `tools/tests/test_platform_neutral_paths.py` | 5724 | 5727 | +3 | 帳本狀態欄回填 `fixed@R105`（DEF-200-202）觸發 `_DIRENT_UNGUARDED_DEBT`（41→42）：`QuotaGateIsWiredToTheBurnPathTest` 新增回歸測試多用一次既有 `.replace()` 慣用句式（同檔既有測試已大量使用同一句式，未另立新形態） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | 6199 | 6199+ | +0（本列自身編修另計） | 本表與本列、`_REPIN_LOG_FROZEN_PREFIX_LEN`／`_REPIN_LOG_HISTORY_SHA256`／`_FROZEN_PREFIX_REWRITE_LEDGER` 隨附編修不計入本輪功能淨額（同既有體例，見 R102 系列多筆「同輪追加」列） |
| **合計** | 88556 | 88656 | **+100** | 四批：端到端回歸測試 +49、`_platform_helpers.py`／`test_defect_id_reference_integrity.py` 功能淨額 +16、`test_platform_neutral_paths.py` 帳本連帶 +3、本檔自身編修（含四批各自的稽核列）+32 |

## §B 為何 `active_model` 用 `model_family()` 正規化，而不是原始逐字稿字串

`quota_policy._model_active()` 對 `axis.scope_model`（伺服器回的顯示名，實測值
`"Fable"`）與 `active_model` 做**逐字** casefold 比對，不做子字串比對。逐字稿的
`message.model` 欄實測是完整模型識別碼（如 `claude-sonnet-5`、`claude-fable-5`），
直接傳入無法匹配 `"Fable"`。`model_family()`（R79 既有函式，家族清單本就含
`"fable"`／`"opus"`／`"sonnet"`／`"haiku"`）把逐字稿字串正規化成家族字後，才與
`scope_model` casefold 相等——本機 `~/.claude/projects/` 逐字稿語料庫實測確認
`claude-fable-5` 為真實出現過的模型識別碼，`model_family("claude-fable-5")`
＝`"fable"`，與 `"Fable"` casefold 相等。

## §C 逐缺陷驗證摘要（8 筆，帳本狀態欄的一句話指標指向本節）

- **DEF-200-202**（唯一真需要動程式碼的一筆，見上方 §A／§B）：`quota_gate()` 新增
  `active_model` 參數接進 `quota_policy.decide()`；`main()` 取逐字稿
  `model_family()` 正規化後傳入。`python3 -m pytest tools/tests/test_context_budget_guard.py
  tools/tests/test_quota_policy.py -q` 實測 1096 passed（2 筆 pre-existing 失敗
  `QuotaEnvFileIsActuallyLoadedTest` 與本缺陷無關，源於開發機真實 `.env`
  `AUTOSDD_QUOTA_HALT_PCT=95` 污染測試假設，非本輪引入）。
- **DEF-101-402**：`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`
  補 `autoclaude-ci.yml` 消費目錄對照＋`TYPE_CHECKING` import 排除＋套件形態
  （`__init__.py`）import 解析。`python3 -m pytest
  AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py -q` 實測 49 passed。
- **DEF-200-012**：`tools/lib/quota_meter.py::cache_path()` 改走 `Path.home()`＋
  逃生口環境變數 `AUTOSDD_QUOTA_CACHE_DIR`（與 mac 各 launchd 服務各自的
  `$TMPDIR` 無關的穩定路徑）；`write_cache()` 補寫入前
  `mkdir(parents=True, exist_ok=True)`。
- **DEF-200-015**：`_REF_RE`／`git grep` pattern 由僅 `DEF-101-\d+` 擴大為
  `DEF-(?:101|200)-\d+`；`ledger_primary_ids()`／`is_ledger_path()` 擴面納管姊妹
  帳本 `AutoSDD_External_Blocked_Log.md`（此前只掃 `AutoSDD_Defect_Log*.md`，拆
  過去的 DEF-200-185／186 結構上必為懸空引用）；`tools/check_handoff_carriers.py`
  的自測合成 ID 比照 `_syn()` 改執行期組字，避免被擴大後的掃描面誤命中。
  `python3 -m pytest tools/tests/test_defect_id_reference_integrity.py -q` 實測
  11 passed。仍非理想形態（具名列舉單一姊妹帳本路徑，非動態現查族號集合），交棒見
  `docs/04_planning/R105_HANDOFF.md` §3。
- **DEF-200-043**：`AutoClaude/autoclaude/infra/repositories/file_state_repository.py::
  save_checkpoint` 的 tmp 檔名改帶 `os.getpid()`＋`uuid.uuid4().hex`。
  `python3 -m pytest tests/integration/test_concurrent_runs.py -q`（AutoClaude/
  目錄下）實測 5 passed，含新增回歸測試
  `test_two_concurrent_writers_to_the_same_playbook_id_do_not_share_a_tmp_file`。
- **DEF-200-158**：`.claude/hooks/block_destructive_git.py::_background_amps()`
  判準③補 `i==0` 分支（段首 `&` 視為 PowerShell call operator，非背景符號）。
  `python3 -m pytest tools/tests/test_block_destructive_git_r83.py -q` 實測
  153 passed，含新增回歸測試 `test_the_background_amp_exclusions_are_load_bearing`。
- **DEF-200-173**：`patch.object(endurance_env.Path, "mkdir", …)` 打
  `pathlib.Path` 本尊的舊版注入，改新增 `_DenyMkdirPath`（`type(Path())` 子類，
  只覆寫 `mkdir`）並 `mock.patch.object(endurance_env, "Path", _DenyMkdirPath)`，
  收斂到受測模組。`python3 -m pytest tools/tests/test_mac_endurance_r83.py -q`
  實測 102 passed。
- **DEF-200-196**：`tools/lib/quota_meter.py::retry_after_at()` 對 `secs <= 0`
  改 `continue`（試下一個候選標頭，全部不可信時交由既有 `return None`），不再
  合成 `now+timedelta(seconds=secs)` 這個等於現在的時刻。實測同 DEF-200-202 的
  `test_context_budget_guard.py` 855 passed 一併涵蓋。
