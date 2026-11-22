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
from datetime import datetime, timedelta
from pathlib import Path

from lib import sandbox_scope

from .. import fakeclaude, leases, sched, snapshot
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
    lease_minutes: int = 0  # 宣告的租約上限（分；0＝用 `sandbox_scope.LEASE_MAX`，上限 `LEASE_CAP`，REQ-SE-03）  # noqa: E501


REGISTRY: dict[str, Case] = {}


def case(case_id: str, family: str, *, refs: tuple[str, ...] = (), long: bool = False, sched: bool = False,  # noqa: E501
         lease_minutes: int = 0):
    def deco(fn: Callable[[CaseContext], None]):
        if case_id in REGISTRY:
            raise ValueError(f"重複的案例 id：{case_id}")
        REGISTRY[case_id] = Case(case_id, family, fn, tuple(refs), long, sched, lease_minutes)
        return fn
    return deco


@dataclass
class CaseContext:
    case_id: str
    sandboxes: list[Sandbox] = field(default_factory=list)
    sched_names: list[str] = field(default_factory=list)
    evidences: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    lease_minutes: int = 0
    extra_tokens: list[str] = field(default_factory=list)  # 快照字樣補充（例：正式目標替身 repo 的名稱／sid）  # noqa: E501

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

    # ---- 副作用租約與替身（REQ-SE-03／27／50）----
    def grant_side_effects(self, sb: Sandbox, minutes: int | None = None, window: bool = True) -> datetime:  # noqa: E501
        """授與沙盒租約（預設拒絕，案例當下明示；存 `min(now+minutes, now+min(宣告上限, LEASE_CAP))`）。
        `window=True` 先 `interactive.assert_trusted(sb)`——不過即 `NotTrusted`（判 ENV，不寫身分檔）；
        身分檔 `window=true` 是 D-18 唯一允許「沙盒目標用沙盒外執行檔」的授權（REQ-SE-50）。
        `window=False`＝只授租約（配合假 `claude` 的案例，不碰 F5 信任）。回實際存下的 `allow_until`。"""  # noqa: E501
        from .. import (
            interactive,  # noqa: PLC0415 — lazy：interactive 頂層會 import leases／sandbox
        )
        if window:
            interactive.assert_trusted(sb)
        now = datetime.now().astimezone()
        cap = self.lease_minutes or sandbox_scope.LEASE_MAX
        return sandbox_scope.grant(sb.home, until=now + timedelta(minutes=minutes or cap), now=now,
                                   max_minutes=cap, window=window)

    def fake_claude(self, sb: Sandbox, mode: str = "fail", *, sleep: int | None = None, rc: int | None = None,  # noqa: E501
                    projdir: Path | str | None = None) -> Path:
        """在沙盒家目錄編出假 `claude`（`<家>/bin/claude.exe`）並寫設定檔；回執行檔路徑。預設模式 `fail`。"""  # noqa: E501
        exe = fakeclaude.build(sb.home)
        fakeclaude.configure(sb.home, mode, sleep=sleep, rc=rc, projdir=projdir)
        return exe

    def tokens(self) -> list[str]:
        return snapshot.tokens_for(self.sandboxes, leases.current_run_id()) + self.extra_tokens

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
        """收尾順序（REQ-SE-31／AT-SE-23）：**第一步撤全部沙盒租約**（拆到一半時到點的 job 必被 L1 拒），
        再撤排程、拆行程與目錄、最後收帳上其餘載具暫存（假 claude、探針 log…）。"""  # noqa: E501
        out: list[str] = []
        for sb in self.sandboxes:
            try:
                sandbox_scope.revoke(sb.home)
            except Exception:  # noqa: BLE001 — 身分檔已不在＝沒有租約可撤
                pass
        if self.sched_names:
            out += [f"RESIDUE sched {n}" for n in leases.revoke_run_kinds(("sched_job",))]
        for sb in self.sandboxes:
            out += sb.cleanup()
        out += [f"RESIDUE ledger {i}" for i in leases.revoke_run_kinds(
            ("temp_file", "worktree", "sandbox_root", "transcript_dir"))]
        return out


def discover() -> dict[str, Case]:
    """匯入 cases/*.py（即登記）；回傳登記表。"""
    pkg_dir = str(Path(__file__).parent)
    for m in pkgutil.iter_modules([pkg_dir]):
        importlib.import_module(f"{__name__}.{m.name}")
    return REGISTRY
