# Agent 憑證紀律 — 單一真相源（Single Home）

**適用**：本版 `agent/core/*.yaml` 與 `agent/specialized/*.yaml` 中所有以
`evidence_discipline.inherits_from` 或 `spec_compliance_check.checklist.correction_protocol`
指向本檔的 agent。

> 🔴 **本檔存在的理由＝「同一份知識只准有一個家」。**
> 這幾條紀律先前只以 runtime agent 的形式存在（見下方〈一、來源〉），
> 而實際產出 SDD 文件的 persona agent（SA／SD／QA…）對它們零約束。
> 修法**不是**把條文複製進每一支 agent（那會變成 N 個家、只有一個會被改），
> 而是把條文寫在這裡一次，agent 端只留「指向本檔 + 套用範圍」的引用。
> **凡引用者不得重述本檔條文**——重述即為第二個家，由
> `AISDLC_SDD/scripts/agent_scg_anchor_lint.py` 的「單一真相源引用可解析」判準守著
> （引用路徑必須解析到磁碟上的本檔；改名／移位即 CI 紅）。

---

## 一、來源（provenance）

| 這一半 | 既有的家 | 逐字內容 |
|--------|---------|---------|
| **執行接地**（不准用靜態閱讀取代實跑） | `agent/specialized/sdd-evaluator-zh.yaml` 的 `responsibilities.boundaries` | 「禁止以靜態 diff 取代實跑（必須有 ExecutionObservation 客觀資料才裁決）」 |
| **對抗複審**（pass 不是自己說了算） | 同上，`responsibilities.core` | 「verdict=pass 聲明須由第二 skeptic 子代理對抗 refute」 |

本檔**不複寫**那兩條，只把它們從 runtime 層延伸到文件層（下方第二、三節），
並補上 runtime 層沒有、而文件層天天在犯的那幾條。

---

## 二、實測憑證紀律（evidence discipline）

1. **無實測即無宣稱**：任何「已驗證／已達標／已覆蓋／零遺漏／已修好」的宣稱，
   必須在同一份產出裡附上：**指令逐字 ＋ 真 rc ＋ ≤3 行關鍵輸出 ＋ 執行環境**
   （OS／直譯器絕對路徑）。貼不出來就改寫成「未驗證（靜態推論）」——不是刪掉宣稱，是**降級**它。
2. **rc 衛生**：讀 rc **絕不接管線**（先重導向檔案，再單獨讀退出碼）。
   接了管線之後讀到的是管線最後一個元素的 rc，而它通常是 0＝真紅被讀成綠。
3. **錨用符號不用行號**：引用程式／文件時錨在符號名或字串上；行號在下一次編輯就失準，
   而失準的錨不會讓任何東西轉紅。
4. **取數管道須先自證活著**（pipeline liveness）：任何 grep／掃描在被當成「沒有」之前，
   必須先用一個**已知一定命中**的對照 pattern 證明管道是活的，並把對照輸出一併附上。
   命中 0 且無對照證明者，一律記為 `UNMEASURED`，**不得記為 `NONE`**——
   「查不到」與「真的沒有」在版面上長得一模一樣。
5. **pass 須經對抗**：`pass`／`APPROVE` 結論須由獨立 skeptic 視角複審；refute 成立即翻 `FAIL`。

## 三、夾具真實性（fixture realism）

**夾具不得比被測世界簡單。** 詳細反模式清單（含母本來源要求）住
`agent/core/07.qa-tester-zh.yaml` 的 `sdd_phase05_qa_tester.automated_at_format`
（`anti_patterns` ＋ `fixture_realism_gate`）——那是 QA 產出面的家，本檔不複寫，只在此登記它存在。

## 四、訂正協議（correction protocol）

訂正一句假話時最常見的失敗，是**在訂正文裡寫下另一句假話**——而訂正文帶著「🔴 訂正」
字樣，讀起來比周圍句子更可信，因此最難被抓到。

1. **訂正的最後一個動作是重新現查標的本身**，不是重讀那句話。
2. **訂正必須全文搜尋同一宣稱的其他站點並一併處置**（同一份知識不得留兩個家）；
   只改到手邊那一個站點的訂正，等於把不一致藏得更深。
3. **被訂正的原文逐字保留在同一處**（註解或引文皆可），禁止靜默覆寫——
   看不到原文的讀者無法判斷這次訂正本身對不對。
4. **訂正不得放寬既有門檻**：把判準改鬆讓紅轉綠，不是訂正。

---

**引用寫法**（agent yaml 端，只要這幾行；不要抄上面的條文）：

```yaml
  evidence_discipline:
    inherits_from: "agent/EVIDENCE_DISCIPLINE.md"
    applies_to: "本 agent 全部 document_responsibilities 產出與 sdd_skills 結論"
```

```yaml
      correction_protocol: ["見 agent/EVIDENCE_DISCIPLINE.md〈四、訂正協議〉（單一真相源，本處刻意不複寫條文）"]
```
