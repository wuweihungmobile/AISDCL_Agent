"""模型角色（improving_113 W1）：主控／子代理／降級三個角色的模型，由 `.env` 的三個鍵設定。

純函式、零 I/O：env 由呼叫端注入（`quota_gate.policy_env()` 或行程的 `os.environ`），本檔
不讀環境、不碰檔案——hook 鏈上的人話面（`quota_messages`／`session_brief`）與喚醒 argv 組裝
（`resume_route`）才都能放心 import 它。三個鍵的出廠預設只有 `quota_policy.ENV_SPEC` 一個家，
本檔不抄；家族詞彙只有 `quota_policy.family_key()` 一個家，本檔不另立一份。

為何不走 `load_policy()`：它對壞值的語意是「整組退回預設」，一個拼錯的模型名會把整套額度
門檻一起重設（耦合方向錯）。所以三列是 `attr=None`，本檔自己讀、自己驗：壞值只退「該鍵」
預設並進 problems，由呼叫端（`--pace`／SessionStart 簡報）出聲，不連坐其他鍵。

三個角色與消費端：
  · 主控 `AUTOSDD_MODEL_HELMSMAN`：喚醒 argv 的 `--model`（`model_argv`）。空＝不帶旗標，沿用
    存檔／設定鏈（現況行為；非空預設會讓沒有該模型存取的機器喚醒靜默失敗）。互動主視窗自己
    的模型 `.env` 管不到，本檔只管「本 repo 程式自己 spawn 的窗口」。
  · 子代理 `AUTOSDD_MODEL_SUBAGENT`：喚醒窗口環境的 `CLAUDE_CODE_SUBAGENT_MODEL`（`child_env`）。
    官方序位＝呼叫時的 model 參數 ＞ 子代理定義的 frontmatter ＞ 本變數 ＞ 主對話模型，所以
    它只是預設；刻意不設 `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`（設了 Agent 工具就沒有 model 參數，
    守衛也讀不到派工目標）。值 `inherit`（只有本鍵收）＝顯式不注入：`child_env` 回空、行程既有
    的原生變數原樣保留、子代理沿用視窗模型；字面 `inherit` 不寫進子行程環境。
  · 降級 `AUTOSDD_MODEL_DOWNGRADE`：降級建議的第二階、額度付費探針用的模型。
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import NamedTuple

import quota_policy

HELMSMAN_ENV = "AUTOSDD_MODEL_HELMSMAN"
SUBAGENT_ENV = "AUTOSDD_MODEL_SUBAGENT"
DOWNGRADE_ENV = "AUTOSDD_MODEL_DOWNGRADE"
#: Claude Code 認的「子代理預設模型」環境變數（喚醒窗口環境注入用）。
CHILD_ENV_KEY = "CLAUDE_CODE_SUBAGENT_MODEL"
#: 子代理鍵專屬的哨兵值：＝不注入。主控要沿用請留空；降級值會拿去當 `--model`，不收。
INHERIT = "inherit"
_KEYS = (HELMSMAN_ENV, SUBAGENT_ENV, DOWNGRADE_ENV)

#: 值會原樣進 argv／環境：只准這些字元，且不得以 `-` 開頭（不得長得像旗標，也不得帶空白、
#: 分號、路徑分隔而被誤解）。完整 id 的 `[1m]` 後綴在白名單內。
_VALUE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\[\]-]*")
#: 壞值進 problems 時最多引用幾個字元（problems 會原樣進簡報／`--pace`，長度要有界）。
_SHOWN_MAX = 40


class ModelRoles(NamedTuple):
    """三個角色的模型值；空字串＝該角色沒有指定（只有主控的出廠預設是空）；子代理另可為 inherit。"""

    helmsman: str
    subagent: str
    downgrade: str

    @property
    def pinned_subagent(self) -> str:
        """真的會注入／建議的子代理模型；空或 `inherit` ＝沒有（子代理沿用視窗模型）。"""
        return "" if self.subagent == INHERIT else self.subagent

    @property
    def hint_first(self) -> str:
        """降級建議的第一階（連分隔斜線）；沒有釘死的子代理模型就不印，建議行只剩降級一階。"""
        return f"{self.pinned_subagent}/" if self.pinned_subagent else ""


_DEFAULTS = {spec.name: str(spec.default or "")
             for spec in quota_policy.ENV_SPEC if spec.name in _KEYS}
DEFAULT_ROLES = ModelRoles(*(_DEFAULTS.get(key, "") for key in _KEYS))


def _acceptable(key: str, value: str) -> bool:
    """字元白名單 ∧ 認得出家族（別名，或 `claude-sonnet-5-5`／`sonnet[1m]` 這類含家族字的 id）；
    子代理鍵另收 `inherit`（精確拼法）。"""
    if key == SUBAGENT_ENV and value == INHERIT:
        return True
    return bool(_VALUE_RE.fullmatch(value)) and bool(quota_policy.family_key(value))


def load_model_roles(env: Mapping[str, str]) -> tuple[ModelRoles, list[str]]:
    """從 mapping（**不是 os.environ**）讀三角色。回 `(roles, problems)`。

    空白視為未設（走該鍵預設）；壞值退「該鍵」預設並各進 problems 一句——呼叫端必須出聲，
    「設了沒生效而沒有人知道」是參數檔最容易假交付的一格。
    """
    problems: list[str] = []
    values: list[str] = []
    for key in _KEYS:
        default = _DEFAULTS.get(key, "")
        raw = str(env.get(key) or "").strip()
        if raw and not _acceptable(key, raw):
            names, shown = "／".join(quota_policy.MODEL_FAMILIES), raw[:_SHOWN_MAX]
            back = repr(default) if default else "（空）"
            more = f"；子代理鍵另可填 {INHERIT}" if key == SUBAGENT_ENV else ""
            problems.append(f"{key}={shown!r} 不是合法模型值（要 {names} 別名或含家族字的完整 id，"
                            f"且只含 A-Za-z0-9._[]-{more}）⇒ 採用預設 {back}")
            raw = ""
        values.append(raw or default)
    return ModelRoles(*values), problems


def child_env(roles: ModelRoles) -> dict[str, str]:
    """併進喚醒窗口子行程環境的鍵：子代理預設模型；空或 `inherit`（不注入）就什麼都不加，
    行程既有的 `CLAUDE_CODE_SUBAGENT_MODEL` 原樣保留。"""
    pinned = roles.pinned_subagent
    return {CHILD_ENV_KEY: pinned} if pinned else {}


def model_argv(roles: ModelRoles) -> list[str]:
    """喚醒 argv 的 `--model <主控>`；主控為空＝不帶旗標（沿用存檔／設定鏈）。"""
    return ["--model", roles.helmsman] if roles.helmsman else []


def roles_line(roles: ModelRoles, problems: Sequence[str] = ()) -> str:
    """三角色設定行（一行人話，無縮排無換行；`--pace` 與 SessionStart 簡報共用這一份字面）。"""
    helm = roles.helmsman or "（空＝沿用存檔／設定鏈）"
    sub = f"{INHERIT}（不注入，沿用視窗模型）" if roles.subagent == INHERIT else roles.subagent
    line = (f"模型角色（.env AUTOSDD_MODEL_*）：主控={helm}｜子代理={sub}"
            f"｜降級={roles.downgrade}（主控值只管無人喚醒窗口；互動視窗自己的模型 .env 管不到，"
            "派工請明寫 model:）")
    if problems:
        line += f" ⚠️ 有 {len(problems)} 個設定值不合法、已退回預設：{'；'.join(problems)}"
    return line
