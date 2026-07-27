"""R57 機械鎖：文件內 pip/uv extras 安裝指令必須加引號（macOS zsh glob 安全）.

# 缺陷（R57 Scan-A2）

macOS 自 Catalina 起預設登入 shell 為 **zsh**。zsh 對未加引號的 `.[dev,notifications]`
執行 filename generation（glob）；repo 內沒有「`.` + 單一字元」的匹配檔名，zsh 遂
**在執行指令之前就中止整條命令列**：

    $ zsh -c 'echo REACHED .[dev,notifications]'
    zsh:1: no matches found: .[dev,notifications]      rc=1     ← echo 從未執行
    $ zsh -c "echo REACHED '.[dev,notifications]'"
    REACHED .[dev,notifications]                        rc=0
    $ bash -c 'echo REACHED .[dev,notifications]'
    REACHED .[dev,notifications]                        ← bash 無此行為

實害：macOS 開發者照文件複製貼上 `uv pip install -e .[dev,notifications]`，看到的是  <!-- zsh-glob-ok: 本檔即此鎖的實作，docstring 必須原樣引述壞形態才能說明缺陷本身 -->
一個與套件完全無關的 `no matches found` —— uv/pip 根本沒被呼叫到。同一行在 bash 與
PowerShell 下都正常，故 **Windows 開發者永遠不會遇到**，是單邊平台缺陷。

R57 動工時全 repo 活文件共 16 處未加引號（`AutoClaude/README.md` 9、
`docs/AISDLC_Agent_UserGuide.md` 4、另三份各 1），全部已修。

# 為何需要這道鎖

修完 16 處只是解決當下；本 repo 反覆的教訓是「人工修完的東西沒有機械鎖就會回流」。
extras 語法在文件裡是高頻複製貼上的樣板，未來任一次新增安裝說明都可能寫回未加引號
形態，而 `check_pytest_baseline_sites.py` 等既有守門完全不看這個面向。

# 掃描面與邊界（誠實劃界）

- 掃描 **git tracked 的 `*.md` + `*.sh` + `*.py` + 三處 git-hooks 無副檔名檔**（清單見
  `_SCAN_PATHSPECS`／`_HOOK_DIRS`；R57 round 1 由「只掃 `*.md`」擴面，理由見該處註解）。
  未 tracked 的新檔在 `git add` 前不在掃描面內——這是 `git ls-files` 的固有性質（與
  `test_platform_utils_dedup.py` R57 改用 `git ls-files` 同政策）：pre-commit 於 `git add`
  後才跑、CI 跑的是已 commit 樹，故實務上不構成缺口，但**本機手跑時新檔確實掃不到**，
  誠實記載。`.ps1` 刻意不納入（PowerShell 無此 glob 語意，納入只製造偽陽性）。
- 排除 `_EXCLUDED_SUBSTRINGS` 所列的**歷史紀錄檔**（缺陷帳本與其 archive、sprint_history、
  improving 系列）——那些是時代快照，逐字保全優先於修正，比照 `check_pytest_baseline_sites.py`
  對歷史紀錄檔的既有政策。
- 只認 `pip install` / `uv pip install` 後接**裸 `.[`** 的形態。不認 `pip install pkg[extra]`
  （具名套件的 extras 在 zsh 下同樣會 glob，但 repo 內無此寫法，加進來只會製造未來偽陽性；
  真出現時本鎖會漏——這是明文承認的邊界，不是保證）。
- 本鎖**不驗證 shell 實際行為**（那需要 zsh，CI 的 ubuntu runner 未必有）；它是純文字形態鎖。
  行為面的證據記在本 docstring 頂部與缺陷帳本 DEF-101-479。

# 豁免機制（`zsh-glob-ok:`）

雷區對照表這類**刻意引述壞形態**的文件行（ONBOARDING §5 就必須寫出
`uv pip install -e .[dev,notifications]` 才說得清楚症狀）無法避免命中，故提供行內豁免：  <!-- zsh-glob-ok: 說明豁免機制存在理由時必須舉出壞形態 -->
在該行加上 `<!-- zsh-glob-ok: <理由> -->`。比照 `check_pytest_baseline_sites.py` 的
`baseline-ok:` 既有慣例——**豁免必須附理由，且被 `test_exemptions_are_audited` 稽核**
（要求理由非空、且豁免總數不得超過 `_MAX_EXEMPTIONS`），避免「豁免變成靜默放行的後門」。
R57 round 1 擴面後的合法豁免為 **3 行**：ONBOARDING §5 雷區表 1 行、本檔 docstring 病例
樣本 2 行（本檔即此鎖的實作，內含壞形態是本質需求；整檔排除才是 fail-open，故走逐行豁免）。
"""

import re
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# `pip install [-e] .[extras]` / `uv pip install [-e] .[extras]`，裸 `.[`（未被引號包住）。
#
# R57 round 1 SD 複審訂正兩處（皆經實測，見 DEF-101-479）：
# (a) 旗標段原為 `(?:-[A-Za-z]+\s+)*`，**只吃單槓短旗標**——`pip install --upgrade -e .[dev]`  # zsh-glob-ok: 正則沿革說明必須引述被漏報的壞形態
#     這種帶 GNU 長旗標的寫法整條漏報（實測 old=False / new=True）。改為 `--?[A-Za-z][A-Za-z-]*`。
# (b) 原有的前方 lookbehind `(?<!["'])` 是**死碼**：加引號版長成 `install -e '.[dev]'`，該位置
#     的字元是 `'` 而 `\.\[` 本身就要求是 `.`，正則在此必然失配，lookbehind 沒有額外作用。
#     實測 6 組樣本在「有 lookbehind／無 lookbehind」下結果完全相同，故移除並訂正註解——
#     留著死碼會讓後人以為「引號情境是靠 lookbehind 擋的」而不敢動。
_UNQUOTED_EXTRAS_RE = re.compile(
    r"(?:uv\s+)?pip\s+install\s+(?:--?[A-Za-z][A-Za-z-]*\s+)*\.\[[^\]]+\]"
)

# 歷史紀錄檔：逐字保全優先，不納管（與 check_pytest_baseline_sites.py 同政策）
_EXCLUDED_SUBSTRINGS = (
    "AutoSDD_Defect_Log",
    "sprint_history",
    "improving",
    "/archive/",
)

# R57 round 1 Architect／QA 交叉指出（DEF-101-479）：原掃描面只有 tracked `*.md`，
# 完全看不到**執行期真的印給使用者複製貼上**的訊息——`AutoClaude/tools/git-hooks/pre-push`
# 與 `AutoClaude/tools/local_ci_gate.py` 當時各有一處壞形態，這道鎖卻全綠。那比文件更要命：
# 那是 push 被擋當下的唯一指引，mac 使用者照做 → `zsh: no matches found` → 再 push 再被擋，
# 形成迴圈。故掃描面擴為「tracked *.md + *.sh + *.py + 三處 git-hooks 無副檔名檔」。
# `.ps1` 刻意不納入：PowerShell 無此 glob 語意，納入只會製造偽陽性。
_SCAN_PATHSPECS = ("*.md", "*.sh", "*.py")
_HOOK_DIRS = ("tools/git-hooks", "AutoClaude/tools/git-hooks", "AISDLC_SDD/.githooks")

# 掃描面下限：防「glob/排除清單被改壞導致掃 0 份檔案卻靜默綠燈」的 fail-open。
# R57 擴面後實測 tracked 檔（扣除排除項）為 3000+ 份，取保守下限。
_MIN_SCANNED = 500

# 已加引號的正確形態下限：本鎖若只斷言「沒有未加引號」，把全部 extras 指令從文件裡
# 刪光也會綠。釘一個正確形態的數量下限，讓「修復被整段刪除」也有訊號。
# R57 修復後實測 30 處（含 ONBOARDING 雷區表與帳本說明文字中的示範）。
_MIN_QUOTED = 20

# 行內豁免標記（見 docstring §豁免機制）。刻意引述壞形態的行專用。
# R57 round 1 擴面後改為**語言中立**：不再綁死 HTML 註解，`# zsh-glob-ok: 理由`（Python/bash）
# 與 `<!-- zsh-glob-ok: 理由 -->`（markdown）皆可，理由取到行尾或 `-->` 之前。
_EXEMPT_RE = re.compile(r"zsh-glob-ok:\s*(?P<why>.*?)\s*(?:-->\s*)?$")

# 豁免總數上限：豁免是給「必須引述壞例子」這類少數情境用的，不是給人繞過的後門。
# 超過此數＝豁免正在被濫用，fail-loud 要求人重新檢視（同 check_script_parity 對
# `_SINGLE_SIDED_EXEMPT` 的 stale 反向檢查精神）。
# R57 擴面後實際豁免 3 行：ONBOARDING §5 雷區表 1 行 + 本檔 docstring 病例樣本 2 行
# （本檔是這道鎖的實作，內含壞形態是本質需求；整檔排除才是 fail-open，故仍走逐行豁免）。
_MAX_EXEMPTIONS = 5


def _tracked_scan_targets() -> list[Path]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z", *_SCAN_PATHSPECS, *_HOOK_DIRS],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout
    paths = []
    for rel in out.split("\0"):
        if not rel:
            continue
        if any(sub in rel for sub in _EXCLUDED_SUBSTRINGS):
            continue
        paths.append(_REPO_ROOT / rel)
    return paths


class TestExtrasQuotingZshSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.files = _tracked_scan_targets()

    def test_scan_surface_not_silently_shrunk(self) -> None:
        """掃描面下限：排除清單或 glob 被改壞時 fail-loud，而非掃 0 份仍綠。"""
        self.assertGreaterEqual(
            len(self.files),
            _MIN_SCANNED,
            f"掃描面只剩 {len(self.files)} 份 < 下限 {_MIN_SCANNED}"
            "——排除清單或 git ls-files pathspec 疑似被改壞（fail-open 風險）",
        )

    def _scan(self) -> tuple[list[str], list[tuple[str, str]]]:
        """回傳 (未豁免的違規行, [(位置, 豁免理由)])。"""
        offenders: list[str] = []
        exemptions: list[tuple[str, str]] = []
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(_REPO_ROOT).as_posix()
            for lineno, line in enumerate(text.splitlines(), 1):
                if not _UNQUOTED_EXTRAS_RE.search(line):
                    continue
                exempt = _EXEMPT_RE.search(line)
                if exempt:
                    exemptions.append((f"{rel}:{lineno}", exempt.group("why")))
                else:
                    offenders.append(f"{rel}:{lineno}: {line.strip()[:110]}")
        return offenders, exemptions

    def test_exemptions_are_audited(self) -> None:
        """豁免必須附非空理由、且總數受限——防豁免退化為靜默放行的後門。"""
        _, exemptions = self._scan()
        self.assertLessEqual(
            len(exemptions),
            _MAX_EXEMPTIONS,
            f"zsh-glob-ok 豁免已達 {len(exemptions)} 行 > 上限 {_MAX_EXEMPTIONS}，"
            f"疑似被當成繞過手段：{exemptions}",
        )
        for where, why in exemptions:
            self.assertTrue(
                why.strip(),
                f"{where} 的 zsh-glob-ok 豁免未附理由——豁免必須說明為何該行必須引述壞形態",
            )

    def test_no_unquoted_extras_in_live_docs(self) -> None:
        offenders, _ = self._scan()
        self.assertEqual(
            offenders,
            [],
            "以下文件的 extras 安裝指令未加引號，macOS zsh 下會 `no matches found`、"
            "指令根本不會執行（R57 DEF-101-479）。修法：`install -e '.[dev,notifications]'`\n"
            + "\n".join(offenders),
        )

    def test_quoted_form_still_present(self) -> None:
        """防「把 extras 指令整段刪掉」這種也能讓上一支測試變綠的退化。"""
        quoted = 0
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            quoted += len(re.findall(r"pip\s+install\s+(?:--?[A-Za-z][A-Za-z-]*\s+)*'\.\[", text))
        self.assertGreaterEqual(
            quoted,
            _MIN_QUOTED,
            f"全 repo 活文件只剩 {quoted} 處加引號的 extras 指令 < 下限 {_MIN_QUOTED}"
            "——安裝說明疑似被整段刪除；本鎖的『無未加引號』因而變成空洞的真",
        )


if __name__ == "__main__":
    unittest.main()
