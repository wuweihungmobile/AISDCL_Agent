# CrossPlatform R87 護欄層重釘證據

> 對應 `_GUARD_LINES_REPIN_LOG` 的 R87 那一列。重釘理由欄依規只能是索引，全文在此。

## 淨額與逐檔清單

| 項 | 值 |
|---|---|
| 重釘前 | 83470 |
| 重釘後 | 83607 |
| 淨額 | +137 |
| 逐檔 | `tools/tests/test_quota_policy.py` +137（唯一成長檔） |

## 為什麼必須長大（非淨減法輪）

R87 開工時舵手把 `spend` / `extra_usage` 兩軸從取數層排除，誤讀依據是
`is_enabled: false` / `enabled: false`。真意是 `used 610 > limit 500` 已撞月度支出上限，
購買功能因此被 org 層停用 —— `enabled:false` 是撞頂的**後果**，不是「這一軸不算數」。

後果：本輪派出的全部 subagent 撞 `You've hit your monthly spend limit`，
消耗 1,319,703 tokens、331 次工具呼叫、634 秒，**零產出**。

架構缺口（本次重釘要買下的東西）：判讀層 `quota_policy.decide()` 的
「halt 一票否決」不變式當時**完好無損**，但它只保證「給定的軸不會被放寬」，
**不保證「軸不會消失」**。舵手是從上游取數層把輸入抽掉的，於是整道保護
在**零判準觸發**的情況下失效，且失敗表徵與「一切正常」完全相同。

## 買到什麼（新增的鎖）

| 鎖 | 守什麼 |
|---|---|
| `test_quota_policy.py::TestR87TheMeterMayNotDropAThrottlingAxis` | 事故當下的真實 payload 釘成 fixture；任何讓它不再 halt 的改動當場轉紅。含**鑑別力自證**：重演錯誤實作（排除兩軸）必須不再 halt，證明前面幾條不是恆真的假鎖 |
| `test_quota_policy.py::TestR87AccountPostureIsKnownBeforeDispatch` | 派工前置：帳號指紋與 credits 姿態。含「沒有 credits 的帳號預設無 fallback」「健康的池必須回 True（鑑別力）」「讀不出來不得樂觀」 |

## 掌舵者裁決（本次重釘的立案理由）

逐字：「不是要寫在程式架構控制嗎？怎麼變成你在控制？」
⇒ 散文約束對當下的模型零攔阻力，所以「模型不得推翻機制」必須是**機械事實**。
本次重釘買的就是那個機械事實。

帳本：`DEF-200-107`（事故本體）、`DEF-200-108`（派工前置檢查缺口）。
