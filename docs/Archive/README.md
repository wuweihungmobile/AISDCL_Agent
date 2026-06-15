# Archive — 已結案迭代文件封存區

本目錄封存**已執行完並結案**的整合迭代（軌道①）文件，使 `docs/04_planning/` 與
`docs/06_quality/` 只保留**最新一輪 active 文件**，降低導航雜訊。

## 封存內容

| 檔名樣式 | 原始位置 | 說明 |
|----------|---------|------|
| `AutoSDD_improving_01.md` ～ `_12.md` | 原 `docs/04_planning/` | 第 1–12 輪迭代計畫/設計/RTM |
| `AutoSDD_ZeroTrust_Audit_01.md` ～ `_12.md` | 原 `docs/06_quality/` | 對應各輪零信任審計 |

> **最新 active**：第 13 輪（`AutoSDD_improving_13.md` / `AutoSDD_ZeroTrust_Audit_13.md`）
> 仍留在 `docs/04_planning/` 與 `docs/06_quality/`，供下一輪 `improving_14` 階段一讀取。
> 每輪結案後，將「上上輪」之前的文件搬入本區（保留最新一輪 active）。

## 注意

- 檔案以 `git mv` 搬移，**git 歷史完整保留**。
- 跨輪累積帳本 `docs/06_quality/AutoSDD_Defect_Log.md` **不封存**（持續累積、只增不刪）。
- 部分既有文字引用（CLAUDE.md／迭代範本／Defect_Log 內如「improving_01.md §5.3」）
  指向的舊檔現位於本目錄；屬歷史引用、非建置連結，不影響任何測試/CI。
