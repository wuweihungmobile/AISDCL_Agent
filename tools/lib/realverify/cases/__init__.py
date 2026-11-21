"""案例登記與自動發現：`cases/*.py` 內以 `@case(...)` 裝飾的函式在 `discover()`
時自動登記（多包並行不搶登記檔）。

案例函式簽名 `fn(ctx: CaseContext) -> None`：不 raise＝過；`ctx.check(False,
"…")`／AssertionError＝失敗；
`EnvMissing`＝環境缺件（runner 回 rc 2）。案例 id 取 `RV-<家族字母><序號>`，並在
`docs/06_quality/RealVerify_Protocol/cases.json` 登記對應的 V／AT／DEF。
"""

from __future__ import annotations

import importlib
import pkgutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .. import leases, sched
from ..driver import RunResult, run_claude
from ..sandbox import Sandbox, kept_dir
from ..transcript import Transcript


class CaseFail(AssertionError):
    pass


@dataclass(frozen=True)
class Case:
    id: str
    family: str
    fn: Callable[[CaseContext], None]
    refs: tuple[str, ...] = ()
    long: bool = False  # 長等案例（如保溫 55 分鐘）：只在 --long／nightly 跑
    uses_sched: bool = False  # 用真 schtasks：runner 以全域鎖串行


REGISTRY: dict[str, Case] = {}


def case(case_id: str, family: str, *, refs: tuple[str, ...] = (), long: bool = False, sched: bool = False):  # noqa: E501
    def deco(fn: Callable[[CaseContext], None]):
        if case_id in REGISTRY:
            raise ValueError(f"重複的案例 id：{case_id}")
        REGISTRY[case_id] = Case(case_id, family, fn, tuple(refs), long, sched)
        return fn
    return deco


@dataclass
class CaseContext:
    case_id: str
    sandboxes: list[Sandbox] = field(default_factory=list)
    sched_names: list[str] = field(default_factory=list)
    evidences: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # ---- 建構 ----
    def sandbox(self, probe_hooks: bool = True) -> Sandbox:
        """建沙盒（repo 外、git init、含探針 hook 檔）；`probe_hooks=True` 另把探針掛上 SessionStart／UserPromptSubmit／Stop。"""  # noqa: E501
        sb = Sandbox.create()
        self.sandboxes.append(sb)
        if probe_hooks:
            sb.add_probe_hooks()
        return sb

    def run_claude(self, sb: Sandbox, prompt: str, **kw) -> RunResult:
        return run_claude(sb, prompt, **kw)

    def transcript(self, sb: Sandbox) -> Transcript:
        return Transcript.for_sid(sb.sid)

    def sched_register(self, name: str, run_at_local_iso: str, arguments: str) -> dict:
        n = sched.rv_name(name)
        self.sched_names.append(n)
        return leases.register_once(n, run_at_local_iso, arguments)

    def sched_track(self, name: str) -> str:
        """被測產品代為註冊排程時（案例只知道名字）：**註冊前**先把名字記上租約帳，收尾由帳撤銷。"""
        n = leases.track(name)
        self.sched_names.append(n)
        return n

    # ---- 斷言／證據 ----
    def check(self, cond: bool, msg: str) -> None:
        if not cond:
            raise CaseFail(msg)

    def evidence(self, text: str) -> None:
        self.evidences.append(text)

    def keep_failure_evidence(self, base: Path | None = None, stamp: str | None = None) -> str:
        """案例判失敗時、清理前呼叫：把每個沙盒的逐字稿／hook 輸出複製到持久目錄；回保留路徑
        （沒有可留的沙盒或複製失敗 ⇒ `""`，失敗原因照舊由案例自己的訊息報，不吞）。"""
        root = (base or kept_dir()) / f"{self.case_id}_{stamp or time.strftime('%Y%m%dT%H%M%S')}"
        kept = False
        for i, sb in enumerate(self.sandboxes):
            try:
                kept = bool(sb.preserve(root / f"sandbox{i}_{sb.sid[:8]}")) or kept
            except OSError as e:
                self.notes.append(f"保留證據失敗（sandbox{i}）：{e}")
        return str(root) if kept else ""

    # ---- 收尾（runner 的 finally 呼叫；案例本身不用管）----
    def close(self) -> list[str]:
        out: list[str] = []
        if self.sched_names:
            out += [f"RESIDUE sched {n}" for n in leases.revoke_run()]
        for sb in self.sandboxes:
            out += sb.cleanup()
        return out


def discover() -> dict[str, Case]:
    """匯入 cases/*.py（即登記）；回傳登記表。"""
    pkg_dir = str(Path(__file__).parent)
    for m in pkgutil.iter_modules([pkg_dir]):
        importlib.import_module(f"{__name__}.{m.name}")
    return REGISTRY
