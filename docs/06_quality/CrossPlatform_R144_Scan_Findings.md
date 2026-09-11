# CrossPlatform R144 — DEF-200-275 第五輪四方複審收斂＋DEF-200-281／282 收尾：護欄層淨額記帳

- **輪籤**：R144（2026-09-11，macOS；並行子 agent 執行〔Dev-A／Dev-A2／Dev-B／Dev-C／喚醒鏈鑑識代理〕，
  主控收尾單人窗口 commit）。
- **體例**：不使用前瞻輪號句型；數字皆本場親跑（`--print-guard-lines`）或各包 `[他包回報]` 標記。
- **上承**：R143（DEF-200-275 第四輪＋DEF-200-278 首輪收尾，見 `CrossPlatform_R143_Scan_Findings.md`）。
  本輪非開新一輪 CrossPlatform 掃描輪四件套，僅為 DEF-200-275 第五輪四方獨立複審收斂＋
  DEF-200-281（喚醒鏈斷裂）／DEF-200-282（稽核帳本效能）兩項缺陷收尾附帶的護欄層淨額記帳延伸。

---

## §1 護欄層淨額承認

<!-- guard-total:R144 --> R144 護欄層累積淨額＝ 97056 → 97488（+432＝+130 D15 判準新增 ＋ +24 同輪自身漂移收斂 ＋ +120 DEF-200-281 首輪收尾 ＋ +34 同輪自身漂移收斂 ＋ +92 DEF-200-281 第二輪收尾 ＋ +32 同輪自身漂移收斂，全額歸回歸鎖軌）——
逐項見下方 §2；證據見 `docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md`〈第五輪〉節
與 `docs/06_quality/CrossPlatform_DEF200278_Halt_Handoff_Evidence.md`〈第二輪〉節；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-275／DEF-200-279／DEF-200-280／DEF-200-281／
DEF-200-282。此附記為 doc-total 對帳（≥2 站點）另一站點寄居 `AutoSDD_improving_112.md`，同
R129～R143 寄居體例。round-label-ok

## §2 逐檔清單

| 檔 | 前 | 後 | 淨額 | 歸類 |
|---|---|---|---|---|
| `tools/tests/test_claim_provenance_r86.py`（D15） | 806 | 936 | +130 | 回歸鎖軌（Stop hook 第五判準） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py`（自身漂移，第一批） | 97056 | 97210 | +24（合計，2 列） | 回歸鎖軌（記帳誠實度） |
| `tools/tests/test_wake_chain_halt_r278.py`（DEF-200-281 首輪） | 299 | 399 | +100 | 回歸鎖軌（halt 標記自檢＋relay 白名單） |
| `tools/tests/test_quota_policy.py`（DEF-200-281 首輪隔離止血） | 3396 | 3416 | +20 | 回歸鎖軌（測試夾具環境隔離） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py`（自身漂移，第二批） | 97210 | 97364 | +34（合計，7 列） | 回歸鎖軌（記帳誠實度） |
| `tools/tests/test_wake_chain_halt_r278.py`（DEF-200-281 第二輪） | 400 | 492 | +92 | 回歸鎖軌（RC-3 per-sid 閂鎖＋naive-now 拒寫） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py`（自身漂移，第三批） | 97456 | 97488 | +32（合計，6 列） | 回歸鎖軌（記帳誠實度） |
| `tools/lib/guard_bucket_policy.py`（`guard_self` 分桶，不計入本檔淨額） | 3416 | 3431 | +15 | shrink-only 分桶（同輪重釘，任務書明文授權，非正式四方複審） |

SDD 子專案側（`AISDLC_SDD/AISDLC_SDD_v0.30/`）的 hook／runtime／測試改動（D11～D16、R-D11／R-D13
複審修復、Dev-C 稽核帳本效能修復）計入該子專案自身的 LOC 政策，不落本檔棘輪射程；逐檔見證據檔
〈第五輪〉§修法逐檔。

## §3 本輪摘要

**DEF-200-275 第五輪（D11～D16）**：commit ea6113d push 後掌舵者要求 Architect／SA／SD／QA 四方獨立
複審「已修好」的宣稱，四方一致判問題 1「新視窗一開就被擋」與問題 2「不用真實 /context 或 API 查數據」
皆為 partial，收斂出 (a) PENDING×首擊 m=None 首擊 deny、(b) per-stage cap 仍寫專案級 ESCALATION
致新視窗全擋不自癒、(c) 指定值分母對 observed_model 零交叉、(d) Stop hook 無「被擋／水位」宣稱佐證
判準四項真缺陷，另立 (e) SD-06／(f) ARCH-06 兩項另案（已立 DEF-200-279／DEF-200-280）。裁決
D11～D16 分兩包（Dev-A：D11／D12／D13／D16 SDD 治理面；Dev-B：D14／D15 量測面＋根層 Stop hook）
並行修復，先紅後綠。

**R-D11／R-D13 複審修復（Dev-A2）**：複審（唯讀）用合成重現腳本抓到兩個真缺陷並判 REJECT——
R-D11（PENDING 放行未排除 Rule 9.6 規格檔寫入絕對禁令）、R-D13（per-stage cap marker 未隨 stage
換新，導致新 stage 的 cap 事件拿不到自己的 `abort_report`）。Dev-A2 修復後先紅後綠，複審轉 APPROVE。

**Dev-C（DEF-200-282，稽核帳本效能）**：`context_ledger_post.py` 逾 8.0s 未回應被 router 中止放行、
留 `.part.*` 孤兒。量測拆解：>95% 耗時落在純 Python YAML 編解碼；改用 libyaml C 綁定
（`CSafeLoader`/`CSafeDumper`，`getattr` 保底回純 Python），1500 筆規模 append 耗時
0.6567s→0.1192s；802KB 真實活帳本端到端 5.09s→0.42s（~12x）。另修孤兒 `.part.*` 清理
（`cleanup_orphan_part_files`，POSIX `os.kill(pid,0)`／Windows `psutil.pid_exists()` 保守 fallback）。
複審 APPROVE，備註 AISDLC_SDD 未宣告 `psutil` 依賴 ⇒ Windows 分支實質 no-op（fail-safe）。

**DEF-200-281（喚醒鏈鑑識代理，兩輪修復）**：自願停機喚醒鏈斷裂，根因 RC-1（`test_quota_policy.py`
測試夾具未隔離 `CLAUDE_CODE_SESSION_ID`／`CLAUDE_PROJECT_DIR`，凍結 `NOW` 常數污染真實 halt 標記為
一個月前的日期）疊加 RC-3（halt latch machine-wide、非 session-scoped）。首輪修復：F-1 halt 標記
寫入前自檢（牆鐘偏移／reset_at 已過即拒寫）＋F-2 `relay_problems()` 補 `"halt-marker"` 白名單（真
launchd 端到端演練揪出的整合缺口，修前每次靠 halt 標記完成的循環都會觸發不必要的自癒並靜默重置
`allow_resume`）。第二輪（複審點名）：RC-3 per-sid 閂鎖鍵＋naive-now 拒寫（`now` 缺 tzinfo 時拒寫而
非拋 `TypeError` 崩掉整條武裝路徑）。真 launchd 端到端演練（假 sid，零真實模型 API 呼叫）驗證
`arm_reset → probe（零 token）→ resume 嘗試（安全失敗）` 完整鏈路。詳見
`CrossPlatform_DEF200278_Halt_Handoff_Evidence.md`〈第二輪〉。

**治理 yaml 污染事件**：本輪期間某探針漏加 telemetry 前綴，觸發 `transition()` 的
`rule_loader.record_state_fires` 以 `yaml.safe_dump` 回寫 11 支 tracked `governance/rules/R-9.*.yaml`
（形態重排＋`fire_count` 灌值）。主控以 `git show HEAD:<path> > <path>` 逐支還原 10 支；`R-9.2` 因
本輪確有合法 `failure_mode:` 文字改動（D13 session 級語意），改為手動重寫為只含該改動的版本。還原後
`git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/` 只列 R-9.2。

**收尾實測**（主控親跑，還原治理 yaml 污染後）：
```
$ SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
1872 passed, 8 skipped, 34 deselected, 14 subtests passed in 42.16s   rc=0
```

## §4 未做事項（另案，承本輪〈未做事項〉節）

- DEF-200-279（並行 subagent 共用專案級 FSM-STATE）、DEF-200-280（v0.30 settings.json PreToolUse
  matcher 缺 `Agent|Workflow`）：本輪僅立案，未修復，狀態皆 open。
- `quota_prepare_actions()` 閂鎖鍵同型未含 sid（DEF-200-281 延伸，優先權較低，未修）。
- Windows 側：喚醒鏈修法皆未在 Windows 真機驗證；Dev-C 孤兒清理的 `psutil` Windows 分支未實測
  （AISDLC_SDD 未宣告該依賴，實質 no-op）。
- `guard_self` shrink-only 分桶本輪重釘（3416→3431）為單一代理在任務書明文授權下執行，非正式四方
  複審，留待掌舵者事後追認或推翻。
