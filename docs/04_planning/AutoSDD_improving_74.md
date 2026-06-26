# AutoSDD_improving_74 — A 軌 wexpect 路徑 TIMEOUT/auto-respond 分支測試覆蓋補強

> **本輪柱位**：**A 軌（整合）**——pty wexpect 後端剩餘零覆蓋分支的回歸測試補強（執行器層可測性加固）。
> **下一份**：`AutoSDD_improving_75.md`。
> **誠實級別**：**測試覆蓋補強輪**（補 improving_73 §8 遞延候選 (c)：wexpect `_readline_wexpect` index==1〔TIMEOUT〕空回傳 + `_auto_respond` 經 wexpect `child.sendline` 兩條零覆蓋分支），**生產碼零改、非缺陷修復、非成熟度推進**。`L_合體 = min(A=L5, B=L5, C=L5) = L5` 維持。
> **Copy-on-Evolve / 五軌 TLC**：本輪純 AutoClaude 整合層測試檔（`tests/test_perception.py`）、未動 `AISDLC_SDD/` 任一檔、未碰 `*.tla`/FSM/DAL、**未動任何生產碼** → **免 Copy-on-Evolve、免五軌 TLC、DAL 等價 N/A**。

---

## 1. 本輪輸入（自上輪繼承）

### 1.1 improving_73 RTM / 遺留
- improving_73（commit cf4b18b）已結案：A 軌 pty wexpect raw log 觀測缺口修復（DEF-73-001：顯式擷取取代不觸發的 `logfile_read` callback + EOF 殘留對稱），基線升至 **3377 passed / 122 skipped / 0 failed**。
- improving_73 §8 遞延 improving_74 候選：**(a)** 更長/觸發 compaction 的 playbook A/B 分 token 峰值差異；**(b)** SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01）；**(c)** wexpect 路徑其餘分支（readline TIMEOUT 回 `""` 無內容、`_auto_respond` 經 wexpect `sendline`）的測試覆蓋補強。
- 本輪選 **(c)**：候選 (b) 時間閘未到（今日 2026-06-26 < ~06-29，延後正當）；候選 (a) 屬「需真模型統計、慢、價值在統計對比」，留待時間閘成熟輪一併；候選 (c) 是**具體、可單元測試、低風險（生產碼零改）**的可測性補強，**直接命中連三輪揭露的跨輪根因「pty wexpect 路徑長期無測試覆蓋」**（DEF-71/72/73 同源），當場做最符合「不要無謂延後」紀律（[[no-defer-unless-justified]]）。

### 1.2 缺陷帳本 open/routed（階段一複驗）
- open：DEF-01-007（cc-switch GUI，P3，環境工具缺裝）/ DEF-01-009（sdd_governance_plugin LOC watch，P3）/ DEF-62-001（auto_recovery 註解滯後，P3 routed）/ DEF-23-005（RFC 生命週期自動化，P3 routed）。
- routed：DEF-17-001 / DEF-19-001 / DEF-35-001（P2，C 軌 SD_09 W1）/ DEF-42-001（皆 P3 除 DEF-35-001）。
- 本輪只動 `tests/test_perception.py`（新增測試），未動 `sdd_governance_plugin`、未動 `auto_recovery`、未碰多後端 A/B、未動 goal_synthesis → **不觸發任何 open/routed 缺陷**，全維持原狀態（詳見 Defect_Log 本輪 recap）。

---

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）— 硬閘 PASS

| 項目 | 命令 | 實測 | 判定 |
|------|------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3377 passed / 122 skipped / 0 failed**（67.23s） | = improving_73 實測值，**硬閘 PASS** |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（196 files / 492 deps） | 過 |
| (c) LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19385 baseline=17032 cap=20438） | 過 |
| (d) Snapshot | `python tools/snapshot_sync.py --check` | **OK（FRESH）** | 過 |
| (e) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129） | 過 |
| (f) 上輪構件存在性 | `_readline_wexpect` index==0 顯式 raw（:103-104）/ index==2 EOF 殘留（:107-112）/ `_RawLogAdapter` 死碼已除 / 三回歸測試名皆存在 | 與 improving_73 §4 一致 | **無虛報** |
| (g) 本輪 W 項覆蓋缺口偵察 | `_readline_wexpect` index==1（TIMEOUT，:114 `return ""`）與 `_auto_respond`（:144-150 經 `send()`→wexpect `child.sendline`，:135-136）現有測試覆蓋 | TIMEOUT 分支：`_FakeWexpectChild.expect` 只回 0/2，**從不回 1**；`_auto_respond` 三測試全 `_WEXPECT_AVAILABLE=False`，**zero wexpect `sendline` 覆蓋** | **缺口成立、有實質 delta** |
| (h) 外部依賴形態 | 本輪 W 項涉 wexpect（Windows-only），以 `MagicMock`+`create=True` patch（沿 improving_72/73 既有測試手法），**不需** headless 外部 CLI/服務 | 純單元測試樁，非 GUI/PATH 假設 | 已確認，非 DEF-10-002a 陷阱 |

> **硬閘**：(a) 基線 3377 = improving_73 實測值，無 failed、無低於上輪 → 准進階段二。

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：**生產碼零改**——本輪僅在 `tests/test_perception.py` 擴充測試樁 `_FakeWexpectChild`（**向後相容**：新增 `timeout_rounds`/`self.sent` 預設不影響既有三測試）+ 新增 3 回歸測試。無新 class／無 God-object；`playbook_runner.py` Thin Facade 全無觸碰。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**、不動 DAL 三後端、不動 checkpoint → 零停機。純測試層補強。
3. **安全防護網**：**不新增任何生產碼路徑**、不新增「從文件生成指令」或 shell 字串路徑、不弱化 CONDITIONAL 三層。W-74-2 測試的 `_auto_respond` 為**既有**自動回應邏輯（固定 `auth_response` 字串、非文件生成），本輪僅補其 wexpect 分支的回歸守界，未新增/弱化任何消毒。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防本輪 N/A。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `tests/test_perception.py` `_FakeWexpectChild.__init__` | 加 `timeout_rounds=0`（前 N 次 `expect` 回 index==1〔TIMEOUT〕、不 pop line）+ `self.sent=[]` | 加 ~3 行（向後相容） |
| `tests/test_perception.py` `_FakeWexpectChild.expect` | `timeout_rounds>0` 時遞減並回 1（不碰 after/before、不 pop line）；其餘維持原 0/2 行為 | 加 ~3 行 |
| `tests/test_perception.py` `_FakeWexpectChild.sendline` | 由 `pass` 改 `self.sent.append(text)`（記錄自動回應內容） | 改 1 行 |
| `tests/test_perception.py` `test_wexpect_readline_timeout_returns_empty_not_none`（**W-74-1**） | TIMEOUT 回 `""`（非 None、不終止串流）、不寫 raw、TIMEOUT 後仍能讀到後續行 | 新增測試 |
| `tests/test_perception.py` `test_wexpect_auto_respond_via_sendline_on_pattern_match`（**W-74-2**） | 匹配 auth_pattern 的行 → `fake_child.sent == ["y"]`（守 wexpect `send()`→`child.sendline` 分支） | 新增測試 |
| `tests/test_perception.py` `test_wexpect_no_auto_respond_on_normal_line`（**W-74-3**） | 正常行不誤觸發 → `fake_child.sent == []`（對稱 subprocess 的 `test_no_auth_on_normal_line`） | 新增測試 |

- **importlinter**：無新跨層 import（純測試檔）→ **8 kept** 不變。
- **LOC**：`tests/` 不受 LOC tier 約束（`check_loc_budget` 不掃 tests）；`pty_wrapper.py` 生產碼**零改**、行數不變 → `violations=0` 維持。

### 3.3 設計關鍵：為何這兩條分支值得補、且能以受控突變實證守界

improving_71/72/73 連三輪真跑/實證各揪一個 pty wexpect 路徑潛伏缺陷，**共同根因＝wexpect 為 Windows-only、既有測試長期全走 `_WEXPECT_AVAILABLE=False` subprocess 分支**，wexpect 真實分支零覆蓋。improving_73 已補 index==0（讀到行）/ index==2（EOF 殘留）兩條；本輪補齊剩餘兩條可測分支，使 `_readline_wexpect` 四出口（讀到行/TIMEOUT/EOF/例外）與 wexpect 自動回應路徑均有回歸守界：

- **W-74-1（index==1 TIMEOUT）**：production `return ""`（[pty_wrapper.py:114](../../AutoClaude/autoclaude/perception/pty_wrapper.py#L114)）。守界意圖（Rule 9）：TIMEOUT **不可**回 None（會被上層讀取迴圈誤判 EOF 提前終止串流）、**不可**寫 raw（無內容）。受控突變：把 `return ""` 暫改 `return None` → W-74-1「TIMEOUT 後仍能讀到後續行」斷言轉紅。
- **W-74-2（`_auto_respond` 經 wexpect `sendline`）**：production `_auto_respond`→`send()`→wexpect 模式 `self._child.sendline(text)`（[pty_wrapper.py:135-136,144-150](../../AutoClaude/autoclaude/perception/pty_wrapper.py#L135-L150)）。守界意圖：wexpect 模式偵測到授權提示須經 `child.sendline` 回應——既有三測試全走 subprocess（驗 `proc.stdin.write`），此分支壞掉（如 send() 漏掉 wexpect 分支）現有測試**抓不到**。受控突變：把 `send()` 的 `self._child.sendline(text)` 暫改 no-op → W-74-2 `sent==["y"]` 轉紅。
- **W-74-3（正常行不誤觸發）**：對稱 subprocess 的 `test_no_auth_on_normal_line`，守 `_auto_respond` 不過度回應（pattern 不匹配時 `sent` 須為空）。

---

## 4. 階段三：實作與雙重驗證

### 4.1 實作（純 AutoClaude A 軌測試層、生產碼零改、無 Copy-on-Evolve）

- [tests/test_perception.py](../../AutoClaude/tests/test_perception.py)：
  - `_FakeWexpectChild` 擴充（向後相容）：`__init__` 加 `timeout_rounds=0`（前 N 次 `expect` 回 index==1〔TIMEOUT〕、不消耗 line）+ `self.sent=[]` + `raise_on_expect=None`（expect 拋此例外，W-74-4 用）；`expect` 加 TIMEOUT 分支與 raise 分支；`sendline` 由 `pass` 改 `self.sent.append(text)`。既有三測試（raw 擷取/EOF 殘留/不依賴 callback）不檢查新欄位 → 不受影響。
  - 新增 4 回歸測試：`test_wexpect_readline_timeout_returns_empty_not_none`（W-74-1）、`test_wexpect_auto_respond_via_sendline_on_pattern_match`（W-74-2）、`test_wexpect_no_auto_respond_on_normal_line`（W-74-3）、`test_wexpect_readline_returns_empty_on_expect_exception`（**W-74-4，audit_74 SA-SD 鏡發現 except 分支零覆蓋、閉環內補**）。
- **生產碼 `pty_wrapper.py` 零改動**（`git status --short AutoClaude/autoclaude/` = 0）；本輪純補既有行為的回歸守界，使 `_readline_wexpect` **四出口全覆蓋**（index==0 讀到行〔improving_73〕/ index==1 TIMEOUT / index==2 EOF 殘留〔improving_73〕/ except 例外）。

### 4.2 受控突變實證（測試非空殼，R-74-4）

| 突變 | 改動 | 對應測試 | 結果 |
|------|------|---------|------|
| MUT-74-1 | `_readline_wexpect` index==1 `return ""` → `return None` | `test_wexpect_readline_timeout_returns_empty_not_none` | **轉紅**（`AssertionError: None == ''`） |
| MUT-74-2 | `send()` wexpect 分支 `self._child.sendline(text)` → `pass` | `test_wexpect_auto_respond_via_sendline_on_pattern_match` | **轉紅**（`AssertionError: [] == ['y']`） |
| MUT-74-4 | `_readline_wexpect` except 分支 `return ""` → `return None` | `test_wexpect_readline_returns_empty_on_expect_exception` | **轉紅**（`AssertionError: None == ''`） |

- 三處突變均以 **Edit 還原**（禁 `git checkout`，本輪含 tracked 未 commit 改動〔test_perception.py〕+ untracked 新檔〔計畫書〕，遵 [[git-checkout-mutation-revert-hazard]]）。
- 還原後 `git diff --stat autoclaude/perception/pty_wrapper.py` 無變更行、`test_perception.py` **30 passed** 復綠（原 26 + 4 新）。

### 4.3 測試守界意圖（Rule 9）

- **W-74-1**：TIMEOUT 是「本輪暫無輸出」非「結束」。斷言鏈 `readline()=="" → 再 readline()=="AFTER_TIMEOUT\r\n" → raw 檔 == b"AFTER_TIMEOUT\r\n"` 同時守三件事：(1) 不回 None（否則上層誤判 EOF 提前終止）、(2) TIMEOUT 後串流不中斷、(3) TIMEOUT 不寫空 raw。MUT-74-1 證實 (1) 退化即紅。
- **W-74-2**：`assert fake_child.sent == ["y"]` 固化「wexpect 模式經 `child.sendline` 自動回應」決策——既有三測試全走 subprocess（驗 `proc.stdin.write`），此 wexpect 分支壞掉它們抓不到；MUT-74-2 證實 send() 漏掉 wexpect 分支即紅。
- **W-74-3**：`assert fake_child.sent == []` 守「pattern 不匹配不誤觸發」，與 subprocess 的 `test_no_auth_on_normal_line` 對稱，防自動回應過度觸發。

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3377 / 0 failed | **3381 / 122 / 0**（floor 3377 + 4 新測〔含 W-74-4〕，~70s；單獨壓測 ×10 驗穩定，見 §7 flaky 釐清） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken**（196 files / 492 deps） ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19385 baseline=17032 cap=20438；tests/ 不受 tier、生產碼零改） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK（FRESH）** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **N/A — 本輪零碰 AISDLC_SDD/**（`git status --short AISDLC_SDD/` = 0 鐵證）；階段一已實測 exit 0（v0.01:1478 / v0.26:1665 / scripts:129），本輪無觸發路徑 |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A — 條件未觸發**（git status 鐵證零碰 `*.tla`/FSM；TLC 不在 pytest 全套、需 Java+tla2tools，本輪確實未跑） |
| DAL 等價 | `tests/equivalence/`（隨全套） | 三後端等價 | **既有等價測試隨全套 3381 通過** ✅；本輪無新 DAL/checkpoint 改動 → 無新增針對性 round-trip 契約 |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-74-1 wexpect readline TIMEOUT 回 `""` 非 None、不終止串流、不寫 raw | `_readline_wexpect` index==1（:114） | `test_wexpect_readline_timeout_returns_empty_not_none` **PASS**（`""`→後續行→raw 無空寫入三斷言） |
| R-74-2 wexpect 模式 `_auto_respond` 經 `child.sendline` 自動回應授權 | `send()` wexpect 分支（:135-136）+ `_auto_respond`（:144-150） | `test_wexpect_auto_respond_via_sendline_on_pattern_match` **PASS**（`sent==["y"]`） |
| R-74-3 wexpect 模式正常行不誤觸發自動回應 | `_auto_respond` pattern 不匹配時不 send | `test_wexpect_no_auto_respond_on_normal_line` **PASS**（`sent==[]`） |
| R-74-4 測試非空殼（受控突變實證） | 暫改 production 對應分支 | MUT-74-1（`return ""`→`None`）+ MUT-74-2（`sendline`→no-op）+ MUT-74-4（except `return ""`→`None`）各令對應測試**轉紅**，Edit 還原後 30 passed 復綠（§4.2） |
| R-74-6 wexpect readline expect 例外被 except 接住、回 `""` 不崩潰（fail-soft） | `_readline_wexpect` except（:115-117） | `test_wexpect_readline_returns_empty_on_expect_exception` **PASS**（`raise_on_expect=RuntimeError` → readline 回 `""`）；audit_74 SA-SD 鏡發現零覆蓋、閉環內補 |
| R-74-5 零退化 | 收斂矩陣 | **3381/0**、8 kept、LOC 0、snapshot FRESH、零碰 SDD（§5） |

---

## 7. 多專家 Zero-Trust 審查結論

證據見 [AutoSDD_ZeroTrust_Audit_74.md](../06_quality/AutoSDD_ZeroTrust_Audit_74.md)。三鏡（Architect / SA-SD / QA）**全 OVERALL PASS、P0=0**：

- **Architect**：生產碼零改實證（`git diff --stat autoclaude/`=空）、`_FakeWexpectChild` 擴充向後相容、8 kept / LOC 0、計畫書無虛報、帳本誠實。
- **SA-SD**：覆蓋缺口確存且被填、獨立重做受控突變（MUT-74-1/2 轉紅、Edit 還原 git diff 空）；**揪出 `_readline_wexpect` except 分支（:115-117）零覆蓋之 P1** → 依 [[no-defer-unless-justified]] **閉環內補 W-74-4**（+ MUT-74-4 受控突變）。
- **QA**：獨立親跑全套 3381/0、獨立重做三處突變全轉紅還原乾淨、工作樹乾淨、無 skip/xfail 規避；**揪出本帳本 recap 初版數字滯後（3380/29，應 3381/30）之 P1**（低報非虛報）→ **已訂正**；獨立分析 `_FakeWexpectChild` 確定性 + 壓測複核，**確認 flaky 根因結論成立**。

**🟠 過程事故（已釐清零殘留，流程教訓）**：初次**並行**派 Architect + SA-SD 於同一主樹，而 SA-SD 職責含**就地受控突變** tracked `pty_wrapper.py`（index==1 `return ""`→`return None`）。Architect 在突變窗口內並行跑全套 pytest → import 到被突變源碼 → W-74-1 readline 回 None → `assert None==''` **假紅**（即 Architect 觀察的「~1/16 flaky」真因）。

**證實非本輪測試真 flaky**：`_FakeWexpectChild(timeout_rounds=1)` 之 `expect` 為純確定性狀態機（無 thread/計時/隨機），源碼未突變時第一次 expect 必回 index==1→`""`、邏輯上不可能自發回 None；**單獨壓測 ×10 全 3381/0**（無並行突變）+ QA 獨立複核共同證實。**根因＝並行就地突變 tracked 檔互踩（Nightly #18 / 審查閉環 #1 情境）**，修正＝**序列化派發**第三鏡 QA（獨佔主樹、無並行突變）。**流程教訓**：審查閉環 #1「並行就地突變 tracked 檔 → worktree 隔離」須涵蓋「多 audit 鏡並行時，做突變的鏡與跑全套的鏡互踩」——做突變的鏡須以 `isolation: worktree` 派發，或序列化（先非突變鏡跑完、再單獨派突變鏡）。

---

## 8. 誠實級別標註

本輪＝**A 軌 wexpect 路徑剩餘分支測試覆蓋補強輪（生產碼零改、無新缺陷），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**：①補齊 improving_71/72/73 連三輪揭露之跨輪根因「pty wexpect 路徑長期無測試覆蓋」的剩餘可測分支——`_readline_wexpect` 四出口（讀到行〔73〕/ TIMEOUT〔本輪 W-74-1〕/ EOF 殘留〔73〕/ 例外〔本輪 W-74-4〕）+ wexpect `_auto_respond` 經 `child.sendline`（W-74-2）+ 正常行不誤觸發（W-74-3）均有回歸守界；②4 測皆以受控突變實證非空殼（MUT-74-1/2/4 各令對應測試轉紅）。
- **本輪無新框架缺陷**（補覆蓋輪、生產碼零改；SA-SD 發現的 except 零覆蓋屬測試完整性缺口、當場補 W-74-4，非框架缺陷不入帳）。
- **過程誠實**：審查揭兩個 P1（SA-SD except 零覆蓋 / QA 帳本數字滯後）皆當場修正；並誠實記錄「並行突變互踩假紅」過程事故與流程教訓（非掩蓋為真 flaky）。
- **遞延 improving_75 候選**：(a) 用更長/會觸發 compaction 的 playbook 跑 A/B 分出 token 峰值差異（improving_72/73 候選）；(b) SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）。**wexpect 路徑可測分支本輪已補齊**（四出口 + auto_respond + 正常行），該根因家族收尾。

三件套：improving_74 / ZeroTrust_Audit_74 / Defect_Log（improving_74 recap，無新 DEF）。
