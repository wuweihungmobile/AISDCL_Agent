# R119 護欄層淨額標記

<!-- guard-total:R119 --> **護欄層累積淨額（`--print-guard-lines` 現查）：91247 → 91646（+399）**
——P1-6 skip 天花板①②③與 M6 落款④共同變更鎖落地（`test_skip_ceiling_ratchet_direction.py`
165→304，+139，含全套背景跑覆審揪出的 subprocess encoding 補丁）＋本表與凍結表自身編修
（含到期義務兌現列＋兩筆凍結前綴協同改寫帳本新列，`test_adr_xplat001_c1c2_lock.py`
7122→7153，+31）。全額歸功能軌（`[全額功能軌]`：新增治理鎖，非驗收既有 PRD/ADR 指定的
回歸測試，不進 `_REGRESSION_LANE_LOG`）。同輪兌現 `_REPIN_NET_CAP_DUE_ROUND=119` 到期義務
（cap 570→564）並重新武裝下一段（R121，559）；凍結前綴協同改寫帳本兩列載體皆＝DEF-200-240。
逐檔清單與必要性辯護見 `docs/06_quality/CrossPlatform_R119_Guard_Repin_Evidence.md`。

🔴 **同輪修復包續（DEF-200-240 同批延續，push 被 pre-push 擋下後修復，+229）**：F1——落地時的
共同變更鎖判準是**檔案級**（①②③任一檔出現在變更清單即紅），落地當回合就抓到了自己：本鎖
自身的程式碼住在其中一個檔案裡，`a1fbbba`（新增本鎖程式碼）只是 touch 檔案、`_FROZEN_CEILING_MAX`
零變動，卻仍被要求同動④。修法：判準改為**剖面鍵值級**——只有 `_RUNTIME_SKIP_CEILING`／
`_RUNTIME_SKIP_CEILING_MAX`／`_FROZEN_CEILING_MAX` 三張 dict 的字面在兩版之間有實質差異
（正規化掉註解後逐字比對）才要求同動④；新增 `_extract_dict_literal`／`_dict_literal_changed`／
`_source_path_value_changed` 等取數函式，反事實測試由四格擴為五格（新增「層③被 touch 但值零
變動 ⇒ 綠」），`test_skip_ceiling_ratchet_direction.py` 304→508（+204）。F2——
`governance_docs.py` E501（`round-label-ok` 與輪號拆行未拆開，同行斷行修復），零貢獻護欄層。
本表與凍結表自身編修（新增稽核列三支＋凍結前綴協同改寫帳本一列），`test_adr_xplat001_c1c2_lock.py`
7153→7178（+25）。逐項見 `docs/06_quality/CrossPlatform_R119_Guard_Repin_Evidence.md`。
