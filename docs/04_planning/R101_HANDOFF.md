# R101 交棒書（收尾單人窗口 → R102）

<!-- guard-total:R101 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 86452 → 87784（+1332）**
——逐檔清單見 [`CrossPlatform_R101_Scan_Findings.md`](../06_quality/CrossPlatform_R101_Scan_Findings.md)。
四方複審核准 DEF-200-208 一次性例外，磁碟現值與凍結表現已對帳一致（drift=0）。

- **輪次**：R101（承接 R100 交棒的兩筆治理修憲：DEF-200-207 provenance 缺陷、DEF-200-208 護欄層死結）
- **性質**：收斂輪——治好一個結構性恆假判準，收斂六支跨多輪陳舊漂移

---

## §1 已驗證什麼（逐字實測輸出 ＋ rc；不採信任何未附輸出的宣稱）

### 1.1 DEF-200-207：`pricing_exemption_problems()` provenance 修復

RED（修前判準邏輯對真實磁碟值求值，重現原病灶）：

```
AssertionError: 17032 not greater than 17079
RC=1
```

GREEN（修後，`TestPricingChangeExemptionExpiresOnItsOwn` 全組）：

```
Ran 5 tests in 1.034s

OK
RC=0
```

### 1.2 DEF-200-208：護欄層重釘（決策 b：四方複審核准一次性例外）

重釘後自我覆核（`--print-guard-lines`）：

```
# 淨額 87784→87784 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
```

`TestGuardLayerRatchet`／`TestApprovedRoundOverageIsScoped`／
`TestPricingChangeExemptionExpiresOnItsOwn` 全套（rc 見 §2 全檔總覽）。

---

## §2 全檔總覽

```
python -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v
```

見主控交件回報逐字貼出的完整輸出與 rc；本檔不重複貼一份會漂移的複本
（同 `_PHASE2_REVIEW_LOG` 一份知識一個家的紀律）。

---

## §3 還沒做什麼

- `DEF-200-207` 的 E3（provenance 判準改寫）已於本輪落地，但 ADR-XPLAT-013 §7 的
  U1~U7（四方獨立審查打勾）仍未執行，`DEF-200-207` 承接 R102。現查：
  `python -c "import pathlib; print(pathlib.Path('docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md').read_text(encoding='utf-8').count('未進行'))"`
  應 > 0（U1~U4 逐列仍是「未進行」）。
- `DEF-200-209`（ruff E701/E702 閘門缺口）、`DEF-200-210`（macOS onboarding 基線回填）
  等既有 open 列本輪仍未觸碰，狀態不變。現查：
  `git diff HEAD --unified=0 -- docs/06_quality/AutoSDD_Defect_Log.md` 的輸出裡不含任何
  帶 `+`／`-` 前綴且提到這兩個案號的行（context 行不算，只有這兩份既有列本身完全沒被改動）。

## §4 下一步的確切指令

```bash
python -m unittest tools.tests.test_adr_xplat001_c1c2_lock -v
```

## §5 禁止事項

- 不准調整 `net_cap_for_round()`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`／
  `_REPIN_ROUND_CAP_SINCE` 等棘輪常數本身（`_REPIN_APPROVED_ROUND_OVERAGE` 是唯一核准的
  例外通道，且僅限指名輪號＋精確淨額）。
- 不准把 `_REPIN_APPROVED_ROUND_OVERAGE` 當成慣例濫用——名冊筆數受
  `_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES`（=1）鎖住，第二筆需另立缺陷帳本案號並
  再走一次四方複審。
