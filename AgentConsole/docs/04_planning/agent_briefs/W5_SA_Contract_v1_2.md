# 任務書 W5-SA：契約 v1.2（API_Contract_P3-6.md ＋ openapi-p3-6.yaml）、ADR-001 與 Architecture 同步

> 先讀 `W5_OVERVIEW.md`（全貌、裁決 C-1～C-22、持有面）。你是 SA／SD：只改文件，不寫程式、不改測試、不 commit。你的交卷是 BE／FE／INFRA 三棒的開工前提，先做 C-1～C-12 的端點條目（FE 要從 YAML 重產型別），再做漂移回寫與 ADR。

## 必讀

1. `docs/02_architecture/API_Contract_P3-6.md` v1.1 全文（§0 權威順位、§1 端點、§2 SSE、§3 Bridge 對映、§4 設計稿缺口、§5 E2E 情境、§6 差異與裁決）與 `openapi-p3-6.yaml`。
2. `docs/06_quality/QA_P3-6_E2E_Verification.md` §1、§11（缺陷）、§13（與設計稿差異）、§14（W5 建議）、§11 末的觀察表 O-01～O-21。
3. `docs/04_planning/agent_briefs/W4_QA_E2E.md`〈契約漂移裁決〉（第 56～60 行）。
4. 四份開發者交卷（scratchpad，唯讀）：`C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\6121f0db-8785-4286-9143-5c37c2fc9496\scratchpad\f1_handoff.md`、`b1_handoff.md`、`f2_handoff.md`、`b2_handoff.md`——各自的〈契約漂移〉節（B2 六條只在 `b2_handoff.md`）。
5. 現行實作是事實來源（契約以實作為準回寫時要對程式）：`backend/src/main/java/com/aisdlc/console/adapter/in/web/**`（controller／dto）、`frontend/lib/api/*.ts`、`engine-bridge/app/**`。

## 範圍（依序）

1. **版本與變更記錄**：契約標頭改 v1.2（日期 2026-10-15），§6 加「6.5 v1.2 變更一覽」表：每條對應 C-x／DEF-AC-x／O-x、改了哪一節。
2. **新端點與改動條目**（契約正文＋YAML 同步，YAML 的 schema／範例／錯誤碼都要有）：C-1 `GET /monitor/task-totals`（放 §1.3 新小節 1.3.x，並改寫 §4.6 G-G3 與 §6.3 第 9 項為「v1.2 已補」）；C-2 Bridge `GET /health/deep`（§3 Bridge 契約處；原 `/health` 條目不動）；C-3 `POST /projects/{id}/restore` 與 `GET /projects?deleted=true`、retention 屬性、新 reason 常數 `project_not_deleted`／`restore_window_expired`；C-4 PDF 報表改 200（§1.3 report 條目；`PDF_NOT_AVAILABLE` 常數退役，§0.3 一併整理）；C-5 §2.8 客戶端流程改寫「換新失敗三類」與 SSE 退避；C-6 §1.5.10 的 skipped 判準與順序；C-7 §3.7 去重鍵；C-8 目標／任務刪除的 409 `project_executing`（§1 對應刪除條目與 §0.3）；C-9 手動重試明文（§1.2 retry 條目）；C-10 §1.1.9 回 `warnings[]`／`parseOptions`、§0.5 Flyway V8；C-11 §1.2.2 列表項 `bridgeStatus`；C-12 `X-Trace-Id` 貫穿（§0.4 與 §3 Bridge 請求標頭、Bridge 回應標頭、日誌欄位）。
3. **漂移回寫**（C-21、C-22）：逐條把 B1-1～B1-9、F1-3～F1-6、F2-1／F2-2／F2-5／F2-6、B2 六條寫進對應正文（不是只記在 §6.3）；§6.2 表每列改「已回寫（v1.2 §x.y）」；§3.7 補 O-15 觸發路徑說明。
4. **ADR-001**：§4 偏離 PRD 清單與 §5 加 G-20（C-13 KPI 環形→數值卡）；§3 若需要加 D19「軟刪除保留期與清除排程預設關閉」（C-3）。`Architecture.md`：若有端點地圖／資料所有權表（§7、§10），補 task-totals、restore、`/health/deep`、import_records 兩欄、traceId 貫穿；其餘不動。
5. **C-14**：契約 §4.3 M-12 補一句「追蹤鏈視圖以批次下拉＋事件時間軸＋日誌查詢涵蓋（主控裁決 2026-10-15）」。

## 一致性要求

- 契約 MD 與 YAML 不得矛盾：每個新端點兩邊都有、欄位名與型別相同、角色與錯誤碼相同。
- YAML 必須能被 openapi-typescript 讀：在 scratchpad 跑 `npx --prefix D:\CursorProject\AISDCL_Agent\AgentConsole\frontend openapi-typescript <YAML 絕對路徑> -o <scratchpad>\types.check.ts`，rc=0 才算（前端實際重產由 FE 棒做；你不碰 `frontend/`）。
- 不改既有端點的語意，除非裁決表要求；以實作為準回寫時逐條附「對應程式位置」（檔名＋符號）。
- 繁體中文；測試計數不寫「N passed」字樣；LF。

## 交卷

依 `W5_OVERVIEW.md` §5 格式；〈給 QA 的提醒〉列出 v1.2 新增的 E2E 情境建議（至少：task-totals 與各專案 task-trend 加總相等、restore 的三種 409／404、PDF 下載、refresh 502 不登出、import 原樣匯入 0 errors、escalation 跨批次不被吞）。
