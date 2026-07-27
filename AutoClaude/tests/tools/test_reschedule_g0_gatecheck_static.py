"""tests/tools/test_reschedule_g0_gatecheck_static.py — G0 gate-check 排程腳本的成功判定鎖。

WHY（真實事故，非假想風險；2026-07-27 真 Windows 原生機器實測）：
`AutoClaude/tools/reschedule_g0_gatecheck.ps1` 設定四項排程電源／補跑保護
（StartWhenAvailable／WakeToRun／DisallowStartIfOnBatteries=False／
StopIfGoingOnBatteries=False），但成功判定只驗其中 **2 項**（NextRunTime ＋
StartWhenAvailable），且只印 3 行中的 2 項。實測當下本機已安裝的
`AutoClaude_SD09_G0_GateCheck` 的 `StopIfGoingOnBatteries` 是 `True`（schtasks 預設），
腳本仍印 `[OK] ... with catch-up protection`。

危害不是「少印一行」而是**維運者被騙**：筆電執行中切到電池 → 工作排程器當場砍掉
行程 → gate check 的取證輸出被截斷或全無；而維運者已經看到 [OK]，不會回頭查。
四項是四個彼此獨立的失敗模式，缺一即破，所以四項都必須是成功判定的一部分。

純 Windows（Task Scheduler）機制：macOS launchd 無 `StopIfGoingOnBatteries` 這類欄位，
R1~R57 在 macOS 上模擬時不可能發現。

本檔做兩層鎖：
  1. 靜態層：四項都被印出、四項都在成功判定式內、判定式與姊妹腳本
     `fix_nightly_catchup.ps1` 逐字同一份（禁止兩支腳本養出兩套「設定正確」定義）、
     目標時間不得重複硬編。
  2. 行為層：把腳本裡**真正那一行**判定式抽出來丟給真的 PowerShell 執行，對五組
     合成輸入斷言紅／綠——這才證明四項每一項都是承載的（load-bearing），
     而非只是寫在式子裡好看。靜態子字串比對擋不住「加了項但極性寫反」。

──────────────────────────────────────────────────────────────────────────────
2026-07-27 第二批（本檔第二個主題）：**排程腳本硬編日曆日期＝會自己過期的缺陷**

原腳本 `$TargetWhen = Get-Date '2026-06-29 09:00:00'` 是硬編日曆時刻。過了那天再跑，
一次性 trigger 就被設在**過去**。這不是「日期不好看」而是兩層實害：
  * 實測（本機 Windows 11 build 26100 / Windows PowerShell 5.1.26100.8875，非提權，
    用可丟棄的臨時任務量測）：一次性 trigger 的 `-At` 落在過去時
    `NextRunTime` 讀回來是 **`$null`**；設在未來則讀回精確時刻。腳本底部的驗證式
    要求 `$info.NextRunTime` 非 null，**故照官方文件跑官方腳本反而得到
    `[FAIL] reschedule did not fully take effect` ＋ exit 1**，即使寫入其實成功。
  * 換一個未來日期只是把過期時間往後挪，同一個缺陷會再發生一次——這正是本 repo
    反覆抓到的形態，故本檔的鎖是「功能碼裡不准有日曆日期字面」，不是「日期要夠新」。

因此本檔在原有兩層鎖之外，另鎖三件事（對應修復包 N 的三條回歸鎖）：
  ① 默認時間不得落在過去——把 `Get-G0TargetWhen`（刻意寫成純函式、不內含
     `Get-Date`）抽出來丟給真 PowerShell，以**合成時鐘**掃過整日各時刻與月末／年末／
     閏年翻頁，斷言結果恆在未來且是「下一個」而非某個遙遠的時刻。
  ② 使用者給過去時間必須 fail loud——靜態鎖「拒絕判定在任何排程寫入之前」＋行為層
     真跑腳本（`-When` 給過去時刻）斷言 rc=1 與拒絕訊息。
  ③ 印出的 expected 時間必須與實際設定的一致——上一輪修掉的缺陷（兩處各自硬編、
     對 2099 年的排程仍印 2026-06-29）不得回歸。
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[2]
_RESCHEDULE_PS1 = _AUTOCLAUDE_ROOT / "tools" / "reschedule_g0_gatecheck.ps1"
_FIX_CATCHUP_PS1 = _AUTOCLAUDE_ROOT / "tools" / "fix_nightly_catchup.ps1"

# PowerShell 執行檔的探測一律走 monorepo 根的 SSOT，不在本檔自帶第三份實作
# （ARCH-R58R1-03）。本檔原本寫成 `platform.system() == "Windows"` → `which("powershell.exe")`，
# 非 Windows 分支只回 `which("pwsh")`、**不兜底 powershell**，與 SSOT 語意已分歧；而 SSOT 自己
# 的登記表（`tools/tests/test_platform_guard_availability.py::_CAPABILITY_PROVENANCE`）當輪就
# 寫著「凡需要 PowerShell 能力者一律走 powershell_exe()」——同一輪內政策自相矛盾。
#
# `.exe` 後綴不需要（已實測，非推測）：2026-07-27 於真 Windows 11 Pro + Windows PowerShell 5.1
# 實測 `shutil.which("powershell")` 回 `C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.EXE`
# ——`which` 本身會套用 PATHEXT，故裸名可解析，第三份實作沒有任何情境上的必要性，直接刪。
#
# 跨子專案 import 的先例：`AutoClaude/tests/integration/test_sdd_bridge/test_rollback_compat.py`
# 同樣以 parents[N] 上溯 monorepo 根取用根層資產。以 `as _ps_exe` 保留原呼叫名，讓所有既有
# `skipif(_ps_exe() is None, ...)` 與呼叫點不必連帶改動（Rule 3：只動必須動的）。
# 呼叫端鎖見 `tools/tests/test_platform_guard_availability.py::PowerShellExeSsotCallsiteLock`。
sys.path.insert(0, str(_AUTOCLAUDE_ROOT.parent / "tools" / "tests"))
from _platform_helpers import powershell_exe as _ps_exe  # noqa: E402

# 四項電源／補跑保護設定 → 期望值（True 代表「屬性必須為真」）。
# 這不是可機械推導的清單，而是「Task Scheduler 有哪些漏跑/中斷開關」的領域知識，
# 故顯式登記；新增第五項風險時同步補此表與兩支 .ps1。
_POWER_SETTINGS: dict[str, bool] = {
    "StartWhenAvailable": True,          # 關機錯過排程窗口後補跑
    "WakeToRun": True,                   # 睡眠／休眠中喚醒機器準時執行
    "DisallowStartIfOnBatteries": False,  # 吃電池時不擋啟動
    "StopIfGoingOnBatteries": False,     # 執行中切到電池不被中途砍掉
}

# 判定式所在行的錨（腳本內以 $powerOk 匯總四項）。
_POWER_OK_LINE = re.compile(r"^\s*(\$powerOk\s*=\s*.+)$", re.MULTILINE)

# 「目標時刻不在未來就拒絕」那一行的錨。刻意要求 `-le` 而非 `-lt`：與 `$now` 相等的
# 時刻不算「在未來」，等到真的寫入時它已經是過去。
_PAST_GUARD_LINE = re.compile(r"^\s*if \((\$TargetWhen\s+-le\s+\$now)\)\s*\{", re.MULTILINE)

# 日曆日期字面（YYYY-MM 起即算）。功能碼裡出現任何一個就是「會自己過期」的硬編。
# 格式字串 `'yyyy-MM-dd HH\:mm'` 全是字母，不會誤命中。
_CALENDAR_LITERAL = re.compile(r"\d{4}-\d{2}")

# 合成時鐘用的固定格式（culture 無關，PowerShell 側以 InvariantCulture 解析）。
_CLOCK_FMT = "%Y-%m-%d %H:%M"


@pytest.fixture(scope="module")
def ps1_content() -> str:
    assert _RESCHEDULE_PS1.exists(), f"reschedule ps1 missing: {_RESCHEDULE_PS1}"
    # 本檔刻意宣告 ASCII-only（無 BOM），utf-8-sig 對無 BOM 檔亦安全。
    return _RESCHEDULE_PS1.read_text(encoding="utf-8-sig")


def _code_lines(text: str) -> list[str]:
    """剝除整行 `#` 註解後的行（本檔無區塊註解 `<# #>`，故不處理）。

    為何要剝：本腳本檔頭註解本來就會提到日期與設定名，不剝的話所有錨點都會被
    「註解裡留著字樣」假陽性通過（R57 QA-R57-03 在 macOS 側踩過同一個坑）。
    """
    return [ln for ln in text.splitlines() if not ln.strip().startswith("#")]


def _strip_double_quoted(line: str) -> str:
    """把雙引號字串字面值挖空後回傳該行。

    為何需要：腳本刻意在維運提醒訊息裡寫出 `Unregister-ScheduledTask`（告訴維運者
    G0 已簽核時正解是移除任務而非重排），那是**訊息文字**不是呼叫。掃「第一個排程
    cmdlet 呼叫點」時若不挖空字串，就會把這行提醒誤判成側effect 而讓順序鎖假紅。
    已實測涵蓋：本腳本現有形態（單行、字串內無跳脫引號）。未窮舉：here-string、
    跨行字串、單引號字串內的 cmdlet 名（本檔語料皆不存在）。
    """
    return re.sub(r'"[^"]*"', '""', line)


def _extract_power_ok_expression(text: str) -> str:
    m = _POWER_OK_LINE.search("\n".join(_code_lines(text)))
    assert m is not None, (
        "找不到 `$powerOk = ...` 成功判定式——腳本結構已變動；本檔的兩層鎖都靠這一行，"
        "改名/搬走請同步更新本測試，勿讓它靜默失去鑑別力"
    )
    return m.group(1)


def _extract_past_guard_expression(text: str) -> str:
    m = _PAST_GUARD_LINE.search("\n".join(_code_lines(text)))
    assert m is not None, (
        "找不到 `if ($TargetWhen -le $now) {` 拒絕判定——這是「不得靜默把 trigger 設在"
        "過去」的唯一守門。改名/改寫請同步本測試，並確認新寫法仍拒絕『與 now 相等』"
        "（`-lt` 不夠：相等的時刻不在未來）"
    )
    return m.group(1)


def _extract_ps_function(text: str, name: str) -> str:
    """抽出 `function <name> { ... }` 完整區塊（含大括號），以大括號深度掃描。

    不用 regex：函式體內有巢狀 `{}`（`if {}`／`${var}`），regex 的 `.*?}` 會在第一個
    內層 `}` 就停下，抽到半截函式後所有斷言都失去意義。形狀鏡射
    `tools/tests/test_install_windows_nightly.py::_extract_ps_function`（同一 repo 慣例）。
    """
    marker = f"function {name} {{"
    assert marker in text, f"腳本內找不到 `{marker}`——結構已變動，本檔的合成時鐘鎖依賴它"
    start = text.index(marker)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError(f"function {name} 大括號不成對——無法抽出完整區塊")


def _script_int_constant(text: str, name: str) -> int:
    """抽出腳本頂層 `$<name> = <整數>` 的值（須恰一處）。

    測試刻意**不自帶** GateHour／MinLeadMinutes 的數字：腳本改了門檻，本檔的斷言要
    跟著改，否則就是「測試自己硬編一份會漂移的數字」——本 repo 明令禁止的形態。
    """
    lines = [ln for ln in _code_lines(text) if re.match(rf"\s*\${name}\s*=", ln)]
    assert len(lines) == 1, f"${name} 賦值行應恰為 1 行，實得 {len(lines)}：{lines}"
    m = re.search(r"=\s*(-?\d+)\s*$", lines[0])
    assert m is not None, f"${name} 不是整數字面賦值，無法供合成時鐘使用：{lines[0]!r}"
    return int(m.group(1))


def _run_ps(script_text: str, tmp_path: Path) -> str:
    """把一段 PowerShell 寫成臨時 .ps1 真跑，回傳 stdout（rc != 0 即失敗）。

    寫檔而非 `-Command`：抽出來的函式含引號與大括號，塞進命令列引數會被兩層解析
    折斷。臨時檔落在 tmp_path（repo 樹外），不會被 .ps1 BOM／parity 等全語料掃描
    看到，也不留殘骸。
    """
    exe = _ps_exe()
    assert exe is not None
    script = tmp_path / "probe.ps1"
    script.write_text(script_text, encoding="ascii")
    proc = subprocess.run(
        [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0, (
        f"探針腳本在真 PowerShell 上執行失敗（rc={proc.returncode}）：\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
    return proc.stdout


class TestPowerSettingsReported:
    def test_all_four_settings_printed_with_expected_marker(self, ps1_content: str) -> None:
        """四項都必須連同 `(expected ...)` 標註印出——維運者要能逐行對照，
        而不是只看最後一行 [OK]/[FAIL]。"""
        code = "\n".join(_code_lines(ps1_content))
        for name, expected in _POWER_SETTINGS.items():
            assert f"$($v.{name})" in code, (
                f"{_RESCHEDULE_PS1.name} 未回讀並印出 {name} 實況——"
                f"設定被排程器默默忽略時維運者無從發現"
            )
            assert re.search(
                rf"\$\(\$v\.{name}\)\s*\(expected {expected}\)", code
            ), (
                f"{name} 缺 `(expected {expected})` 標註（或標註值與 _POWER_SETTINGS "
                f"登記的期望值不一致）——本測試與腳本必須對期望值有同一個定義"
            )


class TestSuccessGateCoversAllFour:
    def test_gate_expression_references_all_four_with_correct_polarity(
        self, ps1_content: str
    ) -> None:
        """四項都要在判定式內，且極性正確（期望 False 的兩項必須被 `-not` 包住）。"""
        expr = _extract_power_ok_expression(ps1_content)
        for name, expected in _POWER_SETTINGS.items():
            assert f"$v.{name}" in expr, (
                f"成功判定式未納入 {name}——這正是本檔存在的原因：印了卻不驗，"
                f"等於印給空氣看（實測 StopIfGoingOnBatteries=True 時仍印 [OK]）"
            )
            negated = re.search(rf"-not\s+\$v\.{name}\b", expr) is not None
            assert negated == (not expected), (
                f"{name} 在判定式中的極性錯誤：期望值 {expected}，"
                f"故{'不應' if expected else '應'}被 `-not` 包住。實際判定式：{expr}"
            )

    def test_gate_expression_is_byte_identical_to_fix_nightly_catchup(
        self, ps1_content: str
    ) -> None:
        """SSOT 鎖：本腳本的四項判定式必須與姊妹腳本 fix_nightly_catchup.ps1 的
        成功條件逐字（正規化空白後）相同。

        為何鎖成「同一份」而非各自獨立驗四項：兩支腳本管的是同一台機器上同一組
        Task Scheduler 開關，一旦兩邊對「設定正確」有兩套定義，維運者會拿到互相
        矛盾的 [OK]/[FAIL]，而且下次只有一邊被修。
        """
        fix_text = _FIX_CATCHUP_PS1.read_text(encoding="utf-8-sig")
        m = re.search(r"^\s*if \((\$v\..+?)\)\s*\{", fix_text, re.MULTILINE)
        assert m is not None, (
            f"{_FIX_CATCHUP_PS1.name} 找不到 `if ($v....) {{` 成功條件——"
            f"登記表已腐化，需同步核對（勿直接放寬本測試）"
        )
        fix_expr = " ".join(m.group(1).split())
        mine = _extract_power_ok_expression(ps1_content)
        mine_expr = " ".join(mine.split("=", 1)[1].split())
        assert mine_expr == fix_expr, (
            "兩支排程腳本的成功判定式已漂移，必須改回同一份：\n"
            f"  reschedule_g0_gatecheck.ps1: {mine_expr}\n"
            f"  fix_nightly_catchup.ps1    : {fix_expr}"
        )


class TestTargetMomentIsNotHardcoded:
    """回歸鎖 ③（含前一輪修復的不得回歸）：目標時刻不得硬編、印出的必須是設定的。

    本類取代舊的 `TestTargetDatetimeNotDuplicated`。舊測試鎖的是「日期字面只准出現
    一次」——它的意圖（expected 訊息必須由 `$TargetWhen` 推導）仍然完整保留在下面
    第二支測試裡，但它的**實作**反而硬性要求腳本裡存在一個日期字面（`assign` 行必須
    抽得出 `'YYYY-MM-DD`），因此在「日期改為執行期推導」後會誤紅。現行版把上限從
    「一次」收到「零次」，是嚴格更強的鎖：一次都不准。
    """

    def test_no_calendar_date_literal_in_functional_code(self, ps1_content: str) -> None:
        """功能碼裡不准有任何日曆日期字面（YYYY-MM 起）。

        這是本缺陷**類別**的鎖，不是某個日期的鎖：把 2026-06-29 換成別的未來日期
        照樣會被擋下。註解裡寫日期是允許的（不影響行為，且事故脈絡必須留痕），
        故只掃功能碼。
        """
        offenders = [
            ln for ln in _code_lines(ps1_content) if _CALENDAR_LITERAL.search(ln)
        ]
        assert offenders == [], (
            "功能碼出現日曆日期字面——排程腳本硬編日期會自己過期："
            "過期後一次性 trigger 被設在過去，實測 NextRunTime 讀回 $null，"
            "腳本自己的驗證式因此印 [FAIL] 並 exit 1（照官方文件跑官方腳本卻失敗）。"
            "目標時刻必須執行期推導或由 -When 傳入：\n  " + "\n  ".join(offenders)
        )

    def test_printed_expected_moment_derives_from_the_armed_variable(
        self, ps1_content: str
    ) -> None:
        """印出的 expected 時間必須與實際設定的時刻同源（`$TargetWhen`）。

        修復前 `(expected 2026-06-29 09:00)` 與 [OK] 訊息各自硬編同一個日期，實測
        對一個 2099 年的排程仍印 `expected 2026-06-29 09:00`。現行契約：
        `$targetText` 只由 `$TargetWhen.ToString(...)` 產生一次，所有對外訊息一律用它，
        而 trigger 也用同一個 `$TargetWhen`——同源即不可能再分岔。
        """
        code_lines = _code_lines(ps1_content)
        code = "\n".join(code_lines)

        derive = [ln for ln in code_lines if "$targetText = " in ln]
        assert len(derive) == 1, (
            f"$targetText 賦值行應恰為 1 行，實得 {len(derive)}：{derive}"
        )
        assert "$TargetWhen.ToString(" in derive[0], (
            f"$targetText 未由 $TargetWhen 推導（會與實際設定的時刻分岔）：{derive[0]!r}"
        )

        assert re.search(r"New-ScheduledTaskTrigger\s+-Once\s+-At\s+\$TargetWhen", code), (
            "一次性 trigger 不是用 $TargetWhen 建立的——一旦與 $targetText 不同源，"
            "印出的 expected 時間就會再次與實際設定的時刻不一致（本輪前一批修的正是這個）"
        )
        assert re.search(r"\(expected \$targetText\)", code), (
            "NextRunTime 那行的 `(expected ...)` 未使用 $targetText——不得再硬編一份"
        )
        assert re.search(r"rescheduled to \$targetText", code), (
            "[OK] 訊息未使用 $targetText——不得再硬編一份"
        )


class TestPastMomentRefusedBeforeAnySideEffect:
    """回歸鎖 ②（靜態層）：拒絕判定必須在任何排程寫入之前。

    順序本身就是安全保證：使用者硬給過去時刻時，腳本必須在還沒碰任何
    `*-ScheduledTask` 之前就 exit 1。本鎖同時是下面行為層測試（真跑腳本並傳入過去
    時刻）能在**任何**主機上安全執行的前提——包含提權主機與裝有真任務的機器。
    """

    def test_guard_precedes_elevation_check_and_every_scheduled_task_call(
        self, ps1_content: str
    ) -> None:
        code_lines = _code_lines(ps1_content)
        stripped = [_strip_double_quoted(ln) for ln in code_lines]

        guard_idx = next(
            (i for i, ln in enumerate(code_lines) if _PAST_GUARD_LINE.match(ln)), None
        )
        assert guard_idx is not None, (
            "找不到「目標時刻不在未來就拒絕」那一行——見 _extract_past_guard_expression 說明"
        )

        sched_idx = next(
            (i for i, ln in enumerate(stripped) if re.search(r"\w+-ScheduledTask", ln)),
            None,
        )
        assert sched_idx is not None, "腳本內找不到任何 *-ScheduledTask 呼叫——結構已變動"
        assert guard_idx < sched_idx, (
            f"拒絕判定（行 {guard_idx}）出現在第一個排程 cmdlet（行 {sched_idx}："
            f"{code_lines[sched_idx].strip()!r}）之後——過去時刻可能在被拒絕之前就已寫入"
        )

        admin_idx = next(
            (i for i, ln in enumerate(stripped) if "IsInRole" in ln), None
        )
        assert admin_idx is not None, "腳本內找不到提權檢查——結構已變動"
        assert guard_idx < admin_idx, (
            f"拒絕判定（行 {guard_idx}）在提權檢查（行 {admin_idx}）之後——引數錯誤"
            f"應該報引數錯誤，不該先被「請用管理員身分重跑」蓋掉（非提權主機上使用者"
            f"會提權重跑一次才發現時間本來就無效）"
        )

    def test_guard_block_exits_nonzero(self, ps1_content: str) -> None:
        """拒絕分支必須 `exit 1`：只 Write-Warning 然後往下跑＝照樣把過去時刻寫進去。

        本支為何不能省（注入實測）：把腳本的 `exit 1` 拿掉後，下面那支「真跑腳本」的
        行為層測試**照樣全綠**——非提權主機上腳本會繼續往下撞到提權檢查，rc 仍是 1、
        拒絕訊息也還在，四條斷言全部滿足。也就是說行為層對這個突變零鑑別力，只有本支
        靜態鎖抓得到。已實測涵蓋：非提權主機（本機）；未實測：提權且任務存在的主機
        （那裡的後果更嚴重——會真的把過去時刻寫進排程，正是本鎖要防的事）。
        """
        code_lines = _code_lines(ps1_content)
        guard_idx = next(
            (i for i, ln in enumerate(code_lines) if _PAST_GUARD_LINE.match(ln)), None
        )
        assert guard_idx is not None
        depth = 0
        block: list[str] = []
        for ln in code_lines[guard_idx:]:
            block.append(ln)
            depth += ln.count("{") - ln.count("}")
            if len(block) > 1 and depth == 0:
                break
        joined = "\n".join(block)
        assert re.search(r"^\s*exit 1\s*$", joined, re.MULTILINE), (
            f"拒絕分支沒有 `exit 1`——警告完仍會繼續執行並把過去時刻寫進排程：\n{joined}"
        )
        assert "Write-Warning" in joined, (
            "拒絕分支沒有 Write-Warning——fail loud 要求把理由寫給維運者看"
        )


@pytest.mark.skipif(_ps_exe() is None, reason="本機無可用 PowerShell，跳過行為層驗證")
class TestGateExpressionBehaviour:
    """行為層：把腳本裡真正那一行判定式丟給真的 PowerShell 跑。

    靜態子字串比對有個已知繞過：把某項加進式子但極性寫反、或用恆真的寫法包住，
    字面檢查照樣通過。本測試對五組合成輸入斷言紅／綠，四項每一項單獨翻轉都必須
    讓判定式變 False——這才是「四項皆為承載項」的證明。

    刻意不碰任何真實排程任務（不需 Get-ScheduledTask、不需系統管理員）：`$v` 由
    [pscustomobject] 合成，故本測試在 CI runner 與開發機上都可安全真跑。
    """

    @staticmethod
    def _run(expr: str, values: dict[str, bool]) -> str:
        props = "; ".join(
            f"{k}=${str(v).lower()}" for k, v in values.items()
        )
        script = (
            f"$v = [pscustomobject]@{{ {props} }}; "
            f"{expr}; "
            'Write-Output "$($powerOk.GetType().Name)|$powerOk"'
        )
        exe = _ps_exe()
        assert exe is not None
        proc = subprocess.run(
            [exe, "-NoProfile", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert proc.returncode == 0, (
            f"判定式在真 PowerShell 上執行失敗：\n{proc.stdout}\n{proc.stderr}"
        )
        return proc.stdout.strip()

    def test_all_settings_correct_yields_true(self, ps1_content: str) -> None:
        expr = _extract_power_ok_expression(ps1_content)
        assert self._run(expr, dict(_POWER_SETTINGS)) == "Boolean|True", (
            "四項全部符合期望時判定式竟不為 True——這會讓正確設定的機器恆紅。"
            "回傳型別若不是 Boolean（例如 Object[]），代表式子裡混進了會寫入 "
            "success stream 的東西"
        )

    @pytest.mark.parametrize("flipped", sorted(_POWER_SETTINGS))
    def test_each_setting_is_load_bearing(self, ps1_content: str, flipped: str) -> None:
        """逐項翻轉：任一項不符期望，判定式都必須為 False。"""
        expr = _extract_power_ok_expression(ps1_content)
        values = dict(_POWER_SETTINGS)
        values[flipped] = not values[flipped]
        assert self._run(expr, values) == "Boolean|False", (
            f"只把 {flipped} 翻成 {values[flipped]}，判定式仍為 True——"
            f"該項不是承載項，等於沒驗。實測事故：StopIfGoingOnBatteries=True 的"
            f"真實排程被印成 [OK] with catch-up protection"
        )


@pytest.mark.skipif(_ps_exe() is None, reason="本機無可用 PowerShell，跳過行為層驗證")
class TestDerivedDefaultBehaviour:
    """回歸鎖 ①：默認時間永遠不得落在過去（合成時鐘掃過整日與翻頁邊界）。

    為何要合成時鐘而不是「跑一次看結果」：跑一次只驗到「測試執行那一刻」的行為，
    而這個缺陷的本質就是**時間相依**——硬編日期在 2026-06-28 跑是綠的、隔天才變紅。
    腳本因此刻意把推導寫成純函式 `Get-G0TargetWhen -Now ...`（不內含 `Get-Date`），
    本測試把它抽出來灌各種時刻，包含月末、年末與閏年 2/28→2/29 翻頁。
    """

    @staticmethod
    def _clocks(gate_hour: int, lead: int) -> list[datetime]:
        clocks: list[datetime] = []
        base = datetime(2026, 7, 27, 0, 0)
        # 連續 3 天、每 37 分鐘一格：橫跨 GateHour 前後與整日各時段（37 為質數，
        # 不會與整點對齊而漏掉「剛好差幾分鐘」的邊界）。
        clocks += [base + timedelta(minutes=37 * i) for i in range(0, 117)]
        # 🔴 lead 邊界必須顯式送入，否則 $MinLeadMinutes 不是承載常數：37 分鐘的格子
        # 永遠落不到 GateHour 整點上，實測把 $MinLeadMinutes 改成 0 時上面 117 格全綠
        # （now 恰等於 GateHour:00 時才會推導出「等於 now」的目標）。
        gate = base.replace(hour=gate_hour, minute=0)
        clocks += [
            gate,                                  # 恰好 GateHour:00
            gate - timedelta(minutes=1),
            gate - timedelta(minutes=max(lead, 0)),
            gate - timedelta(minutes=max(lead, 0) + 1),
            gate + timedelta(minutes=1),
        ]
        # 翻頁邊界：月末、年末、閏年 2/28（AddDays(1) 若被改成日期字串拼接就會爆）。
        clocks += [
            datetime(2026, 7, 31, 23, 59),
            datetime(2026, 12, 31, 23, 59),
            datetime(2028, 2, 28, 23, 0),
            datetime(2028, 2, 29, 12, 0),
        ]
        return clocks

    def test_derived_default_is_always_in_the_future(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        fn = _extract_ps_function(ps1_content, "Get-G0TargetWhen")
        gate_hour = _script_int_constant(ps1_content, "GateHour")
        lead = _script_int_constant(ps1_content, "MinLeadMinutes")
        clocks = self._clocks(gate_hour, lead)
        rows = "\n".join(f"    '{c.strftime(_CLOCK_FMT)}'," for c in clocks).rstrip(",")
        script = (
            f"{fn}\n"
            "$fmt = 'yyyy-MM-dd HH:mm'\n"
            "$inv = [System.Globalization.CultureInfo]::InvariantCulture\n"
            "$clocks = @(\n"
            f"{rows}\n"
            ")\n"
            "foreach ($s in $clocks) {\n"
            "    $n = [datetime]::ParseExact($s, $fmt, $inv)\n"
            f"    $t = Get-G0TargetWhen -Now $n -GateHour {gate_hour} "
            f"-MinLeadMinutes {lead}\n"
            '    Write-Output ("{0}|{1}" -f $s, $t.ToString($fmt))\n'
            "}\n"
        )
        out = _run_ps(script, tmp_path)
        pairs = [ln.split("|") for ln in out.strip().splitlines() if "|" in ln]
        assert len(pairs) == len(clocks), (
            f"合成時鐘回報 {len(pairs)} 列、送入 {len(clocks)} 列——輸出被截斷，"
            f"不得把「沒驗到」當成通過：\n{out}"
        )
        for now_s, target_s in pairs:
            now = datetime.strptime(now_s, _CLOCK_FMT)
            target = datetime.strptime(target_s, _CLOCK_FMT)
            assert target > now, (
                f"now={now_s} 推導出的默認目標 {target_s} 不在未來——一次性 trigger 設在"
                f"過去時實測 NextRunTime 讀回 $null，腳本自己的驗證式會印 [FAIL]"
            )
            assert target - now >= timedelta(minutes=lead), (
                f"now={now_s} 的默認目標 {target_s} 距現在不足 $MinLeadMinutes={lead} 分——"
                f"寫入與回讀之間 trigger 就過期，會產生假的 [FAIL]"
            )
            assert (target.hour, target.minute) == (gate_hour, 0), (
                f"now={now_s} 的默認目標 {target_s} 不是 $GateHour={gate_hour} 整點——"
                f"09:00 是刻意的（在 02:00 nightly 之後，能看到當日累積）"
            )
            assert target <= now + timedelta(days=1, minutes=lead), (
                f"now={now_s} 的默認目標 {target_s} 比「下一個 {gate_hour} 點」更遠——"
                f"默認值必須是最近的可用時刻，不是把閘門無謂往後推"
            )


@pytest.mark.skipif(_ps_exe() is None, reason="本機無可用 PowerShell，跳過行為層驗證")
class TestPastMomentRefusalBehaviour:
    """回歸鎖 ②（行為層）：過去時刻必須 fail loud，且判定式是承載的。"""

    def test_guard_expression_rejects_past_and_equal_accepts_future(
        self, ps1_content: str, tmp_path: Path
    ) -> None:
        """把拒絕判定式抽出來灌合成時刻：過去→True（拒絕）、相等→True、未來→False。

        與 `$powerOk` 那組同一個理由：靜態比對擋不住極性寫反（`-ge`／`-le` 打錯字
        就會變成「只接受過去時刻」而且靜態鎖照樣全綠）。
        """
        expr = _extract_past_guard_expression(ps1_content)
        cases = {-1: "True", 0: "True", 1: "False"}
        script = (
            "$fmt = 'yyyy-MM-dd HH:mm'\n"
            "$inv = [System.Globalization.CultureInfo]::InvariantCulture\n"
            "$now = [datetime]::ParseExact('2026-07-27 12:00', $fmt, $inv)\n"
            + "".join(
                f"$TargetWhen = $now.AddMinutes({delta})\n"
                f"$r = ({expr})\n"
                '$out = "{0}|$($r.GetType().Name)|$r" -f ' + f"{delta}\n"
                "Write-Output $out\n"
                for delta in cases
            )
        )
        out = _run_ps(script, tmp_path)
        got = dict(
            (int(p[0]), f"{p[1]}|{p[2]}")
            for p in (ln.split("|") for ln in out.strip().splitlines() if "|" in ln)
        )
        assert got == {d: f"Boolean|{v}" for d, v in cases.items()}, (
            f"拒絕判定式對合成時刻的紅綠不符預期（delta 分鐘 → 型別|值）：{got}\n"
            f"預期 過去/相等→True（拒絕）、未來→False（接受）；判定式：{expr}"
        )

    def test_real_script_refuses_a_past_when_with_nonzero_exit(
        self, ps1_content: str
    ) -> None:
        """真跑腳本本體，`-When` 給一個確定的過去時刻 → rc=1 ＋ 拒絕訊息。

        **為何這樣真跑是安全的、連提權主機都安全**：本檔的
        `TestPastMomentRefusedBeforeAnySideEffect` 已靜態證明拒絕判定在任何
        `*-ScheduledTask` 呼叫與提權檢查之前，所以這條路徑碰不到任何真實排程。
        本測試在 spawn 前**再跑一次**那個順序斷言，讓「安全前提」與「真跑」綁在
        同一支測試裡——順序哪天被改壞，這裡會先紅，而不是默默去動使用者的排程。
        """
        TestPastMomentRefusedBeforeAnySideEffect().test_guard_precedes_elevation_check_and_every_scheduled_task_call(
            ps1_content
        )
        exe = _ps_exe()
        assert exe is not None
        past = "2000-01-01 09:00"
        proc = subprocess.run(
            [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(_RESCHEDULE_PS1), "-When", past],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        combined = proc.stdout + proc.stderr
        assert proc.returncode == 1, (
            f"對過去時刻 {past} 的 rc 應為 1（fail loud），實得 {proc.returncode}：\n{combined}"
        )
        assert past in proc.stdout, (
            f"腳本未印出實際採用的時刻——維運者無從得知它到底要設哪一刻：\n{combined}"
        )
        assert "[FAIL]" in combined and "not in the future" in combined, (
            f"拒絕訊息缺少 [FAIL] 或理由（過去時刻）——靜默拒絕與靜默照設一樣糟：\n{combined}"
        )
        assert "rescheduled to" not in combined, (
            f"對過去時刻竟出現 [OK] 語句——腳本可能已把 trigger 設進去：\n{combined}"
        )


@pytest.mark.skipif(_ps_exe() is None, reason="本機無可用 PowerShell，跳過語法檢查")
class TestScriptParses:
    def test_zero_parse_errors_on_this_machine(self) -> None:
        """本機真 parser 零 parse error。

        為何值得單獨鎖：本檔其他測試都是抽片段去跑，抽不到整檔語法問題——而本輪加
        `param()`／`function` 區塊時就真的踩到一個：`"...$targetText: ..."` 裡變數
        後緊接 `:` 被 PowerShell 當成 scope 限定變數參考，整檔無法解析。那種錯誤會讓
        腳本連啟動都不行，卻不影響任何字面錨點。
        （全語料版的同型守門另見 tools/tests/test_ps_comment_golden.py。）
        """
        exe = _ps_exe()
        assert exe is not None
        cmd = (
            "$e = $null; $t = $null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile("
            f"'{_RESCHEDULE_PS1.as_posix()}', [ref]$t, [ref]$e); "
            'Write-Output "errors=$($e.Count)"; '
            "$e | ForEach-Object { Write-Output $_.Message }"
        )
        proc = subprocess.run(
            [exe, "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert proc.returncode == 0, f"{proc.stdout}\n{proc.stderr}"
        assert "errors=0" in proc.stdout, (
            f"{_RESCHEDULE_PS1.name} 有 parse error：\n{proc.stdout}\n{proc.stderr}"
        )
