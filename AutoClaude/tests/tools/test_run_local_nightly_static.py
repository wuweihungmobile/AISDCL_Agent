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

import re
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
