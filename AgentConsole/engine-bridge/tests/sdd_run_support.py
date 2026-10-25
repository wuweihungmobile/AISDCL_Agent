"""SDD 批次測試的共用夾具內容與輔助函式（test_sdd_run*.py、test_rtm.py、
test_sdd_integration_parity.py）。

整套流程用「真引擎＋mock claude＋假 SDD 樹」：引擎真的被起來、PRE_RUN 的 SDD 治理真的載入規格、
mock claude 回放驗收關鍵字；FSM 這一側由 tests/fake_sdd.py 的假 CLI 扮演（真 CLI 的對拍在整合步
驟）。
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from tests.fake_sdd import read_calls, read_state, seed_state

TOKEN = "run-sdd-token-" + "r" * 32
FSM_REL = Path("build") / "reports" / "fsm"
CONTRACTS_REL = Path("docs") / "03_testing" / "contracts"
TCS_NAME = "TCS-Alpha-20261017.md"
TCS_REL = f"{CONTRACTS_REL.as_posix()}/{TCS_NAME}"

#: 官方模板格式的最小 TCS：兩個 AT（同屬 AC-001-1）、Gherkin 的 Then 引號字面值取替身必然回放的
#: `[AT_OK_n]`。
TCS_TEXT = """# Test Contract Specification — Alpha

**spec-format-version**: 1.0
**scenario**: greenfield

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 第一個驗收 | AT-001-1-1 | 第一個 | ✅ | Unit | □ |
| AC-001-1 | 第一個驗收 | AT-001-1-2 | 第二個 | ✅ | Unit | □ |

## 2. AT 格式

```gherkin
# AT-001-1-1
Scenario: 第一個
  Given 系統就緒
  When 執行
  Then 輸出 "[AT_OK_1]"
```

```gherkin
# AT-001-1-2
Scenario: 第二個
  Given 系統就緒
  When 執行
  Then 輸出 "[AT_OK_2]"
```
"""


def digest_of(text: str) -> str:
    """獨立於產品碼的摘要算法（ADR §4.3）：換行正規化後的 UTF-8 文字的 sha256。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def make_project(parent: Path, name: str = "alpha", text: str = TCS_TEXT) -> Path:
    """專案根（須在 allowed roots 之下）：規格放在 docs/03_testing/contracts/。"""
    root = parent / name
    (root / CONTRACTS_REL).mkdir(parents=True)
    (root / CONTRACTS_REL / TCS_NAME).write_text(text, encoding="utf-8", newline="")
    return root


def contracts_dir(root: Path) -> Path:
    return root / CONTRACTS_REL


def seed_frozen(root: Path, current_state: str = "SPEC_FROZEN", *, key: str = "alpha",
                digests: bool = True, text: str = TCS_TEXT, stage_digest: str | None = None,
                **fsm: Any) -> Path:
    """扮演「人在 SDD session 把專案推到某個狀態、並已核准凍結」。`digests=False`＝舊狀態檔（凍結
    時沒帶--digest，沒有 `spec_doc_digests`）；`stage_digest` 可蓋掉摘要值（模擬凍結後規格被
    改）。"""
    stage: dict[str, Any] = {"stage": "Stage-1", "frozen_at": "2026-10-17T00:00:00+00:00",
                             "compaction_report": None, "spec_docs": [TCS_REL]}
    if digests:
        stage["spec_doc_digests"] = {TCS_REL: stage_digest or digest_of(text)}
        stage["approved_by"] = "operator"
    return seed_state(root / FSM_REL, key, current_state, frozen_stages=[stage], **fsm)


def make_tasks(spec_digest: str | None, *, fail_step: int | None = None,
               count: int = 2) -> list[dict[str, Any]]:
    """SDD 編譯任務的樣子：step_id＝`sdd-<場景>-<at 小寫>`、name＝AT id、帶匯入時的 `spec_digest`。
    `fail_step`（1 起算）的 prompt 含 FORCE_FAIL（配 MOCK_CLAUDE_FAIL_REGEX 讓那一步必然失敗＝引擎
    升級）。"""
    tasks = []
    for n in range(1, count + 1):
        prompt = f"依契約實作並輸出 [AT_OK_{n}]" + (" FORCE_FAIL" if n == fail_step else "")
        task: dict[str, Any] = {
            "step_id": f"sdd-greenfield-at-001-1-{n}", "name": f"AT-001-1-{n}", "prompt": prompt,
            "expected_output_regex": rf"\[AT_OK_{n}\]", "max_retries": 1,
            "maintain_context": n % 2 == 0}
        if spec_digest is not None:
            task["spec_digest"] = spec_digest
        tasks.append(task)
    return tasks


def make_playbook(spec_digest: str | None, *, project: str = "SddDemo",
                  fail_step: int | None = None, count: int = 2) -> dict[str, Any]:
    return {"version": "1.0", "project": project, "global_goal": "SDD 批次整合測試",
            "global_invariants": {"max_retries_per_step": 1, "auto_compact_interval": 0},
            "tasks": make_tasks(spec_digest, fail_step=fail_step, count=count)}


def sdd_block(root: Path, *, key: str = "alpha", spec_file: str | None = None,
              approver: str | None = "operator", with_root: bool = True,
              spec_dir: Path | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {"spec_dir": str(spec_dir or contracts_dir(root)), "fsm_project": key}
    if spec_file is not None:
        block["spec_file"] = spec_file
    if with_root:
        block["root"] = str(root)
    if approver is not None:
        block["approver"] = approver
    return block


def sdd_body(run_body, root: Path, *, digest: str | None = None, sdd: dict[str, Any] | None = None,
             fail_step: int | None = None, delay: str = "0.2", project: str = "SddDemo",
             execution_path: Path | None = None, env: dict[str, str] | None = None,
             run_id: str | None = None, count: int = 2) -> dict[str, Any]:
    """`POST /autoclaude/runs` 的 body（含 `sdd`）。`digest` 省略＝現檔的摘要（三點摘要的匯入那一
    點）。"""
    spec_digest = digest_of(TCS_TEXT) if digest is None else digest
    merged_env = dict(env or {})
    if fail_step is not None:
        merged_env.setdefault("MOCK_CLAUDE_FAIL_REGEX", "FORCE_FAIL")
    body = run_body(playbook=make_playbook(spec_digest, project=project, fail_step=fail_step,
                                           count=count),
                    delay=delay, execution_path=execution_path or root, project=project,
                    env=merged_env, run_id=run_id)
    body["sdd"] = sdd if sdd is not None else sdd_block(root)
    return body


def post(live, body: dict[str, Any], *, token: str | None = TOKEN, trace: str | None = None):
    headers = {}
    if token is not None:
        headers["X-Bridge-Token"] = token
    if trace is not None:
        headers["X-Trace-Id"] = trace
    return live.client.post("/autoclaude/runs", json=body, headers=headers)


def verbs(fake: Path) -> list[str]:
    return [c["verb"] for c in read_calls(fake)]


def argv_of(fake: Path, verb: str, nth: int = 0) -> list[str]:
    return [c for c in read_calls(fake) if c["verb"] == verb][nth]["argv"]


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def fsm_state(root: Path, key: str = "alpha") -> dict[str, Any]:
    return read_state(root / FSM_REL, key)


def wait_fsm(root: Path, wanted: set[str] | str, *, key: str = "alpha",
             timeout: float = 45.0) -> dict[str, Any]:
    """輪詢到 FSM 的 current_state 屬於 wanted（終態同步在終態事件之後約 0.1～0.5 秒，不能單次
    讀）。"""
    targets = {wanted} if isinstance(wanted, str) else set(wanted)
    deadline = time.monotonic() + timeout
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = fsm_state(root, key)
        if state["current_state"] in targets:
            return state
        time.sleep(0.1)
    raise AssertionError(f"FSM 在 {timeout:g}s 內沒有到達 {sorted(targets)}；現況："
                         f"{state.get('current_state')}")


def wait_sync(run_dir: Path, *, timeout: float = 20.0) -> dict[str, Any]:
    """輪詢 `<run_dir>/run.json` 到 `sdd.sync` 落盤，回傳整份紀錄。

    終態同步在終態事件**之後**，而且 Bridge 的順序是「CLI 寫完 FSM → 記 sync → persist」
    （runner `_finalize` → `_sdd_sync_terminal` → `_record_sdd_sync`）：run 已終態、FSM 已回到
    IMPLEMENTATION 的那一刻，run.json 的 sync 仍可能是 None（雲端 runner 慢時真的讀到過），
    不能單次讀。替換中的 run.json 偶爾讀到半檔也只當「還沒好」再讀一次。"""
    deadline = time.monotonic() + timeout
    record: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            record = {}
        if (record.get("sdd") or {}).get("sync") is not None:
            return record
        time.sleep(0.05)
    raise AssertionError(f"{timeout:g}s 內 run.json 的 sdd.sync 沒有落盤；現況："
                         f"{record.get('sdd')}")


def audit_entries(live) -> list[dict[str, Any]]:
    import json

    path = live.settings.engine_workspace / "_audit.jsonl"
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def wait_audit(live, ready, *, timeout: float = 20.0) -> list[dict[str, Any]]:
    """輪詢 `_audit.jsonl` 直到 `ready(entries)` 為真，回傳當時的全部稽核列。

    `sdd_cli` 稽核列在 CLI 子行程**結束之後**才追加，而 FSM 狀態檔是子行程在跑的時候就寫好：
    `wait_fsm` 回到 IMPLEMENTATION 的那一刻，`delegate-exit` 那一列可能還沒落地（雲端 runner
    2026-10-26 真的讀到只剩 `delegate-enter` 一列），所以稽核斷言不能緊接著單次讀。"""
    deadline = time.monotonic() + timeout
    entries: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        entries = audit_entries(live)
        if ready(entries):
            return entries
        time.sleep(0.1)
    raise AssertionError(f"稽核檔在 {timeout:g}s 內沒有到齊；現有事件："
                         f"{[(e.get('event'), e.get('verb')) for e in entries]}")


def trace_calls(trace: Path) -> list[dict[str, Any]]:
    import json

    if not trace.is_file():
        return []
    rows = [json.loads(x) for x in trace.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [r for r in rows if r["keywords"]]


def workspace_has(live, run_id: str) -> bool:
    return (live.settings.engine_workspace / run_id).exists()


def sdd_context(root: Path, *, key: str = "alpha", approver: str = "operator"):
    """`RunRecord.sdd` 對應的已驗證路徑與身分（與 `RunManager` 建立 run 時算出的同一形狀）。"""
    from app.sdd_run import SddContext

    return SddContext(
        spec_dir=contracts_dir(root).resolve(), spec_file=None, fsm_project=key,
        root=root.resolve(), state_dir=(root / FSM_REL).resolve(), approver=approver)


def build_handle(settings, tmp: Path, *, sdd: dict[str, Any] | None, status: str = "RUNNING",
                 env: dict[str, str] | None = None):
    """不起任何引擎的 `RunHandle`（直接驅動 `_sdd_sync_terminal`、補償與子行程環境用）。
    回傳 (manager, handle)；run 目錄在 `settings.engine_workspace/<run_id>/`，稽核檔在
    `tmp/audit.jsonl`。"""
    import uuid

    from app.locks import AdvisoryLock
    from app.runner import RunHandle, RunManager
    from app.runstate import RunPaths, RunRecord
    from app.security import AuditLog

    mgr = RunManager(settings, locks=AdvisoryLock(None), audit=AuditLog(tmp / "audit.jsonl"))
    run_id = str(uuid.uuid4())
    paths = RunPaths(settings.engine_workspace / run_id)
    paths.run_dir.mkdir(parents=True)
    paths.playbook.write_text("tasks: []\n", encoding="utf-8", newline="\n")
    rec = RunRecord(run_id=run_id, project="parity", execution_path=str(tmp), status=status,
                    sdd=sdd)
    handle = RunHandle(mgr, rec, paths, [], request_env=env)
    handle.persist()
    return mgr, handle


def alert_codes(handle) -> list[str]:
    """這個 handle 事件環裡所有 alert 的代碼（依序）。"""
    return [e["code"] for e in handle.store.replay(0, 5000) if e["event"] == "alert"]


def events_of(live, run_id: str, kind: str) -> list[dict[str, Any]]:
    return [e for e in live.events(run_id) if e["event"] == kind]
