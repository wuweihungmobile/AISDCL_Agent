# CrossPlatform R131 — 喚醒鏈四方審計對抗查證與破洞修復收尾 round-label-ok

- **輪籤**：R131（2026-09-07，macOS；收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R130（M-01／M-05 死碼修復＋四方審計撿回 22 筆撿回稿，見
  `CrossPlatform_R130_FourParty_Salvage.md`）。該稿承認「對抗證偽未跑（撞上限）」——
  本輪補做這一步。

---

## §1 護欄層淨額承認

<!-- guard-total:R131 --> 本輪護欄層行數 93734→94239（淨額 +505）。

四方審計撿回 22 筆裡與「主 agent 沒起來就不該浪費 token」三大問題最相關的一批發現，
派 24 個小幫手（每項各兩位互不見面獨立重查）對抗查證：10 項兩人判斷一致（其中兩項
判 `fixed`＝M-01／M-05，此前已修；其餘一致判 `confirmed_open`），2 項意見不合
（M-19／M-20，當「還沒修好」處理）。確認仍是破洞的一批本輪逐一修復並經主控獨立重跑
驗證（非僅信任執行者回報），新增回歸鎖：

- `DIFF test_context_budget_guard.py 11169 → 11628 (+459)`：
  - M-06：INV2 第一窗機械擋 fan-out 工具（新姿態檔 `.claude/settings.
    unattended_first_window.json` ＋ `posture_settings_path()` 接線測試）。
  - M-07：INV5 假後端尊重 `prefix` 參數＋跨族命名辨識測試。
  - M-13：INV5 owner 檢查下沉到 `_register_and_record` 共同漏斗＋`--register-schtasks`
    CLI 分支補站的端到端測試。
  - M-15：INV4 `settle_window`→`no_progress_limit()` 端到端測試（env 放寬下仍第一窗即停）。
  - M-16：`--pace` 真子行程 CLI 驗證（`subprocess.run`，非同進程 `patch.object`）。
  - M-20：`InvariantLocksArePresentTest`——INV1~5／FIX 測試類別存在性與方法數下限清單。
  - M-19：`[WINDOWS-NATIVE-ONLY]` 真機測試（INV5 `list_jobs` 消費，mac 上正確 skip，
    待下次 windows-latest CI 真跑時第一次真的執行）。
  - 修復過程中順帶發現並修正一個連帶洞：`_run_resume` 的 A-PRE 預檢原本恆讀
    `UNATTENDED_SETTINGS`，與 argv 實際可能已改用的第一窗姿態檔脫鉤——已同步改讀
    `resume_route.posture_settings_path(allow_followup=…)`。
- `DIFF test_run_root_unittests.py 2428 → 2451 (+23)`：M-03，`sentinel_lifecycle.
  leak_fence()` 接進 `main()` 的 AST 接線鎖（`test_main_is_wrapped_by_the_leak_fence`）。
- `DIFF test_adr_xplat001_c1c2_lock.py 7352 → 7361 (+9)`：R131 稽核列本身（同 R130 判例）。

## §2 U9 root-tools 舊尺債 — 本輪未涉及

本輪未觸碰 root-tools 舊尺債持有面，無需處置。

## §3 淨額合規

- 淨額 +491 ≤ `net_cap_for_round(131)`＝550（到期輪兌現 `(131, 550)`；`_REPIN_NET_CAP_DUE_ROUND`
  原訂 131，本輪剛好到期兌現，同輪重新武裝下一段：`_REPIN_NET_CAP_DUE_ROUND=133`／
  `_REPIN_NET_CAP_DUE_TARGET=549`，步伐 1 < 前一段的 2）。
- 連升 streak 第 2／2（前輪 R130 為第 1／2，R129＝approved-overage 不計入款(11)；
  下一輪起須淨額 ≤0 或另申請一次性核准）。
- 指紋鏈：`_REPIN_LOG_HISTORY_SHA256` 前進至 `a25e7cb62391…`；`_FROZEN_PREFIX_REWRITE_LEDGER`
  追加 `("R131","79ab4a9a386e","a25e7cb62391","DEF-200-272")`（載體＝四方審計撿回同家族）。

## §4 修法逐筆

- 逐檔行數與對帳一律現查 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
- 對抗查證的完整過程（24 位小幫手逐項 verdict）與修復逐項的紅綠指令、獨立重跑證據，
  見 `docs/06_quality/WakeChain_IronLaws_Verification.md`。
- 22 筆撿回稿全貌（含本輪未涉及的 M-02／M-04／M-08／M-09～M-12／M-14／M-17／M-18／
  M-21／M-22）見 `docs/06_quality/CrossPlatform_R130_FourParty_Salvage.md`；本輪未觸碰
  項目現況一律沿用該檔原始記載，未經本輪覆核。
- 缺陷帳本更新見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-272。
