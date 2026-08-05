"""tests/tools/test_run_local_nightly_static.py — nightly ps1 靜態檢查（言以裝鏡子）。

SD_09 W3 Round 19 audit P0-AUDIT-R18-2 修復（紀律 #4「驗證鏡子自身要被驗證」）：

背景：2026-05-26 02:00 schtasks 第 14 跑（首次自動跑）pg-e2e stage 36ms 內 EXCEPTION crash
      「在此物件上找不到屬性 'Source'」— 根因
      `(Get-Command alembic.exe -EA SilentlyContinue).Source`
      在 StrictMode 3.0 下，當 Get-Command 回 $null 時 `.Source` 拋 PropertyNotFoundException。
      schtasks 自動跑 PATH 不含 pyenv shims 觸發；互動模式因 pyenv hook 動態注入路徑而躲過。

紀律 #4：ps1 複雜分支邏輯（630 行）也算「鏡子」必須被驗證。修復後須有靜態檢查防止
同類 bug 再生 — 任何 `(...-ErrorAction SilentlyContinue).<Property>` 鏈式存取在 StrictMode
3.0 下都是潛在 $null.Property 例外點。

涵蓋 case：
    1) StrictMode 3.0 啟用：確保未來不會被誤刪
    2) 禁止模式：`(...-ErrorAction SilentlyContinue).<Prop>` 鏈式存取絕跡
    3) 禁止模式：`(...-EA SilentlyContinue).<Prop>` 簡寫絕跡
    4) PATH 補強區塊存在（pyenv-win Scripts 自動加入）
    5) Pre-snapshot jsonl count 區塊存在（觀察期 delta 取證可見）

互補關係：本檔做靜態檢查（grep）；行為驗證需 Pester（PowerShell）— 留待 SD_10 W0 補建。
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_NIGHTLY_PS1 = _REPO_ROOT / "tools" / "run_local_nightly.ps1"


@pytest.fixture(scope="module")
def ps1_content() -> str:
    """nightly ps1 內容（UTF-8）。"""
    assert _NIGHTLY_PS1.exists(), f"nightly ps1 missing: {_NIGHTLY_PS1}"
    return _NIGHTLY_PS1.read_text(encoding="utf-8")


def test_strict_mode_3_enabled(ps1_content: str) -> None:
    """case 1：Set-StrictMode -Version 3.0 必須存在（防誤刪）。"""
    assert re.search(
        r"Set-StrictMode\s+-Version\s+3\.0", ps1_content
    ), "Set-StrictMode -Version 3.0 必須啟用（SD_09 W3 R3 P2-2 紀律）"


def test_no_null_property_chain_silentlycontinue_full(ps1_content: str) -> None:
    """case 2：`(...-ErrorAction SilentlyContinue).<Prop>` 鏈式存取絕跡（P0-AUDIT-R18-1）。

    StrictMode 3.0 下 Get-Command 找不到時回 $null → `.Source` / `.Path` / `.Name` 等
    屬性存取拋 PropertyNotFoundException。修復後必須改兩步式：
        $cmd = Get-Command X -ErrorAction SilentlyContinue
        if ($cmd) { $cmd.Source } else { ... }
    """
    pattern = re.compile(
        r"\(\s*[^)]*-ErrorAction\s+SilentlyContinue\s*\)\s*\.\s*[A-Za-z]",
        re.IGNORECASE,
    )
    matches = []
    for i, line in enumerate(ps1_content.splitlines(), start=1):
        # 跳過註解行
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if pattern.search(line):
            matches.append((i, line.strip()))
    assert not matches, (
        "禁止 `(...-ErrorAction SilentlyContinue).<Prop>` 鏈式存取"
        f"（StrictMode 3.0 + $null.Property 拋例外）。違規行：{matches}"
    )


def test_no_null_property_chain_silentlycontinue_short(ps1_content: str) -> None:
    """case 3：`(...-EA SilentlyContinue).<Prop>` 簡寫變體也禁止。"""
    pattern = re.compile(
        r"\(\s*[^)]*-EA\s+SilentlyContinue\s*\)\s*\.\s*[A-Za-z]",
        re.IGNORECASE,
    )
    matches = []
    for i, line in enumerate(ps1_content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if pattern.search(line):
            matches.append((i, line.strip()))
    assert not matches, (
        "禁止 `(...-EA SilentlyContinue).<Prop>` 簡寫鏈式存取。"
        f"違規行：{matches}"
    )


def test_pyenv_path_augmentation_present(ps1_content: str) -> None:
    """case 4：PATH 補強區塊存在（pyenv-win Scripts 自動加入）。

    schtasks 自動跑場景下 PATH 不含 user pyenv-win/Scripts → alembic.exe / 其他 Python
    entry-point exe 找不到 → 各 stage exception。修復後必須在 ps1 開頭偵測 pyenv-win
    並自動補入 Scripts 路徑。
    """
    assert "pyenv-win" in ps1_content, "ps1 必須處理 pyenv-win 環境"
    assert re.search(
        r"\$env:PATH\s*=\s*[\"'].*\$scriptsPath", ps1_content
    ), "ps1 開頭必須有 PATH 補強區塊（將 pyenv-win/Scripts 加入 $env:PATH）"


def test_pre_snapshot_jsonl_count_present(ps1_content: str) -> None:
    """case 5：Pre-snapshot jsonl count + END delta 區塊存在（觀察期取證可見性）。

    紀律 #13：觀察期 jsonl 進度可見 — `delta=0; stage!=0` 才能明示「本次未進帳」。
    """
    assert "PreAc4Count" in ps1_content or "PreMutationCount" in ps1_content, (
        "ps1 必須含 pre-snapshot jsonl count（PreAc4Count / PreMutationCount 等變數）"
    )
    assert "delta=" in ps1_content, "ps1 END observation progress 必須含 delta= 取證"


def test_no_unguarded_get_command_source_pattern(ps1_content: str) -> None:
    """case 6：`Get-Command X -ErrorAction Stop).Source` 雖然 -Stop 會拋例外（被外層
    try/catch 接住），但與 P0-AUDIT-R18-1 同模式 → 為紀律一致性也禁止。

    例外：可包在註解中或 ToolTip 描述（非可執行行）。
    """
    pattern = re.compile(
        r"\(\s*Get-Command[^)]*-ErrorAction\s+Stop\s*\)\s*\.\s*[A-Za-z]",
        re.IGNORECASE,
    )
    matches = []
    for i, line in enumerate(ps1_content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if pattern.search(line):
            matches.append((i, line.strip()))
    assert not matches, (
        "禁止 `(Get-Command X -ErrorAction Stop).<Prop>` 鏈式存取（紀律一致性）。"
        f"違規行：{matches}"
    )


def test_concurrency_guard_mutex_present(ps1_content: str) -> None:
    """case 7（DEF-101-228，R20 真 Windows 機器驗證）：具名 Mutex 去重鎖必須存在，
    且必須在任何 stage（BEGIN log／Stage 1 等）之前就先檢查，防排程觸發與手動重跑
    時間重疊時重複執行整套 gate（mac 側 run_local_nightly.sh 已有對等 mkdir lock）。

    真機驗證（R20）已實測確認：① Global\\ 命名空間下非管理員一般使用者可正常建立
    具名 Mutex；② 另一行程仍持有鎖時 WaitOne(0) 正確回傳 False（非阻塞式互斥）；
    ③ 前一行程未顯式釋放即結束（含 exit N／被砍）後，鎖仍會由 OS 自動回收，不會
    永久卡死下一輪。本測試僅做靜態文字驗證；QA 二審對抗式 bug-injection 發現此
    靜態鎖可被繞過（見下方 `TestConcurrencyGuardBehavior` 的行為驗證）。
    """
    assert "Global\\AutoClaude_Nightly_Run" in ps1_content, (
        "缺具名 Mutex 去重鎖（Global\\AutoClaude_Nightly_Run）——"
        "排程觸發與手動重跑時間重疊時會重複執行整套 gate（DEF-101-228）"
    )
    assert re.search(r"System\.Threading\.Mutex", ps1_content), (
        "去重鎖必須用 System.Threading.Mutex（Windows 原生慣用手法，非 mkdir 土法煉刻）"
    )
    assert "AbandonedMutexException" in ps1_content, (
        "必須處理 AbandonedMutexException——前次持有者未正常釋放鎖時仍應視同成功取得，"
        "不可讓例外未捕捉而讓 stage 中斷"
    )

    mutex_guard_pos = ps1_content.find("Global\\AutoClaude_Nightly_Run")
    begin_log_pos = ps1_content.find("BEGIN nightly run")
    assert mutex_guard_pos != -1 and begin_log_pos != -1, (
        "找不到去重鎖或 BEGIN log 區塊——結構已變動"
    )
    assert mutex_guard_pos < begin_log_pos, (
        "去重鎖必須在 BEGIN nightly run log 之前檢查——否則被鎖擋下的行程仍會建立一份"
        "只含開頭訊息的殘留 log 檔（與 mac 側 ARCH-R15-REV-1 訂正的教訓同構）"
    )


# 🔴 測試專用鎖名必須「每個 pytest 行程獨一」（QA2-R60-04）。
#
# 原本這裡是固定字面 `Global\AutoClaude_Nightly_Run_TestOnly`。`Global\` 是**機器級**
# 命名空間，於是任兩個同時進行的 pytest 行程會共用同一顆核心物件：A 的
# `test_guard_blocks_…` 會讓 holder 子行程持有該鎖 6 秒，這段期間 B 跑到
# `test_guard_proceeds_when_mutex_is_free` 就必然被擋 → 假紅（訊息長得跟真回歸一樣：
# 「另一個 nightly 行程持有去重鎖（…）——本輪跳過」）。R60 複審協定要求四方各自重跑
# 全套，與固定機器級鎖名**結構性衝突**，每一輪都會自造假紅並被誤報成回歸。
#
# 為何加後綴不會削弱 `test_guard_blocks_…` 的鑑別力：該測試驗的是「**另一個行程**持有
# 同一顆具名核心物件時，守門會跳過」。holder 與被測 snippet 兩邊都取用本常數，改名後
# 仍是同一個名稱、同樣的 `Global\` 命名空間、同樣兩個各自獨立的 powershell.exe 子行程
# ——唯一變的是名稱字面，跨行程互斥語意一字未動（落地後實測仍會因 holder 持鎖而擋下，
# 且把 snippet 的守門分支拿掉後該測試立刻轉紅，見 R60 Pkg-P3 鑑別力證明）。
_TEST_MUTEX_NAME = (
    f"Global\\AutoClaude_Nightly_Run_TestOnly_{os.getpid()}_{uuid.uuid4().hex[:8]}"
)


def test_test_mutex_name_is_process_scoped() -> None:
    """QA2-R60-04 回歸鎖：測試專用鎖名不得退回固定字面（否則並行必假紅）。

    刻意**不**加 Windows-only skipif：這是純字串不變量，在 mac/Linux 上也該守住，
    以免「Windows 才跑的鎖」在別的平台被無聲改壞。
    """
    assert _TEST_MUTEX_NAME.startswith("Global\\AutoClaude_Nightly_Run_TestOnly_"), (
        "鎖名必須保留 Global\\ 命名空間與 _TestOnly 前綴（前者是被驗證的跨行程語意，"
        f"後者確保不撞真實排程用的正式鎖）——實際為 {_TEST_MUTEX_NAME!r}"
    )
    assert _TEST_MUTEX_NAME != "Global\\AutoClaude_Nightly_Run_TestOnly", (
        "鎖名退回固定字面 —— 兩個同時進行的 pytest 行程會共用同一顆機器級核心物件，"
        "`test_guard_proceeds_when_mutex_is_free` 必然假紅（QA2-R60-04）"
    )
    assert str(os.getpid()) in _TEST_MUTEX_NAME, (
        "鎖名必須含本行程 pid（行程唯一性的來源）—— 缺 pid 則不同 pytest 行程仍會互撞"
    )
    assert re.fullmatch(
        r"Global\\AutoClaude_Nightly_Run_TestOnly_\d+_[0-9a-f]{8}", _TEST_MUTEX_NAME
    ), (
        "鎖名後綴形態必須為 _<pid>_<uuid 前 8 碼 hex>（pid 擋同時存在的行程、uuid 擋 pid "
        f"回收後的殘留鎖）——實際為 {_TEST_MUTEX_NAME!r}"
    )


def _extract_mutex_guard_snippet(ps1_content: str) -> str:
    """抽出 DEF-101-228 去重鎖判斷片段（`try { ... } catch [...] { ... }` +
    `if (-not $NightlyMutexAcquired) { ... }`），並把正式鎖名代換成測試專用名稱
    ——避免測試執行時撞上真實排程 nightly 使用的正式鎖（`Global\\AutoClaude_Nightly_Run`），
    以免互相干擾或造成測試對真實 nightly run 產生副作用。

    該測試專用名稱**每個 pytest 行程獨一**（QA2-R60-04；理由見 `_TEST_MUTEX_NAME` 上方
    註解——固定字面會讓並行的兩個 pytest 行程共用機器級核心物件而互撞成假紅）。"""
    m = re.search(
        r"try \{\s*\n\s*\$NightlyMutex = New-Object System\.Threading\.Mutex.*?"
        r"\nif \(-not \$NightlyMutexAcquired\) \{.*?\n\}",
        ps1_content, re.DOTALL,
    )
    assert m is not None, "找不到 Mutex 去重鎖判斷片段——結構已變動，需同步更新此測試"
    snippet = m.group(0)
    assert "Global\\AutoClaude_Nightly_Run" in snippet, "抽出片段未含正式鎖名——抽取範圍可能錯位"
    return snippet.replace("Global\\AutoClaude_Nightly_Run", _TEST_MUTEX_NAME)


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] System.Threading.Mutex 具名核心物件跨行程互斥語意，"
    "只在 Windows 上真機驗證有意義（R44 DEF-101-348 標籤，供 "
    "conftest.py::pytest_terminal_summary 彙整可見度）",
)
class TestConcurrencyGuardBehavior:
    """DEF-101-228（R20 QA 二審對抗式 bug-injection 發現）：`test_concurrency_guard_mutex_present`
    只做字面比對——把判斷式改成恆不觸發 skip（邏輯完全廢掉、`Global\\AutoClaude_Nightly_Run`／
    `System.Threading.Mutex`／`AbandonedMutexException` 字面全數保留）該靜態測試仍全綠，是
    真實的假陽性。本測試直接抽出原始碼裡的鎖判斷片段（代換成測試專用 Mutex 名稱，不觸碰
    真實排程用的正式鎖），真機執行驗證兩種真實行為，而非只信任文字存在：
    ① 另一行程持有鎖時會被擋下（不會執行到鎖之後的程式碼）；
    ② 鎖是空的時會正常繼續執行。"""

    def test_guard_blocks_when_another_process_holds_the_mutex(self, ps1_content: str) -> None:
        snippet = _extract_mutex_guard_snippet(ps1_content)
        holder = subprocess.Popen(
            [
                "powershell.exe", "-NoProfile", "-Command",
                f"$m = New-Object System.Threading.Mutex($false, '{_TEST_MUTEX_NAME}'); "
                "$m.WaitOne(0) | Out-Null; Start-Sleep -Seconds 6",
            ],
        )
        try:
            time.sleep(2)  # 讓 holder 行程先取得鎖
            proc = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-Command",
                    f"{snippet}\nWrite-Output 'PAST_GUARD'",
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
            )
            assert "PAST_GUARD" not in proc.stdout, (
                "另一行程持有鎖時，本應被鎖擋下（不執行到鎖之後的 PAST_GUARD 標記）——"
                f"實際輸出：{proc.stdout!r}\n{proc.stderr!r}"
            )
        finally:
            holder.wait(timeout=15)

    def test_guard_proceeds_when_mutex_is_free(self, ps1_content: str) -> None:
        snippet = _extract_mutex_guard_snippet(ps1_content)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", f"{snippet}\nWrite-Output 'PAST_GUARD'"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
        )
        assert "PAST_GUARD" in proc.stdout, (
            f"鎖是空的時應該繼續執行到 PAST_GUARD 標記，實際輸出：{proc.stdout!r}\n{proc.stderr!r}"
        )


# --- adversarial / negative cases（紀律 #4「假 PASS 場景驗證」）-----------------
# SD_09 W3 Round 20 audit P2-F4 修復：原 6 case 全為「正向」grep（pattern 不應存在），
# 缺對抗性 case 驗證 regex 自身能擋住惡意輸入。下列 case 餵 mock 字串給 regex，
# 驗證若 ps1 未來被改回 P0-AUDIT-R18-1 同模式時，靜態鏡子確實會抓到（reject）。

_MALICIOUS_SAMPLES_SILENTLYCONTINUE_FULL = [
    "$x = (Get-Command alembic.exe -ErrorAction SilentlyContinue).Source",
    "  $py = (Get-Command python -ErrorAction SilentlyContinue).Path",
    "if ((Get-Command docker -ErrorAction SilentlyContinue).Name) { }",
]

_MALICIOUS_SAMPLES_SILENTLYCONTINUE_SHORT = [
    "$x = (Get-Command alembic.exe -EA SilentlyContinue).Source",
    "  $py = (Get-Command python -EA SilentlyContinue).Path",
]

_MALICIOUS_SAMPLES_STOP = [
    "$x = (Get-Command alembic.exe -ErrorAction Stop).Source",
    "  $py = (Get-Command python -ErrorAction Stop).Path",
]


def test_regex_rejects_malicious_silentlycontinue_full() -> None:
    """case 7（adversarial）：餵惡意 mock 字串驗證 case 2 regex 真能擋。"""
    pattern = re.compile(
        r"\(\s*[^)]*-ErrorAction\s+SilentlyContinue\s*\)\s*\.\s*[A-Za-z]",
        re.IGNORECASE,
    )
    for sample in _MALICIOUS_SAMPLES_SILENTLYCONTINUE_FULL:
        assert pattern.search(sample), (
            f"regex 漏抓（紀律 #4 假 PASS 風險）：{sample!r}"
        )


def test_regex_rejects_malicious_silentlycontinue_short_and_stop() -> None:
    """case 8（adversarial）：餵惡意 mock 字串驗證 case 3 + case 6 regex 真能擋。"""
    pattern_short = re.compile(
        r"\(\s*[^)]*-EA\s+SilentlyContinue\s*\)\s*\.\s*[A-Za-z]",
        re.IGNORECASE,
    )
    for sample in _MALICIOUS_SAMPLES_SILENTLYCONTINUE_SHORT:
        assert pattern_short.search(sample), (
            f"-EA regex 漏抓（紀律 #4 假 PASS 風險）：{sample!r}"
        )

    pattern_stop = re.compile(
        r"\(\s*Get-Command[^)]*-ErrorAction\s+Stop\s*\)\s*\.\s*[A-Za-z]",
        re.IGNORECASE,
    )
    for sample in _MALICIOUS_SAMPLES_STOP:
        assert pattern_stop.search(sample), (
            f"-Stop regex 漏抓（紀律 #4 假 PASS 風險）：{sample!r}"
        )


# --- Round 21 audit QA P1-R21-2 修復鏡子（紀律 #1 真實 rc） ----------------
def test_cleanup_stage_does_not_force_zero_when_docker_rm_present(ps1_content: str) -> None:
    """case 9（紀律 #1 真實 rc）：Cleanup stage 不可在 docker rm 之後強制 LASTEXITCODE=0
    將真實失敗 rc 吞掉。允許在「未建立 container 不需要 rm」分支內清零。

    舊版違規模式（已修）：
        Invoke-Native { docker rm -f $script:UsedContainer }
        Log "..."
        $global:LASTEXITCODE = 0       # ← 違規：吞掉 docker rm 真實 rc

    修復後模式（Round 21）：保留真實 rc，rc != 0 印 WARN 但不阻斷後續 stage。
    """
    cleanup_idx = ps1_content.find("Stage 'Cleanup'")
    assert cleanup_idx > 0, "ps1 必須含 Cleanup stage"
    # 抓 Cleanup stage 區塊（從 Stage 'Cleanup' 到下一個閉合大括號區塊末）
    block = ps1_content[cleanup_idx : cleanup_idx + 1500]
    # 在同個區塊中，docker rm 之後不應緊跟著 unconditional `$global:LASTEXITCODE = 0`
    docker_rm_idx = block.find("docker rm")
    assert docker_rm_idx > 0, "Cleanup 必須含 docker rm 操作"
    after_docker_rm = block[docker_rm_idx:docker_rm_idx + 400]
    # 模式：必須先取 $rmRc = $global:LASTEXITCODE（保存真實 rc），才視情境處理
    assert "$rmRc" in after_docker_rm or "$rm_rc" in after_docker_rm, (
        "Round 21 修復後：docker rm 之後必須保留真實 rc（變數 $rmRc）"
        "供取證使用。違反紀律 #1（真實 rc）。"
    )


# --- Round 21 audit Architect P1 #4 修復鏡子（observability stage Docker uncoupling） ---
# Note: 不強制 print effective_stages percentage（屬可選 UX 改進，延 SD_10）；
# 此 case 確認 obs stage 不依賴 Docker（mutation/pg-e2e/drift SKIP 時仍可跑）。
def test_observability_stage_independent_of_docker(ps1_content: str) -> None:
    """case 10：observability-snapshot stage 不依賴 Docker（其他 stage SKIP 時仍可跑）。"""
    obs_idx = ps1_content.find("observability-snapshot")
    assert obs_idx > 0, "ps1 必須含 observability-snapshot stage"
    # obs stage scriptblock 應只跑 python tools/observability_snapshot.py，
    # 不含 docker 指令（紀律 #9 對 obs stage 不適用 — obs 是 Docker-independent）
    block = ps1_content[obs_idx:obs_idx + 500]
    # 確認 obs stage 內部不該 invoke docker（否則 SKIP 流程斷裂）
    docker_in_obs = re.search(r"^\s*Invoke-Native\s*\{\s*docker\b", block, re.MULTILINE)
    assert not docker_in_obs, (
        "observability stage 不應 Invoke docker（其應為 Docker-independent；"
        "若需 docker 應走獨立 stage）"
    )


# --- AutoClaude_Improving_012 Phase 0 修復鏡子（紀律 #4：TD-N01 / TD-N03 自身要被驗證） ---
# QA 終審指出：ps1 新增的 (a) perf_results.json 缺檔守門、(b) observability 末筆 UTC 日期
# 整合驗證，兩段「驗證鏡子」自身無測試 → 違反紀律 #4。下列 case 以靜態錨點斷言補齊：
# 若有人刪掉 ps1 對應驗證段（或改掉 fail-loud 分支），這些 case 必須 fail。

_OBS_SNAPSHOT_PY = _REPO_ROOT / "tools" / "observability_snapshot.py"


def _extract_stage_block(ps1_content: str, stage_marker: str, end_marker: str | None = None) -> str:
    """擷取指定 stage scriptblock 原文（靜態錨點檢查用；找不到標記即 fail）。"""
    idx = ps1_content.find(stage_marker)
    assert idx > 0, f"ps1 必須含 stage 標記：{stage_marker}"
    if end_marker is not None:
        end = ps1_content.find(end_marker, idx)
        assert end > idx, f"ps1 stage 區塊找不到結尾標記：{end_marker}"
        return ps1_content[idx:end]
    return ps1_content[idx : idx + 3000]


def test_perf_stage_missing_results_fails_loud(ps1_content: str) -> None:
    """case 11（TD-N01）：perf stage 內 perf_results.json 缺檔 → rc=1 + ERROR log。

    意圖：pytest 跑完後若 tests/perf/conftest.py pytest_sessionfinish hook 未產出
    perf_results.json，本次採集無效（紀律 #1 真實失敗）；不可讓後續 regression check
    的「baseline 或 results 不存在」WARN 分支把 stage 染綠。
    """
    block = _extract_stage_block(ps1_content, "Invoke-Stage 'perf-baseline'")
    guard_idx = block.find("if (-not (Test-Path 'perf_results.json'))")
    assert guard_idx > 0, "perf stage 必須含 perf_results.json 缺檔守門 if（TD-N01）"
    branch = block[guard_idx : guard_idx + 400]
    assert "'ERROR'" in branch, "TD-N01 缺檔分支必須以 ERROR 等級 Log（取證可見）"
    assert "$global:LASTEXITCODE = 1" in branch, (
        "TD-N01 缺檔分支必須標記 stage rc=1（fail-loud；禁止染綠）"
    )
    assert "TD-N01" in branch, "缺檔分支 Log 必須含 TD-N01 取證錨點"


def test_observability_validation_missing_history_branch(ps1_content: str) -> None:
    """case 12（TD-N03 分支 1）：.observability_history.jsonl 缺檔 → rc=1 + ERROR。

    意圖：snapshot 宣稱成功（rc=0）但 jsonl 根本不存在 = 「印 OK 但未落盤」假綠，
    必須 fail-loud。
    """
    block = _extract_stage_block(
        ps1_content, "Invoke-Stage 'observability-snapshot'", "Stage 'Cleanup'"
    )
    assert "'.observability_history.jsonl'" in block, (
        "obs 驗證段必須以 .observability_history.jsonl 為驗證標的"
    )
    guard_idx = block.find("if (-not (Test-Path $histPath))")
    assert guard_idx > 0, "obs 驗證段必須含 jsonl 缺檔守門 if（TD-N03）"
    branch = block[guard_idx : guard_idx + 400]
    assert "'ERROR'" in branch, "TD-N03 缺檔分支必須以 ERROR 等級 Log"
    assert "$global:LASTEXITCODE = 1" in branch, "TD-N03 缺檔分支必須標記 stage rc=1"


def test_observability_validation_parse_failure_try_catch(ps1_content: str) -> None:
    """case 13（TD-N03 分支 2）：jsonl 末筆解析失敗（try/catch）→ rc=1 + ERROR。

    意圖：StrictMode 3.0 下 PSCustomObject 缺 ts 屬性 / 非法 JSON / 非法日期都拋例外，
    必須由 catch 接住並 fail-loud，不可讓例外把 stage rc 留在 snapshot 的 0。
    """
    block = _extract_stage_block(
        ps1_content, "Invoke-Stage 'observability-snapshot'", "Stage 'Cleanup'"
    )
    try_idx = block.find("try {")
    assert try_idx > 0, "obs 驗證段必須以 try/catch 包住 jsonl 末筆解析（TD-N03）"
    assert "ConvertFrom-Json" in block, "obs 驗證段必須解析 jsonl 末筆（ConvertFrom-Json）"
    catch_idx = block.find("} catch {", try_idx)
    assert catch_idx > try_idx, "obs 驗證段 try 之後必須有 catch 分支"
    catch_block = block[catch_idx : catch_idx + 400]
    assert "'ERROR'" in catch_block, "TD-N03 解析失敗分支必須以 ERROR 等級 Log"
    assert "$global:LASTEXITCODE = 1" in catch_block, "TD-N03 解析失敗分支必須標記 stage rc=1"


def test_observability_validation_date_match_branches(ps1_content: str) -> None:
    """case 14（TD-N03 分支 3+4）：末筆 UTC 日期 = 今日 → rc=0；不符 → rc=1 + ERROR。

    意圖：today 與末筆 ts 都必須以 UTC 語意比較（ToUniversalTime + yyyy-MM-dd）；
    日期不符 = snapshot 假綠 → fail-loud；通過分支明確清 rc=0（取證可見）。
    """
    block = _extract_stage_block(
        ps1_content, "Invoke-Stage 'observability-snapshot'", "Stage 'Cleanup'"
    )
    assert re.search(
        r"\(Get-Date\)\.ToUniversalTime\(\)\.ToString\('yyyy-MM-dd'\)", block
    ), "todayUtc 必須以 UTC 日期計算（ToUniversalTime + yyyy-MM-dd）"
    pass_idx = block.find("if ($lastDate -eq $todayUtc)")
    assert pass_idx > 0, "obs 驗證段必須含「末筆 UTC 日期 = 今日」判斷分支（TD-N03）"
    else_idx = block.find("} else {", pass_idx)
    assert else_idx > pass_idx, "日期判斷必須有 else（不符）分支"
    pass_branch = block[pass_idx:else_idx]
    assert "$global:LASTEXITCODE = 0" in pass_branch, "通過分支必須明確標記 rc=0"
    else_branch = block[else_idx : else_idx + 400]
    assert "'ERROR'" in else_branch, "日期不符分支必須以 ERROR 等級 Log"
    assert "$global:LASTEXITCODE = 1" in else_branch, "日期不符分支必須標記 stage rc=1"


def test_mutation_stage_validate_call_requires_version_marker(ps1_content: str) -> None:
    """case 16（TD-N02）：mutation stage 呼叫 validate_mutmut_log.py 必須帶
    --require-version-marker flag。

    意圖：--require-version-marker 預設關閉（零破壞其他呼叫端），nightly ps1 的
    mutation stage 呼叫處是 TD-N02 防護的唯一生效點（防 mutmut 換版後輸出格式
    漂移仍被統計 regex 誤判通過）。若有人移除該 flag，validate_mutmut_log.py
    自身的單元測試仍全綠 → silent regression 回舊行為，本 case 必須 fail。
    """
    block = _extract_stage_block(
        ps1_content, "Invoke-Stage 'mutation-test", "Invoke-Stage 'pg-e2e"
    )
    call_lines = [
        line
        for line in block.splitlines()
        if "validate_mutmut_log.py" in line and not line.strip().startswith("#")
    ]
    assert call_lines, (
        "mutation stage 必須呼叫 tools/validate_mutmut_log.py（log 真實性驗證）"
    )
    for line in call_lines:
        assert "--require-version-marker" in line, (
            "mutation stage 的 validate_mutmut_log.py 呼叫必須帶 "
            "--require-version-marker（TD-N02 防護唯一生效點；缺 flag = "
            f"silent regression）。違規行：{line.strip()}"
        )


def test_observability_ts_field_isomorphic_with_snapshot_tool(ps1_content: str) -> None:
    """case 15（防漂移）：ps1 驗證段 ↔ tools/observability_snapshot.py 的 ts/UTC 語意同構。

    比照 F2 分支 ↔ ac4_nightly_alert_parser.py 的 SSOT 同構樣板（紀律 #4 延伸）：
    ps1 端讀 `$lastRecord.ts` 並轉 UTC 日期；py 端必須同時存在
    `.observability_history.jsonl` 檔名、"ts" 欄位字串與 UTC 語意（timezone.utc）。
    任一端改檔名 / 欄位名 / 時區語意而未同步另一端 = silent drift → 本 case fail。
    """
    assert _OBS_SNAPSHOT_PY.exists(), f"snapshot 工具缺失：{_OBS_SNAPSHOT_PY}"
    py_src = _OBS_SNAPSHOT_PY.read_text(encoding="utf-8")
    block = _extract_stage_block(
        ps1_content, "Invoke-Stage 'observability-snapshot'", "Stage 'Cleanup'"
    )
    # ps1 端錨點：讀 ts 欄位 + UTC 轉換 + jsonl 檔名
    assert re.search(r"\$lastRecord\s*\.\s*ts\b", block), "ps1 端必須讀取 jsonl 記錄之 ts 欄位"
    assert ".ToUniversalTime()" in block, "ps1 端 ts 比較必須走 UTC 語意"
    assert "'.observability_history.jsonl'" in block, "ps1 端必須引用 jsonl 檔名"
    # py 端同構錨點：同檔名 + 同欄位名 + 同 UTC 語意
    assert ".observability_history.jsonl" in py_src, (
        "observability_snapshot.py 必須含 .observability_history.jsonl（檔名同構）"
    )
    assert '"ts"' in py_src, 'observability_snapshot.py 必須含 "ts" 欄位字串（欄位名同構）'
    assert "timezone.utc" in py_src, (
        "observability_snapshot.py 必須以 timezone.utc 寫入 ts（UTC 語意同構）"
    )


# --- R10 四方複審修復鏡子（QA-5 / DEF-101-130：R9 三修復 + R10 四修復零錨點補齊） ---
# QA 發現：本檔的存在理由是「每個 nightly 修復配一個靜態錨點」，但 R9 的
# (a) Stage L local_ci_gate、(b) PG contract、(c) 終端 exit decision 三段皆無錨點——
# 任何人「精簡 nightly」都能無聲退回 R9 前狀態。下列 case 17~24 補齊 R9 + R10 全部錨點。


def test_stage_l_local_ci_gate_present(ps1_content: str) -> None:
    """case 17（R9 (b)）：Stage L 必須實跑 tools/local_ci_gate.ps1 全套。"""
    block = _extract_stage_block(ps1_content, "Invoke-Stage 'local-ci-gate full")
    assert "local_ci_gate.ps1" in block, (
        "Stage L 必須呼叫 tools/local_ci_gate.ps1（R9 (b) 深度回歸；刪除＝push 空窗"
        "期間零全套訊號的無聲退化）"
    )
    assert "local_ci_gate=" in ps1_content, "END summary 必須含 local_ci_gate 欄位"


def test_pg_contract_wired_with_ref_capture(ps1_content: str) -> None:
    """case 18（R9 (a)）：pg-e2e stage 必須跑 PG contract 測試且以 [ref] 捕捉 rc。"""
    assert "tests/contract/test_pg_state_repository_contract.py" in ps1_content, (
        "pg-e2e stage 必須含 PG contract 測試（R9 (a)；CI 停擺期間唯一機械通道）"
    )
    assert "$contractRcRef" in ps1_content, (
        "contract rc 必須以 [ref] 捕捉（不被 collector/progress_check 覆蓋）"
    )
    assert re.search(
        r"if \(\$contractRcRef\.Value -ne 0\)", ps1_content
    ), "contract rc 非零必須回寫 stage rc（fail-loud 分支）"


def test_terminal_exit_decision_present(ps1_content: str) -> None:
    """case 19（R9 (c)）：終端 exit code 必須帶訊號（schtasks Last Result 取證）。"""
    assert "END exit decision" in ps1_content, (
        "ps1 末段必須印 END exit decision（R9 (c)；刪除＝Last Result 恆 0x0 退化）"
    )
    assert "$finalFailures" in ps1_content, "exit 決策必須以 $finalFailures 聚合失敗 stage"
    assert re.search(
        r"-ne \$SKIP_RC -and \$stageRc -ne 0 -and \$stageRc -ne 2", ps1_content
    ), "exit 決策必須維持 SKIP(-1)/WARN(2) 不計失敗的既有語意"
    assert re.search(r"if \(\$finalFailures\.Count -gt 0\) \{ exit 1 \}", ps1_content), (
        "失敗時必須真的 exit 1（判定與 exit 分離但兩者都要在）"
    )


def test_mutation_validate_failure_is_rc1_not_warn(ps1_content: str) -> None:
    """case 20（R10 QA-3 / DEF-101-128）：validate_mutmut_log 失敗必須設 rc=1。

    意圖：rc=2 是 WARN（Invoke-Stage 不算 fail、終端 exit 決策排除）——「防假 pass
    守門自身觸發」若設 rc=2 會 WARN 綠出場，正是 R9 Last Result 修復要杜絕的形狀。
    """
    block = _extract_stage_block(ps1_content, "Invoke-Stage 'mutation-test", "Invoke-Stage 'pg-e2e")
    guard_idx = block.find("if ($validateRc -ne 0)")
    assert guard_idx > 0, "mutation stage 必須含 validate rc 守門分支"
    branch = block[guard_idx : guard_idx + 700]
    assert "$global:LASTEXITCODE = 1" in branch, (
        "validate 失敗分支必須設 rc=1（真實失敗）——不得改回 rc=2 WARN（QA-3）"
    )
    executable = [
        line for line in branch.splitlines() if not line.strip().startswith("#")
    ]
    assert not any("$global:LASTEXITCODE = 2" in line for line in executable), (
        "validate 失敗分支禁止 rc=2（WARN 會讓終端 exit=0 假綠；QA-3）"
    )


def test_recall_pytest_rc_captured_with_ref(ps1_content: str) -> None:
    """case 21（R10 QA-4 / DEF-101-129）：recall pytest rc 必須以 [ref] 捕捉並回寫。

    意圖：collector（恆 return 0）/ progress_check（連紅 3 次才非零）會覆蓋
    $LASTEXITCODE——recall 單日真紅必須當日翻紅（CI 對等 job 該 step 是硬紅）。
    """
    assert "$recallRcRef" in ps1_content, "recall pytest rc 必須以 [ref] 捕捉（QA-4）"
    assert re.search(
        r"if \(\$recallRcRef\.Value -ne 0\)", ps1_content
    ), "recall rc 非零必須回寫 stage rc（fail-loud 分支；QA-4）"


def test_sdd_chaos_stage_mirrors_ci_workflow(ps1_content: str) -> None:
    """case 22（R10 QA-6 / DEF-101-131）：SDD chaos 本地補償 stage 必須存在且入決策。

    意圖：CI 停擺期間 aisdlc-sdd-fsm-chaos-nightly.yml（Rule 9.9.4 必跑）零本地
    補償——FSM 有界停機只在 chaos 情境可測，pre-push `-m "not chaos"` 永遠測不到。
    """
    block = _extract_stage_block(ps1_content, "Invoke-Stage 'sdd-fsm-chaos")
    assert "-m chaos" in block, "chaos stage 必須跑 pytest -m chaos（鏡射 CI step 1）"
    assert "chaos_runner" in block, "chaos stage 必須跑 100 輪 chaos_runner sweep（鏡射 CI step 2）"
    assert "sdd_chaos=" in ps1_content, "END summary 必須含 sdd_chaos 欄位"
    assert re.search(r"@\('sdd_chaos', \$rcChaos\)", ps1_content), (
        "sdd_chaos 必須列入終端 exit 決策 pairs（失敗要翻紅 Last Result）"
    )


def test_docker_skip_streak_escalation(ps1_content: str) -> None:
    """case 23（R10 QA-11 / DEF-101-140）：Docker 連續 SKIP ≥3 必須升級為失敗。

    意圖：單次 SKIP 合理（Docker Desktop 未開），但連續多日＝mutation/pg-e2e/drift
    （含 PG contract 本地對等）長期零機械通道；CI 停擺期間即驗證真空，不可無聲。
    """
    assert ".docker_skip_streak" in ps1_content, "必須以 .docker_skip_streak 檔累計連續 SKIP"
    assert re.search(
        r"if \(\$dockerSkipStreak -ge 3\)[\s\S]{0,200}\$finalFailures \+=", ps1_content
    ), "連續 ≥3 次 Docker SKIP 必須列入 finalFailures（exit 1；QA-11）"
    assert re.search(
        r"elseif \(Test-Path \$skipStreakPath\)", ps1_content
    ), "Docker 恢復可用時必須清零 streak 檔（避免永久紅）"


def test_nightly_log_retention_rotation_present(ps1_content: str) -> None:
    """case 25（R22 DEF-101-200 ARCH-R15-5）：dated nightly log 必須有 14 天保留期輪替。

    意圖：mac 側 run_local_nightly.sh 早於 R15 就有
    `find ... -name 'nightly_mac_2*.log' -mtime +14 -delete`；Windows 側自 R15
    記為已知 backlog（ARCH-R15-5）卻遲遲未落地，log 目錄無界累積。修復後必須：
    ①實際刪除超過 14 天的 dated log，②絕不誤刪 nightly_latest.log 心跳指標檔。
    """
    assert re.search(
        r"-Filter\s+'nightly_2\*\.log'", ps1_content
    ), "必須以 nightly_2*.log pattern 掃描 dated log（與 mac 側 nightly_mac_2*.log 同構）"
    assert re.search(
        r"AddDays\(-14\)", ps1_content
    ), "保留期必須為 14 天（對齊 mac 側既有政策）"
    rotation_idx = ps1_content.find("nightly_2*.log")
    assert rotation_idx > 0, "找不到輪替區塊"
    block = ps1_content[rotation_idx : rotation_idx + 400]
    assert "nightly_latest.log" in block, (
        "輪替判斷式必須明確排除 nightly_latest.log（防誤刪心跳指標檔）"
    )
    assert "Remove-Item" in block, "輪替區塊必須實際執行 Remove-Item（非只是掃描不刪除）"


def test_mutation_gate_asks_the_authority_and_holds_no_threshold(ps1_content: str) -> None:
    """case 24（R10 SA-2 / DEF-101-142 → R71 G-1 改寫）：mutation 判定必須問權威實作。

    意圖（Rule 9 — 為何這件事重要）：舊版在 ps1 裡持有第二份門檻
    `$G0_MUTATION_UNIQUE_SHA_TARGET = 7`，並用自寫的 Get-MutationUniqueCount 掃**整檔**
    算 unique sha 去比對它。但權威 `mutation_baseline_lock.should_lock` 只看
    `history[-CONSECUTIVE_RUNS:]` 的 tail，且有效門檻是 **≥5**
    （`MAX_BACKWARD_COMPAT_MISSING=2` 允許 2 筆 legacy 缺 sha）。
    真實後果（2026-08-03 實測）：should_lock 早已回 `(True, 0.7071…)`、
    `.mutation_baseline.toml` 也真的鎖了，nightly 卻每晚照印
    `[G0-NOT-READY] mutation unique-sha 未達 7` 把 W1 擋著——**兩處門檻各寫各的**。

    本 case 鎖三件事：① 權威被真的呼叫；② ps1 端不再持有任何 mutation 門檻字面值；
    ③ G0 mutation 軌的布林值只由權威回傳決定（不得再出現數值比較）。
    行為層鑑別力（換不同 history 會不會跟著權威改答案）見 `TestMutationLockGateBehavior`。
    """
    assert "function Get-MutationLockGate" in ps1_content, (
        "必須有 Get-MutationLockGate helper（向 should_lock 現場提問）"
    )
    m = re.search(r"(?ms)^function\s+Get-MutationLockGate\s*\{.*?^\}", ps1_content)
    assert m, "抽不到 Get-MutationLockGate 本體"
    body = m.group(0)
    assert "mutation_baseline_lock" in body and "should_lock" in body, (
        "Get-MutationLockGate 必須 import tools/mutation_baseline_lock 並呼叫 should_lock"
        "——不得在 ps1 端重寫鎖定規則"
    )
    # 🔴 反向鎖 ①：門檻字面值不得回到本檔（把 7 改成 5 只是換一個寫死的數字）。
    assert "$G0_MUTATION_UNIQUE_SHA_TARGET" not in ps1_content, (
        "ps1 不得再持有 mutation 門檻常數——這正是 G-1 拔掉的第二份真相源"
    )
    assert "function Get-MutationUniqueCount" not in ps1_content, (
        "自寫的整檔 unique-sha 計數器不得復活：它的射程（整檔）與權威（tail 7 筆）不同，"
        "history 一超過 7 筆就分岔"
    )
    # 🔴 反向鎖 ②：G0 mutation 軌只能是「權威回傳的布林」，不得夾帶任何數值比較。
    assigns = re.findall(r"(?m)^[ \t]*\$g0MutOk\s*=.*$", ps1_content)
    assert len(assigns) == 1, f"$g0MutOk 必須恰有一處賦值，實得 {len(assigns)} 處：{assigns}"
    assign = assigns[0]
    assert "$mutGate.Ok" in assign and "$mutGate.Locked" in assign, (
        f"$g0MutOk 必須同時要求 Ok（量得出來）與 Locked（權威判定）。實得：{assign.strip()!r}"
    )
    assert not re.search(r"-(ge|gt|le|lt|eq|ne)\s", assign), (
        "$g0MutOk 不得出現數值比較——比較就代表 ps1 又自己持有了一個門檻。"
        f"實得：{assign.strip()!r}"
    )
    assert "unique-sha" in ps1_content, (
        "END observation progress 仍須保留 unique-sha 語意標記（人類判讀用；"
        "紀律 #13 契約與 test_end_progress_format_contract_matches_discipline_doc 依賴它）"
    )


# ---------------------------------------------------------------------------
# R69 取證失真修復（S-1a / S-1b / S-1c / S-4）回歸鎖
#
# 事故背景（2026-08-01~02 真機，logs/nightly_latest.log 為證）：
#   8/1 02:00 觸發漏跑 → StartWhenAvailable 於 10:17:53 補跑 → 跑到 sdd-fsm-chaos
#   時機器 10:23:30 睡眠 → 8/2 21:52 才醒 → pytest 自報
#   `34 passed ... in 127828.28s (1 day, 11:30:28)` ＝ 35.6 小時。
# 取證鏈卻完全看不出來，因為兩處數字失真：
#   (a) elapsed 印成 `11:30:41.799`（days 分量被 .NET TimeSpan 'hh' 無聲丟棄）
#   (b) `ac4=41/14` 取整檔原始列數，真實滾動窗閘門其實只有 7/14 且 ready=false
# (b) 的方向偏向「看起來已達標」，比 (a) 更危險——會誤導人去按下升級動作。
# ---------------------------------------------------------------------------


# 「TimeSpan 自訂格式字串以 h 起頭」＝ days 分量會被 .NET 無聲丟棄的 bug 形狀。
# 只錨定開頭字元，不碰內部跳脫（前一版正是死在把 PowerShell 的 `\:` 當成 Python
# 跳脫來寫）。單引號/雙引號、`ToString(` 後的空白皆容忍。
_BARE_HH_FORMAT_RE = re.compile(r"\.ToString\(\s*['\"]h")


def test_bare_hh_format_regex_has_discrimination() -> None:
    r"""紀律 #4：反向鎖的 regex 自身要被驗證（上一版就是漏了這步才交出死鎖）。

    意圖：`test_stage_elapsed_preserves_days_component` 的反向鎖若 regex 寫錯，
    它會「永遠通過」而不是「永遠失敗」——這種壞法在 CI 上完全無聲。本 case 直接
    餵真實形狀的正/反樣本，讓 regex 失去鑑別力時當場翻紅。
    """
    must_hit = [
        r"$e = $sw.Elapsed.ToString('hh\:mm\:ss\.fff')",   # ps1 真實字面（含 PS 跳脫）
        r'$e = $sw.Elapsed.ToString("hh\:mm\:ss")',        # 雙引號變體
        r"  Log ($span.ToString( 'hh\:mm' ))",             # 括號後有空白
        "$e = $sw.Elapsed.ToString('hh:mm:ss')",           # 未跳脫變體（PS 亦合法）
    ]
    for sample in must_hit:
        assert _BARE_HH_FORMAT_RE.search(sample), (
            f"反向鎖 regex 漏抓真實繞過形狀（死鎖風險，紀律 #4）：{sample!r}"
        )
    must_miss = [
        r"return $Span.ToString('d\.hh\:mm\:ss\.fff')",    # Format-Elapsed 內合法 days 格式
        r"$todayUtc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')",
    ]
    for sample in must_miss:
        assert not _BARE_HH_FORMAT_RE.search(sample), (
            f"反向鎖 regex 誤傷合法寫法（會製造假紅）：{sample!r}"
        )


def test_stage_elapsed_preserves_days_component(ps1_content: str) -> None:
    """S-1a：stage 耗時格式必須保留 days 分量。

    意圖（Rule 9 — 為何這件事重要）：.NET TimeSpan 自訂格式的 `hh` 是「小時分量
    0-23」，跨日耗時會被**無聲截斷**成看似正常的數字。這不是美觀問題——35.6 小時
    印成 11:30 會讓「整輪被睡眠凍住並吃掉隔日觸發」這個 P0 完全隱形。
    """
    assert "function Format-Elapsed" in ps1_content, (
        "必須有 Format-Elapsed helper（days-aware 耗時格式化）"
    )
    assert r"d\.hh\:mm\:ss\.fff" in ps1_content, (
        r"TotalDays >= 1 時必須用帶 days 分量的格式 'd\.hh\:mm\:ss\.fff'"
    )
    assert re.search(r"\$elapsed\s*=\s*Format-Elapsed\s+\$sw\.Elapsed", ps1_content), (
        "Invoke-Stage 必須經 Format-Elapsed 取得耗時字串"
    )
    # 反向鎖：Format-Elapsed **函式本體之外**不得再有任何以 'hh' 起頭的 TimeSpan
    # 自訂格式字串——那正是 S-1a 的 bug 形狀（days 分量被 .NET 無聲丟棄）。
    #
    # 🔴 為何要重寫（前一版是零鑑別力的死鎖）：原本寫
    #     re.findall(r"\.ToString\('hh\:mm", ps1_content)
    # Python 的 re 對「非字母」跳脫（`\:`）直接還原成該字元，實際比對的字面是
    # `.ToString('hh:mm`；但 ps1 裡真正的字面是 `.ToString('hh\:mm`（PowerShell 用
    # 反斜線跳脫格式字串裡的 ':'）。兩者永遠對不上 → 恆 0 命中，把真正的繞過塞進
    # ps1 也照樣全綠（實測：注入 `([TimeSpan]::Zero).ToString('hh\:mm\:ss\.fff')`
    # 後本測試仍 2 passed）。改成只比對「格式字串的開頭字元」，完全不依賴內部跳脫，
    # 單引號／雙引號／有無空白／`hh:mm` 或 `hh\:mm` 皆能命中；合法的
    # `'d\.hh\:mm\:ss\.fff'`（開頭是 d）與 `'yyyy-MM-dd'` 不會誤傷。
    fn = re.search(r"(?ms)^function\s+Format-Elapsed\s*\{.*?^\}", ps1_content)
    assert fn, "抽不到 Format-Elapsed 函式本體——反向鎖無法定界"
    fn_first = ps1_content[: fn.start()].count("\n") + 1
    fn_last = ps1_content[: fn.end()].count("\n") + 1
    bare = [
        (i, line.strip())
        for i, line in enumerate(ps1_content.splitlines(), start=1)
        if not (fn_first <= i <= fn_last) and _BARE_HH_FORMAT_RE.search(line)
    ]
    assert bare == [], (
        f"發現 {len(bare)} 處裸 TimeSpan 'hh' 格式化繞過 Format-Elapsed"
        f"（Format-Elapsed 本體＝L{fn_first}~L{fn_last}，該區間內合法）——"
        f"days 分量會再次被無聲丟棄。違規行：{bare}\n"
        "註：**註解行也算**（不留反例免得被複製走）；要在註解裡提到這個壞寫法，"
        "請用文字描述『以小時分量起頭的 TimeSpan 自訂格式』，不要寫出字面。"
    )


def test_slow_stage_emits_warning(ps1_content: str) -> None:
    """S-1c：單一 stage 超過門檻須印 WARN，讓異常耗時在取證鏈裡當場可見。

    意圖：B-01 那輪 stage rc 是 0（真的跑完了），純看 rc 永遠發現不了 35 小時的
    異常。門檻告警是唯一能把「跑完了但不對勁」表面化的機制。
    """
    assert re.search(r"\$STAGE_SLOW_WARN_MINUTES\s*=\s*30", ps1_content), (
        "必須定義 30 分鐘的 stage 耗時告警門檻"
    )
    assert re.search(
        r"\$sw\.Elapsed\.TotalMinutes\s+-gt\s+\$STAGE_SLOW_WARN_MINUTES", ps1_content
    ), "Invoke-Stage 必須比較 TotalMinutes 與門檻（不可用會截斷的 .Minutes 分量）"
    assert "Stage SLOW:" in ps1_content, "超時必須印可 grep 的 `Stage SLOW:` 標記"


def test_ac4_progress_uses_rolling_window_not_raw_record_count(ps1_content: str) -> None:
    """S-1b：AC4 進度分子必須取真實滾動 14 天窗，不得用整檔原始列數。

    意圖（Rule 9）：`ac4=41/14` 這種假數字方向偏向「已達標」，會誘發錯誤的升級
    決策；真實閘門是 ac4_progress_check.filter_recent() 的滾動 14 日曆天窗
    （實測同日 observation_days=7、ready_for_labeled_pr=false）。
    ps1 內**不可**自造第二套滾動窗邏輯——必須呼叫既有權威工具，否則就是新漂移點。
    """
    assert "function Get-Ac4Gate" in ps1_content, "必須有 Get-Ac4Gate helper"
    assert "ac4_progress_check.py" in ps1_content, (
        "Get-Ac4Gate 必須呼叫既有權威工具 ac4_progress_check.py（不自造滾動窗邏輯）"
    )
    assert "ready_for_labeled_pr" in ps1_content, "必須讀取真實 ready 旗標"
    # R71：placeholder 索引不再寫死（END 進度加了 obs/drift 兩軌後索引會位移；
    # 「分子綁到哪個變數」由 test_all_progress_numerators_come_from_authority_gates
    # 以解析 -f 綁定的方式鎖住，比鎖索引字面值強）。
    assert re.search(r"ac4=\{\d+\}/14 rolling-window-days", ps1_content), (
        "END 進度 ac4 分子必須標明是 rolling-window-days（防再被誤讀為列數）"
    )
    # 🔴 R71 收緊（A-3）：舊寫法是
    #     re.search(r"\$ac4Numerator\s*=.*\$ac4Gate\.Days", ps1_content, re.DOTALL)
    # `re.DOTALL` + `.*` 讓 `.` 跨行貪婪吃到檔尾——只要**檔案後面任何地方**出現一次
    # `$ac4Gate.Days`，這條就通過，即使 $ac4Numerator 本身已經被改回 $ac4Count。
    # 今天全檔恰好只有 1 處所以還驗得出紅，多一處引用鎖就自動失效（潛伏假綠）。
    # 改成把三項主張全部綁在**同一行賦值**上：來源是 Days、沒有 $ac4Count 回退、
    # 失敗時印 'unavailable'。
    assigns = re.findall(r"(?m)^[ \t]*\$ac4Numerator\s*=.*$", ps1_content)
    assert len(assigns) == 1, (
        "$ac4Numerator 必須恰有一處賦值（多處＝後面那處可能靜默覆寫前面的正確值，"
        f"本檢查也會只驗到第一處）。實際找到 {len(assigns)} 處：{assigns}"
    )
    assign_line = assigns[0]
    assert "$ac4Gate.Days" in assign_line, (
        "ac4 分子必須來自 Get-Ac4Gate 的 Days，不得回退成 $ac4Count 原始列數。"
        f"實際賦值行：{assign_line.strip()!r}"
    )
    assert "$ac4Count" not in assign_line, (
        "$ac4Numerator 賦值行不得出現 $ac4Count（原始列數 41 對 14 門檻＝假達標，"
        f"正是 S-1b 拔掉的東西）。實際賦值行：{assign_line.strip()!r}"
    )
    # 反向鎖：取不到閘門值時必須印 'unavailable'，**不得**退回原始列數假達標。
    assert "'unavailable'" in assign_line, (
        "Get-Ac4Gate 失敗時必須印 unavailable，不得靜默退回 $ac4Count（那等於把假達標裝回去）。"
        f"實際賦值行：{assign_line.strip()!r}"
    )


def _extract_end_progress_statement(ps1_content: str) -> str:
    """抽出 END observation progress 那一整條（含反引號續行）PowerShell 敘述。"""
    lines = ps1_content.splitlines()
    starts = [
        i
        for i, ln in enumerate(lines)
        if "END observation progress:" in ln and not ln.strip().startswith("#")
    ]
    assert len(starts) == 1, f"ps1 必須恰有一處印 END observation progress，實得 {len(starts)}"
    i = starts[0]
    stmt = [lines[i]]
    while lines[i].rstrip().endswith("`"):
        i += 1
        stmt.append(lines[i])
    return "\n".join(stmt)


def _parse_format_binding(stmt: str) -> tuple[str, list[str]]:
    """把 `("<fmt>" -f $a, $b, …)` 拆成 (格式字串, 依序的引數運算式清單)。"""
    m = re.search(r'\("(?P<fmt>.*?)"\s*-f\s*(?P<args>.*)\)\s*$', stmt, re.DOTALL)
    assert m, f"解析不出 -f 綁定：{stmt[:120]!r}…"
    raw_args = m.group("args").replace("`", " ").replace("\n", " ")
    return m.group("fmt"), [a.strip() for a in raw_args.split(",")]


def test_all_progress_numerators_come_from_authority_gates(ps1_content: str) -> None:
    """R71 G-3：END 進度**每一軌**的分子都必須是判準算出來的值，不得是 jsonl 原始列數。

    意圖（Rule 9 — 為何這件事重要）：「分母是判準門檻、分子卻是原始列數」是本包
    反覆出現的同一種取證失真，而且方向偏向「看起來已達標」——會誘發錯誤的升級動作。
    R69 只修了 ac4 一軌；R71 實測發現 obs（42 列 vs green_streak 42，**巧合相等**）、
    drift（35 列 vs green_streak 26，**已經分岔**）、mutation（整檔 unique-sha vs
    權威只看 tail 7 筆）三軌都還是舊病。

    本 case 不看字面，而是**解析 `-f` 綁定**：把格式字串裡每個 `軌名={n}` 的 n 對到
    第 n 個引數運算式，逐一斷言它來自對應的閘門 helper、且不是 `$*Count`。
    這樣寫的理由：舊版 ac4 鎖用 `re.DOTALL` 跨行比對，只要檔案任何角落出現一次
    `$ac4Gate.Days` 就通過（見 A-3 收緊註解）——位置無關的比對抓不到「分子被換掉」。
    """
    stmt = _extract_end_progress_statement(ps1_content)
    fmt, args = _parse_format_binding(stmt)

    expected_numerator = {
        "mutation": "$mutVerdict",     # should_lock 布林判定（locked/observing/unavailable）
        "ac4": "$ac4Numerator",        # ac4_progress_check 滾動 14 日曆天窗
        "obs": "$obsNumerator",        # observability_ga_check green_streak
        "drift": "$driftNumerator",    # drift_log_ga_check green_streak
    }
    for track, want in expected_numerator.items():
        m = re.search(rf"(?<![A-Za-z_-]){track}=\{{(\d+)\}}", fmt)
        assert m, f"格式字串裡找不到 `{track}={{n}}` 分子欄位"
        idx = int(m.group(1))
        assert idx < len(args), f"{track} 綁到 {{{idx}}} 但 -f 只有 {len(args)} 個引數"
        got = args[idx]
        assert got == want, (
            f"{track} 軌分子必須綁 {want}（權威判準值），實得 {got!r}——"
            "分子換成別的東西就是 S-1b 那種假達標復發"
        )
        assert not got.endswith("Count"), (
            f"{track} 軌分子綁到 jsonl 原始列數 {got!r}：分母是判準門檻、分子卻是列數＝取證失真"
        )

    # obs / drift 的**分母**也必須來自工具回報的 window，不得寫死 30。
    for track, want in (("obs", "$obsWindow"), ("drift", "$driftWindow")):
        m = re.search(rf"(?<![A-Za-z_-]){track}=\{{\d+\}}/(?P<den>\{{(\d+)\}}|\d+)", fmt)
        assert m, f"格式字串裡找不到 `{track}=N/門檻` 形狀"
        den = m.group("den")
        assert den.startswith("{"), (
            f"{track} 軌分母寫死成 {den!r}——門檻必須取工具回報的 window，"
            "否則工具改門檻時 nightly 會拿舊門檻報一個看起來合理的假進度"
        )
        assert args[int(den.strip("{}"))] == want, (
            f"{track} 軌分母必須綁 {want}，實得 {args[int(den.strip('{}'))]!r}"
        )

    # 原始列數只准出現在 records= 欄位（保留 delta 取證用途），順序必須對得上四軌。
    record_slots = [int(n) for n in re.findall(r"records=\{(\d+)\}", fmt)]
    got_records = [args[i] for i in record_slots]
    assert got_records == ["$mutCount", "$ac4Count", "$obsCount", "$driftCount"], (
        f"records= 欄位必須依序綁四軌的 jsonl 原始列數，實得 {got_records}"
    )
    # 語意標記：obs/drift 兩軌的分子若不標明是 green_streak，讀者仍會把它讀成列數。
    assert fmt.count("green_streak") >= 2, (
        "obs / drift 兩軌分子必須各自標明 green_streak 語意（缺標記＝分子會被誤讀為整檔列數，"
        "正是 S-1b 的假達標形狀）"
    )


_DISCIPLINE_MD = _REPO_ROOT / "docs" / "06_quality" / "Nightly_Forensic_Discipline.md"

# ps1 進度行的格式字串在 em dash 之後接一段人類可讀的語意說明（提到
# `mutation_baseline_lock.should_lock` / `ac4_progress_check` 等工具名與 `M-05` 等代號）。
# 那段是**說明**、不是輸出形狀：擷取契約素材前必須切掉，否則工具名會被當成語意標記
# 要求文件照抄，鎖就變成在鎖散文。
_EM_DASH = "—"

# 語意標記的**下限集合**：這幾個標記若從 ps1 消失，分子就會被讀回「整檔列數」
# （S-1b 假達標的原形）。下限之外的標記由 `_semantic_markers_of` 自動納管——ps1 新增
# 標記時文件不同步就會紅，不需要有人記得回來改這個常數。
_REQUIRED_SEMANTIC_MARKERS = frozenset(
    {"unique-sha", "rolling-window-days", "green_streak", "should_lock"}
)


def _end_progress_shape(ps1_line: str) -> str:
    """ps1 進度行裡屬於「輸出形狀」的部分（切掉 em dash 之後的語意說明）。"""
    return ps1_line.split(_EM_DASH, 1)[0]


def _labels_of(text: str) -> set[str]:
    """`x=` 形狀的欄位標籤集合。"""
    return set(re.findall(r"(?<![A-Za-z0-9_-])([A-Za-z][A-Za-z0-9_-]*)=", text))


def _semantic_markers_of(shape: str) -> set[str]:
    """帶連字號／底線的小寫語彙＝語意標記（`green_streak`／`rolling-window-days`…）。

    這類標記**不是 `x=` 形狀**，正是 B-5 的漏洞所在：舊鎖只掃標籤集合，R71 新增的
    `green_streak` / `should_lock` 因此完全逃過。改成機械擷取後，ps1 加語意就自動納管。
    """
    stripped = re.sub(r"\{\d+\}", " ", shape)
    return set(re.findall(r"(?<![A-Za-z0-9_-])[a-z][a-z0-9]*(?:[-_][a-z0-9]+)+", stripped))


def _ps1_denominator_shapes(shape: str) -> dict[str, str | None]:
    """每個欄位的**分母形狀**：None＝無分母／`<dynamic>`＝取自工具的 `{n}`／字面數字。

    分母形狀本身就是語意：`ac4=…/14` 的 14 是常數（文件應逐字寫死），`obs=…/{12}` 的
    分母來自工具回報的 window（文件**不得**填死數字，填了就是把「工具改門檻、nightly
    仍報舊門檻」那個假進度裝回來），而 mutation 軌根本沒有分母（分子是 should_lock
    判定詞、不是分數——文件若還寫 `mutation=U/7` 就是把 R71 拔掉的東西寫回契約）。
    """
    shapes: dict[str, str | None] = {}
    for m in re.finditer(r"(?<![A-Za-z0-9_-])([A-Za-z][A-Za-z0-9_-]*)=\{\d+\}", shape):
        label = m.group(1)
        dm = re.match(r"/(\{\d+\}|\d+)", shape[m.end() :])
        if dm is None:
            den: str | None = None
        elif dm.group(1).startswith("{"):
            den = "<dynamic>"
        else:
            den = dm.group(1)
        prev = shapes.setdefault(label, den)
        assert prev == den, (
            f"ps1 進度行的 {label}= 出現兩種分母形狀（{prev!r} vs {den!r}）——"
            "同名欄位形狀不一致，文件無從對齊"
        )
    return shapes


def _fence_field_values(fence: str) -> dict[str, list[str]]:
    """code fence 裡每個 `x=` 欄位的值（同名欄位如 records= 會有多筆）。"""
    values: dict[str, list[str]] = {}
    for m in re.finditer(r"(?<![A-Za-z0-9_-])([A-Za-z][A-Za-z0-9_-]*)=([^\s;)]*)", fence):
        values.setdefault(m.group(1), []).append(m.group(2))
    return values


def _extract_discipline_13_contract_fence(md: str) -> tuple[str, str]:
    """回傳（紀律 #13 整節, 載明 END 進度契約的 **code fence 內文**）。

    🔴 為何一定要收斂到 fence：#13 的**內文**為了解釋 R69/R71 訂正，本來就會出現
    `green_streak`／`should_lock`／`rolling-window-days`／`/30` 這些字樣。若比對範圍是
    整節，加了語意標記檢查也會**巧合通過**——那是巧合，不是設計，鑑別力仍為零。
    """
    start = md.find("### 紀律 #13")
    assert start > 0, "紀律文件找不到 #13 節"
    end = md.find("### 紀律 #14", start)
    assert end > start, "紀律文件找不到 #13 節結尾（#14 標題）"
    section = md[start:end]
    fences = [
        body
        for body in re.findall(r"(?ms)^```[^\n]*\n(.*?)^```", section)
        if "END observation progress:" in body
    ]
    assert len(fences) == 1, (
        "紀律 #13 必須恰有一個 code fence 載明 END observation progress 契約"
        f"（多個＝兩套契約並存，無從對齊）。實得 {len(fences)} 個"
    )
    fence = fences[0]
    # 自我防呆：抓到的必須真的只是 fence，不是整節。markdown 連結語法
    # （`](`）只會出現在內文、絕不會出現在一行 log 契約裡，用它當哨兵——
    # 若哪天有人把範圍放寬回整節，下面第二個 assert 就會紅。
    prose = section.replace(fence, "")
    assert "](" in prose, (
        "哨兵前提失效：紀律 #13 內文已無 markdown 連結，無法再用它判別「抓到的是 fence "
        "還是整節」。請改用其他只存在於內文的標記，別直接刪掉這道防呆。"
    )
    assert "](" not in fence, (
        "抓到的區塊含 markdown 連結＝抓到的是整節內文而非 code fence。"
        "比對整節會讓語意標記檢查巧合通過（內文本來就在討論 green_streak），鑑別力歸零。"
    )
    return section, fence


def test_end_progress_format_contract_matches_discipline_doc(ps1_content: str) -> None:
    """A-4（B-5 升級）：ps1 實際輸出 ↔ 紀律 #13 **code fence** 契約，機械雙向對齊。

    意圖（Rule 9 — 為何這件事重要）：R69 把 ac4 分子從「整檔列數」改成「滾動 14 日
    曆天窗」並加印 `rolling-window-days` / `ready=` / `records=`，但紀律 #13 還寫著
    舊格式 `ac4=N/14`。兩邊互相矛盾、且**沒有任何機械鎖會發現**——文件於是從「契約」
    退化成「考古紀錄」，下一個讀文件的人會照舊格式去解析 log 或誤判分子語意。

    B-5 揭露初版鎖對此形態**零鑑別力**：它只比對 `x=` 形狀的標籤集合，而 R71 G-1/G-2/G-3
    換掉的是**語意**（mutation 分子→`should_lock` 判定詞、obs/drift 分子→`green_streak`
    且分母改取工具回報的 window），這些都不是 `x=` 形狀，於是 fence 仍逐字寫著
    `mutation=U/7 unique-sha`／`obs=N/30`（把剛修掉的缺陷寫成規範），鎖卻整路是綠的。
    故本鎖擴為三面，素材全部自 ps1 格式字串機械擷取：
      ① 欄位標籤**雙向**（ps1 有 fence 沒有＝漏記；fence 有 ps1 沒有＝考古殘留）
      ② 語意標記（帶連字號／底線的小寫語彙，另設下限集合防 ps1 反向拔掉）
      ③ 分母形狀三態（無分母／字面常數／取自工具的動態值）

    **刻意仍不鎖排版與逐字措辭**：鎖逐字會讓任何文案微調都翻紅（脆弱耦合，最後一定
    被人拿掉），漏欄位／錯分母才是真正會誤導判讀的漂移。
    """
    assert _DISCIPLINE_MD.exists(), f"紀律文件缺失：{_DISCIPLINE_MD}"
    md = _DISCIPLINE_MD.read_text(encoding="utf-8")

    # --- ps1 端：抓 END observation progress 的格式字串本體 ---
    # 註解行要排除：ps1 內另有一則 R19 留下的**舊格式**舉例
    # （`「END observation progress: ac4=4/14」誤導 user`），那是在說明 delta 取證的
    # 由來、不是格式契約；拿它去比對會鎖到已被 R69 取代的形狀。
    ps1_lines = [
        ln
        for ln in ps1_content.splitlines()
        if "END observation progress:" in ln and not ln.strip().startswith("#")
    ]
    assert len(ps1_lines) == 1, (
        "ps1 必須恰有一處印 END observation progress（紀律 #13）；多處＝兩套格式並存，"
        f"文件契約無從對齊。實際找到 {len(ps1_lines)} 處"
    )
    shape = _end_progress_shape(ps1_lines[0])

    # --- 文件端：只取 code fence，不取內文（理由見 _extract_… docstring） ---
    _section, fence = _extract_discipline_13_contract_fence(md)
    doc_values = _fence_field_values(fence)

    # ① 欄位標籤雙向
    ps1_labels = _labels_of(re.sub(r"\{\d+\}", "", shape))
    assert ps1_labels, f"從 ps1 進度行擷取不到任何欄位標籤：{shape.strip()!r}"
    missing = sorted(ps1_labels - set(doc_values))
    assert not missing, (
        f"ps1 進度行印了這些欄位但紀律 #13 的 code fence 沒記載：{missing}——"
        "腳本輸出與文件契約已漂移（R69 就是這樣加了 rolling-window-days/ready= 卻沒同步）。"
        f"ps1 全部標籤={sorted(ps1_labels)}"
    )
    stale = sorted(set(doc_values) - ps1_labels)
    assert not stale, (
        f"紀律 #13 的 code fence 還留著 ps1 已不再印的欄位：{stale}——"
        "契約退化成考古紀錄，照它實作的人會去 parse 一個不存在的欄位"
    )

    # ② 語意標記（機械擷取 + 下限集合）
    ps1_markers = _semantic_markers_of(shape)
    floor_missing = sorted(_REQUIRED_SEMANTIC_MARKERS - ps1_markers)
    assert not floor_missing, (
        f"ps1 進度行少了語意標記 {floor_missing}——沒有它們，分子會被讀回整檔列數"
        "（S-1b 假達標的原形）"
    )
    doc_missing = sorted(m for m in ps1_markers if m not in fence)
    assert not doc_missing, (
        f"ps1 進度行帶了語意標記 {doc_missing}，紀律 #13 的 code fence 卻沒有——"
        "讀者會照 fence 把分子當成別的東西（B-5 就是這個形態：fence 停在 obs=N/30 列數，"
        f"ps1 早已改印 green_streak）。ps1 全部標記={sorted(ps1_markers)}"
    )

    # ③ 分母形狀三態
    for label, den in sorted(_ps1_denominator_shapes(shape).items()):
        for value in doc_values[label]:
            if den is None:
                assert "/" not in value, (
                    f"ps1 的 {label}= 沒有分母，fence 卻寫成 {value!r}——"
                    "把分數形狀寫回契約（`mutation=U/7` 就是這樣把 R71 拔掉的寫死 7 復活）"
                )
            elif den == "<dynamic>":
                assert "/" in value, f"ps1 的 {label}= 有分母，fence 的 {value!r} 卻沒有"
                doc_den = value.rsplit("/", 1)[1]
                assert doc_den and not doc_den.isdigit(), (
                    f"{label} 軌分母取自工具回報的 window，fence 卻填死 {doc_den!r}——"
                    "工具改門檻時文件會繼續宣稱舊門檻（`obs=N/30` 的原形）"
                )
            else:
                assert value.endswith(f"/{den}"), (
                    f"ps1 的 {label}= 分母是常數 {den}，fence 卻寫成 {value!r}"
                )


# G0 四軌的閘門 helper。R71 G-1/G-2 把 mutation 與 drift 兩軌接進來後，
# 「三態契約」不再是兩支函式的巧合，而是四支必須共同遵守的規格。
_GATE_HELPERS = ("Get-Ac4Gate", "Get-ObsGaPass", "Get-DriftGaPass", "Get-MutationLockGate")


def test_ac4_and_obs_gate_helpers_are_stderr_safe(ps1_content: str) -> None:
    """S-1b/S-4（R71 擴到四軌）：閘門 helper 不得依賴呼叫端的 $ErrorActionPreference。

    意圖：PS 5.1 對 native 指令做 `2>&1` 時每行 stderr 會變 ErrorRecord，若當下
    偏好設定是 'Stop' 就成終止性錯誤 → helper 回 Ok=$false → G0 判定永遠印 ERROR。
    被呼叫的 python 工具**常態**會往 stderr 印東西（ac4/obs 的 legacy WARN、
    drift 的 [FAIL] 行、should_lock 的 `reject reason=` 標籤），所以這不是邊角情境。
    本檔開頭目前是 'Continue'，但那是環境剛好對，不是函式自身不變量
    （以 'Stop' 實測確實重現該炸法）。
    """
    for fn in _GATE_HELPERS:
        m = re.search(rf"(?ms)^function\s+{fn}\s*\{{.*?^\}}", ps1_content)
        assert m, f"找不到函式 {fn}"
        assert "$ErrorActionPreference = 'Continue'" in m.group(0), (
            f"{fn} 必須在函式作用域內固定 $ErrorActionPreference='Continue'，"
            "否則呼叫端改成 'Stop' 時會被 stderr 的 WARN 行炸掉並靜默回報失敗"
        )


def test_gate_helpers_stop_at_first_parseable_json(ps1_content: str) -> None:
    """🔴 R73（DEF-101-775）：四支 helper 的 JSON 擷取必須「parse 成功即停」。

    意圖（Rule 9）：舊形態是「見到第一個 `{` 之後**後面全收**」，隱含假設 stderr 一律
    排在 JSON 之前。實測不成立——`observability_ga_check.py` 的 legacy-record WARN
    排在 JSON **之後**，`2>&1` 合流後被接到尾巴 ⇒ ConvertFrom-Json 炸 ⇒ 閘門把
    「已達標 43/30」報成「量不出來」（假未達標，與 R71 要治的假達標同樣是假訊號）。

    為何要**靜態**鎖而不只靠行為鎖：四支之中 `Get-Ac4Gate` **沒有**行為測試，
    只靠行為鎖會漏掉它。本 case 讓四支一起被綁住。
    🔴 R73 二審訂正（Architect N1）：本段初版寫「只有 Get-ObsGaPass 與 Get-DriftGaPass
    有行為測試，`Get-Ac4Gate` 與 `Get-MutationLockGate` 沒有」——**後半為假**，
    `TestMutationLockGateBehavior` 就是抽 `Get-MutationLockGate` 本體餵真 python 跑的。
    四支裡有三支有行為測試。在一輪專門治「治理文件寫假事實」的迭代裡，
    新鎖的 docstring 自己寫了一筆假事實，訂正於此。

    判準取「函式本體內必須出現 break-on-success 的三個要件」，不比對整段字面——
    字面比對會在任何無害重排下假紅（本 repo 已有 `test_bare_hh_format_regex_has_
    discrimination` 那筆「regex 對不上檔案卻沒人發現」的前例）。
    """
    for fn in _GATE_HELPERS:
        m = re.search(rf"(?ms)^function\s+{fn}\s*\{{.*?^\}}", ps1_content)
        assert m, f"找不到函式 {fn}"
        body = m.group(0)
        assert "$jsonText" in body, (
            f"{fn} 必須以 $jsonText 持有「已成功 parse 的那一段」——舊形態直接 join "
            "$jsonLines 丟給 ConvertFrom-Json，尾隨 stderr 會讓它炸（DEF-101-775）"
        )
        assert re.search(r"ConvertFrom-Json\s+-ErrorAction\s+Stop", body), (
            f"{fn} 的試 parse 必須帶 -ErrorAction Stop——函式作用域是 'Continue'，"
            "不帶 Stop 時 ConvertFrom-Json 的錯誤不會進 catch，break 條件永遠測不到"
        )
        assert "break" in body, (
            f"{fn} 必須在第一次 parse 成功時 break——不 break 就會繼續吃後面的 stderr，"
            "等於退回 DEF-101-775 的形態"
        )


def test_gate_helpers_share_three_state_contract(ps1_content: str) -> None:
    """R71（G-1/G-2）：四軌閘門 helper 的三態契約以機械鎖綁在一起。

    意圖（Rule 9）：R71 為 drift 軌新增的 Get-DriftGaPass 與 Get-ObsGaPass 是刻意的
    逐行同構複製（不抽共用層的理由見 ps1 內註解：行為測試要能單獨抽出函式本體真跑）。
    複製最怕的是**只改一邊**——某一支後來被「精簡」掉 rc 檢查或 Ok 三態，就會退回
    A-2 那種「工具壞掉被讀成觀察期未達標」的假訊號，而且只在該軌無聲發生。
    本 case 讓四支共用同一份結構斷言：任何一支缺項，這裡就紅。
    """
    for fn in _GATE_HELPERS:
        m = re.search(rf"(?ms)^function\s+{fn}\s*\{{.*?^\}}", ps1_content)
        assert m, f"找不到函式 {fn}"
        body = m.group(0)
        for field in ("Ok", "Error"):
            assert re.search(rf"\b{field}\s*=", body), (
                f"{fn} 回傳物件必須含 {field} 欄位——缺 Ok 就無法區分「觀察期未達標」"
                "（要等）與「量不出來」（要修工具）"
            )
        assert "$result.Ok = $true" in body, (
            f"{fn} 必須只在真的量到值時才把 Ok 設為 $true（fail-closed）"
        )
        assert "'python unavailable'" in body, (
            f"{fn} 必須在 $script:PyExe 缺席時回 Ok=$false，而不是讓呼叫端拿到預設值"
        )
    # rc 感知：三支「shell out 到 python 並依 rc 判定」的 helper 必須讀 $LASTEXITCODE。
    # （Get-Ac4Gate 例外：ac4_progress_check 的 rc 與 ready 旗標無契約關係，
    #   它取的是 JSON 裡的 ready_for_labeled_pr，不是 rc。）
    for fn in ("Get-ObsGaPass", "Get-DriftGaPass", "Get-MutationLockGate"):
        body = re.search(rf"(?ms)^function\s+{fn}\s*\{{.*?^\}}", ps1_content).group(0)
        assert "$LASTEXITCODE" in body, (
            f"{fn} 必須讀取 $LASTEXITCODE——不看 rc 就等於相信一段可能來自壞掉行程的文字"
            "（A-2 假綠根因）"
        )
        assert "--json" in body or "json.dumps" in body, (
            f"{fn} 必須取結構化 JSON，不得刮人類可讀文字"
        )


def test_obs_ga_helper_consults_exit_code_and_has_three_states(ps1_content: str) -> None:
    """A-2 靜態鎖：Get-ObsGaPass 必須看退出碼，且回傳型別要能表達「量不出來」。

    意圖（Rule 9）：舊版只做 `$raw -match '\\[PASS\\]'`——工具 rc≠0 但輸出裡出現
    `[PASS]` 字樣就回 Pass=$true，nightly 會印出**假的 [G0-READY]**。這包存在的
    理由就是消滅假達標數字，在活載體上種一個是方向性自打臉。行為層鑑別力見
    `TestObsGaPassBehavior`；本 case 只做便宜的結構防刪。
    """
    m = re.search(r"(?ms)^function\s+Get-ObsGaPass\s*\{.*?^\}", ps1_content)
    assert m, "找不到函式 Get-ObsGaPass"
    body = m.group(0)
    assert "$LASTEXITCODE" in body, (
        "Get-ObsGaPass 必須讀取 $LASTEXITCODE——不看 rc 就等於相信一段可能來自壞掉"
        "行程的文字（A-2 假綠根因）"
    )
    assert "--json" in body, (
        "必須走 --json 取結構化 status，不要刮人類可讀文字（[PASS] 三個字太容易被"
        "任何一段輸出偶然滿足）"
    )
    for field in ("Ok", "Pass", "Error"):
        assert re.search(rf"\b{field}\s*=", body), (
            f"回傳物件必須含 {field} 欄位（Ok/Error 三態；缺 Ok 就無法區分"
            "「觀察期未達標」與「工具壞了」）"
        )
    # 反向鎖：呼叫端必須真的把 Ok=$false 印成「量不出來」而不是「未達標」。
    assert "TOOL-UNAVAILABLE" in ps1_content, (
        "G0 gaps 敘述必須能區分 TOOL-UNAVAILABLE（量不出來，要修工具）與"
        "「觀察期未達標」（要等）——兩者處置完全不同"
    )


#: G0 gap 敘述必須承接的診斷欄位（工具 `--json` 已經算出來的東西）。
_GA_DIAGNOSTIC_FIELDS = ("Reason", "SpanDays")


def test_ga_gap_messages_do_not_hardcode_a_false_inequality(ps1_content: str) -> None:
    """🔴 R76 複審 SD-01：G0 gap 敘述不得自己推導 `streak < window` 這種不等式。

    意圖（Rule 9 — 這條測的是「印出來的話會不會是假的」，不是字串長相）：
    R76 之前 `passed` 唯一的來源就是 `green_streak >= window`，所以
    `'... green_streak {0} < window {1}'` 恆為真。R76 給兩支 GA 工具加了 staleness 與
    窗內連續性（sparse）之後，「未達標」不再蘊含「streak 不足」——實測
    `status=sparse green_streak=44 window=30` 會讓那句話印出 **「44 < 30」**。
    它是人判斷 G0 進度的日常介面，一句自打嘴巴的話會把讀者指向錯誤的修法
    （「再等幾天湊滿 streak」），而真因是採集不連續、該修的是排程。

    判準有兩半，缺一都可能全綠而缺陷仍在：
      ① gap 敘述不得帶硬編的 `<` 比較字樣；
      ② 必須帶 `status=` 並承接工具自己算出的診斷欄位（`Reason`／`SpanDays`），
         否則「不印假話」會退化成「什麼都不印」。
    """
    gap_lines = [
        ln for ln in ps1_content.splitlines()
        if "$g0Gaps +=" in ln and ("observability GA" in ln or "drift_log GA" in ln)
    ]
    assert len(gap_lines) >= 2, (
        f"找不到兩支 GA 的 g0Gaps 敘述（實得 {len(gap_lines)} 行）——判準失去量測面")
    for ln in gap_lines:
        assert "TOOL-UNAVAILABLE" in ln or "<" not in ln, (
            "GA gap 敘述帶硬編的 `<` 比較 ⇒ 在 sparse／stale 狀態下會印出數學上為假的"
            f"不等式（實測 44 < 30）：{ln.strip()}")
        if "TOOL-UNAVAILABLE" in ln:
            continue
        assert "status=" in ln, (
            "GA gap 敘述必須印工具的 status（sparse／stale／observing 處置各不相同）："
            f"{ln.strip()}")
    # 兩支 helper 都必須有欄位承接工具算好的診斷，否則呼叫端只能拿 Streak/Window 硬湊。
    for fn in ("Get-ObsGaPass", "Get-DriftGaPass"):
        body = re.search(rf"(?ms)^function\s+{fn}\s*\{{.*?^\}}", ps1_content)
        assert body, f"找不到函式 {fn}"
        for field in _GA_DIAGNOSTIC_FIELDS:
            assert re.search(rf"\b{field}\s*=", body.group(0)), (
                f"{fn} 缺 {field} 欄位 ⇒ 工具算好的 `last_failure_reason`／"
                "`window_span_days` 在進 log 之前就被丟掉（最好的解釋被丟掉，"
                "呼叫端只好硬湊一句話）")
        assert "last_failure_reason" in body.group(0), (
            f"{fn} 必須真的去取 `last_failure_reason`——只宣告欄位不取值＝永遠是空字串")


def _write_fake_python(dir_path: Path, rc: int, payload: str) -> Path:
    """造一支假的 python 載具：把 payload 原樣吐到 stdout，並以指定 rc 結束。

    用 `type` 讀外部檔而不是在 batch 裡 `echo`，是為了完全避開 cmd 的跳脫地獄
    （`{`/`>`/`|` 在 batch 裡都有特殊意義，payload 一旦被 shell 改寫，這個測試
    就會變成在測 batch 跳脫而不是在測 Get-ObsGaPass）。
    """
    (dir_path / "payload.txt").write_text(payload, encoding="ascii")
    fake = dir_path / "fake_python.cmd"
    fake.write_text(
        "@echo off\r\n"
        'type "%~dp0payload.txt"\r\n'
        f"exit /b {rc}\r\n",
        encoding="ascii",
    )
    return fake


_READY_JSON = '{"status": "ready", "green_streak": 41, "window": 30}'
_OBSERVING_JSON = '{"status": "observing", "green_streak": 7, "window": 30}'
_NO_HISTORY_JSON = '{"status": "no_history", "green_streak": 0, "window": 30}'
_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "tools/observability_ga_check.py", line 204, in main\n'
    "    records = _load_history(history_path)\n"
    "MemoryError\n"
)
_LEGACY_PASS_TEXT = "[PASS] green_streak=41 >= window=30 (total 41 records)"

# 🔴 R73（DEF-101-775）：JSON **之後**才出現的 stderr。這是 production 的真實形狀——
# `observability_ga_check.py` 的 legacy-record WARN 走 stderr，而 helper 以 `2>&1` 合流，
# 實測 WARN 排在 JSON 之後（本輪於真檔 `.observability_history.jsonl` 上重現）。
# 舊濾法「見到第一個 `{` 之後**後面全收**」會把這行 WARN 接到 JSON 尾巴 ⇒
# ConvertFrom-Json 拋「Additional text encountered after finished reading JSON」⇒
# Ok=False ⇒ 把「已達標 43/30」報成「量不出來」。整批既有 case 全綠卻抓不到，
# 因為每一個 payload 都是「乾淨 JSON」或「完全沒有 JSON」——真實世界的第三種形狀
# （JSON ＋ 尾隨雜訊）沒有任何 case 覆蓋。
_WARN_AFTER = "[observability_ga_check] WARN: 1 legacy record(s) missing observability_emit_real"
_READY_JSON_THEN_STDERR = f"{_READY_JSON}\n{_WARN_AFTER}\n"
_OBSERVING_JSON_THEN_STDERR = f"{_OBSERVING_JSON}\n{_WARN_AFTER}\n"
# 對照組：雜訊在 JSON **之前**（舊濾法本來就處理得了，修法不得使其退化）。
_STDERR_THEN_READY_JSON = f"{_WARN_AFTER}\n{_READY_JSON}\n"
# fail-closed 組：JSON 起了頭但被截斷 ⇒ 永遠 parse 不完，必須判「量不出來」而非達標。
_TRUNCATED_JSON = '{"status": "ready", "green_streak": 43,\n'


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] 需真的由 PowerShell 執行原生行程才能驗 $LASTEXITCODE "
    "與 2>&1 合流行為；純 grep 證明不了『rc≠0 時不會回 Pass=True』",
)
class TestObsGaPassBehavior:
    """A-2 行為鑑別力：抽出 ps1 裡 Get-ObsGaPass 的**實際文字**，餵假載具真跑。

    WHY 不能只做 grep：上一批交出的三條鎖全是靜態字面比對，其中一條的 regex 根本
    對不上檔案內容卻沒人發現（見 `test_bare_hh_format_regex_has_discrimination`）。
    「有寫鎖」與「鎖擋得住」是兩件事。本類不重打一份函式副本（重打就變成測我自己
    寫的東西、零鑑別力），而是從 ps1 原始碼抽文字執行。

    三態契約（observability_ga_check.py:257 `return 0 if passed else 1`）：
      Ok=True /Pass=True   ← rc=0 且 status=ready
      Ok=True /Pass=False  ← rc≠0 且 status=observing（真正的「還在觀察」）
      Ok=False             ← 量不出來（rc 與 status 不一致／無 JSON／no_history）
    """

    @staticmethod
    def _run(ps1_content: str, tmp_path: Path, rc: int, payload: str) -> dict[str, str]:
        m = re.search(r"(?ms)^function\s+Get-ObsGaPass\s*\{.*?^\}", ps1_content)
        assert m, "抽不到 Get-ObsGaPass 函式本體"
        fake = _write_fake_python(tmp_path, rc, payload)
        history = tmp_path / ".observability_history.jsonl"
        history.write_text('{"ts": "2026-08-02T00:00:00+00:00"}\n', encoding="utf-8")
        probe = tmp_path / "probe.ps1"
        probe.write_text(
            # StrictMode 3.0 與 production 同條件（缺欄位存取必須拋例外並被 catch 接住）
            "Set-StrictMode -Version 3.0\n"
            f"$script:PyExe = '{fake}'\n"
            f"{m.group(0)}\n"
            f"$r = Get-ObsGaPass '{history}'\n"
            'Write-Output ("OK={0}|PASS={1}|RC={2}|STATUS={3}|ERR={4}" -f '
            "$r.Ok, $r.Pass, $r.Rc, $r.Status, $r.Error)\n",
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert proc.returncode == 0, f"probe 執行失敗：\n{proc.stdout}\n{proc.stderr}"
        line = [ln for ln in proc.stdout.splitlines() if ln.startswith("OK=")]
        assert line, f"probe 沒印出結果行：\n{proc.stdout!r}\n{proc.stderr!r}"
        return dict(kv.split("=", 1) for kv in line[-1].split("|"))

    def test_rc0_ready_is_the_only_pass(self, ps1_content: str, tmp_path: Path) -> None:
        got = self._run(ps1_content, tmp_path, rc=0, payload=_READY_JSON)
        assert got["OK"] == "True" and got["PASS"] == "True", got

    def test_rc1_observing_is_ok_but_not_pass(self, ps1_content: str, tmp_path: Path) -> None:
        """真正的「觀察期未達標」：工具健康、判定為 observing。"""
        got = self._run(ps1_content, tmp_path, rc=1, payload=_OBSERVING_JSON)
        assert got["OK"] == "True" and got["PASS"] == "False", got

    def test_nonzero_rc_with_ready_status_is_not_a_pass(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """🔴 A-2 回歸鎖：rc≠0 但輸出宣稱達標 → 絕不可回 Pass=True。

        這是「假的 [G0-READY]」的直接來源：輸出與 rc 不同源（被 shim/wrapper 攔截、
        工具被換掉、輸出被截斷）時，唯一安全的答案是「量不出來」。
        """
        got = self._run(ps1_content, tmp_path, rc=1, payload=_READY_JSON)
        assert got["PASS"] == "False", f"rc≠0 卻回報達標＝假綠：{got}"
        assert got["OK"] == "False", f"rc/status 不一致必須判工具壞掉（Ok=False）：{got}"

    def test_legacy_pass_text_with_nonzero_rc_is_not_a_pass(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """🔴 A-2 回歸鎖（舊實作的原形）：rc=2 + 純文字 `[PASS]` → 舊版回 Pass=True。

        舊版是 `$raw -match '[PASS]'` 且不看 rc，這個 payload 會直接騙過它。
        """
        got = self._run(ps1_content, tmp_path, rc=2, payload=_LEGACY_PASS_TEXT)
        assert got["PASS"] == "False", f"[PASS] 字樣 + rc=2 仍被當成達標＝A-2 假綠復發：{got}"
        assert got["OK"] == "False", got

    def test_crashed_tool_is_distinguishable_from_not_yet_met(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """A-2 另一半：工具壞掉不可被讀成「觀察期未達標」（一個要修、一個要等）。"""
        got = self._run(ps1_content, tmp_path, rc=1, payload=_TRACEBACK)
        assert got["OK"] == "False", f"traceback 必須判工具壞掉，不可回 Ok=True：{got}"
        assert "no JSON" in got["ERR"], got

    def test_no_history_is_not_reported_as_observing(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        got = self._run(ps1_content, tmp_path, rc=1, payload=_NO_HISTORY_JSON)
        assert got["OK"] == "False", f"no_history＝沒資料可判，不是「觀察中」：{got}"

    def test_stderr_after_json_does_not_break_parsing(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """🔴 R73 回歸鎖（DEF-101-775）：JSON 後面跟著 stderr，仍必須量到真值。

        意圖（Rule 9）：這條鎖存在的理由不是「JSON 要能 parse」，而是**方向**——
        舊濾法在這個 payload 下把「已達標」讀成「量不出來」，於是 nightly 印
        `obs=unavailable`、`[G0-NOT-READY]`，而真相是 `green_streak=43/30` 早已達標。
        假未達標和假達標一樣是假訊號：前者讓人白等，後者讓人誤按升級。R71 那包自陳
        「存在的理由就是消滅假達標數字」，卻在同一個閘門種了假未達標——本鎖是它的解藥。

        若有人把濾法改回「見到 `{` 後面全收」，本 case 立刻紅。
        """
        got = self._run(ps1_content, tmp_path, rc=0, payload=_READY_JSON_THEN_STDERR)
        assert got["OK"] == "True", (
            f"JSON 後跟 stderr 被讀成「量不出來」＝DEF-101-775 復發（真值是 ready）：{got}"
        )
        assert got["PASS"] == "True", f"真值為 ready 卻沒判達標：{got}"
        assert got["STATUS"] == "ready", got

    def test_stderr_after_json_preserves_observing_verdict(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """同上但真值是 observing：不可因尾隨 stderr 就從「還在觀察」退化成「量不出來」。"""
        got = self._run(ps1_content, tmp_path, rc=1, payload=_OBSERVING_JSON_THEN_STDERR)
        assert got["OK"] == "True" and got["PASS"] == "False", got
        assert got["STATUS"] == "observing", got

    def test_stderr_before_json_still_works(self, ps1_content: str, tmp_path: Path) -> None:
        """對照組：雜訊在 JSON 之前是舊濾法本來就處理得了的形狀，修法不得讓它退化。"""
        got = self._run(ps1_content, tmp_path, rc=0, payload=_STDERR_THEN_READY_JSON)
        assert got["OK"] == "True" and got["PASS"] == "True", got

    def test_truncated_json_fails_closed(self, ps1_content: str, tmp_path: Path) -> None:
        """fail-closed：JSON 起頭卻被截斷 ⇒ 判「量不出來」，絕不可猜成達標。"""
        got = self._run(ps1_content, tmp_path, rc=0, payload=_TRUNCATED_JSON)
        assert got["OK"] == "False", f"被截斷的 JSON 必須判量不出來：{got}"
        assert got["PASS"] == "False", got


_DRIFT_READY_JSON = (
    '{"status": "ready", "green_streak": 30, "window": 30, "total_records": 35}'
)
_DRIFT_OBSERVING_JSON = (
    '{"status": "observing", "green_streak": 26, "window": 30, "total_records": 35}'
)
_DRIFT_NO_HISTORY_JSON = '{"status": "no_history", "green_streak": 0, "window": 30}'


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] 需真的由 PowerShell 執行原生行程才能驗 $LASTEXITCODE "
    "與 2>&1 合流行為",
)
class TestDriftGaPassBehavior:
    """R71 G-2 行為鑑別力：drift 軌 helper 與 obs 軌同契約，且真的擋得住假達標。

    WHY 要獨立一份而不是相信「它是 Get-ObsGaPass 的複製品」：複製品最常見的壞法就是
    複製時漏掉一段（rc 檢查、no_history 分支）。靜態測試只能證明字串在，證不了行為。
    這裡比照 TestObsGaPassBehavior，從 ps1 抽 **Get-DriftGaPass 的實際文字**餵假載具真跑。
    """

    @staticmethod
    def _run(ps1_content: str, tmp_path: Path, rc: int, payload: str) -> dict[str, str]:
        m = re.search(r"(?ms)^function\s+Get-DriftGaPass\s*\{.*?^\}", ps1_content)
        assert m, "抽不到 Get-DriftGaPass 函式本體"
        fake = _write_fake_python(tmp_path, rc, payload)
        history = tmp_path / ".drift_log_history.jsonl"
        history.write_text(
            '{"ts": "2026-08-03T00:00:00+00:00", "passed": true}\n', encoding="utf-8"
        )
        probe = tmp_path / "drift_probe.ps1"
        probe.write_text(
            "Set-StrictMode -Version 3.0\n"
            f"$script:PyExe = '{fake}'\n"
            f"{m.group(0)}\n"
            f"$r = Get-DriftGaPass '{history}'\n"
            'Write-Output ("OK={0}|PASS={1}|RC={2}|STATUS={3}|STREAK={4}|WINDOW={5}|ERR={6}" -f '
            "$r.Ok, $r.Pass, $r.Rc, $r.Status, $r.Streak, $r.Window, $r.Error)\n",
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert proc.returncode == 0, f"probe 執行失敗：\n{proc.stdout}\n{proc.stderr}"
        line = [ln for ln in proc.stdout.splitlines() if ln.startswith("OK=")]
        assert line, f"probe 沒印出結果行：\n{proc.stdout!r}\n{proc.stderr!r}"
        return dict(kv.split("=", 1) for kv in line[-1].split("|"))

    def test_rc0_ready_is_the_only_pass(self, ps1_content: str, tmp_path: Path) -> None:
        got = self._run(ps1_content, tmp_path, rc=0, payload=_DRIFT_READY_JSON)
        assert got["OK"] == "True" and got["PASS"] == "True", got
        assert got["STREAK"] == "30" and got["WINDOW"] == "30", got

    def test_rc1_observing_carries_the_authoritative_streak(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """真機形態：total_records=35 但 green_streak=26——分子必須是 26 不是 35。"""
        got = self._run(ps1_content, tmp_path, rc=1, payload=_DRIFT_OBSERVING_JSON)
        assert got["OK"] == "True" and got["PASS"] == "False", got
        assert got["STREAK"] == "26", f"分子必須取權威 green_streak，不得是列數 35：{got}"

    def test_nonzero_rc_with_ready_status_is_not_a_pass(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """🔴 回歸鎖：rc≠0 但輸出宣稱達標 → 只能判「量不出來」，絕不可回 Pass=True。"""
        got = self._run(ps1_content, tmp_path, rc=1, payload=_DRIFT_READY_JSON)
        assert got["PASS"] == "False", f"rc≠0 卻回報達標＝假綠：{got}"
        assert got["OK"] == "False", f"rc/status 不一致必須判工具壞掉：{got}"

    def test_crashed_tool_is_distinguishable_from_not_yet_met(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        got = self._run(ps1_content, tmp_path, rc=1, payload=_TRACEBACK)
        assert got["OK"] == "False", f"traceback 必須判工具壞掉，不可回 Ok=True：{got}"
        assert "no JSON" in got["ERR"], got

    def test_no_history_is_not_reported_as_observing(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        got = self._run(ps1_content, tmp_path, rc=1, payload=_DRIFT_NO_HISTORY_JSON)
        assert got["OK"] == "False", f"no_history＝沒資料可判，不是「觀察中」：{got}"


def _mutation_record(kill_rate: float, sha: str | None) -> str:
    """一筆 .mutation_history.jsonl 紀錄（欄位對齊 mutation_baseline_lock.run()）。"""
    rec: dict[str, object] = {
        "timestamp": "2026-08-03T00:00:00+00:00",
        "module": "token_guard",
        "kill_rate": kill_rate,
        "counts": {"killed": 10, "survived": 4},
    }
    if sha is not None:
        rec["source_sha256"] = sha
    return json.dumps(rec, ensure_ascii=False)


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] 要驗的是 PowerShell 5.1 把 inline python 探測碼交給 "
    "CreateProcess 後還原不還原得回來（DEF-101-760 同型），純 python 測不到",
)
class TestMutationLockGateBehavior:
    """🔴 R71 G-1 行為鑑別力：nightly 的 mutation 判定必須**跟著權威一起改答案**。

    WHY 這組是真鎖而不是裝飾：Get-MutationLockGate 走的是 `python -c` inline 探測碼，
    有兩種各自無聲的壞法——(a) PS 5.1 把探測碼的引號吃掉 → SyntaxError → 恆 unavailable
    （本輪 DEF-101-760 就是這個形態）；(b) 有人「順手」把判定改回本地門檻比較 →
    答案與權威分岔。兩者都只有「拿真 python 對不同 history 跑出不同答案」才驗得到。

    這裡刻意用**真的** tools/mutation_baseline_lock.py（不是假載具）：fixture A 正是
    production 現況——7 筆 tail 只有 **5** 個 unique sha（2 筆 legacy 缺欄位），
    權威 should_lock 回 True。任何把門檻寫回 `>= 7` 的實作在這一格必然翻紅。
    """

    @staticmethod
    def _run(ps1_content: str, tmp_path: Path, history_lines: list[str],
             tools_dir: Path | None = None) -> dict[str, str]:
        m = re.search(r"(?ms)^function\s+Get-MutationLockGate\s*\{.*?^\}", ps1_content)
        assert m, "抽不到 Get-MutationLockGate 函式本體"
        history = tmp_path / ".mutation_history.jsonl"
        history.write_text("\n".join(history_lines) + "\n", encoding="utf-8")
        probe = tmp_path / "mut_probe.ps1"
        probe.write_text(
            "Set-StrictMode -Version 3.0\n"
            f"$script:PyExe = '{sys.executable}'\n"
            f"{m.group(0)}\n"
            f"$r = Get-MutationLockGate -HistoryPath '{history}' "
            f"-ToolsDir '{tools_dir or (_REPO_ROOT / 'tools')}'\n"
            'Write-Output ("OK={0}|LOCKED={1}|UNIQUE={2}|TAIL={3}|RECORDS={4}'
            '|BASELINE={5}|RC={6}|REJECT={7}|ERR={8}" -f '
            "$r.Ok, $r.Locked, $r.UniqueSha, $r.Tail, $r.Records, "
            "$r.Baseline, $r.Rc, $r.Reject, $r.Error)\n",
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        assert proc.returncode == 0, f"probe 執行失敗：\n{proc.stdout}\n{proc.stderr}"
        line = [ln for ln in proc.stdout.splitlines() if ln.startswith("OK=")]
        assert line, f"probe 沒印出結果行：\n{proc.stdout!r}\n{proc.stderr!r}"
        return dict(kv.split("=", 1) for kv in line[-1].split("|"))

    def test_production_shape_five_unique_plus_two_legacy_is_locked(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """production 現況：tail 7 筆＝2 筆 legacy 缺 sha + 5 unique sha → 權威判 locked。

        🔴 這一格就是 G-1 的核心鑑別力：舊實作（unique-sha >= 7）在這裡會回
        observing，把 W1 擋住整整 12 天——而 `.mutation_baseline.toml` 早就寫了
        `token_guard = 0.7071`。
        """
        lines = [_mutation_record(0.71, None), _mutation_record(0.71, None)]
        lines += [_mutation_record(0.71, f"{i:064x}") for i in range(5)]
        got = self._run(ps1_content, tmp_path, lines)
        assert got["OK"] == "True", got
        assert got["LOCKED"] == "True", (
            f"權威 should_lock 對此 history 回 True，nightly 必須跟著回 True（否則就是"
            f"又把門檻寫回 ps1 了）：{got}"
        )
        assert got["UNIQUE"] == "5" and got["TAIL"] == "7", got
        assert got["REJECT"] == "", f"鎖定成功不應有拒鎖原因：{got}"

    def test_same_sha_seven_times_is_rejected_with_authority_reason(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """反作弊：同一份源碼跑 7 次不得鎖定，且拒鎖原因必須是權威自己給的標籤。"""
        lines = [_mutation_record(0.71, "a" * 64) for _ in range(7)]
        got = self._run(ps1_content, tmp_path, lines)
        assert got["OK"] == "True" and got["LOCKED"] == "False", got
        assert "sha_not_unique_full" in got["REJECT"], (
            f"拒鎖原因必須轉述 should_lock 寫到 stderr 的 reason 標籤，不得由 ps1 自行詮釋：{got}"
        )

    def test_insufficient_runs_reason_is_surfaced(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        lines = [_mutation_record(0.71, f"{i:064x}") for i in range(3)]
        got = self._run(ps1_content, tmp_path, lines)
        assert got["OK"] == "True" and got["LOCKED"] == "False", got
        assert "insufficient_runs" in got["REJECT"], got

    def test_kill_rate_below_threshold_is_rejected_even_with_seven_unique_sha(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """反向：7 個 unique sha 但 kill_rate 不到門檻 → 仍不鎖。

        意圖：證明 nightly 印的不是「unique sha 數量」這個單一維度——舊實作只看
        unique sha，會在這一格印出達標；權威 should_lock 還要求 tail 全數 ≥
        `target - TOLERANCE - EXTRA_TOLERANCE`（token_guard = 0.68）。
        """
        lines = [_mutation_record(0.50, f"{i:064x}") for i in range(7)]
        got = self._run(ps1_content, tmp_path, lines)
        assert got["OK"] == "True" and got["LOCKED"] == "False", got
        assert "kill_rate_below_threshold" in got["REJECT"], got

    def test_broken_probe_is_unavailable_not_not_yet_met(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """🔴 A-2 同型：探測碼跑不起來（找不到權威模組）→ Ok=False，不可讀成「未達標」。

        這一格同時是 inline 探測碼的**存活哨兵**：若 PS 5.1 把探測碼引號吃掉導致
        SyntaxError，正常 fixture 那幾格會全部退化成 Ok=False；反過來若探測碼永遠
        「成功」，這一格會翻紅。兩個方向都被夾住。
        """
        empty_tools = tmp_path / "no_such_tools"
        empty_tools.mkdir()
        lines = [_mutation_record(0.71, f"{i:064x}") for i in range(7)]
        got = self._run(ps1_content, tmp_path, lines, tools_dir=empty_tools)
        assert got["OK"] == "False", f"找不到權威模組必須判「量不出來」：{got}"
        assert got["LOCKED"] == "False", got
        assert "no JSON" in got["ERR"] or "rc=" in got["ERR"], got


def test_g0_three_track_verdict_is_on_the_live_carrier(ps1_content: str) -> None:
    """S-4：G0 三軌綜合判定必須長在每晚都會跑的 nightly 上。

    意圖：這段判定原本只活在一次性排程任務 AutoClaude_SD09_G0_GateCheck 裡，該任務
    2026-06-29 觸發一次後 NextRunTime 永遠空白 → 此後 34 天零檢查，而三軌其實每晚
    都在動。判定必須接到活載體才有意義。
    三軌各取權威源（unique-sha / ac4 ready / obs GA [PASS]），且**不得**影響 exit
    code——觀察期未滿是預期狀態，接進 finalFailures 會讓每晚都紅（違反紀律 #1）。
    """
    assert "[G0-READY]" in ps1_content, "四軌全過時必須印 [G0-READY]"
    assert "[G0-NOT-READY]" in ps1_content, "未達標必須印 [G0-NOT-READY] 與 gaps"
    assert "function Get-ObsGaPass" in ps1_content, (
        "obs 軌必須取 observability_ga_check 的 [PASS]，不可拿 obs 原始列數當閘門"
    )
    assert re.search(
        r"\$g0MutOk\s+-and\s+\$g0Ac4Ok\s+-and\s+\$g0ObsOk\s+-and\s+\$g0DriftOk", ps1_content
    ), "必須四軌 AND 才判 READY（R71 G-2 起含 drift；任一軌未過即 NOT-READY）"
    # 反向鎖：G0 判定不得污染 exit code。
    assert not re.search(r"finalFailures\s*\+=.*[Gg]0", ps1_content), (
        "G0 判定不得進 finalFailures——那會讓觀察期未滿的每一晚都翻紅"
    )


def test_drift_track_is_wired_into_the_g0_verdict(ps1_content: str) -> None:
    """R71 G-2：觀察期 #3（drift_log）必須進 G0 判定視野。

    意圖（Rule 9 — 為何這件事重要）：#3 的唯一權威判準 tools/drift_log_ga_check.py
    在本輪前是**零 production caller**——舊載體 g0_gate_check.ps1 的標籤寫
    「#3 observability/drift」但實際只查 observability，新載體 nightly 的 G0 又是
    三軌（mutation/ac4/obs）不含它。於是 #3 從來沒有被任何自動載體判定過，
    唯一看得到的數字是 END 進度那個原始列數（2026-08-03 實測 35，印成 `drift=35/30`
    像早就達標；權威 green_streak 其實只有 26，被 2026-06-02 一筆採集失敗
    `drift_log_table_exists=false` 打斷）。「有工具」與「工具被接上」是兩件事。
    """
    assert "function Get-DriftGaPass" in ps1_content, "必須有 Get-DriftGaPass helper"
    m = re.search(r"(?ms)^function\s+Get-DriftGaPass\s*\{.*?^\}", ps1_content)
    assert m, "抽不到 Get-DriftGaPass 本體"
    body = m.group(0)
    assert "drift_log_ga_check.py" in body, (
        "drift 軌必須呼叫既有權威工具 drift_log_ga_check.py（不得在 ps1 內自造 streak 邏輯）"
    )
    assert "green_streak" in body, "必須讀取權威的 green_streak"
    # G0 判定接線
    assigns = re.findall(r"(?m)^[ \t]*\$g0DriftOk\s*=.*$", ps1_content)
    assert len(assigns) == 1, f"$g0DriftOk 必須恰有一處賦值，實得 {len(assigns)} 處：{assigns}"
    assert "$driftGa.Ok" in assigns[0] and "$driftGa.Pass" in assigns[0], (
        f"$g0DriftOk 必須同時要求 Ok（量得出來）與 Pass（達標）。實得：{assigns[0].strip()!r}"
    )
    assert "drift_ga=" in ps1_content, (
        "G0 明細必須印 drift_ga= 欄位，否則人類看不出這一軌被判成什麼"
    )
    # 反向鎖：drift 軌 gap 也要能區分「量不出來」與「未達標」（同 A-2）。
    gap_block = ps1_content[ps1_content.find("$g0Gaps = @()") :]
    drift_gap = re.search(r"drift_log GA TOOL-UNAVAILABLE", gap_block)
    assert drift_gap, (
        "drift 軌的 Ok=$false 必須印成 TOOL-UNAVAILABLE（要修工具），"
        "不可與「observation window 未滿」（要等）混為一談"
    )


def test_trigger_timing_is_reported_and_never_defaults_to_on_time(ps1_content: str) -> None:
    """額外項：桶位漂移可見化——本輪起跑時刻 vs 排定時刻必須印出來。

    意圖（Rule 9）：本機 WakeToRun 實測失效（近 10 天 6 筆 Power-Troubleshooter
    事件 1 的 WakeSourceType 全為 0/Unknown），02:00 從不準時、全靠開機後
    StartWhenAvailable 補跑。腳本改不掉韌體，但可以讓它不再靜默——補跑若跨日，
    隔日觸發會被 MultipleInstances=IgnoreNew 擋掉而該日零紀錄，AC4 滾動 14 日曆
    天窗缺一天就順延。所以「補跑」是觀察期空洞的前兆指標，值得每輪印一行。

    反向鎖重點：取不到排程資訊時**不得**預設成「準時」——那就是這包一路在拔的
    假綠形狀（假達標比沒數字更糟）。
    """
    assert "function Get-NightlyScheduleTiming" in ps1_content, (
        "必須有 Get-NightlyScheduleTiming helper（排定時刻 vs 實際起跑時刻）"
    )
    assert "function Get-ScheduleOffsetMinutes" in ps1_content, (
        "位移計算必須抽成純函式（才驗得起來；混在 CIM 查詢裡就只能靠真排程碰運氣）"
    )
    assert "END trigger timing:" in ps1_content, (
        "END 段必須印可 grep 的 `END trigger timing:` 標記"
    )
    m = re.search(r"(?ms)^function\s+Get-NightlyScheduleTiming\s*\{.*?^\}", ps1_content)
    assert m, "找不到 Get-NightlyScheduleTiming 本體"
    body = m.group(0)
    assert re.search(r"Label\s*=\s*'unknown'", body), (
        "初始 Label 必須是 'unknown'——取不到排程資訊時的預設值不可以是任何"
        "「看起來準時」的字眼"
    )
    assert "'within-grace'" in body and "'off-schedule'" in body, (
        "必須有 within-grace / off-schedule 兩種明確標籤"
    )
    # 反向鎖：unknown 分支不得被寫成 within-grace
    unknown_branch = re.search(
        r"unknown[^\n]*—[^\n]*不代表準時", ps1_content
    )
    assert unknown_branch, (
        "取不到排程資訊的分支必須在 log 裡明說『不代表準時』，"
        "否則讀者會把 unknown 讀成沒問題"
    )


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] Get-ScheduledTask 是 Windows Task Scheduler CIM "
    "provider；位移算術也要在真 PowerShell 的 DateTime 語意下驗",
)
class TestScheduleTimingBehavior:
    """額外項行為驗證：抽 ps1 原文真跑，證明「算得對」且「查不到時不會謊報準時」。"""

    @staticmethod
    def _run(ps1_content: str, tmp_path: Path, body: str) -> str:
        fns = []
        for name in ("Get-ScheduleOffsetMinutes", "Get-NightlyScheduleTiming"):
            m = re.search(rf"(?ms)^function\s+{name}\s*\{{.*?^\}}", ps1_content)
            assert m, f"抽不到 {name} 本體"
            fns.append(m.group(0))
        probe = tmp_path / "sched_probe.ps1"
        probe.write_text(
            "Set-StrictMode -Version 3.0\n" + "\n".join(fns) + "\n" + body,
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(probe)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        assert proc.returncode == 0, f"probe 失敗：\n{proc.stdout}\n{proc.stderr}"
        return proc.stdout.strip()

    def test_offset_arithmetic(self, ps1_content: str, tmp_path: Path) -> None:
        """排定 02:00 下的位移：準時 0／小誤差 3／事故當輪 10:17 → 497／
        01:30 起跑歸給昨天那格（1410，不可算成 -30 而被讀成差不多準時）。"""
        body = (
            "$tod = [timespan]'02:00:00'\n"
            "$cases = @('2026-08-03 02:00:00','2026-08-03 02:03:00',"
            "'2026-08-01 10:17:00','2026-08-03 01:30:00')\n"
            "$out = foreach ($c in $cases) "
            "{ Get-ScheduleOffsetMinutes -ActualStart ([datetime]$c) -ScheduledTimeOfDay $tod }\n"
            'Write-Output ($out -join ",")\n'
        )
        assert self._run(ps1_content, tmp_path, body) == "0,3,497,1410"

    def test_unknown_task_never_reports_within_grace(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """🔴 反向鎖：排程查不到時必須 Ok=False / Label=unknown，絕不謊報準時。"""
        body = (
            "$r = Get-NightlyScheduleTiming -ActualStart (Get-Date) "
            "-TaskName 'AutoClaude_NoSuchTask_R71Probe'\n"
            'Write-Output ("OK={0}|LABEL={1}|OFFSET={2}" -f $r.Ok, $r.Label, $r.OffsetMinutes)\n'
        )
        got = self._run(ps1_content, tmp_path, body)
        assert "OK=False" in got, got
        assert "LABEL=unknown" in got, f"查不到排程卻給了非 unknown 的標籤：{got}"
        assert "within-grace" not in got, f"查不到排程卻謊報準時：{got}"

    def test_real_task_is_read_when_present(self, ps1_content: str, tmp_path: Path) -> None:
        """真機取證：排程存在時要真的讀到它的排定時刻（不是硬寫 02:00）。

        排程未安裝的機器（fresh clone / 別台）走 skip，不製造假紅。
        """
        probe_exists = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "if (Get-ScheduledTask -TaskName 'AutoClaude_Nightly' "
             "-ErrorAction SilentlyContinue) { 'YES' } else { 'NO' }"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        if "YES" not in probe_exists.stdout:
            pytest.skip("本機未安裝 AutoClaude_Nightly 排程（非缺陷）")
        body = (
            "$r = Get-NightlyScheduleTiming -ActualStart (Get-Date)\n"
            'Write-Output ("OK={0}|SCHED={1}|LABEL={2}" -f $r.Ok, $r.Scheduled, $r.Label)\n'
        )
        got = self._run(ps1_content, tmp_path, body)
        assert "OK=True" in got, got
        assert re.search(r"SCHED=\d{2}:\d{2}", got), f"未讀到排定時刻：{got}"


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] 需真的執行 PowerShell 才能驗證 .NET TimeSpan "
    "格式化行為；純 grep 無法證明 days 分量真的被印出來",
)
def test_format_elapsed_runtime_actually_prints_days(ps1_content: str) -> None:
    r"""S-1a 行為驗證：直接抽出腳本裡 Format-Elapsed 的**實際文字**執行。

    WHY 不能只做 grep：格式字串對不對，最終取決於 .NET 怎麼解讀 `d\.hh\:mm\:ss`。
    這正是 DEF-101-249 的教訓——「字面看起來對」與「真的呼叫起來對」是兩件事。
    本測試不重打一份函式（重打就變成測我自己的副本、零鑑別力），而是從原始碼抽文字。
    """
    m = re.search(r"(?ms)^function\s+Format-Elapsed\s*\{.*?^\}", ps1_content)
    assert m, "抽不到 Format-Elapsed 函式本體"
    snippet = m.group(0)
    # 舊格式對照組（PowerShell 單引號字面）。抽成變數是為了避開 Python 引號地獄：
    # 內層需要真正的單引號，直接內嵌會提前終止 Python 字串字面。
    buggy_probe = r"'hh\:mm\:ss'"
    proc = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-Command",
            f"{snippet}; "
            # 35.6 小時＝事故當輪真實跨日耗時；2m52s＝正常 stage 量級
            "$a = New-TimeSpan -Hours 35 -Minutes 30 -Seconds 41; "
            "$b = New-TimeSpan -Minutes 2 -Seconds 52; "
            'Write-Output "$(Format-Elapsed $a)|$(Format-Elapsed $b)'
            f'|$($a.ToString({buggy_probe}))"',
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, f"Format-Elapsed 真機呼叫失敗：\n{proc.stdout}\n{proc.stderr}"
    got = proc.stdout.strip()
    days_fmt, short_fmt, buggy_fmt = got.split("|")
    assert days_fmt.startswith("1."), (
        f"35.5 小時必須印出 days 分量（預期 '1.11:30:41...'），實得 {days_fmt!r}"
    )
    assert short_fmt == "00:02:52.000", f"未滿一天須維持原格式，實得 {short_fmt!r}"
    # 同一句話印出舊格式當對照：證明這個 bug 是真的，不是臆測。
    assert buggy_fmt == "11:30:41", (
        f"舊格式對照組應重現截斷後的 11:30:41（days 被吃掉），實得 {buggy_fmt!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 本輪四項落地的靜態鎖（mutation 監控角色 / AC4 判準 / 排程漂移 / 達標憑證）
# ══════════════════════════════════════════════════════════════════════════════


def test_mutation_stage_skips_only_when_locked_and_sha_already_measured(
    ps1_content: str,
) -> None:
    """ADR-SD09-011 §2.2：mutation 轉監控角色，但**不得**因此漏測真變動。

    意圖（Rule 9 — 為何這條比「有沒有跳過」重要）：把「已鎖定就不再跑」寫成單一條件，
    就會在源碼改動後仍然不跑 —— 那是反作弊的真實破口（改了 code 卻不重測 mutation，
    baseline 從此守著一份不存在的源碼）。所以本鎖釘的是**兩個條件同時成立**才跳過，
    以及「探測不出來時照跑」這個 fail-open 方向。
    """
    assert "function Get-MutationRetestNeeded" in ps1_content, (
        "必須有 Get-MutationRetestNeeded helper（跳過決策要能被單獨檢視）"
    )
    m = re.search(
        r"if \(\$result\.Locked -and \$result\.ShaAlreadyMeasured[^\)]*\) \{\s*\n"
        r"\s*\$result\.Needed = \$false",
        ps1_content,
    )
    assert m, (
        "跳過條件必須是「已鎖定 AND 該 sha 已量過」兩者同時成立——"
        "只看鎖定就跳過＝源碼改了也不重測，是反作弊破口"
    )
    # fail-open 方向：探測失敗必須維持 Needed=$true（預設值即 $true，且不得被改成 $false）
    assert re.search(r"Needed = \$true;", ps1_content), (
        "result 物件的 Needed 預設必須是 $true——探測失敗時要照跑，不得靜默省測"
    )
    assert "Skip mutation-test（監控角色，非失敗）" in ps1_content, (
        "跳過時必須印可 grep 的原因，否則『今晚為何沒跑 mutation』會靜默消失"
    )


def test_ac4_gate_reads_green_streak_and_recognises_stale(ps1_content: str) -> None:
    """ADR-SD09-012 L-6：AC4 閘門值改為 green_streak，且必須認得 status='stale'。

    意圖（Rule 9）：`ready=false` 有兩種成因——「還在累積」與「採集器死了」。
    印成同一句話會讓人繼續等一個不會到的日子（同 A-2 對 obs 軌「還沒到 vs 量不出來」
    的處置）。另一半意圖：門檻（green_streak_required）必須向工具現場問，
    ps1 不得再持有第二份門檻數字。
    """
    assert "$parsed.green_streak_required" in ps1_content, (
        "門檻必須取工具回報的 green_streak_required，不得在 ps1 寫死第二份"
    )
    assert "$parsed.green_streak" in ps1_content, "閘門值必須取 green_streak"
    assert re.search(r"\$result\.Stale\s*=\s*\(\$result\.Status\s+-eq\s+'stale'\)", ps1_content), (
        "必須認得新的 status='stale'（ADR-SD09-012 L-7）"
    )
    assert re.search(r"elseif \(\$ac4Gate\.Stale\)", ps1_content), (
        "G0 gap 敘述必須把 stale 與『連續綠不足』分開——處置完全不同"
    )
    assert "採集停擺" in ps1_content, "stale 的 gap 文案必須明說是採集停擺而非未達標"


def test_schedule_drift_counts_as_failure_and_unmeasured_stays_fail_closed(
    ps1_content: str,
) -> None:
    """R76：排程漂移必須顯著可見**且計入失敗**；「量不出來」仍要紅。

    R75 版的本鎖守的是相反的一半（「已知存量不得製造無限期紅燈」⇒ status=drift 只印
    WARN）。那個豁免的解除條件是「偵測器回報 status=ok」，2026-08-05 提權安裝器執行後
    實測 `status=ok` / rc=0 ⇒ 條件達成，豁免退場，本鎖同步翻向。**保留這段歷史是刻意的**：
    翻向的理由必須留在鎖裡，否則下一個人會以為「drift 計失敗」是從來就有的設計，
    而看不到「暫時豁免會活過它自己的解除條件」這個真正的教訓。

    意圖（Rule 9 — 這裡要守的是**三個方向**，少一邊都會壞）：
      ① 不可靜默：線上排程設定沒有任何自動比對者，五項落差曾連續三輪存活而沒東西轉紅。
         故偵測器呼叫、可 grep 的標記、每輪印出，三者都不得消失。
      ② 漂移即回歸：提權修復已完成，此後任何 drift 都是**回歸**而非存量，必須計入
         finalFailures，且要有自己的標籤（與 task_missing／unmeasured 分得開）。
      ③ fail-closed：status 讀不出來／status=error＝**量不出來**，那是工具或系統壞了，
         必須照樣計入 finalFailures；判定必須是**白名單式**（不看 rc）——缺席那一向
         根本沒有 rc 可讀，以 rc 為主判準時它會靜默通過。
    """
    assert "check_scheduled_task_drift.py" in ps1_content, "必須呼叫排程漂移偵測器"
    assert "[SCHED-DRIFT]" in ps1_content, "輸出必須帶可 grep 的標記"
    # ③ 判定必須白名單式（不看 rc）：缺席那一向沒有 rc 可看
    assert not re.search(
        r"if \(\$schedDriftRc -ne 0\) \{\s*\n\s*\$finalFailures \+=", ps1_content
    ), "以 rc 為主判準時「偵測器缺席」那一向沒有 rc 可讀 → 靜默通過"
    assert re.search(
        r"if \(\$schedDriftStatus -notin @\('ok', 'skip'\)\) \{", ps1_content
    ), (
        "白名單只准留 ok/skip：R76 已把 drift 移出（豁免解除條件 status=ok 已達成）。"
        "把 drift 加回去＝復活一個解除條件早已成立的豁免"
    )
    assert "'task_missing'" in ps1_content, (
        "R75 偵測器新增的 task_missing 必須有專屬分支（訊息＋標籤）"
    )
    for label in ("schedule_drift_task_missing", "schedule_drift_unmeasured",
                  "schedule_drift_regression"):
        assert label in ps1_content, f"缺 {label} 標籤——END 那行必須分得出是哪一種失敗"
    assert re.search(r"\$schedDriftStatus = 'absent'", ps1_content), (
        "偵測器缺席必須寫進狀態字（否則它落在白名單外這件事沒有來源）"
    )
    # ② 豁免退場的史料與一般化教訓不得被清掉（下一個人立新豁免時要看得到）
    assert "立新豁免的規矩" in ps1_content, (
        "本項的一般化教訓（豁免解除條件必須機械可讀＋同時上鎖）必須留在檔內；"
        "刪掉它等於把『暫時豁免＝永久豁免』這個實證重新變成未知"
    )


def _extract_sched_drift_snippet(ps1_content: str) -> str:
    """抽出 [SCHED-DRIFT] 偵測器段 + 它對應的 finalFailures 判定（兩段真原始碼）。

    與 `_extract_mutex_guard_snippet` 同手法：靜態字面比對抓不到「印的字說要計失敗、
    程式卻沒計」這種**行為**缺陷（字面全在，行為相反），故把真程式碼抽出來真跑。
    """
    block = re.search(
        r"\$monoRoot = Split-Path -Parent \$RepoRoot\n.*?\n\} else \{\n.*?\n\}\n",
        ps1_content,
        re.DOTALL,
    )
    assert block is not None, "找不到 [SCHED-DRIFT] 偵測器段——結構已變動，需同步更新此測試"
    # 判定段刻意以「它做什麼」（往 $finalFailures 加 schedule_drift_* 標籤）錨定，
    # **不錨定判準寫法、也不假設 body 幾行**：若錨定 `-notin` 這種形態，判準退回舊寫法時
    # 會在「抽不到片段」就先炸，行為斷言反而永遠沒機會執行——鎖會紅，但紅的理由與真缺陷
    # 無關（R75 實測踩過一次）。改成行索引式：找到那行 `+=`，往上找 col-0 的 `if (`、
    # 往下找 col-0 的 `}`。
    lines = ps1_content.split("\n")
    plus = [
        i for i, ln in enumerate(lines)
        if "$finalFailures +=" in ln
        and ("schedule_drift" in ln or "$schedDriftStatus" in ln)
    ]
    assert len(plus) == 1, f"預期恰一處排程漂移的 finalFailures 寫入，實際 {len(plus)} 處"
    idx = plus[0]
    start = max(i for i in range(idx, -1, -1) if lines[i].startswith("if ("))
    end = min(i for i in range(idx, len(lines)) if lines[i] == "}")
    decision = "\n".join(lines[start:end + 1]) + "\n"
    assert "check_scheduled_task_drift.py" in block.group(0), "抽出片段錯位（未含偵測器路徑）"
    return block.group(0) + "\n$finalFailures = @()\n" + decision


_DRIFT_STUB = "print('[schedule-drift] status=drift')\nraise SystemExit(1)\n"
_TASK_MISSING_STUB = (
    "print('[schedule-drift] status=task_missing')\n"
    "print('  - AutoClaude_WindowsSmoke: bu cun zai')\n"
    "raise SystemExit(1)\n"
)


@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="[WINDOWS-NATIVE-ONLY] 需以 powershell.exe 真跑 ps1 片段驗證分支行為"
    "（判定邏輯本身平台中立，但載具只在 Windows 上存在；標籤供 "
    "conftest.py::pytest_terminal_summary 彙整可見度）",
)
class TestSchedDriftDispositionBehavior:
    """R75 二次訂正（SD 複審）注入式行為鎖：「量不出來」兩個方向都必須真的計入失敗。

    為何非行為鎖不可（Rule 9）：缺席那一向原本印著「無法量測，不當成通過」，而
    `$schedDriftRc` 留在 0 ⇒ 判定看 rc 就必然放行——**字面與行為相反，任何字面鎖都抓不到**。
    偵測器本體刻意 fail-closed（讀不到設定回 rc=1，理由是「量不出來不得當成沒問題」），
    接線層把它反轉回 fail-open，等於把那份設計意圖在最後一哩丟掉。
    觸發條件是真會發生的：偵測器改名／搬走／`$RepoRoot` 上一層不是 monorepo 根。
    """

    def _run(self, ps1_content: str, tmp_path: Path, repo_root: Path) -> str:
        script = tmp_path / "probe.ps1"
        body = (
            "function Log { param([string]$Msg,[string]$Level='INFO') "
            "Write-Output (\"LOG[{0}] {1}\" -f $Level, $Msg) }\n"
            f"$RepoRoot = '{repo_root}'\n"
            f"$script:PyExe = '{sys.executable}'\n"
            f"{_extract_sched_drift_snippet(ps1_content)}\n"
            'Write-Output ("STATUS={0}" -f $schedDriftStatus)\n'
            'Write-Output ("FINALFAILURES={0}" -f ($finalFailures -join \',\'))\n'
        )
        # BOM：PS 5.1 以 ANSI 碼頁讀無 BOM 的 UTF-8 會把片段內的中文毀成亂碼 → parser 爆
        script.write_text(body, encoding="utf-8-sig")
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        return proc.stdout + proc.stderr

    def test_detector_absent_counts_as_failure(self, ps1_content: str, tmp_path: Path) -> None:
        """偵測器缺席（Test-Path 為假）→ 必須計入 finalFailures，不得靜默通過。"""
        repo_root = tmp_path / "mono_absent" / "AutoClaude"
        repo_root.mkdir(parents=True)
        out = self._run(ps1_content, tmp_path, repo_root)
        assert "STATUS=absent" in out, f"缺席未寫進狀態字：\n{out}"
        assert "FINALFAILURES=schedule_drift_unmeasured" in out, (
            f"偵測器缺席＝量不出來，必須計入本輪失敗（否則 nightly 照樣 exit 0）：\n{out}"
        )

    def test_task_missing_counts_as_failure_with_its_own_message(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """`status=task_missing`（受管任務整支不存在）→ 必須計失敗，且訊息不得說「讀不出 status」。

        意圖（Rule 9）兩層：
          ① **不得搭 drift 的便車**：drift 的豁免理由是「那五項設定要提權才能改」，而任務
             不見了的修法（重跑安裝器）不需等那個提權。折進 drift 就等於把「漏跑」這個最強
             訊號從 exit code 上拿掉——漏跑正是整條偵測鏈存在的理由。
          ② **訊息要對**：status 其實讀到了（只是新值），若還印「rc≠0 但讀不出 status」，
             人會去修一個不存在的解析問題，而真正該做的是重跑安裝器。標籤同理要分得出來。
        """
        repo_root = tmp_path / "mono_missing" / "AutoClaude"
        repo_root.mkdir(parents=True)
        detector = tmp_path / "mono_missing" / "tools" / "check_scheduled_task_drift.py"
        detector.parent.mkdir(parents=True, exist_ok=True)
        detector.write_text(_TASK_MISSING_STUB, encoding="utf-8", newline="\n")
        out = self._run(ps1_content, tmp_path, repo_root)
        assert "STATUS=task_missing" in out, f"未解析出新狀態字：\n{out}"
        assert "FINALFAILURES=schedule_drift_task_missing" in out, (
            f"任務缺席必須計失敗，且標籤要與『量不出來』分開（修法不同）：\n{out}"
        )
        assert "讀不出 status" not in out, (
            f"status 已讀到（task_missing），不得印成解析失敗——會把人導向錯的修法：\n{out}"
        )
        assert "install_windows_nightly.ps1" in out, "訊息必須給出可執行的修法（重跑安裝器）"

    def test_drift_counts_as_failure_under_its_own_label(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """R76 翻向：偵測器在、回報 status=drift（rc=1）→ **必須**計入失敗。

        R75 版這一組斷言的是相反結論（drift 不得計失敗），因為當時的漂移修法卡在未執行
        的系統管理員提權。提權已於 2026-08-05 執行、偵測器實測 status=ok ⇒ 豁免的解除
        條件成立，drift 自此是**回歸**。標籤要與 unmeasured 分開：漂移是量到的，
        把它印成「量不出來」會把人導向修工具而不是重跑安裝器。
        """
        repo_root = tmp_path / "mono_drift" / "AutoClaude"
        repo_root.mkdir(parents=True)
        detector = tmp_path / "mono_drift" / "tools" / "check_scheduled_task_drift.py"
        detector.parent.mkdir(parents=True, exist_ok=True)
        detector.write_text(_DRIFT_STUB, encoding="utf-8", newline="\n")
        out = self._run(ps1_content, tmp_path, repo_root)
        assert "STATUS=drift" in out, f"未解析出 status=drift：\n{out}"
        assert "FINALFAILURES=schedule_drift_regression" in out, (
            f"漂移＝回歸，必須計入本輪失敗（豁免已隨 status=ok 退場）：\n{out}"
        )
        assert "schedule_drift_unmeasured" not in out, (
            f"漂移是量到的，不得掛上『量不出來』的標籤（修法完全不同）：\n{out}"
        )


def test_g0_readiness_certificate_is_machine_readable_and_always_written(
    ps1_content: str,
) -> None:
    """R74 D 項：四軌判定必須留下機器可讀憑證，且每輪都寫。

    意圖（Rule 9）：在此之前 [G0-READY] 只是一行文字，需要有人在對的那一晚剛好去讀
    log（而 log 14 天就被輪替刪掉）。使用者問了三輪「這測試測完了嗎」都得不到答案，
    機械成因就是達標事件沒有留下任何可查詢的狀態。
    「每輪都寫」也是判準的一部分：只在達標時寫，就無法區分「還沒達標」與「nightly
    根本沒跑」——後者才是真正危險的狀態（同 AC4 staleness 要防的病）。
    """
    assert "$g0CertPath" in ps1_content, "必須有憑證檔路徑變數"
    assert ".g0_readiness.json" in ps1_content, "憑證必須是 JSON（機器可讀）"
    assert "generated_at" in ps1_content, "憑證必須帶產出時間，否則無法判斷新鮮度"
    assert "recommended_action" in ps1_content, "憑證必須帶下一步建議（供降頻／退場判斷）"
    # 不得只在 ready 分支寫：憑證區塊必須在 [G0-READY]/[G0-NOT-READY] 兩個分支之外
    cert_idx = ps1_content.index("$g0CertPath = ")
    notready_idx = ps1_content.index("[G0-NOT-READY]")
    assert cert_idx > notready_idx, (
        "憑證必須寫在 G0 兩分支之後（每輪都寫），不得只在達標時寫"
    )
    assert "UTF8Encoding($false)" in ps1_content, (
        "憑證不得帶 BOM——第一個消費者是 python json.load，遇 BOM 會炸"
    )
