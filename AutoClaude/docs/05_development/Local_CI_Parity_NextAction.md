# Local CI Parity — 交付驗證 + 複審 + Next Action

**日期**：2026-06-11 | **狀態**：✅ 完成（OVERALL PASS）| **指南**：[Local_CI_Parity_Guide.md](../08_deployment/Local_CI_Parity_Guide.md)

## 1. 目標
根本解決「push 到 GitHub 才發現 CI/CD 紅燈」：把 CI 把關前移本機，善用 Docker 在 Linux 容器重現雲端流程，**本機全綠才 push**。

## 2. 交付物（四大需求對照）

| 需求 | 交付物 | 驗證證據 |
|------|--------|----------|
| 一 迷你正式環境 | `docker-compose.ci.yml`（pg17 對齊 CI）| `docker compose config` VALID；逐欄位 == ci.yml service |
| 二 act 跑 Actions | `.actrc` + `tools/run_act.ps1` | `act -l` 解析 9 job；**`act push -j test` Job succeeded（2558 passed）** |
| 三 pre-commit hooks | `tools/git-hooks/{pre-commit,pre-push}` + `install_git_hooks.ps1` + `.pre-commit-config.yaml` | pre-commit 實跑 exit=0；LF/SSOT 達標 |
| 四 高擬真 mock+LLM | `tools/mock_brain_server.py` + `docker-compose.llm.yml` + 契約測試 | 契約對齊 minimax_client；測試 6 passed |
| 統整入口 | `tools/local_ci_gate.ps1` | 一鍵鏡像 ci.yml push jobs |

## 3. 審查—修復閉環（zero-trust）

**首輪獨立審查**（Architect/SA/SD/QA 整合專家）：**OVERALL PASS（0 P0 / 0 P1 / 4 P2）**。

**act 真跑揭露 1 個假陽性**（本機制核心價值體現）：
- `test_minimax_missing_api_key` 在 Linux 容器 DID NOT RAISE。根因：**act 預設載入 repo `.env`（含真實 MINIMAX_API_KEY）→ 容器內 key 非空 → 該測試（預期 key 缺）失效**。真實 GitHub CI 無 `.env` 故會過。
- 雙修：(a) `run_act.ps1` 傳空 `--env-file` 阻止 act 載入 `.env`（忠實對齊 CI + 不洩漏金鑰）；(b) 測試加 `monkeypatch.delenv("MINIMAX_API_KEY")` 變 hermetic（取證紀律 #16）。

**4 個 P2 全數修復**：
1. `mock_brain_server.py` 非 UTF-8 body → 回 400（非 500）+ 補單元測試。
2. `local_ci_gate.ps1 -Pg` 改全程 asyncpg DSN（對齊 CI；env.py 自動 strip）。
3. `local_ci_gate.ps1 -Pg` 改 `docker compose up -d --wait`（取代固定 sleep）。
4. Guide「act 已安裝」→「需安裝 act + 安裝指引」。

**過程修掉 2 個 Windows 真 bug**：3 個 .ps1 編碼 no-BOM → PS5.1 cp950 誤讀 parse 失敗（已轉 UTF-8 BOM）；hooks/文件 `pwsh`（本機僅 PS5.1）→ `powershell`。

## 4. 複審：符合原設計功能

- 全量 Windows pytest：**2732 passed / 122 skipped**（baseline 2726 + 6 新 mock 測試，零回歸）。
- act Linux CI `test` job：**Job succeeded, EXIT=0**（pytest 2558 + LOC budget + import-linter 全綠）。
- 全檔編碼掃描：3 ps1 UTF-8 BOM、其餘 LF/no-BOM —— **ALL-ENCODING-OK**（取證紀律 #8）。
- 架構：run_act 只跑 push gating jobs、nightly 由 `if: schedule` 正確排除；docker-compose.ci(pg17)/主 compose(pg18) 差異標註處理非新漂移；mock 契約實證對齊。
- **結論：符合原設計，PASS。**

## 4b. 上版結果（2026-06-11）
- Tag `v2026.06.11-01`；commit `5f1b22b`（feature）→ `00b467f`（merge main）；已 push `wuweihungmobile/AutoClaude`（sprint + main + tag）。
- **GitHub CI（push run 27350225400）整體 conclusion = `success`**：Tests+LOC ✓ / CLAUDE.md+Snapshot ✓ / Equivalence ✓；nightly job 由 `if: schedule` 排除。
- **本機 act 預測綠 → 雲端實測綠**，機制端到端驗證成功。
- PG Contract job 在 GitHub 為 `X`，但 ci.yml:138 標 `continue-on-error: true`（R56 已知 deferred-track，**非阻塞**，不影響 run success）→ 見 §5 SD_10 backlog。

## 5. Next Action（後續事項）

**首次設定（使用者需各做一次）**：
1. `powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1`（啟用 commit/push 自動把關）。
2. 首次 `tools/run_act.ps1` 會 `docker pull` runner 鏡像（約 1~1.5GB）。

**SD_10 backlog（非阻塞）**：
- `local_ci_gate.ps1 -Pg` 的 pg-contract 真跑未在本輪驗證（CI 本就標 `continue-on-error`，含 R56 已知 schema/fixture 待 PG-track 正式重構）；待 SD_10 PG-track 一併驗。
- `docker-compose.llm.yml` 的 vLLM `--profile llm` 真模型路徑需 GPU + 下載 Qwen 權重，本輪僅驗 mock profile；真模型/GGUF（llama.cpp）待有 GPU 環境時驗收。
- act `push` 完整圖（含 pg-contract service）端到端真跑可選驗（本輪已驗 `-j test` 主閘門全綠）。
