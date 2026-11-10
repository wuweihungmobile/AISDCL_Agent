# Test Contract Specification — SelfImproving P6（研究來源單一化：Console 登記鏡像入帳、安全抓取與文章展開；歷史缺陷反事實回測）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層單半，Console 端由另一把鍵交付）

**文件類型**: Test Contract Specification (TCS)　**SDD Gate**: SCG-4　**spec-format-version**: 1.0　**scenario**: brownfield
**使用時機**: 已凍結系統（PRD v0.14 於 P5 鍵 Stage-1 凍結）的單一 Feature（P6）；FSM 功能鍵 `monorepo-si-p6-registry-backtest`；`spec-frozen --doc` 指向本檔
**存放位置**: `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md`　**輸入快照**: HEAD `b562d063`（寫稿時現查，工作樹乾淨；本稿作者只讀 repo）
**建立日期**: 2026-11-10　**QA**: SCG-4 獨立 QA 棒（規格作者＝本 SD 棒，實作者＝Developer 棒＋主控〔收尾、真機、重釘〕，三方不同）　**SCG Gate**: SCG-4 □ 待審
**對齊**: 已對齊主控裁決 D-RR-11～18（kind 名、kind 值域、24576／65536 上限、`research.registry` 必帶欄、`status` 兩鍵、`arxiv-agents` URL、G-S1 由根層實作輪先產出）。
**範圍界線**: 本檔只涵蓋**根層**（`tools/`）。Console 端（登記 UI、`console.research_watch_sources` 表、Bridge `GET /research/registry`、同步端點、種子遷移、R2P TCS 勘誤；Console 端錯誤碼自成 `REGISTRY_` 家族）由 `agentconsole-research-registry` 鍵的 `TCS-ResearchRegistry-*` 交付；**共享附錄（A 公網位址表、B golden 鏡像、C 稽核檔位元組表、D 追蹤來源 URL parity 表）的唯一本文是本檔**；Console 端 TCS 不複製全文，只以「路徑＋表位元組 `sha256`」引用（sha 見本檔附錄 E），並各自加 AT 以該表為判定依據；**原則：Console 的接受集合 ⊆ SI 的接受集合**（Console 只能比 SI 嚴、不能比 SI 寬）。介面變動只能由 PRD 修訂產生，並同步改本檔附錄與 附錄 E 的 sha。

---

## 增量追溯表（BRIDGE §8.5；SCG-0～3 每個清單項一列；摘要取自 P5 鍵 `build/reports/fsm/FSM-STATE-monorepo-si-p5-expert-review.yaml` 的 `frozen_stages[*].spec_doc_digests`，寫稿時現查）

> **誠實揭露**：P6 自己的上位文件（PRD v0.15、SOP）於本稿寫成時**尚未在 P6 鍵凍結**，不能被引用為已凍結。下表分兩類：①**繼承項**（本 Feature 不改的清單項）追溯到 P5 鍵已凍結的 PRD v0.14／SOP／TCS-P5（摘要如下，`show` 可查）；②**P6 新增項**標 `P6-PENDING`，由主控在 P6 鍵完成 Stage-1 凍結後回填摘要；**未回填前不得 `spec-frozen --stage Stage-2`**。

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---|---|---|---|
| SCG-0／需求完整（FR 與 AC 皆有 Given-When-Then） | FR-SI-30（AC-30-1 繼承；30-2～30-10 P6）、FR-SI-45、FR-SI-46 | `docs/01_requirements/SelfImproving_PRD.md`（v0.15） | `P6-PENDING`（v0.14 繼承部分：`sha256:25bec84cd2fd99c95980a87050ada72201dfc7cfd50f390e6bf58b16b047795c`） |
| SCG-0／AC 可測且可判定 | AC-SI-30-2～30-10、45-1～45-8、46-1～46-8、自增 AC-P6-090-1～4 | 同上＋本檔 §1 | `P6-PENDING` |
| SCG-0／上位繼承：研究事件必有、四問、排程、Console 稽核通道 | AC-SI-30-1、FR-SI-33／35／36／38／39／41～44 | `docs/01_requirements/SelfImproving_PRD.md`（v0.14） | `sha256:25bec84cd2fd99c95980a87050ada72201dfc7cfd50f390e6bf58b16b047795c` |
| SCG-1／架構與元件落點（C4、模組落點表） | C26、C27、〈C4 套件檔案表（P6）〉；`Root_Layout_and_Module_Placement.md` §2 新增列 | PRD v0.15 §9.1；`docs/02_architecture/Root_Layout_and_Module_Placement.md` | `P6-PENDING`（PRD）；Root_Layout 非 FSM 凍結文件，以 `git` 版本為準 |
| SCG-1／資料模型與事件契約 | §9.2：`research.registry`、`backtest.result`、`research.scan` 新欄位、鏡像格式、回測資料格式 | PRD v0.15 §9.2 | `P6-PENDING` |
| SCG-2／重大架構決策有 ADR | ADR-SI-17、ADR-SI-18（PRD §9.5 加列、不開 ADR 檔，C.2 #15）；繼承 ADR-SI-03′、ADR-SI-10、ADR-SI-11、ADR-SI-14、ADR-SI-16 | PRD v0.14／v0.15 §9.5 | 繼承：`sha256:25bec84c…795c`（v0.14）；新增：`P6-PENDING` |
| SCG-2／安全與停機（外聯、鎖、預算） | PRD §9.4〈P6 增補〉；繼承 NFR-SI-01／02／09 | PRD v0.14／v0.15 §9.4 | 同上 |
| SCG-3／介面契約（CLI 動詞、事件欄位、稽核檔 body） | §9.3 `research`／`registry-ingest`／`backtest` 列；稽核檔 `kind=src-registry`（繼承 R94 外層、P2b 簽章） | PRD v0.15 §9.3；繼承 `TCS-SelfImproving-P2-20261021.md`（R94） | `P6-PENDING`；P2 TCS 摘要現查（非 P5 鍵凍結清單，標 `ADOPTED-BY-REFERENCE`，不引用為摘要依據） |
| SCG-3／OpenAPI delta | **無**（本鍵不新增、不改任何 HTTP 端點；Bridge／console-api 端點屬 Console 鍵） | — | — |
| SCG-4～6 | 不因增量而縮減（SCG-4 獨立 QA、RTM、RELEASE_READY 照走） | — | — |
| 下位繼承（本檔沿用的 AT 體例與同步站點） | `TCS-SelfImproving-P5-20261110.md`（AT 格式、驗收字樣、hermetic、`-k` 錨定） | `docs/03_testing/contracts/TCS-SelfImproving-P5-20261110.md` | `sha256:10662b64ab14f47db5581bb2e4a28999e37e78d70c267f23f4a38549ed58d2b1`（P5 鍵最新 refreeze） |
| 上位 SOP（無人運轉範本、研究者節） | SOP〈研究者〉〈無人運轉任務書範本〉〈反事實回測〉（新） | `docs/05_development/SelfImproving_Operations_SOP.md` | 繼承 `sha256:25ec8069b10964916f452d0e204375ffbd204e3a193b3084e2bc422dd9bb6eba`；P6 改版：`P6-PENDING` |

## FRD-lite（US／AC；AC 本文以 PRD v0.15 為準，本表只列編號與一句話，避免第二份真相源）

| US ID | User Story | AC ID | AC（一句話；全文見 PRD） |
|---|---|---|---|
| US-P6-01 | 身為掌舵者，我只想在一個地方設定研究來源，不要兩處各設一次 | AC-SI-30-2 | 預檢讀鏡像、事件綁定、逐來源再驗網域 |
| US-P6-01 | 同上 | AC-SI-45-1～45-3 | 稽核檔驗證碼序、原子入帳與冪等、鏡像綁定與手改偵測 |
| US-P6-01 | 同上 | AC-SI-45-4、45-5、45-6、45-7 | 巡邏自動入帳、指紋與 dirty-tree、舊表凍結、事件欄位與大小 |
| US-P6-02 | 身為主控，我要抓取器和研發工作流一樣安全，且讀得到文章全文 | AC-SI-30-3、30-5、30-6 | 增量 digest 改寫、預算、指紋排除 |
| US-P6-02 | 同上 | AC-SI-30-7～30-10 | DNS／釘 IP／SNI 安全閘、文章展開、HTML→純文字確定性、無人運轉複製擴及 |
| US-P6-03 | 身為掌舵者，我要知道提案器的診斷能力有沒有進步 | AC-SI-46-1～46-8 | 案例庫、prepare、answer、score、洩漏稽核、結果帳本、cleanup、status 與護欄 |
| US-P6-04 | 身為維護者，我要新增的模組守得住既有純度與範圍護欄 | AC-P6-090-1～090-4（自增） | 能力登記、`params.json` 與指紋不動、既有判準不退化、範圍守衛 |

**Before／After（寫稿時現查，`檔:行`）**：Before——`KINDS` 25（`evspec.py:28-33`）、`CAPABILITY` 62＝45 `ro`／10 `rw`／2 `net`／5 `exec`（`test_selfimproving_capability.py:338-346`）、`ITEM_IDS` 35（`evcheck.py:24-28`）、`PARAM_SPECS` 44 鍵（本表不改）、`CHECK_RULES_REV` 6（`params.py:13`）、`FINGERPRINT_EXCLUDED`＝{`research_sources.json`}（`params.py:17`）、`C_CLASS` 13 動詞（`unattended.py:23-24`）、`status` 17 鍵、`EVENT_LABELS` 25、`fetch.py` 只驗字串形態不做 DNS（`sources.py:93-105`、`fetch.py:154-198`）、`research --fetch` 預檢讀 `research_sources.json` 且要求已提交（`research.py:27-54`）；After——`KINDS` 27、`CAPABILITY` 72＝52／13／2／5、`ITEM_IDS` 35（判準併入既有三項）、`PARAM_SPECS` 44（`params.json` 位元組不變，sha256 `594494910f77f029060aa1b0f79767f1f74927331a81a14a14dc24ca86398e9c`）、`CHECK_RULES_REV` 6、`FINGERPRINT_EXCLUDED`＝{`research_sources.json`,`research_registry.json`}、`C_CLASS` 15、`status` 20 鍵（17＋`research_fetch_max`、`research_registry`、`backtest`）、`EVENT_LABELS` 27、抓取器做 DNS 全公網驗證與釘 IP。**不含**：Console 程式、真機（V-P6-1 登記→入帳→實抓、V-P6-2 K=5 回測，不入 AT）、research 內容品質（P）、子代理答題品質（P）、macOS 真機。

**編號**：FR 30、45、46＋自增 AC `AC-P6-090-1`～`-4`；AT 編號 `AT-6<FR 兩位>-<AC 序>-<序>`（承 `AT-130-*`、`AT-445-*` 先例：前三位＝階段碼與 FR 號）：`AT-630-*`（FR-SI-30）、`AT-645-*`、`AT-646-*`、`AT-690-*`（自增）；`E` 為負控。**AT 共 95（正控 58、負控 37）**；測試檔：RG＝`tools/tests/test_selfimproving_registry.py`（登記、入帳、check、舊表、事件）、NF＝`tools/tests/test_selfimproving_netfetch.py`（netguard、fetch、expand、htmltext、patrolrun 複製）、BT＝`tools/tests/test_selfimproving_backtest.py`（回測）、SY＝既有測試檔的同步編修與自增 AC（§2）；夾具＝`tools/tests/_selfimproving_p6_fixtures.py`（`px`，§3）。

**交付物與順序**：①夾具與既有測試同步站點（§2）先行（先把 `KINDS`／`CAPABILITY`／`EVENT_LABELS` 的期望值改為新值再寫碼，使紅燈來自「碼未到位」）→②`evspec6.py`＋`evspec.py`／`events.py` 併表（零行為變更：既有 AT 全綠才往下）→③`netguard`、`htmltext`、`expand`（純函式，先寫先測）→④`registry`（`validate`、`known_ids`、`mirror_binding`）→⑤`fetch.py` 改寫（釘 IP；注入縫 `resolver`／`connector`）→⑥`research.py`（預檢、展開、旁檔、`_scans`）→⑦`regwrite`＋入口 `registry-ingest`＋巡邏與 `status.console_pending` 接線→⑧`check` 三項判準與 `known_ids` 換呼叫→⑨`btcases`、`btscore`、`btwrite`、`btrecord`＋入口 `backtest`→⑩`status`／`PROOF-BACKTEST`／`issuemap` 標籤→⑪能力登記與重釘。每支程式完成立即跑該區 AT。
**提交程序（沿 TCS-P5 D-EQA-5、D-EQA-9）**：①規格 commit（PRD、SOP、`Root_Layout`、本 TCS）不含允許集合路徑；②規格與實作 commit 連續、同一次 push；③實作 commit 不得含 PRD、SOP、TCS；本機跑範圍守衛（AT-690-4-1）時才設 `SI_SCOPE_BASE=<規格 commit>`（相容舊名 `SI_P4_BASE_SHA`；可選 `SI_SCOPE_TIP`；勘誤 E-7）；開發期以 `-k "not AT_690_4_"` 排除；④本檔日後勘誤單獨 commit；⑤重釘儀式（`tools/tests` 新檔的 12 道鎖）另一 commit（主控收尾）。

---

## 1. AC → AT 映射

**共同判定指令**（逐 AT 另有指令者在表內「判定」欄標明）：`python -m pytest <檔> -k <AT 底線形>_ -q -p no:xdist -o addopts=`，預期 `1 passed`（rc 0）；AT 底線形＝把 `-` 換成 `_`（例 `AT_630_2_E_1`），尾端底線錨定避免 `-k` 前綴誤配。**預期突變**欄＝把該行改成「錯的」會使該 AT 紅（QA 逐條突變鏡要重跑）；`px`＝夾具建構器（§3）。

### AC-SI-30-2 來源登記鏡像與預檢（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變（改哪裡會紅） |
|---|---|---|---|
| AT-630-2-1 | RG | `px.repo()`：合法鏡像（golden 附錄 B）＋同 sha 的 `research.registry` 事件＋已開運轉；注入替身 `connector`／`resolver`。`research --fetch --run <RUN>` ⇒ rc 0、`research.scan` 一筆、其 `registry_seq`＝該事件 `seq`、`registry_sha256` 相等、無 `sources_sha256` 鍵 | `research.py` 組事件處仍寫 `sources_sha256` 或漏寫 `registry_seq` ⇒ 紅 |
| AT-630-2-E-1 | RG | 同夾具逐項變體（每項獨立 repo）：運轉已關（`RUN-NOT-OPEN`）；已有研究事件（`RESEARCH-ALREADY`）；無鏡像（`REGISTRY-ABSENT`）；鏡像多一空白（`REG-NORMAL`＋`REGISTRY-UNBOUND`）；鏡像存在而零事件、事件存在而鏡像被換成另一合法內容（皆 `REGISTRY-UNBOUND`）；11 筆啟用（`FETCH-MAX`）；啟用 0 筆（`ZERO-SUCCESS`）。⇒ 每例 rc 1、輸出含 `obs-draft:`、**替身 `connector` 呼叫次數 0**、事件帳本位元組不變 | 預檢順序或任一碼被刪／改名；預檢在發請求之後才判 ⇒ 連線次數 ≠0 紅 |
| AT-630-2-E-2 | RG | 鏡像檔**未 commit**（工作樹新檔、HEAD 無）且與事件綁定 ⇒ 預檢通過（`SOURCES-UNCOMMITTED` 已退場）；把凍結舊表在工作樹改壞 ⇒ 預檢與抓取結果相同 | 預檢仍讀 `git show HEAD:<鏡像>` 或仍讀舊表 ⇒ 紅 |
| AT-630-2-E-3 | RG | 啟用來源 host 不在 `hosts`（網域被停用）⇒ 該來源 `blocked`：rc 2、事件仍寫、`sources[]` 不含它、連線次數 0、OBS 草稿一列；另一來源 host 在清單內者正常 | 抓取時未再驗 host ∈ `hosts` ⇒ 該來源被抓、紅 |
| AT-630-2-E-4 | RG | 注入 `research.PAUSE_HOOK`（新模組自己的鉤子，位置＝全部來源抓取完成、取寫入鎖之前；不得沿用 `evwrite.PAUSE_HOOK`）：在鉤子內把鏡像換成另一合法內容並補一筆事件 ⇒ rc 1、`REGISTRY-CHANGED`、零新事件 | 鎖內不重驗鏡像雜湊 ⇒ 事件寫入、紅 |

### AC-SI-30-3 增量 digest、失敗集合、牆鐘（NF）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-3-1 | NF | 替身 `connector` 對 3 個來源回 200＋文字；已有一筆先前 `research.scan`（其中 1 個 `id` 同 sha、1 個不同、1 個新）。⇒ `changed` 依序 `false`、`true`、`true`；落地檔 `research/<id>/<sha12>.txt` 位元組＝回應位元組、`latest` 內容＝12 碼；事件 `sources[]` 依 `id` 位元組序 | `changed` 比對改成全 `true`；`latest` 不寫 ⇒ 紅 |
| AT-630-3-E-1 | NF | 逐例各一來源失敗（其餘成功）：`connector` 回 500（`http-status`）、拋 `TimeoutError`（`timeout`）、超 `research_bytes_max`（`too-large`）、`image/png`（`non-text`）、`Content-Encoding: gzip`（`encoding`）、`charset=big5`（`encoding`）、連線拋 `OSError`（`network`）。⇒ rc 2、失敗來源不入 `sources[]`、不以舊 digest 代填、各附一列 `obs-draft`；全部來源皆失敗 ⇒ rc 1、零事件 | 失敗來源仍入 `sources[]`／沿用舊 sha ⇒ 紅 |
| AT-630-3-E-2 | NF | 注入單調時鐘：第 2 個來源完成時已超 `SCAN_WALL_SECONDS` ⇒ 其後來源與全部文章 `timeout`、事件仍寫（rc 2）、已完成者保留 | 總牆鐘常數被改成不生效 ⇒ 紅 |
| AT-630-3-E-4 | NF | **請求鏈牆鐘（D-EQA-9）**：偽時鐘下一條鏈有 3 跳重導、每跳各耗 `research_timeout_seconds×0.4` ⇒ 該鏈總耗時 1.2× 逾時 ⇒ `timeout`（即使每一跳單獨都未逾時）；有 `expand.max=3` 的來源，索引與 3 篇文章各自一條鏈、每條 ≤ 逾時，單一來源總耗時上界＝(1＋3)×逾時；無展開來源上界＝1×逾時 | 牆鐘改成逐跳計或整次掃描共用一個 deadline ⇒ 紅 |
| AT-630-3-E-3 | NF | 重導 `https→http`、`https→https:8443`（見 AT-630-7-E-3）；鏡像內 `http://` 來源 ⇒ `REG-WATCH-URL`（預檢整次拒收） | 抓取器仍接受 http ⇒ 紅 |

### AC-SI-30-4 候選的來源解析（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-4-1 | RG | OBS 夾具列：`src=<鏡像停用 id>`、`src=<凍結舊表 id>`、`src=<鏡像啟用 id>` 各一 ⇒ `check` 的 `row.markers`／`ref.*` 皆綠；負控 `src=nope` ⇒ `SRC-UNKNOWN` | `known_ids` 少併舊表或少併停用 id ⇒ 對應列紅 |

### AC-SI-30-5 預算與 `params.json` 不動（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-5-1 | RG | 10 筆啟用＋5 筆停用 ⇒ 預檢通過；11 筆啟用 ⇒ `FETCH-MAX`；`research_fetch_max` 取自 `params.json`（值 10） | 把停用者也計入 ⇒ 第一例紅 |

### AC-SI-30-6 指紋（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-6-1 | RG | 合成樹複製真協定目錄：改 `research_registry.json`、改 `research_sources.json` ⇒ `fingerprint` 不變；改 `params.json`、`metrics.md` ⇒ 變；`FINGERPRINT_EXCLUDED == frozenset({"research_sources.json","research_registry.json"})`；`CHECK_RULES_REV == 6` | `params.py:17` 少一個名稱 ⇒ 紅 |

### AC-SI-30-7 抓取器安全對齊（NF）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-7-1 | NF | `netguard.is_public_ip` 對附錄 A 位址表逐列求值，全等於表中 T／F | `netguard` 少剝 `%`、少還原 IPv4-mapped、少擋多播／site-local ⇒ 對應列紅 |
| AT-630-7-2 | NF | **parity**：附錄 A 位址表文字（LF、`位址<TAB>T｜F`）的 `sha256` 常數＝`3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd`；測試先斷言表自身雜湊等於常數（Console 端 Bridge 測試斷言同一常數＝兩端同表）；表中每列再對 `netguard` 求值 | 表被改而常數沒改（或反之）⇒ 紅；兩端表不同＝兩端測試各自紅 |
| AT-630-7-E-1 | NF | `url_shape_problems` 與抓取器：`http://`、`https://h:8443/`、`https://h.:443/`（尾點）、`https://u@h/`、`https:///x`、`https://xn--e1afmkfd.example/`、`https://１２７.0.0.1/`、顯式 `:443` 合格 ⇒ 前七者拒絕；**替身 `resolver` 呼叫次數 0**（字面判準先於 DNS） | 字面判準放在 DNS 之後 ⇒ 次數 ≠0 紅 |
| AT-630-7-E-2 | NF | `resolver` 回 `[8.8.8.8, 10.0.0.1]`（混合）⇒ 該 host 拒絕（`private-ip`）；回 `[]` ⇒ `network`；回 `["::ffff:127.0.0.1"]` ⇒ `private-ip`；`resolver` 對單一請求恰被呼叫 1 次；重導每跳各 1 次 | 只驗第一個位址 ⇒ 混合例紅；解析兩次 ⇒ 次數紅 |
| AT-630-7-3 | NF | 替身 `connector(ip, port, server_hostname)` 記錄參數；`resolver` 回 `[93.184.216.34]` ⇒ 連線 `ip`＝`93.184.216.34`、`port`＝443、`server_hostname`＝原主機名；送出的請求 `Host` 標頭＝原主機名（非 IP） | 以主機名重新連線（二次解析）或 `server_hostname` 填 IP ⇒ 紅 |
| AT-630-7-E-3 | NF | 重導目標：不在 `hosts`、私網 host、`http://`、埠 8443、第 6 跳 ⇒ `redirect-refused`，**不對目標連線**（`connector` 次數＝已完成跳數）；合法同網域 https 重導 ⇒ 成功 | 逐跳重驗少一關 ⇒ 對應例紅 |
| AT-630-7-E-4 | NF | AST：`netguard.py` 只 import `ipaddress`、`re`（不含 `socket`）；全套件 `import socket／ssl／http／urllib` 者只有 `fetch.py` | `netguard` 加 `import socket` ⇒ 紅 |

### AC-SI-30-8 文章展開（NF）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-8-1 | NF | `expand.select` 對 sitemap 夾具（lastmod 亂序、缺 lastmod 者、跨 host、非 prefix、重複、索引自身、`max=3`）⇒ 回固定 URL 清單（lastmod 新→舊、缺者最後、同值保文件序、前 3） | 排序鍵或 prefix／同 host 過濾被改 ⇒ 紅 |
| AT-630-8-2 | NF | `links` 模式：HTML 的相對連結（含 `../`、`#fragment`、`mailto:`）與 Atom `<link rel="alternate" href>`／RSS `<link>text</link>` ⇒ 基底解析、去 fragment、去重、同 host、prefix | 少去 fragment 或少基底解析 ⇒ 紅 |
| AT-630-8-E-1 | NF | sitemap 含 `<!DOCTYPE ... <!ENTITY ...>`（億笑夾具，載入量上限 1 MB 即中止）⇒ 展開失敗（`status=expand-refused`）、索引本身仍成功、事件仍寫、**解析器未被呼叫**：實作必須把唯一的 XML 解析呼叫收在 `expand._parse_xml(raw)`（單一函式、內部用標準庫 `xml.etree.ElementTree`），測試以 `mock.patch.object(expand, "_parse_xml")` spy——含 `<!DOCTYPE`／`<!ENTITY` 時**呼叫次數 0**；**對照例**：合法 sitemap ⇒ 呼叫次數 ≥1（證明 spy 有效）；另一例以 `<!DOCTYPE` 出現在 `<url>` 的 `<loc>` 文字內（合法 CDATA 內的字樣）⇒ 仍拒絕（判準為位元組搜尋，寧可誤拒） | 先解析後檢查 ⇒ 呼叫次數 ≠0 紅；spy 對象換名 ⇒ 對照例紅 |
| AT-630-8-3 | NF | 整合：索引成功＋3 篇文章（其中 1 篇 host 解到私網）⇒ `research/<id>/articles/<sha12>.txt` 落 2 篇、`research/_scans/<RUN>.json` 的 `items[]` 含 3 筆（1 筆 `private-ip`）；事件 `articles_n=3`（＝明細 `items[]` 筆數，含失敗者）、`articles_sha256`＝明細檔位元組 `sha256`；事件 JSON 字串不含任何文章 URL 子字串 | 事件存 URL，或 `articles_sha256` 不等於檔 ⇒ 紅 |
| AT-630-8-4 | NF | 最壞行長：10 來源（`id` 32 字元、`bytes=524288`）＋`articles_n=30`＋5 位數 `seq`／`registry_seq` ⇒ `len(json.dumps(ev, ensure_ascii=False, separators=(",",":")).encode())`＝**2119**（≤4096）；再把明細擴為 30 篇、每篇 URL 2048 字元，事件長度不變；參數（皆於 §9.2 列明）：`run=RUN-SI-999`、`t`／`fetched_at` 各 25 字元、`registry_seq` 與 `seq` 各 5 位數 | 事件欄位增減而未同步 §9.2 ⇒ 數字紅 |
| AT-630-8-5 | NF | **展開每次掃描都做（D-EQA-8）**：連跑兩次掃描，第 2 次索引 `sha256` 與第 1 次相同（`changed=false`）⇒ 第 2 次仍展開並抓 3 篇文章；文章 `changed` 對上一次明細同 URL 的 `sha256` 判定（同＝`false`、異＝`true`、URL 不在上次明細＝`true`）；上次明細檔缺失或雜湊與事件 `articles_sha256` 不符 ⇒ 全部 `changed=true`；第 1 次某篇失敗（`http-status`）⇒ 第 2 次自然重試並記為 `changed=true` | 以索引 `changed` 為展開條件 ⇒ 第 2 次無文章而紅 |
| AT-630-8-E-2 | NF | `research.scan` 驗證：`articles_n=100`、`articles_n` 無 `articles_sha256`、`articles_*` 搭 `sources_sha256` ⇒ `EVENT-TYPE`／`EVENT-KEY-*`（`sound()` 濾掉） | `evspec6` 條件規則被刪 ⇒ 紅 |
| AT-630-8-E-3（非 UTF-8 XML；SCG-4 QA4R-01，勘誤 E-6；測試函式 `test_AT_630_8_E_3_non_utf8_xml_is_refused_before_parse`） | NF | 非 UTF-8 系 XML（UTF-16／UTF-32 BOM、前段 NUL、宣告 `encoding` 非 `utf-8`／`us-ascii`）一律在解析前 `ExpandRefused` | 未在解析前拒收非 UTF-8 系 XML ⇒ 紅 |

### AC-SI-30-9 HTML→純文字（NF）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-9-1 | NF | golden：固定 HTML（`head` 含 `title`、`script`、`style`、`noscript`、`svg`、`template`；`p`／`div`／`li`／`h1`／`pre`／`br`；`&nbsp;`、`&amp;`、多空白、未閉合標籤、巢狀 `noscript` 內有 `script`）⇒ `to_plain` 輸出位元組＝golden 檔（隨測試檔提交，LF，結尾一個 LF） | 任一丟棄標籤或區塊換行規則被改 ⇒ golden 紅 |
| AT-630-9-2 | NF | 確定性：同一位元組輸入在**兩個不同 `PYTHONHASHSEED` 的子行程**（測試用 `sys.executable -c`，非 SI 套件內）與本行程共三次輸出 `sha256` 相同；輸出長度 ≤ 輸入長度 | 輸出依 `set` 迭代序或時鐘 ⇒ 紅 |
| AT-630-9-E-1 | NF | 非 UTF-8 `charset`、`Content-Encoding`（見 AT-630-3-E-1）；空輸入 ⇒ 空輸出 `b""`（無任何文字時不補 LF）；只含 `script` 的輸入 ⇒ 空輸出；非空輸出恰以一個 LF 結尾 | 空輸入拋例外 ⇒ 紅 |

### AC-SI-30-10 無人運轉複製擴及旁檔與文章（NF）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-630-10-1 | NF | 夾具 home：1 個 `changed=true` HTML 來源（`.txt`＋`.plain.txt`）、1 個 `changed=true` 文章（`.plain.txt`）、1 個 `changed=false` 文章；`stage_sources` ⇒ 任務目錄 `research/` 下恰有前三者（位元組相等）、不含 `changed=false`；`compose` 的 `<SOURCE_FILES>` 只列任務目錄副本路徑 | 仍只複製 `<sha12>.txt` ⇒ 紅 |
| AT-630-10-E-1 | NF | `_scans/<RUN>.json` 位元組被改一字（雜湊 ≠ 事件 `articles_sha256`）⇒ 不 spawn（`patrolrun.launch` 回 `("failed", "sources-scans-mismatch")`；現況 `launch` 的失敗形態見 `patrolrun.py:194-231`）；複製目的唯讀（注入 `OSError`）⇒ 清半套副本、不 spawn（回 `("failed", "sources-copy-failed: OSError")`，既有形態 `patrolrun.py:209-211`） | 不驗明細雜湊 ⇒ 紅 |

### AC-SI-45-1 稽核檔驗證與碼序（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-1-1 | RG | `px.audit(kind="src-registry", registry_text=golden)`，金鑰環含簽章金鑰 ⇒ `registry-ingest --carrier console --audit-ref <uuid>` rc 0 | `consoleaudit.KINDS` 未增 `src-registry` ⇒ `AUDIT-KIND-MISMATCH` 紅 |
| AT-645-1-E-1 | RG | 碼序表驅動（每列獨立 repo；單一缺陷時回該碼、兩缺陷時回**較早者**）：缺檔→`AUDIT-FILE-MISSING`；外層缺鍵→`AUDIT-SCHEMA`；body 非 JSON→`AUDIT-BODY-INVALID`；ref 不符→`AUDIT-REF-MISMATCH`；`kind=obs-add` 的稽核檔→`AUDIT-KIND-MISMATCH`；`role=VIEWER`→`ROLE-NOT-ADMIN`；`time` 帶 `Z`→`AUDIT-TIME-FORMAT`；金鑰環空→`AUDIT-KEY-MISSING`；MAC 被改→`AUDIT-MAC-MISMATCH`；ref 已被 `research.registry` 事件使用→`AUDIT-REF-REUSED`；body 多一鍵／缺 `registry_text`／`registry_sha256` 格式錯→`AUDIT-BODY-INVALID`；`time` 早於最新事件 `audit_time`→`REG-STALE`（碼序在 `REG-*` 之後，單例見 AT-645-1-9）；`registry_text` 24,577 bytes→`REGISTRY-TOO-LARGE`、稽核外層檔 65,537 bytes→`AUDIT-FILE-TOO-LARGE`（碼序：檔存在之後、解析之前最先判，故雙缺陷時先回它）；`registry_sha256` 與文字不符→`REGISTRY-SHA-MISMATCH`；文字合 sha 但不合格→`REG-*`。⇒ 每例 rc 1、輸出含 `obs-draft:`、鏡像檔與事件帳本位元組皆不變 | 驗證順序被換（例如先 `REG-*` 後 `REGISTRY-SHA-MISMATCH`）⇒ 雙缺陷例紅 |
| AT-645-1-2 | RG | `registry.validate` 變體表（每例回恰一個預期碼）：BOM／CR／無結尾 LF／非 JSON（`REG-FILE-FORMAT`）；頂層多鍵、缺 `watch`、`schema_rev=true`、`hosts` 元素鍵缺（`REG-SCHEMA`）；縮排 4 或鍵序不同的同語意文字（`REG-NORMAL`）；`host` 大寫／尾點、`list_kind="X"`、`source="Y"`、`layer="Z"`、`min_interval_seconds` 為 0 或 `true`（`REG-HOST-FORMAT`）；同 (`list_kind`,`host`) 重複（`REG-HOST-DUP`）；host 未依序（`REG-HOST-ORDER`）；`id` 大寫或 33 字元（`REG-WATCH-ID`）；id 重複（`REG-WATCH-DUP`）；未依序（`REG-WATCH-ORDER`）；`kind="rss"`（`REG-WATCH-KIND`；`sitemap`、`search` 合格）；`url` 為 http／`:8443`／尾點 host／userinfo／`127.0.0.1`／IDNA／2049 字元（`REG-WATCH-URL`）；`extract` 空／201 字元／含 `\x07`、`enabled="yes"`（`REG-WATCH-FIELD`）；`added_at` 為 `...Z` 或 `+08:00`（`REG-WATCH-TIME`）；`expand` 的 `max=4`／`mode="x"`／`prefix="research"`／多一鍵（`REG-WATCH-EXPAND`）；**正控**：空 `hosts` 與空 `watch` 合格；（URL 判準以附錄 D 逐列為準，見 AT-645-1-6）；`arxiv-agents` 的 D-RR-16 URL（含 `%28`、`&`、`?`）與 `kind=search`、`layer=ACADEMIC`、`expand=null` 合格；啟用來源的 host 不在 `hosts` 仍合格（刻意不判） | 任一判準或其碼被刪 ⇒ 對應例紅；把「host 不在 hosts」加成 `REG-*` ⇒ 正控紅 |
| AT-645-1-3 | RG | **golden 對拍**：附錄 B 的 golden 文字（位元組）⇒ `validate` 回空；其 `sha256` 常數＝`147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8`（2039 bytes）；以 Python 依 §9.2 規則由 golden 物件重新序列化，位元組逐位相等；**golden 內各列與 Console 種子逐字一致（D-EQA-18）**：`anthropic-engineering`＝舊表匯入（`added_by` 為 `migration:V24（SI research_sources.json 匯入）`、`disabled_by` 為 `migration:V24（以 anthropic-research 取代）`、`extract` 取舊表逐字）、`anthropic-research` 與 `arxiv-agents`＝主控代決新增（`added_by` 為 `migration:V24（研究來源單一化種子）`）、`added_at`／`disabled_at` 固定 `2026-11-10T00:00:00+00:00`、網域種子 `min_interval_seconds=5`、`export.arxiv.org` 為部署基底（`ENV`、3 秒）——測試對這些常數逐字斷言（Console 端依同一份常數引用附錄 B） | 序列化參數（`indent`、`sort_keys`、`ensure_ascii`）與 §9.2 不同 ⇒ 紅 |
| AT-645-1-6 | RG | **URL parity（D-EQA-1）**：附錄 D 表文字（LF；`URL<TAB>SI<TAB>CON`）的 `sha256` 常數＝`25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89`；先斷言表自身雜湊等於常數；表中每列以 `registry.validate` 驗：把該 URL 放進合法鏡像的單一 `watch[].url`，`SI` 欄為 `T` ⟺ 結果不含 `REG-WATCH-URL`；並斷言 **CON 為 `T` 者 SI 欄必為 `T`**（Console ⊆ SI）。涵蓋 IDNA／`xn--` 任一 label、非 ASCII、IPv4／IPv6 字面（公網與私網）、`localhost`、`*.localhost`、userinfo、非 443 埠、顯式 `:443`、尾點、http、大寫 host、含 `#`、空路徑、含空白、17 列種子 URL 全部 | 任一 URL 判準被刪或放寬 ⇒ 該列紅；表被改而常數沒改 ⇒ 紅 |
| AT-645-1-7 | RG | **17 列種子 URL 全數合格**：附錄 D 末 17 列（舊表 15 個＋`anthropic-research`＋`arxiv-agents` 的 D-RR-16 URL）逐一過 `registry.validate`（各放入合法鏡像）⇒ 皆回空；整份 17 筆種子鏡像（啟用 10、停用 7）亦回空 | 把 `?`、`&`、`%28` 或 `:` 判成非法 ⇒ arxiv 例紅 |
| AT-645-1-8 | RG | **G-S1 本體（D-EQA-2；QA2-01 修正）**：讀 `tools/tests/fixtures/selfimproving/G-S1.audit.json`（路徑寫死，不存在＝紅、不 skip）⇒ 位元組逐位等於依附錄 C 規則與固定輸入重新產生者（判定以重新產生比對為準；附錄 C 的 G-S1 sha256 回填是文件紀錄、不是測試常數，所以實作 commit 單獨看也可綠——QA 複核 P3）。**本 AT 不讀 `AgentConsole/**`**：提交順序是根層先、Console 後，Console 副本的一致性由 Console 鍵 AT-965-6-7 以同一附錄 C 規則重新產生並比對（兩側同綁附錄 C，等值由構造保證） | 檔被改一字、遺漏、或產生規則漂移 ⇒ 紅 |
| AT-645-1-9 | RG | **單調性（D-EQA-17）**：先入帳稽核檔 A（`time` T1）；再送 `time` 早於 T1 的稽核檔 B（MAC 正確、內容合格）⇒ rc 1、`REG-STALE`、B 檔保留、鏡像位元組與事件帳本不變、巡邏兩次心跳只記一次拒收；`time` 等於 T1（不同 `audit_ref`）⇒ 放行；不同時區但絕對時刻較晚 ⇒ 放行；帳本無前筆事件 ⇒ 不判；碼序：在 `REG-*` 之後 | 以字串比較時刻（時區不同時錯判）或鏡像倒退 ⇒ 紅 |
| AT-645-1-4 | RG | **常數與邊界釘住（D-RR-13）**：`registry.REGISTRY_TEXT_MAX == 24576`、`registry.AUDIT_FILE_MAX == 65536`；`registry_text` 恰 24,576 bytes 的合格樣本（以合法空白不可得時改用長 `extract` 湊足）⇒ 通過 `REGISTRY-TOO-LARGE` 關卡；24,577 ⇒ 拒收；稽核外層檔恰 65,536 ⇒ 通過、65,537 ⇒ `AUDIT-FILE-TOO-LARGE`；超界皆不截斷、零寫入；Console 端以同值常數各自釘住 | 任一常數改值或改成「截斷」⇒ 紅 |
| AT-645-1-5 | RG | **黃金檔 G-S1（D-RR-17）**：`tools/tests/fixtures/selfimproving/G-S1.audit.json`（**由根層實作輪先產出並提交**；Console 端複製同一份交叉核對）依附錄 C 的位元組表由 `px.audit` 產生；測試斷言①檔位元組＝附錄 C 規則重新產生者（逐位元相等）②`consoleaudit.verify` 以測試金鑰通過、`registry-ingest` rc 0 且鏡像位元組＝附錄 B golden③外層鍵序、`body` 鍵序、緊湊分隔、非 ASCII 不跳脫、結尾恰一個 LF 皆符合附錄 C；實作輪產出後把 G-S1 的 `sha256` 回填附錄 C（勘誤單獨 commit） | 序列化參數（鍵序、分隔、`ensure_ascii`）與附錄 C 不同 ⇒ 紅 |

### AC-SI-45-2 原子入帳與冪等（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-2-1 | RG | 入帳 golden ⇒ 鏡像位元組＝`registry_text`；恰多一筆 `research.registry`：`audit_ref`、`audit_sha256`（稽核檔 `sha256`）、`key_id`、`decider`（＝body `user`）、`carrier=console`、`audit_time`（＝body `time`）、`registry_sha256`、`hosts_n=2`、`watch_n=3`、`watch_on=2`、`changed=true`；`seq` 連續；`by` 為 `--by` 值 | 鏡像被重新序列化（位元組不等）⇒ 紅 |
| AT-645-2-2 | RG | 內容相同的第二個稽核檔（新 `audit_ref`）⇒ rc 0、事件 `changed=false`、**`os.replace` spy 呼叫 0 次**（鏡像不改檔）；`console_pending` 不再列兩個稽核檔 | 內容未變仍換檔、或不寫事件 ⇒ 紅 |
| AT-645-2-E-1 | RG | 事件追加失敗（`event_max_bytes` 注入 100／`LOCK-BUSY`）⇒ rc 1；有舊鏡像時還原為入帳前位元組、無舊鏡像時鏡像不存在；事件帳本位元組不變 | 缺 `state.cleanups` 還原 ⇒ 鏡像殘留紅 |
| AT-645-2-E-2 | RG | `os.replace` 注入 `PermissionError` ⇒ rc 1、`LEDGER-WRITE-FAILED`、無 `.tmp` 殘留、無事件 | 未包 `OSError` ⇒ 例外外洩紅 |
| AT-645-2-E-3 | RG | 注入 `regwrite.PAUSE_HOOK`（位置＝全部驗證完成、寫鏡像之前；不得沿用 `evwrite.PAUSE_HOOK`）：在鉤子內由另一程序以同 `audit_ref` 入帳 ⇒ 本次 `AUDIT-REF-REUSED`、零寫入 | 鎖內不重驗 ⇒ 雙事件紅 |
| AT-645-2-E-4 | RG | 崩潰窗口：手動做「鏡像已換、事件未寫」 ⇒ `research --fetch` 回 `REGISTRY-UNBOUND`；對同一稽核檔再 `registry-ingest` ⇒ rc 0（自癒）、其後 `research --fetch` 通過預檢 | 自癒路徑被 `REGISTRY-UNCHANGED` 之類新碼擋下 ⇒ 紅 |

### AC-SI-45-3 綁定與 check（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-3-1 | RG | 入帳後 `check --json` ⇒ rc 0、`items` 長度 35、`research.sources`／`events.research`／`events.prop_files` 皆 PASS | 新增了第 36 個項目 ⇒ 紅 |
| AT-645-3-E-1 | RG | 手改鏡像一個字元；有鏡像無事件；有事件無鏡像 ⇒ `events.research` 含 `REGISTRY-UNBOUND`（fail、rc 1）；兩者皆無 ⇒ nonblocking `CARRIER-NOT-ESTABLISHED`（rc 不變） | 綁定判準被刪 ⇒ 紅 |
| AT-645-3-E-2 | RG | 新格式 `research.scan`：`registry_seq` 指向不存在的 `seq`／指向 sha 不同的事件／大於自身 `seq` ⇒ `SCAN-REGISTRY-MISMATCH`；`sources[].id` 不在鏡像與舊表 ⇒ `SRC-UNKNOWN` | 少驗 `registry_seq` ⇒ 紅 |
| AT-645-3-2 | RG | 突變對拍：還原 `check.py:114-115` 或 `fourqparse.py:294-295` 任一處為「只讀舊表」（以 `mock.patch` 替換 `registry.known_ids` 為只回舊表集合）⇒ AT-630-4-1 紅（證明兩處都走 `known_ids`） | 任一處未改呼叫 ⇒ 該處 `src=<停用 id>` 紅 |

### AC-SI-45-4 巡邏入帳與授權閘（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-4-1 | RG | `patrol._ingest_argv(ctx,"src-registry",ref)` 回 `["registry-ingest","--carrier","console","--audit-ref",ref,"--by","patrol"]`；假依賴整輪心跳（沿 P4 夾具）把 `console_audit/` 內該檔入帳 ⇒ 事件與鏡像齊備、`console_pending` 為空 | `_ingest_argv` 無該 kind ⇒ `AUDIT-KIND-UNKNOWN` 紅 |
| AT-645-4-E-1 | RG | `AUTOSDD_UNATTENDED=1` 直接 `registry-ingest`／`backtest cases --check` ⇒ rc 1、`UNATTENDED-REFUSED`；`unattended.C_CLASS` 含兩動詞；不設該變數 ⇒ 可入 | `C_CLASS` 漏登 ⇒ 紅 |
| AT-645-4-E-2 | RG | 稽核檔 MAC 被改，連跑兩次心跳 ⇒ 該 `audit_ref`＋同碼的 OBS 草稿只記一次（`patrol.py:206-210` 既有規則）、稽核檔保留 | 重複草稿 ⇒ 紅 |

### AC-SI-45-5 dirty-tree（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-5-1 | RG | 真 git 夾具：改動鏡像檔、`docs/06_quality/SelfImproving_Backtest/results.jsonl` ⇒ `sched.dirty_paths` 不列；改動 `tools/x.py` ⇒ 仍列 | `_OWN_PREFIXES` 漏一項 ⇒ 紅 |

### AC-SI-45-6 舊表凍結（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-6-1 | RG | 真樹：`research_sources.json`（LF 正規化後）`sha256` 恆為 `6201d066799e7f13c18053f3474f6883fddd8091baf0ab24e3a4b1c0d348e26f`、位元組數 5226 | 改該檔任一位元組 ⇒ 紅（這是「凍結」的機械物） |
| AT-645-6-2 | RG | 合成樹把舊表刪除或改壞 ⇒ `research --fetch`、`registry-ingest` 行為與結果同前（活動路徑不讀舊表）；`check` 的 `research.sources` 對壞檔仍報 `SRC-*`（既有判準未動） | 活動路徑 import `sources.load_table` ⇒ 紅 |
| AT-645-6-3 | RG | 合成 git repo：舊格式 `research.scan`＋舊表提交歷史 ⇒ `check` 綠；把舊表 `git rm` 後 ⇒ `check` 對該事件只剩 `SOURCE-UNAVAILABLE`（info）而**不再執行** `SOURCES-SHA-MISMATCH` 回查——此例為**特性化測試**，證明刪檔的後果（為何選凍結）；注意它描述的是「若刪除」的行為，不是產品要求 | 特性化行為變動（有人改了 `_scan_findings` 早退）⇒ 紅，需連同 PRD AC-SI-45-6 的理由重審 |
| AT-645-6-4 | RG | 舊事件 `sources_sha256` 被改 ⇒ 仍 `SOURCES-SHA-MISMATCH`（舊判準未被削弱）；新格式事件不帶 `sources_sha256` 時不觸發該碼 | 新格式事件被誤判 ⇒ 紅 |

### AC-SI-45-7 事件欄位與大小（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-7-1 | RG | `len(KINDS)==27`；`set(issuemap.EVENT_LABELS)==set(KINDS)`；三種合法事件（`research.registry`、`backtest.result`、新格式 `research.scan`）`validate` 回空；`evspec` 既有對外名稱仍可自 `events` 取得 | `KINDS` 未增或標籤缺 ⇒ 紅 |
| AT-645-7-E-1 | RG | 變體：`research.registry` 缺鍵／`watch_on>watch_n`／`carrier="x"`／`audit_ref` 非 UUID／表外鍵；`research.scan` 同時帶 `sources_sha256`＋`registry_*`、兩者皆無、`articles_n` 缺 `articles_sha256`、`articles_*` 搭舊格式；`backtest.result` 的 `hit1>hit3`、`k=11`、`batch="B1"`、`seed=-1`、`prec_pm=1001` ⇒ 各 `EVENT-*`；`sound()` 濾掉 | 條件規則被刪 ⇒ 紅 |
| AT-645-7-2 | RG | 依 §9.2 參數建最壞事件 ⇒ 長度恰 2119／561／472 且皆 ≤ `event_max_bytes`；位數參數（D-EQA-13，與 PRD §9.2 逐項同）：`research.registry`＝`seq` 5、`by` 32 字元、`decider` 64 字元、`audit_time` 與 `t` 各 25 字元、三個計數各 3 位數；`backtest.result`＝`seq` 5、`by` 32、批號 `BT-`＋6 位數、`cases_version` 3、`seed` 10、`k`／`n`／`unanswered`／`contaminated`／`hit1`／`hit3`／`hit5` 各 2、`prec_pm`／`rec_pm` 各 4、`ledger_line` 6、兩個 `sha256` 各 71 字元；`evwrite` 對超長行回 `EVENT-BYTES-OVER`（以 `event_max_bytes` 注入 100 驗） | §9.2 數字與實算不一致 ⇒ 紅 |

### AC-SI-45-8 status 供 Console 顯示（RG）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-645-8-1 | RG | 無 `research.registry` 事件 ⇒ `status --json`：`research_fetch_max==10`、`research_registry is None`；入帳後 ⇒ `research_registry=={seq,audit_ref,registry_sha256,watch_enabled}` 且值等於最新事件的 `seq`、`audit_ref`、`registry_sha256`、`watch_on`；再入帳一次（不同內容）⇒ 取較新者；鍵序＝17 鍵之後依序 `research_fetch_max`、`research_registry`；文字模式各多一行；`export --kind status --json` 同樣帶出兩鍵（不為 NOT-EVALUABLE） | 取最舊事件、或鍵序顛倒、或 `export` 漏帶 ⇒ 紅 |
| AT-645-8-E-1 | RG | `params.json` 的 `research_fetch_max` 無效（合成樹改成 `0` 或字串）⇒ `research_fetch_max is None`、不拋例外；`research.registry` 事件缺 `audit_ref`／`registry_sha256`（D-RR-14）⇒ 該事件被 `sound()` 濾掉（`EVENT-KEY-MISSING`），`research_registry` 不採用它 | `evspec6` 未把兩欄列為必備 ⇒ 紅 |

### AC-SI-46-1 案例庫（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-1-1 | BT | `px.git_repo()`（暫存目錄真 git：多個 commit、OBS 與缺陷帳本夾具各含 `fixed@<sha>` 列）；`backtest cases --build` ⇒ `cases[]` 與 `excluded[]` 等於 golden：`pre_commit`＝fix 的 first parent、`changed_files` 只含程式檔且存在於 `pre_commit`、症狀取自指定欄 | 症狀取成處置欄；`pre_commit` 取最後一個 parent ⇒ 紅 |
| AT-646-1-E-1 | BT | 每種排除各一例：`commit-missing`（偽造 sha）、`merge`、`no-code-file`（只改 docs／tests／新增檔）、`files-over`（9 檔）、`symptom-empty`、`symptom-has-sha`（含修復 sha 前 7 碼）、`symptom-names-file`（症狀含被改檔完整路徑）⇒ 皆在 `excluded[]` 且帶對應原因、不在 `cases[]` | 少一種排除 ⇒ 該例紅 |
| AT-646-1-2 | BT | 同輸入連跑兩次 `--build`（第二次指定新版本）⇒ 兩檔 `cases[]` 位元組相同、`version` 遞增、`generated_at` 不同；已存在同版號檔 ⇒ `BT-CASES-VERSION-EXISTS` 且該檔位元組不變；零案例 ⇒ `BT-CASES-EMPTY` | 覆寫既有檔 ⇒ 紅 |
| AT-646-1-3 | BT | 案例檔位元組＝正規化序列化（`indent=2`、`sort_keys`、`ensure_ascii=False`、LF、結尾一個 LF）；`cases --check` rc 0；改一字節 ⇒ `BT-CASES-FORMAT`；`pre_commit` 指向不存在 commit ⇒ `BT-CASES-FORMAT` | 序列化參數不同 ⇒ 紅 |

### AC-SI-46-2 prepare（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-2-1 | BT | 案例檔 12 案；`prepare --seed 7`（`--root` 指向 repo 外暫存）⇒ 抽到 5 案；順序＝`sha256(f"7:{id}")` 十六進位升冪前 5（測試自算 golden）；同 seed 再跑（新批）抽同批案；seed 8 不同；每個 `snap/s<i>` 的 `git rev-parse HEAD`＝該案 `pre_commit`、為 detached；`snap` 路徑不在 repo 之下；任務書含 `nonce`、`snap` 絕對路徑、症狀，**不含** `changed_files` 任何路徑、案例 `id`、`fix_commit`；`batch.json` 含 `changed_files` | 抽樣改用 `random` ⇒ golden 紅；任務書夾帶 `id` ⇒ 紅 |
| AT-646-2-E-1 | BT | `--k 0`／`--k 11`（`BT-K-RANGE`）；`--root` 在 repo 內（`BT-ROOT-INSIDE-REPO`）；SOP 範本缺 `<NONCE>`（`BT-TEMPLATE-INVALID`）；某案 `pre_commit` 已不存在（`BT-WORKTREE-FAILED`）；**池子小於 `K`（D-EQA-6）**：案例檔只有 3 個合格案例、`--k 5` ⇒ `BT-POOL-TOO-SMALL`，輸出含 `pool=3 k=5`，不建批次目錄、不建 worktree、零事件 ⇒ 整批回退：無批次目錄、`git worktree list` 無新項、零事件 | 回退不完整（殘留 worktree）⇒ 紅；池子不足時改成「用盡」⇒ 池子例紅 |
| AT-646-2-2 | BT | `Git.run` spy：`worktree add` 的 argv 含 `--detach`、`-c core.longpaths=true`，逾時參數＝600；全程無 `--force`（AST 掃 `btwrite.py` 無 `"--force"` 字串） | 少 `--detach` ⇒ 紅 |

### AC-SI-46-3 answer（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-3-1 | BT | 合法答案 ⇒ `answers/s1.json` 位元組＝輸入；`binding.json` 記 `agent_id` 與 `answered_at`（帶 offset） | 答案被重新序列化 ⇒ 紅 |
| AT-646-3-E-1 | BT | 變體：多／缺鍵、`case` 不符、`suspects` 空／6 個／非字串／絕對路徑／含 `..`／磁碟代號／控制字元、`hypothesis` 空或 401 字元、`--agent-id` 為 `xyz`（`BT-ANSWER-FORMAT`）；未知案（`BT-ANSWER-CASE-UNKNOWN`）；重複（`BT-ANSWER-EXISTS`）⇒ rc 1、`answers/` 零變化 | 路徑判準放寬 ⇒ 對應例紅 |

### AC-SI-46-4 評分（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-4-1 | BT | `btscore.score_case` 表驅動 golden：命中第 1、第 3、第 5、無命中；重複 suspect 去重；`Src\A.py` 與 `src/a.py` 正規化後相等；`changed_files` 有 2 檔命中 1 檔的 recall＝1/2；`hit@k` 值 | 公式或名次定義被改 ⇒ golden 紅 |
| AT-646-4-E-1 | BT | `aggregate` 邊界：`n=0`（全 `unanswered`）⇒ 分數 0 且標 `n=0`；平均 1/3 ⇒ `prec_pm=333`、2/3 ⇒ `667`、恰 x.5 進位的例（1/8 與 3/8 平均＝1/4）；**AST：`btscore.py` 不含 `float(`、`round(` 呼叫與浮點字面量**（一律以 `Fraction` 運算） | 改用浮點平均 ⇒ 邊界例紅 |
| AT-646-4-2 | BT | 3 ok＋1 contaminated＋1 unanswered ⇒ `n=3`、彙總只算 ok；`contaminated`／`unanswered` 計數正確 | 髒案入分母 ⇒ 紅 |

### AC-SI-46-5 洩漏稽核（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-5-1 | BT | 合成 `claude_home`（`px.claude_home()`）：`<slug>/<sid>/subagents/agent-<id>.jsonl`（每行含 `agentId`、`sessionId`、`cwd`、`type`、`timestamp`、`message`）；乾淨逐字稿（user 行含 `nonce`；assistant 的 `Read`／`Grep`／`Glob` 皆在 `snap/s1` 內且 `Grep` 帶 `path`；末行為含 text 的 assistant）⇒ `ok` | 稽核誤判乾淨逐字稿 ⇒ 紅 |
| AT-646-5-E-1 | BT | 髒樣本各一（每例斷言原因碼）：逐字稿缺／同 id 兩檔／不可解析／零 assistant 行（`transcript-missing`）；user 行無 `nonce`（`binding-mismatch`）；用了 `Bash`／`Write`／`PowerShell`／`WebFetch`（`tool-not-allowed:<name>`）；`Read` 路徑在 `snap/s1x`（同前綴不同目錄）、含 `..` 逃逸、快照外、大小寫不同的根、指向快照外的連結（`outside-snapshot`）——**零 skip、平台中立**：`btscore.inside(snap, target, *, pathmod, realpath)` 的 `pathmod` 與 `realpath` 為注入參數，同一個測試在**同一平台**對 `ntpath`（反斜線與磁碟代號、`normcase` 小寫化）與 `posixpath`（正斜線、大小寫敏感）**各跑一組**路徑表，連結逃逸以注入的假 `realpath`（把指定路徑映射到快照外）表達，不建真連結；`Grep` 無 `path` 且 `cwd` 為 repo 根（`path-missing`）；`Glob` 的 `pattern` 為 `..\..\*`（`pattern-escape`）；零個快照內讀取（`no-reads`）；末行為 `tool_use` 無 text（`transcript-open`） | 少一種判準 ⇒ 該例紅 |
| AT-646-5-E-2 | BT | fail-closed：`transcript_dir` 不存在、佈局改名（`subagents`→`workers`）⇒ 全部 `contaminated(transcript-missing)`、彙總 `n=0`、rc 0 不拋例外 | 找不到逐字稿時放行 ⇒ 紅 |
| AT-646-5-E-3 | BT | harness 回報工具（勘誤 E-8、E-9）：真實形狀乾淨逐字稿（交卷 tool_use＋同 id tool_result、**無**結尾 text）⇒ `None`；同時含讀快照外路徑的 `Read` ⇒ `outside-snapshot`；含 `Bash` ⇒ `tool-not-allowed:Bash` | 白名單放寬到其他工具或路徑判準被放寬 ⇒ 紅 |
| AT-646-5-E-4 | BT | 交卷收尾（勘誤 E-9）：交卷 tool_use＋同 id 非錯誤 tool_result ⇒ `None`（帶與不帶 `toolEndsTurn` 皆是；中間或其後夾 `api-request` 型別紀錄不影響）；交卷無回應、回應 `is_error`、`tool_use_id` 不符、末筆是其他工具的 tool_result ⇒ `transcript-open` | 收尾判準退回只認 text、或不核對 id／`is_error` ⇒ 紅 |
| AT-646-5-E-5 | BT | 只交卷、零讀取 ⇒ `no-reads`（交卷不計入讀取） | 交卷被計入 reads ⇒ 紅 |
| AT-646-5-E-6 | BT | Read 目標＝`file_path`、非字串取 `path`：`path` 在快照內 ⇒ `None`；`path` 在快照外、兩鍵皆無、`file_path` 在快照外而 `path` 在快照內、`file_path` 非字串而 `path` 在快照外 ⇒ `outside-snapshot` | 不認 `path` 或 `path` 蓋過 `file_path` ⇒ 紅 |

### AC-SI-46-6 結果帳本與事件（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-6-1 | BT | `score` ⇒ `results.jsonl` 恰多一行（緊湊 JSON，鍵序如 §9.2）；事件 `backtest.result`：`ledger_line=1`、`row_sha256`＝該行位元組（不含 LF）`sha256`、各整數欄與列相等；第二批 `ledger_line=2` | 事件與列的數值不一致 ⇒ 紅 |
| AT-646-6-E-1 | BT | 同批再 `score` ⇒ `BT-BATCH-SCORED`；事件追加失敗（`event_max_bytes` 注入 100）⇒ `results.jsonl` 位元組與追加前相同（截回） | 缺截回 ⇒ 孤列紅 |
| AT-646-6-2 | BT | `check`：綠；改列一字（`BT-RESULT-SHA-MISMATCH`）、刪列（`BT-RESULT-MISSING`）、手加一列（`BT-ROW-UNBOUND`）、改案例檔一字（`BT-CASES-SHA-MISMATCH`）⇒ 各紅（rc 1）；`items` 仍 35；原綠 | `events.prop_files` 未納入判準 ⇒ 紅 |

### AC-SI-46-7 cleanup（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-7-1 | BT | `cleanup` ⇒ `git worktree list --porcelain` 不含批次路徑、`snap/` 空、`git worktree prune` 已執行（spy）；argv 無 `--force` | 以 `shutil.rmtree` 代替 ⇒ `.git/worktrees` 死登記紅 |
| AT-646-7-E-1 | BT | 在某案 `snap/s2` 寫入未追蹤檔（變髒）⇒ `BT-WORKTREE-DIRTY`、該目錄保留、其他案照清、rc 1、仍執行 `prune` | 髒時強制移除 ⇒ 該目錄消失紅 |

### AC-SI-46-8 status 與護欄（BT）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-646-8-1 | BT | 無事件 ⇒ `status --json` 末鍵 `backtest` 為 `null`、鍵數 20；有 7 次同版本事件＋1 次不同版本 ⇒ 最近一次欄位正確、走勢只含同版本最近至多 5 次的 `hit5`、不同版本分列；文字模式多一行 | 走勢跨版本並列 ⇒ 紅 |
| AT-646-8-E-1 | BT | `prop-new` 的 `proof` 含 `回測`、`backtest`、`BackTest` ⇒ 拒收 `PROOF-BACKTEST`；`check` 重放同判；不含 ⇒ 不判；既有 `PROOF-LEAK` 行為不變；`evspec.GOODHART` 表位元組不變（Q4 答案檔仍可含 `backtest`） | 把 `backtest` 加進 `GOODHART` ⇒ Q4 例紅 |
| AT-646-8-2 | BT | 刪除或改寫 `results.jsonl` ⇒ `tools/probe/selfimproving_measure.py` 的 M1～M5 輸出與 `fingerprint` 不變（回測不入指標） | 指標讀回測 ⇒ 紅 |
| AT-646-8-3 | BT | `AUTOSDD_UNATTENDED=1` 下 `backtest` 每個子命令 ⇒ `UNATTENDED-REFUSED`；全程以 `socket.socket.connect` 注入 `AssertionError` 驗**零網路** | 子命令漏登 C 類 ⇒ 紅 |

### 自增 AC：能力登記、`params.json` 不動、不退化、範圍守衛（SY）
| AT | 檔 | 夾具；Given／When／Then | 預期突變 |
|---|---|---|---|
| AT-690-1-1 | SY | `capability_problems(PKG, CAPABILITY, ENTRY)==[]`；`CAPABILITY` 72 鍵＝(52,13,2,5)；新 10 檔類別：`registry`／`netguard`／`htmltext`／`expand`／`evspec6`／`btcases`／`btscore` 為 `ro`、`regwrite`／`btwrite`／`btrecord` 為 `rw`；`net` 仍只有 `fetch`、`research`；全套件含 `subprocess` 字樣者仍只有 `git.py`、`runner.py` | 新檔含 `subprocess` 字樣（含註解）⇒ 紅 |
| AT-690-1-E-1 | SY | 注入變體（沿 `test_selfimproving_capability.py:458-492` 形態）：`ro` 檔加 `write_text(`；`htmltext` 加 `import socket`；`btscore` 相對 import `btwrite`；`btwrite` 加 `import subprocess`；登記表漏登新檔 ⇒ 各回對應問題 | 登記判準退化 ⇒ 紅 |
| AT-690-2-1 | SY | `params.json` 位元組 `sha256`＝`594494910f77f029060aa1b0f79767f1f74927331a81a14a14dc24ca86398e9c`；`len(PARAM_SPECS)==44`；`CHECK_RULES_REV==6`；`non_evolvable_globs` 與 PRD〈實體 glob〉行對表（`glob_findings` 回空） | 有人改了 `params.json` ⇒ 紅（P6 禁止） |
| AT-690-3-1 | SY | 不退化：既有 SI 測試檔全綠（§2 清單，已改期望值）；`check` 項目數 35；`status` 鍵數 20；`research --skip` 行為位元組不變；舊格式 `research.scan` 夾具全數照舊綠 | 任一既有行為被改 ⇒ 既有 AT 紅 |
| AT-690-3-2 | SY | SOP 機械判準對 P6 版 SOP 回空：`patrolbrief.template_problems`、`_selfimproving_fixtures.sop_problems`、`_selfimproving_p5_fixtures.sop_p5_problems`（常數已依 §2 同步）；負控：把〈研究者〉節還原成 v0.14 文字 ⇒ `sop_p5_problems` 回 `SOP-P5-RESEARCHER-CHANGED`；把〈反事實回測〉節移到〈無人運轉任務書範本〉之後 ⇒ `patrolbrief.template_of` 取到錯誤圍欄而 `template_problems` 非空（證明新節必須置於範本節之前） | 判準常數未同步、或新節放錯位置 ⇒ 紅 |
| AT-690-4-1 | SY | 範圍守衛（允許集合見 §4 表）：差分觸及允許集合時，差分 ⊆ 允許集合且 PRD、SOP、`TCS-SelfImproving-P*`、`Root_Layout` 差異為空（基準讀 `SI_SCOPE_BASE`〔相容舊名 `SI_P4_BASE_SHA`〕、終點讀可選 `SI_SCOPE_TIP`〔缺省 `HEAD`〕，只比對已提交差異；未設基準＝guard-not-triggered；驗法＝本鍵各 commit 逐一以 `SI_SCOPE_BASE=<c>^`、`SI_SCOPE_TIP=<c>` 驗，交錯的他鍵 commit 不驗；勘誤 E-6、E-7；承 `test_AT_440_8_1`／AT-445-5-1 形態）；**不得改**：`fold.py`、`writeverbs.py`、`params.json`、`.claude/**`、`AgentConsole/**`、`.github/**`、`research_sources.json` | 實作 commit 夾帶 PRD ⇒ 紅 |

---

## 2. 既有測試與站點的同步編修（先行，使紅燈來自「碼未到位」）

| 站點 | 現值 | 新值 |
|---|---|---|
| `test_selfimproving_capability.py:338-346`（`AT_143_1_1`）、`:436-440`（`AT_240_5_1`）、`:672-680`（`AT_340_4_2`）；`CAPABILITY` 常數表 | 62、`(45,10,2,5)` | 72、`(52,13,2,5)`；表增 10 檔；檔頭註解 62 鍵 → 72 鍵 |
| `test_selfimproving_fourq_gate.py:416、630` | `len(EVENT_LABELS)==25`、`(62, 25)` | 27、`(72, 27)` |
| `test_selfimproving_issuemap.py:156-157` | `len(EVENT_LABELS)==25` | 27 |
| `test_selfimproving_fourq_model.py:511`、`test_selfimproving_events_p2.py:143`、`test_selfimproving_schedule_gate.py:178、1043` | `len(KINDS)==25` | 27 |
| `status` 鍵數的既有斷言（`test_selfimproving_export_status.py`、`test_selfimproving_fourq_gate.py` 的 17 鍵處；實作者以 Grep `17` 與 `status` 現查，本稿不逐一列行號） | 17 | 20（`research_fetch_max`、`research_registry`、`backtest`） |
| `_selfimproving_p5_fixtures.py:107`（`RESEARCHER_SHA`；判準 `:166-168` 釘〈研究者〉節位元組） | v0.14 節的 `e961796c0a61ab4281db40c6d52a0f7274ff880048bb6883c65deefd526b1593` | P6 版 SOP〈研究者〉節（`section(text, "研究者")` 取 LF 正規化文字的 `sha256`；寫稿時現算值 `ac696ba9cd30adbe7ac689b466172ab655c6914a4fc3851160a956217a8ea212`，**以凍結版 SOP 為準重算**）；P5 TCS 的對應 AT 期望同步 |
| `_selfimproving_fixtures.py` 的 `FRAGMENTS`（〈研究者〉節必含片段；`sop_problems` 於 `:1605`） | 含 `research_sources.json`、`僅 T1` | 改為 `research_registry.json`、`唯一設定處是 Console`（其餘片段不動）；使用處 `test_selfimproving_events.py:1787-1826`、`test_selfimproving_research_scan.py:1922,1970` 隨之核對 |
| `test_selfimproving_ledgerdb_p0.py:507-538` | 讀真樹 `research_sources.json` | **不改**（凍結檔仍在、位元組不變，AT-645-6-1 守住） |
| `tools/tests/_selfimproving_fixtures.py`、`_selfimproving_p4_fixtures.py` | 研究夾具以舊表為預設 | 保留（舊格式事件的回歸夾具）；新增 `px` 夾具檔，不改既有函式簽名 |
| `docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md` | 協定目錄三檔基準列 | **不改**（`params.json`、`metrics.md`、舊表位元組皆不變；`CHECK_RULES_REV` 不變）；`FINGERPRINT_EXCLUDED` 擴充使「排除於指紋」的列多一個檔——該基準檔只登記三檔，**不新增列**（鏡像是新檔，非 P0 基準對象） |

**根層重釘儀式（主控收尾；記憶 `guard-ratchet-repin-ritual`）**：新增 3 個測試檔與 1 個夾具檔 ⇒ 12 道鎖；`tools/lib/selfimproving/` 新增 10 檔 ⇒ `tools/tests/test_root_module_layout.py` 的登記格於實作 commit 後加回反引號路徑；`FINGERPRINT_EXCLUDED`、`C_CLASS`、`_OWN_PREFIXES`、`KINDS`、`EVENT_LABELS`、`CAPABILITY` 的同步為**同一個 commit**。

## 3. 夾具（`px`，`tools/tests/_selfimproving_p6_fixtures.py`）

- `px.repo(**kw)`：沿 `fx.p1_base()` 建合成 repo，另放協定目錄、可選鏡像與 `research.registry` 事件、已開運轉；家目錄 `AUTOSDD_SI_DIR` 指向暫存。
- `px.registry_text(hosts, watch)`：依 §9.2 規則序列化（`json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)+"\n"`）；`px.audit(si, kind, registry_text, key, user="admin", ref=None)`：沿既有 `obs-add` 稽核檔夾具的簽章函式（HMAC-SHA256 over `body` 字串；金鑰環 `AUTOSDD_SI_AUDIT_KEY`）。
- `px.net(resolver=…, responses=…)`：注入 `fetch` 的兩個縫——`resolver(host)->list[str]` 與 `connector(ip, port, server_hostname, deadline)->conn`；記錄每次呼叫的參數；回應表以 `(host, path)` 為鍵，可含重導、Content-Type、Content-Encoding、body。**測試不得真連網**（`socket.socket.connect` 注入 `AssertionError`）。
- `px.git_repo()`：暫存目錄真 git（`git init`、本機 user.name／email、`core.autocrlf=false`）；`px.commit(files, msg)` 回 40 碼；支援合併 commit；OBS 帳本與缺陷帳本夾具（表頭與欄位同真帳本）。
- `px.claude_home(sid, agents)`：在暫存 `claude_home()` 下造 `projects/<slug>/<sid>/subagents/agent-<id>.jsonl`（形態見 PRD §9.2 的實查結構）；`px.line(kind, ...)` 產生 user／assistant／tool_use 行。**只造結構，不抄真實逐字稿內容。**
- **暫停鉤子（D-EQA-10）**：`research.PAUSE_HOOK`（`research --fetch`：抓取完成、取鎖前）、`regwrite.PAUSE_HOOK`（`registry-ingest`：驗證完成、寫鏡像前）、`btrecord.PAUSE_HOOK`（`score`：洩漏稽核完成、取鎖前）；皆預設 `None`、測試以 `mock.patch.object` 設定；與 `evwrite.PAUSE_HOOK`（`evwrite.py:26`，讀末行配號後、追加前）是不同位置、互不取代。
- 時鐘縫：`research.py` 與 `btscore`／`btrecord` 的 `now()` 與單調時鐘皆可注入（鐵律三：測試傳帶 offset 的時間）。

## 4. 實作 commit 的允許集合（AT-690-4-1；實作 commit 的差分必須 ⊆ 本表）

| 類別 | 路徑 |
|---|---|
| 新程式（10） | `tools/lib/selfimproving/{registry,netguard,htmltext,expand,evspec6,btcases,btscore,regwrite,btwrite,btrecord}.py` |
| 改程式（各限 PRD §9.1〈C4 套件檔案表（P6）〉所列呼叫點） | `tools/lib/selfimproving/{fetch,research,evspec,events,evcheck,check,fourqparse,params,consoleaudit,patrol,patrolrun,status,unattended,sched,issuemap}.py`、`tools/selfimproving.py` |
| 新測試與夾具 | `tools/tests/test_selfimproving_registry.py`、`tools/tests/test_selfimproving_netfetch.py`、`tools/tests/test_selfimproving_backtest.py`、`tools/tests/_selfimproving_p6_fixtures.py`、`tools/tests/fixtures/selfimproving/G-S1.audit.json`、`tools/tests/fixtures/selfimproving/html_golden.html`、`tools/tests/fixtures/selfimproving/html_golden.txt` |
| 既有測試同步（§2 表所列，且僅限列明的站點） | `tools/tests/test_selfimproving_{capability,fourq_gate,issuemap,fourq_model,events_p2,schedule_gate,export_status,events,research_scan}.py`、`tools/tests/_selfimproving_fixtures.py`、`tools/tests/_selfimproving_p5_fixtures.py`、`tools/tests/test_root_module_layout.py`（落點鎖，實作 commit 後加反引號路徑）、`tools/tests/test_adr_xplat001_c1c2_lock.py` 與其他重釘儀式檔（主控收尾另一 commit，不在實作 commit） |
| 既有測試同步（勘誤 E-6 補列；QA4R-02） | `tools/tests/test_selfimproving_{sandbox,p2_meta,measure_verb,schedule_model,check,ledgerdb_p0}.py`（範圍守衛 `ALLOWED` 補入） |
| 重釘三檔（勘誤 E-6；重釘儀式另一 commit，範圍守衛 `ALLOWED` 補入） | `tools/tests/test_adr_xplat001_c1c2_lock.py`、`docs/04_planning/AutoSDD_improving_112.md`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md` |
| §2 表外的既有測試同步站點（勘誤 E-3；預期值同步、非弱化） | events.research PASS→NE（AC-SI-45-3／AT-645-3-E-1）於 events、events_p2、fourq_gate、research_scan；status 17→20 鍵（AC-SI-45-8／46-8）於 export_status、events `WEIRD_STATUS_KEYS`、schedule_model、schedule_gate、measure_verb、console_obs、p3_meta、fourq_gate；事件種類與標籤 25→27（AC-SI-45-7）；動詞數 27→28（registry-ingest；BT 再 29）；CAPABILITY 62→72（52／13／2／5） |
| 運行期資料（真機 V-P6-1／V-P6-2 產生，隨實作輪收尾提交） | `docs/06_quality/SelfImproving_Protocol/research_registry.json`、`docs/06_quality/SelfImproving_Backtest/**`、`docs/06_quality/SelfImproving_Event_Ledger.jsonl` |
| 凍結鎖 | `research_sources.json` **不在允許集合**（位元組不變，AT-645-6-1） |
| **不得改** | PRD、SOP、`TCS-SelfImproving-P*`、`Root_Layout_and_Module_Placement.md`、`fold.py`、`writeverbs.py`、`params.json`、`.claude/**`、`AgentConsole/**`（含 G-S1 的 Console 副本，由 Console 鍵提交）、`.github/**` |

## 4A. 勘誤路由與待回填

- 本檔與 PRD v0.15 不一致處以 PRD 為準；本檔日後勘誤單獨 commit（`FROZEN` 以 `TCS-SelfImproving-P` 為前綴、僅豁免 `-P4-`；P6 實作輪結束後主控依 D-EQA-9 慣例處理）。
- **P6-PENDING 回填**：PRD v0.15／SOP／本檔在 P6 鍵凍結後，主控把摘要回填追溯表。
- 共享附錄（A～D）一字不得改；改動走 PRD 修訂＋本檔勘誤，再由 Console 端 TCS 更新其引用的 `sha256`。
- R2P 既有 TCS 對「初始清單恰為四組主機」的勘誤與該鍵 refreeze 屬 Console 鍵（D-RR-08），本檔不處理。

---

## 5. 計數與對照

**AT 共 100（正控 58、負控 42）**；各檔：RG 41、NF 25、BT 28、SY 6（勘誤 E-9：新增 AT-646-5-E-4～E-6；原文「AT 共 97（正控 58、負控 39）；各檔：RG 41、NF 25、BT 25、SY 6」）（勘誤 E-8：新增 AT-646-5-E-3；原文「AT 共 96（正控 58、負控 38）；各檔：RG 41、NF 25、BT 24、SY 6」）（勘誤 E-6：新增 AT-630-8-E-3〔非 UTF-8 XML〕；原文「AT 共 95（正控 58、負控 37）；各檔：RG 41、NF 24、BT 24、SY 6」）。

**每條 FR／AC → AT 對照表**（機械產生：由 §1 每列的 AT 編號推得；每條 AC 至少一個 AT）

| AC | AT |
|---|---|
| AC-SI-30-2 | AT-630-2-1、AT-630-2-E-1、AT-630-2-E-2、AT-630-2-E-3、AT-630-2-E-4 |
| AC-SI-30-3 | AT-630-3-1、AT-630-3-E-1、AT-630-3-E-2、AT-630-3-E-4、AT-630-3-E-3 |
| AC-SI-30-4 | AT-630-4-1 |
| AC-SI-30-5 | AT-630-5-1 |
| AC-SI-30-6 | AT-630-6-1 |
| AC-SI-30-7 | AT-630-7-1、AT-630-7-2、AT-630-7-E-1、AT-630-7-E-2、AT-630-7-3、AT-630-7-E-3、AT-630-7-E-4 |
| AC-SI-30-8 | AT-630-8-1、AT-630-8-2、AT-630-8-E-1、AT-630-8-3、AT-630-8-4、AT-630-8-5、AT-630-8-E-2、AT-630-8-E-3（勘誤 E-6） |
| AC-SI-30-9 | AT-630-9-1、AT-630-9-2、AT-630-9-E-1 |
| AC-SI-30-10 | AT-630-10-1、AT-630-10-E-1 |
| AC-SI-45-1 | AT-645-1-1、AT-645-1-E-1、AT-645-1-2、AT-645-1-3、AT-645-1-6、AT-645-1-7、AT-645-1-8、AT-645-1-9、AT-645-1-4、AT-645-1-5 |
| AC-SI-45-2 | AT-645-2-1、AT-645-2-2、AT-645-2-E-1、AT-645-2-E-2、AT-645-2-E-3、AT-645-2-E-4 |
| AC-SI-45-3 | AT-645-3-1、AT-645-3-E-1、AT-645-3-E-2、AT-645-3-2 |
| AC-SI-45-4 | AT-645-4-1、AT-645-4-E-1、AT-645-4-E-2 |
| AC-SI-45-5 | AT-645-5-1 |
| AC-SI-45-6 | AT-645-6-1、AT-645-6-2、AT-645-6-3、AT-645-6-4 |
| AC-SI-45-7 | AT-645-7-1、AT-645-7-E-1、AT-645-7-2 |
| AC-SI-45-8 | AT-645-8-1、AT-645-8-E-1 |
| AC-SI-46-1 | AT-646-1-1、AT-646-1-E-1、AT-646-1-2、AT-646-1-3 |
| AC-SI-46-2 | AT-646-2-1、AT-646-2-E-1、AT-646-2-2 |
| AC-SI-46-3 | AT-646-3-1、AT-646-3-E-1 |
| AC-SI-46-4 | AT-646-4-1、AT-646-4-E-1、AT-646-4-2 |
| AC-SI-46-5 | AT-646-5-1、AT-646-5-E-1、AT-646-5-E-2、AT-646-5-E-3、AT-646-5-E-4、AT-646-5-E-5、AT-646-5-E-6 |
| AC-SI-46-6 | AT-646-6-1、AT-646-6-E-1、AT-646-6-2 |
| AC-SI-46-7 | AT-646-7-1、AT-646-7-E-1 |
| AC-SI-46-8 | AT-646-8-1、AT-646-8-E-1、AT-646-8-2、AT-646-8-3 |
| AC-P6-090-1 | AT-690-1-1、AT-690-1-E-1 |
| AC-P6-090-2 | AT-690-2-1 |
| AC-P6-090-3 | AT-690-3-1、AT-690-3-2 |
| AC-P6-090-4 | AT-690-4-1 |

| FR | 涵蓋的 AC |
|---|---|
| FR-SI-30（P6 改寫；AC-30-1 為 P1 繼承、本檔不重驗） | AC-SI-30-2～30-10（9 條，AT 皆在 §1） |
| FR-SI-45 | AC-SI-45-1～45-8（8 條） |
| FR-SI-46 | AC-SI-46-1～46-8（8 條） |
| 自增 | AC-P6-090-1～090-4（4 條） |

AC 共 29 條（PRD 新增或改寫 25 條＋自增 4 條），皆有 AT；AT 共 100（原文 95、96、97；勘誤 E-6、E-8、E-9）。

---

## 附錄 A　公網位址 parity 表（根層與 Console 端 Bridge 兩份測試逐字共用）

格式：每行 `位址<TAB>T｜F`（T＝`is_public_ip` 應為真）；文字以 LF 結尾；`sha256`＝`3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd`。位址表由 Bridge 現行 `allowlist.py::is_public_ip`（`AgentConsole/engine-bridge/app/research/fetch/allowlist.py:88-100`）的邏輯在寫稿時求值產生；任何一端改判準，兩端表與常數須同步（PRD 修訂）。

```text
8.8.8.8	T
1.1.1.1	T
2606:4700:4700::1111	T
2001:4860:4860::8888	T
::ffff:8.8.8.8	T
1.2.3.4%eth0	T
127.0.0.1	F
127.255.255.254	F
10.0.0.1	F
172.16.0.1	F
172.31.255.255	F
192.168.1.1	F
169.254.169.254	F
100.64.0.1	F
0.0.0.0	F
255.255.255.255	F
224.0.0.1	F
240.0.0.1	F
198.51.100.1	F
192.0.2.1	F
::1	F
::	F
fe80::1	F
fe80::1%eth0	F
fc00::1	F
fd00::1	F
ff02::1	F
fec0::1	F
::ffff:127.0.0.1	F
::ffff:10.0.0.1	F
not-an-ip	F
	F
999.1.1.1	F
1.2.3	F
```

## 附錄 B　golden 鏡像（`registry_text` 位元組；根層與 Console 端共用）

`sha256`＝`147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8`（`registry_sha256` 即 `sha256:` 加此值），2039 bytes。內容依 §9.2 正規化規則產生（`json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"`）。

```json
{
  "hosts": [
    {
      "host": "export.arxiv.org",
      "layer": null,
      "list_kind": "FETCH",
      "min_interval_seconds": 3,
      "source": "ENV"
    },
    {
      "host": "www.anthropic.com",
      "layer": "INDUSTRY",
      "list_kind": "FETCH",
      "min_interval_seconds": 5,
      "source": "ADMIN"
    }
  ],
  "schema_rev": 1,
  "watch": [
    {
      "added_at": "2026-11-10T00:00:00+00:00",
      "added_by": "migration:V24（SI research_sources.json 匯入）",
      "disabled_at": "2026-11-10T00:00:00+00:00",
      "disabled_by": "migration:V24（以 anthropic-research 取代）",
      "enabled": false,
      "expand": null,
      "extract": "最新 5 篇文章的標題與日期（逐字）",
      "id": "anthropic-engineering",
      "kind": "blog",
      "layer": "INDUSTRY",
      "url": "https://www.anthropic.com/engineering"
    },
    {
      "added_at": "2026-11-10T00:00:00+00:00",
      "added_by": "migration:V24（研究來源單一化種子）",
      "disabled_at": null,
      "disabled_by": null,
      "enabled": true,
      "expand": {
        "max": 3,
        "mode": "sitemap",
        "prefix": "/research/"
      },
      "extract": "最新 3 篇研究文章的全文（逐字）",
      "id": "anthropic-research",
      "kind": "sitemap",
      "layer": "INDUSTRY",
      "url": "https://www.anthropic.com/sitemap.xml"
    },
    {
      "added_at": "2026-11-10T00:00:00+00:00",
      "added_by": "migration:V24（研究來源單一化種子）",
      "disabled_at": null,
      "disabled_by": null,
      "enabled": true,
      "expand": null,
      "extract": "最新 10 篇論文的標題、作者、日期與摘要首句（逐字）",
      "id": "arxiv-agents",
      "kind": "search",
      "layer": "ACADEMIC",
      "url": "https://export.arxiv.org/api/query?search_query=%28abs:%22self-improving%22+OR+abs:%22self-evolving%22+OR+abs:%22agent+memory%22%29+AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy=submittedDate&sortOrder=descending&max_results=10"
    }
  ]
}
```

## 附錄 C　稽核檔位元組表與黃金檔 G-S1（D-RR-17；本文即位元組表，下列圍欄內文字的 `sha256`＝`91f137380530a5959138597add7b145ab7760611a7cca0ac1d7861062d321d87`；**G-S1 本體由根層實作輪先產出**）

```text
G-S1 稽核檔產生規則（本文即位元組表；LF；UTF-8 無 BOM）
key = si-test-key-g-s1-0123456789abcdef
key_id = sha256(key 的 UTF-8 位元組) 十六進位前 8 碼
audit_ref = 00000000-0000-4000-8000-0000000000a1
user = admin
role = ADMIN
time = 2026-11-10T09:00:00+08:00
kind = src-registry
registry_text = 附錄 B golden 的位元組（UTF-8 解碼成字串）
registry_sha256 = "sha256:" + 附錄 B golden 的 sha256 十六進位
body = json.dumps({"schema_rev":1,"audit_ref":audit_ref,"kind":"src-registry","user":user,"role":"ADMIN","time":time,"registry_text":registry_text,"registry_sha256":registry_sha256}, ensure_ascii=False, separators=(",",":"))
body 鍵序即上式順序，不 sort_keys；緊湊（無空白）；非 ASCII 原樣；"/" 不跳脫；控制字元與引號依 JSON 標準跳脫（\n、\"、\\、其餘 \u00xx 小寫十六進位）
mac = HMAC-SHA256(key 的位元組, body 字串的 UTF-8 位元組) 小寫十六進位 64 碼
外層檔 = json.dumps({"schema_rev":1,"kind":"src-registry","audit_ref":audit_ref,"subject":null,"body":body,"key_id":key_id,"mac":mac}, ensure_ascii=False, separators=(",",":")) + 恰一個 LF
外層鍵序即上式順序；subject 恆 null；SI 驗證不依賴排列（解析後對 body 字串驗 HMAC），本表只為 Console 與根層位元組逐位相等
大小：registry_text <= 24576 bytes；外層檔 <= 65536 bytes
黃金檔：tools/tests/fixtures/selfimproving/G-S1.audit.json（根層實作輪先產出並提交；產出後回填其 sha256，勘誤單獨 commit）
Console 副本：AgentConsole/backend/src/test/resources/si/G-S1.audit.json（由主控原樣複製；與根層檔逐位元組相同）
```

## 附錄 D　追蹤來源 URL parity 表（D-EQA-1；根層與 Console 端共用）

格式：每行 `URL<TAB>SI<TAB>CON`（`T`＝接受、`F`＝拒絕）；LF 結尾；`sha256`＝`25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89`。**原則：Console 的接受集合 ⊆ SI 的接受集合**——任何一列若 `CON=T` 則 `SI` 必為 `T`；Console 可比 SI 嚴（例如拒任何 IP 字面，即使是公網位址），不可比 SI 寬。SI 欄的判準＝PRD §9.2 的 `REG-WATCH-URL`（https、無 userinfo、host 非空且僅 ASCII 無 `xn--` label、非 localhost／`*.localhost`／私網字面、無尾點、埠缺省或 `443`、無 `#`、無空白與控制字元、長度 ≤2048）；CON 欄＝Bridge 驗證須達的判準（在 SI 之上再拒任何 IP 字面與 `localhost`，並依 Console DB `url` CHECK 拒大寫 host 與任何顯式埠〔含 `:443`〕；輸入原樣判定、不做正規化，主控 2026-11-10 定案）。末 17 列為種子 URL（舊表 15 個＋`anthropic-research`＋`arxiv-agents`），兩端皆須為 `T`。

```text
https://xn--e1afmkfd.xn--p1ai/	F	F
https://sub.xn--x.example.org/	F	F
https://XN--abc.example/	F	F
https://例え.jp/	F	F
https://１２７.0.0.1/x	F	F
https://example。org/x	F	F
https://93.184.216.34/x	T	F
https://127.0.0.1/x	F	F
https://10.0.0.1/x	F	F
https://[2606:4700:4700::1111]/x	T	F
https://[::1]/x	F	F
https://[::ffff:127.0.0.1]/x	F	F
https://localhost/x	F	F
https://app.localhost/x	F	F
https://u:p@example.org/x	F	F
https://example.org:8443/x	F	F
https://example.org:80/x	F	F
https://example.org:443/x	T	F
https://example.org./x	F	F
http://example.org/x	F	F
https://EXAMPLE.ORG/x	T	F
https://example.org/x#frag	F	F
https://example.org	T	T
https://example.org/a b	F	F
https://example.org/x?q=1&r=%28a%29	T	T
https://www.anthropic.com/engineering	T	T
https://github.com/anthropics/anthropic-sdk-python/releases.atom	T	T
https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md	T	T
https://code.claude.com/docs/en/hooks-guide	T	T
https://code.claude.com/docs/en/hooks-guide.md	T	T
https://code.claude.com/docs/llms.txt	T	T
https://code.claude.com/docs/en/memory	T	T
https://code.claude.com/docs/en/memory.md	T	T
https://code.claude.com/docs/en/skills	T	T
https://code.claude.com/docs/en/skills.md	T	T
https://github.com/anthropics/claude-code/releases.atom	T	T
https://github.com/openai/openai-agents-python/releases.atom	T	T
https://github.com/openai/openai-agents-python/tags.atom	T	T
https://platform.openai.com/docs/changelog	T	T
https://developers.openai.com/api/docs/changelog.md	T	T
https://www.anthropic.com/sitemap.xml	T	T
https://export.arxiv.org/api/query?search_query=%28abs:%22self-improving%22+OR+abs:%22self-evolving%22+OR+abs:%22agent+memory%22%29+AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy=submittedDate&sortOrder=descending&max_results=10	T	T
```

## 附錄 E　共享附錄的位元組 sha256 一覽（Console 端引用用）

| 附錄 | 路徑（本檔內） | 位元組 | `sha256` |
|---|---|---|---|
| A 公網位址表（圍欄內文字） | 附錄 A | 441 | `3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd` |
| B golden 鏡像（`registry_text`） | 附錄 B | 2039 | `147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8` |
| C 稽核檔位元組表（圍欄內文字） | 附錄 C | 1681 | `91f137380530a5959138597add7b145ab7760611a7cca0ac1d7861062d321d87` |
| D URL parity 表（圍欄內文字） | 附錄 D | 1797 | `25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89` |

---

## 勘誤（凍結後的訂正；內文已就地訂正、被訂正的原文逐字保留於下表；走 spec-refreeze）

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| E-1 | 11-10 | 文章失敗與 OBS 草稿（登記型） | 原文：無 | 登記：文章失敗（索引成功）時 `research --fetch` rc=2，且不產 OBS 草稿（實作選擇） | 主控同意 |
| E-2 | 11-10 | 夾具 `p1_base()`（登記型） | 原文：無 | 登記：`p1_base()` 的 `research_fetch_max` 為 8（夾具），故 `px.repo` 設為 10 | 實作輪回報 |
| E-3 | 11-10 | §2 表外的既有測試同步（登記型；已補入 §4 列） | 原文：§2 表無下列站點 | 登記（預期值同步、非弱化）：events.research PASS→NE（AC-SI-45-3／AT-645-3-E-1）於 events、events_p2、fourq_gate、research_scan；status 17→20 鍵（AC-SI-45-8／46-8）於 export_status、events `WEIRD_STATUS_KEYS`、schedule_model、schedule_gate、measure_verb、console_obs、p3_meta、fourq_gate；事件種類與標籤 25→27（AC-SI-45-7）；動詞數 27→28（registry-ingest；BT 再 29）；CAPABILITY 62→72（52／13／2／5） | 根層第一棒交卷 |
| E-4 | 11-10 | `test_selfimproving_research_scan.py` 的 AT-130 系列（登記型） | 原文：無 | 登記：20 條移除、檔頂加「舊 AT→P6 AT」對照表（同表在 `_selfimproving_p6_fixtures.py::SUPERSEDED_P1`，p2_meta／p3_meta 元測試據以豁免並要求取代者存在）；AT-130-3-E-5、5-E-5 改走 `fetch_chain`＋`px.net`；AT-130-5-E-4 保留 `_DeadlineRaw` 前半；AT-230-2-E-2 以 P6 版恢復；新增 AT-630-3-E-5（`--json` 形狀、全失敗 rc 1）、AT-630-3-E-6（抓取不持鎖） | 實作輪回報 |
| E-5 | 11-10 | 舊死碼（登記型） | 原文：無 | 登記：舊 `fetch_source` 等死碼已移除（無產品呼叫點） | 實作輪回報 |
| E-6 | 11-10 | SCG-4 一審（QA4R-01～04）：§1 AT-630-8-E-3 新列、§4 允許集合、§5 計數與對照、AT-690-4-1 驗法 | 原文：§1 無非 UTF-8 XML 拒收列；§4 ALLOWED 無 sandbox、p2_meta、measure_verb、schedule_model、check、ledgerdb_p0 與重釘三檔；§5「AT 共 95（正控 58、負控 37）；各檔：RG 41、NF 24、BT 24、SY 6」「AT 共 95」；AT-690-4-1「（基準＝`SI_P4_BASE_SHA`，缺省 `HEAD~1`；承 `test_AT_440_8_1`／AT-445-5-1 形態）」 | 內文就地訂正：①QA4R-01 `expand` 對非 UTF-8 系 XML（UTF-16／32 BOM、前段 NUL、宣告 encoding 非 utf-8／us-ascii）一律在解析前 `ExpandRefused`，§1 新增 AT-630-8-E-3（`test_AT_630_8_E_3_non_utf8_xml_is_refused_before_parse`；原擬 E-2 與既有 research.scan 驗證列撞號，主控改 E-3）；②QA4R-02 §4 允許集合補入上列六個測試檔與重釘三檔（c1c2 lock、AutoSDD_improving_112、CrossPlatform_R145_Scan_Findings）；③§5 AT 總數 95→96（負控 37→38、NF 24→25）；④AT-690-4-1 驗法＝逐 commit `SI_SCOPE_BASE=<c>^`、`SI_SCOPE_TIP=<c>` 驗本鍵各 commit，交錯的他鍵 commit 不驗；⑤QA4R-03 重釘 commit 11067dd1 為分桶分類補一行 fixtures docstring（儀式所需）；⑥QA4R-04 `fetch.py` 空白行 | SCG-4 一審 FAIL P2×2；22 組突變全殺（M13 白名單判準只由 registry 檔一條 AT 殺，記為鑑別力集中） |
| E-7 | 11-10 | AT-690-4-1 與 §提交程序③（範圍守衛結構修正） | 「基準＝`SI_P4_BASE_SHA`，缺省 `HEAD~1`」「本機跑範圍守衛（AT-690-4-1）時才設 `SI_P4_BASE_SHA=<規格 commit>`」 | 內文就地訂正：有 `SI_SCOPE_BASE`（相容舊名 `SI_P4_BASE_SHA`）才啟用，可選 `SI_SCOPE_TIP`；只比對已提交差異；未設基準＝guard-not-triggered。P4（AT-440-8-1、AT-440-5-E-1）、P5（AT-444-6-1、AT-445-5-1）TCS 同步勘誤，三鍵 refreeze | 兩把鍵 commit 交錯時舊判準對後續工作常駐誤紅（實作 commit 0bea20e4，主控裁決） |
| E-8 | 11-10 | OBS-SI-383／382 修正：AT-646-5-E-3 新列、`btscore.py` 白名單、SOP〈回測子代理任務書範本〉交卷格式、§5 計數 | 原文：§1 無 AT-646-5-E-3；`ALLOWED_TOOLS` 僅 Read／Grep／Glob，`SubagentHandback` 判 `tool-not-allowed`；SOP 範本交卷格式「一句話根因假說」「一句話修法方向」；§5「AT 共 96（正控 58、負控 38）；各檔：RG 41、NF 25、BT 24、SY 6」「AT 共 96」 | 內文就地訂正：①`btscore.py` 新增具名常數 `HARNESS_HANDBACK_TOOL="SubagentHandback"`（harness 2.1.322 子代理交卷工具，不帶路徑、不讀檔），`_tool_verdict` 只對它回 None，路徑判準與其他工具名判準不變；②§1 新增 AT-646-5-E-3（`test_AT_646_5_E_3_harness_handback_tool_is_not_a_leak`）；③SOP 範本交卷格式兩欄補「，≤400 字元」（占位符不動；`test_AT_646_2_1` 補斷言任務書含新字樣；SOP 變更併登於此）；④§5 AT 總數 96→97（負控 38→39、BT 24→25） | 真機首跑 BT-002 三案正常作答全判污染（OBS-SI-383，P2）；範本缺判準實際強制的 ≤400 上限（OBS-SI-382，P3；PRD AC-SI-46-3 已有此上限） |
| E-9 | 11-10 | OBS-SI-384：AC-SI-46-5 洩漏稽核（PRD v0.15.1 同步訂正）、AT-646-5-E-3 固件、AT-646-5-E-4～E-6 新列、§5 計數 | 原文：AT-646-5-E-3 的「乾淨逐字稿」含結尾 text；`transcript-open`＝末行不是含 text 的 assistant 行；交卷工具計入讀取；Read 目標只取 `file_path`；§5「AT 共 97（正控 58、負控 39）；各檔：RG 41、NF 25、BT 25、SY 6」「AT 共 97」 | 內文就地訂正：①`btscore._closed`：只看 `assistant`／`user` 型別紀錄；已收尾＝末筆含 text 的 assistant 行，或末筆 user 行含同 id（緊接其前 assistant 行的 `SubagentHandback` tool_use）且非 `is_error` 的 tool_result；不以 `toolEndsTurn` 為必要條件；②交卷不計入 reads（QA P2-1：只交卷可繞過 no-reads）；③Read 目標＝`file_path`，非字串取 `path`，皆無 ⇒ `outside-snapshot`；④AT-646-5-E-3 固件改真實形狀，新增 E-4（收尾）、E-5（只交卷）、E-6（path 鍵）；⑤§5 AT 總數 97→100（負控 39→42、BT 25→28） | 真機 BT-002 逐字稿：交卷經 `SubagentHandback`、結尾無 text（BT-003 將再 n=0）；Read 偶帶 `path` 鍵（DEF-200-550 案 s4）；四案以修後 `audit_case` 重判全為 `None`（唯讀探針）；QA 聚焦複核 P2-1 |
