# CrossPlatform R101 — 掃描發現與逐檔清單（DEF-200-207／DEF-200-208 收斂）

<!-- guard-total:R101 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 86452 → 87784（+1332）**
——四方複審核准 DEF-200-208 一次性例外，逐檔清單見下方〈§B 逐檔清單〉。

- **輪次**：R101
- **範圍**：① 治好 `pricing_exemption_problems()` provenance 缺陷（DEF-200-207 主線之一）
  ② 落地 DEF-200-208 死結裁決（決策 b：四方複審核准重釘，一次性例外）
- **本檔性質**：`_GUARD_LINES_REPIN_LOG` R101 列逐字指名的「逐檔清單的家」（款(9)
  `[未附刪除清單]` 要求），亦是 `_REPIN_APPROVED_ROUND_OVERAGE["R101"]` 核准理由裡
  引用的同一份清單。

---

## §A 立案事實：DEF-200-207 的 provenance 修復

`AutoClaude/.loc_baseline`（17032）自 2026-06-13 就沒再重釘過，而 `pricing_exemption_problems()`
（ADR-XPLAT-013 條文三）原本用 `baseline > total` 這個**不等式**同時表達「已重釘」與
「total 長過陳舊 baseline」兩件相反的事——計價規則換過（`count_loc()` 改為 assertion-only）
之後，`total` 對同一份原始碼未必變小：R100 §E-4 全樹實測 `total` 反而由 17032 升為
17079（+47），而不是預期中的下降。於是「未重釘」與「total 長過陳舊 baseline」在這組真實
資料上變成**同一個條件的兩種相反解讀**，`baseline > total` 對兩者都判 `False`
⇒ 判準結構上恆假、永久靜音（實測：`test_the_next_round_cannot_reuse_the_exemption` 的
前提斷言 `assertGreater(baseline, total)` 直接因 `17032 not greater than 17079` 炸掉）。

修法：改為 **provenance 比對**——`AutoClaude/tools/check_loc_budget.py` 新增
`.loc_baseline_policy_version`（`write_baseline_policy_version()`／
`read_baseline_policy_version()`），每次 `write_baseline()` 同時記下當時的
`POLICY_VERSION`；`pricing_exemption_problems()` 改判 `baseline_policy_version ==
current_policy_version`，不再從數字大小反推狀態。磁碟上既有的 `.loc_baseline` 因為早於
本機制存在，`read_baseline_policy_version()` 誠實回 `None`（不猜成目前版本），故豁免輪
過期判準對現況仍正確判紅——**這不是本輪的迴歸，是本來就該紅的東西第一次被正確地看到**。

紅綠自證（當回合真跑）：

| 階段 | 動作 | 結果 |
|------|------|------|
| RED | 用原始（修前）判準邏輯——`assertGreater(baseline, total)`——對真實磁碟值 `baseline=17032`／`total=17079` 求值 | `AssertionError: 17032 not greater than 17079`（rc=1，重現原病灶） |
| GREEN | 改判準後，`TestPricingChangeExemptionExpiresOnItsOwn` 全組（5 支） | `OK`（rc=0） |

---

## §B 逐檔清單（護欄層 86452 → 87784，+1332）

本輪淨額由兩部分組成：

### B.1 六支跨多輪陳舊漂移（ADR-XPLAT-013 落地後首次被 `--print-guard-lines` 覆核揪出）

這批檔的成長**不是本輪造成的**——它們在 R100 及更早的多輪裡各自因為既有判準真實擴充
而長大，但歷輪重釘都沒有覆核到它們，於是 `_FROZEN_GUARD_LINES` 上的數字停在舊值、
磁碟已經往前走了好幾輪都沒人發現（DEF-200-208 立案時的 `86452 → 87544`／+1092，
本輪覆核後realign為 +1146，含本輪自身另新增的判準面）：

| 檔案 | 舊值 | 新值 | 淨額 | 陳舊成因 |
|------|-----:|-----:|-----:|----------|
| `test_check_hooks_liveness.py` | 3433 | 3598 | +165 | hook 佈線與載具契約的既有回歸擴充，多輪累積未覆核 |
| `test_check_pytest_baseline_sites.py` | 297 | 299 | +2 | 站點掃描面既有微幅擴充 |
| `test_claim_provenance_r86.py` | 341 | 618 | +277 | 宣稱溯源判準既有擴充，多輪累積未覆核 |
| `test_context_budget_guard.py` | 7713 | 8081 | +368 | 額度／context 水位判準既有擴充（多分支自證），多輪累積未覆核 |
| `test_doc_loc_baseline_freshness_r60.py` | 7138 | 7318 | +180 | 文件新鮮度判準既有擴充，多輪累積未覆核 |
| `test_quota_policy.py` | 2332 | 2432 | +100 | 額度政策既有擴充，多輪累積未覆核 |

小計：**+1092**。

### B.2 本檔自身編修（本輪新增的判準面 + 護欄層自我編修）

| 項目 | 淨額（約） | 內容 |
|------|-----------:|------|
| `pricing_exemption_problems()` provenance 修復 | 含於下列自身編修 | 改參數簽章（`baseline_policy_version`／`current_policy_version`）、改判準邏輯、改五格既有測試、擴充 docstring |
| `_REPIN_APPROVED_ROUND_OVERAGE` 一次性例外機制 | 含於下列自身編修 | 新增登記表 ＋ `repin_growth_problems()` 接線 ＋ `TestApprovedRoundOverageIsScoped`（7 支回歸測試：命中生效／未命中不受影響／精確淨額比對／短理由不算數／打斷連續上升／名冊上限／拿掉本核准會復發死結） |
| `_REPIN_NET_CAP_SCHEDULE` 到期義務兌現 | 0（只改常數，非行數） | 追加 `(101, 750)`，兌現 `_REPIN_NET_CAP_DUE_ROUND=101` 到期義務（cap 850→750，只准往下改，未放寬任何門檻） |
| 護欄層重釘自身編修（本表、稽核列、prefix_len／sha256、`_FROZEN_PREFIX_REWRITE_LEDGER`） | 含於下列自身編修 | 同 R95~R100 既有體例 |
| 本檔自身逐檔漂移合計 | **+240** | `test_adr_xplat001_c1c2_lock.py` 5830 → 6070 |

小計：**+240**。

**B.1 + B.2 = 1092 + 240 = 1332**，與 `_GUARD_LINES_REPIN_LOG` R101 列的淨額逐字相符。

---

## §C DEF-200-208 死結裁決（決策 b：四方複審核准重釘）

立案時的死結（見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-208）：不重釘則
`guard_line_problems()` 紅（磁碟已漂移、凍結表未跟上）；重釘則單輪淨額
`355(R100) + 1092(六支漂移) = 1447 > cap(850)` 觸發 `[超出每輪上限]`，且緊接
R99／R100 兩輪連續上升，第三輪觸發 `[只升不降]`——三個出口（暫緩重釘／一次性豁免／
新判準搬出護欄層）之外別無他路，而暫緩重釘等於讓 `guard_line_problems()` 恆紅，
搬出護欄層是規避計量、不是治本。

四方複審核准**一次性豁免**（決策 b），落地為 `_REPIN_APPROVED_ROUND_OVERAGE["R101"]`：
一個**指名輪號 ＋ 精確淨額**的登記表項，只赦免這一個具體事件的款(10)(11)，
`net_cap_for_round()` 與 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS` 的判準邏輯與門檻數字
本輪一個字未動（回歸鎖：`TestApprovedRoundOverageIsScoped`，含拿掉本核准即復發死結的
紅綠自證）。

---

## §D 交叉引用

- `docs/04_planning/R101_HANDOFF.md`
- `docs/06_quality/AutoSDD_Defect_Log.md` — `DEF-200-207`／`DEF-200-208`
- `docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md`
