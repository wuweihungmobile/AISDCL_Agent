"""喚醒鏈 v2.1.13 G3＋G4——配額內接力狀態機（§3(c)）＋哨兵 fire 後重掛（§3(d)）。

施工圖＝docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md §3(c)/§3(d)（v2.1.13，
2026-08-31 落款）。立案：`_resume_tick()` 的 resume 分支此前是 fire-once——續跑一次即止，
剩餘工作明明有額度也不繼續（G3）；且收窗刪排程但**不清 arm stamp、不重掛哨兵**，喚醒鏈
就此斷線、要等人開下一個 session 才會被 SessionStart 清閂重評（G4）。

WHY 住這裡而不是 `tools/session_resume_planner.py`：`guardrail_cli` 餘裕動工當下實測
750/750（現查 `python AutoClaude/tools/check_loc_budget.py --json`），施工圖 §5 判例
「胖身體一律下 lib、planner 只留最小接線」——同 `resume_route.py`（G1/G2）沿用的判例。

依賴方向：本檔對 `session_resume_planner` 走**函式內 lazy import**（`_planner()`），
而不是模組層 `import`——planner 模組層已 `import relay_machine`，模組層互相 import
會成環；理由與手法逐字同 `tools/lib/sentinel_lifecycle.py::_planner_module()`。

判定序＝③→④→②→①（自上而下短路，施工圖 §3(c) 表列）：
  ③ 任務書仍有未完項？—— `resolve()` 讀 handback 交接檔（G2 批 (b) 落地的同一份文件）
     的「## 下一步指令」節；`handback_verdict != written`（含 REFUSE／rc=None／
     resume_failed 三種失敗態）保守回 `True`（無正面完工證據，不得判 DONE——量不到
     ≠ 量到零同一條紀律），`written` 時看該節是否非空（模型須**顯式清空**才算完工，
     判準收在「有沒有文字」這個值域，不猜文字語意）。
  ④ 連續零新進度是否已達 `AUTOSDD_RELAY_NO_PROGRESS_LIMIT` 窗？—— 新進度＝
     `handback_verdict=written ∧ files_changed>0`；`files_changed` 為 spawn 前後兩次
     `git status --porcelain` 快照的差集（`git_paths` SSOT，quotepath-safe）。
  ② `--pace` 現查 band 是否 ∈ {free, notice}？—— 走 `quota_gate.read_quota()` ＋
     `quota_policy.decide()` 同一份純讀取面（零 spawn 子行程，同 `quota_escalation.
     _idle_prepare_watch()` 既有手法）；`unmeasured` 視同不合格（保守向收斂）。
  ① `relay_seq < AUTOSDD_RELAY_MAX_SPAWNS`？

四個判準全真 ⇒ RELAY_NEXT（重排下一窗）；否則依判定序落 DONE／NO_PROGRESS_STOP／
QUOTA_STOP／RELAY_EXHAUSTED 四個停止次態之一——**除「RELAY_NEXT 且排程成功」外，全部
重掛哨兵**（G4 判準1，含失敗路徑；RELAY_NEXT 排程失敗＝喚醒鏈斷線，視同停止次態同樣
重掛，SD-4）：`_rearm_after_stop()` 沿用既有 PATROL_HANDBACK 手法
（`session_resume_planner._resume_tick` 內同型邏輯的第二個呼叫點，本檔不重寫第二份）。
重掛失敗 ⇒ 清 arm latch（`sentinel_lifecycle_arm.clear_arm_latch`）＋loud——讓下一次
SessionStart 的武裝評估重新來過，不留一個「宣稱已重掛」的假閂鎖（R112 §3-5 同型）。round-label-ok
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import git_paths
import quota_gate
import quota_policy

#: 每 reset 視窗 spawn 上限；出廠 2（施工圖 §3(c) 常數表）。
RELAY_MAX_SPAWNS_ENV = "AUTOSDD_RELAY_MAX_SPAWNS"
RELAY_MAX_SPAWNS_DEFAULT = 2
#: 連續無新進度停止閾；出廠 1＝對齊 R112「零推進即停」語意。round-label-ok
RELAY_NO_PROGRESS_LIMIT_ENV = "AUTOSDD_RELAY_NO_PROGRESS_LIMIT"
RELAY_NO_PROGRESS_LIMIT_DEFAULT = 1

#: 次態字面（狀態機表，施工圖 §3(c)）。
STATE_RELAY_NEXT = "RELAY_NEXT"
STATE_DONE = "DONE"
STATE_NO_PROGRESS_STOP = "NO_PROGRESS_STOP"
STATE_QUOTA_STOP = "QUOTA_STOP"
STATE_RELAY_EXHAUSTED = "RELAY_EXHAUSTED"

#: band 判準②：`--pace` 現查 band 必須落在這兩帶才續燒（unmeasured／收緊皆不合格）。
_BAND_OK = frozenset({quota_policy.BAND_FREE, quota_policy.BAND_NOTICE})

#: handback 交接檔（§3(b)）「還有未完項」的判準面：該節非空即視為未完項，模型須
#: 顯式清空才算完工。與 `resume_route.HANDBACK_MARKERS` 同一份文件，不同一個判準
#: （後者驗四節齊備、本檔只看其中一節的內容）。
_NEXT_STEP_HEADING = "## 下一步指令"

#: 停止次態 → 事件名／why／叫人與否／人話理由（施工圖 §4 V-c1：每個次態唯一一組）。
_STOP_EVENT = {STATE_DONE: "relay_done", STATE_NO_PROGRESS_STOP: "relay_stopped",
              STATE_QUOTA_STOP: "relay_stopped", STATE_RELAY_EXHAUSTED: "relay_stopped"}
_STOP_WHY = {STATE_NO_PROGRESS_STOP: "no_progress", STATE_QUOTA_STOP: "band",
            STATE_RELAY_EXHAUSTED: "cap"}
_STOP_REASON = {
    STATE_DONE: "接力工作已完成（handback「## 下一步指令」節已清空，判定無未完項）",
    STATE_NO_PROGRESS_STOP: "接力已連續無新進度達停止門檻，停止自動續跑",
    STATE_QUOTA_STOP: "額度帶已收緊（非 free/notice），交回哨兵巡邏",
    STATE_RELAY_EXHAUSTED: "接力已達每視窗 spawn 上限，停止自動續跑，留任務書給人",
}
#: 恰兩個停止次態需要「叫人」（loud）：無新進度（故障訊號）與達 spawn 上限（人工決策）。
#: DONE（正常結束）與 QUOTA_STOP（交回既有哨兵巡邏）不吵——同 `_resume_tick` 既有
#: `disarm` 分支 `loud=False` 仍呼叫 `escalation.alert()` 收殘骸的紀律。
_LOUD_STATES = frozenset({STATE_NO_PROGRESS_STOP, STATE_RELAY_EXHAUSTED})


def _int_env(name: str, default: int) -> int:
    """壞值／缺席一律退回出廠預設（同 planner `_transcript_cap()` 既有紀律，下界 1）。"""
    raw = str(os.environ.get(name) or "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return value if value >= 1 else default


def max_spawns() -> int:
    return _int_env(RELAY_MAX_SPAWNS_ENV, RELAY_MAX_SPAWNS_DEFAULT)


def no_progress_limit() -> int:
    return _int_env(RELAY_NO_PROGRESS_LIMIT_ENV, RELAY_NO_PROGRESS_LIMIT_DEFAULT)


def current_band(now: datetime) -> str:
    """判準②現查：與 `--pace` 同一份純讀取面（零 spawn 子行程）。

    刻意不呼叫 `quota_gate.pace_report()`——那支還做燃燒率記錄／穩定化／寫檔契約三件
    副作用，本檔只要 band。手法同 `quota_escalation._idle_prepare_watch()` 既有呼叫：
    `read_quota()` 只讀快取檔（零網路／零 subprocess），`decide()` 是純函式。
    """
    policy, _problems = quota_policy.load_policy(quota_gate.policy_env())
    return quota_policy.decide(quota_gate.read_quota(now), now, policy).band


def band_ok(band: str) -> bool:
    return band in _BAND_OK


def git_status_snapshot(repo_root: Path) -> frozenset[str] | None:
    """`git status --porcelain` 一次快照（quotepath-safe，SSOT＝`git_paths`）。

    量不到（逾時／git 不可達／非零 rc）回 `None`——呼叫端（`files_changed()`）把它當
    保守值處理：量不到 ≠ 有改動，不得誤判成本窗有進度。
    """
    try:
        proc = git_paths.run(repo_root, "status", "--porcelain")
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return frozenset(line for line in proc.stdout.splitlines() if line)


def files_changed(before: frozenset[str] | None, after: frozenset[str] | None) -> int:
    """兩次快照的差集筆數（判準④「新進度」的取數）；任一快照量不到 ⇒ 0。

    差集而非計數变化：窗前既有髒污（〈可重啟點四條件〉的 `git stash create` 保全常態）
    留在 `before` 集合裡不會被算進本窗進度；窗內新增／狀態改變（如某檔從未追蹤變已
    暫存）的那一行在 `after` 集合裡是新字面，會被算進差集。
    """
    if before is None or after is None:
        return 0
    return len(after - before)


def snapshot_log_fields(snapshot: frozenset[str] | None) -> dict:
    """R115 修復 F3：把一次 porcelain 快照壓成稽核痕跡可負擔欄位（施工圖§3(c)判準④ round-label-ok
    「前快照落 resume log 痕跡」，此前只活在 `_run_resume()` 的行程記憶體，差集數字
    事後不可稽核）。回行數＋內容雜湊，**不灌 porcelain 全文**進 log——全文可能含使用者
    路徑／檔名且無上限成長，同誠實劃界第 8 條「量不到 ≠ 有改動」的保守紀律：`snapshot`
    為 `None`（量不到）時兩鍵誠實回 `None`，不得偽裝成「0 筆改動」。
    """
    if snapshot is None:
        return {"lines": None, "digest": None}
    return {"lines": len(snapshot),
            "digest": hashlib.sha256("\n".join(sorted(snapshot)).encode("utf-8")).hexdigest()}


def _section_text(text: str, heading: str) -> str:
    """取 `heading` 之後、下一個 `## ` 之前的內容（不含標題行；找不到標題回空字串）。

    與 `sentinel_lifecycle._section()` 同一種切法（同一份 handback 文件的段落格式），
    本檔獨立一份是因為那一支是私有名稱且射程鎖在 handback 四個標記的摘要輸出，不宜
    跨模組借用私有名稱做另一種用途；此處是通用 markdown 段落擷取，非核心業務判準。
    """
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == heading]
    if not starts:
        return ""
    start = starts[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")),
               len(lines))
    return "\n".join(lines[start:end]).strip()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def plan_has_remaining_work(handback_verdict: str, handback_text: str) -> bool:
    """判準③：`handback_verdict != "written"`（含三種失敗態）保守回 `True`；
    `"written"` 時看 handback 的「## 下一步指令」節是否非空。
    """
    if handback_verdict != "written":
        return True
    return bool(_section_text(handback_text, _NEXT_STEP_HEADING))


def made_progress(handback_verdict: str, files_changed_count: int) -> bool:
    """判準④用：本窗「新進度」＝ handback 寫成 ∧ 真有檔案改動。"""
    return handback_verdict == "written" and files_changed_count > 0


def advance_no_progress_streak(streak: int, progressed: bool) -> int:
    """新 streak：本窗有進度歸零，否則 +1。"""
    return 0 if progressed else streak + 1


def no_progress_ok(streak: int, limit: int) -> bool:
    """判準④：streak 尚未達到連續零進度的停止門檻。"""
    return streak < limit


def next_state(*, has_remaining: bool, streak_ok: bool, band_is_ok: bool,
               under_cap: bool) -> str:
    """接力狀態機的純判定（施工圖 §3(c) 表；判定序 ③→④→②→①，自上而下短路）。

    十六格真值表的唯一入口：僅全真格回 `RELAY_NEXT`，其餘依此序落四個停止次態之一。
    """
    if not has_remaining:
        return STATE_DONE
    if not streak_ok:
        return STATE_NO_PROGRESS_STOP
    if not band_is_ok:
        return STATE_QUOTA_STOP
    if not under_cap:
        return STATE_RELAY_EXHAUSTED
    return STATE_RELAY_NEXT


def resolve(state: dict, band: str, *, max_spawns: int, no_progress_limit: int) -> dict:
    """把 `state` 目前已知的本窗欄位（`handback_verdict`／`handback_path`／
    `files_changed`／`relay_seq`／`relay_no_progress_streak`）換算成四個判準輸入，
    跑狀態機，回**要合併回 state 的欄位**（含 `next_state`，呼叫端 `pop()` 取用）。

    純函式（不寫檔、不呼叫排程器）：副作用（重排下一窗／重掛哨兵／寫痕跡）留給
    `settle_window()`，好讓判定本身可以在沒有 planner／schtasks 的情況下獨立測試。
    """
    verdict = str(state.get("handback_verdict") or "missing")
    hb_path = str(state.get("handback_path") or "")
    hb_text = _read_text(Path(hb_path)) if hb_path and verdict == "written" else ""
    remaining = plan_has_remaining_work(verdict, hb_text)
    changed = int(state.get("files_changed") or 0)
    progressed = made_progress(verdict, changed)
    seq = int(state.get("relay_seq") or 0)
    streak = advance_no_progress_streak(int(state.get("relay_no_progress_streak") or 0),
                                       progressed)
    outcome = next_state(has_remaining=remaining,
                        streak_ok=no_progress_ok(streak, no_progress_limit),
                        band_is_ok=band_ok(band), under_cap=seq < max_spawns)
    return {"next_state": outcome, "relay_no_progress_streak": streak, "files_changed": changed,
            "relay_seq": seq + 1 if outcome == STATE_RELAY_NEXT else seq}


def apply_reset_at(state: dict, new_reset_at: str) -> None:
    """R115 修復 F4：寫入新 `reset_at` 前先比對舊值（施工圖 §3(c)「計數持久化」—— round-label-ok
    「歸零邊界＝觀測到 `reset_at` 變更」此前只是散文，`_resume_tick` rearm 分支與
    `_sentinel_tick` arm_reset 分支各自就地改寫 `reset_at` 卻從未歸零 `relay_seq`／
    `relay_no_progress_streak`）。真的變更 ⇒ 兩個計數歸零，不得沿用上一個額度視窗的
    接力計數；未變更（如同一撞線事件的重複巡邏、或 transient 退避不動 reset_at）⇒
    保留既有計數。兩個呼叫站點共用同一份判準，不留第二個家。
    """
    if str(state.get("reset_at") or "") != str(new_reset_at or ""):
        state["relay_seq"] = 0
        state["relay_no_progress_streak"] = 0
    state["reset_at"] = new_reset_at


def _planner():
    """lazy import `session_resume_planner`（同 `sentinel_lifecycle._planner_module()`
    既有理由：planner 模組層已 `import relay_machine`，模組層互相 import 會成環）。
    """
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import session_resume_planner as planner  # noqa: PLC0415 — 見 docstring（成環）

    return planner


def _rearm_after_stop(planner, args, state: dict, plan: Path, log: Path) -> int:
    """G4 判準1（fire 後重掛）：四個停止次態一律重掛哨兵，含失敗路徑（rc=None／
    resume_failed／REFUSE 依 §3(c) 失敗態歸屬同樣走到這裡）。

    命名歸位＋逐字稿解析沿用既有 PATROL_HANDBACK 手法（`_resume_tick` 內同型邏輯的
    第二個呼叫點）；重掛失敗 ⇒ 清 arm latch＋loud，讓下一次 SessionStart 的武裝評估
    重新來過，不留一個「宣稱已重掛」的假閂鎖。
    """
    raw = str(state.get("transcript") or "")
    seen = Path(raw) if raw else planner.resolve_transcript(state.get("session_id") or "")
    args.task_name = planner.DEFAULT_TASK_NAME
    rc = planner._arm_sentinel(args, seen, plan) if seen is not None else 1
    if rc != 0:
        import sentinel_lifecycle_arm  # noqa: PLC0415 — 只在失敗路徑才需要

        sentinel_lifecycle_arm.clear_arm_latch(str(state.get("session_id") or ""))
        planner.escalation.alert(
            f"重掛哨兵失敗（rc={rc}）：喚醒鏈斷線，已清 arm latch 供下次 SessionStart 重新評估",
            state, loud=True, plan=plan)
    return rc


def settle_window(args, state: dict, plan: Path, log: Path, resume_rc: int | None) -> int:
    """v2.1.13 G3+G4：`_resume_tick()` resume 分支收尾——rc 落定＋handback 後檢之後，
    接力狀態機判定 → `RELAY_NEXT` 重排下一窗，或四個停止次態之一重掛哨兵。

    planner 端只有一個呼叫點（見 `_resume_tick` 「action == resume」分支），且刻意
    把整段流程收在這裡而不留在 planner——`guardrail_cli` 餘裕為 0，胖身體只能在這裡。

    🔴 `resume_rc`＝`_run_resume()` 的原始 rc，**停止次態的回傳值必須沿用它**
    （`resume_rc if resume_rc is not None else 1`，逐字同修改前 `_resume_tick` 共用尾段
    的既有契約，回歸鎖＝`ResumeTickWritesStateOnlyAfterConfirmingTest`）——重掛哨兵是
    G4 的旁支自癒動作，它自己的 rc 只進痕跡（`relay_rearmed`／`relay_rearm_failed`），
    不得覆蓋掉「claude 這次到底有沒有真的跑完」這個既有語意。`RELAY_NEXT` 是本批新增
    的次態、沒有既有契約要沿用，回傳排程 rc（同 `_resume_tick` 既有 `rearm`／
    `patrol_handback` 兩支的既有慣例：排出去的動作用它自己的 rc）。

    SD-4：`RELAY_NEXT` 排程失敗（`_register_and_record` rc≠0）**視同停止次態**——
    不記 `relay_spawned`（那是含憑證的成功痕跡）、改記 `relay_spawn_failed`＋loud、
    best-effort 拆自己的 -Once 排程、走 `_rearm_after_stop()`；回傳仍沿用排程 rc
    （rearm rc 不得覆蓋，同上段契約）。`relay_seq` 不回退：fail-safe 方向，失敗窗
    燒掉一格只會讓接力更早停。

    SD-8：主體自 `now = ...` 起整段 try/except——本函式由 pythonw 無 console 行程
    執行（stderr=None），未捕捉例外＝行程靜默消失：-Once 排程沒拆、哨兵沒重掛、
    arm latch 沒清、零痕跡。`_planner()` 留在 try 外：它壞掉時 handler 內也沒有
    任何可用的處置手段。災難 handler 的結構理由見 except 內註解。
    """
    planner = _planner()
    try:
        now = datetime.now().astimezone()
        band = current_band(now)
        outcome = resolve(state, band, max_spawns=max_spawns(),
                          no_progress_limit=no_progress_limit())
        next_st = outcome.pop("next_state")
        state.update(outcome)
        if next_st == STATE_RELAY_NEXT:
            state.update(planner._cleared_credentials())
            at = now + timedelta(seconds=planner.RESET_SKEW_SECONDS)
            rc, moment = planner._register_and_record(plan, state, at, planner.RESUME_TICK)
            if rc == 0:
                planner.append_log(log, "relay_spawned", seq=state["relay_seq"], band=band,
                                   files_changed_prev=int(state.get("files_changed") or 0),
                                   credential=moment)
                return rc
            # SD-4：排程失敗＝喚醒鏈斷線，視同停止次態——不得留下含憑證的成功痕跡。
            planner.append_log(log, "relay_spawn_failed", seq=state["relay_seq"], band=band,
                               rc=rc, credential=moment)
            planner.escalation.alert(
                f"接力排程失敗（rc={rc}）：喚醒鏈斷線，拆 -Once 排程並重掛哨兵",
                state, loud=True, plan=plan)
            unregister_rc = planner._schtasks_remove(state["task_name"])
            rearm_rc = _rearm_after_stop(planner, args, state, plan, log)
            planner.append_log(log,
                               "relay_rearmed" if rearm_rc == 0 else "relay_rearm_failed",
                               rc=rearm_rc, unregister_rc=unregister_rc, next_state=next_st)
            return rc  # 沿用排程 rc；rearm rc 不得覆蓋（docstring 既有契約）
        told = planner.escalation.alert(_STOP_REASON[next_st], state,
                                        loud=next_st in _LOUD_STATES, plan=plan)
        planner.append_log(log, _STOP_EVENT[next_st], why=_STOP_WHY.get(next_st, ""),
                           band=band, **told)
        state.update(planner._cleared_credentials())
        planner.write_relay(plan, state)
        unregister_rc = planner._schtasks_remove(state["task_name"])
        rearm_rc = _rearm_after_stop(planner, args, state, plan, log)
        planner.append_log(log, "relay_rearmed" if rearm_rc == 0 else "relay_rearm_failed",
                           rc=rearm_rc, unregister_rc=unregister_rc, next_state=next_st)
        return resume_rc if resume_rc is not None else 1
    except Exception as exc:
        # SD-8 兜底：pythonw 行程 stderr=None，例外炸穿＝靜默消失。兩個 disposal
        # 呼叫裸放在最前——結構鎖 `test_the_settle_window_delegate_really_disposes`
        # 的支配演算法對 Try 給 handler 的 pre-seen 是空集，disposal 被窄 try 包住
        # 時它看不見（實測紅）；alert／落痕跡殿後、各自窄 try（alert 有 notify_rc=-2
        # 前科，二次例外不得讓回傳契約跑不到——disposal 已在其前跑完）。
        planner._schtasks_remove(str(state.get("task_name") or ""))
        _rearm_after_stop(planner, args, state, plan, log)
        try:
            planner.escalation.alert(
                f"settle_window 崩潰（{exc!r}）：已拆 -Once 排程並重掛哨兵",
                state, loud=True, plan=plan)
        except Exception:
            pass  # 二次例外不得擋住落痕跡與回傳（見上方 WHY）
        try:
            planner.append_log(log, "relay_settle_crashed", error=repr(exc))
        except Exception:
            pass  # 同上：回傳契約優先
        return resume_rc if resume_rc is not None else 1
