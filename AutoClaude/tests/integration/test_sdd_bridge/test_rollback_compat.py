"""三專家審查 P1-1（AutoSDD_improving_01 §6 規則 4）：版本回退相容驗證。

EVOLUTION_LOG 回退指引的可執行落地：config 指回 AISDLC_SDD_v0.01（或留在
v0.02）後，AutoClaude 端 `sdd_compile` 必須仍可消費該版本「真品」FSM 狀態檔。

「真品」定義：不以手寫 dict 偽造，而是以 **subprocess** 在該版本目錄為 cwd
執行小腳本，呼叫該版本自己的 `tools.fsm_runtime.state_loader`
（load_state → FSMState.record_spec_frozen → save_state）在 pytest tmp_path
下產出 FSM-STATE yaml，再由主行程 `autoclaude.tools.sdd_compile.compile_spec`
消費並斷言編譯出 3 步驟。

整合閘門掛載點：根層 `tools/integration_gate.ps1` [4/5] 回退驗證段。
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from autoclaude.tools.sdd_compile import compile_spec
from tests.infra.test_sdd_to_playbook_adapter import _SPEC_MD, _write_spec

# 本檔位於 AutoClaude/tests/integration/test_sdd_bridge/ → parents[4] = monorepo 根
_MONOREPO_ROOT = Path(__file__).resolve().parents[4]
_SDD_ROOT = _MONOREPO_ROOT / "AISDLC_SDD"

# 該版本 state_loader 的真實 API（v0.01/v0.02 經 diff 驗證同源）：
#   load_state(project, path=..., create_if_missing=True) -> FSMState
#   FSMState.record_spec_frozen(stage, spec_docs)
#   save_state(state)   ← 存檔 API 實名（state_loader.py 模組級函式）
_STATE_SCRIPT = textwrap.dedent("""\
    import sys
    from pathlib import Path

    from tools.fsm_runtime import state_loader

    target = Path(sys.argv[1])
    state = state_loader.load_state(
        "rollback", path=target, create_if_missing=True)
    state.current = "SPEC_FROZEN"
    state.record_spec_frozen(
        "SCG-3",
        ["docs/03_testing/contracts/TEST-CONTRACT-SPEC-Demo.md"],
    )
    state_loader.save_state(state)
    print(state.path)
""")


def _produce_real_fsm_state(version_dir: Path, tmp_path: Path) -> Path:
    """以 subprocess 用該版本自己的 state_loader 產出真品 FSM-STATE yaml。"""
    state_path = tmp_path / "build" / "reports" / "fsm" / "FSM-STATE-rollback.yaml"
    proc = subprocess.run(
        [sys.executable, "-c", _STATE_SCRIPT, str(state_path)],
        cwd=str(version_dir),  # 以該版本目錄為 cwd → import 該版本的 tools.fsm_runtime
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"{version_dir.name} 的 state_loader 產出 FSM 狀態失敗（rc={proc.returncode}）\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert state_path.is_file(), f"真品 FSM 狀態檔未落地：{state_path}"
    return state_path


@pytest.mark.parametrize(
    "version",
    ["AISDLC_SDD_v0.01", "AISDLC_SDD_v0.02"],
    ids=["rollback_to_v001", "forward_v002"],
)
def test_rollback_version_real_fsm_state_spec_compiles(version, tmp_path):
    """真實版本回退相容：該版本 state_loader 真品狀態檔 → sdd_compile 3 步驟。"""
    version_dir = _SDD_ROOT / version
    if not version_dir.is_dir():
        pytest.skip(
            f"{version_dir} 不存在（非 monorepo 佈局，無姊妹專案可驗回退）"
        )

    # 1. 真品 FSM 狀態（該版本 state_loader 親手產出，非手寫偽造）
    state_path = _produce_real_fsm_state(version_dir, tmp_path)
    doc = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    root = doc["fsm_state"]
    assert root["current_state"] == "SPEC_FROZEN"
    assert root["frozen_stages"] and root["frozen_stages"][0]["stage"] == "SCG-3"
    # 模板衍生欄位存在 → 證明走的是該版本模板（真品），不是最小手寫 stub
    assert root["project"] == "rollback"

    # 2. 放入 TEST-CONTRACT-SPEC fixture（復用 adapter 單測之 _SPEC_MD）
    spec_dir = _write_spec(tmp_path, text=_SPEC_MD)

    # 3. 主行程 compile_spec 消費（adapter 自 spec_dir 向上找到真品狀態檔）
    playbook = compile_spec(str(spec_dir))
    assert len(playbook.tasks) == 3, (
        f"{version} 真品 FSM 狀態下應編譯出 3 條 AT 契約步驟，"
        f"實得 {len(playbook.tasks)}"
    )
    assert [t.step_id for t in playbook.tasks] == [
        "sdd-brownfield-at-001-1-1",
        "sdd-brownfield-at-001-1-2",
        "sdd-brownfield-at-002-1-1",
    ]
