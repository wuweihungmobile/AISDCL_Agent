# R122 精準修復輪 — 護欄層淨額承認與途中發現

> **性質**：本輪不是掃描輪。本檔承擔兩件事：① `repin_log_problems()` 款(9) 強制的
> **護欄層累積淨額承認**（下節的 `guard-total` 標記行，與 `_GUARD_LINES_REPIN_LOG` 表尾
> 雙向對帳，寫錯即紅）；② 本輪途中發現但**刻意不當場開新戰場**的項目（純結案／精準修復輪
> 紀律：找到先記著）。逐筆結案取證在 `CrossPlatform_R122_Debt_Closure.md`。
> **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型。

---

## §1 護欄層累積淨額承認

<!-- guard-total:R122 --> 本輪護欄層行數 `91793→91668`（淨額 −125）。

四列稽核痕跡逐列如下（與
`tools/tests/test_adr_xplat001_c1c2_lock.py::_GUARD_LINES_REPIN_LOG` 末四列逐字對應）：

| 列 | 起 → 後 | 淨額 | 性質 |
|---|---|---|---|
| 1 | 91793 → 92646 | +853 | 全額功能軌：三筆缺陷的回歸鎖落地 |
| 2 | 92646 → 92660 | +14 | 同輪追加：貼表當下本檔尚未含前兩列 |
| 3 | 92660 → 91649 | −1011 | **淨減法**：護欄層散文搬遷抵銷 |
| 4 | 91649 → 91668 | +19 | 同輪追加：兩筆到期義務兌現＋凍結表同步 |

合計 −125 ⇒ **款(11)（連續上升不得超過兩輪）的 streak 歸零**，款(10)（單輪上限）亦未撞線。

**逐檔清單**（搬遷面，皆為歷史沿革段落逐塊逐字保全，接收檔＝
`CrossPlatform_R122_Guard_Prose_Migration.md`）：

| 檔 | 前 → 後 |
|---|---|
| `test_check_hooks_liveness.py` | 3581 → 3296 |
| `test_archive_defect_log.py` | 3989 → 3839 |
| `test_run_root_unittests.py` | 2558 → 2422 |
| `test_bash_probe_spec_contract.py` | 983 → 865 |
| `test_dev_start.py` | 6636 → 6527 |
| `test_install_windows_nightly.py` | 1469 → 1385 |
| `test_smoke_ci_sync.py` | 1334 → 1258 |
| `test_context_budget_guard.py` | 9906 → 9835 |

**新增面**（本輪三筆缺陷的回歸鎖）：`test_apply_lock.py`／`test_check_archive_required.py`／
`test_archive_apply_locked.py` 三支新檔，加上 `test_run_root_unittests.py` 與
`test_context_budget_guard.py` 的擴充。

**同輪兌現的兩筆到期義務**（皆非本輪造成，是時鐘走到）：

1. `_REPIN_NET_CAP_SCHEDULE` 追加 `(122, 559)`——款(12) 的「那把尺自己是不是還停在當初取的
   最寬值」。同輪重新武裝下一段，步伐續守「刻意變小」。
2. `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 具名展延（理由逐字寫在該常數旁，判準明令
   「不得靜默沿用」）。展延換到的不是時間而是一個**已驗證的手法**——本輪的散文搬遷證實
   「把史料逐字搬進具名證據檔」在本 repo 可行且安全，而那正是四支 `[ROOT-TOOLS]` 檔真拆
   要用的手法。
3. `_PHASE2_REVIEW_LOG` 追加 `[維持觀察]` 列（上一列是 `[落地]` ⇒ 款(5) 連續計數自本列
   起算為一，未觸上限）。

---

## §2 途中發現（記錄，本輪刻意不動工）

### F1 — Stop 稽核器把「hook 的 non-blocking 提醒」誤判為「本平台載具失敗」

**當回合實測**：本輪收尾窗口的 Stop hook additional context 逐字報「本平台自己那條 hook
載具失敗（八筆）⇒ `.claude/hooks/block_destructive_git.py` 這一次**沒有跑**（CC 只記一行
ERROR 就放行，fail-open）」，而它引為證據的每一行內容本身是：

```
Failed with non-blocking status code: [block_destructive_git] 提醒：
tools/tests/test_adr_xplat001_c1c2_lock.py 是治理檔（PRD §15.5 紅線 10 保護面）。
有人值守 ⇒ 只出聲不阻斷；無人值守回合對它是唯讀的，改完請跑對應守衛測試。
```

**矛盾**：那段中文提醒是 `block_destructive_git.py` **自己印的**——它印得出來就證明它跑了。
判準把「hook 回 non-blocking status code 並附訊息」與「載具解析失敗、hook 根本沒跑」歸成
同一桶，而這兩者的處置完全相反。

**為什麼這個方向的假陽性特別貴**：根 CLAUDE.md〈hook 載具〉節逐字寫「exec form 載具解析
不到時 Claude Code fail-open ⇒ 全部守衛靜默失效，表徵與『修好了』完全相同」，因此這道稽核
是那個不對稱風險的唯一觀測者。它現在會對**正常的出聲式提醒**每次都喊狼來了 ⇒ 真的載具死掉
那天，讀者已經學會忽略它。

**候選修法**（未動工、未複驗判準原始碼、未量假陽性母體）：判準改以「stderr 有無該 hook
自己的識別前綴」分流——有前綴＝hook 跑了（不論 exit code），無前綴才是載具失敗。

**發現情境**：收尾單人窗口的守衛線重釘儀式（合法動作，改的是自己持有的治理檔）。

**尚未做**：未入帳本。入帳與否留給下一個結案窗口判斷——本輪是精準修復輪，紀律是
「找到新問題先記著，不當場開新戰場」。

---

## §3 誠實劃界

- 本輪三筆修復與本次搬遷**皆未經四方定點複審**，依成熟度判準 M3「作者自證不計分」屬自證。
- 搬遷面另有可用額度未取（兩支最肥的檔因是別的機械物的逐字比對面而整檔排除，理由見
  `CrossPlatform_R122_Guard_Prose_Migration.md` 的 rejected 節）。
