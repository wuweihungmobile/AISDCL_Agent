# AutoSDD ZeroTrust Audit 31 — A 軌負向斷言保真度（W-31-1）

> **輪次**：improving_31 ｜ **日期**：2026-06-18 ｜ **主柱**：A 軌（雙向協作 / 正向轉譯保真度）
> **審查方式**：三鏡（Architect / SA-SD / QA）**主樹直接審查**（依 DEF-24-001 反向陷阱：本輪僅改 2 個 **tracked** 檔且未 commit，worktree 由 HEAD 建樹看不到未 staged 修改 → 一律主樹派發）。

---

## 1. 階段一基線（Zero-Trust Re-Audit）實測

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | 3196 passed / 122 skipped / 0 failed | ✅ floor=3196 硬閘 PASS |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | OK | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593 + scripts:38） | ✅ |
| 最新框架版本 | — | v0.14（Explore 初報 v0.09 為誤報，主 agent 親跑 `ls -d` 校正為 v0.14） | — |

**硬閘**：基線 = 3196 passed / 0 failed，未低於上輪、無 failed → 准入階段二。

---

## 2. 階段四收斂矩陣實測

| 檢查 | 本輪實測 | 判定 |
|------|----------|------|
| AutoClaude 全套 | **3203 passed / 122 skipped / 0 failed**（115.84s） | ✅ +7 |
| 架構契約 | 8 kept / 0 broken | ✅ |
| LOC 分級 | total=18503 / cap=20438，violations=0（adapter 304<400） | ✅ |
| Snapshot | OK（FRESH） | ✅ |
| AISDLC_SDD ci-gate | exit 0（scripts:38、RFC lint PASS） | ✅ 持平（零觸碰框架） |
| 五軌 TLC | 不觸發（零 `_HAPPY_PATH`/`*.tla` 變更） | N/A |

---

## 3. 突變實證（測試非假，Rule 9）

主 agent + QA 鏡各自親跑三組突變：

| 突變 | 預期 | 實測 |
|------|------|------|
| 負向 `(?!.*{q})` 翻成 `(?=.*{q})`（語意顛倒） | 負向測試轉紅 | 5 failed / 2 passed（單負向/混合/多負向/英文/端到端）→ 還原 7 passed |
| 否定切片 `line[:m.start()]` 改整行 `line` | 引號內否定測試轉紅 | `test_negation_inside_quote_is_positive` 轉紅（整行誤把引號內「不可撤銷」判負向）→ 還原綠 |
| `if neg_frags:` 改 `if False:`（停用分流） | 負向測試轉紅 | 5 failed / 2 passed → 還原 7 passed |

三組突變還原後 `diff` 皆 **clean restore**（無殘留污染）。維持 PASS 的 2 個（引號內否定、純正向哨兵）本就走正向路徑、不依賴 `neg_frags`，符合預期非漏測。

---

## 4. 三鏡裁決

### 4.1 Architect 鏡 — OVERALL PASS（P0=0 / P1=0）
1. 架構純潔性 PASS：304<400、lint 8/0（190 files/480 deps）、零新 import 邊、純函式無 IO。
2. 向後相容性 PASS：純正向 ≥2 引號回 `(?s)(?=.*q)...` 無 `\A`（improving_29 格式完整保留，哨兵測試斷言）；單引號/status/量化/fallback diff 證未動。
3. 正則正確性 PASS：實跑反證 `re.search(r'(?s)(?!.*err)','has err here')` 恆真（span 5,5）、加 `\A` 後正確 None；突變移除 `\A` 後 4 負向測試轉紅。
4. 否定標記精準度 PASS：錨定 `line[:m.start()]`；突變改整行後引號內否定測試轉紅，證切片邊界 load-bearing。

### 4.2 SA-SD 鏡 — OVERALL PASS（P0=0 / P1=0，含 1 P3 觀察）
1. 需求—設計一致性 PASS：負向斷言是真實保真度缺口（安全/隱私 AC 常用否定句式），非投機；改前 `不應包含「password」`→`re.escape("password")` 語意顛倒。
2. 設計完整性與已知限制誠實揭露 PASS：親測非引號負向 status（`不應回傳 500`→`(?i)(500)`）沿用既有正向 status 路徑，屬**正確界定的 out-of-scope**，非新 bug。
3. 否定標記涵蓋面 PASS：清單合理；prompt 點名的孤立 `\bno\b` **實際不存在**（只有 `\bno\s+longer\b`，刻意避高誤判）；`\bnot\b`/`\bnever\b` 以 `\b` 避開 notification/note/nevertheless 子串誤判（親測 None）。
4. 介面契約 PASS：`_gherkin_to_regex(self, gherkin)->tuple[str,bool]` 簽章零變更；SpecContract/PlaybookTask 零欄位增刪（無 schema 影響）。
- **新增 DEF-31-001（P3）**：孤立 `\bnot\b`/`\bnever\b` 對 `not only…but`、`is not empty` 等含 not 非否定語意句式可能誤判（僅同句含引號時生效，影響面極小）。

### 4.3 QA 鏡 — OVERALL PASS（P0=0 / P1=0）
1. 全套零退化：3203 passed / 122 skipped（113.22s），floor=3196 相符、+7、0 failed。
2. 標的測試：53 passed；`TestNegativeAssertionFidelity` 7 綠 + improving_29 `TestMultiAssertionCombination` 7 綠（零退化）。
3. 突變實證：`if neg_frags:`→`if False:` → 5 failed/2 passed；還原 7 passed + diff NO DIFF（clean restore）。
4. 收斂未破壞：lint 8/0、LOC violations=0、snapshot OK。

---

## 5. 結案結論

- 三鏡 **全 OVERALL PASS（P0=0 / P1=0）**。
- 本輪閉合正向橋接「負向斷言語意顛倒（mis-specify）」缺口，A 軌正向轉譯保真度再進一步。
- 零退化（3203=3196+7）、零框架變更、零 Copy-on-Evolve、五軌 TLC 不觸發。
- 新增 P3 觀察 DEF-31-001（已入帳，routed，非阻塞）。
- 既有 open/routed 缺陷（DEF-30-001 / 19-001 / 01-007 / 01-009 / 17-001）維持狀態、未惡化。
