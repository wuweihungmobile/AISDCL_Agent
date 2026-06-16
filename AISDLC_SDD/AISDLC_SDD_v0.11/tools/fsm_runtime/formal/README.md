# SDD FSM Formal Verification (Phase G M5 / ACT-041~042)

形式化驗證 SDD FSM 的「bounded halting」性質 — 用 TLA+/TLC 給 Chaos 100 輪經驗驗證一個數學上的憑證。對應規劃文件 §M5、CLAUDE.md Rule 9.18。

## 目錄結構

```
formal/
├── README.md              ← 本文件（環境準備 + 使用方式）
├── SDD_FSM.tla            ← FSM 規格（state + Init + Next + 不變量）
├── SDD_FSM.cfg            ← TLC 配置（探索深度、變數空間）
├── run_tlc.sh             ← Linux/macOS 執行入口（CI 用）
├── run_tlc.ps1            ← Windows 執行入口（本機開發用）
└── lib/                   ← TLC jar 安裝位置（gitignore，不 commit）
    └── tla2tools.jar      ← 由 install helper 自動下載
```

## 環境需求（B5.1 — A3.1 / OPEN-G.5 結論：採 TLC CLI）

| 元件 | 版本 | 用途 |
|------|------|------|
| Java | ≥ 11（已測 OpenJDK 21）| TLC tool 執行環境 |
| TLC（tla2tools.jar）| ≥ 1.8.0 | TLA+ Model Checker |

## 安裝 TLC

### 自動安裝（推薦）

`run_tlc.sh` / `run_tlc.ps1` 會在 `lib/tla2tools.jar` 不存在時自動下載：

```bash
# Linux/macOS (CI)
bash tools/fsm_runtime/formal/run_tlc.sh --install-only

# Windows (本機)
pwsh tools/fsm_runtime/formal/run_tlc.ps1 -InstallOnly
```

下載來源：`https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar`
SHA256：腳本驗證；不符合即 abort。

### 手動安裝

從 [TLA+ Releases](https://github.com/tlaplus/tlaplus/releases) 下載 `tla2tools.jar`，置於 `tools/fsm_runtime/formal/lib/`。

## 執行驗證

```bash
# Linux/macOS
bash tools/fsm_runtime/formal/run_tlc.sh

# Windows
pwsh tools/fsm_runtime/formal/run_tlc.ps1
```

## CI 整合

CI step 定義於 [`cicd/SDD_CICD_BASE_LAYER.md` §FSM Formal Verification](../../../cicd/SDD_CICD_BASE_LAYER.md)，每次 PR 對 `transition_rules.py` / `*.tla` 修改時自動跑；fail 即 block。

## 與 Chaos Runner 的關係

| 項目 | Chaos Runner（Phase E M2.5）| TLC（Phase G M5）|
|------|----------------------------|------------------|
| 驗證方式 | 100 輪隨機故障注入 | 全 reachable state 窮舉 |
| 保證強度 | 經驗性（probabilistic）| 數學性（exhaustive）|
| 失敗後果 | bounded_ratio < 1 fail | deadlock / invariant violation fail |
| 運行成本 | < 30s | 10~120s（depth 50）|

兩者互補 — Chaos 抓「實際 runtime + IO 故障」，TLC 抓「狀態圖結構錯誤」。

## 相關規則

- **CLAUDE.md Rule 9.18.1** — 每次 `_HAPPY_PATH` 變更必須同步更新 `SDD_FSM.tla`
- **CLAUDE.md Rule 9.18.2** — TLC deadlock 或 invariant violation 即 fail PR
- **CLAUDE.md Rule 9.18.3** — reachable / total ≥ 95% 才能宣稱 L5
- **CLAUDE.md Rule 9.18.4** — 觀測狀態（PRODUCTION_SIGNAL / HUB_SYNC / LEARNING_COMMIT / TRAJECTORY_PREDICTED / AUTO_RECOVERY_ATTEMPT）必須為 transient（不能成為穩定態）
