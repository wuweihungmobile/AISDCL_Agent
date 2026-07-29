#!/usr/bin/env python3
"""「Windows smoke 有沒有心跳」的**修復 ↔ 活文件**跨檔互鎖（R60 QA-R60-06 根治）。

WHY（為何非得有這道鎖）：
  R60 為 `tools/windows_smoke_local.ps1` 補上獨立 schtasks 心跳
  （`AutoClaude_WindowsSmoke`，每日 01:00，由 `tools/install_windows_nightly.ps1` 註冊），
  修復確實落地；但兩份**活文件**仍逐字保留已被推翻的宣稱——
    · `ONBOARDING.md` §8：「…只能手動觸發…沒有自動觸發器＝補償控制自己沒有心跳」
    · `AutoClaude/tools/run_local_nightly.ps1` 檔頭第 1 項：同一組敘述
  修復包已在證據檔標【必做／文件同步】逐處點名請求訂正，主控漏辦，而**三道閘門全綠**：
  既有的 `test_smoke_ci_sync.py` 只比對 `PASS=N` 集合，對散文真偽全盲。QA-R60-06 因此
  判為 blocking——「修好了但文件說沒修好」比沒修更糟：它會讓下一位重做一次已完成的事，
  或誤以為補償控制仍無心跳而繞過它。

判準（雙向，刻意不只單邊）：
  ① **前提**：`install_windows_nightly.ps1` 必須真的註冊該任務（任務名字面 ＋
     `New-ScheduledTaskTrigger` ＋ `Register-ScheduledTask` 三者齊備）。前提消失
     （有人把心跳拿掉）也 fail-loud，並指示往**反方向**同步文件——單邊鎖只會在
     「修復被移除」時靜默放行。
  ② **散文同步**：任何檔案只要出現「已被推翻的宣稱」字樣（`_STALE_CLAIMS`），該檔
     就必須同時出現任務名 `AutoClaude_WindowsSmoke`——即那段敘述旁邊必須有訂正／脈絡，
     不得是孤零零的過期宣稱。
  ③ **反縮面**：掃描面（`_CLAIM_SCAN_FILES`）以 `git grep` 全庫實掃交叉驗證；出現
     任何未登記的檔含該類宣稱即紅（防「文件搬家後這道鎖靜默失守」）。

🔴 判準邊界（誠實劃界）：
  - 這是**字面共現鎖**，不是語意鎖。它保證「過期宣稱旁邊有訂正脈絡」，**不保證訂正
    文字寫得對**。散文真偽終究要人審——本鎖只把「零訊號」升為「有訊號」。
  - 帳本家族（`docs/06_quality/AutoSDD_Defect_Log*`）與本輪證據檔刻意排除：那是**時代
    快照**，逐字保留過期宣稱正是它們的職責（同 repo「歷史紀錄檔不納管」慣例）。
  - 不驗證排程任務在本機**真的存在**（那需要 `Get-ScheduledTask`、依賴機器狀態，
    會在 CI／macOS 上必然失敗）。任務存在性由 `install_windows_nightly.ps1 -Status`
    與 `test_install_windows_nightly.py` 負責。

執行：python tools/run_root_unittests.py
      python -m unittest tools.tests.test_windows_smoke_heartbeat_doc_sync -v
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

_INSTALLER = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"
_SMOKE_TASK_NAME = "AutoClaude_WindowsSmoke"

# 已被 R60 修復推翻的宣稱字樣（任一命中即要求同檔有訂正脈絡）。
_STALE_CLAIMS = (
    "只能手動觸發",
    "沒有自動觸發器",
    "補償控制自己沒有心跳",
)

# 允許出現該類宣稱的檔（＝已帶訂正脈絡者）。相對 repo 根、posix 形態。
_CLAIM_SCAN_FILES = (
    "ONBOARDING.md",
    "AutoClaude/tools/run_local_nightly.ps1",
    "tools/install_windows_nightly.ps1",
    "tools/tests/test_install_windows_nightly.py",
    "tools/tests/test_windows_smoke_heartbeat_doc_sync.py",  # 本檔（判準字面本身）
)

# 時代快照：逐字保留過期宣稱是其職責，刻意不納管（前綴比對）。
_SNAPSHOT_PREFIXES = (
    "docs/06_quality/AutoSDD_Defect_Log",
    "docs/06_quality/CrossPlatform_R60_Fix_Evidence.md",
)


def _git_grep_claim_files() -> list[str]:
    """全庫實掃：回傳含任一過期宣稱字樣的檔案清單（posix 路徑，去重排序）。"""
    args = ["git", "grep", "-I", "-l", "--untracked"]
    for claim in _STALE_CLAIMS:
        args += ["-e", claim]
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode not in (0, 1):
        raise AssertionError(
            f"git grep 失敗（rc={proc.returncode}）——掃描面取不到就不得當成「零違規」。\n"
            f"stderr: {proc.stderr[-800:]}"
        )
    return sorted(
        {
            line.replace("\\", "/").strip()
            for line in proc.stdout.splitlines()
            if line.strip()
        }
    )


class TestWindowsSmokeHeartbeatDocSync(unittest.TestCase):
    def test_installer_actually_registers_the_smoke_heartbeat(self) -> None:
        """前提：心跳真的被註冊（前提消失也要紅，並指示反方向同步）。

        判準刻意用**smoke 專屬**的字面組合，不用 `Register-ScheduledTask` 這種
        泛用字面——該檔另有 nightly 任務也在呼叫它，泛用字面下拿掉 smoke 註冊
        仍會全綠（本鎖第一版實測即如此：注入後 `Ran 4 / OK`，零鑑別力）。
        """
        src = _INSTALLER.read_text(encoding="utf-8-sig")
        for needle in (
            f"$SmokeTaskName = '{_SMOKE_TASK_NAME}'",
            "$smokeTrigger = New-ScheduledTaskTrigger -Daily -At $SmokeAt",
            "Register-ScheduledTask -TaskName $SmokeTaskName",
            "$smokeAction = New-ScheduledTaskAction",
            "windows_smoke_local.ps1",
        ):
            # 用 assertTrue 而非 assertIn：assertIn 失敗時會把整個檔案內容當 haystack
            # 印出來（實測數萬字元），訊息反而看不到重點。
            self.assertTrue(
                needle in src,
                f"{_INSTALLER.name} 不再含 `{needle}` ⇒ Windows smoke 的 schtasks 心跳"
                f"可能已被移除。若這是刻意的，請把 ONBOARDING §8 與 "
                f"AutoClaude/tools/run_local_nightly.ps1 的敘述**改回**「沒有自動觸發器」"
                f"並同步本鎖——單邊鎖會在修復被移除時靜默放行，故此處雙向 fail-loud",
            )

    def test_every_stale_claim_site_carries_the_correction_context(self) -> None:
        """出現過期宣稱的檔，必須同檔出現任務名（＝旁邊有訂正／脈絡）。"""
        offenders: list[str] = []
        for rel in _CLAIM_SCAN_FILES:
            path = _REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"登記的掃描檔不存在：{rel}（改名須同步本清單）")
            text = path.read_text(encoding="utf-8-sig")
            hit = [c for c in _STALE_CLAIMS if c in text]
            if hit and _SMOKE_TASK_NAME not in text:
                offenders.append(f"{rel}（命中宣稱 {hit}，但全檔無 `{_SMOKE_TASK_NAME}`）")
        self.assertEqual(
            offenders,
            [],
            "以下活文件仍帶已被 R60 修復推翻的宣稱，且同檔沒有任何訂正脈絡：\n"
            + "\n".join(f"  - {o}" for o in offenders)
            + f"\n修法：在該敘述旁註明「現由 {_SMOKE_TASK_NAME}（每日 01:00，由 "
            "tools/install_windows_nightly.ps1 註冊）觸發；心跳讀 Get-ScheduledTaskInfo，"
            "-Status 對缺席回 exit 1」，並保留仍為真的那半句"
            "（run_local_nightly.ps1 對它零呼叫＝刻意解耦）。",
        )

    def test_scan_surface_matches_repo_reality(self) -> None:
        """反縮面：全庫實掃到的宣稱檔，必須全在登記清單或時代快照白名單內。"""
        found = _git_grep_claim_files()
        self.assertTrue(
            found,
            "全庫掃不到任何宣稱字樣——判準字面若被整批改寫，本鎖會靜默空轉，故 fail-loud；"
            "請確認 _STALE_CLAIMS 是否仍對應文件用詞",
        )
        unregistered = [
            f
            for f in found
            if f not in _CLAIM_SCAN_FILES
            and not any(f.startswith(p) for p in _SNAPSHOT_PREFIXES)
        ]
        self.assertEqual(
            unregistered,
            [],
            "以下檔含「Windows smoke 沒有心跳」類宣稱但未登記在 _CLAIM_SCAN_FILES："
            f"{unregistered}\n"
            "新文件長出同款過期宣稱時必須被本鎖看見——請登記（並確認該檔已有訂正脈絡），"
            "或若它屬時代快照，加入 _SNAPSHOT_PREFIXES 並說明 WHY。",
        )

    def test_registered_list_has_no_stale_entry(self) -> None:
        """登記清單不得腐化：清單內的檔若已不含任何宣稱字樣，該筆就該被移除。

        WHY：R60 的 `_PENDING_MIGRATION_SITES` 教訓——豁免／登記清單沒有 stale 自檢，
        就會靠殘留文字永久撐著，最後變成沒人回收的死條目。本檔自己那筆例外
        （判準字面必然常在），其餘皆須有真命中。
        """
        stale: list[str] = []
        for rel in _CLAIM_SCAN_FILES:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
            if not any(c in text for c in _STALE_CLAIMS):
                stale.append(rel)
        self.assertEqual(
            stale,
            [],
            f"以下登記檔已不含任何宣稱字樣，屬過期登記（請逕行移除該筆）：{stale}",
        )


if __name__ == "__main__":
    unittest.main()
