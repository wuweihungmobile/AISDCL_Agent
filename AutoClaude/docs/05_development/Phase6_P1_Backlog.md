# Phase 6 P1 Backlog — PostgreSQL Backend Production 切換阻擋項

**最後更新**：2026-05-12（W5 P1 #1~#5 全部完成，DBA 簽核）
**對應簽核**：[Phase6_PG_Stakeholder_Signoff.md](../08_deployment/Phase6_PG_Stakeholder_Signoff.md)
**測試基線**：1006 passed / 11 skipped

---

## 1. 背景

Phase 6 PostgreSQL backend 已通過 stakeholder 條件式簽核（DBA / Infra / SRE / Security 四方 APPROVE WITH CONDITIONS）：

- ✅ `yaml_only` 模式：立即可用（zero PG 依賴）
- ✅ `both` 模式：立即可用於 staging（含 TLS 強制、DSN sanitization、pool 配置）
- ⚠️ `db_only` 模式：**需完成 P1 #1-#5 方可切換 production**

P0 18 項已落實；本檔追蹤 P1 共 10 項後續優化，**阻擋 production `db_only` 切換** 的 5 項（#1-#5）以 🔴 標示。

---

## 2. P1 任務追蹤表

| # | 項目 | 採納方 | 阻擋 production | Owner | 預計完成 | 狀態 |
|---|------|--------|------------------|--------|----------|------|
| 1 | **docker-compose.yml**（postgres:17 + healthcheck）+ `config.yaml.example` | Infra | 🔴 阻擋 | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 2 | **CI workflow 啟用 PG service container**（`pg-contract` job，PR 強制執行）| Infra / DoD | 🔴 阻擋 | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 3 | **PG 連線 startup smoke test**（`SELECT 1` + alembic head check，factory.py） | Infra | 🔴 阻擋 | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 4 | **PG 操作 retry 裝飾器**（tenacity≥8.2，`OperationalError` max 3 backoff） | SRE | 🔴 阻擋 | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 5 | **metrics hook**（`DualMetrics`：dual_write_success/failure + shadow_drift + shadow_load_failure） | SRE / Infra | 🔴 阻擋 | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 6 | **PG 最小權限文件**：`docs/08_deployment/PG_Role_Setup.md` — runtime role vs migration role 兩組 GRANT 範本 | Security | — | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 7 | **`last_correction_prompt` redaction**：寫入前 scrub API key / Bearer token regex | Security | — | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 8 | **`asyncio.run()` 與 running event loop 不相容**：`_run_async()` helper 取代所有 `asyncio.run()`，支援 FastAPI/aiohttp | DBA | — | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 9 | **`migrate_file_to_pg.py`** 補 `--skip-existing` flag + KB 遷移迴圈 + transaction batch | DBA | — | wuweihungmobile | 2026-05-12 | ✅ 完成 |
| 10 | **JSONB GIN index**：未來若新增 by-counter query 需求；`0003_optional_jsonb_gin_index.py` 已就緒 | DBA | — | wuweihungmobile | 2026-05-12 | ✅ 完成（optional migration 待需求時執行） |

---

## 3. 完成判準（DoD）

每項 P1 完成需提供：

- [ ] PR 連結
- [ ] 對應測試（單元 / 契約 / smoke）
- [ ] 文件更新（如需修改 `Phase6_PG_Stakeholder_Signoff.md`）
- [ ] Stakeholder 確認（對應採納方簽核）

---

## 4. Production `db_only` 切換條件

P1 #1-#5 全部完成後：

1. 重新審查 [gate_audit.md](gate_audit.md) Gate G5 並升級為「無條件通過」
2. 在 staging 環境跑 7 項契約測（須通過 PG service container）
3. 在 staging 跑 ≥ 24h `dual_write_strict=true` + `dual_read_resolution=fail_loud`
4. PM + Stakeholder 簽核通過後切換 `storage.mode = "db_only"`

---

## 5. 其他技術 TODO

本段紀錄程式碼中尚待補強但**非 P1 阻擋項**的技術 TODO：

| ID | 位置 | 說明 | 對應採納方 |
|----|------|------|------------|
| TD-1 | [autoclaude/utils/notifier.py](../../autoclaude/utils/notifier.py) `notify_escalation()` | Webhook HTTP 發送尚未實作（目前僅 log warning）；未來規劃以 httpx POST + retry/backoff 實作 `_send_webhook(url, title, message, dump_path)` | Infra / SRE |

---

**文檔元數據**：
- 撰寫者：Phase 0~6 重構稽核（Pass 1）
- 對應簽核：DBA / Infra / SRE / Security 四方
- 下次審查觸發：任一 P1 項完成 / Production 切換 `db_only` 評估前
