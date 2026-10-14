# 文件回寫清單（主控累積；收尾時由一位 Sonnet「文件同步」agent 一次套用，或主控親改）

## Architecture.md
- §10 Bridge 契約：以 `AgentConsole/engine-bridge/README.md` 為準，補「落地差異」16 條（狀態前置條件 409 invalid_state；run_exists／run_not_found／checkpoint_not_found／lock_backend_unavailable／spawn_failed／sdd_unavailable／fsm_not_found／fsm_state_unreadable；422 兩種形狀與 rule 清單；GET run 補充欄位；events 裸陣列；SSE retry/keep-alive/游標/PAUSED 不結束/事件欄位語意；ID 皆 UUID、step_number＝SSE seq；config_overrides 白名單與 secret_in_config；Bridge 管控鍵一律忽略＋CONFIG_OVERRIDE_IGNORED；env 名稱限制與 forbidden_name、值走外呼白名單、不落盤、ENV_LOST；playbook extra=forbid；鎖 normcase+NFC、PAUSED 持鎖、restore 重取；decompose gate 對照與 approve 冪等/409；/sdd/fsm 與 /sdd/compile 回應欄位與錯誤 reason；/health 補充欄位；啟動回收規則；psutil 相依）。
- §8.4 SEC-04：誠實劃界——Bridge 只做精確 host 白名單＋URL 解析一致性＋拒絕 userinfo/反斜線/IDN/十進位十六進位 IP＋私網 IP 除非明列；**DNS 解析後驗 IP 與釘住連線 IP 沒做**（外呼由引擎行程自己解析，Bridge 釘不住）；decompose 的 httpx 不跟 redirect。
- §11.4：`autoclaude.dalBackend → storage.mode` 對映**不生效**（Bridge 固定 yaml_only）；「以 config_overrides 指 checkpoint_dir／log_dir」不採用（落點由 Bridge 決定，`workspace` 欄位回報）。
- §12：補 L-9「`/sdd/compile` 底層 adapter 向上找 FSM 狀態檔取字母序第一個 `FSM-STATE-*.yaml`，與 project 無關」（AutoClaude 既有行為，另案）。
- §2／§9：Bridge 映像 uid 10001；`/sdd` 整棵掛載＋`SDD_ROOT=/sdd`；`ENGINE_WORKSPACE=/workspace` named volume；`BRIDGE_OUTBOUND_ALLOWLIST` 全棧不含 loopback；單 worker。
- E2E 替身：全文把 dummy_cli 改為 `aisdlc-mock-claude`（config_overrides.claude.command）。

## ADR-001
- D8 加註：步驟邊界訊號＝引擎 stdout 三種行；pause 會終止剛 spawn 的下一步、resume 重做（at-least-once）。
- 新 D17：E2E Claude 替身＝`aisdlc-mock-claude`（原因：`claude.command` 不切分字串、`PlaybookTask.command` 零消費）。
- 新 D18（待 Phase 3 決定）：BRD/PRD 解析雙路徑的落地——frozen SDD spec → `/sdd/compile`；自由文件 → 後端呼叫 OpenAI 相容 chat completions（§5.2.4 prompt）產 3 層 JSON，三道有界閘在後端重現；引擎 GoalDecomposer 經 Bridge `/autoclaude/decompose` 保留給「短句高階目標」入口（UI「貼上文字」且長度 < 2,000 字時）。
- 證據欄 E-1～E-5 回填：Spring Boot 4.1.1（start.spring.io 現查，骨架 build.gradle.kts）、Next.js 16.4.0（npm registry 現查）、python:3.11-slim 已可拉。

## RTM.md
- BR-* 列：狀態改為 ✅（實作＋測試），實作檔＝engine-bridge/app/…、測試＝tests/…；新增 BR 列：`/autoclaude/runs/{id}/events`、`:approve`、錯誤碼族。
- 「GET /autoclaude/runs 清單」若 RTM 有列 → 標「契約未含，Phase 4 視需要補」。

## Implementation_Plan.md
- 進度帳：W1-A ✅（Architect）、W1-B ✅（Bridge：235 passed／9 skipped 無 DB；244 含 DB；slim 映像由主控補建）、W2-A／W2-B 依其交卷填。
- D-1（dummy_cli 授權提示）作廢：替身已換成 aisdlc-mock-claude。

## 主控補驗（2026-10-14 深夜）
- Bridge slim 映像：主控以字面指令 `docker build -f AgentConsole/engine-bridge/Dockerfile -t … .` 建置 rc=0；`docker run -v AISDLC_SDD:/sdd:ro -e SDD_ROOT=/sdd` 後 `/health` 回 `engines.autoclaude.ok=true`、`engines.sdd.ok=true latest=AISDLC_SDD_v0.30`；容器與映像已移除。Plan 進度帳 W1-B 可寫「slim 映像已由主控驗證」。
- Bridge pytest 主控親跑：`ruff All checks passed!`、`235 passed, 9 skipped in 25.67s`（無 DB，-n 4）。

## 套用狀態（主控 2026-10-15）
- Architecture §10／§8.4／§11.4：已以「主控回寫」blockquote 註記（指向 engine-bridge/README.md 為 SSOT）；逐條重寫 §10 全文留給 Windows 輪的文件同步 agent。
- ADR-001：已補記 D17／D18 與主控親驗紀錄。
- RTM：各開發者已回填；Plan §5.2 快照已填。
- Implementation_Plan：W1～W3 列、§5.3 三項裁決已填。
- `.env.example`：補 MINIO_ROOT_USER ≠ AWS_ACCESS_KEY_ID 註解（主控驗證時踩到）。
