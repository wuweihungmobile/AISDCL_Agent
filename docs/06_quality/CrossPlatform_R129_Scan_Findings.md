# CrossPlatform R129 — 護欄層對帳與重釘逐檔清單（喚醒鏈零浪費收尾單人窗口）

- **輪籤**：R129（2026-09-06，macOS；收尾單人窗口＝護欄線棘輪＋指紋基線重釘）
- **體例**：不使用前瞻輪號句型；所有數字皆本 session 親跑（`--print-guard-lines`）。

---

## §1 護欄層淨額承認

<!-- guard-total:R129 --> 本輪護欄層行數 `92268→93610`（淨額 +1342）。

四個包新增 +1300 行回歸鎖（喚醒鏈零浪費 INV1~5／FIX1~4 ＋ T-f4b 洩漏止血），逐檔漂移兩支：

- `DIFF test_context_budget_guard.py 9860 → 11057 (+1197)`
- `DIFF test_mac_endurance_r83.py 1784 → 1887 (+103)`

本檔自身 `test_adr_xplat001_c1c2_lock.py 7298 → 7340 (+42)`＝R129 稽核列
＋ `_REPIN_APPROVED_ROUND_OVERAGE` 名冊列 ＋ `_REPIN_NET_CAP_SCHEDULE` 兌現列 `(129,552)`
＋ DUE 重新武裝 ＋ `_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列 ＋ `_PHASE2_REVIEW_LOG` 的 `[提案]` 列
＋ `_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES` 上修 ＋ 凍結前綴延伸。

## §2 款(10)(11)(12) 與 Phase 2 時效的處置

- **款(10)**：淨額 +1342 遠超單輪上限（`net_cap_for_round(129)=552`）⇒ 走 DEF-200-208 一次性
  例外名冊（`_REPIN_APPROVED_ROUND_OVERAGE` 的 R129 那一列，主控本 session 核准，精確淨額逐字
  對上）。名冊上限同步由 1 上修為 2：R101（cap 收斂）永久留在真表、R129 另占一格；`test_the_
  registry_stays_a_one_time_exception` 的設計即「多一筆先讓斷言失敗、逼一次可見決策」。
- **款(11)**：前一輪 R127 淨額 −38 已斷連續上升 streak，R129 未觸發。
- **款(12)**：同輪兌現到期義務 `(129,552)`（cap 555→552）並重新武裝 131／550（步伐 2<3）。
- **Phase 2 §6 時效**（ADR-XPLAT-012 條文五）：R129 越過到期輪 R127、`[維持觀察]` 名額（上限
  一次、有 frozen 孿生鎖）已由 R122 用罄 ⇒ §6 僅剩 `[提案]`／`[落地]` 兩條合法出路。方向 (c)
  依 D-4 裁決仍為觀測欄、其觀測資料（`guard_line_composition()` 末行）已累積逾十輪，故於
  `_PHASE2_REVIEW_LOG` 記一列 `[提案]`（觀測→阻斷的轉換決定送四方複審，複審由主控承接、
  非本收尾窗口執行；同 R113 `[提案]` 由 DEF-200-211 承接的體例）。連續計數歸零。

## §3 指紋鏈與基線

- `_REPIN_LOG_FROZEN_PREFIX_LEN` 117→118；`_REPIN_LOG_HISTORY_SHA256` 前進至
  `1bff7d5bf52e…`；`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 `("R129", a4b92fe15365→1bff7d5bf52e,
  DEF-200-266)`。指紋鏈首尾相接、DEF-ID 在帳本家族內存在。
- ONBOARDING 指紋基線由 `tools/sync_onboarding_baselines.py --write` 回填（四棵測試樹改動使
  `test_doc_loc_baseline_freshness_r60` 指紋漂移）。

## §4 載體歸屬

- 護欄層重釘（`_FROZEN_GUARD_LINES` 三支值＋稽核痕跡＋代價常數）＝DEF-200-266（喚醒鏈零浪費）。
- 逐檔行數與對帳一律現查 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
