# SD_09 W4 G4 DBA 親演簽核

| 項目 | 值 |
|------|---|
| 演練日 | YYYY-MM-DD |
| DBA 姓名 | （待填入）|
| 演練環境 | 公司 staging（≥ 1M 真實列）|
| dry-run script | tools/sd06_w3_staging_dryrun.sh |
| 結果 | ✅ PASS / ❌ FAIL |
| DBA 簽名 | （git commit --signoff 留痕）|

## 演練清單

- [ ] 連線測試
- [ ] alembic upgrade head（含 0013_drift_log / 0014_config_audit_log）
- [ ] 1M 列 INSERT batch
- [ ] WAL lag 驗證（< 2s NORMAL / 2-10s WARN / ≥ 10s CRITICAL）
- [ ] drift_log 寫入測試（detected_at / severity 欄位）
- [ ] rollback dry-run（tools/pg_dump_to_yaml.py）

## 對應

- ADR-SD09-001 §3 取證
- 紅線 ❌21（DBA 親演前不得進入 W5 切換）
- risk_log §15 R-SD09-A-1 / R-SD09-A-2 / R-SD09-A-3 / R-SD09-A-5

## 狀態

⚠️ TEMPLATE（2026-05-19 P0-D4 建立）：待 SD_09 W4 G4 時由 DBA 親自填入並 git commit --signoff 簽核。
