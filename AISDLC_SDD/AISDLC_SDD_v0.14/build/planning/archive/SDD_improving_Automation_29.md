# SDD_improving_Automation_29 — RFC 狀態欄標準化 + lint 缺欄強制（DEF-30-001）

**狀態**：decided
**主題**：閉合 _28（DEF-23-005 RFC 生命週期 lint）§1 點名的「附帶觀察」——RFC「已決」結案
標記**無標準化欄位**，致雙信號 lint 無法覆蓋所有已決 RFC。本 RFC 標準化狀態詞彙
`**狀態**：proposed | decided` 並把 lint 升級為「active/ RFC 缺 狀態 欄即 advisory warn」強制慣例。
**徵用**：DEF-30-001（P3，文檔慣例標準化）；無新 R-9.x（純 shared infra lint 擴充，不涉 FSM/governance/形式化軌）。
**建立日期**：2026-06-18｜**驅動**：AutoSDD_improving_33（軌道① B 軌 dogfooding）
**前置基線**：v0.14 凍結；AutoClaude pytest 3209 / ci-gate 雙軌 exit 0（v0.01:1478 / v0.14:1593 / scripts:38）
**落地形態**：repo 根 **shared infra `scripts/rfc_lifecycle_lint.py`**（version-agnostic、**免
Copy-on-Evolve**、不觸任一 `AISDLC_SDD_v0.0X` 凍結本體；DEF-02-001 / DEF-03-001 / _28 先例）→
本 RFC **不產生 v0.15**。

---

## §1 問題（DEF-30-001 根因）

_28 以「最低誤報」雙信號機械化現有最強已決標記（落地版本指向已存在凍結版 OR
`狀態：已決/結案/archived/closed`），但偵察揭露現有 RFC 狀態標記慣例不統一：

- 37 個 archive RFC 中 `落地版本` 僅 1 檔、`結案` 2 檔、`狀態：已決` 0 檔；
- 實際多用 `**狀態**：✅ 已歸檔` / `EXECUTED` / `EXECUTING` 等**非標準詞彙**，或**無狀態欄**
  （由正文推導）。

後果：(a) 用 `EXECUTED`/`已歸檔` 標記的已決 RFC 若滯留 active/，雙信號 lint **偵測不到**（漏網）；
(b) 無任何機制要求 active/ RFC 宣告狀態 → 慣例靠人工，無強制力。

## §2 提案（落地於 shared infra `scripts/rfc_lifecycle_lint.py`）

1. **標準詞彙**：RFC 開頭以行首欄位宣告 `**狀態**：proposed`（提案中／待決）或
   `**狀態**：decided`（已決／已落地，亦可用 `已決`）。lint module docstring 即此慣例 SSOT。
2. **decided 偵測加標準英文 token**：`_CLOSED_STATUS_RE` 值集補 `decided`（補既有 `已決`），
   使標準 `**狀態**：decided` 被識別為已決。
3. **缺欄 advisory warn**：新增 `_STATUS_FIELD_RE` + `find_active_rfcs_missing_status()` +
   `missing_status()`；active/ RFC 缺行首 `**狀態**：` 欄 → `main()` 印 `::warning::`（**不影響
   exit code**，與「已決滯留 active/」exit 1 硬違規嚴格分級）。

**閉環邏輯**：強制每個 active/ RFC 帶 `**狀態**`，則已決 RFC 滯留 active/ 必帶
`**狀態**：decided` → 被既有 decided 偵測攔下。缺欄 warn 確保慣例被遵循，使 decided 偵測完整
——DEF-30-001 覆蓋缺口閉合。

## §3 驗收

- `scripts/tests/test_rfc_lifecycle_lint.py` 既有 11 case 全保留 + 新增 4 case
  （decided token fire / 缺欄 advisory 非硬違規 / proposed 全乾淨 / CLI 缺欄 warn 但 exit 0）。
- 突變實證：移除 `decided`→decided token case 紅；反轉缺欄邏輯→3 缺欄 case 紅；還原全綠。
- ci-gate 雙軌 exit 0 不退化（advisory warn 不改 exit）。
- 本 RFC 自身採新標準（`**狀態**：proposed`）並走 active→archive 完整生命週期，dogfooding 自驗。

## §4 scope 界定（Rule 2）

- **不回填 archive RFC**：lint 只掃最新版 active/（_28 設計），archive 不在掃描範圍，回填對 lint
  正確性無益（Rule 2，避免大批改動凍結歷史快照）；標準慣例對「未來新建 RFC」生效即達目的。
- **不擴充 `已歸檔`/`EXECUTED` 等舊詞彙**：標準化方向是收斂到 `proposed`/`decided`，非容納所有
  歷史寫法（避免 vocab whack-a-mole；Rule 1 不臆測）。

---

## §5 決策（decided 2026-06-18）

採納。落地於 shared infra `scripts/rfc_lifecycle_lint.py`（+docstring 慣例 + `decided` token +
缺欄 advisory）+ `scripts/tests/test_rfc_lifecycle_lint.py`（11→15 case）。**dogfooding 自驗**：本
RFC 由 `**狀態**：proposed` 起，翻 `decided` 後 lint 即以新標準 token 攔下「decided 滯留 active/」
（exit 1 實證），隨即 `git mv` 入 archive/ → active/ 復乾淨。DEF-30-001 由此 fixed@improving_33。
