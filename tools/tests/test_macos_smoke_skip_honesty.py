#!/usr/bin/env python3
"""tools/macos_smoke_local.sh 的「SKIP 誠實外顯」鎖（R60 F-01）。

執行：python3 -m unittest discover -s tools/tests

缺陷現象（R60 Scan-F F-01，實測於 Windows 11 + Git Bash MINGW64_NT-10.0-26200）：
該腳本在**非 Darwin** 平台把兩項無法驗證的子測試以「SKIP-計-PASS」計入 PASS，
收尾印出的 `===== 彙總：PASS=13 FAIL=0 =====` ＋ `全部通過 ✅` ＋ `rc=0` 與**真
macOS 滿版全驗**逐字相同、計數相同（兩平台皆恰 13——兩處互斥分支已由
`tools/tests/test_smoke_ci_sync.py::_SH_EXCLUSIVE_PASS_GROUPS` 登記），事後稽核
無從分辨「在 Windows 上跑過」與「在 macOS 上全綠」。R59 由 DEF-101-511/512 立的
原則（「讓結論自己說出降級事實」）當輪未回頭套用到這支腳本。

本檔鎖的不變量（刻意全部走靜態結構＋一支真跑載具，不需要 macOS）：
  1. `SKIPPED_AS_PASS` 計數器存在且初始化為 0。
  2. **納管**：腳本裡每一個訊息帶 SKIP 字樣的 `pass "…"` 呼叫點，都必須恰有一次
     計數器遞增緊鄰其前（新增第三處 SKIP-計-PASS 卻忘了遞增 → 紅）。
  3. 彙總行必須印出 `SKIP=$SKIPPED_AS_PASS`。
  4. SKIP>0 與 SKIP==0 兩條收尾路徑**互斥**：SKIP>0 分支自己 `exit 0`，且
     「全部通過」字樣只能出現在其後（＝非 Darwin 永遠印不出「全部通過」）。
  5. 真跑載具：切出收尾彙總段以 bash 實跑兩次（SKIP=0 / SKIP=2），斷言兩份輸出
     可分辨。此支若在無可用 bash 的環境會 skip，故 1~4 為主要防線。

鑑別力（R60 實測）：把 SKIP>0 分支整段刪掉、收尾恢復成單一「全部通過 ✅」，
本檔 5 支全部 FAIL；還原即全綠（紅綠輸出見 R60 回報）。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SH = _REPO_ROOT / "tools" / "macos_smoke_local.sh"

# 「SKIP-計-PASS」的 pass 訊息錨點（顯式登記表；同 test_smoke_ci_sync.py
# _SH_EXCLUSIVE_PASS_GROUPS 的 fail-loud 慣例——錨點消失即紅，逼人工重新核對）。
_SKIP_AS_PASS_MESSAGES = (
    "dispatcher 直呼煙霧（pre-commit 放行、post-commit、pre-push 刪除跳過；"
    "NTFS 保留名子測試 SKIP——非 macOS 平台先擋）",
    "install_mac_nightly.sh --render-only（SKIP-計-PASS：非 macOS）",
)

_PASS_CALL_RE = re.compile(r'^\s*(?:\S+\s+)?pass\s+"([^"]*)"', re.MULTILINE)
_INCREMENT = "SKIPPED_AS_PASS=$((SKIPPED_AS_PASS + 1))"
_SUMMARY_SKIP_FIELD = "SKIP=$SKIPPED_AS_PASS"
_SKIP_GUARD = 'if [ "$SKIPPED_AS_PASS" -gt 0 ]; then'
_ALL_PASS_MARK = "全部通過"
# 收尾彙總段的起點錨點（真跑載具切檔用）
_SUMMARY_ANCHOR = "MIN_PASS="


def _read() -> str:
    return _SH.read_text(encoding="utf-8")


def _usable_bash() -> str | None:
    """回傳能跑 `echo` 的 bash 路徑；找不到回 None。

    刻意不 import AISDLC_SDD/scripts/bash_probe.py：R60 Scan-A 實測該探針在
    unittest 載具下於本機恆回 None（CreateProcess WinError 87），會讓本檔的真跑
    載具在官方閘門裡靜默 skip。此處只做最小驗活（不帶受限 env），並在 setUp 明確
    skip 而非假綠。
    """
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        for up in list(Path(git).resolve().parents)[:4]:
            for sub in ("usr/bin/bash.exe", "bin/bash.exe", "usr/bin/bash", "bin/bash"):
                cand = up / sub
                if cand.exists():
                    candidates.append(str(cand))
    bare = shutil.which("bash")
    if bare:
        candidates.append(bare)
    for cand in candidates:
        try:
            r = subprocess.run(
                [cand, "-c", "echo probe-ok"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=20,
            )
        except Exception:  # noqa: BLE001 — 任何載具問題都只是「這個候選不可用」
            continue
        if r.returncode == 0 and r.stdout.strip() == "probe-ok":
            return cand
    return None


class TestSkipCounterEnrollment(unittest.TestCase):
    """不變量 1+2：計數器存在，且每個 SKIP-計-PASS 站點都被納管。"""

    def test_counter_initialized(self) -> None:
        self.assertRegex(
            _read(), r"(?m)^SKIPPED_AS_PASS=0$",
            "macos_smoke_local.sh 缺 SKIPPED_AS_PASS=0 初始化——SKIP 獨立計數被移除"
            "（R60 F-01 回歸：非 Darwin 的 rc=0 又變回與 macOS 全驗不可分辨）",
        )

    def test_registered_skip_messages_still_exist(self) -> None:
        msgs = _PASS_CALL_RE.findall(_read())
        for msg in _SKIP_AS_PASS_MESSAGES:
            self.assertIn(
                msg, msgs,
                f"SKIP-計-PASS 訊息錨點消失：{msg!r}——登記表已腐化，"
                "需人工重新核對 _SKIP_AS_PASS_MESSAGES",
            )

    def test_every_skip_pass_site_is_enrolled(self) -> None:
        """腳本內帶 SKIP 字樣的 pass 呼叫必須全部在登記表內（防新增站點漏納管）。"""
        skip_msgs = [m for m in _PASS_CALL_RE.findall(_read()) if "SKIP" in m]
        self.assertEqual(
            sorted(skip_msgs), sorted(_SKIP_AS_PASS_MESSAGES),
            f"腳本裡的 SKIP-計-PASS 站點 {skip_msgs} 與登記表 "
            f"{list(_SKIP_AS_PASS_MESSAGES)} 不符——新增 SKIP-計-PASS 分支必須同步"
            f"（a）遞增 SKIPPED_AS_PASS（b）登記進本表",
        )

    def test_increment_count_matches_skip_sites(self) -> None:
        text = _read()
        n_inc = text.count(_INCREMENT)
        self.assertEqual(
            n_inc, len(_SKIP_AS_PASS_MESSAGES),
            f"SKIPPED_AS_PASS 遞增次數={n_inc}，SKIP-計-PASS 站點數="
            f"{len(_SKIP_AS_PASS_MESSAGES)}——某個 SKIP 站點沒把自己計進 SKIP 總數"
            f"（收尾會少報降級項目數）",
        )

    def test_each_increment_is_adjacent_to_its_skip_pass_call(self) -> None:
        """遞增必須緊鄰其 SKIP-計-PASS 呼叫（≤3 行內），不得放在無關位置充數。"""
        lines = _read().splitlines()
        inc_lines = [i for i, ln in enumerate(lines) if _INCREMENT in ln]
        for msg in _SKIP_AS_PASS_MESSAGES:
            target = next(
                (i for i, ln in enumerate(lines) if f'pass "{msg}"' in ln), None
            )
            self.assertIsNotNone(
                target, f"找不到 pass 呼叫所在行：{msg!r}（登記表已腐化）"
            )
            self.assertTrue(
                any(0 < target - i <= 3 for i in inc_lines),
                f"SKIP-計-PASS 站點（行 {target + 1}）前 3 行內找不到 "
                f"{_INCREMENT}——該站點未計入 SKIP 總數：{msg!r}",
            )


class TestSummaryOutputIsDistinguishable(unittest.TestCase):
    """不變量 3+4：彙總行印 SKIP=N，且兩條收尾路徑互斥。"""

    def test_summary_line_reports_skip(self) -> None:
        text = _read()
        summary_lines = [
            ln for ln in text.splitlines() if "彙總：PASS=" in ln
        ]
        self.assertTrue(summary_lines, "找不到彙總行（格式已漂移）")
        for ln in summary_lines:
            self.assertIn(
                _SUMMARY_SKIP_FIELD, ln,
                f"彙總行未印 SKIP 數：{ln.strip()!r}——PASS/FAIL 兩欄無法讓稽核者"
                f"看出有幾項是本平台跳過的（R60 F-01 的原始缺陷形狀）",
            )

    def test_all_pass_message_unreachable_when_skipped(self) -> None:
        text = _read()
        guard_at = text.find(_SKIP_GUARD)
        self.assertNotEqual(
            guard_at, -1,
            f"找不到 SKIP>0 收尾分支 {_SKIP_GUARD!r}——降級事實不再外顯"
            f"（R60 F-01 回歸）",
        )
        # 分支內必須自己 exit 0（否則會續流到「全部通過」）
        guard_end = text.index("\nfi", guard_at)
        guard_body = text[guard_at:guard_end]
        self.assertIn(
            "exit 0", guard_body,
            "SKIP>0 分支未自行 exit——會續流印出「全部通過」，兩種綠燈又變回不可分辨",
        )
        self.assertNotIn(
            _ALL_PASS_MARK, guard_body,
            "SKIP>0 分支內出現「全部通過」字樣——降級路徑不得自稱全部通過",
        )
        # 「全部通過」只能出現在該分支之後（＝SKIP==0 才印得到）。只看功能碼行：
        # 檔頭註解會（也應該）說明兩種收尾字樣，不算可執行的輸出路徑。
        guard_line = text.count("\n", 0, guard_at)
        for i, ln in enumerate(text.splitlines()):
            if _ALL_PASS_MARK in ln and not ln.lstrip().startswith("#"):
                self.assertGreater(
                    i, guard_line,
                    f"「全部通過」出現在 SKIP>0 守門之前（行 {i + 1}：{ln.strip()!r}）"
                    f"——非 Darwin 平台仍可能印出全綠結論",
                )


class TestSummaryTailRealRun(unittest.TestCase):
    """不變量 5：以 bash 實跑收尾彙總段，證明兩種 SKIP 值的輸出真的可分辨。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.bash = _usable_bash()
        if cls.bash is None:
            raise unittest.SkipTest("找不到可用的 bash——收尾彙總段真跑載具無法執行")
        text = _read()
        at = text.find(f"\n{_SUMMARY_ANCHOR}")
        if at == -1:
            raise AssertionError(
                f"切不出收尾彙總段（錨點 {_SUMMARY_ANCHOR!r} 消失）——真跑載具失效"
            )
        cls.tail = text[at + 1:]

    def _run(self, skipped: int) -> subprocess.CompletedProcess[str]:
        script = (
            "set -u\n"
            'fail() { FAIL=$((FAIL + 1)); FAIL_LIST="${FAIL_LIST}\n  - $1"; }\n'
            "PASS=13\nFAIL=0\nFAIL_LIST=''\n"
            f"SKIPPED_AS_PASS={skipped}\n"
            f"{self.tail}"
        )
        return subprocess.run(
            [self.bash, "-c", script], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )

    def test_skip_zero_and_skip_two_outputs_differ(self) -> None:
        zero = self._run(0)
        two = self._run(2)
        self.assertEqual(zero.returncode, 0, f"SKIP=0 應 rc=0：{zero.stderr}")
        self.assertEqual(two.returncode, 0, f"SKIP=2 應 rc=0：{two.stderr}")
        self.assertNotEqual(
            zero.stdout, two.stdout,
            "SKIP=0 與 SKIP=2 的收尾輸出逐字相同——這正是 R60 F-01 的缺陷本體"
            "（真 macOS 全驗 與 非 Darwin 部分驗 不可分辨）",
        )
        self.assertIn("SKIP=0", zero.stdout)
        self.assertIn("SKIP=2", two.stdout)
        self.assertIn(_ALL_PASS_MARK, zero.stdout, "SKIP=0（macOS 全驗）應印全部通過")
        self.assertNotIn(
            _ALL_PASS_MARK, two.stdout,
            "SKIP=2 仍印出「全部通過」——降級結果被說成全綠",
        )


if __name__ == "__main__":
    unittest.main()
