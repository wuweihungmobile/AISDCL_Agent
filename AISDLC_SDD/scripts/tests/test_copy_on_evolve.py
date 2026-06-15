"""DEF-11-001 Copy-on-Evolve 安全複製 helper 的意圖鎖（Rule 9：測 WHY 非僅 WHAT）。

WHY：
DEF-11-001（P3）= 官方 UPGRADE_SOP §2.1 `cp -r` 整碗複製會把 runtime 產物
（build/reports/、arch-fitness.json、chaos-report.json、__pycache__/*.pyc）一併夾帶
入 Copy-on-Evolve commit（would-add 1013 含 173 build/reports）。系統性修復＝通用
`scripts/copy_on_evolve.sh` helper，以 tar --exclude 在「複製前」剔除 runtime 產物。
本測試鎖定該 helper 的**排除/保留意圖**，使其退化即紅：

  1. **排除 runtime 產物**：build/reports/（含巢狀）、arch-fitness.json、chaos-report.json、
     任意深度 __pycache__/ 與 *.pyc/*.pyo——複製後**必不存在**於目標。
     （把 helper 的 --exclude 拿掉任一條，對應 assert 即紅。）
  2. **保留真源碼**：agent/、build/planning/、build/logs/README.md、一般 .py/.yaml/.md——
     複製後**必存在**。（防「排除過頭」誤殺源碼。）
  3. **拒絕覆蓋**：目標已存在 → exit 1（保護既有版本，對齊 SOP「不可覆蓋」）。
  4. **參數/來源防呆**：參數數不對 → exit 2；來源不存在 → exit 1。

路徑策略：測試 fixture 建於**與 REPO_ROOT 同碟**的暫存目錄，全程以「相對 REPO_ROOT」
的 posix 路徑（forward slash、無 drive-letter）傳入 bash——避開 Windows 絕對路徑經
subprocess→bash.exe 的掛載點差異（Git usr/bin bash 用 /mnt/c、其他用 /c）與反斜線
被吃問題。helper 實際使用本就走相對路徑（`scripts/copy_on_evolve.sh v0.05 v0.06`）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# scripts/tests/ → scripts/ → AISDLC_SDD（REPO_ROOT）
REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "copy_on_evolve.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("tar") is None,
    reason="copy_on_evolve.sh 為 bash 腳本且依賴 GNU tar",
)


@pytest.fixture
def work():
    """與 REPO_ROOT 同碟的暫存工作目錄（使相對路徑可跨 src/dst/script 通用）。"""
    d = Path(tempfile.mkdtemp(prefix=".coe_tmp_", dir=str(REPO_ROOT)))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _rel(p: Path) -> str:
    """轉為相對 REPO_ROOT 的 posix 路徑（bash-flavor 無關）。"""
    return Path(os.path.relpath(p, REPO_ROOT)).as_posix()


def _run(*args: Path | str) -> subprocess.CompletedProcess:
    norm = [_rel(a) if isinstance(a, Path) else a for a in args]
    return subprocess.run(
        ["bash", "scripts/copy_on_evolve.sh", *norm],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _make_source(root: Path) -> Path:
    """造一個含「真源碼 + runtime 產物」的合成版本目錄，覆蓋各排除/保留情境與深度。"""
    src = root / "AISDLC_SDD_vTEST"
    # ── 真源碼（必保留）──
    (src / "agent" / "core").mkdir(parents=True)
    (src / "agent" / "core" / "foo.yaml").write_text("role: foo\n", encoding="utf-8")
    (src / "tools").mkdir(parents=True)
    (src / "tools" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    (src / "build" / "planning" / "active").mkdir(parents=True)
    (src / "build" / "planning" / "active" / "rfc.md").write_text("# rfc\n", encoding="utf-8")
    (src / "build" / "logs").mkdir(parents=True)
    (src / "build" / "logs" / "README.md").write_text("# logs\n", encoding="utf-8")
    # ── runtime 產物（必排除）──
    (src / "build" / "reports" / "fsm").mkdir(parents=True)
    (src / "build" / "reports" / "fsm" / "FSM-STATE-x.yaml").write_text("s: 1\n", encoding="utf-8")
    # DEF-15-001：FSM 種子模板＝真輸入（state_loader._load_template 必需），須**保留**
    (src / "build" / "reports" / "fsm" / "FSM-STATE-TEMPLATE.yaml").write_text(
        "current_state: INIT\n", encoding="utf-8"
    )
    (src / "build" / "reports" / "abort").mkdir(parents=True)
    (src / "build" / "reports" / "abort" / "ABORT-1.md").write_text("abort\n", encoding="utf-8")
    (src / "arch-fitness.json").write_text("{}\n", encoding="utf-8")
    (src / "chaos-report.json").write_text("{}\n", encoding="utf-8")
    (src / "tools" / "__pycache__").mkdir(parents=True)
    (src / "tools" / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\x00")
    (src / "a" / "b").mkdir(parents=True)
    (src / "a" / "b" / "deep.pyc").write_bytes(b"\x00")  # 深層 *.pyc
    (src / "a" / "b" / "deep.pyo").write_bytes(b"\x00")  # 深層 *.pyo
    return src


def test_helper_exists():
    assert HELPER.is_file(), f"helper 不存在：{HELPER}"


def test_excludes_runtime_keeps_source(work: Path):
    src = _make_source(work)
    dst = work / "AISDLC_SDD_vNEW"
    proc = _run(src, dst)
    assert proc.returncode == 0, f"helper 非零退出：{proc.returncode}\n{proc.stderr}"

    # 真源碼必保留
    assert (dst / "agent" / "core" / "foo.yaml").is_file()
    assert (dst / "tools" / "mod.py").is_file()
    assert (dst / "build" / "planning" / "active" / "rfc.md").is_file()
    assert (dst / "build" / "logs" / "README.md").is_file()

    # runtime 產物必排除（DEF-15-001：但 FSM-STATE-TEMPLATE.yaml 種子模板須保留，見專屬 case）
    assert not (dst / "build" / "reports" / "fsm" / "FSM-STATE-x.yaml").exists(), \
        "build/reports/ runtime FSM-STATE 檔未被排除"
    assert not (dst / "build" / "reports" / "abort").exists(), "build/reports/abort/ 未被排除"
    assert not (dst / "arch-fitness.json").exists(), "arch-fitness.json 未被排除"
    assert not (dst / "chaos-report.json").exists(), "chaos-report.json 未被排除"
    assert not (dst / "tools" / "__pycache__").exists(), "__pycache__/ 未被排除"
    assert not (dst / "a" / "b" / "deep.pyc").exists(), "深層 *.pyc 未被排除"
    assert not (dst / "a" / "b" / "deep.pyo").exists(), "深層 *.pyo 未被排除"
    # 但 build/planning 與 build/logs（同在 build/ 下）不可被連坐排除
    assert (dst / "build" / "planning").is_dir()
    assert (dst / "build" / "logs").is_dir()


def test_preserves_fsm_state_template(work: Path):
    """DEF-15-001：排除 build/reports/ 時，FSM 種子模板 FSM-STATE-TEMPLATE.yaml 必須保留。

    WHY：該模板是 state_loader._load_template() 必需的真輸入（非運行時輸出）；早期
    `cp -r`/robocopy 因不排除 build/reports 而碰巧帶上，改用 copy_on_evolve.sh 的
    `tar --exclude build/reports` 後被誤殺 → 演化版整個 FSM runtime 無法 bootstrap
    （46+ 測試全紅，improving_15 首次真實 v0.06 演化當場揭露）。helper 須在排除後補回。
    退化（拿掉 helper 的補回步驟）→ 本 assert 即紅。
    """
    src = _make_source(work)
    dst = work / "AISDLC_SDD_vNEW"
    proc = _run(src, dst)
    assert proc.returncode == 0, f"helper 非零退出：{proc.returncode}\n{proc.stderr}"
    tmpl = dst / "build" / "reports" / "fsm" / "FSM-STATE-TEMPLATE.yaml"
    assert tmpl.is_file(), "FSM-STATE-TEMPLATE.yaml 種子模板被誤排除（DEF-15-001 回歸）"
    assert tmpl.read_text(encoding="utf-8") == "current_state: INIT\n", "模板內容應原樣保留"


def test_refuses_existing_target(work: Path):
    src = _make_source(work)
    dst = work / "AISDLC_SDD_vNEW"
    dst.mkdir()  # 目標已存在
    proc = _run(src, dst)
    assert proc.returncode == 1, "目標已存在應 exit 1（拒絕覆蓋）"
    assert "已存在" in proc.stderr


def test_missing_source(work: Path):
    dst = work / "AISDLC_SDD_vNEW"
    proc = _run(work / "nope", dst)
    assert proc.returncode == 1, "來源不存在應 exit 1"
    assert "不存在" in proc.stderr


def test_wrong_arg_count():
    proc = _run("only-one-arg")
    assert proc.returncode == 2, "參數數不對應 exit 2"
    assert "用法" in proc.stderr
