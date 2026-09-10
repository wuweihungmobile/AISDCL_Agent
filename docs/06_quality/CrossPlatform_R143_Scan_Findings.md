# CrossPlatform R143 — DEF-200-275 第四輪收尾：護欄層淨額記帳

- **輪籤**：R143（2026-09-10，macOS；單一 Developer 執行，主控收尾單人窗口 commit）。
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R142（DEF-200-275／DEF-200-277 收尾，見 `CrossPlatform_R142_Scan_Findings.md`）。
  本輪非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-275 第四輪（hook 分子改讀本 session
  逐字稿 API usage、≥95% 改 session 級拒絕、一行人工恢復）收尾時，護欄層淨額棘輪的記帳延伸。

---

## §1 護欄層淨額承認

<!-- guard-total:R143 --> R143 護欄層累積淨額＝ 96506 → 97056（+550＝+238 收尾 ＋ +73 第 1 輪審查修復同輪追加 ＋ +312 DEF-200-278 同輪三度追加，全額歸回歸鎖軌）——
DEF-200-275 第四輪：新增 `tools/tests/test_context_window_parity.py`（+145；根層
`.claude/hooks/context_budget_guard.py` ↔ SDD LATEST `tools/fsm_runtime/context_window.py` 的
parity 鎖，同一組夾具比對 `used_of`／`scan_transcript`／`compact_boundary_count`／
`carries_wide_marker`／`model_family`／`window_from_model`／`resolve_window`+`may_block`，
含 bug-injection 自證；兩子專案刻意不跨 import，複製的知識只有一份會被改，本鎖是唯一的機械物）；
`test_adr_xplat001_c1c2_lock.py` 自身逐檔漂移 +17（主表本列＋本軌新列＋
`_REPIN_NET_CAP_SCHEDULE` 到期兌現列 `(143, 544)`、`_FROZEN_PREFIX_REWRITE_LEDGER` R143 鏈列與重新武裝
`_REPIN_NET_CAP_DUE_ROUND=145`／`_REPIN_NET_CAP_DUE_TARGET=543`）；
`test_platform_neutral_paths.py` +3（`_DIRENT_UNGUARDED_DEBT` 42→40 的**下修**註解——SDD
`conversation_ledger.py` 原三個 `os.replace` 站點收斂為 `_atomic_write_yaml` 一處）。
證據見 `docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第四輪〉；
缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-275。此附記為 doc-total 對帳
（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同 R129～R142 寄居體例。round-label-ok

**同輪追加（四方第 1 輪審查修復，單一 Developer；+73，全額歸回歸鎖軌）**：SA-R4-03 點名整合閘門
候選鏈（D8／C14）零鑑別測試——`tools/tests/test_find_git_bash_parity.py::TestIntegrationGateShellDelegation`
補三案（+60）：PATH 只有 python3 ⇒ 第二候選接手；PATH 無 python／python3 但 repo 有 `.venv/bin/python`
⇒ 第三候選接手；三候選全無 ⇒ rc=1 且 stderr 逐字點名三候選、核心未被執行。遮蔽真直譯器的手法＝把假
`python`／`python3` 放進名為 `WindowsApps/` 的目錄排 PATH 最前（`is_real_python_candidate` 對該路徑段
一律回 1），不必從 PATH 拔掉住著 `dirname`／`tr` 的系統目錄；bug-injection 自證：把候選鏈拔回只認
`python` ⇒ 恰好那兩案轉紅（`2 failed, 5 passed`），還原後 7 passed、`check_wrapper_thinness.py` rc=0。
`test_adr_xplat001_c1c2_lock.py` 自身漂移 +13（主表同輪追加列 96671→96744、`_REGRESSION_LANE_LOG`
同輪列、`_FROZEN_PREFIX_REWRITE_LEDGER` 鏈列 7bd3af08e2e2→3d5c464c7535）。Windows 側未實跑
（shim 以 `.exe` 命名、靠 MSYS `command -v` 的 `.exe` 透明解析），交 windows-compat-ci 驗證。

## §2 逐檔清單

| 檔 | 前 | 後 | 淨額 | 歸類 |
|---|---|---|---|---|
| `tools/tests/test_context_window_parity.py` | 0（新檔） | 145 | +145 | 回歸鎖軌 |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | 7723 | 7740 | +17 | 回歸鎖軌（記帳誠實度） |
| `tools/tests/test_platform_neutral_paths.py` | 5759 | 5762 | +3 | 回歸鎖軌（欠債表下修註解） |
| `tools/tests/test_find_git_bash_parity.py`（同輪追加） | 1266 | 1326 | +60 | 回歸鎖軌（候選鏈三案） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py`（同輪追加） | 7740 | 7753 | +13 | 回歸鎖軌（記帳誠實度） |
| `tools/tests/test_wake_chain_halt_r278.py`（三度追加） | 0（新檔） | 299 | +299 | 回歸鎖軌（DEF-200-278） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py`（三度追加） | 7753 | 7766 | +13 | 回歸鎖軌（記帳誠實度） |

SDD 子專案側（`AISDLC_SDD/AISDLC_SDD_v0.30/`）的 hook／runtime／測試改動計入該子專案自身的
LOC 政策，不落本檔棘輪射程；逐檔見證據檔〈第四輪〉§修法逐檔。

## §3 三度追加（DEF-200-278，單一 Developer；+312，全額歸回歸鎖軌）

喚醒鏈缺口收尾（額度 halt 後不會自動續跑）：`quota_gate.resolve_halt_transcript()` 在
payload 缺 `transcript_path` 時以 `CLAUDE_CODE_SESSION_ID`＋`project_transcript_dir()`
還原逐字稿路徑；`quota_halt_actions()` 落一份持久 halt 標記（`~/.autosdd/traces/
halt_<sid>.json`）並讓「未武裝」訊息依實際成因分流（不再對所有成因印同一句「拿不到
逐字稿路徑」）；`quota_messages.halt_verdict()` 把 halt 標記轉譯成既有 `arm_reset`／
`probe`／`escalate` 判決；`session_resume_planner.sentinel_decide()` 新增 `halt` 參數，
使哨兵認得自願停機（此前只認逐字稿裡的未復原 429 撞線）；`check_claim_provenance.py`
詞表加入「自動續跑」「會自動繼續」。新增回歸鎖 `tools/tests/test_wake_chain_halt_r278.py`
（18 test，+299）＋本檔自身逐檔漂移（新增主表列＋本軌列本身＋凍結前綴延伸 152→153，+13）。
證據見 `docs/06_quality/CrossPlatform_DEF200278_Halt_Handoff_Evidence.md`；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-278。
