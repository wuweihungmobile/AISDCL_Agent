#!/usr/bin/env python3
"""活文件「`VAR=value <指令>` bash 前綴語法必附 PowerShell 對照」機械鎖
（R60 Scan-D D-02 根治，DEF-101-513 家族）。

WHY（為何非得有這道鎖）：
  PowerShell **沒有** `VAR=value <指令>` 這種行內環境變數前綴語法。照抄 bash 形態的
  Windows 使用者拿到的是 `The term 'PYTHONUTF8=1' is not recognized as the name of a
  cmdlet...`（本機 Windows PowerShell 5.1 實測），而且錯誤訊息完全不指向真正的原因，
  看起來像「lint-imports 沒裝」。設環境變數須寫 `$env:VAR=值; <指令>`。
  這個家族已**三度復發、四個站點**，每次都靠人工逐份補：
    - R57：`ONBOARDING.md` §7 補齊；
    - R59（DEF-101-513）：根 `CLAUDE.md` §測試/Lint、`docs/AISDLC_Agent_UserGuide.md`
      §1.4 補齊——但同一份修復**漏掉** `AutoClaude/README.md`；
    - R60 Scan-D D-02：`AutoClaude/README.md` 的 `PYTHONUTF8=1 lint-imports` 仍是
      bash 單邊，且整份 README 的 `$env:` 出現 **0 次**（不是「對照隔太遠」而是
      「完全沒有」）。
  該家族在 R60 之前**零機械鎖**（實查：全 repo 沒有任何檢查器碰過這個形狀），所以
  「下一份新文件又只寫 bash 形態」是必然而非偶然。本測試把它升為機械守門。

判準邊界（誠實劃界，比照 check_pytest_baseline_sites.py docstring 風格）：
  掃描面＝下方 `_LIVE_DOCS` 名冊（**活文件**，非全 repo）。名冊沿用
  `tools/check_pytest_baseline_sites.py::_SCAN_FILES` 的既定語意並補上根 `README.md`
  與 `AISDLC_SDD/CLAUDE.md`。**刻意不掃全 repo `*.md`**：實測（R60 全庫 fence-aware
  掃描）歷史帳本、`docs/04_planning/` improving 系列、AISDLC_SDD 各版
  `scenarios/`／`docs_template/` 的 CI/CD 範本裡有數百處 `VAR=$(...)` 形態，那些是
  **給使用者專案用的 bash/YAML 範本**與**時代快照**，不是「本 repo 開發者照著在自己
  機器上敲的指令」——強掃會製造大量偽陽性，且與本 repo「歷史紀錄檔／時代快照不納管」
  的既定慣例衝突（見 ONBOARDING §7 首段 🔴 與 check_pytest_baseline_sites docstring）。
  擴大範圍時加入 `_LIVE_DOCS` 即可，判定邏輯不需改動。

  命中＝**程式碼圍欄（fenced code block）內**、行首（允許前導空白）形如
  `NAME=值 <後續 token>` 且 `NAME` 為全大寫環境變數慣例（`[A-Z][A-Z0-9_]+`）。
    - 只認 fence 內：散文裡談論這個語法（例如本鎖自己的說明文字、
      `` `VAR=value <指令>` `` 這種反引號引述）不該被當成可執行指令。
    - 只認全大寫：排除 `name='John Doe',`／`className="..."` 這類 Python/TSX 具名引數
      （實測全庫掃描時這是最大宗偽陽性來源）。
    - 只認行首：`# 需 FOO=1 才會啟用` 這種註解行不命中。
  判定：
    - fence 語言屬 PowerShell 家族（`powershell`/`pwsh`/`ps1`/`ps`/`posh`）→ **直接違規**
      （該語法在 PS 根本不存在，寫在 PS 區塊內必然是錯的）。
    - fence 語言屬 POSIX 家族（`bash`/`sh`/`zsh`/`shell`/`console`）**或未標註語言**
      → 要求**同一份文件內**存在 `$env:<同一個 VAR>` 字樣的 PowerShell 對照，否則違規。
    - 其他語言（`python`/`yaml`/`json`/`toml`/`diff`…）→ 略過（非 shell 指令指引）。
  刻意接受的侷限（明說，勿誤讀為完整性保證）：
    - 對照要求是**檔案級**而非「同節／±N 行」。檔案級是本 repo R57／R59 兩次修復
      實際採用的形態（每份文件並列 bash／powershell 兩塊），也避開「節界線怎麼算」
      這個新的漂移來源；代價是理論上有人把對照寫在文件另一端也算過關（節級歸屬
      靠人審，比照 check_pytest_baseline_sites 的「守門粒度＝檔案級」誠實劃界）。
    - 只管 `.md` 活文件，不管 `.ps1`／`.sh`／workflow YAML 內的註解。
  豁免語法：違規行行內含 `envprefix-ok: WHY`（建議 HTML 註解形式）。**WHY 必填**，
  空 WHY 不具豁免力（比照 `baseline-ok:`／`encoding-ok:` 紀律）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

# 活文件名冊（相對 repo 根）。缺席即紅（fail-loud：改名/搬移須同步本清單，
# 防守門範圍靜默失守——手法鏡射 check_pytest_baseline_sites._SCAN_FILES）。
_LIVE_DOCS = [
    "CLAUDE.md",
    "README.md",
    "ONBOARDING.md",
    "useMacWin.md",
    "AutoClaude/CLAUDE.md",
    "AutoClaude/README.md",
    "AISDLC_SDD/CLAUDE.md",
    "docs/AISDLC_Agent_UserGuide.md",
    # 以下兩份非 check_pytest_baseline_sites 名冊成員，但同屬「開發者會照著把指令
    # 貼進自己終端」的活指引，且正是本家族的主場（跨平台指令對照）。R60 實測兩者
    # 現況皆 0 站點，加入純為前瞻覆蓋（未來新增 bash-only 指令即當場被抓）。
    "docs/06_quality/CrossPlatform_Scan_Dimensions.md",
    "AutoClaude/docs/08_deployment/Local_CI_Parity_Guide.md",
]

# 抽取數量下限釘選＝2026-07-28（R60）實測值：名冊內共 4 處 bash 前綴站點
# （CLAUDE.md、ONBOARDING.md、AutoClaude/README.md、docs/AISDLC_Agent_UserGuide.md
# 各 1 處 `PYTHONUTF8=1 lint-imports`）。0 命中＝正則／fence 解析漂移導致靜默縮面，
# 故設下限 fail-loud（比照 check_script_parity._MIN_EXTRACT_COUNTS 慣例）。
_MIN_PREFIX_SITES = 4

_EXEMPT_MARK = "envprefix-ok:"

# 圍欄起訖：``` 或 ~~~（允許 ≤3 空白縮排），info string 為語言標籤。
_FENCE_RE = re.compile(r"^\s{0,3}(?P<ticks>`{3,}|~{3,})\s*(?P<info>\S*)")
# 行首環境變數前綴 + 後續指令 token。VAR 限全大寫（環境變數慣例）。
_PREFIX_RE = re.compile(r"^\s*(?P<var>[A-Z][A-Z0-9_]+)=(?P<val>\S*)\s+(?P<rest>\S.*)$")

_POWERSHELL_LANGS = frozenset({"powershell", "pwsh", "ps1", "ps", "posh"})
_POSIX_LANGS = frozenset({"bash", "sh", "zsh", "shell", "console", ""})


class PrefixSite(tuple):
    """(lineno, lang, var, line) — 具名讀取以免索引魔數散落。"""

    __slots__ = ()

    def __new__(cls, lineno: int, lang: str, var: str, line: str):
        return super().__new__(cls, (lineno, lang, var, line))

    @property
    def lineno(self) -> int:
        return self[0]

    @property
    def lang(self) -> str:
        return self[1]

    @property
    def var(self) -> str:
        return self[2]

    @property
    def line(self) -> str:
        return self[3]


def iter_env_prefix_sites(text: str) -> list[PrefixSite]:
    """回傳文件內所有「fence 內行首 `VAR=值 指令`」站點（判準見模組 docstring）。

    fence 巢狀刻意不支援（markdown 本身也不支援同符號巢狀）；以「同符號、無 info
    string」判為收尾圍欄，這是 markdown 的實際語意。
    """
    sites: list[PrefixSite] = []
    fence: str | None = None
    lang = ""
    for lineno, line in enumerate(text.splitlines(), 1):
        m = _FENCE_RE.match(line)
        if m:
            marker = m.group("ticks")[0] * 3
            if fence is None:
                fence, lang = marker, m.group("info").lower()
                continue
            if marker == fence and not m.group("info"):
                fence, lang = None, ""
                continue
        if fence is None:
            continue
        pm = _PREFIX_RE.match(line)
        if pm:
            sites.append(PrefixSite(lineno, lang, pm.group("var"), line))
    return sites


def _exempt_why(line: str) -> str:
    """抽出 `envprefix-ok:` 後的 WHY（截去 HTML 註解收尾與前後空白；可為空）。"""
    return line.split(_EXEMPT_MARK, 1)[1].split("-->", 1)[0].strip()


def doc_violations(rel: str, text: str) -> list[str]:
    """單一文件的違規清單（空清單＝通過）。純函式，供合成文本自證紅綠。"""
    problems: list[str] = []
    for site in iter_env_prefix_sites(text):
        if _EXEMPT_MARK in site.line and _exempt_why(site.line):
            continue
        if site.lang in _POWERSHELL_LANGS:
            problems.append(
                f"{rel}:{site.lineno}：PowerShell 區塊（```{site.lang}）內出現 "
                f"`{site.var}=…` 前綴語法——PS 沒有這種語法，照抄會得到 "
                f"`The term '{site.var}=…' is not recognized`；改寫為 "
                f"`$env:{site.var}=值; <指令>`｜行文：{site.line.strip()[:90]}"
            )
            continue
        if site.lang not in _POSIX_LANGS:
            continue  # python/yaml/… 非 shell 指令指引，不納管
        if f"$env:{site.var}" in text:
            continue  # 同檔已有 PowerShell 對照
        label = f"```{site.lang}" if site.lang else "未標註語言的圍欄"
        problems.append(
            f"{rel}:{site.lineno}：{label} 內的 `{site.var}=…` bash 前綴語法"
            f"**全檔找不到 PowerShell 對照**（未出現 `$env:{site.var}`）——"
            f"Windows 讀者照抄會得到 `The term '{site.var}=…' is not recognized`。"
            f"修法：加一塊 ```powershell 區塊寫 `$env:{site.var}=值; <指令>`；"
            f"若確定本處不需雙平台對照，於該行加 "
            f"`<!-- {_EXEMPT_MARK} WHY -->`（WHY 必填）｜行文："
            f"{site.line.strip()[:90]}"
        )
    return problems


def scan_live_docs(root: Path = _REPO_ROOT, docs: list[str] | None = None) -> list[str]:
    """掃描活文件名冊，回傳違規訊息清單（含名冊缺席的 fail-loud）。"""
    problems: list[str] = []
    total_sites = 0
    for rel in docs if docs is not None else _LIVE_DOCS:
        path = root / rel
        if not path.is_file():
            problems.append(
                f"找不到掃描目標：{rel}——活文件改名/搬移必須同步 _LIVE_DOCS"
                f"（缺席即紅，防守門範圍靜默失守）"
            )
            continue
        text = path.read_text(encoding="utf-8-sig")
        total_sites += len(iter_env_prefix_sites(text))
        problems.extend(doc_violations(rel, text))
    if total_sites < _MIN_PREFIX_SITES:
        problems.append(
            f"全名冊只抽到 {total_sites} 個 `VAR=值 指令` 站點 < 下限 "
            f"{_MIN_PREFIX_SITES}——fence 解析或 _PREFIX_RE 疑似漂移（靜默縮面成假綠）；"
            f"若確為刻意刪減指令，請同步下修 _MIN_PREFIX_SITES"
        )
    return problems


class TestLiveDocEnvPrefixPlatformParity(unittest.TestCase):
    """真實活文件掃描（本鎖的正職）。"""

    def test_live_docs_have_powershell_counterpart(self) -> None:
        """名冊內每個 bash 前綴站點都有同檔 PowerShell 對照，且 PS 區塊內零前綴語法。"""
        problems = scan_live_docs()
        self.assertEqual(
            problems,
            [],
            "活文件 `VAR=value <指令>` 雙平台對照守門失敗（DEF-101-513 家族）：\n  - "
            + "\n  - ".join(problems),
        )

    def test_known_sites_are_still_discovered(self) -> None:
        """釘住已知站點仍被 fence 解析器看到（防解析器壞掉導致全面假綠）。

        本清單只是庫存盤點（是否附 PowerShell 對照由上一支判），逐份加入的沿革＝
        `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
        """
        found = {
            rel: [s.lineno for s in iter_env_prefix_sites(
                (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
            )]
            for rel in _LIVE_DOCS
            if (_REPO_ROOT / rel).is_file()
        }
        nonempty = {rel: lns for rel, lns in found.items() if lns}
        self.assertEqual(
            sorted(nonempty),
            [
                "AutoClaude/README.md",
                "CLAUDE.md",
                "ONBOARDING.md",
                "docs/AISDLC_Agent_UserGuide.md",
                "useMacWin.md",
            ],
            f"已知站點集合變動——新增活文件請確認已附 PowerShell 對照；"
            f"實測：{nonempty}",
        )

    # ── 以下以合成文本自證判定器紅綠（不落 repo 樹內、不碰任何活文件）──

    def test_bash_fence_without_counterpart_is_violation(self) -> None:
        """bash 區塊有前綴語法、全檔無 `$env:VAR` → 違規（＝D-02 的原始狀態）。"""
        text = "# Doc\n\n```bash\nPYTHONUTF8=1 lint-imports   # 8 kept / 0 broken\n```\n"
        problems = doc_violations("fake.md", text)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("全檔找不到 PowerShell 對照", problems[0])
        self.assertIn("$env:PYTHONUTF8", problems[0])

    def test_bash_fence_with_counterpart_passes(self) -> None:
        """同檔任一處出現 `$env:VAR` → 通過（＝R57/R59/R60 的修復形態）。"""
        text = (
            "# Doc\n\n```bash\nPYTHONUTF8=1 lint-imports\n```\n\n"
            "```powershell\n$env:PYTHONUTF8=1; lint-imports\n```\n"
        )
        self.assertEqual(doc_violations("fake.md", text), [])

    def test_counterpart_must_match_same_var(self) -> None:
        """對照必須是同一個 VAR——別的變數有 `$env:` 不算（防「隔壁有就算過」）。"""
        text = (
            "```bash\nPYTHONUTF8=1 lint-imports\n```\n"
            "```powershell\n$env:PYTHONIOENCODING='utf-8'; foo\n```\n"
        )
        problems = doc_violations("fake.md", text)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("$env:PYTHONUTF8", problems[0])

    def test_prefix_inside_powershell_fence_is_violation(self) -> None:
        """PS 區塊內出現前綴語法 → 直接違規（即使同檔別處有 `$env:VAR`）。"""
        text = (
            "```powershell\nPYTHONUTF8=1 lint-imports\n```\n"
            "散文提到 $env:PYTHONUTF8 也不算對照，因為 PS 區塊本身就是錯的。\n"
        )
        problems = doc_violations("fake.md", text)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("PowerShell 區塊", problems[0])

    def test_unlabeled_fence_is_treated_as_needing_counterpart(self) -> None:
        """未標註語言的圍欄同樣要求對照（任務指定的「未標註平台」情境）。"""
        problems = doc_violations("fake.md", "```\nMYVAR=1 do-thing\n```\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("未標註語言的圍欄", problems[0])

    def test_prose_mention_is_not_a_site(self) -> None:
        """散文/反引號引述該語法不算站點（否則本鎖自己的說明文字就會誤殺）。"""
        text = (
            "PowerShell 沒有 `VAR=value <指令>` 前綴語法，"
            "PYTHONUTF8=1 lint-imports 照抄會失敗。\n"
        )
        self.assertEqual(iter_env_prefix_sites(text), [])
        self.assertEqual(doc_violations("fake.md", text), [])

    def test_non_shell_fence_langs_are_skipped(self) -> None:
        """python/yaml 等非 shell 圍欄不納管（避開具名引數等偽陽性大宗）。"""
        for lang, body in (
            ("python", "TimePeriod={'Start': s}, extra=1"),
            ("yaml", "COVERAGE=$(cat cov.json) something"),
        ):
            with self.subTest(lang=lang):
                self.assertEqual(doc_violations("f.md", f"```{lang}\n{body}\n```\n"), [])

    def test_comment_line_is_not_a_site(self) -> None:
        """註解行內提到 `VAR=1` 不命中（只認行首）。"""
        text = "```bash\n# 需 SD07_REAL_PG_E2E_ENABLED=true + PG DSN\npytest -m pg_real\n```\n"
        self.assertEqual(iter_env_prefix_sites(text), [])

    def test_exemption_requires_why(self) -> None:
        """`envprefix-ok:` 空 WHY 不具豁免力；填了 WHY 才放行。"""
        bare = "```bash\nFOO=1 bar   <!-- envprefix-ok: -->\n```\n"
        self.assertEqual(len(doc_violations("f.md", bare)), 1)
        withwhy = "```bash\nFOO=1 bar   <!-- envprefix-ok: 僅示範 POSIX 語法本身 -->\n```\n"
        self.assertEqual(doc_violations("f.md", withwhy), [])

    def test_missing_roster_file_fails_loud(self) -> None:
        """名冊檔缺席 → fail-loud（防改名後守門範圍靜默縮小）。"""
        problems = scan_live_docs(docs=["no/such/doc_r60.md"])
        self.assertTrue(any("找不到掃描目標" in p for p in problems), problems)

    def test_min_site_floor_fails_loud(self) -> None:
        """抽取數量掉到下限以下 → fail-loud（fence 解析漂移的靜默縮面防護）。"""
        # 單掃一份文件，其站點數必然遠低於全名冊下限（R83 訂正原註解「該檔本就 0 站點」
        # ——useMacWin.md 自 R83 起有 1 個站點，下限判準靠的是 1 < `_MIN_PREFIX_SITES`，
        # 不是「恰好是 0」）
        problems = scan_live_docs(docs=["useMacWin.md"])
        self.assertTrue(any("下限" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
