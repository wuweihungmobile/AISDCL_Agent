"""續航情境矩陣（規範性常數表；R218 Q1；DES §2.2、PRD §4.5.11 R-4.5.11-1、REQ-QW-61）。

鍵＝(情境 S1～S6, 平台 win32｜darwin)，值＝`{"primary", "backup", "notify"}` 三欄皆非空；空格＝缺陷
（AT-QW-60 表驅動讀本表）。載具名只准 W1～W6（DES §2.1）或 `absent(platform)`；後者合法，但其
`notify` 欄必須連到出聲管道與 OI 編號（macOS 沒有自動開窗備援，DES S-14、OI-d）。
"""
from __future__ import annotations

ABSENT = "absent(platform)"
PLATFORMS = ("win32", "darwin")
SITUATIONS = ("S1", "S2", "S3", "S4", "S5", "S6")
CARRIERS = ("W1", "W2", "W3", "W4", "W5", "W6")
_OI_MAC = "OI-d"
_VOICE = "失敗鏈終點出聲（handback＋SessionStart 公告＋UserPromptSubmit 提示＋通知佇列）"
_VOICE_MAC = f"到點只出聲（{_OI_MAC}：mac 無自動開窗備援）"

#: 情境說明（人讀；測試不依賴）。
DESCRIPTION = {
    "S1": "互動、視窗開著、主動停工（close 階段或 park --why）、短窗",
    "S2": "互動、視窗開著、撞線",
    "S3": "互動、視窗已關或電腦重開",
    "S4": "無人窗口（AUTOSDD_UNATTENDED）",
    "S5": "週窗（park --at，天級）",
    "S6": "視窗開著但卡死（holder 活著、醒來時刻已過、觀察期內無任何記錄）",
}


def _cell(primary: str, backup: str, notify: str) -> dict:
    return {"primary": primary, "backup": backup, "notify": notify}


_P1 = "W2（付得起）／W1（付不起）"
_B1 = "W4（F4＝RESUME；活窗⇒fork）或 W5，失敗鏈→W6"
_B3 = "W4（無活窗⇒普通 -r）或 W5，依 F4"
_NONE_CTL = "既有（無人窗口不開互動視窗）"
_UNMAN = "W5（既有 planner／哨兵 FRESH 路）"
_S6_P = "W2／W1（已卡死，等觀察期）"
_S6_B = "W4 fork 或 W5（不殺窗；殺窗須 close_stuck_window）"

MATRIX: dict[tuple[str, str], dict] = {
    ("S1", "win32"): _cell(_P1, _B1, _VOICE),
    ("S1", "darwin"): _cell(_P1 + "＋心跳", ABSENT, _VOICE_MAC),
    ("S2", "win32"): _cell("W3（reset＋約 100 秒）；已掛 W1 者在 reset＋s 醒", "W6", _VOICE),
    ("S2", "darwin"): _cell("W3（reset＋約 100 秒）", "W6", _VOICE_MAC),
    ("S3", "win32"): _cell("W6（holder 行程已死，主載具不存在）", _B3, _VOICE),
    ("S3", "darwin"): _cell("W6（holder 行程已死，主載具不存在）", ABSENT, _VOICE_MAC),
    ("S4", "win32"): _cell(_UNMAN, "W6", _NONE_CTL),
    ("S4", "darwin"): _cell(_UNMAN, "W6", _NONE_CTL),
    ("S5", "win32"): _cell("W1（同一目標，並掛）", "W4／W5（WakeToRun），fire＝目標＋10 分",
                           _VOICE),
    ("S5", "darwin"): _cell("W1（同一目標，並掛）＋心跳", ABSENT, _VOICE_MAC),
    ("S6", "win32"): _cell(_S6_P, _S6_B, _VOICE),
    ("S6", "darwin"): _cell(_S6_P, ABSENT, _VOICE_MAC),
}
