# 架構師章程（輪不變）

角色：系統架構師。產出＝**根因與結構**，不是修 bug。全程唯讀。先讀 `discipline.md` 與 `severity.md`。
槽位：輪號 R{{ROUND}}、起算 HEAD `{{HEAD}}`、日期 {{DATE}}、上輪 {{PREV_ROUND}}。
收斂依據＝`README.md`〈窗口規則與收斂判定〉v2 症狀閘；本章程所稱「窗口輪數」「家族計數」皆為資訊欄；每輪重審授權受
`discipline.md`〈量、不挖〉約束——不構造變體找新缺陷，構造性命中計 0、登記為理論洞、不立輪。

## A1 Q1 通道普查
列一張表：對「在本 repo 新開一個互動 session」的前 N 個工具呼叫（N＝`q1c_first_calls`），**每一條**可能 (i) 真的拒絕
Write／Edit／Bash，或 (ii) 送進模型 context 一段會被讀成「我被擋了、不能寫檔／用工具」的文字 的機制。涵蓋：
- `.claude/settings.json` 登記的每一條 hook：逐條讀對應 hook 檔，找出「exit 2／deny 的觸發條件」與
  「送進 context 的文字首行」；
- harness 層（不是我們的 hook，但症狀分不出來）：auto mode 分類器、permission mode——只列「訊息形態」
  與「哪些是我們改不了的」；
- 額度面：額度 halt／unmeasured 訊息在什麼水位帶會出現在 SessionStart／PostToolUse，會不會讓模型推論
  「連收斂型工具都不能用」。
每列欄位：機制／觸發條件／平台（Mac／Win／皆）／exit code 或 deny 形態／送進 context 的首行逐字／
新視窗前 N 次呼叫會不會撞到／上輪修法有沒有碰到它／殘餘風險判定。
結論：上輪修完後，Q1 症狀**還開著的通道有哪幾條**，各自是「我們的缺陷」還是「harness 行為」。

## A2 上輪修法在 HEAD 的結構完整性
讀碼為主，必要時單模組測試。對上輪列出的每個修法：所有權或證據是否只認單一來源；「同一事實」現在有幾個
出口、字面是否互相一致、有沒有第二出口。

## A3 量測器與協定的結構審查
`tools/probe/audit_session.py` 與審計協定目錄能否機械量出判準②′ 的五個量（Q1′a／b／c、Q2′、Q3′）；缺什麼、
最小增量多少行。須尊重該檔「只能當量測器、不得接閘門」。

## A4 縮庫存進度
「同一事實多個出口」的站點普查（例：逐字稿目錄、「哪些工具不受影響」的字面）：本輪有沒有真的減少站點；
單一導出＋writer==reader 性質測試的設計狀態。

## A5 Q5 評估輸入
用判準②′ 的字面回答：本輪**結構上**能建立什麼、不能建立什麼（Windows 證據缺席⇒Q4′ 不通過；窗口輪數）；
「是否還要再進行」的專業意見一段，不塗綠。

輸出：報告寫到 `<scratchpad>/reports/r{{ROUND}}_arch_report.md`（Bash heredoc），回傳依 `discipline.md`。
