# CrossPlatform R108 四方複審紀錄（架構輪・第一審）

- 輪次：R108（架構輪；標的＝兩份設計文件，本輪不動生產代碼）
- 日期：2026-08-28
- 審查者：Architect／SA／SD／QA 四鏡（獨立 Opus subagent，唯讀複審、zero-trust 親驗）
- 標的：
  1. `docs/04_planning/ADR/ADR-XPLAT-014-resume-chain-hardening.md`（DEF-200-231 續跑鏈三缺陷設計）
  2. `docs/04_planning/PRD_Amendment_R108_Pacing.md`（修憲級配速批：DEF-200-197/198/199＋配速三改動 a/b/c）
- 收斂協議：依 Playbook §8.1——blocking 全修才可送裁決／落款；複審收斂上限 2 輪，發散即停損。

## 一審判決表

| 鏡 | ADR-XPLAT-014 | PRD 修憲案 |
|---|---|---|
| Architect | APPROVE_WITH_CONDITIONS（4 blocking） | **REJECT**（5 blocking；§2/§3/§4.2-L1 三塊逐數複現全對、可原樣過） |
| SA | APPROVE_WITH_CONDITIONS（0 blocking、4 non-blocking） | APPROVE_WITH_CONDITIONS（4 blocking，全在 §6 修憲文本） |
| SD | APPROVE_WITH_CONDITIONS（2 blocking） | APPROVE_WITH_CONDITIONS（1 blocking） |
| QA | APPROVE_WITH_CONDITIONS（2 blocking） | APPROVE_WITH_CONDITIONS（1 blocking） |

溯源品質（四鏡一致）：抽驗座標與數字近乎全中（SA 21 處引述零失真；SD 40+ 座標僅 1 函式名錯；QA 24 筆抽驗 23 筆獨立複現、零編造；Architect 抽驗全中）。**blocking 全部是「架構歸屬／宣稱射程／落地連鎖」，不是數字造假。**

## Blocking 清單（B1~B19）

### ADR-XPLAT-014（B1~B8）

- **B1（SD）§2.2/§2.3**：F1/F2 兩道不夠——`quota_messages.halt_resets_at()` 在無 halt 軸時 fallback `binding_resets_at()`，回 binding 軸的遠未來 reset（探針實測 seven_day、now+6000 分）照樣通過 F1/F2 ⇒ 人在未撞線時跑 `--register-schtasks` 會排出 4.2 天後的排程。需第三道判準（如 `decision.band ∈ {halt, unmeasured}`，或沿用 `reset_branch()` 既有 6 小時視界上界）。
- **B2（SD）§落地物/§7**：落點檔 `tools/session_resume_planner.py` 實測 749/750 行（`check_loc_budget --json`）、刪 `DEFAULT_AT_EXPR` 僅釋 1 行（`#:` 註解不計 LOC）⇒ 三項改動全落此檔結構上放不下；§7 必須先排「抽共用模組」前置格（前例：鎖檔 `:947` 記載同一面牆）。
- **B3（Architect）§2.2**：時刻解析與 `ADR-XPLAT-005` §2.7 既有裁決重複造家——該節已裁「endpoint-authoritative → transcript/probe-verbatim → 拒絕武裝」，L3 把同一值命名為 `meter-observed`＝同一份知識第二個家；並漏了 A5「`resets_at` 比較與去重一律截到分鐘」（少它每次巡邏都判 reset 變了）。兩份 Proposed ADR 對同一欄位的狀態字必須先合一。
- **B4（Architect）§4.4**：L-a（PostToolUse）蓋不到 DEF-200-231③ 的立案窗口——`ADR-XPLAT-004:114/:363-364` 已判「額度耗盡＝API 層失敗，Pre/PostToolUse 一次都不會被叫到」；§4.4 論證 1（「沒人用時哨兵活著不重要」）在續航情境為假（立案那晚正是沒人用、且有工作要續）。修法＝正文與標題改「縮小失明窗口」、劃界軸改「額度耗盡使 session 發不出工具呼叫之後」、明說立案窗口落地後仍只有 L-c（人）。
- **B5（Architect）§2.2 約束 3**：L0 借用 `operator` 狀態字換了鑑別軸——`planner:486-487` 白名單的軸是「有沒有在宣稱 reset 時刻」，人打 `--at 14:00` 正是在宣稱 ⇒ 需自立字面（如 `operator-asserted`）或連同判詞改寫。
- **B6（Architect）§3.4/§3.5 Q4**：本 ADR 自己新增第三處 PRD↔實作歧異（PRD `:1093-1104` 建議帶 `--allowed-tools`，設計刻意不帶）卻沒進 Q4 裁決清單 ⇒ 掌舵者會在不完整清單上拍板、下輪稽核重開（DEF-200-206 族）。
- **B7（QA）§2.2 L4/§2.4/§6**：L4「拒絕武裝」缺兜底判準——§2.4 自己寫「L4 之後正確的下一步是確保哨兵在武裝著」，但 A1~A5 無一條驗它、§7① 規模沒算它 ⇒ 立案情境（哨兵已死＋解不出時刻）下 L4 是淨退化（今天至少排一支晚的，L4 之後什麼都沒有）。需新增 A6：L4 觸發後排程器現查必須存在哨兵工作且 NextRunTime 非空（憑證是值），不成立時先武裝哨兵再回 rc≠0。
- **B8（QA）§4.4 vs §5-4**：「主力」定位與誠實劃界矛盾（正文像解決了、劃界節承認沒解）——L-a 改定位「機會性自癒」（真實價值＝消除 `latched` 永久失明）；§6 缺陷③ 明載「無人期間的哨兵死亡在本設計下仍不可偵測」。（與 B4 同址，可合併修。）

### PRD 修憲案（B9~B19）

- **B9（SA）§6.2**：廢除 `T_MIN_MINUTES` 只改一半——PRD `:453` `V_safe = U_rem / max(T_MIN_MINUTES, T_rem)` 的除數用途未同步 ⇒ 落款後懸空引用。或保留除數角色只廢 hold 語意、或同步改寫 `:453`。
- **B10（SA）§6.1/§6.3**：新條文用 `cap`/`rec`、被插入的 §4.2.2/§4.2.3 用 `C_target`/`C_cap` 等八步 `C = …` 封閉列舉，無對映語句 ⇒ 沿 PRD 既有 `_PAIRS` 判例（v2.1.9）明文寫出 `C_cap↔cap`／`C_target↔rec` 再插新步驟。
- **B11（SA）§3.1**：承重句算術錯——「15 個取樣點全部落在不會擋人的兩格」實為 10+4=14，且 `cap=0` 落 halt 列（四格皆 0＝擋死非放行）。改「14/15」並註明第 15 點＝DEF-200-202 探針 429（M197-1 後結構上消失）。
- **B12（SA）§8.8/Q6**：低估爆炸半徑——PRD v2.1.9 `:549-555` 訂正的承重理由（「已由 §11.2 別條管」）被本案實測證偽（free 列四格 cap 皆 None）⇒ Q6 補此事實、§6 增列對 `:549-555` 的處置（最小＝標注該承重理由在 §11.2 落地前不成立）。
- **B13（SD）§2.3 M197-4**：`QuotaState.retry_after` 無寫入通道——M197-1 下 429 讀數在 `refresh_quota_blocking():621-625` 於 `write_cache` 前被丟棄、unmeasured 的 `QuotaState` 全出自 `_blank()`；且 TTL 180s 視窗內 hook 讀快取不讀那次 429。與 `account_key` 先例不同型（它只有一個寫入點）。需貫穿 `measure_detail→refresh_quota_blocking→_blank/read_quota`（跨 2 檔）的管線設計，否則 P3 判準恆綠無鑑別力。
- **B14（Architect）§4.2 L2**：L2 違反本案自己要入憲的 §6.1(4)「加軸 rec 不得變大」——L2 判準相對當次讀數的軸集合，加一條更長窗軸會把原最長軸重分類為 rate 軸（算例：加 monthly 後 weekly far×0.5→×1.0，rec 4→8）。同文件兩條文互相否定，不能落款。
- **B15（Architect）§4.2 L2**：「週軸結構上到不了 L2」是量測值非結構事實——`quota_pace.py:77-81` `_UNIT_MINUTES` 已含 `month/months: 43200`、`_PERIOD_MINUTES` 含 `monthly` ⇒ 伺服器回月桶當天週軸靜默進入射程。判準需絕對地板（入憲上界）或明文列舉，不得 `max(當次讀數)`。
- **B16（Architect）§4.2 L2**：指定的判準之家 `amort_for()` 拿不出逐軸分類——`amortize()` 只回最短/最長兩個 argmax，中間窗軸無分類（探針：三窗長餵入、1440 軸無歸屬）；`ratio=None` 時回 None。家應為 `quota_pace.windows()`＋一條入憲絕對判準。
- **B17（Architect）全文**：零 ADR 引用而動到 **Accepted** 的 `ADR-XPLAT-009` §2.2 裁決面（`core_signature` 的 `∩ KNOWN_KINDS` 定義與「未知桶名＝schema 演進不觸發攤提重置」理由）⇒ 同一份知識兩個家；且「取數面排除 SYNTHETIC_KINDS」在 Q1 建議（自造 kind 不進 KNOWN_KINDS）下建構上不可達＝死碼。
- **B18（Architect）§10 Q7**：v2.1.10 疊在一疊未生效修憲上（修訂表僅 v2.1.4 標已生效；v2.1.9 狀態＝REJECT 承接待再審），而本案多處前提取自 v2.1.8/v2.1.9 條文 ⇒ Q7 改問「v2.1.9 待再審期間本批能否落款；先決條件為何」，逐條標出依賴未生效版本的前提。
- **B19（QA）§7 P9 vs §4.3**：P9 期望「兩次 rec 相等」被本文件自己的實測表（A=4／A2=8）否定，且 §4.4 自承翻不動那個 4 ⇒ P9 把未裁決的 Q3 當已通過前提寫進驗收＝假綠產生器。改結構斷言（「binding 的 band 與供給乘數的 horizon 須來自同一軸」）或明寫 P9 綠面依賴 Q3 裁決為放寬、否則改記 known-and-accepted。

## Non-blocking 清單（修復包順手可收的）

- （SA→ADR）§3.2「這一類修實作不需修憲」過寬——判例有兩臂，`--max-turns` 屬「PRD 與實測不符」臂＝須修憲；標題句改窄。
- （SA→ADR）§6 C1~C3 與 PRD §4.5.8 已實作的 C1~C4 同號同語意，有被既有綠燈冒領風險——改號（C1'~ 或具名站點）＋加一列「差別＝求值站點」。
- （SA→ADR）L4 對「月度支出上限＝沒有 reset 可等」無格位（PRD §8-2 逐字要求 escalate）——L4 拆兩臂或 §5 具名劃界。
- （SA→ADR）§5 劃界漏一條同函式上的 PRD↔實作歧異：`RESUME_MAX_TRANSCRIPT_TOKENS`（token）vs `choose_resume_route()` 實為 byte 比較——補列（不必本輪修）。
- （SA→修憲）帳本 `:205` 點名「PRD §4.2 那張表」未被具名對應——明說指哪張表或明說本批不處置並記入 §8。
- （SA→修憲）§落款順序：v2.1.10 狀態欄應具名寫出「依賴 v2.1.8/v2.1.9，該兩版尚未完成再審」（與 B18 同修）。
- （SA→ADR）§3.2 對 PRD `:1104` 引述壓縮掉「使用者明確設定」——補回或加省略標記。
- （SD→ADR）`args.at` 有兩個消費端（`:1559` `--print-schtasks-command` 與 `:1562`），§7 鐵律七欄位漏印出面同步拒絕。
- （SD→修憲）§2.3/§8-6 函式名錯：`refresh_quota_cache` 全庫僅存於過期 docstring，真名 `refresh_quota_blocking`（`quota_gate.py:597`）；順帶：該項「未逐行複驗」已由 SD/Architect 本輪複驗成立，可改標已驗證＋正確座標。
- （SD→修憲）§9 W0~W6 七批序列與護欄棘輪 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2` 相撞、R109 另有淨額 ≤0 到期義務（`_REPIN_NET_CAP_DUE_ROUND=109`／target 610）——W2/W4 間插淨減法輪；§9 鐵律七檢查補「護欄層行數棘輪」持有面。
- （SD→修憲）本批 5 支生產檔 LOC 餘裕充足（`quota_policy` 261/400 等），與 ADR-014 落點相反，§9 值得明說；`quota_policy.py:503`「餘裕個位數」自陳已過期。
- （Architect→ADR）§5-5 `%TEMP%` 後果只對一半——`maybe_arm()` marker 不在時會重新武裝，真正靜默的只有 `liveness_line()` 回 "" 那條回報路。
- （Architect→ADR）`claim_once` 的家在 `tools/lib/quota_ledger.py:177`，消費端才在 `quota_gate`——鐵律七盤點寫清楚。
- （Architect→ADR）§3.2 方案 B 事實上回答了 `ADR-XPLAT-004:104` 掛著的「🔴 未解」——明文交叉引用，不留兩個家。
- （Architect→修憲）§5.1「(a) S 級可先行」與 §9 把 (a) 綁進 W3 自相矛盾、且改了 Playbook `:248/:257` 執行序沒說明。
- （QA→ADR）§6 A1 紅面是一次性的（判字面、刪後永綠）——改判形態（排程時刻運算式出現 `AddHours(`/`AddMinutes(`）。
- （QA→修憲）Q3 裁決包補量級：均勻網格實測 (a) 實際射程＝far 區 24.4%（2066/8484 格）、FAR 覆蓋 62.7%→50.6%（上界性質的量級感，非機率）。
- （QA→修憲）P8 紅面的「60」是出廠值導出量，勿凍成常數——P8 只斷言方向（放寬組數 >0）。
- （QA→修憲）§6.7 把自標未複驗的「15 取樣點中 cap=16 佔 4」寫進 PRD 條文——條文只留 DEF-200-198 座標，數字留提案書。
- （QA→ADR）DEF-200-231 帳本列「三項各自落地」與 §7 分批矛盾——§7 直接指定：①③ 落地時把 ② 拆新列（200- 家族），原列收斂為索引。
- （QA→修憲）197 結案前置：查 `quota_gate.quota_floor_reading()`（`:631`）同型性——明列為結案前置，不留劃界節。

## Q3（最重裁決項）獨立意見彙整

- **Architect 判定**：(a) thrifty floor 對週軸那一半**在否決射程內**——`anchor_margin_pp(10080)=0.595pp` 低於讀數量化階 1pp ⇒ 門檻無鑑別力，等於「沒超前就放行」；17,069 格網格實測 12.1% 由 far 翻 mid。**但否決可解除**：給 thrifty floor 自己的證據門檻（連續 N 筆節儉落款、或 `max(anchor_margin_pp, k×量化階)` 且 k 入憲），三條辯護即補齊。連帶：A 案鄰居會翻（週軸 40%→39% 使 rec 4→8）——「1pp 讀數變化讓扇出加倍」本身該進帳本。建議帳本 `:205` 改記 A 案＝known-and-accepted、另立一列記「thrifty 門檻在長窗上低於輸入量化階」。
- **QA 量化**：(a) 實際射程＝far 區的 24.4%（均勻網格上界）。
- **L2**：Architect 判不在否決射程內，但另有 B14/B15/B16 三筆 blocking ⇒ 兩者皆不應在本批原樣落款。

## 四鏡誠實劃界共通點（一審）

- 四鏡皆未跑任何測試／閘門（架構輪唯讀複審，零「全綠」宣稱）。
- 修憲案 §4.2 的 1422/2674/60 三數需先實作 L1 才能複現——QA 僅核母體算術自洽；落地包必須自己重導。
- 排程器現況、mac 側、排程器事件日誌一律未實測（ADR 自陳同）。
- DEF-200-198 的 15 個取樣點維持〔他包回報，未複驗〕。

## 附帶發現（射程外，交收尾窗口）

- （QA）`docs/04_planning/R107_RESUME.md:91/:113` 含完整 session UUID 且已隨 `b36767a` 進 Public 歷史——session id 只定址本機逐字稿、非遠端憑證，嚴重度低；要不要遮蔽交掌舵者裁決（遮蔽工作樹不改歷史）。
- （本輪主控實測）派第四鏡時 `context_budget_guard.py` 扇出節流真的攔下 Agent 呼叫（每 300s 上限 2 次、已用 3 次）——節流層會煞車的活體證據，DEF-200-198 結案時可引用（注意：擋的是扇出節流層，不是 cap 致動層，兩層別混）。

## 護欄層重釘逐檔清單

收尾單人窗口重釘（`_GUARD_LINES_REPIN_LOG` 本輪列指名本節為逐檔清單的家；淨額落款見 `CrossPlatform_R106_Scan_Findings.md` 與 `R108_HANDOFF.md` 兩處 `guard-total` 標記行）。

| 檔 | 舊 | 新 | 淨額 | 內容 |
|---|---|---|---|---|
| `tools/tests/test_quota_policy.py` | 3071 | 3152 | +81 | DEF-200-230 回歸鎖：`usage_url_homes()` 純函式＋`usage_url_scan_surface()` 全樹 tracked `*.py` 現查＋兩支測試（現況斷言、合成注入紅綠自證） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | 6282 | 6295 | +13 | 本輪稽核列（10）＋`_FROZEN_PREFIX_REWRITE_LEDGER` 追加列與其 WHY（3）；`_REPIN_LOG_FROZEN_PREFIX_LEN` 76→77、`_REPIN_LOG_HISTORY_SHA256` abd0dc217e2b→21c85dff06f9（就地改值，不計行） |
| **合計** | **89124** | **89218** | **+94** | 單輪上限 630（`_REPIN_NET_CAP_SCHEDULE` 末列 `(107, 630)`）；`_REPIN_NET_CAP_DUE_ROUND=109` 於本輪尚未到期 |

合法出口逐條實查（款(9) 要求的「不是淨減法輪」的明文承認）：無死碼可刪；抽共用層不適用（本判準只有一個消費端，抽層只會多一個沒人維護的家）；散文搬遷不適用（新增全是判準本體與注入語料，本輪未新增可搬的史料散文）。

非護欄層改動（不計入上表）：`tools/lib/governance_docs.py` 現為 350 行（登記本檔與 `CrossPlatform_R108_Sentinel_Forensics.md` 兩列＋各自 WHY；`guardrail_lib` tier 上限 400、本輪實測餘裕 50；`tools/lib/` 不在 `tools/tests/*.py` 行數棘輪掃描面內）。
