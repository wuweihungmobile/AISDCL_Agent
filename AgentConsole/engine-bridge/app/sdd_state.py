"""FSM 狀態檔的**唯讀**存取與衍生資訊（`GET /sdd/fsm*`、`:freeze` 前置、批次預檢與回收點共用）。

Rule 9 絕對禁令 #1（繞過 FSMRuntime 直接讀寫 `FSM-STATE-*.yaml`）：本模組只讀；Bridge 的所有寫入一律
經 `sdd_cli.run_verb` 子行程。tests/test_sdd_integration_parity.py 的 AST 鎖（F-4）掃整個 `app/`——
出現 `FSM-STATE` 字串的模組不得含寫入形態呼叫（`open` 寫模式、`write_text`、`os.replace`、
`unlink`…）。讀取前請先 `with sdd_cli.state_guard(fsm_dir, key)`：同一把鎖罩住 CLI 呼叫與這裡的讀
檔，消除「讀的當下被 `os.replace` 換檔」的 Windows 共享違規。
"""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path
from typing import Any

import yaml

from . import security
from .errors import ApiError, not_found
from .sdd_cli import CLI_MODULE

STATE_PREFIX = "FSM-STATE-"
STATE_SUFFIX = ".yaml"
#: `decision_trace`／`escalation_history` 回幾筆（尾端，舊→新）。
TRAIL = 5
ESCALATION_STATES = frozenset({"ESCALATION", "ESCALATION_FINAL"})
#: 人工恢復 `--to` 的合法目標（SDD 側 `RESUME_TARGETS` 的鏡像；Bridge 不 import SDD）。
RESUME_TARGETS = ("SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW")
DELEGATION_FAILED_SOURCE = "autoclaude_delegated_failed"


def state_dir_of(root: Path) -> Path:
    """專案根（或 SDD 版本目錄）底下的 FSM 狀態目錄。"""
    return root / "build" / "reports" / "fsm"


def readable_state_file(fsm_dir: Path, key: str) -> Path | None:
    """`FSM-STATE-<key>.yaml`；不是檔案、或 resolve 後跑出 fsm 目錄（symlink 逃逸）＝None。
    `key` 必須已通過 `fsm_names.fsm_component`／`is_fsm_project_name`（分隔符與 `..` 在那一關就被
    擋掉）。"""
    path = fsm_dir / f"{STATE_PREFIX}{key}{STATE_SUFFIX}"
    if not path.is_file() or not security.is_within(path.resolve().parent, fsm_dir):
        return None
    return path


def load_state(path: Path) -> dict[str, Any]:
    """讀出 `fsm_state` 根節點；讀不動、不是 YAML、缺根節點一律 422（不是 500）。"""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, RecursionError, yaml.YAMLError) as exc:
        raise ApiError(422, "fsm_state_unreadable", detail=str(exc)) from exc
    state = doc.get("fsm_state") if isinstance(doc, dict) else None
    if not isinstance(state, dict):
        raise ApiError(422, "fsm_state_unreadable", detail="缺少 fsm_state 根節點")
    return state


def read_state(fsm_dir: Path, key: str, *, display_name: str | None = None
               ) -> tuple[Path, dict[str, Any]]:
    """讀一個專案的狀態：找不到＝404 `fsm_not_found`；壞檔＝422 `fsm_state_unreadable`。"""
    path = readable_state_file(fsm_dir, key)
    if path is None:
        raise not_found("fsm_not_found", project=display_name if display_name is not None else key)
    return path, load_state(path)


def tail(value: Any, count: int = TRAIL) -> list[Any]:
    return value[-count:] if isinstance(value, list) else []


def frozen_stage_count(state: dict[str, Any]) -> int:
    stages = state.get("frozen_stages")
    return len(stages) if isinstance(stages, list) else 0


def delegation_ref(state: dict[str, Any]) -> str | None:
    """`autoclaude_delegated_tracking.playbook_ref`。🔴 只在 `current_state=AUTOCLAUDE_DELEGATED`
    時才有意義：FSM 檔的 tracking 在 `delegate-exit` 後**不清除**（ADR §2.4 #15），在
    IMPLEMENTATION 上是歷史殘留欄，呼叫端必須先看 `current_state`（回收點判定、`resume`／
    `restore` 的比對都這樣用）。"""
    tracking = state.get("autoclaude_delegated_tracking")
    ref = tracking.get("playbook_ref") if isinstance(tracking, dict) else None
    return ref if isinstance(ref, str) else None


def frozen_digest_of(state: dict[str, Any], spec_path: Path) -> str | None:
    """凍結時記下的、這份規格檔的摘要（`frozen_stages[*].spec_doc_digests` 的聯集，後一階段勝出）。
    比對法鏡像 adapter（ADR §6.1）：鍵以 `/` 拆段、`os.path.join` 組成本機路徑，兩邊各過
    `normcase`，判 `me == 鍵` 或 `me.endswith(os.sep + 鍵)`，多個鍵吻合取最長者——不依賴專案根的絕
    對路徑，所以 Docker 與主機路徑不同也成立。**不得**對 `as_posix()` 字串直接 `normcase`
    （Windows 會把 `/` 換成 `\\`）。
    只用在「回報 409 時補上凍結摘要」，不用在放行判斷（放行判斷是 adapter 的事）。"""
    merged: dict[str, str] = {}
    stages = state.get("frozen_stages")
    for stage in stages if isinstance(stages, list) else []:
        digests = stage.get("spec_doc_digests") if isinstance(stage, dict) else None
        if isinstance(digests, dict):
            merged.update({k: v for k, v in digests.items()
                           if isinstance(k, str) and isinstance(v, str)})
    me = os.path.normcase(str(spec_path.resolve()))
    best: tuple[int, str] | None = None
    for key, value in merged.items():
        local = os.path.normcase(os.path.join(*key.split("/")))
        if (me == local or me.endswith(os.sep + local)) and (best is None or len(local) > best[0]):
            best = (len(local), value)
    return best[1] if best else None


def resume_target(state: dict[str, Any]) -> str:
    """人工恢復的 `--to` 目標（鏡像 SDD `recovery_hint.resume_target`）。委派失敗
    （provenance.source＝
    `autoclaude_delegated_failed`）取 `autoclaude_delegated_tracking.resume_state`（缺或不合法＝
    IMPLEMENTATION）；
    其餘取 `auto_compact_state.resume_state`，不合法＝SPEC_DRAFTING（fallback）。"""
    provenance = state.get("escalation_provenance")
    if isinstance(provenance, dict) and provenance.get("source") == DELEGATION_FAILED_SOURCE:
        tracking = state.get("autoclaude_delegated_tracking")
        resume = tracking.get("resume_state") if isinstance(tracking, dict) else None
        return resume if resume in RESUME_TARGETS else "IMPLEMENTATION"
    auto = state.get("auto_compact_state")
    resume = auto.get("resume_state") if isinstance(auto, dict) else None
    return resume if resume in RESUME_TARGETS else "SPEC_DRAFTING"


def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def recovery_commands(state: dict[str, Any], *, sdd_root: Path, fsm_dir: Path,
                      key: str) -> dict[str, str]:
    """ESCALATION／ESCALATION_FINAL 時的可複製恢復指令（ADR §5.3）。恢復**只有人能做、留在 SDD
    session**：Bridge 與 Console 不提供恢復動詞，只把「怎麼做」交給人。PowerShell 形：
    `Push-Location … -ErrorAction
    Stop; …; Pop-Location` 同一句內成對、不裸 `cd`（根層鐵律一、二）；POSIX 形：`VAR=值 指令
    ` 前綴只作用於該指令。`<人工原因
    >` 是要人改的佔位。路徑值依平台引用（PowerShell 單引號、POSIX shlex），不被
    殼展開。"""
    target = resume_target(state)
    py = sys.executable
    tail_args = (f"-m {CLI_MODULE} resume-from-escalation --project {{project}} --to {target} "
                 '--reason "<人工原因>"')
    powershell = (
        f"Push-Location {_ps_quote(str(sdd_root))} -ErrorAction Stop; "
        f"$env:SDD_STATE_DIR = {_ps_quote(str(fsm_dir))}; "
        f"& {_ps_quote(py)} " + tail_args.format(project=_ps_quote(key)) + "; "
        "Remove-Item Env:SDD_STATE_DIR; Pop-Location")
    posix = (
        f"cd {shlex.quote(str(sdd_root))} && SDD_STATE_DIR={shlex.quote(str(fsm_dir))} "
        f"{shlex.quote(py)} " + tail_args.format(project=shlex.quote(key)))
    return {"target": target, "powershell": powershell, "posix": posix}
