"""被拒絕的長睡之外部續跑交棒（PRD §4.5.2／§4.5.5；ARCH-01）。"""
# WHY 這支存在
# ------------
# `AutoResumeService._wait` 對 > max_inprocess_wait_seconds 的等待拒絕行程內長睡、以 rc=1 退出。
# 修前那之後**沒有任何元件**重啟引擎（日誌自己寫「須由外部人工／自備排程器重啟」）：無人值守時整場
# run 在第一次撞週額度就停死，與「喚醒鏈必須自癒、不接受人介入」直接相衝。
# 引擎不自己蓋排程器（那是 launchd／schtasks 兩套平台知識，住 monorepo 根層 harness；而
# `.importlinter` Rule 9 禁止 autoclaude import 根層護欄層），所以只開**一個環境變數鉤子**：
# `AUTOCLAUDE_EXTERNAL_RESUME_CMD` 非空時，拒絕之後以它為 argv 範本呼叫一次（承接者＝根層
# `tools/lib/engine_resume_job.py`，操作者把它寫進範本；檔案契約，不 import）。預設空＝本機制不
# 存在、行為與修前逐位元相同。
#
# 🔴 範本**先切字、再逐項代入**佔位（`{playbook}`／`{resume_at}`／`{cwd}`），且不經殼：路徑含空白、
#    引號、`;`、`$()` 都仍是單一 argv 項，資料不會被當成指令。代入是單趟（路徑裡剛好有 `{cwd}`
#    字面不會被再展開一次）。
# 🔴 失敗只出聲、不改回傳：交棒是**加項**，引擎照舊 rc=1 並帶真實續跑時刻——操作者看得到 ERROR 行
#    與 WARNING 行，手動重跑仍然成立。逾時上限 60 秒（承接者只該註冊一個排程就退出）。
# 🔴 checkpoint 未確認落地時**不交棒**：外部續跑會從頭重跑，而「從頭重跑」不是「續跑」。
# 🔴 時刻帶 offset：檔案後端的 checkpoint 時刻是 naive 本地時間（Pg 是 aware），一律在這裡收斂成
#    帶 offset 的 ISO，承接者（排程器）才不必猜時區。誠實劃界：子行程只繼承引擎行程的環境，
#    承接者掛出去的排程帶哪些環境變數由承接者決定（見其檔頭）。
from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
from datetime import datetime, timedelta

from ...utils.platform_caps import is_windows

logger = logging.getLogger("autoclaude.core.services.external_resume")

#: 交棒指令範本的環境變數名。字面兩個家：根層 `tools/lib/engine_resume_job.py` 的同名常數，
#: 對齊由 `tools/probe/engine_resume_job_sim.py` 讀兩邊原始碼比對（跨 importlinter 只能這樣接）。
EXTERNAL_RESUME_CMD_ENV = "AUTOCLAUDE_EXTERNAL_RESUME_CMD"
#: 承接者只該註冊一個排程就退出；卡住 60 秒就放棄（不拖住即將退出的引擎）。
HAND_OFF_TIMEOUT_SECONDS = 60
_PLACEHOLDER = re.compile(r"\{(playbook|resume_at|cwd)\}")


def split_template(template: str, posix: bool | None = None) -> list[str]:
    """把範本切成 argv。posix 切字會吃掉 Windows 路徑的反斜線 ⇒ nt 用非 posix 模式並去成對引號。"""
    posix = (not is_windows()) if posix is None else posix
    parts = shlex.split(template, posix=posix)
    if posix:
        return parts
    return [p[1:-1] if len(p) >= 2 and p[0] == p[-1] and p[0] in "\"'" else p for p in parts]


def _aware_iso(resume_at: str | None, wait_secs: float) -> str:
    try:
        moment = datetime.fromisoformat(resume_at) if resume_at else None
    except (TypeError, ValueError):
        moment = None
    if moment is None:                       # 時刻沒釘住（改寫失敗）⇒ 以「現在＋等待秒數」推
        moment = datetime.now().astimezone() + timedelta(seconds=wait_secs)
    return moment.astimezone().isoformat(timespec="seconds")      # naive 視為本地時間


def hand_off(playbook: str, resume_at: str | None, wait_secs: float, *, confirmed: bool) -> None:
    """拒絕長睡之後呼叫一次外部續跑指令；任何失敗只 `logger.warning`，不拋、不改引擎回傳。"""
    template = os.environ.get(EXTERNAL_RESUME_CMD_ENV, "").strip()
    if not template:
        return
    if not confirmed:
        logger.warning("AutoResumeService | %s 已設定，但 checkpoint 未確認落地 ⇒ 不交棒給外部續跑"
                       "（從頭重跑不是續跑）", EXTERNAL_RESUME_CMD_ENV)
        return
    values = {"playbook": os.path.abspath(playbook), "cwd": os.getcwd(),
              "resume_at": _aware_iso(resume_at, wait_secs)}
    try:
        argv = [_PLACEHOLDER.sub(lambda m: values[m.group(1)], tok)
                for tok in split_template(template)]
        proc = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                              timeout=HAND_OFF_TIMEOUT_SECONDS, check=False)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.warning("AutoResumeService | 外部續跑指令無法執行（不影響本次結果，請手動於續跑"
                       "時刻後重啟）：%s: %s", type(exc).__name__, exc)
        return
    if proc.returncode != 0:
        logger.warning("AutoResumeService | 外部續跑指令 rc=%d（不影響本次結果）：%s",
                       proc.returncode, (proc.stderr or proc.stdout or "").strip()[-300:])
        return
    logger.info("AutoResumeService | 已交棒外部續跑（續跑時刻 %s）：%s", values["resume_at"],
                (proc.stdout or "").strip()[-300:])
