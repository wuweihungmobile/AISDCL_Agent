# PRD 修憲增補 — §4.2.2-b (4c) gate 聚合面切換為設計內例外（DEF-200-244）

| 欄位 | 值 |
| :---- | :---- |
| 狀態 | **落地版本 v2.1.14**：掌舵者 2026-09-02 採 R121 呈報單 `DEF-200-244` 方向 B；R126 四方設計複審（Architect／SA／SD／QA，`docs/06_quality/CrossPlatform_R126_Debt_Closure.md` §D）**4×APPROVE**；程式面隨同批落地並過定點複審。依 R110 判例不疊層：本增補只新增一則條文與一條可觀測性義務，不改動 v2.1.10 任何既有條文 |
| 提案輪 | R126（落地輪） |
| 標的 PRD | `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` |
| 上游條文 | `docs/04_planning/PRD_Amendment_R108_Pacing.md` §6.1「改後（新增小節 4.2.2-b）」的 (4)／(4b)（Adopted，v2.1.10） |
| 覆蓋缺陷 | `DEF-200-244`（gate 聚合面第三通道＝(4b) 通道 C，未被 (4) 涵蓋、動它會碰 R89／R98 兩次憲法裁決） |
| 為何另開一檔而非就地改 Pacing 檔 | 本 repo 慣例＝每個 PRD 版號對應一份獨立施工圖檔（v2.1.10~v2.1.13 皆如此），且就地改一份 **Adopted** 文件會讓讀者誤以為整份已生效決議被重新開放；Pacing 檔 (4b) 段落只補一行指向本檔的指針 |

---

## 1. 條文（新增 §4.2.2-b (4c)）

```
(4c) gate 聚合面切換屬**設計內例外**（(4b) 通道 C 的裁決）：
     C_cap／C_target 的聚合成員集合（本實作面＝quota_policy.decide() 的 gate_list）排除
       · 美元計價／超額類軸（現查 quota_policy.FALLBACK_KINDS）——R89 憲法裁決
         「保險池不得一票否決主力」；
       · 未命中本次模型的分軌軸（現查 quota_policy.MODEL_SCOPED_KINDS ∧ 非 active_model）
         ——R98 裁決「不得用一個沒在用的模型的水位節流主力」。
     兩類排除屬**取數層裁決**，不受 (4) 多軸單調律約束：加一條軸使 gate_list 由空翻非空、
     致原本在聚合面上的煞車軸整批離開而 C_target 變大，是這兩次裁決**要的**方向（實測定向
     兩例 4 → 16），不是缺陷。`gate = gate_list or readings` 的 fail-safe 退回語意（全部軸皆
     被排除時寧可全部參與、可能過度保守）**保留**。
     實作義務只有一條＝**可觀測**：gate 面發生排除時，Decision.reason 必須帶
     `gate_excluded=<kind>+<kind>…`（去重、排序）；fallback 觸發（gate_list 為空）時等於
     沒有排除，不得寫出與事實不符的「被排除」。band／cap／rec／per_axis 一個位元不因本條改變。
```

## 2. 為什麼是方向 B（不是單調性夾層）

方向 A（`min(rec_with_gate, rec_all)` 夾層）會讓保險軸／未命中模型軸重新透過夾層否決主力，
實質推翻 R89「保險池不得一票否決主力」——用 (4) 治它等於重開已判過的憲法。方向 B 承認
切換是設計內例外、只補痕跡，(4) 的射程說明 (4b) 一字不改（R121 裁決卡 `DEF-200-244` 原文）。

## 3. 程式面（同批落地）

- `tools/lib/quota_policy.py::decide()`：`excluded = sorted({kind∈readings} − {kind∈gate_list})`
  （僅 `gate_list` 非空時），併入 `reason` 的 note 集合為 `gate_excluded=…`。
- 回歸鎖 `tools/tests/test_quota_policy.py::TestDef200244GateExclusionIsObservable`：
  FALLBACK 軸留痕且 band／cap／rec 與對照組逐位元相等；單軸無痕；全 FALLBACK（fallback 觸發）無痕；
  未命中 MODEL_SCOPED 軸同時帶 `NOTE_MODEL_EXCLUDED` 與 `gate_excluded=`；kind 去重排序。

## 4. 驗收

- `python -m pytest tools/tests/test_quota_policy.py -q` 全綠（實跑輸出見
  `docs/06_quality/CrossPlatform_R126_Debt_Closure.md` §DEF-200-244）。
- 帳本 `DEF-200-244` 依本檔結案（`fixed`）。
