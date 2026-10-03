# 五問覆核審計協定（判準②′ 的審計錨；輪不變模板）

用途：把「每輪四方覆核怎麼做」凍結成可雜湊的模板，讓「近 6 輪窗口」有一個不會被悄悄改動的分母。
判準②′ 的提案全文見 `docs/06_quality/CrossPlatform_R191_FiveQuestion_Verification_Evidence.md`〈八〉
（「判準②′ 修憲」），採納經過見 `docs/06_quality/CrossPlatform_R192_FiveQuestion_Convergence_Evidence.md`
〈八〉；量測由 `tools/probe/audit_session.py` 執行（只印不擋）。

## 目錄
- `charter_{arch,sa,sd,qa}.md`：四個角色的章程（角色、審查面、輸出格式）；事實一律用槽位。
- `discipline.md`：共同紀律（工具上限、唯讀、rc 不接管線、鐵律四、回傳格式、判決規則、Windows 形態）。
- `severity.md`：嚴重度口徑、家族登記制、拆殘判法。
- `probes/PA|PB|PC.txt`：活體探針三型 prompt 逐字（`<n>`／`<scratchpad>` 與 `{{ROUND}}` 為槽位）。
- `params.json`：②′ 全部判準常數都住這裡（本段點名的鍵集合與該檔逐字相等，有測試釘住）：
  - 數值：`q1b_min_n`（Q1′b 的最小母體，不足印 NOT-EVALUABLE，不再對 0／0 印 PASS）、`q1c_gate`／
    `q1c_n`（Q1′c 取最近幾支；取到每輪 1～3 支真實 session 的窗口內可達）／`q1c_first_calls`（Q1′c 看前幾個
    呼叫；與 `q2_max_index`／`claim_max_uses` 同寬，早期的阻斷才看得到）、`claim_max_uses`（Q1′b 只計前幾個
    呼叫內的宣稱）、`claim_lookback`（宣稱往回看幾個 tool_result 找阻斷）、`q2_max_index`／`q2_min_n`、
    `q3_n`／`q3_min_pairs`／`q3_tolerance_tokens`、`q3_quiescent_seconds`（Q3′ 只納入靜止配對：feed 與
    逐字稿最後 usage 較晚者已過這麼多秒；在途視窗的逐字稿落盤落後 feed 一則，不靜止者排除並印
    NOT-QUIESCENT）、`q4_max_age_days`（Q4′ 證據新鮮度）、`rounds_required`。
  - 句型（正則是 JSON 字串，反斜線雙寫）：`claim_re`／`claim_exc_re`／`quote_re`（宣稱、排除、引述）、
    `planner_re`、`feed_read_re`（Q2′ 認列的唯讀現查退路：Read context feed 或額度快取檔）。
  - 工具集：`converge_tools`（收斂型工具）、`parity_non_shell_tools`（`--parity` 逐支崩塌判準不計入的
    非 shell 內建工具；此前寫死在量測器碼裡）。
  - 🔴 **量測器碼不入 manifest，判準常數全部住 `params.json`**：改任何判準數字或句型＝改本檔＝重置窗口；
    碼裡不得再寫死判準常數（定義漂移不重置窗口，正是這條規定要堵的洞）。

## 事實槽位（不入雜湊）
`{{ROUND}}` 輪號、`{{HEAD}}` 起算 commit、`{{DATE}}` 日期、`{{PREV_ROUND}}` 上輪結論指標。
每輪任務書＝本目錄模板＋槽位填值；填值只住當輪任務書，不寫進本目錄。

## 雜湊規則
manifest＝本目錄每個檔的（相對路徑, sha256(內容；CRLF 先正規化為 LF)），依路徑排序；
`protocol_sha256`＝sha256(`json.dumps(manifest, ensure_ascii=False)`)。算法在 `audit_session.py --protocol-status`
（實作住 `tools/probe/fivequestion_ledger.py`），結果登記在輪帳本 `FiveQuestion_Round_Ledger.jsonl`
（append-only，每輪一列）。

## 窗口規則
`window_len`＝輪帳本尾端連續同 `protocol_sha256` 的列數（遇 `window_reset:true` 即止）。
評估式（`rounds_required`＝6）：window_len ≥ 6，且近 6 輪 `new_p_le2` 合計 ≤ 2、`p1` 合計 = 0，
且最近一輪 `new_p_le2` 為零。不足即印 `NOT-EVALUABLE(k/6)`；量測器 rc 恆 0，不得接閘門。
評估式只含家族計數與 `p1`，不含 Q1′～Q4′（`--protocol-status` 會就地註明；Q4′ 另印九格讀判）。

## 更動＝重置，不是紅燈
改本目錄任一檔（含一個字）→ `--protocol-status` 印 `PROTOCOL-CHANGED`；須追加新列帶
`window_reset:true`＋理由，窗口自該列重數。不得無聲換協定，也不必為了換協定而假裝沒換。
完整性閘（`new_p_le2`／`excluded_p_le2` 必須涵蓋窗口內所有 P1／P2 列）見 `severity.md`；
`--protocol-status` 會印出該檢查的結果（`完整性閘 ✓`／`✗ 漏列：…`，rc 恆 0）。
