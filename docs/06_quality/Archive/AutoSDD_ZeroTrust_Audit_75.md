# AutoSDD_ZeroTrust_Audit_75 — improving_75 多專家零信任審查證據

> **輪次**：improving_75（A 軌 pty-vs-sdk A/B 載具 compaction-cost 量測補強）。
> **審查標的**：tracked 未 commit（`AutoClaude/tools/ab_compare_backends.py` / `AutoClaude/tests/tools/test_ab_compare_backends.py` / 根 `docs/06_quality/AutoSDD_Defect_Log.md`）+ untracked 新檔（本計畫書 / 本審計文件）。
> **派發隔離**：依 DEF-24-001——審查含 tracked 未 commit + untracked 新檔 → **一律主樹派發、禁 worktree**（worktree 由 HEAD 建樹看不到未 commit/未追蹤檔，會假陰性）；為避免 [[parallel-mutation-audit-collision]]，**並行的 Architect/SA-SD 不做就地突變**，需重做突變的 QA 鏡**序列化獨佔主樹**（本輪實作期突變已單線完成並 Edit 還原）。

---

## 0. 階段一基線（zero-trust 重偵察實測）

| 項 | 實測 | 判定 |
|---|------|------|
| AutoClaude 全套 pytest | 3381 passed / 122 skipped / 0 failed（69.06s） | = improving_74 floor，硬閘 PASS |
| lint-imports | 8 kept / 0 broken | 過 |
| LOC | violations=0（total=19385 cap=20438） | 過 |
| snapshot | OK FRESH | 過 |
| AISDLC_SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129） | 過 |

---

## 1. Architect 鏡（主樹唯讀）— OVERALL PASS，P0=0 / P1=0

1. **架構純潔性**：`git diff --stat` 只動 `tools/ab_compare_backends.py`（+35/-7）+ `tests/tools/test_ab_compare_backends.py`，**零 autoclaude/ 生產碼變更**；載具非 autoclaude package 成員（`tools/__init__.py` 不存在、只 import argparse/re，無 autoclaude 跨層 import）→ 不在 importlinter 相依圖；無新 God-object、`playbook_runner.py` 全無觸碰。
2. **閘門實測**：lint-imports **8 kept / 0 broken**（196 files）、check_loc_budget **violations=0**、snapshot **OK FRESH**——與計畫書 §5 一致。
3. **計畫書誠實性**：§4.1「+35/+98/9 測/26 passed」對得上實測；誠實邊界反覆切分「真跑需真 token、非離網 → 真跑延後」與「本輪只交付載具使能、不虛報已分出 token 差異」，§8 用詞「真跑時方能量化差異」明確是能力非數字。**無誇大**。
4. **缺陷帳本誠實性**：DEF-75-001 證據與源碼一致（`_RE_FIELD_BOOL` 含 halted :50；`RunMetrics.halted` :68；`m.halted = bools.get("halted", False)` :109 確為本輪新增）、回歸測皆實存通過、P3 分級合理，**無漏記/虛報**。
5. **N/A 標註**：`git status --short AISDLC_SDD/` 空 → ci-gate / 五軌 TLC 標 N/A 屬「條件未觸發」正當類型，標註精確。

---

## 2. SA-SD 鏡（主樹唯讀）— OVERALL PASS，P0=0 / P1=2（均閉環補測）

1. **覆蓋缺口真偽**：(a) compact_count 差異維度論述成立——peak 只取最高水位純量，TOKEN_COMPACT 固定門檻 ≥80%，兩後端長 playbook 下反覆撞同門檻時 peak 雙雙飽和、分不出「壓 1 次 vs 5 次」的 churn 成本，compact_count 補上此正交維度；(b) halted 確為真 dead-parse——改動前 RunMetrics 連 halted 欄都不存在（`+ halted: bool = False` :68 為新增），解析進 bools 後完全無處可寫＝徹底丟棄。`KernelResult` 之 halted 為 frozen dataclass 真實欄位、`main.py:140` `%s` repr 必印 `halted=...`，合成 log 與 production 對齊。**W-75-1/3 為真實補強非 make-work**。
2. **設計正確性**：compact_count 與 peak **共用同一次 log 掃描**（`compact_count += 1` 與 `peak = max(...)` 並列、無額外迭代、未破壞 max 邏輯）；aggregate compact_count_mean/total/max 與既有 peak/correction 聚合同模式；halted_count 與 success_count/escalated_count 三行同構對稱。format 單輪/多輪兩表皆同步加欄無遺漏。
3. **測試守界（Rule 9）**：`test_compact_count_counts_token_compact_lines` 同時斷言 compact_count==2 AND peak==91（守正交性）；`test_halted_parsed_from_kernel_result` 斷言 halted is True（dead-parse 復活即紅）；8 測皆非 tautology。
4. **載具實測**：`pytest tests/tools/test_ab_compare_backends.py -q` = 25 passed（17 既有 + 8 新、零既有刪改）。
5. **挖漏洞 → 2 個 P1 測試對稱性缺口（非生產碼缺陷）**：
   - **P1-1**：`bools.get("halted", False)` 的「KernelResult repr 完全無 halted= 子串」兜底分支未專測。
   - **P1-2**：`test_aggregate_empty_is_zero_no_crash` 未斷言 compact_count_total==0 / halted_count==0 的空輸入 default。
   → **依 [[no-defer-unless-justified]] 閉環內當場補**：新增 `test_halted_absent_field_defaults_false`（守舊版無 halted= log 相容）+ 擴充 `test_aggregate_empty_is_zero_no_crash`（斷言新欄空輸入 default 0）。載具 25→**26 passed**、全套 3389→**3390**。

---

## 3. QA 鏡（序列化獨佔主樹）— OVERALL PASS，P0=0 / P1=0（另記 P2=2 文字殘留，已訂正）

1. **獨立全套 pytest**：`3390 passed, 122 skipped` in 68.80s——與宣稱完全一致。
2. **獨立重做受控突變**（序列化、Edit 還原、零 git checkout）：MUT-A（`compact_count += 1`→`+= 0`）致 `test_compact_count_counts...` 轉紅（`0==2`）；MUT-B（`m.halted = bools.get(...)`→`= False`）致 `test_halted_parsed...` + `test_aggregate_halted_count` 兩測轉紅（`0==1`）；還原後載具 **26 passed** 復綠。確證新測真綁 business logic。
3. **工作樹潔淨度**：還原後 `git diff --stat` 只剩 `ab_compare_backends.py` + `test_ab_compare_backends.py` + `Defect_Log`（帳本 modified 預期內）；`grep MUT-` 無殘留；untracked 僅 improving_75.md + ZeroTrust_Audit_75.md。
4. **誠實複核**：9 新測數目核對無誤；誠實邊界三處（題頭/§8/帳本 recap）一致、未誇大為「已取得實測 token 差異」。**揪 P2×2 文字殘留**（補測 25→26 後未同步的「25 passed」字樣於 improving_75.md R-75-4 + Defect_Log DEF-75-001 行尾）→ **已訂正為 26**（Audit_75:36 與 improving_75 SA-SD bullet 的「25」為 SA-SD 審查當下歷史實測值，且該句已寫「25→26」，保留正確）。
5. **收斂未破壞**：3390 ≥ floor 3381（+9 零退化）、lint-imports 8 kept、LOC violations=0、無 skip 規避（122 = 基線值）。

---

## 4. 結案收斂（階段四零退化驗證矩陣，全項實測）

| 檢查 | 通過條件 | 實測 |
|------|---------|------|
| AutoClaude 全套 | ≥3381 / 0 failed | **3390 / 122 / 0**（floor 3381 + 9 新測，68.09s） ✅ |
| 架構契約 | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | 全過 | **violations=0** ✅ |
| Snapshot | 新鮮 | **OK FRESH** ✅ |
| AISDLC_SDD ci-gate | exit 0 | **N/A — 零碰 AISDLC_SDD/**（git status 空；階段一實測 exit 0） |
| 五軌 TLC | 僅 FSM 變更時 | **N/A — 條件未觸發**（零碰 `*.tla`/FSM） |
| DAL 等價 | 三後端等價 | **既有等價測試隨全套 3390 通過**；無新 round-trip 契約 |

**受控突變實證（測試非空殼）**：MUT-75-1（compact 計數 `+=1`→`+=0`）/ MUT-75-2（聚合 total→0）/ MUT-75-3（halted 寫回回退）各令對應測試轉紅，Edit 還原後 26 passed 復綠。

**結論**：三鏡全 OVERALL PASS、P0=0；SA-SD 2 個 P1 已閉環補測。本輪定位（A 軌 A/B 載具能力補強、零 autoclaude/ 生產碼、修 1 個 P3 載具 dead-parse、L_合體=L5 維持）與系統實況一致，誠實邊界切分清楚、無虛報「已取得 token 差異」。
