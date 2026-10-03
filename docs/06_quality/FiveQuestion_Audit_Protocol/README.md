# 五問覆核審計協定（判準②′ 的審計錨；輪不變模板）

用途：把「每輪四方覆核怎麼做」凍結成可雜湊的模板，讓「近 6 輪窗口」有一個不會被悄悄改動的分母。
判準②′ 全文與採納經過見證據檔〈八〉；量測由 `tools/probe/audit_session.py` 執行（只印不擋）。

## 目錄
- `charter_{arch,sa,sd,qa}.md`：四個角色的章程（角色、審查面、輸出格式）；事實一律用槽位。
- `discipline.md`：共同紀律（工具上限、唯讀、rc 不接管線、鐵律四、回傳格式、判決規則）。
- `severity.md`：嚴重度口徑、家族登記制、拆殘判法。
- `probes/PA|PB|PC.txt`：活體探針三型 prompt 逐字（`<n>`／`<scratchpad>` 與 `{{ROUND}}` 為槽位）。
- `params.json`：②′ 各閘門數值（q1c_gate、q1c_n、q2_max_index、q3_n、rounds_required…）與量測句型
  （宣稱／排除／引述／planner 的正則、收斂型工具集；正則是 JSON 字串，反斜線雙寫）。

## 事實槽位（不入雜湊）
`{{ROUND}}` 輪號、`{{HEAD}}` 起算 commit、`{{DATE}}` 日期、`{{PREV_ROUND}}` 上輪結論指標。
每輪任務書＝本目錄模板＋槽位填值；填值只住當輪任務書，不寫進本目錄。

## 雜湊規則
manifest＝本目錄每個檔的（相對路徑, sha256(內容；CRLF 先正規化為 LF)），依路徑排序；
`protocol_sha256`＝sha256(`json.dumps(manifest, ensure_ascii=False)`)。算法在 `audit_session.py --protocol-status`，
結果登記在輪帳本 `FiveQuestion_Round_Ledger.jsonl`（append-only，每輪一列）。

## 窗口規則
`window_len`＝輪帳本尾端連續同 `protocol_sha256` 的列數（遇 `window_reset:true` 即止）。
評估式（`rounds_required`＝6）：window_len ≥ 6，且近 6 輪 `new_p_le2` 合計 ≤ 2、`p1` 合計 = 0，
且最近一輪 `new_p_le2` 為零。不足即印 `NOT-EVALUABLE(k/6)`；量測器 rc 恆 0，不得接閘門。

## 更動＝重置，不是紅燈
改本目錄任一檔（含一個字）→ `--protocol-status` 印 `PROTOCOL-CHANGED`；須追加新列帶
`window_reset:true`＋理由，窗口自該列重數。不得無聲換協定，也不必為了換協定而假裝沒換。
完整性閘（`new_p_le2`／`excluded_p_le2` 必須涵蓋窗口內所有 P1／P2 列）見 `severity.md`。
