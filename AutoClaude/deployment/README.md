# AutoClaude 部署指南

對應 [SD_Improving_05.md v1.2](../docs/04_planning/SD_Improving_05.md) §10 + SD_Improving_06（規劃中）。

---

## 1. 部署形態

| Phase | 範圍 | AutoClaude 主程式 | PostgreSQL | BGE-M3 Embedder |
|-------|------|-------------------|------------|-----------------|
| **目前（SD_05）** | 混合模式 | host process | Docker（pgvector/pgvector:pg16） | Docker（TEI BGE-M3） |
| 未來（SD_07） | 全容器化 | Docker（含 UI） | Docker | Docker |

**為何混合模式**：AutoClaude 主程式需呼叫 host 上的 `claude` CLI、操作 git、註冊 ESC+F12 全域熱鍵 → 容器化會破壞這些 host 整合。SD_07 將以 UI 中斷按鈕（`IInterruptSource` port）取代 ESC+F12，屆時可全容器化。

---

## 2. 前置需求

| 項目 | 版本 | 說明 |
|------|------|------|
| Docker Engine | ≥ 24.0 | Windows 用 Docker Desktop |
| Docker Compose | v2（內建） | `docker compose` 而非 `docker-compose` |
| NVIDIA GPU | Compute Capability ≥ 7.0 | RTX 4060 Ti 16GB ✅ |
| nvidia-container-toolkit | 最新 | TEI GPU passthrough 必需；Windows 走 WSL2 + NVIDIA Container Toolkit |
| 磁碟空間 | ≥ 10 GB | pgvector image ~400 MB / TEI image ~2 GB / BGE-M3 model ~2 GB / pg_data 視資料量 |

---

## 3. 啟動步驟

```bash
# 1. 複製環境變數範本並填入真實憑證
cp .env.example .env
# 編輯 .env：填入 MINIMAX_API_KEY 等

# 2. 啟動服務（背景執行）
docker compose up -d

# 3. 等待 healthcheck 全綠（約 60 秒首次）
docker compose ps

# 4. 套用 PostgreSQL schema migration
alembic upgrade head

# 5. 驗證 pgvector extension
docker compose exec postgres psql -U autoclaude -d autoclaude -c "\dx"
# 預期看到 vector | 0.7+

# 6. 驗證 TEI 健康狀態
curl http://localhost:8080/health
# 預期 200 OK

# 7. 試算一筆 embedding（驗證 BGE-M3 1024 維）
curl -X POST http://localhost:8080/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs": "AutoClaude 是一套自動執行引擎"}' | jq 'length'
# 預期輸出 1024
```

---

## 4. 服務說明

### 4.1 postgres（pgvector/pgvector:pg16）

| 項目 | 值 |
|------|-----|
| Image | `pgvector/pgvector:pg16` |
| Volume | `pg_data`（named volume，container 移除不影響資料） |
| Port | `5432` → host `5432`（可改 `.env` 的 `POSTGRES_PORT`） |
| 健康檢查 | `pg_isready` 每 5 秒 |
| extension | `vector` 內建（無需手動 `CREATE EXTENSION`，alembic 0004 已處理） |

### 4.2 embedder（TEI BGE-M3）

| 項目 | 值 |
|------|-----|
| Image | `ghcr.io/huggingface/text-embeddings-inference:1.5` |
| Volume | `tei_cache`（model 快取，~2GB；首次啟動下載） |
| Port | `8080` → host `8080` |
| GPU | NVIDIA 1 卡 passthrough（`deploy.resources.reservations`） |
| 健康檢查 | `curl /health` 每 10 秒；start_period 60 秒（等 model load） |
| 維度 | **1024**（BGE-M3 固定） |
| 最大 batch | 32（可調 `--max-client-batch-size`） |

---

## 5. 資料安全（PostgreSQL Volume + Backup）

### 5.1 Volume 機制（已自動）

`docker-compose.yml` 使用 named volume `pg_data`：
- 資料寫在 host 上的 Docker volume 路徑（Linux：`/var/lib/docker/volumes/autoclaude_pg_data/`；Windows WSL2：`\\wsl$\docker-desktop-data\...`）
- `docker compose down` **不會** 刪除 volume
- 僅 `docker compose down -v` 會刪 volume（破壞性指令，需明示）

### 5.2 必做：每日 pg_dump 備份

#### Linux / macOS（cron）

```bash
# /etc/cron.d/autoclaude_pg_backup
0 3 * * * cd /path/to/AutoClaude && \
  docker compose exec -T postgres pg_dump -U autoclaude autoclaude \
  > backups/autoclaude_$(date +\%Y\%m\%d).sql && \
  find backups/ -name "autoclaude_*.sql" -mtime +30 -delete
```

#### Windows（工作排程器，PowerShell）

建立 `tools/backup_pg.ps1`：
```powershell
$date = Get-Date -Format "yyyyMMdd"
docker compose exec -T postgres pg_dump -U autoclaude autoclaude `
  > "backups/autoclaude_$date.sql"
Get-ChildItem backups/autoclaude_*.sql |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item
```

工作排程器：每日 03:00 觸發 → 動作：`powershell -File tools/backup_pg.ps1`

### 5.3 還原

```bash
docker compose exec -T postgres psql -U autoclaude -d autoclaude < backups/autoclaude_20260516.sql
```

---

## 6. 常見問題

### Q1：TEI 啟動 60+ 秒沒 ready？
首次啟動會從 HuggingFace 下載 BGE-M3 model（~2GB）。檢視進度：
```bash
docker compose logs -f embedder
```

### Q2：GPU 未被 TEI 偵測到？
- Linux：確認 `nvidia-container-toolkit` 安裝 + `sudo systemctl restart docker`
- Windows：確認 WSL2 已啟用 GPU + Docker Desktop 啟用 GPU support
- 驗證：`docker compose exec embedder nvidia-smi`

### Q3：要切換回 Minimax embedding API？
編輯 `.env`：
```
EMBEDDER_BACKEND=minimax_api
```
重啟 AutoClaude 主程式（不需重啟 container）。`embedder` 服務可繼續跑（不影響）或 `docker compose stop embedder` 釋放 GPU。

### Q4：pg_data volume 在 Windows 哪裡？
WSL2 backend：`\\wsl$\docker-desktop-data\data\docker\volumes\autoclaude_pg_data\_data`
建議：**不要直接編輯**，必要時用 `docker compose exec postgres bash` 進 container 操作。

### Q5：要完全重置？
```bash
docker compose down -v   # ⚠️ 刪除 pg_data + tei_cache
docker compose up -d     # 重新建立（PG 會空、TEI 會重抓 model）
```

---

## 7. Production 加固（未來 SD_07+）

- [ ] 移除 `AUTOCLAUDE_ALLOW_INSECURE_DB=1`，啟用 TLS
- [ ] postgres 移除 `ports: 5432`（僅 internal network 存取）
- [ ] postgres 密碼使用 Docker secrets，不寫 `.env`
- [ ] embedder 設 `mem_limit` 防 OOM
- [ ] 加入 reverse proxy（Caddy / Traefik）統一對外
- [ ] 加入 Prometheus + Grafana（對應 SD_05 §M-9 AutoResumeMetrics）
