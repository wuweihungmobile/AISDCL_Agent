# 跨平台複審 Scan-A/B/C/D 四維掃描慣例（正式規格）

> **緣起**：Mac/Windows-11 相容性複審輪（R1 起累積至今 R47）自 ~10+ 輪前開始，習慣把每輪掃描
> 拆成「Scan-A/B/C/D」四個維度分工，但此慣例此前只活在各輪缺陷帳本列的引用文字裡
> （如 `docs/06_quality/AutoSDD_Defect_Log.md` 的 DEF-101-265／269／289／352／353），從未有
> 一份獨立文件把字母對應的維度定義寫下來——新加入的審查員/agent 只能逐一翻歷史帳本引用逆向
> 推敲字母含義。本檔（DEF-101-387 落地）補上這道缺口，**只做正式定義，不重複教學**。

## 四維定義

| 維度 | 範圍 | 典型產出/信號 | 歷史帳本佐證 |
|------|------|--------------|-------------|
| **Scan-A** | 廣泛／背景 agent 通用掃描，**無固定子範圍**——不預設鎖定某類檔案或機制，讓 agent 自由發現跨平台問題 | 任意類型缺陷（路徑穿越、編碼、guard 覆蓋…皆可能命中） | DEF-101-352（R43 Scan-A：`pty_executor.py`／`prompt_dispatcher.py` 路徑穿越，背景 agent 全面掃描發現） |
| **Scan-B** | 檔名淨化／防增生鎖覆蓋率——`component_sanitizer` 家族（`_sanitize_component`／`_sanitize_log_filename`）與 WindowsApps guard 家族（`windowsapps_guard.sh`／`WindowsAppsGuard.ps1`／`is_real_python_candidate`）的覆蓋面是否有語言/檔案類型/呼叫點遺漏 | 未淨化呼叫點、guard 覆蓋不對稱（如某語言/某檔案缺席） | DEF-101-353（R43 Scan-B：WindowsApps guard 只收斂 `.ps1`／`.py`，9 支 bash 呼叫端從未排除） |
| **Scan-C** | CI/CD 與排程基礎設施維度——workflow（`.github/workflows/*-compat-ci.yml`）的 `runs-on`／步驟覆蓋是否對稱、nightly 佈線（`run_local_nightly.*`）是否對等、runner 環境（如 `windows-latest`＝Server SKU 而非用戶端 Windows 11）是否誠實揭露 | workflow 步驟缺席、平台落差未揭露、排程機制不對稱 | DEF-101-265（R24 Scan-C：Windows runner 實為 Server 2022，未如 macOS 側揭露）；DEF-101-269（R26 Scan-C：`windows-compat-ci.yml` 從未實跑 `install_windows_nightly.ps1 -WhatIf`） |
| **Scan-D** | 缺陷帳本／文件維度——基線數字新鮮度（如 pytest passed/skipped 是否隨新測試增長而回填）、帳本歸檔輪替（是否逼近 256KB 上限）、跨文件引用一致性（帳本 vs `ONBOARDING.md` 等 crossref 目標是否各說各話） | 基線數字落後、帳本超限未歸檔、跨文件狀態矛盾 | DEF-101-289（R32 Scan-D：`ONBOARDING.md` §7 pytest 基線落後實測 +11） |

## 使用方式

- **動工前**：依本輪待辦性質對照上表，決定本輪要跑哪幾維（通常四維皆跑，Scan-A 兜底發現
  未預期問題，B/C/D 針對性複查已知高風險面）。
- **記帳時**：帳本「發現情境」欄援引維度代號（如「R47 Scan-B」），供未來審查員／本文件
  對照，不需每次重新解釋字母含義。
- **擴充新維度**：若未來出現無法歸入 A/B/C/D 任一類的常態性掃描焦點，於本表新增一列並
  同步命名慣例（Scan-E…），不需改動既有四維定義。

## 邊界

本文件只定義「維度是什麼」，不規定「每輪必須怎麼跑」——各輪掃描的深度、工具、觸發時機由
`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` 與各輪 prompt 自行決定，本檔不越權。
