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
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_NIGHTLY_SH = _REPO_ROOT / "tools" / "run_local_nightly.sh"


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
