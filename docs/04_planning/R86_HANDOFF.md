# R86 → R87 交棒書（R86＝**macOS 第四輪、六包串行 ＋ 淨減法到期義務兌現（但只在量測面內）**）

> 前一份＝[`R85_HANDOFF.md`](R85_HANDOFF.md)。本輪計畫書＝[`AutoSDD_improving_110.md`](AutoSDD_improving_110.md)；
> 證據檔＝[`CrossPlatform_R86_Pace_Calibration.md`](../06_quality/CrossPlatform_R86_Pace_Calibration.md)／
> [`CrossPlatform_R86_Ledger_Reassign_Evidence.md`](../06_quality/CrossPlatform_R86_Ledger_Reassign_Evidence.md)／
> [`CrossPlatform_R86_Guard_Repin_Evidence.md`](../06_quality/CrossPlatform_R86_Guard_Repin_Evidence.md)／
> [`CrossPlatform_R86_Scan_Findings.md`](../06_quality/CrossPlatform_R86_Scan_Findings.md)。
>
> 🔴 **本檔體例**：會漂移的量測值一律不寫死，只寫「哪一支載具會印出它」。
> 凡本檔寫出的 rc，都是**收尾單人窗口當回合真的跑過**的；沒跑的一律標明「未驗證」。

---

## §0 開場必讀（跑完再往下讀）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
git log -1 --format='%H %s'; git status --porcelain | wc -l
.venv/bin/python -c "import sys;sys.path.insert(0,'tools');import check_defect_log_crossref as C;from pathlib import Path;print(C.current_round(Path('docs/06_quality/AutoSDD_Defect_Log.md').read_text(encoding='utf-8')))"
.venv/bin/python tools/session_resume_planner.py --pace     # 🔴 R86 起第三行印攤提中間量
```

1. **不採信本檔任何「已通過」宣稱。** 重啟後第一件事是重驗（§5.1）。
   本輪 agent **逐字駁回舵手判讀 12 次以上，無一次是錯的**。
2. 🔴 **R86 是「收斂 70%」出口收輪，不是「四方複審通過」出口。** 兩者保證強度不同，**不得混記**。
   四方複審**本輪未執行**（配額進入 `band=prepare`），已列入 §9 第 1 項。
   現查（印 0 即本句仍為真）：`python -c "import pathlib;print(len(list(pathlib.Path('docs/06_quality').glob('CrossPlatform_R86_Review_*.md'))))"`
3. 🔴 **本輪 Windows 側零真機量測。** 凡本檔提到 Windows 的地方一律是靜態推論。
   現查（落款輪次 < 86 即本句仍為真）：`grep -n "snapshot-fingerprints-win32" ONBOARDING.md`
4. 🔴 **本輪的 −5 是「量測面內的減法」，不是總量的減法。** 見 §3 那段紅字，**不得讀成「護欄層瘦了」**。

<!-- absent-if: measured-at=2026-08-12 host=Windows -->
<!-- absent-if: R86 / 四方複審 -->

---

## §1 一句話總結

**R86 是第一次「六包串行 ＋ 舵手在批間裁決」的一輪，也是 `_GUARD_LINES_REPIN_LOG` 歷來第一個負淨額輪。**
三個主要產出：
1. **訴求 2 的到期義務兌現**：淨額 `+5400 → +5260 → +3755 → +637 → **−5**`。🔴 **但只在量測面內**（§3）。
2. **訴求 6b 的演算法真的落到程式**：跨窗攤提 ＋ 換算比 `r` 由歷史差分推估 ＋ horizon 相對窗長 ＋ 燃燒率；
   `--pace` 第三行印出全部中間量 ⇒ **舵手不再需要手算**。
3. **11 筆被實測推翻的自我宣稱**（見計畫書 §3.5），含推翻 R85 自稱「本輪最有價值的單一洞見」的分桶結論。

---

## §2 掌舵者訴求逐條結算

> 四級判定：**達成／部分／未達成／做不到（附結構性理由）**。

| 訴求 | 判定 | 依據 |
|---|---|---|
| **1** 兩平台零相容性問題 | **做不到（今天不可查證）** | Windows 零真機 ＋ 雲端 CI 本輪零量測（額度用盡、依注⑥零 push）。mac 半邊四閘門全綠（§5.1） |
| **2** 架構簡潔／拿掉不合理機制 | **部分（量測面達成、總量未動）** | 淨額 **−5**（歷來首個負值）；手段＝史前列整列搬出 −192／理由欄壓索引 −180／模組層敘事 −21。🔴 **但那是搬到 `docs/`，總體積一行未少**。**整支移除機制數仍＝0**（M-B 連三輪） |
| **3** 兩邊不落差 | **未達成（未量）** | M5 注入矩陣需 `--apply` ＋停工窗口，六包串行始終有人在動 ⇒ **一次都沒跑**。這是「未量」不是「惡化」 |
<!-- absent-if: R86 / M5 注入矩陣 -->
| **4** Windows 低級錯誤根因 | **部分（首個機械物落地）** | Stop hook `check_claim_provenance.py`（真實面命中 13/478、**假陽性 1**）。🔴 同輪訂正其立案數字：桶內 **195/201 是帳本列**，只有 6 筆是逐字稿原文 ⇒ **桶大是因為我們寫了很多次這個病** |
| **5** 挖深清債 | **達成** | 帳本逐列 bytes 全部 ≤700、存量超標總量**精準貼齊上限 82,896**、零豁免新增；治理文件 36→40 份皆已登記 |
| **6a** 隨時監控 | **達成** | 伺服器端算好的 %，分母不在本機 |
| **6b** cap＝f(水位, 距 reset) | **達成，且演算法本輪治本** | 見 §4 |
| **6C/6c** 85 準備／95 停止 | **達成，且本輪真的觸發** | 收輪時 `band=prepare`（攤提後本窗餘裕 −15.6pp）⇒ 舵手據此**停止派新包**並改走「收斂 70%」出口 |
| **6d** 同 session 續跑 | **部分（武裝端首次驗到「綁對 session」）** | `launchctl list` 列出 `AutoSDD_Sentinel_ab089d8d-…`，**session ID 與本 session 逐字吻合**、rc=0。🔴 撞線→喚醒端仍零驗證，且本輪確認它是**結構性兩難**：短窗 reset 是正常節律、不觸發 `arm_reset`，要驗證**必須先真的撞線一次** |
| **6e** 撐過 0~5h | **部分（沿用 R85）** | R85 已實測否決「每 50 分鐘」；mac 解＝`caffeinate`。本輪未新增量測 |
| **6f** `.env` 實測調優 | **部分** | 本輪新增 4 個攤提門檻**刻意無 env 鍵**（`quota_policy.py` 餘裕實測只剩 4 行，須先拆 env 層）⇒ 已具名交棒 |
| **6z** 前沿調研 | **達成** | 新增一筆**外部獨立校準基準**（掌舵者貼出的 CLI 畫面），已落成 `CrossPlatform_R86_Pace_Calibration.md` |
| **7** Windows 彈窗 | **未動** | 本輪零處置 |
| **8** Container 整理 | **未動** | 本輪零處置 |
| **S1** skipped | **判定收窄：根層做不到、AutoClaude 側有路** | 根層 44 支全 `[WINDOWS-NATIVE-ONLY]`＝mac 結構不可執行；**但 AutoClaude 側 11 支 `[ENV-DISABLED]` 有已登記的治本路徑**（`make_service` fake-executor 重寫成 hermetic）⇒ R85 的「做不到」是**判定過寬**。本輪未實作（配額） |
| **S2** 帳本警告線 | **未達成** | 未結 89 → **91**（warn 86／fail 98，**距 7 筆**）。淨增 2 列，26 列改派至 R87 |
| **M6** 判準粒度 | **達成（結構性升級）** | 剖面／計數 → **test-id 集合**；門檻由 2 條加嚴為 **3 條**（新增「不可求值不得讀成達標」）；現況＝**不可求值** |
| **注③** Archive | **未動** | 沿用 R85 盤點 |
| **注⑥** 先本機驗證 | **達成** | 全程零 `push` 試探 |

---

## §3 訴求 2 的量化（到期義務兌現，但射程要看清楚）

| 量 | R84 | R85 | **R86** | 判定 |
|---|---|---|---|---|
| **M-B 整支移除機制** | 0 | 0 | **0** | ❌ 連三輪 |
| **M-C 護欄層單輪淨額** | +3755 | +637 | **-5** | ✅ 首次為負 |

<!-- guard-total:R86 --> **本輪護欄層累積淨額＝ 83475 → 83470（-5）** `[收尾單人窗口、六包全部停工後當回合實測；憑證＝--print-guard-lines 印「淨額 83470→83470 (+0)」且「逐檔漂移 0 支」]`

🔴 **Arch 包的誠實劃界（它要求務必寫進本檔，我完整照收）**：
> **本輪的 −5 是量測面內的減法，不是總量的減法。** 行從 `tools/tests/*.py`（棘輪量測的那個面）
> 搬到 `docs/`，棘輪的數字變好，而「護欄層＋文件」的總體積**一行都沒有少**。
<!-- absent-if: R86 / 護欄層總體積淨減 -->
> 這句話已同時寫在 `_GUARD_LINES_REPIN_LOG` 的 R86 理由、兩個 guard-total 標記站點、以及證據檔檔頭
> ——四處同源，避免下一輪把它讀成「護欄層瘦了」。

🔴 **R86 覆核 R85 §5.4 那筆訂正的結果（R85 要求 R86 查兩件事）**：
① `_NET_SUBTRACTION_DUE_ROUND = 86` **未被往後挪**；
② 到期輪一到，`repin_round_nets()` 末列為 `(86, −5)` ⇒ **≤0 出現了** ⇒ **那筆訂正未退化成放寬**。

🔴 **`_bail` 併家實測後決定不做**（Arch 以 rc 而非判斷決定，理由三條，具名交棒 R87）：
`run_root_unittests.py` loc **754 / budget 754＝餘裕 0**；既有鎖自陳射程只管一支工具；
且**兩個 `_bail` 不是真同義**（一個說「一支測試都沒執行」、一個說「還有哪幾道沒跑」，後者需 `_CHECK_ORDER` 有序登記表，而它加不進 754/754 的檔）。

🔴 **分桶棘輪在落地當輪就抓到一個真缺陷**（`CrossPlatform_R86_Scan_Findings.md` §F-4）：
它對搬家報 `prose +60`，逐單元追查後成因**不是**散文長了，而是**分類器瞎了一族**——
`BUCKET_TREES` 登記的 `.claude/hooks/`／`.claude/settings.json`／`.github/workflows/`
因 token 抽取器要求以英數起頭而**結構上永不命中** ⇒ `root_infra` 被系統性低報。
修正後 prose **4464 → 4119**、`root_infra` **8308 → 10025**，基準同步**下修＝更嚴**；
缺口已上機械物 `dead_tree_prefixes()`（登記卻抓不到即紅，現值 `[]`）。

---

## §4 訴求 6b：演算法本輪真的落到程式（不再靠模型判斷）

`--pace` 第三行現在印出攤提全部中間量，例：

```
攤提：weekly_all 剩 19pp／距 reset 4463 分鐘 ÷ 14.9 個 session 窗 = 每窗 1.28pp
      ×r=6.6（n=1<3 樣本不足 ⇒ 保守取 min）⇒ 本窗配額 8.4pp；
      session 已用 24pp 剩 263 分鐘 ⇒ 本窗餘裕 −15.6pp
```

| 缺陷 | 修法 | 方向鎖 |
|---|---|---|
| horizon 絕對門檻**雙向**失效（`five_hour` 窗 300 分 ＜ 門檻 360 ⇒ **永不減速**；`seven_day` 門檻僅佔窗長 **3.6%** ⇒ **96.4% 恆減速**） | `near = 窗長×(accel_window/300)`、`far = 窗長×0.5`；窗長由**文法**解出（不是桶名表——實測 `schema_keys` 已有 5 個 `seven_day_*` 桶，表對它們整片失明）＋同 reset 繼承 | 解不出**不偽造**，退回既有絕對門檻；兩個既有 env 鍵未消失且多一個「不准比它更鬆」的夾層消費者 |
| 燃燒率失明 | `lead_pp = pct − 100×elapsed`；**超前⇒任何幅度都減速，省⇒須越過 anchor 邊際才放行** | 不對稱是刻意的（加速須有證據、減速不須）。🔴 實測否證逐秒版本：兩個不同窗長的軸 `resets_at` 秒尾同為 `:59:59.288` ⇒ 伺服器另有小時級 snap ⇒ 推導只在小時精度成立 |
| 跨窗攤提缺席 | `amortize()`；`r` 由 `~/.autosdd/traces/quota_burn.jsonl` 相鄰差分推估，量化保守取下界，`n<3` 取 min 並逐字說「樣本不足」 | 攤提**只調高**餵給 `pct_band` 的水位 ⇒ 結構上不可能放寬；封頂 `halt−1` |
| `cap` 旋鈕語意錯置 | **本輪只做上半場**（攤提讓 cap 有正確依據）。旋鈕語意分離（併發度←短窗／總工作量←長窗）**未做** | 已具名交棒 §9 |

**驗收（SA 當回合實測）**：今天真實快取下逐軸**更寬鬆＝0 筆**；全域 cap 舊 2 → 新 **1**（binding 由 `seven_day` 變 `five_hour`）。
**攤提中間量與舵手手算逐項吻合**（15.12／1.65pp／24.8pp／+8.8pp vs 手算 15.1／1.66／25%／+9）。

🔴 **本輪抓到的下游缺陷（R87 應優先修）**：`quota_gate.py:338` 的快取 TTL＝**180 秒**，
而**它短於任何東西刷新那份快取的間隔**（唯一刷新者是 Claude Code hook，只在有 session 打工具時才跑）
⇒ **手動叫 `--pace` 多半落在 stale 帶，印出的可派數是 degraded 地板、不是量測值**。
本輪舵手整輪看到 `binding=seven_day` 是因為 hook 一直在刷＝**運氣好，不是機制可靠**。
訊息已改為說出「哪一種量不到」；同一族資料上現有**三個 TTL**（180／900／1800），WHY 已收進證據檔一處。

---

## §5 R87 首日要做的事

### 5.1 開工前先確認基線（照順序，全部讀 rc 不接管線）

```bash
r=$(git rev-parse --show-toplevel) && cd "$r"
cd AutoClaude && docker compose -f docker-compose.ci.yml up -d; echo rc=$?    # 🔴 檔在 AutoClaude/，不在 root
cd "$r" && .venv/bin/python -c "import sys;sys.path.insert(0,'AutoClaude/tools');import local_ci_gate as G;print(G.pg_autodetect())"
   # 🔴 PG 就緒憑證＝pg_autodetect() 回出 DSN，不是 docker ps 的 healthy
.venv/bin/python tools/run_root_unittests.py; echo rc=$?
   # 🔴 R86 起早退會印「本次在〈階段〉早退 ⇒ 一支測試都沒有執行」。**沒有 FAIL 行不代表通過。**
cd tools/tests && ../../.venv/bin/python -m unittest discover; echo rc=$?
cd "$r" && .venv/bin/python tools/check_defect_log_crossref.py; echo rc=$?
.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
cd AutoClaude && ../.venv/bin/python -m pytest tests -q; echo rc=$?
cd ../AISDLC_SDD && bash scripts/ci-gate.sh; echo rc=$?
```

**R86 收輪實測（四大閘門全綠）**：根層 unittest `Ran 3315 OK (skipped=44)` rc=0／
AutoClaude pytest `4586 passed / 73 skipped` rc=0／SDD ci-gate `v0.01:1478＋v0.30:1747＋scripts/tests:344` rc=0／crossref rc=0。

🔴 **R86 訂正 R85 §5.1 的兩行假事實**：`docker compose` 與 `alembic` 在 repo root **都不可執行**
（兩檔實住 `AutoClaude/`，且 alembic 還需先注入 DSN）⇒ 立案 `DEF-200-105`。
**交棒書的指令清單至今沒有任何機械物在守它可執行**，這是 R87 可以做的一支便宜判準。

### 5.2 R87 的三件最該先做

1. 🔴 **四方複審（R86 欠的）**：本輪六包交付**全部只有作者自證**，第三方注入面為空 ⇒ M3 結構上不可能達標。
   複審前**先宣告凍結點**（R85 教訓 6 ＋ R86 實證：帳本包在複審中兩度撞到「別包剛落檔、登記稍晚」的假紅）。
2. 🔴 **`--pace` 的 TTL 缺口**（§4 末段）：180s 短於任何刷新間隔 ⇒ 該值該調、或該讓 `--pace` 在 stale 時
   自己補量一次（它已經有那條路，只是沒走）。**這直接決定訴求 6b 的機制今天可不可靠。**
3. 🔴 **M5 注入矩陣**（本輪一次都沒跑）：需 `--apply` ＋停工窗口。**R87 請在開工第一件事就跑它**
<!-- absent-if: R86 / M5 注入矩陣 -->
   （那時工作樹最乾淨），不要留到收尾——本輪就是留到收尾而始終沒有窗口。

### 5.3 Windows 真機清單（沿用 R84 §5.2，本輪仍一項未驗）

```powershell
Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR '.venv\Scripts\pythonw.exe')   # 必須 True
$hookLog = Join-Path $env:TEMP 'autosdd_r87_hooks.log'
claude -p --model haiku --debug hooks --debug-file $hookLog "ok"
Select-String -Path $hookLog -Pattern 'Hook SessionStart.*success'          # 有 success 才算活著
Get-ScheduledTask | Where-Object TaskName -like 'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime
```
🔴 **驗收條件是正負兩面一起看**：「不閃窗」單獨成立**不算**通過（那正是 fail-open 的表徵）。

### 5.5 成熟度 M1~M6（判準 SSOT＝[`CrossPlatform_Maturity_Criteria.md`](../06_quality/CrossPlatform_Maturity_Criteria.md)）

| # | 判定 | 理由 |
|---|---|---|
| **M1** | ❌ | 合取兩半。**護欄行數半首次開始計數**（R86 淨額為負，連五輪加法後第一個非上升輪）——但門檻是「**連續三輪**不上升」⇒ 本輪是三輪中的第 1 輪。UEP 回執半：R85 實查回執列數＝0，本輪未動 |
| **M2** | ❌ | 門檻＝連續三輪假宣稱 ≤1。本輪計畫書 §3.5 登記 **11 筆**被實測推翻的宣稱。🔴 **且四方複審未執行 ⇒ 這 11 筆全是自查，第三方分母為 0** |
| **M3** | ❌ | 門檻＝新增判準的**第三方**注入 100%（作者自證不計分）。本輪六包**全部只有作者自證** ⇒ 第三方面為空。**這一格相對 R85 退步**（R85 有四方各自的獨立注入） |
| **M4** | ❌ | 門檻＝一輪 0 筆。本輪修掉多筆散文≠實作（`.env.example` 的「引擎只在 halt 才動作」已為假／`quotepath-ok:` 被散文鑄成真標記／R85 分桶結論不可複現／**鐵律二被寫成 Windows 專屬而實測 mac 的 Bash 工具同樣 cwd 跨呼叫持續**） |
| **M5** | ❌ | 🔴 **本輪一次都沒跑**（`--apply` 需停工窗口）⇒ **未量，不是惡化** |
<!-- absent-if: R86 / M5 注入矩陣 -->
| **M6** | ❌ | 判準本輪升為 **test-id 集合**、門檻 2→**3 條**；當輪答案＝**不可求值**（win32 無 id 落款）。距離＝在真 Windows 上跑一次同一支 runner 並把落款填進 `docs/06_quality/skip_id_ledger.json` |

**總判：0 / 6**，與 R80~R85 相同。

🔴 **本輪與 R85 的實質差異（兩個方向都要說）**：
- **前進**：M1 的護欄行數半首次開始計數；M6 判準粒度從結構上補齊；訴求 6b 演算法落到程式。
- **退步**：M2／M3 的第三方分母由「非空」變回「空」——因為走「收斂 70%」出口而未執行四方複審。
  ⇒ **R87 的第一件事就是把這一格補回來**。

---

## §6 方法論收穫（每條附「為什麼它會再犯」）

1. 🔴 **一句舉例會被鑄造成一個真的豁免標記／真的分類依據。本輪出現兩次。**
   ①Dev 包在註解裡寫「沿用既有豁免慣例」時**逐字寫出 `quotepath-ok:`**，而那就是 `_QUOTEPATH_OK_MARKER`；
   ②SA 在 `tools/tests` 註解寫 `docs/06_quality/<檔名>` 路徑，讓分桶把整塊歸進 shrink-only 的 prose 桶。
   **為什麼會再犯**：舉例在寫作上是好習慣，而「這個字面同時是掃描器的輸入」不會寫在任何地方。
   加上 R85 教訓 1，**這一族已出現三次**，是本 repo 最穩定的復發形態。
2. 🔴 **取數要用鎖自己的函式，不要自己拼一把尺。本輪也出現兩次，且都是同一把錯尺（位元組 vs 顯示寬度）。**
   ①Dev 用 `awk length`（預設 locale 算位元組、中文一字 3 bytes）量到 15165，而棘輪實際 153；
   ②Arch 按 `len()` 折行後實測 **155 > 139**，全部重折才回 139——那道鎖量的是 **East Asian Width（CJK 佔 2 欄）**。
   **為什麼會再犯**：`awk length`／`len()` 看起來就是「量長度」，而「這道鎖用的是另一種長度」要讀實作才知道。
3. 🔴 **鎖把「性質」綁在「字面」上，就會擋住讓那個性質變強的修法。** 一道鎖要求 `return 1` **逐字**出現，
   於是 `return _bail(...)`（同樣 rc=1，只多印一行）被判紅。修法＝**量行為不量字面**。
4. 🔴 **「最短可行」不等於「正確」。** 舵手要求「最短的改派字樣」，實作者實測發現純最短版（39 bytes）
   會讓另一道棘輪停在紅——因為「改派**至** R87」不落在承接樣式的 regex 內。正確版是 30 bytes 且**機器可解析**。
   **為什麼會再犯**：省 bytes 是可量的，「機器解析得到」不是。
5. 🔴 **半成品文件會讓一批「只有收輪者滿足得了」的鎖提早生效。** Arch 把一個測試站點放進自建的交棒書種子檔，
   當場多兩筆紅（`TestR78HandoffClaimsCarryLiveCommands` 兩向對只有一節的種子檔零射程）⇒ 它撤回並刪檔，
   **而那次刪除連帶刪掉了收尾窗口已寫好的完整交棒書**（未追蹤檔、git 無備份）。
   **為什麼會再犯**：派工時把「文件」當成無主資產，而它其實有持有者。
6. 🔴 **舵手層的失誤今天零機械物，而且會連續復發。** 本輪舵手自陳**5 筆真實失誤**：
   ①憑推測給錯行數射程（宣稱先於查證）；②派工未切分帳本／治理登記面；③看到帳本 `M` 就推斷是別包改的（實為自己）；
   ④**背景指令末尾接 `echo` ⇒ 讀到假 rc=0，真值 rc=1**（讀 rc 陷阱的第三種變體，CLAUDE.md 只記載了前兩種）；
   ⑤派工未把交棒書劃入自己的持有面（導致它被別包刪除）。
   **為什麼會再犯**：所有現行判準的射程都在「repo 內的檔案」或「工具呼叫」，而舵手的判讀與派工
   **只存在於 `SendMessage` 內文與對話裡**，永不變成檔案。
7. 🔴 **自我批評同樣可以是未經查證的宣稱。** 舵手在 ④ 之後連續三次「修正」一個**不存在的** cwd 問題
   （實測 `pwd` 一直都是對的），而真正的原因（`test_push_and_pr_paths_symmetric` 不對稱）第一次就修對了。
   其中一次的工具 description 還逐字宣稱「with explicit absolute cd」而**指令字串裡根本沒有 cd**。
   **為什麼會再犯**：認錯在對話裡看起來一定是進步，而「這個歸因有沒有查過」沒有人在問。
   ⇒ 這一筆與第 6 筆合起來是 R87 最該補的**輸出面**判準：**凡宣稱一個根因，必須附一條當回合真跑過的鑑別指令。**

---

## §7 誠實劃界

- **Windows 側零覆蓋**：本輪一次都沒上 Windows 真機。
<!-- absent-if: measured-at=2026-08-12 host=Windows -->
- **雲端 CI 零量測**：額度用盡 ＋ 依注⑥零 push ⇒ 有一整類未結缺陷（解鎖條件寫「要 Windows CI」）**結構上結不掉**。
- 🔴 **本輪的 −5 是量測面內的搬家，不是總量的減法**（§3 那段紅字）。
- **四方複審未執行** ⇒ 六包**全部只有作者自證**，M2／M3 分母為空。
- **M5 注入矩陣一次都沒跑**（需停工窗口，而本輪始終有人在動工作樹）。
<!-- absent-if: R86 / M5 注入矩陣 -->
- **`--pace` 的可靠性未確立**（TTL 180s 短於刷新間隔）。
- **`_bail()` 現在有兩個家**，且實測**併家會淨增**（`run_root_unittests.py` 餘裕已為 0）⇒ 需先騰出 LOC 預算。
- **「就地改寫既有承接輪號字面」這條路徑零機械物**：硬規則② 只比大小，改寫與追加對它完全等價 ⇒ 下一次同樣靜默。
- **Arch 階段一盤點的「餘裕 44」實際上是 0**：帳面 −393 被加項與棘輪副作用吃掉大半。

---

## §8 禁止事項

1. 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准 `--allow-pg-extras`。
2. 🔴 不准任何毀滅性 git；並行包**連 `git stash create` 都不准**。
3. 不准為了讓紅變綠而刪測試／改成不比較／加 `skip`／放寬棘輪。
   本輪具體形態：`OVERSIZE_ROW_CEILING` 與存量超標總量是**相等**斷言（多一 byte 是成長紅、少一 byte 是「常數與實測不符」紅）；
   `_NET_SUBTRACTION_DUE_ROUND` 只准往前挪。
4. 🔴 等長跑時不准裸 `pgrep -f <字面>`、不准 `nohup <cmd> &`；
   **且 `until` 條件的 pattern 不得在同一條指令的任何其他位置出現純文字複本**（本輪實證：`echo` 裡的說明文字
   讓已經做對的字元類自我否定整個失效，失敗表徵是「它還在等」＝與正常進行相同）。
   🔴 **另加一條（本輪新增）**：**背景指令末尾不得接 `echo`**——通知回報的是整條指令的 rc，接了 echo 就恆 0。
5. 🔴 突變／注入實驗一律在拋棄式副本上做。
6. 🔴 **派工前先切鎖的持有面**（常數／史料／消費端），並**明文列出帳本、治理登記面、交棒書歸誰**——本輪舵手漏了後兩者。

---

## §9 交給 R87 的待辦

1. 🔴 **四方複審（R86 欠的，最高優先）**——見 §5.2 第 1 項。
2. 🔴 **`--pace` TTL 缺口**——見 §4 末段。
3. 🔴 **M5 注入矩陣**——開工第一件事就跑。
4. **`_bail()` 併家**——實測需先騰出 `run_root_unittests.py` 的 LOC 預算（現 754/754），詳見 `CrossPlatform_R86_Scan_Findings.md` §F-5。
5. **`waitform_hits()` 新判準**：比對「`until` 條件裡的 pattern」與「同一條指令其餘文字」有無交集，有交集即紅。
6. **S1 的 AutoClaude 側 11 支 `[ENV-DISABLED]`**：用 `make_service` fake-executor 重寫成 hermetic ⇒
   那 11 支會變成**兩平台都跑得到**。**這是 S1 首次出現的可執行路徑。**
7. **帳本 26 列改派至 R87 已到期**：R85 三方獨立驗證過「84 列次只找到 3 列真的已修」⇒ **需要一輪專門處理**。未結 91、fail 線 98，**距 7 筆**。
8. **攤提四個新門檻無 env 鍵**（`quota_policy.py` 餘裕實測只剩 4 行）⇒ 須先拆 env 層。
9. 🔴 **舵手層失誤零機械物**（§6 第 6、7 條）——需要的是**輸出面**判準：
   **凡宣稱一個根因，必須附一條當回合真跑過的鑑別指令。**
10. **鐵律二的射程訂正**：根 `CLAUDE.md` 把「cwd 跨呼叫持續」寫成 Windows／PowerShell 專屬，
    而 mac 的 Bash 工具同樣如此（工具通知逐字說「Session cwd remains …」）⇒ 該節需補平台中立說明。
