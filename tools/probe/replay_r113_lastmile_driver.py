#!/usr/bin/env python3
"""重演 2026-08-30 撞線事件，驗喚醒鏈最後一哩四缺口（G1~G4）全閉合。

施工圖：`docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md` §4 V-e2e 列。
本檔即 V-e2e 的**唯一入口**（PRD 草案名 `replay_r113_lastmile.sh` 的實交付形態：
R115 round-label-ok 裁量改為純 Python——初版曾附 .sh 薄入口，但單邊 .sh 會撞
ADR-XPLAT-002 §4.2 的 AC/UEP 張力（例外面只出不進），而薄入口做的只有「找
python、跑本檔」，Python 直跑零豁免需求且雙平台同一條指令），假後端注入全部
在這裡以 `unittest.mock` 完成。

四缺口對照（見 PRD §1 缺口表 ／ §3 設計）：
  G1 無頭窗口權限姿態（§3(a)）——`resume_route.resume_argv/fresh_argv` 是否真的
     帶 `--permission-mode acceptEdits --settings <檔>`；`preflight_problem()`
     缺席時是否真的拒 spawn。
  G2 交接可見性（§3(b)）——`resume_route.handback_verdict()` 三值判準；
     `handback_postcheck()` 在交接不可見時是否真的落痕跡＋loud 告警。
  G3 配額內自循環（§3(c)）——`relay_machine` 狀態機：有進度就繼續（RELAY_NEXT）、
     達 spawn 上限停（RELAY_EXHAUSTED）、連續零進度停（NO_PROGRESS_STOP）、
     band 收緊交回哨兵（QUOTA_STOP）。
  G4 哨兵自癒（§3(d) 判準1）——四個停止次態（含失敗路徑）是否都重掛哨兵；
     RELAY_NEXT 是否正確地「不」重掛（下一窗自己接手）。

🔴 硬約束（PRD §4 V-e2e 逐字，本檔以下列手法兌現）：
  · 零真實額度消耗、零真 spawn `claude`——`probe_quota()`／`_run_resume()` 兩個
    唯一會呼叫 `claude` 二進位的站點，全部以 `unittest.mock.patch.object` 換成
    假結果；唯一一支「不 mock `_run_resume()` 本體」的場景改在**更底層**的
    `subprocess.run` 邊界注入假子行程（同 `RunResumeWritesHandbackPathIntoStateTest`
    既有回歸鎖的紀律：只騙 OS 邊界，不騙業務邏輯），一樣沒有任何 `claude` 二進位
    被啟動。
  · 零真 schtasks／launchd——排程原語只有三個進場站點
    （`_register_and_record`／`_arm_sentinel`／`_schtasks_remove`），本檔全數
    `patch.object` 掉，`schedule_backend.select()` 背後的 `SchtasksBackend`／
    `LaunchdBackend` 一次都不會被呼叫到。工作名一律用本檔自建的合成字面
    （`T-replay-*`），不沿用任何曾經真實掛過的工作名。
  · `--pace` band 注入——沒有另外 shell 出去跑 `--pace` CLI，而是直接注入
    `--pace` 背後那個唯一的判讀函式 `relay_machine.current_band()`（G3 判準②
    的真正讀點；`RelaySettleWindowTest` 既有回歸鎖同款手法）。這裡誠實劃界：
    注入的是「`--pace` 會讀到的值」，不是「跑一次 `--pace` 子行程」。

CI-skip 家族（同 `tools/check_hooks_liveness.py` 檔頭〈開發機出聲層〉）：本檔刻意
不進 CI——它驗的是「本機 mock 注入是否把 G1~G4 四個判準真的串起來」，屬一次性
（或人工重跑）取證工具，不是雲端契約守門；且駕駛器對 `session_resume_planner`
的 sys.path 佈線與本機 Python 環境相依，容器面貌與本機不同不具備同等鑑別力。

用法：
    python tools/probe/replay_r113_lastmile_driver.py
    python tools/probe/replay_r113_lastmile_driver.py --break handback-marker
        （自我證偽：刻意弄壞一個場景的輸入，驗證本腳本真的有鑑別力——
         PRD §4 V-e2e 驗收項 3。正常演練不要帶這個旗標。）

Exit：0＝全部場景通過（G1~G4 四缺口重演成功）；1＝至少一個場景斷言失敗。
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import subprocess as _real_subprocess
import sys
import tempfile
import unittest.mock
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools"))

# 🔴 模組身分：本檔刻意只在這裡插一次 `tools/` 到 sys.path，其餘 `tools/lib/*`
# （`context_budget_guard`／`quota_policy`／`relay_machine`／`resume_route`）都是
# 靠 `import session_resume_planner` 觸發的既有 sys.path 佈線（該檔本身會插入
# `tools/lib`／`.claude/hooks`）取用——同一個行程內只有一份模組物件，
# `unittest.mock.patch.object` 才會打中被生產路徑實際引用的那一份（同檔既有
# `ModuleIdentityIsSingleTest` 那條判例）。
import session_resume_planner as planner  # noqa: E402

import context_budget_guard as guard  # noqa: E402
import quota_policy  # noqa: E402
import relay_machine  # noqa: E402
import resume_route  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  — Windows 非 UTF-8 終端印中文防崩潰


class _FakeSubprocessModule:
    """`session_resume_planner.subprocess` 的替身——只換掉 `.run`，其餘（例外類別）
    原封不動指回真模組。刻意**不**patch 全域 `subprocess.run`：那會連
    `tools/lib/git_paths.py` 自己 `import subprocess` 的那一份也一起换掉，波及
    `relay_machine.git_status_snapshot()` 的真 `git status --porcelain`
    （唯讀、非本檔要騙的對象——見檔頭〈硬約束〉只騙 `claude` 二進位與排程器）。
    """

    SubprocessError = _real_subprocess.SubprocessError
    CompletedProcess = _real_subprocess.CompletedProcess
    TimeoutExpired = _real_subprocess.TimeoutExpired

    def __init__(self, run_fn):
        self.run = run_fn


# ═══════════════════════════════════════════════════════════════════════════
# 共用建材：合成一份最小可通過 `relay_problems()` 體檢的續航狀態塊。
# ═══════════════════════════════════════════════════════════════════════════
def _handback_text(next_step: str) -> str:
    return ("## 做了什麼\n演練（合成）\n\n## 驗了什麼\nrc=0（合成）\n\n"
            "## 卡在哪\n無\n\n" + f"## 下一步指令\n{next_step}\n")


def _initial_state(plan: Path, task_name: str, session_id: str, **overrides: object) -> dict:
    state = {
        "schema": planner.RELAY_SCHEMA, "session_id": session_id, "plan_path": str(plan),
        "state": "armed", "kind": guard.LIMIT_SESSION,
        # reset_at／next_run_time 皆為合成憑證：僅供 `relay_problems()` 的既有體檢
        # （armed 必須有非空排程憑證、reset_source 必須是觀測值）通過，不是真排程
        # 器回報值——本檔從不呼叫任何真排程器（見檔頭〈硬約束〉）。
        "reset_at": "2026-08-31T00:10:00+08:00",
        "reset_source": "transcript-verbatim", "attempts": 0, "max_attempts": 5,
        "allow_resume": True, "task_name": task_name,
        "next_run_time": "2026/08/31 00:12:00",
        "transcript": str(plan.parent / f"{session_id}.jsonl"),
        "relay_seq": 0, "relay_no_progress_streak": 0,
    }
    state.update(overrides)
    return state


def _build_plan(tmp: Path, task_name: str, session_id: str, **state_overrides: object) -> Path:
    plan = tmp / "plan.md"
    state = _initial_state(plan, task_name, session_id, **state_overrides)
    plan.write_text("# 可重啟點任務書（R113 最後一哩演練，合成，非真實事故）\n\n"
                    + planner.render_relay(state), encoding="utf-8", newline="\n")
    return plan


def _run_resume_tick(plan: Path, task_name: str, *, run_resume_result: dict, band: str,
                     max_spawns: int, no_progress_limit: int) -> tuple:
    """重演一次 `_resume_tick()`：合成撞線探測（假 reset 已回來）→ 假 spawn（依劇本
    回填 state，代表 `--pace` band 已注入之後續跑那一跳的結果）→ 真正的 G3 狀態機
    判定 → G4 重掛哨兵。回 `(rc, written_state, events, alert_calls, arm_calls,
    registered)`。

    `_register_and_record` 的假身仍呼叫真正的 `planner.write_relay()`——RELAY_NEXT
    分支本來就是靠它把 `relay_seq` 落盤，多視窗串接（同一個 `plan` 檔連續呼叫本函式
    好幾次）能不能看到序號真的往前走，全靠這一行是不是真寫檔。
    """
    args = planner.build_parser().parse_args(
        ["--resume-tick", "--plan", str(plan), "--task-name", task_name])
    events: list[dict] = []
    alert_calls: list[dict] = []
    arm_calls: list = []
    registered: list = []

    def _fake_run_resume(_a, st, _lg):
        st.update(run_resume_result)
        return run_resume_result.get("_rc", 0)

    def _fake_alert(reason, _st, *, loud=True, plan=None, **_kw):  # noqa: ARG001
        alert_calls.append({"reason": reason, "loud": loud})
        return {"note_written": loud}

    def _fake_append_log(_log, event, **fields):
        events.append({"event": event, **fields})

    def _fake_register(pl, st, _at, tick):
        registered.append({"relay_seq": st.get("relay_seq"), "tick": tick})
        planner.write_relay(pl, st)
        return 0, "已回讀（演練假憑證，非真排程）"

    def _fake_arm_sentinel(_a, transcript, _pl):
        arm_calls.append(str(transcript))
        return 0

    with contextlib.ExitStack() as stack:
        stack.enter_context(unittest.mock.patch.object(
            planner, "probe_quota", lambda *_a, **_k: {
                "open": True, "kind": guard.LIMIT_NONE, "rc": 0,
                "text": "ok（假探針：模擬 reset 已發生，零真實 API 呼叫）"}))
        stack.enter_context(unittest.mock.patch.object(
            planner, "_run_resume", side_effect=_fake_run_resume))
        stack.enter_context(unittest.mock.patch.object(
            planner, "append_log", side_effect=_fake_append_log))
        stack.enter_context(unittest.mock.patch.object(
            planner.escalation, "alert", side_effect=_fake_alert))
        stack.enter_context(unittest.mock.patch.object(
            planner, "_schtasks_remove", side_effect=lambda _t: 0))
        stack.enter_context(unittest.mock.patch.object(
            planner, "_arm_sentinel", side_effect=_fake_arm_sentinel))
        stack.enter_context(unittest.mock.patch.object(
            planner, "_register_and_record", side_effect=_fake_register))
        stack.enter_context(unittest.mock.patch.object(
            relay_machine, "current_band", lambda *_a, **_k: band))
        stack.enter_context(unittest.mock.patch.object(
            relay_machine, "max_spawns", lambda: max_spawns))
        stack.enter_context(unittest.mock.patch.object(
            relay_machine, "no_progress_limit", lambda: no_progress_limit))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        rc = planner._resume_tick(args)
    written = planner.parse_relay(plan.read_text(encoding="utf-8"))
    return rc, written, events, alert_calls, arm_calls, registered


@contextlib.contextmanager
def _isolated_handback_dir():
    """暫時把 `AUTOSDD_HANDBACK_DIR` 指到本次演練自己的 tmp 目錄，演練結束歸還原值
    ——防止本腳本任何一步意外碰到使用者真正的 `~/.autosdd/handback`（PRD §3(b)1
    的逃生口本來就是為了「單元測試／沙箱不得在家目錄留下移動零件」而設）。
    """
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-hb-"))
    old = os.environ.get("AUTOSDD_HANDBACK_DIR")
    os.environ["AUTOSDD_HANDBACK_DIR"] = str(tmp)
    try:
        yield tmp
    finally:
        if old is None:
            os.environ.pop("AUTOSDD_HANDBACK_DIR", None)
        else:
            os.environ["AUTOSDD_HANDBACK_DIR"] = old
        shutil.rmtree(tmp, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════
# G1 —— 無頭窗口權限姿態（§3(a)）
# ═══════════════════════════════════════════════════════════════════════════
def scenario_g1_permission_argv() -> None:
    add_dir = Path(tempfile.gettempdir())
    for argv, label in ((resume_route.resume_argv("claude", "sid-g1", "PROMPT", add_dir),
                        "resume_argv"),
                       (resume_route.fresh_argv("claude", "PROMPT", add_dir), "fresh_argv")):
        assert "--permission-mode" in argv, f"{label} 缺 --permission-mode：{argv}"
        idx = argv.index("--permission-mode")
        assert argv[idx + 1] == "acceptEdits", f"{label} permission-mode 非 acceptEdits：{argv}"
        assert "--settings" in argv, f"{label} 缺 --settings：{argv}"
        prompt_idx = argv.index("PROMPT")
        add_dir_idx = argv.index("--add-dir")
        assert prompt_idx < add_dir_idx, (
            f"{label}：prompt 必須排在 --add-dir 之前（R80 P0 沿革，變長旗標會吃掉 "
            f"排在它後面的 prompt）：{argv}")
    assert "-r" not in resume_route.fresh_argv("claude", "PROMPT", add_dir), (
        "FRESH 路徑不得帶 -r（降級語意：不得假裝有可續的 session）")


def scenario_g1_preflight_missing_settings_rejects_spawn() -> None:
    missing = Path(tempfile.gettempdir()) / "replay-r113-does-not-exist" / "settings.unattended.json"  # noqa: E501
    problem = resume_route.preflight_problem(settings=missing)
    assert problem is not None, (
        "unattended settings 檔缺席時 preflight_problem() 必須拒絕 spawn"
        "（2026-08-30 G1 原事故形態：無頭窗口收不了尾）")


def scenario_g1_preflight_real_settings_passes() -> None:
    with _isolated_handback_dir():
        problem = resume_route.preflight_problem()  # 用真正的 .claude/settings.unattended.json
    assert problem is None, f"真實 settings 檔應通過 A-PRE 預檢，卻拒絕：{problem}"


# ═══════════════════════════════════════════════════════════════════════════
# G2 —— 交接可見性（§3(b)）
# ═══════════════════════════════════════════════════════════════════════════
def scenario_g2_handback_verdict(break_mode: str | None) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-g2-"))
    try:
        spawn_at = datetime.now().timestamp()
        written_text = _handback_text("還有第 4 步")
        if break_mode == "handback-marker":
            # 🔴 自我證偽開關（PRD §4 V-e2e 驗收項 3）：刻意拿掉「## 下一步指令」
            # marker，模擬模型沒寫全四節——下面的斷言仍要求 verdict == "written"，
            # 於是這一格必須紅，用來證明本腳本不是「永遠 rc=0」的空殼。
            written_text = written_text.replace("## 下一步指令\n還有第 4 步\n", "")
        hb = tmp / "sid-g2.md"
        hb.write_text(written_text, encoding="utf-8", newline="\n")
        verdict = resume_route.handback_verdict(str(hb), spawn_at)
        assert verdict == "written", f"完整四節 handback 應判 written，實得 {verdict!r}"

        verdict_missing = resume_route.handback_verdict(str(tmp / "not-there.md"), spawn_at)
        assert verdict_missing == "missing", f"檔不存在應判 missing，實得 {verdict_missing!r}"

        stale_path = tmp / "sid-stale.md"
        stale_path.write_text(_handback_text("舊內容"), encoding="utf-8", newline="\n")
        future_spawn_at = spawn_at + 3600  # spawn 發生在寫檔「之後」⇒ 這份是舊檔冒充
        verdict_stale = resume_route.handback_verdict(str(stale_path), future_spawn_at)
        assert verdict_stale == "stale", f"spawn 之後才寫的舊檔應判 stale，實得 {verdict_stale!r}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_g2_handback_postcheck_alerts_on_missing() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-postcheck-"))
    try:
        route = {"handback": str(tmp / "does-not-exist.md")}
        state: dict = {"session_id": "sid-postcheck"}
        events: list[dict] = []
        alerts: list[dict] = []

        def _append_log(_log, event, **fields):
            events.append({"event": event, **fields})

        def _alert(reason, _st, *, loud=True, plan=None, **_kw):  # noqa: ARG001
            alerts.append({"reason": reason, "loud": loud})
            return {}

        verdict = resume_route.handback_postcheck(
            route, datetime.now().timestamp(), state, tmp / "log.jsonl", _append_log, _alert)
        assert verdict == "missing", f"handback 檔缺席應判 missing，實得 {verdict!r}"
        assert any(e["event"] == "handback_missing" for e in events), (
            f"G2：交接檔缺席必須落 handback_missing 事件，實得 {events}")
        assert any(c["loud"] for c in alerts), (
            "G2：交接不可見是 2026-08-30 原事故形態，postcheck 必須 loud 告警")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_g1g2_real_run_resume_exercises_full_wiring(break_mode: str | None) -> None:
    """與上面幾支不同：**不 mock `_run_resume()`本體**，只在 `subprocess.run` 這個
    OS 邊界注入假子行程——讓 G1（argv 權限姿態組裝）與 G2（handback postcheck 接線）
    走**真正的生產路徑**（同 `RunResumeWritesHandbackPathIntoStateTest` 既有回歸鎖
    的紀律），而不是像其他場景那樣直接把劇本塞進 state。這是本檔最貼近「重演一次
    真實續跑」的一格。
    """
    with _isolated_handback_dir() as hb_root:
        tmp = Path(tempfile.mkdtemp(prefix="replay-r113-real-run-resume-"))
        try:
            session_id = "sid-real-run-resume"
            plan = tmp / "plan.md"
            transcript = tmp / f"{session_id}.jsonl"
            transcript.write_text("", encoding="utf-8", newline="\n")
            state = {
                "schema": planner.RELAY_SCHEMA, "session_id": session_id,
                "plan_path": str(plan), "state": "armed", "kind": guard.LIMIT_SESSION,
                "reset_at": "2026-08-31T00:10:00+08:00",
                "reset_source": "transcript-verbatim", "attempts": 0, "max_attempts": 5,
                "allow_resume": True, "task_name": "T-replay-real",
                "next_run_time": "2026/08/31 00:12:00", "transcript": str(transcript),
            }
            plan.write_text("# 可重啟點任務書（演練）\n\n## 3. 下一步\n\n讀本檔照做\n\n"
                            + planner.render_relay(state), encoding="utf-8", newline="\n")
            args = planner.build_parser().parse_args(
                ["--resume-tick", "--plan", str(plan), "--task-name", "T-replay-real"])
            log = tmp / "log.jsonl"
            captured_argv: list = []

            def _fake_subprocess_run(argv, **_kwargs):
                captured_argv.append(argv)
                if break_mode != "no-handback":
                    hb_path = resume_route.handback_report(session_id)
                    hb_path.parent.mkdir(parents=True, exist_ok=True)
                    hb_path.write_text(_handback_text("還有第 4 步"),
                                       encoding="utf-8", newline="\n")
                return _real_subprocess.CompletedProcess(
                    args=argv, returncode=0, stdout="ok（假 spawn，未啟動任何 claude 二進位）",
                    stderr="")

            events: list[dict] = []
            alerts: list[dict] = []
            with contextlib.ExitStack() as stack:
                stack.enter_context(unittest.mock.patch.object(
                    planner, "subprocess", new=_FakeSubprocessModule(_fake_subprocess_run)))
                stack.enter_context(unittest.mock.patch.object(
                    planner, "append_log",
                    side_effect=lambda _l, e, **f: events.append({"event": e, **f})))
                # 🔴 `escalation.alert()` 在 loud 分支會寫一支**固定路徑**的真檔
                # （`%TEMP%/AUTOSDD_ATTENTION.md`）——那是這台機器上任何一個真實續航
                # 事件（人工或排程）共用的同一張紙，本演練絕不能碰它，否則會與真實
                # 事件互踩（本機實測就撞過一次：演練寫完馬上被另一支真排程覆寫回
                # 去，兩者互相看不見對方）。全程改用假身只記錄呼叫，不落地。
                stack.enter_context(unittest.mock.patch.object(
                    planner.escalation, "alert",
                    side_effect=lambda reason, _st, *, loud=True, plan=None, **_kw: (
                        alerts.append({"reason": reason, "loud": loud}), {})[1]))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                rc = planner._run_resume(args, state, log)

            assert rc == 0, f"假 spawn rc 應為 0，實得 {rc}"
            assert captured_argv, "subprocess.run 邊界從未被呼叫——argv 組裝路徑沒被真的走過"
            argv0 = captured_argv[0]
            assert "--permission-mode" in argv0 and "acceptEdits" in argv0, (
                f"G1：真實生產路徑組出來的 argv 缺權限姿態旗標：{argv0}")
            assert "--settings" in argv0, f"G1：真實生產路徑組出來的 argv 缺 --settings：{argv0}"
            assert state.get("handback_path"), (
                "G1 修復 F1 回歸：state['handback_path'] 必須被寫入"
                "（此前 production 路徑上這個鍵恆缺席，見 relay_machine 檔頭 WHY）")
            expected_hb = str(resume_route.handback_report(session_id))
            assert state["handback_path"] == expected_hb, (
                f"handback 路徑與 route 算出來的不一致：{state['handback_path']!r} != "
                f"{expected_hb!r}")

            if break_mode == "no-handback":
                assert state["handback_verdict"] == "missing", (
                    f"刻意不寫 handback 時應判 missing，實得 {state['handback_verdict']!r}")
                assert any(e["event"] == "handback_missing" for e in events), (
                    "G2：postcheck 必須落 handback_missing 事件")
                assert any(c["loud"] for c in alerts), (
                    "G2：交接不可見必須 loud 告警（本場景已將 alert 假身化，不落地真檔）")
            else:
                assert state["handback_verdict"] == "written", (
                    f"真的照四節寫了 handback 應判 written，實得 {state['handback_verdict']!r}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    assert hb_root  # 僅供靜態分析：hb_root 用於 with-as 語意完整性，無額外斷言


# ═══════════════════════════════════════════════════════════════════════════
# G3 + G4 —— 配額內自循環 ＋ 哨兵 fire 後重掛（§3(c)／§3(d)）
# ═══════════════════════════════════════════════════════════════════════════
def scenario_g3g4_relay_chain_to_exhaustion() -> None:
    """真正的多視窗串接：同一份任務書連續呼叫 `_resume_tick()` 好幾次，驗
    `relay_seq` 真的逐窗遞增（RELAY_NEXT），直到撞上 spawn 上限（RELAY_EXHAUSTED）
    才停並重掛哨兵——這是本檔對「G3：有額度就該繼續，2026-08-30 原事故卻續跑
    單回合即止」這句話最直接的重演。
    """
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-chain-"))
    try:
        hb = tmp / "handback.md"
        hb.write_text(_handback_text("還有工作"), encoding="utf-8", newline="\n")
        plan = _build_plan(tmp, "T-replay-chain", "sid-chain")
        cap = 2  # 出廠值（PRD §3(c) 常數表 AUTOSDD_RELAY_MAX_SPAWNS 出廠 2），本檔顯式
                 # 注入固定值（見 _run_resume_tick 的 max_spawns 參數），不依賴宿主環境
                 # 變數，確保演練結果不受本機既有 ENV 影響。
        run_result_progress = {"handback_verdict": "written", "handback_path": str(hb),
                               "files_changed": 2, "route_strategy": planner.STRATEGY_RESUME}

        for window in range(1, cap + 1):
            rc, _written, events, _alerts, arm_calls, registered = _run_resume_tick(
                plan, "T-replay-chain", run_resume_result=run_result_progress,
                band=quota_policy.BAND_FREE, max_spawns=cap, no_progress_limit=1)
            assert rc == 0, f"window{window} rc 應為 0，實得 {rc}"
            assert any(e["event"] == "relay_spawned" for e in events), (
                f"window{window} 應觸發 relay_spawned，實得事件：{events}")
            assert registered and registered[0]["relay_seq"] == window, (
                f"window{window} 之後 relay_seq 應落盤為 {window}：{registered}")
            assert arm_calls == [], (
                f"window{window}（RELAY_NEXT）不該重掛哨兵——下一窗自己接手：{arm_calls}")

        # 第 cap+1 窗：relay_seq 已等於 cap ⇒ 判準①（under_cap）為假 ⇒ RELAY_EXHAUSTED
        rc, _written, events, alerts, arm_calls, registered = _run_resume_tick(
            plan, "T-replay-chain", run_resume_result=run_result_progress,
            band=quota_policy.BAND_FREE, max_spawns=cap, no_progress_limit=1)
        assert any(e["event"] == "relay_stopped" and e.get("why") == "cap" for e in events), (
            f"達 cap 應觸發 relay_stopped why=cap，實得事件：{events}")
        assert any(c["loud"] for c in alerts), "達 spawn 上限必須 loud 告警（留任務書給人）"
        assert len(arm_calls) == 1, (
            f"G4 判準1：RELAY_EXHAUSTED 仍必須重掛哨兵恰一次，實得 {arm_calls}")
        assert registered == [], "RELAY_EXHAUSTED 不得再排下一窗"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_g3g4_no_progress_stop_rearms() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-noprog-"))
    try:
        plan = _build_plan(tmp, "T-replay-noprog", "sid-noprog")
        # 假 spawn 例外（rc=None）：handback_verdict/files_changed 維持 `_run_resume`
        # 一開場就寫的乾淨初值（"missing"/0）——判準③保守回真（有未完項）、
        # 判準④因零進度而 streak 立刻達門檻。
        rc, written, events, alerts, arm_calls, registered = _run_resume_tick(
            plan, "T-replay-noprog", run_resume_result={"_rc": None},
            band=quota_policy.BAND_FREE, max_spawns=2, no_progress_limit=1)
        assert rc == 1, f"resume_rc=None 時既有契約應回傳 1，實得 {rc}"
        assert written["state"] == "resume_failed", f"實得 {written.get('state')!r}"
        assert any(e["event"] == "relay_stopped" and e.get("why") == "no_progress"
                  for e in events), f"應觸發 relay_stopped why=no_progress，實得 {events}"
        loud = [c for c in alerts if c["loud"]]
        assert len(loud) == 1, f"escalate(loud) 必須恰一次，實得 {loud}"
        assert len(arm_calls) == 1, f"G4 判準1：NO_PROGRESS_STOP 仍必須重掛哨兵，實得 {arm_calls}"
        assert registered == [], "NO_PROGRESS_STOP 不得再排下一窗"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_g3g4_quota_stop_rearms_quietly() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-quota-"))
    try:
        hb = tmp / "handback.md"
        hb.write_text(_handback_text("還沒做完"), encoding="utf-8", newline="\n")
        plan = _build_plan(tmp, "T-replay-quota", "sid-quota")
        run_result = {"handback_verdict": "written", "handback_path": str(hb),
                     "files_changed": 1, "route_strategy": planner.STRATEGY_RESUME}
        rc, _written, events, alerts, arm_calls, registered = _run_resume_tick(
            plan, "T-replay-quota", run_resume_result=run_result,
            band=quota_policy.BAND_UNMEASURED, max_spawns=2, no_progress_limit=1)
        assert rc == 0, f"實得 {rc}"
        assert any(e["event"] == "relay_stopped" and e.get("why") == "band" for e in events), (
            f"band 量不到（unmeasured）應觸發 relay_stopped why=band，實得 {events}")
        assert not any(c["loud"] for c in alerts), "QUOTA_STOP 交回既有哨兵巡邏，不該吵人"
        assert len(arm_calls) == 1, f"G4 判準1：QUOTA_STOP 仍必須重掛哨兵，實得 {arm_calls}"
        assert registered == [], "QUOTA_STOP 不得再排下一窗"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_g3g4_done_state_rearms() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-done-"))
    try:
        hb = tmp / "handback.md"
        hb.write_text(_handback_text(""), encoding="utf-8", newline="\n")  # 下一步指令節清空
        plan = _build_plan(tmp, "T-replay-done", "sid-done")
        run_result = {"handback_verdict": "written", "handback_path": str(hb),
                     "files_changed": 1, "route_strategy": planner.STRATEGY_RESUME}
        rc, _written, events, _alerts, arm_calls, registered = _run_resume_tick(
            plan, "T-replay-done", run_resume_result=run_result,
            band=quota_policy.BAND_FREE, max_spawns=2, no_progress_limit=1)
        assert rc == 0, f"實得 {rc}"
        assert any(e["event"] == "relay_done" for e in events), f"實得事件：{events}"
        assert registered == [], "DONE 不得再排下一窗"
        assert len(arm_calls) == 1, f"G4 判準1：DONE 仍必須重掛哨兵，實得 {arm_calls}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_g3g4_refuse_never_written_as_resumed() -> None:
    """讓真正的 `_resume_tick()`／`settle_window()` 接線跑一遍，只把
    `choose_resume_route()` 換成一支恆回 REFUSE 的假函式——REFUSE 分支在
    `_run_resume()` 裡 `argv is None` 就直接 `return 1`，早於任何
    `subprocess.run`／`preflight_problem()`，所以連這個假身都不需要碰
    subprocess 邊界，天生零風險。
    """
    tmp = Path(tempfile.mkdtemp(prefix="replay-r113-refuse-"))
    try:
        plan = _build_plan(tmp, "T-replay-refuse", "sid-refuse")
        args = planner.build_parser().parse_args(
            ["--resume-tick", "--plan", str(plan), "--task-name", "T-replay-refuse"])
        arm_calls: list = []
        events: list[dict] = []

        def _fake_choose_route(*_a, **_k):
            return {"strategy": planner.STRATEGY_REFUSE, "argv": None,
                   "reason": "演練合成：任務書路徑缺席"}

        with contextlib.ExitStack() as stack:
            stack.enter_context(unittest.mock.patch.object(
                planner, "probe_quota", lambda *_a, **_k: {
                    "open": True, "kind": guard.LIMIT_NONE, "rc": 0, "text": "ok"}))
            stack.enter_context(unittest.mock.patch.object(
                planner, "choose_resume_route", side_effect=_fake_choose_route))
            stack.enter_context(unittest.mock.patch.object(
                planner, "append_log",
                side_effect=lambda _l, e, **f: events.append({"event": e, **f})))
            stack.enter_context(unittest.mock.patch.object(
                planner, "_schtasks_remove", side_effect=lambda _t: 0))
            stack.enter_context(unittest.mock.patch.object(
                planner, "_arm_sentinel",
                side_effect=lambda _a, t, _pl: (arm_calls.append(str(t)), 0)[1]))
            stack.enter_context(unittest.mock.patch.object(
                planner.escalation, "alert", side_effect=lambda *_a, **_k: {}))
            stack.enter_context(unittest.mock.patch.object(
                relay_machine, "current_band", lambda *_a, **_k: quota_policy.BAND_FREE))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            rc = planner._resume_tick(args)
        written = planner.parse_relay(plan.read_text(encoding="utf-8"))
        assert written["state"] != "resumed", "REFUSE 是拒絕動作，不是成功續跑，不得寫成 resumed"
        assert written["state"] == "resume_failed", f"實得 {written.get('state')!r}"
        assert len(arm_calls) == 1, "REFUSE 仍必須重掛哨兵（G4 判準1／失敗態歸屬）"
        assert rc == 1, f"REFUSE 既有 rc 契約（choose_resume_route 早退回的 1）應沿用，實得 {rc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_SCENARIOS: list[tuple[str, str]] = [
    ("G1-argv-permission-posture", "scenario_g1_permission_argv"),
    ("G1-preflight-missing-settings-rejects", "scenario_g1_preflight_missing_settings_rejects_spawn"),  # noqa: E501
    ("G1-preflight-real-settings-passes", "scenario_g1_preflight_real_settings_passes"),
    ("G2-handback-verdict-3-values", "scenario_g2_handback_verdict"),
    ("G2-handback-postcheck-alerts-on-missing", "scenario_g2_handback_postcheck_alerts_on_missing"),  # noqa: E501
    ("G1G2-real-run-resume-full-wiring", "scenario_g1g2_real_run_resume_exercises_full_wiring"),
    ("G1G2-real-run-resume-broken-handback", "scenario_g1g2_real_run_resume_exercises_full_wiring"),  # noqa: E501
    ("G3G4-relay-chain-to-exhaustion", "scenario_g3g4_relay_chain_to_exhaustion"),
    ("G3G4-no-progress-stop-rearms", "scenario_g3g4_no_progress_stop_rearms"),
    ("G3G4-quota-stop-rearms-quietly", "scenario_g3g4_quota_stop_rearms_quietly"),
    ("G3G4-done-state-rearms", "scenario_g3g4_done_state_rearms"),
    ("G3G4-refuse-never-written-as-resumed", "scenario_g3g4_refuse_never_written_as_resumed"),
]


def _invoke(name: str, break_mode: str | None) -> None:
    """依名字分派到對應場景函式，需要 `break_mode` 的場景各自認自己的關鍵字。"""
    fn = globals()[name]
    if name == "scenario_g2_handback_verdict":
        fn(break_mode)
        return
    if name == "scenario_g1g2_real_run_resume_exercises_full_wiring":
        # 兩個帳號名共用同一支函式：一支跑正常路徑，一支跑「模型忘了寫 handback」
        # 這個**合法的真實場景**（不是自我證偽開關，是本檔既有的覆蓋率）。
        fn(None)
        return
    fn()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="R113 最後一哩端到端演練駕駛器（tools/probe/replay_r113_lastmile.sh 專用）")
    parser.add_argument("--break", dest="break_mode", default=None,
                        choices=["handback-marker"],
                        help="自我證偽開關：刻意弄壞一個場景的輸入，驗證本腳本真的有鑑別力"
                             "（PRD §4 V-e2e 驗收項 3）。正常演練不要帶這個旗標。")
    args = parser.parse_args(argv)

    print("=" * 78)
    print("R113 最後一哩端到端演練 —— 重演 2026-08-30 撞線事件，驗 G1~G4 四缺口全閉合")
    if args.break_mode:
        print(f"⚠️  自我證偽模式已開啟：--break {args.break_mode}（本次跑完預期 rc!=0）")
    print("=" * 78)

    failures: list[str] = []
    for idx, (label, fn_name) in enumerate(_SCENARIOS, start=1):
        # G1G2-real-run-resume-broken-handback 那一列復用同一支函式但要傳
        # break_mode="no-handback"（與 --break handback-marker 是兩件事：前者是
        # 常駐覆蓋率，後者是使用者觸發的自我證偽開關）。
        try:
            if label == "G1G2-real-run-resume-broken-handback":
                scenario_g1g2_real_run_resume_exercises_full_wiring("no-handback")
            else:
                _invoke(fn_name, args.break_mode)
        except AssertionError as exc:
            failures.append(f"{label}: {exc}")
            print(f"  [FAIL]  {idx:2d}. {label}: {exc}")
        except Exception as exc:  # noqa: BLE001 — 演練腳本：未預期例外一律算場景失敗，不吞掉
            failures.append(f"{label}: 未預期例外 {type(exc).__name__}: {exc}")
            print(f"  [ERROR] {idx:2d}. {label}: {type(exc).__name__}: {exc}")
        else:
            print(f"  [PASS]  {idx:2d}. {label}")

    print("-" * 78)
    if failures:
        print(f"❌ {len(failures)}/{len(_SCENARIOS)} 場景失敗：")
        for item in failures:
            print(f"   - {item}")
        print("=" * 78)
        return 1
    print(f"✅ 全部 {len(_SCENARIOS)} 場景通過 —— G1~G4 四缺口全閉合重演成功，"
         "全程零真實額度消耗、零真 spawn claude、零真 schtasks/launchd。")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
