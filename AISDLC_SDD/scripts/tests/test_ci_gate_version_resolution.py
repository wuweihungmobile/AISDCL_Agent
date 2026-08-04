"""DEF-03-001 雙軌版本閘門 — 版本解析邏輯回歸鎖。

WHY（測意圖非僅行為，Rule 9）：
原缺陷 DEF-03-001（P2）= `ci-gate.sh` 寫死 `FW_DIR=AISDLC_SDD_v0.01`，致官方閘門
永遠只測凍結基線、實際承載演化的最新版（v0.02+）從不進 CI/pre-push。本測試以
`SDD_GATE_DRY_RUN=1` 的版本清單輸出鎖定修復後的解析語意：

  1. 雙軌必同時含「凍結基線 v0.01」（回歸防護）與「最新演化版」（演化軌）——
     缺任一即代表治理缺口復發。
  2. 最新演化版必等於磁碟上語意版本最高者（auto-detect），而非任何寫死值——
     直接防止「又退回寫死某版」這個原缺陷再現。
  3. `SDD_FW_VERSION` 覆寫須能收斂為單一版本（debug/二分逃生口）。

純解析驗證（dry-run 不實跑 pytest/arch_fitness），快速且不依賴 Java/TLC。
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from scripts import bash_probe  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

# scripts/tests/ → scripts/ → AISDLC_SDD（REPO_ROOT，即 ci-gate.sh 的 REPO_ROOT）
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_GATE = REPO_ROOT / "scripts" / "ci-gate.sh"

# R43 Scan-B（DEF-101-353）：ci-gate.sh 現以 `../../tools/lib/windowsapps_guard.sh`
# dot-source monorepo 根層共用 guard；沙盒 fixture 需同步備有此檔（相對於
# sandbox/scripts/ci-gate.sh 的 `../..` 落在 sandbox 的**上一層**，即 tempdir 本身
# ——因為 sandbox 本身扮演的是 AISDLC_SDD/ 這一層，故 guard 需放在 sandbox 的
# 手足目錄，而非 sandbox 內部）。
_MONOREPO_ROOT = REPO_ROOT.parent
_GUARD_SH = _MONOREPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh"

# WSL 佔位 bash（System32）吃不下 Windows 路徑引數 → 紅燈而非 skip（第五輪 DEF-101 P3）
_BASH = bash_probe.usable_bash()


def _env_without_fw_version() -> dict[str, str]:
    """複製當前行程環境並移除 SDD_FW_VERSION（DEF-101-621）。

    WHY：`ci-gate.sh` 檔頭第 11 行明文記載的官方單版 debug 用法
    `SDD_FW_VERSION=X bash scripts/ci-gate.sh` 只在呼叫當下的 shell 行程樹內設定該
    變數；若本檔呼叫 ci-gate.sh 的 subprocess.run 未帶 `env=` 而原樣繼承呼叫者（例如
    pytest 本身）環境，一旦外層曾以該用法啟動整條 pytest（如 ci-gate.sh 自身
    「共享 infra scripts/tests/」階段），此處巢狀組出的 dry-run 呼叫就會被那個外溢的
    SDD_FW_VERSION 覆寫成單版，使原本要驗證雙軌/降軌情境的斷言失真而假紅——即使
    ci-gate.sh 已於版本迴圈後 `unset` 該變數，此處仍需獨立防禦（測試不該預設信任
    呼叫鏈上游已清乾淨環境）。四個直接呼叫 ci-gate.sh 的 subprocess.run 呼叫點皆用此。
    """
    env = dict(os.environ)
    env.pop("SDD_FW_VERSION", None)
    return env


pytestmark = pytest.mark.skipif(
    _BASH is None, reason="ci-gate.sh 為 bash 腳本，需可用 bash（非 WSL 佔位）"
)


def _dry_run(overrides: dict[str, str] | None = None) -> list[str]:
    """跑 ci-gate.sh dry-run，回傳解析出的版本清單。

    以 `bash -c '<VARS> bash scripts/ci-gate.sh'` 在外層 shell 自身環境內設變數，
    再呼叫內層腳本——繞過 Windows→WSL bash 不繼承宿主環境變數的屏障（CI 原生 bash
    亦適用）；相對路徑 scripts/ci-gate.sh 由 cwd 解析（WSL 自動轉譯 /mnt 路徑）。
    """
    assignments = {"SDD_GATE_DRY_RUN": "1", **(overrides or {})}
    prefix = " ".join(f"{k}={v}" for k, v in assignments.items())
    proc = subprocess.run(
        [_BASH, "-c", f"{prefix} bash scripts/ci-gate.sh"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=_env_without_fw_version(),
    )
    assert proc.returncode == 0, f"dry-run 非零退出：{proc.returncode}\n{proc.stderr}"
    m = re.search(r"^SDD_GATE_VERSIONS=(.*)$", proc.stdout, re.MULTILINE)
    assert m, f"未找到 SDD_GATE_VERSIONS 行：\n{proc.stdout}"
    return m.group(1).split()


def _disk_versions() -> list[str]:
    """磁碟上的版本目錄，依語意版本由低到高排序。

    DEF-19-002：glob 由 `v0.0*` 放寬為 `v0.*`，與修復後的 ci-gate.sh 雙 glob 同涵蓋面
    （含 v0.10+）。否則 helper 漏 v0.10 → 誤算「磁碟最高版=v0.09」，與腳本實測 v0.10 不符。
    """
    dirs = [p.name for p in REPO_ROOT.glob("AISDLC_SDD_v0.*") if p.is_dir()]
    # 以版本數值排序（對齊 scripts/sdd_version.py SSOT 的排序語意）
    return sorted(dirs, key=lambda n: [int(x) for x in re.findall(r"\d+", n)])


def test_ci_gate_exists():
    assert CI_GATE.is_file(), f"ci-gate.sh 不存在：{CI_GATE}"


def test_dual_track_includes_frozen_baseline_and_latest():
    """雙軌必同時含凍結基線 v0.01 與最新演化版（治理缺口不復發）。"""
    versions = _dry_run()
    assert "AISDLC_SDD_v0.01" in versions, "凍結基線 v0.01 必恆測（回歸防護）"
    latest = _disk_versions()[-1]
    assert latest in versions, f"最新演化版 {latest} 必納入官方閘門（DEF-03-001 修復點）"


def test_latest_is_highest_semver_not_hardcoded():
    """演化軌取磁碟語意版本最高者，而非任何寫死值（直防原缺陷再現）。"""
    versions = _dry_run()
    latest = _disk_versions()[-1]
    if latest != "AISDLC_SDD_v0.01":
        # 雙軌：[凍結基線, 最新演化版]，且最新版 = 磁碟最高版
        assert versions[-1] == latest, (
            f"演化軌應為磁碟最高版 {latest}，實得 {versions[-1]}——"
            f"疑似又退回寫死版本（DEF-03-001 復發）"
        )


def test_single_version_override_collapses_to_one():
    """SDD_FW_VERSION 覆寫須收斂為單一指定版本（debug 逃生口）。"""
    versions = _dry_run({"SDD_FW_VERSION": "AISDLC_SDD_v0.04"})
    assert versions == ["AISDLC_SDD_v0.04"], f"覆寫應僅測單版，實得 {versions}"


def test_missing_python_fails_loud_not_silent_downgrade():
    """R14 DEF-101-188 守門鎖：python 缺席須 rc=1 指路 venv，不得假綠。

    WHY：現代 macOS 乾淨 PATH 只有 python3 無 python，修復前 LATEST 解析的
    `|| true` 把 127 靜默吞成「無演化版」——dry-run 假綠 exit 0、非 dry-run
    雙軌閘門靜默降為單軌 v0.01（驗證鏡子靜默縮面家族）。本測試鎖住守門分支，
    防日後誤刪守門塊零訊號（R14 一審 ARCH-R14-REV-1 / QA-R14-REV-1）。
    """
    probe = subprocess.run(
        [_BASH, "-c", "PATH=/usr/bin:/bin command -v python"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if probe.returncode == 0:
        pytest.skip("此環境 /usr/bin:/bin 內有 python，無法模擬缺席情境")
    proc = subprocess.run(
        [_BASH, "-c", "PATH=/usr/bin:/bin SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        env=_env_without_fw_version(),
    )
    assert proc.returncode == 1, (
        f"python 缺席應 rc=1 fail-loud，實得 rc={proc.returncode}（假綠復發？）\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert "找不到 python" in proc.stderr, f"stderr 應含指路文案，實得：{proc.stderr!r}"
    assert "SDD_GATE_VERSIONS" not in proc.stdout, "守門應在版本解析前攔下，不得輸出版本清單"


def test_resolver_failure_downgrades_with_stderr_warning():
    """R14 DEF-101-188 守門鎖：resolver 失敗須 stderr 降軌警示、stdout 純淨、僅測基線。

    以 tmp 沙盒複製 ci-gate.sh ＋ 換入恆 exit 1 的 sdd_version.py stub 模擬 resolver
    自身故障（QA-R14 一審驗證此注入法可行）：降軌不再靜默（可見化），且警示走 stderr
    不污染 dry-run 的 stdout 機械輸出。
    """
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        # sandbox 扮演 AISDLC_SDD/ 這一層（比照 REPO_ROOT），故須巢狀一層，
        # 讓 tools/lib/windowsapps_guard.sh 能放在 td 底下、與 sandbox 手足並列
        # ——對齊 ci-gate.sh 內 `../../tools/lib/windowsapps_guard.sh` 的兩層相對路徑。
        sandbox = Path(td) / "AISDLC_SDD"
        sandbox.mkdir()
        (sandbox / "scripts").mkdir()
        shutil.copy2(CI_GATE, sandbox / "scripts" / "ci-gate.sh")
        (sandbox / "scripts" / "sdd_version.py").write_text(
            "import sys; sys.exit(1)\n", encoding="utf-8"
        )
        guard_dir = Path(td) / "tools" / "lib"
        guard_dir.mkdir(parents=True)
        shutil.copy2(_GUARD_SH, guard_dir / "windowsapps_guard.sh")
        proc = subprocess.run(
            [_BASH, "-c", "SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh"],
            cwd=str(sandbox),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            env=_env_without_fw_version(),
        )
    assert proc.returncode == 0, f"降軌屬容忍情境應 rc=0：{proc.stderr}"
    m = re.search(r"^SDD_GATE_VERSIONS=(.*)$", proc.stdout, re.MULTILINE)
    assert m and m.group(1).split() == ["AISDLC_SDD_v0.01"], (
        f"resolver 失敗應僅測凍結基線，實得：{proc.stdout!r}"
    )
    assert "LATEST 解析為空" in proc.stderr, (
        f"降軌須 stderr 警示可見化（勿再靜默縮面），實得 stderr={proc.stderr!r}"
    )


@pytest.mark.parametrize(
    ("stub_body", "label"),
    [
        ("import sys; sys.exit(2)\n", "rc=2（腳本缺失／參數被拒）"),
        ("import sys; sys.exit(126)\n", "rc=126（存在但不可執行／權限）"),
        ("import sys; sys.exit(127)\n", "rc=127（找不到直譯器）"),
    ],
)
def test_resolver_abnormal_exit_code_fails_loud_not_silent_downgrade(stub_body, label):
    """R74：resolver **異常**退出（非 rc=1）須 fail-loud，不得降級為只測凍結基線。

    WHY（測意圖，Rule 9）：修復前本行對 resolver 的所有非零退出碼一律抹平，於是
    「resolver 根本沒跑起來」與「這個 repo 沒有演化版」在閘門眼中完全同義——結果是
    只測 v0.01 凍結基線、LATEST 軌與其後全部硬閘一次都沒跑，**而且 rc=0 印出成功**。
    閘門靜默降級是最危險的一類缺陷，因為它回報綠：稽核者拿到的是「通過」。
    上方 `test_missing_python_fails_loud_not_silent_downgrade` 只覆蓋「PATH 上沒有
    python」（由檔頭守門攔下），攔不到本組這三種「有 python、但呼叫本身壞了」。

    三個退出碼各跑一次而非只挑一個：分級判準寫成 `-ne 0 && -ne 1` 是一句話，但退化
    成「只擋某個特定碼」時單一樣本看不出來。
    """
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        # sandbox 扮演 AISDLC_SDD/ 這一層（同上兩測試的既有構造說明）。
        sandbox = Path(td) / "AISDLC_SDD"
        sandbox.mkdir()
        (sandbox / "scripts").mkdir()
        shutil.copy2(CI_GATE, sandbox / "scripts" / "ci-gate.sh")
        (sandbox / "scripts" / "sdd_version.py").write_text(stub_body, encoding="utf-8")
        guard_dir = Path(td) / "tools" / "lib"
        guard_dir.mkdir(parents=True)
        shutil.copy2(_GUARD_SH, guard_dir / "windowsapps_guard.sh")
        proc = subprocess.run(
            [_BASH, "-c", "SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh"],
            cwd=str(sandbox),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            env=_env_without_fw_version(),
        )
    assert proc.returncode != 0, (
        f"resolver {label} 應 fail-loud，實得 rc=0——閘門又把「沒跑起來」讀成「無演化版」，"
        f"只測凍結基線卻回報綠。\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert "SDD_GATE_VERSIONS" not in proc.stdout, (
        f"異常退出時不得輸出版本清單（那正是降級後的假綠證據），實得：{proc.stdout!r}"
    )
    assert "LATEST 解析器異常退出" in proc.stderr, (
        f"stderr 須明說是 resolver 異常而非「無演化版」（訊息含糊時讀者會照降軌流程"
        f"排查，找錯方向），實得：{proc.stderr!r}"
    )
    assert "LATEST 解析為空" not in proc.stderr, (
        "異常退出不得沿用「解析為空」的降軌警示——那句話會把「呼叫壞了」講成"
        f"「這個 repo 沒有演化版」，實得：{proc.stderr!r}"
    )


def test_override_with_failed_resolver_suppresses_downgrade_warning():
    """R14 一審 SD-R14-REV-1 鎖：SDD_FW_VERSION 覆寫時不印降軌警示（避免「警示說
    僅測基線、實際測覆寫版」的自相矛盾訊息）。"""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        # sandbox 扮演 AISDLC_SDD/ 這一層（見上一測試同款說明）。
        sandbox = Path(td) / "AISDLC_SDD"
        sandbox.mkdir()
        (sandbox / "scripts").mkdir()
        shutil.copy2(CI_GATE, sandbox / "scripts" / "ci-gate.sh")
        (sandbox / "scripts" / "sdd_version.py").write_text(
            "import sys; sys.exit(1)\n", encoding="utf-8"
        )
        guard_dir = Path(td) / "tools" / "lib"
        guard_dir.mkdir(parents=True)
        shutil.copy2(_GUARD_SH, guard_dir / "windowsapps_guard.sh")
        proc = subprocess.run(
            [_BASH, "-c",
             "SDD_GATE_DRY_RUN=1 SDD_FW_VERSION=AISDLC_SDD_v0.04 bash scripts/ci-gate.sh"],
            cwd=str(sandbox),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            env=_env_without_fw_version(),
        )
    assert proc.returncode == 0
    m = re.search(r"^SDD_GATE_VERSIONS=(.*)$", proc.stdout, re.MULTILINE)
    assert m and m.group(1).split() == ["AISDLC_SDD_v0.04"]
    assert "LATEST 解析為空" not in proc.stderr, (
        f"覆寫時不應印降軌警示（SD-R14-REV-1），實得 stderr={proc.stderr!r}"
    )


# ── DEF-101-512（R59）：降級 fallback 不得冒充完整閘門 ─────────────────────────
# WHY：`ci-gate.ps1` 在偵測不到 Git Bash 時走 fallback，只跑 **v0.01 凍結基線單軌**
# 的 3 個 stage——不含 LATEST 軌、不含 `ci-gate.sh` 的 lint 硬閘、不含 `scripts/tests`
# 共享 infra 測試。原本它的收尾訊息是完整閘門收尾行去掉括號後綴後的**前綴子字串**：
# 兩者非逐字相同，但實務稽核取證（人工回報、歷輪帳本引用、grep）用的錨點正是那段前綴，
# 於是「跑了完整雙軌閘門」與「只跑了凍結基線 3 stage」在取證上無法分辨。只有 Windows
# 走得到 fallback（mac 一律有 bash）＝單邊平台的取證可信度缺口。
#
# 本鎖為何放在這裡：本檔已在讀 `ci-gate.sh`、且屬 `scripts/tests/` 共享 infra 套件，
# 每輪隨 ci-gate 自己執行——等於「閘門自己鎖住自己的誠實性」。
_CI_GATE_PS1 = REPO_ROOT / "scripts" / "ci-gate.ps1"


def _cut_ps_inline_comment(line: str) -> str:
    """剝掉引號外的尾隨 `#` 註解（逐字元追蹤引號狀態）。

    WHY（SD-R59-05）：只剝整行註解不夠——把成功訊息寫成含糊的 `✅ 完成`、再把
    `fallback`／`未含` 兩個關鍵字放進尾隨註解，反向鎖就會被騙過。本 repo 既有
    `test_ps51_compat.split_code_comment`／`test_find_git_bash_parity._cut_inline_comment`
    是同款判準（DEF-101-482 修法），此處沿用其語意的最小實作。
    """
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _ps1_code_lines(text: str) -> list[str]:
    """剝掉整行 `#` 註解後的功能碼行（沿用本 repo 既有 `_code_only()` 判準精神）。

    必須剝註解：本輪修復的註解裡刻意保留一次完整閘門的字面值以說明缺陷本身，
    若不剝就會自我命中（同 zsh-glob-ok／baseline-ok 兩個豁免家族處理「文件必須
    引述壞形態」的既有做法——此處刻意不寫出那兩個標記的完整字面形式，避免本行
    被誤讀為一筆豁免宣告）。
    """
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def test_full_gate_success_anchor_is_not_reachable_from_ps1_fallback():
    sh_text = CI_GATE.read_text(encoding="utf-8")
    m = re.search(r'echo\s+"(✅ [^（"]*全數通過)', sh_text)
    assert m, "ci-gate.sh 找不到完整閘門收尾錨點——結構已變動，請同步本鎖"
    anchor = m.group(1)

    ps1_code = "\n".join(_ps1_code_lines(_CI_GATE_PS1.read_text(encoding="utf-8-sig")))
    assert anchor not in ps1_code, (
        f"ci-gate.ps1 的功能碼行出現完整閘門的成功錨點 {anchor!r}——降級 fallback "
        f"只跑 v0.01 單軌 3 stage，卻會在稽核 grep 下冒充完整雙軌閘門（DEF-101-512 迴歸）。"
        f"請讓 fallback 的收尾訊息自己說出降級事實。"
    )


def test_ps1_fallback_success_message_self_declares_degradation():
    """反向鎖：光是「不含錨點」還不夠——改成一句含糊的 `✅ 完成` 同樣會讓讀者誤判。
    故要求 fallback 的成功訊息必須自陳兩件事：這是 fallback、以及**未含**什麼。"""
    ps1_code = "\n".join(_ps1_code_lines(_CI_GATE_PS1.read_text(encoding="utf-8-sig")))
    success_lines = [ln for ln in ps1_code.splitlines()
                     if "Write-Host" in ln and "✅" in ln]
    assert success_lines, "ci-gate.ps1 功能碼行找不到任何 ✅ 成功訊息——結構已變動"
    # R59 QA-R59-06／SD-R59-05 兩項訂正：
    #  ① 只看**最後一行**：修法的 WHY 明寫「人讀 log 取的是最後那行結論」，但原實作把
    #     所有 ✅ 行 join 起來找關鍵字——在 L80 之後追加一行 `Write-Host "✅ 完成"` 仍會
    #     全綠，而人在終端看到的最後一行又變回無條件成功，DEF-101-512 的危害復原。
    #  ② 剝尾隨行內註解：原 `_ps1_code_lines()` 只剝**整行** `#`，故
    #     `Write-Host "✅ 完成"   # fallback 3-stage，未含 LATEST` 這種寫法會讓兩個關鍵字
    #     從註解被讀到而通過（DEF-101-482 同型；本輪剛因這件事被抓過一次）。
    joined = _cut_ps_inline_comment(success_lines[-1])
    assert "fallback" in joined, "fallback 的成功訊息必須自陳它是 fallback"
    assert "未含" in joined, (
        "fallback 的成功訊息必須明列**未含**哪些閘門（LATEST 軌／lint 硬閘／"
        "共享 infra 測試），否則讀者無從得知覆蓋率差距"
    )


def test_ci_gate_pytest_calls_carry_dash_rs():
    """QA-R59-10：`ci-gate.sh` 的兩處 pytest 呼叫必須帶 `-rs`（印出 skip 理由）。

    WHY：R59 為 unittest 面的「skip 可見度」寫了 5 支鎖，pytest 面（真正的測試量體）
    卻 0 支——任何人覺得 log 太長把 `-rs` 拿掉即全綠，DEF-101-510 在 pytest 面復發。
    對計數無影響已實測：`scripts/pytest_passed_count.sh` 抓 `N passed` 並 `tail -1`，
    `-rs` 的 SHORT SUMMARY 段排在最終統計行之前，取值不受影響。
    """
    # R59 二審 ARCH-R59-NB2：`.ps1` 的 fallback pytest 呼叫同樣要鎖——本測試檔對 `.ps1`
    # 的成功訊息鎖得很細（最後一行 + 剝尾隨註解），卻漏了它的 `-rs`，屬同型的
    # 「鎖住 N 份中的 1 份」。
    ps1_code = "\n".join(_ps1_code_lines(_CI_GATE_PS1.read_text(encoding="utf-8-sig")))
    ps1_calls = [ln for ln in ps1_code.splitlines() if "-m pytest" in ln]
    assert ps1_calls, "ci-gate.ps1 功能碼行找不到 pytest 呼叫——結構已變動"
    for ln in ps1_calls:
        assert " -rs" in ln, (
            f"ci-gate.ps1 的 fallback pytest 呼叫缺 `-rs`（ARCH-R59-NB2）：{ln.strip()}")

    sh = CI_GATE.read_text(encoding="utf-8", errors="replace")
    calls = [ln for ln in sh.splitlines()
             if "python -m pytest" in ln and not ln.lstrip().startswith("#")]
    assert len(calls) >= 2, f"ci-gate.sh 的 pytest 呼叫少於 2 處——結構已變動：{calls}"
    for ln in calls:
        assert " -rs" in ln, (
            f"ci-gate.sh 的 pytest 呼叫缺 `-rs`，skip 理由會被丟掉（DEF-101-510／QA-R59-10）：{ln.strip()}"
        )
