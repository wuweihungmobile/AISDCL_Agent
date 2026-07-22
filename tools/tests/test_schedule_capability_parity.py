"""tools/tests/test_schedule_capability_parity.py — 排程能力對照契約（R22 DEF-101-233 殘留修復）。

背景：DEF-101-233（R16 Architect 架構檢視）建議補「排程能力對照契約」機械測試，
斷言 mac 支援子命令集合 ⊆ Windows 支援子命令集合；`tools/install_windows_nightly.ps1`
自 R19 建立後，五輪掃描/複審（R19~R22）皆確認此測試從未真正落地——
`tools/check_script_parity.py` 把這對腳本登記為 `_EXEMPT_PAIRS`（放棄字面比對），
註解暗示「行為對等由 test_install_windows_nightly.py 守門」，但該檔實際只驗證
Windows 腳本自身結構，從未跨檔比對 mac 側能力集合，形成「兩邊都以為對方在管」
的治理縫隙（R22 Architect 一審發現）。

設計原則（R22 SD 一審技術指引）：**禁止字面旗標字串集合比對**——mac `--render-only`
與 Windows `-WhatIf` 語意對等但字面完全不同（前者是自訂旗標產出 plist 供 lint，
後者是 PowerShell 原生 `SupportsShouldProcess` 機制），若用字面集合比對會產生假紅。
改用「語意能力 → 各平台實際承載物」的對照表，各自以靜態 regex 從原始碼抽取實際
存在的承載物，逐一比對映射表宣稱的能力是否兩邊都有對應物。
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAC_SCRIPT = _REPO_ROOT / "tools" / "install_mac_nightly.sh"
_WIN_SCRIPT = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"


def _mac_source() -> str:
    assert _MAC_SCRIPT.exists(), f"mac 安裝器缺失：{_MAC_SCRIPT}"
    return _MAC_SCRIPT.read_text(encoding="utf-8")


def _win_source() -> str:
    assert _WIN_SCRIPT.exists(), f"windows 安裝器缺失：{_WIN_SCRIPT}"
    return _WIN_SCRIPT.read_text(encoding="utf-8-sig")


def _mac_case_labels(src: str) -> set[str]:
    """從 `case "${MODE}" in ... esac` 區塊抽出所有字面 case label。"""
    m = re.search(r'case\s+"\$\{MODE\}"\s+in(.*?)\nesac', src, re.DOTALL)
    assert m is not None, "mac 腳本找不到 case \"${MODE}\" in ... esac 區塊——結構已變動"
    block = m.group(1)
    labels: set[str] = set()
    for raw_label in re.findall(r'^\s*([^)#\n]+)\)\s*$', block, re.MULTILINE):
        for part in raw_label.split("|"):
            labels.add(part.strip())
    return labels


def _win_switch_names(src: str) -> set[str]:
    """從 `param( ... )` 區塊抽出所有 `[switch]$Name` 宣告。"""
    m = re.search(r"param\s*\((.*?)\n\)", src, re.DOTALL)
    assert m is not None, "windows 腳本找不到 param( ... ) 區塊——結構已變動"
    return set(re.findall(r"\[switch\]\$(\w+)", m.group(1)))


def test_mac_case_labels_extracted_sane() -> None:
    """靜態抽取本身要抽到已知的四個核心標籤，證明 regex 未失準（鏡子自證）。"""
    labels = _mac_case_labels(_mac_source())
    for expected in ("install", "--uninstall", "--status", "--render-only"):
        assert expected in labels, (
            f"mac case label 抽取遺漏 {expected!r}——regex 可能已與腳本結構脫節，"
            f"抽到的集合：{labels}"
        )


def test_win_switch_names_extracted_sane() -> None:
    """靜態抽取本身要抽到已知的兩個 switch，證明 regex 未失準（鏡子自證）。"""
    switches = _win_switch_names(_win_source())
    assert switches == {"Uninstall", "Status"}, (
        f"windows switch 抽取結果與預期不符（可能新增/刪除了 switch，"
        f"需同步更新本測試的能力對照表）：{switches}"
    )


def test_capability_uninstall_present_on_both_platforms() -> None:
    """能力：uninstall。mac=`--uninstall`；windows=`-Uninstall` switch。"""
    assert "--uninstall" in _mac_case_labels(_mac_source())
    assert "Uninstall" in _win_switch_names(_win_source())


def test_capability_status_present_on_both_platforms() -> None:
    """能力：status query。mac=`--status`；windows=`-Status` switch。"""
    assert "--status" in _mac_case_labels(_mac_source())
    assert "Status" in _win_switch_names(_win_source())


def test_capability_install_default_action_present_on_both_platforms() -> None:
    """能力：install（預設動作，無參數時觸發）。

    mac：`MODE="${1:-install}"` 明確以 install 為預設值；windows：docstring
    明文記載「install（預設）」且無 `$Install` switch（無旗標即走 install 分支，
    非另立旗標），並實際呼叫 `Register-ScheduledTask`（ensure 語意落地，非空殼宣稱）。
    """
    mac_src = _mac_source()
    assert re.search(r'MODE="\$\{1:-install\}"', mac_src), (
        "mac 腳本必須以 install 為 MODE 預設值（無參數呼叫＝安裝）"
    )
    win_src = _win_source()
    assert re.search(r"install（預設）", win_src), (
        "windows 腳本 docstring 必須明文記載「install（預設）」語意"
    )
    assert "Install" not in _win_switch_names(win_src), (
        "windows install 能力應為「無旗標時的預設分支」，不應另立 $Install switch"
        "（與 mac 側「無參數＝install」的預設語意對齊）"
    )
    assert "Register-ScheduledTask" in win_src, (
        "windows install 分支必須實際呼叫 Register-ScheduledTask（ensure 語意，"
        "非僅文件宣稱）"
    )


def test_capability_render_preview_present_on_both_platforms() -> None:
    """能力：render/preview only（不落地執行，僅預覽/產出供檢視）。

    mac=`--render-only <path>`（自訂旗標，產出 plist 供 lint）；
    windows=`-WhatIf`（PowerShell 原生 `SupportsShouldProcess` 機制）。
    **刻意不比較字面旗標字串**——兩者語意對等但字面不同，字面比對會產生假紅
    （R22 SD 一審明確指出的陷阱）。
    """
    assert "--render-only" in _mac_case_labels(_mac_source())
    win_src = _win_source()
    assert re.search(r"SupportsShouldProcess", win_src), (
        "windows 腳本必須以 SupportsShouldProcess 提供 render/preview-only 能力"
        "（PowerShell 原生 -WhatIf 機制，語意對等 mac 側 --render-only）"
    )
    assert re.search(r"\$PSCmdlet\.ShouldProcess\(", win_src), (
        "windows 腳本的實際落地動作（Register-ScheduledTask）必須包在 "
        "$PSCmdlet.ShouldProcess(...) 判斷內，-WhatIf 才能真的攔下執行"
    )
