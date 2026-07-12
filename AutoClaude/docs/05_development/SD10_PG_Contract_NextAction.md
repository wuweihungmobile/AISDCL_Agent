# SD_10 PG-track Next-Action — pg-contract 日期分界約束矛盾（DEF-101-051）

> **狀態**：open（SD_10 PG-track；**非阻塞**——`autoclaude-ci.yml` pg-contract job 明標 `continue-on-error: true`，第 170 行）。
> **本輪不動工**：屬 repository／約束／fixture 重設計，超出「dependabot 升版 + nightly 紅燈追查」範疇；帳本 [AutoSDD_Defect_Log.md](../../../docs/06_quality/AutoSDD_Defect_Log.md) DEF-101-051 如實記 open。

## 根因

`alembic/versions/0010_link_legacy_to_tiers.py:176-177` 的 CHECK 約束：

```sql
ADD CONSTRAINT ck_runs_post_cutoff_has_goal
CHECK (goal_task_id IS NOT NULL OR started_at < '2026-05-20 00:00:00+00'::timestamptz)
```

cutoff（2026-05-20）**已過**，約束對「無 `goal_task_id` 的新 run」生效；但 `PgStateRepository` 對此類 run 仍裸 INSERT → 契約測試 **12 案中 7 案 CheckViolation**（先前被 DEF-101-049 的 `alembic upgrade` 靜默 rollback／UndefinedTable 遮蔽，修後真實失敗面現形）。

現況：**5 passed / 7 CheckViolation / 1 skipped**（非 setup 全滅——本輪貢獻＝揭開遮蔽使真實面可見）。

## SD_10 待決修法（三選一，需 PM/SD 拍板）

1. **repository 補齊寫入語意**：`PgStateRepository` 建立 run 時保證 `goal_task_id` 有值（或 legacy 走豁免 `started_at`）；最貼近約束原意，但需盤點所有無 goal 的建立路徑。
2. **contract test fixture 對齊約束**：測試前置補 `goal_task_id`／設 legacy `started_at`，使測試資料符合 cutoff 後語意；改動最小，但未修產線寫入路徑。
3. **約束/三層 schema 重審**：評估 cutoff 型 CHECK 是否仍為正確的 legacy 豁免機制（見 0010 三步 FK + `test_three_tier_schema.py`）。

## 移除非阻塞的條件

`autoclaude-ci.yml` pg-contract job 檔頭（第 168-169 行）明訂：正式修復 contract test fixture + 三層 schema 後**移除 `continue-on-error: true`**。詳見 `sprint_history.md §1.7.3 R56`。

## 追蹤

- 帳本：DEF-101-051（open，SD_10 PG-track）
- SD_10 尚無 `SD_Improving_10.md`（SD_Improving_09.md:30 僅預告 W6 末建立大綱）；本檔為 SD_10 PG-track 的具體種子項，開track 時併入其 backlog。
