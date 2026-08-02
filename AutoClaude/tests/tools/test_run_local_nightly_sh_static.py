"""tests/tools/test_run_local_nightly_sh_static.py — mac 側 nightly .sh 靜態檢查
（R31 Architect 架構深度評估發現：測試嚴謹度不對稱的補強）。

背景：Windows 側 `tools/run_local_nightly.ps1` 有 25 個結構化 pytest case
（`test_run_local_nightly_static.py`），逐項鎖心跳／保留期輪替／trigger 標註／
去重鎖／exit 語意；mac 側 `AutoClaude/tools/run_local_nightly.sh` 此前**沒有對等
的 pytest 靜態測試**，同款行為只在 `tools/macos_smoke_local.sh` [7/7] 步驟以粗
粒度 grep 驗證 5 個錨點字串（打包在 shell smoke 腳本裡當一個 pass/fail 項），
沒有負向測試。這降低了 mac 側 nightly 契約走樣（尤其近幾輪才新增的 mkdir atomic
lock／trigger 歸因欄位）的偵測靈敏度，與本 repo「驗證鏡子自身要被驗證」的紀律
精神（`docs/06_quality/Nightly_Forensic_Discipline.md`）不符。

本檔不取代 `macos_smoke_local.sh` [7/7]（該步驟仍作為端到端 smoke 補充保留），
而是補上 pytest 靜態層級的結構化正向 + 負向 case，涵蓋現有 5 個 smoke 錨點
（exec >>／nightly_mac_2*.log／-mtime +14／--force／RunAtLoad 補跑去重文案）之外
的 mkdir atomic lock、trigger= 四態枚舉、終端 exit 語意、心跳三站點契約格式。
"""
from __future__ import annotations

import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_NIGHTLY_SH = _REPO_ROOT / "tools" / "run_local_nightly.sh"
# monorepo 根（AutoClaude/ 的上一層）——跨檔字面一致性鎖要讀根層安裝器。
_MONOREPO_ROOT = _REPO_ROOT.parent
_MAC_INSTALLER = _MONOREPO_ROOT / "tools" / "install_mac_nightly.sh"


@pytest.fixture(scope="module")
def sh_content() -> str:
    assert _NIGHTLY_SH.exists(), f"nightly sh missing: {_NIGHTLY_SH}"
    return _NIGHTLY_SH.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    """剝除整行註解（`^\\s*#` 起頭），比照 macos_smoke_local.sh [7/7] 既有手法——
    防「功能碼被改壞、但同名舊註解字樣仍在」造成靜態比對假陽性。"""
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )


# --- 正向 case：現有 smoke 5 錨點的 pytest 對等版（更精確——剝註解後比對） -----

def test_run_id_log_exec_redirect_present(sh_content: str) -> None:
    """RunId log 必須以 `exec >>`（非互動）將輸出改道獨立日誌檔。"""
    code = _code_only(sh_content)
    assert "exec >>" in code, "缺 RunId log exec 改道（非互動路徑）"
    assert 'exec > >(tee -a "${RUN_LOG}")' in code, "缺互動終端機 tee 雙寫路徑"


def test_dated_log_retention_pattern_and_window(sh_content: str) -> None:
    """dated log 保留期輪替：pattern 必須是 `nightly_mac_2*.log`，保留 14 天。"""
    code = _code_only(sh_content)
    assert "nightly_mac_2*.log" in code, "缺 dated log pattern"
    assert "-mtime +14" in code, "保留期必須為 14 天"


def _rotation_glob(code: str) -> str | None:
    """抽出 dated log 輪替 `find -name '<pattern>'` 的 glob 字面值；找不到回傳 None。"""
    m = re.search(r"-name\s+'([^']+)'", code)
    return m.group(1) if m else None


def _rotation_pattern_excludes_heartbeat(code: str) -> bool:
    """輪替 pattern 是否真的不會（以 shell glob 語意，非純字串子字串）誤配到
    `nightly_mac_latest.log` 心跳指標檔，且輪替行確有 `-delete`。用 `fnmatch`
    做真正的 glob 比對，而非只查字面子字串——`nightly_mac_*.log` 這種寬鬆版本
    字面上不含 "nightly_mac_latest.log"，但 glob 語意上會命中它，純子字串比對
    抓不到這個退化，必須用 fnmatch 才驗證得出來。"""
    pattern = _rotation_glob(code)
    if pattern is None:
        return False
    line = next((line for line in code.splitlines() if pattern in line), "")
    if "-delete" not in line:
        return False
    return not fnmatch.fnmatch("nightly_mac_latest.log", pattern)


def test_retention_rotation_excludes_heartbeat_file(sh_content: str) -> None:
    """輪替必須實際執行刪除（非只是掃描），且絕不誤刪 nightly_mac_latest.log 心跳檔
    ——以 `fnmatch` 對 glob pattern 本身做語意比對，而非只查字面子字串。"""
    code = _code_only(sh_content)
    assert _rotation_glob(code) is not None, "找不到輪替 -name pattern"
    assert _rotation_pattern_excludes_heartbeat(code), (
        "輪替 pattern 必須實際執行 -delete，且以 glob 語意（非純字面）確認不會"
        "誤配到 nightly_mac_latest.log 心跳指標檔"
    )


def test_force_flag_bypasses_dedup(sh_content: str) -> None:
    """`--force` 必須能繞過當日去重（手動重跑逃生門）。"""
    code = _code_only(sh_content)
    assert '"${1:-}" != "--force"' in code or '"${1:-}" = "--force"' in code, (
        "缺 --force 旗標判斷（手動重跑必須能繞過當日去重）"
    )
    assert "RunAtLoad 補跑去重" in sh_content, "缺 RunAtLoad 補跑去重說明文案（取證可讀性）"


# --- 補強 case：mkdir atomic lock、trigger 枚舉、終端 exit 語意（此前無鏡子） ---

def test_mkdir_atomic_lock_present(sh_content: str) -> None:
    """並行防護：必須用 `mkdir` 原子鎖（非 flock/shlock——macOS 無 flock，shlock
    非所有版本保證存在），且鎖不到時必須 exit 0（跳過本輪，不阻斷排程）。"""
    code = _code_only(sh_content)
    assert "NIGHTLY_LOCK_DIR=" in code, "缺 mkdir atomic lock 目錄變數定義"
    assert 'mkdir "${NIGHTLY_LOCK_DIR}"' in code, "缺 mkdir 原子鎖建立呼叫"
    lock_guard_idx = code.find("_nightly_lock_acquire")
    assert lock_guard_idx > 0, "缺去重鎖 acquire 函式"
    assert "trap _nightly_lock_release EXIT" in code, (
        "必須在 EXIT trap 釋放鎖——否則行程正常結束後鎖永久卡死下一輪"
    )


def _has_stale_lock_liveness_check(code: str) -> bool:
    """陳舊鎖清除是否用 `kill -0 <pid>` 存活性檢查（而非固定逾時秒數判斷）。"""
    return bool(re.search(r"kill\s+-0\s+", code))


def test_stale_lock_uses_liveness_check_not_fixed_timeout(sh_content: str) -> None:
    """陳舊鎖清除必須依「鎖檔內 PID 是否仍存活」（kill -0）判斷，而非固定逾時秒數
    ——4-stage gate 執行時間會變動，固定逾時容易誤殺仍在跑的合法行程（同 dev_start.py
    `_acquire_bootstrap_lock()` 慣例）。"""
    code = _code_only(sh_content)
    assert _has_stale_lock_liveness_check(code), (
        "陳舊鎖清除必須用 `kill -0 <pid>` 存活性檢查，不可用固定逾時秒數判斷"
    )
    assert re.search(r"echo\s+\"\$\$\"\s*>\s*", code), (
        "取得鎖後必須把自身 PID（$$）寫入鎖檔，供陳舊鎖判斷讀取"
    )


def test_trigger_source_four_state_enum(sh_content: str) -> None:
    """trigger 歸因必須涵蓋四態：manual-force／launchd／manual-interactive／
    non-interactive-unknown（BEGIN log 需可歸因觸發來源，防「同日兩輪 PASS」
    無法判讀是合理手動重跑還是去重漏洞）。"""
    code = _code_only(sh_content)
    for expected in (
        "manual-force",
        "XPC_SERVICE_NAME",
        "manual-interactive",
        "non-interactive-unknown",
    ):
        assert expected in code, f"trigger 歸因缺少 {expected!r} 分支"
    assert "trigger=%s" in sh_content or "trigger=${TRIGGER_SRC}" in sh_content, (
        "BEGIN log 必須把 trigger 來源寫入輸出（取證可讀）"
    )


def test_terminal_exit_reflects_fail_count(sh_content: str) -> None:
    """終端 exit 語意：FAIL>0 必須 exit 1；否則 exit 0（對齊 .ps1 R9 ③ exit 語意，
    防止 stage 真失敗卻靜默 exit 0 讓排程 Last Result 恆綠）。"""
    code = _code_only(sh_content)
    assert re.search(r'if \[ "\$FAIL" -gt 0 \]', code), "缺 FAIL 計數守門判斷"
    tail = code[code.find('if [ "$FAIL" -gt 0 ]'):]
    assert re.search(r"exit 1", tail), "FAIL>0 分支必須 exit 1"
    assert re.search(r"exit 0\s*$", code.strip()), "腳本結尾必須有明確 exit 0（全數通過語意）"


def test_heartbeat_three_site_contract_lines(sh_content: str) -> None:
    """心跳檔前兩行格式為三站點契約（dev_start.py mtime 讀取／install_mac_nightly.sh
    --status／本函式寫入），絕不可變。"""
    code = _code_only(sh_content)
    assert "nightly_mac heartbeat（UTC）" in code, "心跳檔第一行格式（三站點契約）不得變動"
    assert "nightly 彙總：PASS=" in code, "心跳檔彙總行格式不得變動"


# --- R67-F10：CLI 契約（--help 不得開跑整套 nightly；未知旗標 fail-loud）--------
#
# WHY：修復前全檔對 `$1` 只有兩處 `= "--force"` 二元比對——無 usage 分支、無未知
# 旗標拒絕。實測兩種失敗形態：(a) 剛 clone／logs 已被輪替掉的樹上，`--help` 直接
# 啟動 macos_smoke → root_unittests → autoclaude_gate → sdd_ci_gate（沙箱實測落下
# nightly_mac_*.log 並跑進 smoke 的 7 個子步驟，被 kill 才停）；(b) 當日已有心跳時
# `--help` rc=0 並印「今日已有心跳…跳過本輪」——查說明的動作被記成一次成功的
# nightly 去重，事後從 log 看不出使用者輸錯了旗標。`--forse`／`-f`／`--Force`／
# `--FORCE`／裸位置參數七種變體實測 rc 全為 0，無一被拒。

_POSIX_ONLY = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="需要 POSIX bash 實跑本 .sh（Windows 側對等品為 run_local_nightly.ps1，"
           "其 CLI 契約缺口另案處理）",
)


def _sandbox_nightly(tmp_path: Path) -> Path:
    """把真的 run_local_nightly.sh 放進臨時樹（ROOT 由 BASH_SOURCE/../.. 推得）。

    在沙箱而非真 repo 執行：本組要斷言的正是「有沒有產生 nightly log／有沒有開跑
    stage」，在真 repo 上跑會污染真心跳與 RunId log；沙箱裡 `$ROOT/tools/*.sh`
    全不存在，萬一契約退化也會在第一個 stage 立刻失敗而非真的跑完整套 gate。
    """
    dest = tmp_path / "AutoClaude" / "tools"
    dest.mkdir(parents=True)
    shutil.copy2(_NIGHTLY_SH, dest / "run_local_nightly.sh")
    return dest / "run_local_nightly.sh"


def _run_sh(
    script: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    if env is not None:
        full_env.update(env)
    return subprocess.run(
        # bash-ok: 呼叫端全掛 _POSIX_ONLY（含 `sys.platform == "win32"` 短路），
        # Windows 上恆 skip ⇒ 無 WSL 佔位版劫持面（DEF-101-753）。
        ["bash", str(script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, env=full_env,
    )


@_POSIX_ONLY
def test_help_prints_usage_rc_zero_and_starts_no_stage(tmp_path: Path) -> None:
    script = _sandbox_nightly(tmp_path)
    proc = _run_sh(script, "--help")
    assert proc.returncode == 0, f"`--help` 必須 rc=0，實得 {proc.returncode}：{proc.stderr}"
    assert "用法：" in proc.stdout, f"`--help` 必須印出用法，實得 stdout={proc.stdout!r}"
    for token in ("--force", "macos_smoke", "nightly_mac_latest.log"):
        assert token in proc.stdout, f"usage 應說明 {token}（旗標語意／stage 名／log 落點）"
    logs = tmp_path / "AutoClaude" / "logs"
    assert not logs.exists() or not list(logs.glob("nightly_mac_*.log")), (
        "`--help` 絕不得產生 RunId log／心跳——那代表它其實開跑了 nightly"
    )


@_POSIX_ONLY
@pytest.mark.parametrize("bad", ["--forse", "-f", "--Force", "--FORCE", "bogus-positional"])
def test_unknown_flag_fails_loud_and_starts_no_stage(tmp_path: Path, bad: str) -> None:
    """typo 一律 rc=2 且指名該字——修復前這七種變體全部 rc=0 靜默走去重路徑。"""
    script = _sandbox_nightly(tmp_path)
    proc = _run_sh(script, bad)
    assert proc.returncode == 2, f"未知參數 {bad!r} 必須 rc=2，實得 {proc.returncode}"
    assert bad in proc.stderr, f"錯誤訊息必須逐字指名 {bad!r}，實得 {proc.stderr!r}"
    logs = tmp_path / "AutoClaude" / "logs"
    assert not logs.exists() or not list(logs.glob("nightly_mac_*.log")), (
        f"{bad!r} 被拒後不得留下任何 nightly log"
    )


@_POSIX_ONLY
def test_extra_arguments_fail_loud(tmp_path: Path) -> None:
    proc = _run_sh(_sandbox_nightly(tmp_path), "--force", "--bogus")
    assert proc.returncode == 2, "多個參數必須 fail-loud（本腳本最多接受一個旗標）"


@_POSIX_ONLY
def test_no_args_is_not_rejected(tmp_path: Path) -> None:
    """鑑別力對照組：無參數＝排程路徑，**不得**被新的參數檢查誤擋。

    少了這條，把腳本改成「一律 exit 2」也能讓上面全綠——那會讓 launchd 每天空跑。
    無參數時沙箱裡的 stage 腳本不存在故必然失敗（rc=1），關鍵是它**確實走進了
    stage 執行**（印得出 BEGIN／stage 標題），而不是在參數關卡就被擋掉。
    """
    script = _sandbox_nightly(tmp_path)
    proc = _run_sh(script)
    assert proc.returncode != 2, f"無參數不得被當成參數錯誤，實得 rc=2：{proc.stderr!r}"
    logs = list((tmp_path / "AutoClaude" / "logs").glob("nightly_mac_2*.log"))
    assert logs, "無參數時應照舊產生 RunId log（證明真的進入了排程執行路徑）"
    assert "BEGIN nightly_mac" in logs[0].read_text(encoding="utf-8", errors="replace")


# --- R67-F26：觸發來源歸因（XPC_SERVICE_NAME 值比對，而非存在性）---------------
#
# WHY：`XPC_SERVICE_NAME=0` 是 macOS 對**一般使用者行程**注入的常態值（Darwin
# 25.5.0 實測 `/bin/bash -c 'echo ${XPC_SERVICE_NAME}'` → `0`），舊判定用
# `[ -n ... ]` 測存在性，於是任何手動／agent／CI 呼叫都被標成 `launchd(...)`，
# 而 manual-interactive／non-interactive-unknown 兩態成為死碼。此欄位存在的唯一
# 目的就是「同日兩輪 PASS 時能機械判讀是手動重跑還是去重漏洞」——舊判定正好在
# 那個情境給出反向結論（把去重漏洞歸因給無辜的排程器）。


def _extract_trigger_block(code: str) -> str:
    """抽出「label 常數 ＋ 觸發來源判定」兩段真實碼，供實跑對照（非字串比對）。"""
    label = re.search(r'^NIGHTLY_LAUNCHD_LABEL=.*$', code, re.M)
    block = re.search(
        r'^if \[ "\$\{1:-\}" = "--force" \]; then$.*?^fi$', code, re.M | re.DOTALL
    )
    assert label and block, "找不到 label 常數或觸發來源判定區塊——抽取正則已與實作漂移"
    return f"{label.group(0)}\n{block.group(0)}\n"


def _trigger_for(tmp_path: Path, code: str, *, xpc: str | None, args: tuple[str, ...] = ()) -> str:
    probe = tmp_path / "trigger_probe.sh"
    probe.write_text(
        "set -u\n" + _extract_trigger_block(code) + 'printf "%s" "${TRIGGER_SRC}"\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("XPC_SERVICE_NAME", None)
    if xpc is not None:
        env["XPC_SERVICE_NAME"] = xpc
    return subprocess.run(
        # bash-ok: 同上，呼叫端全掛 _POSIX_ONLY（DEF-101-753）。
        ["bash", str(probe), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30, env=env,
    ).stdout


@_POSIX_ONLY
def test_sentinel_xpc_value_is_not_attributed_to_launchd(tmp_path: Path, sh_content: str) -> None:
    """真機常態值 `XPC_SERVICE_NAME=0`（非 launchd job）不得被標成 launchd。"""
    got = _trigger_for(tmp_path, sh_content, xpc="0")
    assert "launchd" not in got, (
        f"XPC_SERVICE_NAME=0 是一般使用者行程的常態值，不得歸因為 launchd，實得 {got!r}"
    )
    assert got == "non-interactive-unknown", (
        f"非互動且非排程應為 non-interactive-unknown，實得 {got!r}"
    )


@_POSIX_ONLY
def test_real_launchd_label_is_attributed_to_launchd(tmp_path: Path, sh_content: str) -> None:
    """對照組：真 launchd 注入的值是 job Label，必須仍被正確歸因。

    沒有這條，把判定改成「永不回 launchd」也能讓上一條綠——那會把歸因能力整個
    拆掉（本機 7 份真排程 log 皆為 XPC_SERVICE_NAME=com.autoclaude.nightly）。
    """
    label = re.search(r'^LABEL="([^"]+)"', _MAC_INSTALLER.read_text(encoding="utf-8"), re.M)
    assert label, "install_mac_nightly.sh 找不到 LABEL 常數"
    got = _trigger_for(tmp_path, sh_content, xpc=label.group(1))
    assert got == f"launchd(XPC_SERVICE_NAME={label.group(1)})", (
        f"真 launchd Label 必須歸因為 launchd，實得 {got!r}"
    )


@_POSIX_ONLY
def test_force_flag_wins_over_environment(tmp_path: Path, sh_content: str) -> None:
    got = _trigger_for(tmp_path, sh_content, xpc="0", args=("--force",))
    assert got == "manual-force", f"--force 應優先於環境判定，實得 {got!r}"


@_POSIX_ONLY
def test_unset_xpc_is_non_interactive_unknown(tmp_path: Path, sh_content: str) -> None:
    got = _trigger_for(tmp_path, sh_content, xpc=None)
    assert got == "non-interactive-unknown", (
        f"未設定 XPC 時應為 non-interactive-unknown，實得 {got!r}"
    )


def test_launchd_label_matches_the_installer_verbatim(sh_content: str) -> None:
    """跨檔字面一致性：歸因基準值必須與 tools/install_mac_nightly.sh 的 LABEL 同字。

    測意圖：兩邊一旦漂移，真排程觸發會被靜默降級成 non-interactive-unknown——
    沒有任何錯誤訊息，只是取證欄位開始說謊（正是 R67-F26 的失敗形態）。
    """
    ours = re.search(r'^NIGHTLY_LAUNCHD_LABEL="([^"]+)"', _code_only(sh_content), re.M)
    theirs = re.search(r'^LABEL="([^"]+)"', _MAC_INSTALLER.read_text(encoding="utf-8"), re.M)
    assert ours and theirs, "兩側 label 常數至少一支抽不到——正則已與實作漂移"
    assert ours.group(1) == theirs.group(1), (
        f"run_local_nightly.sh 的 launchd label {ours.group(1)!r} 與安裝器的 "
        f"{theirs.group(1)!r} 不一致——真排程觸發會被誤標為手動"
    )


def test_trigger_uses_value_comparison_not_mere_presence(sh_content: str) -> None:
    """靜態面補刀：判定式不得退回 `[ -n "${XPC_SERVICE_NAME:-}" ]` 存在性寫法。

    與上面的實跑對照組互補——實跑證明「當前行為對」，本條把「用什麼判準」釘住，
    讓退化在 code review／grep 層面也留下痕跡。
    """
    block = _extract_trigger_block(_code_only(sh_content))
    assert '[ -n "${XPC_SERVICE_NAME:-}" ]' not in block, (
        "存在性判定會把 XPC_SERVICE_NAME=0（macOS 對一般行程注入的常態值）"
        "誤判為 launchd 觸發——必須與 job Label 做值比對"
    )
    assert "${NIGHTLY_LAUNCHD_LABEL}" in block, "判定式必須以 label 常數為比對基準"


# --- 對抗式（負向）case：真突變（mutate）真實 sh_content 後重跑正向斷言邏輯 -----
# R31 QA 一審必修條件 1：原版本對著測試檔內手刻的 degraded_sample／degraded_line
# 字面字串做斷言，從未讀取或修改真正的 sh_content——是恆真的裝飾性測試（tautology），
# 沒有任何鑑別力。改為：對真實 sh_content 做文字替換模擬退化，重跑上面同一組
# `_has_stale_lock_liveness_check()` / `_rotation_pattern_excludes_heartbeat()`
# 判斷式本身，確認其在退化樣本上真的翻轉為 False，才算真正驗證了鑑別力。

def test_bug_injection_missing_stale_lock_liveness_check_is_caught(sh_content: str) -> None:
    """真突變：把真實 sh_content 裡的 `kill -0` 存活性檢查行換成固定逾時判斷，
    重跑 `_has_stale_lock_liveness_check()` 本身，確認會由 True 翻轉為 False。"""
    code = _code_only(sh_content)
    assert _has_stale_lock_liveness_check(code), "測試前提不成立：真實 sh 應含 kill -0"

    liveness_line = next(line for line in code.splitlines() if "kill -0" in line)
    degraded_line = (
        '      _age=$(( $(date +%s) - $(stat -f %m "${NIGHTLY_LOCK_DIR}") )); '
        '[ "${_age}" -gt 300 ]  # mutated: 固定逾時取代存活性檢查'
    )
    mutated = code.replace(liveness_line, degraded_line)
    assert mutated != code, "突變未生效——找不到可替換的 kill -0 那一行"
    assert not _has_stale_lock_liveness_check(mutated), (
        "退化為固定逾時判斷後，_has_stale_lock_liveness_check() 必須翻轉為 False"
        "——若仍為 True，代表該判斷式本身沒有鑑別力"
    )


def test_bug_injection_dedup_pattern_matching_heartbeat_file_is_caught(sh_content: str) -> None:
    """真突變：把真實 sh_content 裡的輪替 pattern `nightly_mac_2*.log` 改壞為會
    誤配到心跳檔的寬鬆版本 `nightly_mac_*.log`，重跑
    `_rotation_pattern_excludes_heartbeat()` 本身，確認會由 True 翻轉為 False。"""
    code = _code_only(sh_content)
    assert _rotation_pattern_excludes_heartbeat(code), "測試前提不成立：真實 sh 應排除心跳檔"

    mutated = code.replace("nightly_mac_2*.log", "nightly_mac_*.log")
    assert mutated != code, "突變未生效——找不到可替換的輪替 pattern"
    assert fnmatch.fnmatch("nightly_mac_latest.log", "nightly_mac_*.log"), (
        "測試前提檢查：退化 pattern 必須真的以 glob 語意命中心跳檔案名"
    )
    assert not _rotation_pattern_excludes_heartbeat(mutated), (
        "退化為寬鬆 pattern 後，_rotation_pattern_excludes_heartbeat() 必須翻轉為"
        " False——若仍為 True，代表該判斷式本身沒有鑑別力（純字面子字串比對"
        "抓不到這個退化，這正是本 case 存在的理由）"
    )
