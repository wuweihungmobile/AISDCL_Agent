# 06_quality/Archive — 已結案迭代審計封存

封存**已執行完並結案**的整合迭代（軌道①）零信任審計文件 `AutoSDD_ZeroTrust_Audit_<N>.md`，
使 `docs/06_quality/` 只保留**與上層 active 計畫同輪**的審計。`git mv` 搬移、歷史完整保留。

> **現況以 `ls` 實查為準**——本檔刻意不快照「Archive 存到第幾號／active 是第幾號」。
> R72 訂正：原文字（「封存 `_01.md ～ _12.md`」「最新 active＝`_13.md`」）自寫下後
> 就沒再更新過，實查時 Archive 已有數十檔、上層積了 50 輪未搬，是一份**看起來精確、
> 實則差近 90 號**的假資訊——與 `docs/04_planning/Archive/README.md` 開頭治的是同一個病。
> 對應計畫封存於 `docs/04_planning/Archive/`。

**上層可以是空的**：留在上層的判準是「與 `docs/04_planning/` 上層 active 計畫**同輪**」。
某輪若沒產出零信任審計（R72 實查：最新幾輪確實沒有，四件套並非每輪都齊），
本層就沒有 active 檔——這是誠實反映現況，不是漏搬。

**不封存**：跨輪累積帳本 `docs/06_quality/AutoSDD_Defect_Log.md`（持續累積、只增不刪）。
它的歷史分冊 `AutoSDD_Defect_Log_archive_*.md` **也不住這裡**——那個家族有自己的歸檔
工具與稽核（`tools/archive_defect_log.py`），一律留在 `docs/06_quality/` 上層。

## 搬檔造成的歷史引用斷鏈 — 見 04_planning 側同名檔

裁決（不改引用／不留 stub／改用可推導的轉址規則）、四方案評比與機械鎖清單，
權威在 [`docs/04_planning/Archive/README.md`](../../04_planning/Archive/README.md)，
本檔不複寫（複寫＝製造第二個會漂移的站點）。轉址規則對本層的形態是：

```
docs/06_quality/AutoSDD_ZeroTrust_Audit_<N>.md
  → 上層找不到時，改到 docs/06_quality/Archive/AutoSDD_ZeroTrust_Audit_<N>.md 找
```
