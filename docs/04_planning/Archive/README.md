# 04_planning/Archive — 已結案迭代計畫封存

封存**已執行完並結案**的整合迭代（軌道①）計畫文件，使 `docs/04_planning/` 只保留
**最新一輪 active** 計畫，降低導航雜訊。

> **慣例**：每輪結案後將舊輪搬入本區，保留最新一輪在 active。`git mv` 搬移、歷史完整保留。
> 對應審計封存於 `docs/06_quality/Archive/`。
> **現況以 `ls` 實查為準**——本檔刻意不快照「Archive 存到第幾號／active 是第幾號」：
> 原文字（「封存 _01～_12」「最新 active＝improving_13」）自 improving_13 起就沒再更新過，
> 到 R71 實查時 Archive 已有 50 檔、上層積了 53 輪，成為一份**看起來精確、
> 實則差 90 號**的假資訊。與根 `CLAUDE.md` 三軌表「本欄不快照具體號次」同政策。

## 🔴 為什麼「最新一輪」必須留在上層（不是美觀問題，是機械依賴）

**上層至少要有一支 `AutoSDD_improving_<N>.md`**，兩處依賴它：

1. 根 `CLAUDE.md` 三軌表的取號規則＝「`docs/04_planning/` 現存最大號＋1」。上層清空後
   `ls` 看不到任何號次，下一輪會不知道從幾號開始。
2. `tools/tests/test_check_defect_log_crossref.py::
   test_real_ledger_current_round_is_two_digit_and_not_the_planning_dir_max`
   以**非遞迴** glob 取上層 improving 清單並 `assertTrue(improving, …)`——上層清空即紅。

## 搬檔會打斷歷史引用 — R72 已裁決（本節取代原「未解治理衝突」）

**衝突原文**：`docs/06_quality/AutoSDD_Defect_Log_archive_*.md` 等歷史檔內有
`docs/04_planning/AutoSDD_improving_<NN>.md` 形態的引用，搬檔後全部指向不存在的路徑；
而 **DEF-101-633 已訂立紀律：歷史歸檔帳本逐字保全、不得改寫其散文**。

**為何「搬檔同時把引用一起改掉」在規則上不可能做完**：斷鏈引用的持有者有兩類是
**明文禁止就地改寫**的，而且兩類都非空——
① `docs/06_quality/AutoSDD_Defect_Log_archive_*.md`（DEF-101-633：歷史歸檔帳本逐字保全）；
② `AISDLC_SDD/AISDLC_SDD_v0.XX/` 凍結版（Copy-on-Evolve）。
**「非空」才是決定性的事實，規模只是佐證**——這兩類各只要有一處，該候選就出局。
「在原處留轉址 stub」則會憑空長出上百個必須跟著搬檔維護的新檔案，
等於製造一整批新的會過期站點，同樣出局。

> **規模是會漂移的量測值，一律現查**（本檔開頭那條規矩對它同樣適用：本節初稿曾寫死
> 「78 處／54 檔／15／19」，同一輪內複查即四個數字全部對不上，故改為 dated snapshot
> ＋複查方法）。2026-08-03（R72）全 repo 實測：斷鏈引用 **298 處／176 份檔**，
> 其中 ①16 處、②176 處、AutoClaude 子專案 8 處。
> **複查方法**：`git ls-files` 逐檔套 `tools/tests/test_ntfs_trailing_space_device_name.py`
> 的 `_ARCHIVABLE_DOC_RE`，命中但不在 git index 者即斷鏈；機械鎖自己掃的是其中的
> root `docs/**.md` 子集（同日實測 110 處／75 檔）。

**裁決：不改引用、不留 stub、不列舉映射表，改以一條可推導的轉址規則。**

```
docs/<04_planning|06_quality>/<四件套檔名>
  → 上層找不到時，改到 docs/<同一層>/Archive/<同一個檔名> 找
```

適用檔名形態只有兩種（**刻意不外溢到任意 `docs/**.md`**，否則真死連結會被洗成
「看似可解析」而失去鑑別力）：`AutoSDD_improving_<N>.md`（含 `_backlog` 尾綴）、
`AutoSDD_ZeroTrust_Audit_<N>.md`。

**為何是規則而不是映射表**：表要有人維護、每搬一次就得補一列，漏補即 stale——那正是
本檔開頭在防的病。規則零維護，且它「成不成立」由機械鎖每次執行都重新驗證一遍。

## 機械鎖（歸檔後務必重跑）

`tools/tests/test_ntfs_trailing_space_device_name.py`：

| 類別／測試 | 守什麼 |
|-----------|--------|
| `TestRootDocsPathRefsAreCaseExact` | 根層 `docs/` 路徑引用的**大小寫**與 git index 一致（DEF-101-633 落地） |
| `TestArchivedIterationDocRefsResolve::test_every_archivable_reference_resolves` | 四件套引用經轉址規則後**必須解析得到**；零白名單 |
| `…::test_the_fallback_rule_is_actually_load_bearing` | 至少一處引用非靠轉址不可解析（反向鎖：歷史引用若被就地改寫即紅） |
| `…::test_archive_and_active_round_ranges_do_not_interleave` | 已歸檔輪號必須全部小於上層輪號＝**歸檔只准由最舊往下搬** |

最後一條是本區積壓多輪的結構性對策：以前「歸檔」沒有可機械檢查的完成定義，
於是每次只搬一部分、號段交錯，下一個人看不出還剩哪些該搬。
