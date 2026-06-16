"""DEF-02-001 跨版 pytest 同跑 fail-loud guard 回歸測試（AutoSDD_improving_05 W1）.

WHY：guard 的存在價值是把「單一 process 跨版同跑」這個 Copy-on-Evolve 結構性不可支援的
誤用，從 cryptic ``ImportPathMismatchError`` 轉為可行動訊息（Rule 12 Fail-Loud）。下列測試
鎖定偵測「意圖」：缺任一斷言 = guard 失能（多版漏報 / 單版誤觸 / 訊息不可行動）。
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
SDD_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))  # AISDLC_SDD/
sys.path.insert(0, os.path.join(SDD_ROOT, "scripts"))

from cross_version_guard import build_guard_message, versions_touched  # noqa: E402


# ---- 純函式：偵測意圖 ----------------------------------------------------------

def test_two_version_paths_detect_both():
    """兩個不同版本路徑 → 偵測到兩版（guard 將 fire）。WHY：跨版同跑必須被攔。"""
    vs = versions_touched(
        ["AISDLC_SDD_v0.03/tools/fsm_runtime/tests",
         "AISDLC_SDD_v0.04/tools/fsm_runtime/tests"],
        SDD_ROOT,
    )
    assert vs == {"AISDLC_SDD_v0.03", "AISDLC_SDD_v0.04"}


def test_single_version_path_detects_one():
    """單一版本路徑 → 只一版（len==1，guard 不 fire）。WHY：正常單版用法不可誤觸。"""
    vs = versions_touched(["AISDLC_SDD_v0.04/tools/fsm_runtime/tests"], SDD_ROOT)
    assert vs == {"AISDLC_SDD_v0.04"}


def test_non_version_path_detects_none():
    """非版本路徑（如 scripts/tests）→ 空集（guard 不 fire）。WHY：共享 infra 自測不可被擋。"""
    vs = versions_touched(["scripts/tests"], SDD_ROOT)
    assert vs == set()


def test_nodeid_with_colons_not_false_positive(tmp_path):
    """pytest 單一測試 nodeid（``path::test``）含 :: → 剝除後判路徑，不誤觸跨版 guard。

    WHY（DEF-12-002）：從 REPO_ROOT 跑 ``pytest 檔案.py::test_y`` 取突變證據時，token 含
    ``::`` 使 ``os.path.exists`` 為 False → 舊碼誤判「無路徑 arg」→ 走 bare 分支展開
    cwd 下全部版本 → 誤報跨版 UsageError。修後須回傳空集（不 fire）。退化即紅。
    """
    (tmp_path / "AISDLC_SDD_v0.12").mkdir()
    (tmp_path / "AISDLC_SDD_v0.13").mkdir()
    (tmp_path / "smoke.py").write_text("def test_x(): pass\n", encoding="utf-8")
    vs = versions_touched(["smoke.py::test_x"], str(tmp_path))
    assert vs == set(), f"單一非版本 nodeid 不該展開版本目錄，實得 {vs}（DEF-12-002 回歸）"


def test_versioned_nodeid_still_detects_version(tmp_path):
    """版本路徑帶 nodeid（``v0.12/x.py::test``）→ 仍正確偵測該版（剝 :: 不傷版本偵測）。

    WHY：DEF-12-002 修法只剝 :: 判存在，版本片段由 VERSION_RE 涵蓋，不可因修法漏掉真跨版。
    """
    vs = versions_touched(
        ["AISDLC_SDD_v0.12/tools/fsm_runtime/tests/test_x.py::test_y"],
        str(tmp_path),
    )
    assert vs == {"AISDLC_SDD_v0.12"}


def test_flags_and_option_values_ignored():
    """旗標與選項值（-m 'not chaos'）不得被當路徑，只認真正的版本路徑。

    WHY：避免把 ``not chaos`` 之類選項值誤判為路徑而擾亂版本集合判定。
    """
    vs = versions_touched(
        ["-q", "-m", "not chaos", "AISDLC_SDD_v0.04/tools/fsm_runtime/tests"],
        SDD_ROOT,
    )
    assert vs == {"AISDLC_SDD_v0.04"}


def test_bare_no_path_args_expands_cwd(tmp_path):
    """無任何路徑 arg（bare 呼叫）→ 展開 cwd 下所有版本目錄。

    WHY：``cd AISDLC_SDD && pytest`` 是最常見 footgun，必須由 cwd 展開偵測到多版。
    """
    (tmp_path / "AISDLC_SDD_v0.04").mkdir()
    (tmp_path / "AISDLC_SDD_v0.05").mkdir()
    (tmp_path / "scripts").mkdir()  # 非版本目錄，不應計入
    vs = versions_touched([], str(tmp_path))
    assert vs == {"AISDLC_SDD_v0.04", "AISDLC_SDD_v0.05"}


def test_bare_with_only_flags_still_expands_cwd(tmp_path):
    """只有旗標、無路徑（如 ``pytest -m 'not chaos'`` from root）仍須展開 cwd。

    WHY：選項值被正確忽略後，path_args 為空 → 走 bare 展開，否則此 footgun 漏報。
    """
    (tmp_path / "AISDLC_SDD_v0.01").mkdir()
    (tmp_path / "AISDLC_SDD_v0.04").mkdir()
    vs = versions_touched(["-m", "not chaos"], str(tmp_path))
    assert vs == {"AISDLC_SDD_v0.01", "AISDLC_SDD_v0.04"}


def test_message_is_actionable():
    """fail-loud 訊息必含 DEF-02-001、觸及版本名、與正確用法。WHY：Rule 12 可行動性。"""
    msg = build_guard_message({"AISDLC_SDD_v0.04", "AISDLC_SDD_v0.05"})
    assert "DEF-02-001" in msg
    assert "AISDLC_SDD_v0.04" in msg and "AISDLC_SDD_v0.05" in msg
    assert "cd <version>" in msg or "ci-gate.sh" in msg


# ---- 整合煙霧：guard 實際接線於 conftest ----------------------------------------

def test_bare_pytest_from_root_fires_guard():
    """端到端：從 AISDLC_SDD 根 bare 跑 pytest → guard fail-loud（早於 collection）。

    WHY：證明 conftest.py 的 pytest_configure 真的接上純函式並 raise；
    退化（conftest 未載/未 raise）此測試立即紅。
    """
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--co", "-q"],
        cwd=SDD_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode != 0, f"bare pytest 竟成功收集，guard 失能：\n{out}"
    assert "DEF-02-001" in out, f"guard 訊息未出現：\n{out}"
