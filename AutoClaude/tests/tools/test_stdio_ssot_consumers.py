"""AutoClaude/tools 的 CLI 與 stdio UTF-8 唯一實作（`init_utf8_streams`）的關係鎖。

唯一實作住 monorepo 根 `tools/lib/`（`tools/_stdio_utf8.py` 檔頭有完整理由）。兩條契約：

[A] 覆蓋棘輪：每支帶 `__main__` 的 CLI 都必須接唯一實作，或列在 `_UNPROTECTED_CLIS`
    （shrink-only）。WHY：Windows cp950 主控台上 print 非 cp950 字元（✅／≥）會
    UnicodeEncodeError，POSIX CI 永遠看不到，只能以原始碼結構釘。名單是「靜態掃描輸出
    字面皆 cp950 可編碼」的 CLI（動態輸出未驗證）；新增 CLI 一律接唯一實作、不准入名單。
    名單同時鎖住「已收斂的消費者不得退回行內複本或被刪掉呼叫」（行內複本的數量棘輪在根層
    tools/tests/test_platform_utils_dedup.py 的 per-tree 棘輪）。
[B] 容器隔離：mock_brain_server.py 與 mutation_analysis.py 會被丟進只有 AutoClaude 子樹的
    容器（docker-compose.llm.yml 只掛 `./tools` 進 python:3.11-slim；run_mutmut_in_docker.sh
    在 `/workspace`＝AutoClaude 內呼叫），沒有 monorepo 根可 import，所以寫成「根在就用、
    不在就略過」。有人把守衛「簡化」成硬 import 時 CI 不跑這兩條容器路徑、會靜默壞掉；
    本鎖把「單獨複製到無根目錄後可執行」釘成測試（--help 先走 main 前導、再由 argparse
    以 rc=0 結束）。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
_MAIN_RE = re.compile(r"""^if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.M)
_SSOT_RE = re.compile(r"init_utf8_streams|import\s+_stdio_utf8")

# shrink-only：尚未接唯一實作的 CLI。收斂一支就自此刪除（下方自緊測試強制）。
_UNPROTECTED_CLIS = frozenset({
    "_backfill_emit_real.py", "_check_claude_md.py", "_compute_sha.py",
    "ac4_nightly_collector.py", "drift_log_snapshot.py", "mutation_baseline_lock.py",
    "mutmut_cache_counts.py", "mutmut_counts_parser.py", "mutmut_exit_code.py",
    "observability_snapshot.py", "perf_baseline_lock.py", "setup_pg_runtime_role.py",
    "tree_state.py",
})


def _unprotected_clis(tools_dir: Path = _TOOLS) -> set[str]:
    out: set[str] = set()
    for p in sorted(tools_dir.glob("*.py")) + sorted((tools_dir / "hooks").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        if _MAIN_RE.search(src) and not _SSOT_RE.search(src):
            out.add(p.relative_to(tools_dir).as_posix())
    return out


def test_no_new_cli_without_the_stdio_ssot():
    new = _unprotected_clis() - _UNPROTECTED_CLIS
    assert not new, (
        f"帶 __main__ 的 CLI 未接 stdio UTF-8 唯一實作：{sorted(new)}；"
        "修法＝`from platform_utils import init_utf8_streams`（見 snapshot_sync.py）並在入口呼叫"
    )


def test_unprotected_list_is_tight():
    """自緊：收斂掉一支卻沒自名單刪除 ⇒ 餘裕就是破口。"""
    assert _unprotected_clis() == set(_UNPROTECTED_CLIS)


def test_coverage_scan_has_teeth(tmp_path):
    """鎖的自證：掃描面若瞎了（恆回空），上面兩條就是恆綠的假鎖。"""
    (tmp_path / "hooks").mkdir()
    main = "if __name__ == '__main__':\n    pass\n"
    guarded = "import platform_utils\n" + main.replace("pass", "platform_utils.init_utf8_streams()")
    files = {"bare.py": main, "ok.py": guarded, "lib_only.py": "x = 1\n", "hooks/h.py": main}
    for rel, text in files.items():
        (tmp_path / rel).write_text(text, encoding="utf-8")
    assert _unprotected_clis(tmp_path) == {"bare.py", "hooks/h.py"}


@pytest.mark.parametrize("script", ["mock_brain_server.py", "mutation_analysis.py"])
def test_container_script_runs_alone_without_monorepo_root(script, tmp_path):
    box = tmp_path / "workspace" / "tools"  # 往上兩層沒有 tools/lib：與容器內佈局同構
    box.mkdir(parents=True)
    shutil.copy(_TOOLS / script, box / script)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    done = subprocess.run(
        [sys.executable, str(box / script), "--help"],
        capture_output=True, encoding="utf-8", errors="replace",
        cwd=str(tmp_path), env=env, check=False,
    )
    assert done.returncode == 0, (
        f"{script} 單獨執行失敗（rc={done.returncode}）：{done.stderr[-400:]}"
    )
