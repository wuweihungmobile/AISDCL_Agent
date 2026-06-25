# SDD_improving_Automation_28 — RFC 生命週期機械強制（DEF-23-005）

**主題**：把框架明定但無機械強制的 RFC 生命週期「active=待決 / archive=已決」升級為
**ci-gate 硬閘 lint**——偵測「已決 RFC 滯留 active/」，杜絕靠人工 zero-trust 盤點才揪出的
流程衛生缺口。
**徵用**：DEF-23-005（P3，框架治理自動化缺口）；無新 R-9.x（純 shared infra lint，不涉 FSM/governance/形式化軌）。
**建立日期**：2026-06-18｜**驅動**：AutoSDD_improving_30（軌道① B 軌 dogfooding）
**前置基線**：v0.14 凍結；AutoClaude pytest 3196 / ci-gate 雙軌 exit 0（v0.01:1478 / v0.14:1593 / scripts:27）
**落地形態**：repo 根 **shared infra `scripts/`**（version-agnostic、**免 Copy-on-Evolve**、不觸任一
`AISDLC_SDD_v0.0X` 凍結本體；DEF-02-001 `cross_version_guard.py` / DEF-03-001 `ci-gate.sh` 先例）→
本 RFC **不產生 v0.15**。

---

## §1 問題（DEF-23-005 根因）

CLAUDE.md 與 dogfooding SOP 明定 RFC 生命週期：提案落 `build/planning/active/`（待決）、決策後
`git mv` 入 `archive/`（已決）。但**無任何 hook/lint/CI 自動強制此轉換** → 已完成的 RFC 會滯留
active/ 直到人工 zero-trust 盤點才被發現。

**實證（本輪階段一親查）**：`AISDLC_SDD_v0.12/build/planning/active/` 與
`AISDLC_SDD_v0.13/build/planning/active/` **至今仍凍結著已決的 _26/_27**（Copy-on-Evolve 把當時
未清的 active/ 一併複製凍結）；v0.14 是 improving_23 人工 `git mv` 清理後才乾淨（DEF-23-002）。
症狀已人工修，但**根因（缺機械強制）未除**，每輪 Copy-on-Evolve / RFC 收官皆潛在復發。

**附帶觀察（非本 RFC scope）**：RFC「已決」標記慣例不一致——37 個 archive RFC 中僅 1 個帶
`落地版本` 欄、2 個含「結案」、0 個 `狀態：已決`。標準化結案標記欄位本身是另一缺口（記為
DEF-30-001 觀察項），本 RFC 先以「最低誤報」雙信號機械化現有最強標記。

## §2 提案（落地於 shared infra）

新增 `scripts/rfc_lifecycle_lint.py`（純函式 + thin CLI，**read-only 純觀察者**，不寫 FSM-STATE、
不影響 churn/meta-loop，呼應 R-9.37.4 視覺化 read-only 精神）+ `scripts/tests/test_rfc_lifecycle_lint.py`
（10 case），並接入 `scripts/ci-gate.sh` 共享 infra 區塊後為**硬閘**。

**掃描範圍**：僅**最新演化版**的 `build/planning/active/`（對齊 ci-gate「動態偵測最新版」）——
舊凍結版 active/ 是 Copy-on-Evolve 歷史快照，掃描會對歷史誤報且違反「不動凍結本體」。

**已決偵測（最低誤報雙信號）**：
- (a) 宣告 `落地版本：AISDLC_SDD_vX` 且該版**目錄已存在於磁碟**（已落地＝已決、已凍結）；
- (b) 顯式結案狀態行 `狀態：已決/結案/archived/closed`。
genuinely-proposed RFC 兩者皆無（用 前置基線/目標版本），故近零誤報。`\**` 容忍 markdown 粗體
（真實格式 `**落地版本**：`）。

## §3 決策

**採納，落 shared infra**（非 Copy-on-Evolve）。理由：與 DEF-02-001/DEF-03-001 同精神——跨版本
通用、防退化的 CI 機制應落 version-agnostic `scripts/`，避免每版重複複製且確保「地端=CI」同一檢查。
本 RFC 隨 improving_30 收官，決策完成後 `git mv` 入 `archive/`（並以新 lint 自我驗證：proposal
態不誤報、archived 後不再被掃）。

## §4 驗證證據（improving_30 階段三/四）

- `scripts/tests/test_rfc_lifecycle_lint.py` **10 passed**（正例 fire / 負例不誤報 / 只掃最新版 /
  語意版本 / CLI exit code / 真實 v0.14 active 乾淨）。
- 真實資料健全性：lint 對 archive 的 RFC 27（落地 v0.12 存在）正確 fire、對 RFC 26（無標記）正確不 fire。
- `bash scripts/ci-gate.sh` exit 0：v0.01:1478 + v0.14:1593 + **scripts/tests:37（27→37，+10）** + RFC lint PASS。
- 零 `_HAPPY_PATH`/`*.tla` 變更 → 五軌 TLC 不觸發；零凍結本體變更 → 無 Copy-on-Evolve。
