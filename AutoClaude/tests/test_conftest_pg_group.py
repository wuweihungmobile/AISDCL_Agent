"""conftest.py 的 pg_serial xdist_group 分群機制回歸鎖（DEF-200-274 D5）。

WHY（Rule 9，測意圖非僅行為）：`pytest_collection_modifyitems` 併入 pg_serial
標記邏輯後，正確性繫於兩個**非顯而易見**的必要條件——(1) 整個函式必須帶
`@pytest.hookimpl(tryfirst=True)`；(2) 標記迴圈必須排在既有「PG 已啟用即早退」的
`return` **之前**。兩者任一被拿掉，分群都會**靜默**失效（rc=0、零警告，只是
「同群測試沒有真的分到同一個 worker」）——純函式層級的單元測試測不出這件事，
必須用 `pytester` 以子行程真跑一次 xdist（見設計 design_xdist.md §2.3 對照實測）。

本檔比照既有 `test_conftest_windows_native_skip_report.py` 的手法：把本套件真實
`tests/conftest.py` 原始碼複製進 pytester 沙盒真跑（而非重新實作一份等價邏輯），
確保鎖住的是生產程式碼本身，不是測試自己編造的替身。
"""
from __future__ import annotations

from pathlib import Path

pytest_plugins = ["pytester"]

_CONFTEST_SOURCE = (Path(__file__).resolve().parent / "conftest.py").read_text(encoding="utf-8")

# 附加在沙盒 conftest.py 尾端：把每一支測試的 nodeid 與其執行所在的 xdist worker id
# 記到一個「每個 worker 各自一份」的檔案（DEF-200-274 D5：不共用同一個檔案 append，
# 避免 Windows 上跨行程同檔並發寫入的檔案鎖疑慮，見根 CLAUDE.md 鐵律三）。
_WORKER_RECORDER = '''

def pytest_runtest_logreport(report):
    """測試專用：記錄每一支測試實際落在哪一個 xdist worker（含 controller 本身）。"""
    if report.when != "call":
        return
    base = os.environ.get("_PG_GROUP_TEST_LOG_BASE")
    if not base:
        return
    worker = os.environ.get("PYTEST_XDIST_WORKER", "controller")
    with open(f"{base}.{worker}", "a", encoding="utf-8") as fh:
        fh.write(report.nodeid + "\\n")
'''


def _write_toy_tree(pytester) -> None:
    (pytester.path / "tests" / "contract").mkdir(parents=True)
    (pytester.path / "tests" / "contract" / "test_c1.py").write_text(
        "def test_c1():\n    pass\n\n\ndef test_c2():\n    pass\n", encoding="utf-8"
    )
    (pytester.path / "tests" / "other").mkdir(parents=True)
    (pytester.path / "tests" / "other" / "test_o1.py").write_text(
        "def test_o1():\n    pass\n\n\ndef test_o2():\n    pass\n", encoding="utf-8"
    )


def test_pg_serial_marker_present_when_pg_enabled(pytester, monkeypatch) -> None:
    """🔴 這支測試專門釘住「早退分支吃掉新邏輯」這個坑：PG 啟用（`_resolve_real_pg_dsn()`
    非 None）時，`tests/contract/` 下的項目仍必須帶 `xdist_group` marker——若標記迴圈
    被搬到既有早退 `return` 之後，本測試必須紅（見模組 docstring）。
    """
    monkeypatch.setenv("SD07_REAL_PG_E2E_ENABLED", "true")
    monkeypatch.setenv("AUTOCLAUDE_TEST_PG_DSN", "postgresql+asyncpg://fake:fake@localhost/fake")
    pytester.makeconftest(
        _CONFTEST_SOURCE
        + '\n\n'
          'def pytest_collection_finish(session):\n'
          '    for item in session.items:\n'
          '        m = item.get_closest_marker("xdist_group")\n'
          '        print(f"MARKER-CHECK {item.nodeid} "\n'
          '              f"{\'YES:\' + str(m.args) if m else \'NO\'}")\n'
    )
    _write_toy_tree(pytester)
    result = pytester.runpytest_subprocess("--collect-only", "-q", "-s")
    out = result.stdout.str()
    assert "MARKER-CHECK tests/contract/test_c1.py::test_c1 YES:('pg_serial',)" in out, out
    assert "MARKER-CHECK tests/contract/test_c1.py::test_c2 YES:('pg_serial',)" in out, out
    # 反方向對照：不在 pg_serial 路徑前綴下的測試不該被誤標
    assert "MARKER-CHECK tests/other/test_o1.py::test_o1 NO" in out, out


def test_pg_serial_grouping_takes_effect_with_dist_loadgroup(
    pytester, monkeypatch, tmp_path
) -> None:
    """真跑 xdist（`--dist loadgroup`）：`tests/contract/` 下的兩支同群測試必須落在
    同一個 worker，且 nodeid 帶 `@pg_serial` 後綴——防止未來任何 refactor 把
    `tryfirst=True` 拿掉又無人發現（拿掉後 rc 仍是 0，唯一的差別是兩支測試散落到
    不同 worker，只有真跑才看得到）。
    """
    log_base = tmp_path / "worker_assign.log"
    monkeypatch.setenv("_PG_GROUP_TEST_LOG_BASE", str(log_base))
    pytester.makeconftest(_CONFTEST_SOURCE + _WORKER_RECORDER)
    _write_toy_tree(pytester)
    result = pytester.runpytest_subprocess(
        "-p", "no:cacheprovider", "-n", "2", "--dist", "loadgroup", "-q",
        "tests/contract", "tests/other",
    )
    result.assert_outcomes(passed=4)
    assigned: dict[str, str] = {}
    for log_file in tmp_path.glob("worker_assign.log.*"):
        worker = log_file.suffix.lstrip(".")
        for nodeid in log_file.read_text(encoding="utf-8").splitlines():
            if nodeid:
                assigned[nodeid] = worker
    c1_id = "tests/contract/test_c1.py::test_c1@pg_serial"
    c2_id = "tests/contract/test_c1.py::test_c2@pg_serial"
    assert c1_id in assigned and c2_id in assigned, assigned
    assert assigned[c1_id] == assigned[c2_id], (
        f"同群（xdist_group pg_serial）測試被分到不同 worker：{assigned}"
    )


# --- DEF-200-274 X1：PG 在場 + xdist 平行 + 非 loadgroup/no ⇒ fail-loud ---

def _pg_env(monkeypatch) -> None:
    monkeypatch.setenv("SD07_REAL_PG_E2E_ENABLED", "true")
    monkeypatch.setenv("AUTOCLAUDE_TEST_PG_DSN", "postgresql+asyncpg://fake:fake@localhost/fake")


def test_pg_present_with_worksteal_dist_fails_loud(pytester, monkeypatch) -> None:
    """PG 在場、`-n`>0、`--dist worksteal`（非 loadgroup/no）⇒ pytest.UsageError，
    不得靜默降級——這是 conftest.py::_reject_pg_present_with_mismatched_xdist_dist
    的存在理由（design_xdist.md 主控追加需求 X1）。
    """
    _pg_env(monkeypatch)
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(test_x="def test_x():\n    pass\n")
    result = pytester.runpytest_subprocess("-n", "2", "--dist", "worksteal", "-q")
    assert result.ret == 4, (result.ret, result.stdout.str())  # ExitCode.USAGE_ERROR
    out = result.stdout.str() + result.stderr.str()
    assert "PG 在場但未用 --dist loadgroup" in out, out
    assert "--dist loadgroup" in out, out


def test_pg_present_with_dist_loadgroup_does_not_raise(pytester, monkeypatch) -> None:
    """反向對照：同樣 PG 在場，但呼叫端已用 --dist loadgroup ⇒ 正常跑完（鑑別力來源）。"""
    _pg_env(monkeypatch)
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(test_x="def test_x():\n    pass\n")
    result = pytester.runpytest_subprocess("-n", "2", "--dist", "loadgroup", "-q")
    result.assert_outcomes(passed=1)


def test_pg_present_with_n_zero_does_not_raise(pytester, monkeypatch) -> None:
    """PG 在場但 `-n 0`（停用平行）⇒ 不誤擋（numprocesses 為 0/falsy 時直接放行）。"""
    _pg_env(monkeypatch)
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(test_x="def test_x():\n    pass\n")
    result = pytester.runpytest_subprocess("-n", "0", "-q")
    result.assert_outcomes(passed=1)


def test_no_pg_with_worksteal_dist_does_not_raise(pytester, monkeypatch) -> None:
    """反向對照：沒有 PG 在場時，即使 `-n auto --dist worksteal` 也不該被本判準攔下
    （本 repo 絕大多數呼叫端的常態）。"""
    monkeypatch.delenv("SD07_REAL_PG_E2E_ENABLED", raising=False)
    monkeypatch.delenv("AUTOCLAUDE_TEST_PG_DSN", raising=False)
    monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(test_x="def test_x():\n    pass\n")
    result = pytester.runpytest_subprocess("-n", "2", "--dist", "worksteal", "-q")
    result.assert_outcomes(passed=1)
