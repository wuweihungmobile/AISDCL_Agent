"""planner 排程站點的副作用隔離接線（DES RealVerify_SideEffect_Isolation §3.4／§4／§5.4，S2）。"""
# 立案：2026-11-20 幽靈 session 57d0ccad（DEF-200-632）＋A6f 鑑定：RV-SK1／SK2 的沙盒哨兵
# `AutoSDD_Sentinel_<沙盒 sid>` 是真前綴，排程 tick 吃機器環境，痕跡進真 `~/.autosdd`、
# SK2 會發真 `claude -p -r`。判準本體在 `sandbox_scope`（只吃目標自帶資料、不讀 env、不開行程）；
# 本檔只是 `session_resume_planner` 的三個接點：
#   · `register_gate`：登記前——目標是沙盒而租約／主人／存在性不成立 ⇒ 拒絕登記（rc 4）；
#   · `carriage`：登記時——沙盒或有顯式 env 時，把 `--job-env`（居所／行為開關）與 OS 自毀
#     （EndBoundary＋DeleteExpiredTaskAfter，Windows）併進 Action／觸發器；正式目標且無顯式
#     env ⇒ 全空 ⇒ 註冊腳本與 Action 引數逐字不變；
#   · `tick_gate`：到點首判——沙盒目標而租約過期／主人已死／家已刪（或起 `claude` 前執行檔
#     不在沙盒家內）⇒ 不探測、不 spawn、自拆排程、落痕跡 `sideeffect_refused`、回 rc 10。
# 🔴 排程名不改（D-5）：哨兵仍叫 `AutoSDD_Sentinel_<sid>`，驗的是真路徑；前綴只解「掃得到」
# 不解「到點照開」，且改名會讓 `sentinel_lifecycle` 的 GC／活性檢查與單一擁有者判準失明。
# 🔴 誠實劃界：launchd 無 EndBoundary 對等物，本檔也不改 launchd 的 plist argv（
# `LaunchdBackend._argv` 與其回讀比對自成一套）⇒ macOS 靠 `tick_gate`／`register_gate`（L1）
# ＋L2 清掃，居所 env 不過 launchd 邊界（本批當輪只有合成測試）stale-premise-ok: 當輪事實
# 🔴 守衛面（根 CLAUDE.md〈守衛面准入〉）：暴露證據同 DES §1（幽靈 session 57d0ccad、A6f 鑑定）。
from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import endurance_env
import sandbox_scope

#: `jsonl_trace` 缺省落的痕跡檔名（站點自帶痕跡者不用它）。
TRACE_NAME = "autosdd_sideeffect_refused.jsonl"

#: 登記站點被 L1 拒絕的 rc（CLI 既有拒絕碼＝4，D-24）；與 `RC_SIDEEFFECT_REFUSED`（10）、
#: `endurance_env.RC_RESIDENCE_MISSING`（9）、job 環境值不合法（2）互異。
RC_REGISTER_REFUSED = 4
_AT_LITERAL = re.compile(r"^'(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d:\d\d)'$")


class Carriage(NamedTuple):
    """併進排程註冊的三段：Action 引數後綴、觸發器後綴、設定後綴（全空＝與修前逐字相同）。"""

    argument: str = ""
    trigger_ps: str = ""
    settings_ps: str = ""


def _fire_of(at_expr: str | None) -> datetime | None:
    """`'YYYY-MM-DD HH:MM:SS'` 字面（`register_endurance` 的產物，機器本地框架）⇒ 帶 offset 的
    時刻；其他（手動 `--at` 的 PowerShell 運算式）解不出 ⇒ None，不假精確。"""
    match = _AT_LITERAL.match((at_expr or "").strip())
    return datetime.fromisoformat(f"{match[1]}T{match[2]}").astimezone() if match else None


def carriage(repo_root, env: Mapping[str, str], now: datetime,
             at_expr: str | None = None) -> Carriage:
    """登記時的隔離搬運。`repo_root` 是**本 planner 自己的 checkout**（沙盒內的工具副本 ⇒ 沙盒）。

    沙盒：env 中顯式有值的 `JOB_ENV_KEYS` 全轉送（值不合法 ⇒ `JobEnvValueError`，
    `register_gate` 已先攔）；租約有效 ⇒ 帶 OS 自毀；自毀不晚於觸發 ⇒ 腳本在註冊前 `throw`
    （rc≠0、無 NextRunTime，大聲失敗）。正式目標：只轉送顯式且在允許值內者，無顯式值 ⇒ 空。"""
    home = sandbox_scope.sandbox_home(repo_root)
    pairs = endurance_env.job_env_argv(env, sandbox=home is not None)
    # 不用 zip(strict=)：py3.9 無此參數
    argument = "".join(f' {pairs[i]} "{pairs[i + 1]}"' for i in range(0, len(pairs) - 1, 2))
    expire = sandbox_scope.job_expiry(home, now)
    if expire is None:
        return Carriage(argument)
    # 自毀 PowerShell 的唯一家＝engine_resume_job；沙盒路徑才需要，避免 planner 載入期拖入它
    from engine_resume_job import expiry_ps  # noqa: PLC0415
    fire = _fire_of(at_expr)
    trigger, settings = expiry_ps(fire or now, expire)
    if fire is not None and expire <= fire:
        trigger = (f"throw '拒絕註冊：沙盒租約到期 {expire:%H:%M:%S} 不晚於觸發時刻 "
                   f"{fire:%H:%M:%S}（EndBoundary 必須晚於 StartBoundary）'\n")
    return Carriage(argument, trigger, settings)


def _refuse(site: str, reason: str, trace: Callable, **fields) -> None:
    trace("sideeffect_refused", site=site, reason=reason, **fields)
    print(f"❌ 副作用隔離拒絕（{site}）：{reason}", file=sys.stderr)  # pythonw：stderr None 靜默


def register_gate(repo_root, env: Mapping[str, str], fire_at: datetime | None,
                  trace: Callable, site: str) -> int:
    """登記前首判；0＝放行。拒絕＝不登記、落痕跡、stderr 帶 reason；回 4（判準拒絕）或 2
    （job 環境值不合法）。`fire_at` 為 None（手動運算式觸發）⇒ 以現在代入，只驗租約有效、
    不驗「租約長於觸發」。"""
    now = datetime.now().astimezone()
    verdict = sandbox_scope.register_verdict(cwd=repo_root, fire_at=fire_at or now, now=now)
    if not verdict.allow:
        _refuse(site, verdict.reason, trace, roots=list(verdict.roots))
        return RC_REGISTER_REFUSED
    try:
        endurance_env.job_env_argv(env, sandbox=verdict.reason == "sandbox_lease")
    except endurance_env.JobEnvValueError as exc:
        _refuse(site, f"job_env:{exc}", trace, roots=list(verdict.roots))
        return endurance_env.JobEnvValueError.rc
    return 0


def sandboxed(repo_root) -> bool:
    """本 checkout（或資料根）是不是驗證沙盒；`job_env_argv(sandbox=…)` 的唯一來源（D-20）。"""
    return sandbox_scope.sandbox_home(repo_root) is not None


def job_env_pairs(repo_root, env: Mapping[str, str]) -> list[str]:
    """job argv 的 `--job-env KEY=VAL` 串（正式且無顯式 env ⇒ `[]`，argv 逐字不變）。沙盒目標值不在
    允許值內拋 `JobEnvValueError`——站點的 `register_gate` 已先以 rc 2 攔下，這裡不再重複包裝。"""
    return endurance_env.job_env_argv(env, sandbox=sandboxed(repo_root))


def expire_for(repo_root, now: datetime) -> datetime | None:
    """沙盒目標的排程 OS 自毀時刻（租約有效才有值）；正式目標 ⇒ None。"""
    return sandbox_scope.job_expiry(sandbox_scope.sandbox_home(repo_root), now)


def jsonl_trace(path=None) -> Callable:
    """給沒有自帶 `trace(event, **fields)` 的站點（quota_escalation、openitems、SI）用的痕跡寫入器：
    append 一行 JSONL 到 `path`（缺省＝持久痕跡目錄的 `autosdd_sideeffect_refused.jsonl`）；
    寫不進去不得升級為故障（同本 repo 各 `append_log` 的紀律）。"""
    def _trace(event: str, **fields) -> None:
        row = {"event": event, "at": datetime.now().astimezone().isoformat(timespec="seconds"),
               **fields}
        try:
            target = Path(path) if path else endurance_env.trace_dir() / TRACE_NAME
            with target.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return _trace


def headless_refusal(repo_root, site: str, run: str, exe: str) -> str | None:
    """headless 站點（起 `claude -p` 前）首判：None＝放行；否則回說明字串。

    說明＝`sideeffect-refused: rc=<n>`；執行檔一併判（`sandbox_real_exe`：沙盒不得用真 claude）。"""
    rc = tick_gate(repo_root, site, run, jsonl_trace(), exe=exe)
    return None if rc is None else f"sideeffect-refused: rc={rc}"


def notify_refused(repo_root, transcript, site: str, log_path=None) -> bool:
    """有目標上下文的通知呼叫者（`patrol_housekeeping`、`alert`）首判：True＝拒絕——呼叫端不得出
    toast、不得入佇列。`transcript`＝該目標的逐字稿（slug 帶沙盒字樣也算沙盒）；缺席只判 cwd。"""
    refused = tick_gate(repo_root, site, None, jsonl_trace(log_path),
                        transcript=transcript or None)
    return refused is not None


def si_arm_problem(repo, env: Mapping[str, str], claude: str | None, win: bool) -> str | None:
    """SelfImproving `sched arm` 登記前首判（DES S3 REQ-SE-12／25）。None＝放行；否則回拒絕理由
    （已落痕跡 `sideeffect_refused`）。Windows 巡邏任務由安裝器 `install_windows_nightly.ps1` 註冊，
    它自己寫 argv：沙盒目標帶不進 `--job-env`／OS 自毀、非預設 `--claude` 也帶不進——一律拒絕，
    不靜默丟掉（偏離 DES 的「登記時帶 job_env」：安裝器是守衛面外的固定腳本，改它屬另案）。"""
    trace = jsonl_trace()
    if (rc := register_gate(repo, env, None, trace, "selfimproving.sched_arm")):
        return f"副作用隔離拒絕登記（rc={rc}；理由見 stderr 與痕跡）"
    if win and (sandboxed(repo) or claude):
        why = "sandbox_installer_no_job_env" if sandboxed(repo) else "claude_flag_unsupported"
        trace("sideeffect_refused", site="selfimproving.sched_arm", reason=why)
        return f"Windows 巡邏任務由安裝器註冊，無法帶 job 環境／OS 自毀／--claude（{why}）"
    return None


def tick_gate(repo_root, site: str, task: str | None, trace: Callable, *, transcript=None,
              exe=None) -> int | None:
    """到點首判；None＝放行。拒絕＝落痕跡並回 `RC_SIDEEFFECT_REFUSED`；**自拆排程由呼叫端做**
    （planner 既有 disarm 路 `_schtasks_remove`；tick「每條 return 先處置排程」的靜態鎖認得它）。
    `exe`＝這一刻起要用的 `claude` 執行檔（探測／續跑前傳；純巡邏讀檔的首判傳 None）；
    `transcript`＝狀態塊記的逐字稿。"""
    verdict = sandbox_scope.target_verdict(cwd=repo_root, transcript=transcript, exe=exe,
                                           now=datetime.now().astimezone())
    if verdict.allow:
        return None
    _refuse(site, verdict.reason, trace, task=task or "", roots=list(verdict.roots))
    return sandbox_scope.RC_SIDEEFFECT_REFUSED
