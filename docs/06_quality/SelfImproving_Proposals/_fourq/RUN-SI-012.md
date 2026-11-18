# 四問審視 RUN-SI-012
## Q1 此頂尖專家會做那些我沒有想到的事？
- Q1-1｜領域：SRE 守衛回歸｜做法：每次 Claude Code 升版後以固定探針回放全部守衛判決表｜機制：多 hook 的 updatedInput 決策順序與 decision:block 生效範圍改動時重跑判決並比對｜座標：src=cc-releases may start blocking calls、tools/lib/hook_wiring.py:1｜查詢：「updatedInput」＝零命中｜查詢：「決策順序」＝零命中
- Q1-2｜領域：無人續跑可靠性｜做法：無人續跑前顯式釘住中斷回合重跑開關｜機制：CLAUDE_CODE_RESUME_INTERRUPTED_TURN 在 continue:false 停下的回合上的行為已變更，不釘住就隨升版漂移｜座標：src=cc-releases RESUME_INTERRUPTED_TURN、tools/lib/model_roles.py:1｜查詢：「顯式釘住」＝零命中｜查詢：「INTERRUPTED_TURN」＝零命中
- Q1-3｜領域：容量與成本工程｜做法：以替身未識別模型 ID 重驗水位守衛的視窗推斷｜機制：未識別模型 ID 的 context 假設由 200K 改 1M 會讓水位分母漂移｜座標：src=cc-releases context window assumed、.claude/hooks/context_budget_guard.py:1｜查詢：「未識別模型 ID」＝零命中｜查詢：「水位分母」＝零命中
## Q2 在哪裡找到最前沿的資料與研究結果？
- Q2-F1｜來源：cc-releases｜座標：src=cc-releases may start blocking calls｜發現：hook 的 decision:block 在更多情況生效，總是印出 block 的 hook 可能開始擋呼叫，守衛判決需重放確認
- Q2-F2｜來源：cc-docs-index｜座標：src=cc-docs-index slow uncached turn in Claude Code｜發現：官方新增 prompt caching 文件頁，可作為快取冷熱成本判準的外部對照
- Q2-G1｜URL：https://code.claude.com/docs/en/hooks｜分級：T1｜為何前沿：hooks 事件與 decision 語意的官方完整參考，登記表只有 hooks-guide 而無此頁｜更新頻率：隨 Claude Code 版本更新
## Q3 使用哪些方法與工具？
- Q3-1｜對象：Q1-1｜方法：固定探針的判決表回放（升版前後差異比對）｜工具：tools/check_hooks_liveness.py、tools/probe/shell_command_corpus.py
- Q3-2｜對象：Q1-2｜方法：升版後以逐字稿重放續跑決策、檢查是否有重跑被停回合｜工具：tools/sessionctl.py、tools/probe/audit_session.py
- Q3-3｜對象：Q1-3｜方法：以替身模型 ID 重算水位分母並與實際值對照｜工具：tools/lib/quota_policy.py、tools/probe/waste_census.py
## Q4 如何證明資料與改善結果是有正面影響與收斂的？
- Q4-1｜擬提案：升版後守衛判決回放｜指標類別：症狀：守衛判決漂移｜症狀定義：`python tools/probe/shell_command_corpus.py --summary`｜反證：回放判決與升版前一致，但真實逐字稿仍出現應擋而放行的指令｜收斂：引 PRD 〈FG-N 邊界與誠實劃界〉，守衛判決差異連續多輪為零且症狀不再被掌舵者回報
- Q4-2｜擬提案：未識別模型 ID 的水位推斷重驗｜指標類別：症狀：水位推斷與實際視窗不符｜症狀定義：`python tools/session_resume_planner.py --check`｜反證：替身模型推斷一致，但真機簡報顯示的水位與實際壓縮時機仍有落差｜收斂：引 PRD 〈FG-N 邊界與誠實劃界〉，同一症狀不再於真機回報中重現
