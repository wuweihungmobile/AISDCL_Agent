# RTM - WebhookSender（TD-1：ESCALATION 的 Webhook 發送）

**版本**: 1.0（整合輪 116 W3 QA 建立；依 `AISDLC_SDD:rtm-generate` 表格形，路徑依 D-116-09 落 `docs/06_quality/`）
**日期**: 2026-10-18
**狀態**: In Review（SCG-4 一審有 P2：F-01，見 `SCG4-REVIEW-WebhookSender-20261018.md`；RTM 覆蓋已達 100%，`RTM_VERIFY` 閘門待二審通過後執行）
**覆蓋率**: 6/6 AC（100%）；AT 9/9
**規格**: `AutoClaude/docs/03_testing/contracts/TCS-WebhookSender-20261018.md`（凍結摘要 `sha256:2d473454d33d46fa341566a6f4cea25d135ce3a7a22dd0acce1d41f1bfcec8cf`）
**實作**: commit `306dbb2a`（`autoclaude/utils/webhook_sender.py`、`autoclaude/utils/notifier.py`、`tests/utils/test_webhook_sender.py`）；引擎根因修復 `d9dc1ff0`（DEF-200-550）

## 追溯矩陣

| EPIC | Feature | User Story | AC | Test Case（`tests/utils/test_webhook_sender.py::`） | API | NFR | 狀態 |
|------|---------|-----------|-----|---------------------------------------------------|-----|-----|------|
| EPIC-001（TD-1：ESCALATION 離機告警；來源 `Phase6_P1_Backlog.md` §5） | F-001 | US-001 | AC-001-1 | AT-001-1-1 → `test_AT_001_1_1_success_posts_json` | － | NFR-001-3、-4、-5、-6 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-2 | AT-001-2-1 → `test_AT_001_2_1_non_https_urls_are_never_sent` | － | NFR-001-1 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-3 | AT-001-3-1 → `test_AT_001_3_1_retries_then_succeeds_with_backoff` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-3 | AT-001-3-2 → `test_AT_001_3_2_exhausts_attempts_and_reports_last_result` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-3 | AT-001-3-E-1 → `test_AT_001_3_E_1_non_retryable_statuses_stop_after_one_attempt` | － | NFR-001-3 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-4 | AT-001-4-E-1 → `test_AT_001_4_E_1_never_raises_on_bad_input` | － | NFR-001-1 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-5 | AT-001-5-1 → `test_AT_001_5_1_logs_only_the_masked_url` | － | NFR-001-4 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-6 | AT-001-6-1 → `test_AT_001_6_1_notify_escalation_posts_via_send_webhook` | － | NFR-001-7 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-6 | AT-001-6-2 → `test_AT_001_6_2_no_webhook_url_keeps_behaviour_unchanged` | － | NFR-001-7 | ✅ |

## 覆蓋率統計

| 指標 | 數值 |
|------|------|
| 總 Feature 數 | 1 |
| 總 AC 數 | 6 |
| 有 TC 的 AC 數 | 6 |
| **覆蓋率** | **100%** |
| SCG-5 目標 | 100% |
| 引擎 RTM（`RTM-COVERAGE-autoclaude-webhook.yaml`，run `4e6bd6c9-5655-4aec-9294-a6674ead055a`） | AT 9／9、AC 6／6、`fully_covered: true`、`unmapped_at_ids: []` |
| 實跑（2026-10-18，當回合） | 整檔 9 支通過；AutoClaude 全套 5889 通過、7 略過；行覆蓋 100%、分支覆蓋 100%（隔離環境量測） |

## R 條文 → AT 對映（TCS NFR-001-8 要求的逐條核對；當回合讀碼與測試逐條確認）

| R | 內容 | 觸及它的 AT |
|---|------|------------|
| R1 | 位址驗證 | AT-001-2-1 |
| R2、R3 | payload 與參數驗證 | AT-001-4-E-1 |
| R4、R5 | 發送與結果分類 | AT-001-1-1、AT-001-3-E-1 |
| R6、R7 | 重試退避與終局結果 | AT-001-3-1、AT-001-3-2 |
| R8 | 永不拋例外 | AT-001-4-E-1 |
| R9 | 日誌遮罩 | AT-001-5-1 |
| R10、R11 | 接線呼叫與接線日誌 | AT-001-6-1 |
| R12 | 空位址不變 | AT-001-6-2 |

## NFR 追溯

| NFR | 驗證結果（當回合） |
|-----|------------------|
| NFR-001-1 | 只 import 標準庫與 httpx；lint-imports 9 kept、0 broken |
| NFR-001-2 | 模組 135 行（≤ 200）；`check_loc_budget.py --json` rc 0 |
| NFR-001-3 | 整檔單跑 1.80 秒（< 5 秒） |
| NFR-001-4 | 測試只經 `httpx.MockTransport`；grep 無 `httpx.get`／socket／`time.sleep` |
| NFR-001-5 | ruff 三檔 All checks passed |
| NFR-001-6 | 無 skip／xfail／平台分支；`read_text` 帶 encoding；假 URL 皆 example.com 子網域 |
| NFR-001-7 | AutoClaude 全套 rc 0（含既有 notifier 與 notification 測試） |
| NFR-001-8 | 覆蓋率 100%（≥ 80%）；R↔AT 對映如上 |
| NFR-001-9 | 引擎評估環境：建批次請求層 `env` 帶 `AUTOCLAUDE_NO_PG_AUTODETECT=1`；九步評估各 rc 0 |
| NFR-001-10 | `git show --stat 306dbb2a` 恰三檔；樹下限重釘（241→242）由主控於 `d9dc1ff0` 完成 |

## 備註

- **測試強度缺口（SCG-4 F-01，P2）**：下列行為在 TCS 的 R 條文中明文要求、但現有測試不會因其被改壞而轉紅（記憶體內突變檢驗存活）：R4 四階段逾時、R3 驗證順序 R1→R2→R3、R9 終局 WARNING 含 `attempts`、R9 的 `invalid_payload` 與 `invalid_argument` 路徑日誌不含 payload 與 URL、R10 時間戳為 UTC、R10 先寫 alert log 再呼叫、R3 `timeout_s` 接受 int、`WebhookResult` 欄位順序。補強限於在既有測試追加斷言，不改 TCS。
- 引擎層 TOKEN_HALT 偽陽性（DEF-200-550）已於 `d9dc1ff0` 修復；Bridge StepTracker 遮罩漏配（DEF-AC-038，P3）不影響本 RTM。
- 狀態欄 ✅＝測試實跑為綠；整體仍待 SCG-4 二審通過後才算閉環。
