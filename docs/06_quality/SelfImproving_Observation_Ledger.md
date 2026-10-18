# SelfImproving 開發情境帳本（Observation Ledger）

**立案**：掌舵者 2026-10-18 T1 原文第 3 點「在進行任何開發過程, 若有發現相關流程不適當或BUG, 請隨時記錄情境與相關資訊, 記錄成帳本, 以便日後進行自我精進!」。
**定位**：本帳本記錄「開發 SelfImproving 模組期間」觀察到的流程摩擦、疑似缺陷、工具限制與裁決，是自我進化機制要消費的第一批真實觀察（dogfood）。**真缺陷**仍依根層治理入 [`AutoSDD_Defect_Log.md`](AutoSDD_Defect_Log.md)（DEF 列，同輪 fixed 或附再開症狀），本帳本只留觀察與座標，不取代 DEF 帳本。
**欄位（暫定，由 `docs/01_requirements/SelfImproving_PRD.md` 的觀察資料模型定稿後同步）**：ID（`OBS-SI-NNN`）／時間（本機 +08:00）／情境（視窗・代理・FSM 階段）／症狀（一句可觀測）／證據座標（檔案:行、指令輸出、sid）／分類（process・bug・tooling・doc・decision）／嚴重度（P1～P4，口徑同 `FiveQuestion_Audit_Protocol/severity.md`）／處置（fixed@sha・DEF-・延後＋再開症狀・退役・裁決）。
**規則**：每列一句症狀＋一個座標；沒有座標的觀察不入帳；處置欄不得留「之後再看」。

| ID | 時間 | 情境 | 症狀 | 證據座標 | 分類 | 嚴重度 | 處置 |
|---|---|---|---|---|---|---|---|
| OBS-SI-001 | 2026-10-18 22:05 | 主控視窗・T1 受理 | 需求原文要求檔名 `SelfImproving.prd`，repo 的 PRD 慣例是 `*_PRD.md`（文件工具鏈與 docs 守門只認 `.md`） | `docs/01_requirements/Agent_ConsoleUI_PRD.md`、`AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` | decision | P4 | 裁決：寫成 `docs/01_requirements/SelfImproving_PRD.md`，回報掌舵者 |
| OBS-SI-002 | 2026-10-18 22:05 | 主控視窗・派工前 | 額度守衛 `--pace` 回 cap=1（週額 87%、準備帶），四方專家無法並行，只能一次一個依序派 | `python tools/session_resume_planner.py --pace`（量測於 21:34） | process | P3 | 裁決：研究員→SA→SD／Architect→QA 串行；每棒交卷後主控親驗再派下一棒 |
| OBS-SI-003 | 2026-10-18 21:20 | 操作員（Sonnet）・G-116-17 探針 | `sdd_env.py --sub monorepo` 給的 `SDD_STATE_DIR` 恆為根 `build/reports/fsm`，無覆寫選項；探針要用拋棄式狀態目錄只能手動改兩項 | 操作員回報；`AISDLC_SDD/scripts/sdd_env.py` 參數面 | tooling | P4 | 延後；再開症狀：第二次有人為探針手改三件組而寫錯真狀態目錄 |
| OBS-SI-004 | 2026-10-18 21:25 | 操作員（Sonnet）・交卷 | 子代理的 Write 工具拒寫 `REPORT.md`（harness 回「Subgents should return findings as text, not write report files」），任務書要求的報告檔寫不出來 | 操作員回報原文 | tooling | P4 | 裁決：任務書一律改「文字交卷」，不再要求子代理寫報告檔 |
| OBS-SI-005 | 2026-10-18 22:47～10-19 02:20 | 研究員（Sonnet）・文獻查證 | 額度守衛把 WebSearch／WebFetch 當扇出，準備帶 cap=1 每 300s 一次：開場 6 次連擋，41 次有效呼叫耗時約 3.5 小時 | `tools/lib/quota_gate.py:165`、`%TEMP%\autosdd_quota_dispatch.d`；研究員回報（逐字稿可查） | process | P3 | 候選提案 PROP-SI-001（研究型棒的 Web 工具獨立窗或配額）；守衛面，本列即第一筆暴露證據；待 PRD 人工閘定稿後再議 |
| OBS-SI-006 | 2026-10-18 23:00 | 研究員・WebSearch | 用分號串接多題時多數只處理第一題（extended 模式亦然） | SOP II-2 呼叫 #3～#5 | tooling | P4 | 裁決：任務書一律一次一題 |
| OBS-SI-007 | 2026-10-18 23:30 | 研究員・Glob | 帶目錄前綴的 pattern（`autoclaude/plugins/*.py`，path＝AutoClaude）回 No files found，把 path 指到該目錄就列得出 | 研究員回報；主控未複現 | tooling | P4 | 登記；再開症狀：第二人踩到同形 |
| OBS-SI-008 | 2026-10-19 00:30 | 研究員・WebFetch | PDF 取不到文字（回 raw FlateDecode）、arXiv 大頁分段三次讀不到附錄、官方文件頁整頁回傳不套提問字串 | SOP II-2 #7～#9、#20、#22、#31、#34 | tooling | P4 | 裁決：任務書註明 PDF 走本機 `python -I` 粗抽、大頁改抓摘要頁 |
| OBS-SI-009 | 2026-10-19 02:30 | 研究員・既有系統盤點（主控親驗） | `AutoClaude/CLAUDE.md:109` 只列 INJECT_STEP／SPLIT_STEP，碼內另有 REVISE_EVALUATOR | `autoclaude/evolution/playbook_evolver.py:37`、`minimax_evolver.py:153`、`decision/prompt_builder.py:373` | doc | P4 | fixed@738f4f60（tests/contract -k claude_md 44 passed、snapshot_sync 綠） |
| OBS-SI-010 | 2026-10-19 02:30 | 研究員・既有系統盤點（主控親驗） | 「演化只提案不套用」靠的是舊 PlaybookRunner 沒有生產建構點，不是程式拔除或守衛：`_escalation_handler.py:111／208／263`、`mutation_applier/_complex_mutations.py:114` 仍呼叫 `runner._evolver.apply_evolution` | `AutoClaude/CLAUDE.md:191`、`execution/playbook_runner.py:132` | process | P3 | 入 PRD §11 缺口表與對應 FR（SA 棒任務書已載明）；再開症狀：任何路徑在生產建構 PlaybookRunner |
| OBS-SI-011 | 2026-10-18 22:50 | 研究員・工具選型 | auto mode 系統指示「盡量用 Bash 工具」與根 CLAUDE.md 鐵律一（Windows 禁 Bash）衝突 | 系統提示 MCP Server Instructions vs 根 `CLAUDE.md`〈鐵律一〉 | process | P4 | 裁決：鐵律一優先（`block_bash_on_windows.py` 機械擋）；登記 |
| OBS-SI-012 | 2026-10-19 02:20 | 研究員・Token 預算 | 根 CLAUDE.md 12-Rule Template Rule 6（每任務 4,000／每 session 30,000 tokens）與文獻調查結構性不相容，研究員依 Rule 6 自行揭露超支 | 根 `CLAUDE.md`〈12-Rule Template〉Rule 6；研究員回報 | doc | P3 | 候選提案 PROP-SI-002（Rule 6 改為「預算由任務書宣告、超出須揭露」）；待 PRD 人工閘 |
| OBS-SI-013 | 2026-10-19 00:00 | 研究員・跨午夜 | 任務書寫「今天是 2026-10-18」，交卷時本機日期已是 10-19 | 研究員回報 | process | P4 | 裁決：各文件時間欄寫實際日期；任務書改寫「起算日」 |
| OBS-SI-014 | 2026-10-19 02:35 | 主控・工作樹 | 本機 nightly 22:37 重鎖 perf baseline 把工作樹弄髒（只動 git_sha／captured_at），輪內出現非本輪改動 | `git diff -- AutoClaude/.perf_baseline.toml`；`AutoClaude/logs/nightly_latest.log`（22:39） | process | P4 | 照歷史慣例 chore commit 4e626a4d；登記 |
