# ADR-001: 本機優先 CI 平價層（Local-First CI Parity）

**日期**: 2026-06-11
**狀態**: Accepted
**決策者**: SD 架構師 + DevOps 整合專家 + 人類確認（wuweihung）

---

## 情境（Context）

上版到 GitHub 後 CI/CD 反覆紅燈。根因稽核（`gh run view --log-failed`）顯示**並非程式碼錯誤**：

1. **主因 — GitHub Actions artifact 儲存配額耗盡**：`fsm-chaos-nightly` 與
   `arch-fitness`(strict) 的測試本身通過（chaos `bounded=100/100`、arch
   advisory exit=1），卻在 `upload-artifact` 步驟 `Failed to CreateArtifact:
   Artifact storage quota has been hit` 而把整個 job 判紅。
2. **推送競爭**：`drift-daily` 與 `arch-fitness`(nightly) 同 cron(02:30) 且都
   `git push` 回 main，無 `concurrency` 護欄 → non-fast-forward 失敗。
3. **Node.js 20 退役**：checkout@v4 / setup-python@v5 / upload-artifact@v4 將於
   2026-06-16 強制改 Node24，為前瞻性風險。
4. **缺口**：push/PR **完全沒有** workflow 跑那 1473+ 離線測試套件，問題只能
   等 nightly 或上雲才暴露。

技術限制：本機為 Windows（vs 雲端 Linux），易有路徑 / 換行 / 大小寫 / bash·java
差異；本機已裝 Docker，且為高階工作站（充足 RAM）。

---

## 決策（Decision）

建立**「本機優先 CI 平價層」**：以單一閘門腳本 `scripts/ci-gate.sh` 為唯一真相源，
讓**地端與雲端跑同一組檢查**，並在 push 前於本機強制把關。四支柱：

1. **迷你正式環境（Docker）**：`docker/Dockerfile.ci`（python:3.11-slim + Java +
   tla2tools.jar）+ `docker-compose.yml` 的 `ci-runner`，鏡像 ubuntu-latest，跑
   `ci-gate.sh`，消除 Windows/Linux 差異。
2. **act 地端跑 Actions**：`.actrc` + `scripts/act-ci.sh`，用 Docker 在地端讀
   `.github/workflows/` 模擬雲端流程，抓 YAML / 步驟 / 相容性結構錯誤。
3. **Pre-commit / pre-push 攔截**：`.pre-commit-config.yaml` + 零相依
   `.githooks/pre-push`（`install-hooks` 設 `core.hooksPath`），push 前自動跑
   `ci-gate.sh`，本機過才能 push。
4. **Mock 與地端 LLM**：擴充 `llm_backend.py` 註冊表，新增 `MockBackend`（確定性
   零外連）與 `LocalOpenAIBackend`（Ollama/vLLM，OpenAI 相容 /v1，stdlib urllib，
   預設 OFF）；CI 預設 `session` 後端維持 hermetic。

同時硬化既有 workflow：upload-artifact 一律 `continue-on-error` + 降 retention；
兩個推送 job 共用 `main-push-serialize` concurrency + rebase-retry；action 版本
升至 Node24 相容；新增 `ci.yml` 在 push(main)/PR 跑離線閘門補缺口。

---

## 理由（Rationale）

1. **主要原因**：紅燈真因是 CI 基礎設施（配額 / 競爭 / 退役）而非邏輯；治本要把
   「可在本機重現的閘門」與「雲端不可靠的副作用（artifact/push）」解耦——前者本機
   強制跑、後者設為 best-effort 永不判紅。
2. **次要原因**：單一 `ci-gate.sh` 真相源避免「地端跑 A、雲端跑 B」漂移，達成
   「地端綠 ⇒ 雲端綠」。
3. **排除替代方案**：見下節。

---

## 後果（Consequences）

- **正面**：push 前本機即可發現問題；nightly 不再因配額假性紅燈；推送競爭消除；
  Node24 就緒；多模態可選地端 LLM 而不破 CI hermetic。
- **負面**：新增 root 層 dev 基礎設施檔（docker-compose / scripts / .githooks /
  .actrc）需維護；首次需 `scripts/install-hooks` 啟用 hook。
- **技術債務**：`continue-on-error` 會掩蓋真實 artifact 故障 → 以 Step Summary 補
  觀測；配額長期解需另排 artifact 清理（見後續行動）。
- **後續行動（Next Action）**：見章末「Next Action」。

---

## 替代方案評估（Alternatives Considered）

| 方案 | 優點 | 缺點 | 排除原因 |
|------|------|------|---------|
| 只刪 upload-artifact 步驟 | 最快止血 | 失去 chaos/fitness 可觀測產物 | 觀測性不該為配額犧牲；改 continue-on-error+降 retention |
| 只靠 act 驗證 | 免額外 Docker 檔 | act 不連 artifact 儲存，**抓不到本次真因**；GitHub 表達式/服務模擬有落差 | 不足以保證雲端綠，需 docker ci-runner 跑真實檢查 |
| 付費升 GitHub 儲存配額 | 無需改碼 | 治標不治本、成本、仍有推送競爭/Node20 | 不解結構問題 |
| 在 CI 安裝完整服務（DB 等）做 compose | 貼近教科書做法 | 本專案無前後端/DB，純 Python 框架 | 按實際技術棧裁剪：迷你環境 = Py3.11+Java |

---

## 相關文件

- 關聯規格：`AISDLC_SDD_v0.01/cicd/SDD_CICD_BASE_LAYER.md` §本機優先 CI 平價層
- 關聯 workflow：`.github/workflows/{ci,fsm-chaos-nightly,arch-fitness,drift-daily}.yml`
- 關聯模組：`AISDLC_SDD_v0.01/tools/fsm_runtime/modality/llm_backend.py`
- 關聯規則：CLAUDE.md Rule 9.9.4（chaos nightly）/ Rule 9.17.4（drift dogfood）/
  R-9.36·R-9.37（meta-loop 外聯限制；本層地端 LLM 為 opt-in、未接 meta-loop，無涉）

---

## Next Action

1. ✅ **artifact 配額治本（已落地）**：新增 `.github/workflows/artifact-cleanup.yml`
   ——每日 03:00 UTC + workflow_dispatch，用 gh CLI（actions:write）刪除 expired/逾齡
   artifact（預設 > 7 天，對齊 retention）。首次可手動 `gh workflow run
   artifact-cleanup.yml` 立即清掉既有累積、解除配額。
2. ⏳ **branch protection（待 repo admin 手動）**：將 `ci / offline-gate` 設為 main 的
   required status check（讓雲端閘門與本機 pre-push 雙層強制）。GITHUB_TOKEN 無 admin
   scope，無法由 workflow 自動設定，須在 repo Settings → Branches 手動啟用。
3. **act 全 workflow 煙霧測試**：定期 `act -W .github/workflows/ci.yml` 驗證 YAML。

**存放位置**: `docs/02_architecture/adr/ADR-001-local-first-ci-parity.md`
