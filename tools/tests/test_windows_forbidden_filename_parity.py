"""交叉一致性鎖：Windows 禁用檔名邏輯的**四處**獨立實作，內容一致但無機械保證。

四處（R57 全 repo `git grep -n -E "PRN|AUX|LPT[0-9]"` 實測，確認恰四處生產實作，
其餘命中皆為測試樣本或委派）：
1. `tools/git-hooks/pre-commit` 的 `_ntfs_seg_bad()`（bash）
2. `tools/check_ntfs_paths.py` 的 `_ntfs_seg_bad()`（Python，CI 全量掃描版）
3. `AutoClaude/autoclaude/utils/logger.py` 的 `_sanitize_log_filename()`
4. `AISDLC_SDD/scripts/component_sanitizer.py` 的 `sanitize_component()`

原始缺口為 R33 Architect 架構深度評估發現（DEF-101-295）。四處保持獨立實作是
**刻意決策**：bash 版無法 import Python 模組（語言邊界）；`logger.py` 屬獨立可 pip
安裝的 `autoclaude` 套件、`component_sanitizer.py` 屬獨立可 checkout 的 AISDLC_SDD
子專案，兩者都不可依賴 monorepo 根層 `tools/lib/*.py`（子專案邊界，見各自檔內註解）。
本檔只負責「漂移即知」，**不合併四者**。

**R57 訂正（DEF-101-478／round 2 SA-R57R2-04）**：本段原文寫「三處」並只列前三處，
而同一輪的 R57 修復已把第 4 處（`component_sanitizer.py`）納入同一缺陷的修復範圍、
且在本檔新增了 `TestCrossSubprojectSampleParity` 跨子專案樣本鎖——**檔頭與檔身當場
矛盾**。這與本輪判為 P2 的 `windows-compat-ci.yml` 檔頭失實（DEF-101-486）是同一
缺陷類別（「宣稱與實況不符」），由 round 2 SA 抓出，一併訂正。第 4 處的行為鎖因
子專案邊界不可跨界 import 而置於
`AISDLC_SDD/scripts/tests/test_component_sanitizer_reserved_trailing_space.py`；
本檔只以 AST 讀檔比對其**樣本清單**（實作可以四份，樣本沒有理由分歧）。

DEF-101（後續修復）：`AutoClaude/autoclaude/models/escalation.py`
（EscalationDump.save）與 `AutoClaude/autoclaude/plugins/checkpoint/_escalation.py`
（last_log_path 顯示字串）曾是同一淨化規則的第四、五個消費者候選——若各自照抄
一份字元集合，即會重蹈本檔存在的理由（同一規則多處獨立實作、其一漏改即復發）。
兩者最終選擇直接 `import` `autoclaude.utils.logger._sanitize_log_filename`（同一顆
函式物件），而非另寫一份，故不需要在本檔新增第四個獨立條目——
`TestEscalationModulesReuseSharedSanitizer` 僅作存在性檢查，鎖住「未來不會有人
在這兩處又內嵌一份新的淨化邏輯」。
"""

import ast
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS_DIR = REPO_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import check_ntfs_paths  # noqa: E402

sys.path.insert(0, str(_TOOLS_DIR / "lib"))
import bash_probe_spec as _spec  # noqa: E402
import sdd_latest  # noqa: E402

_AUTOCLAUDE_DIR = REPO_ROOT / "AutoClaude"
if str(_AUTOCLAUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTOCLAUDE_DIR))
from autoclaude.utils import logger as autoclaude_logger  # noqa: E402

PRE_COMMIT_HOOK = REPO_ROOT / "tools" / "git-hooks" / "pre-commit"

_FUNC_RE = re.compile(r"^_ntfs_seg_bad\(\)\s*\{.*?^\}\s*$", re.MULTILINE | re.DOTALL)

# R60（Scan-B 反駁者自找 #1）：`CONIN$`／`CONOUT$` 納入四處保留名集合。判準的權威模型
# 是 git for Windows 的 `core.protectNTFS`（Windows 預設 true）——本機實測（Win 11 Pro
# 26200 / Git Bash 5.2.37，拋棄式 repo）`git -c core.protectNTFS=true update-index --add
# --cacheinfo` 對 CONIN$.log／CONOUT$.txt／CONIN$／conin$.log／CONIN$.tar.gz／
# CONIN$ .log／CONOUT$   .txt 全數回 `error: Invalid path`；實害是含此類檔名的 repo 在
# Windows 上 `git clone` rc=128、`fatal: unable to checkout working tree`、工作樹**全空**
# （連無關的 plain.txt 也沒有）——不是單檔失敗，是整個 clone 不可用。
RESERVED_NAMES = [
    "CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9", "CONIN$", "CONOUT$",
]
# `CLOCK$` 刻意**不**納入：同批實測 git（protectNTFS=true）對 `CLOCK$.txt`／`CLOCK$ .txt`
# 皆 ACCEPT 且 clone rc=0 正常簽出，擋它只是偽陽性。`CONIN`（少了 `$`）同理 ACCEPT，故
# 正則要求完整 token 而非前綴比對——兩者常駐於此以防未來把三個 `$` 裝置名綁成一組處理。
NON_RESERVED_NAMES = [
    "CONSOLE", "PRINTER", "COM10", "LPTX", "NULLABLE", "hello", "CLOCK$", "CONIN",
]


def _usable_bash() -> str | None:
    """回傳可跑 repo bash 腳本的 bash 路徑；只有 WSL 佔位 bash、缺 coreutils 的
    殘缺 bash、或無 bash → None。

    邏輯鏡自 `tools/tests/test_pre_push_dispatcher.py::_usable_bash()`（根層
    tools/tests 的既有慣例，本身又鏡自 AISDLC_SDD/scripts/bash_probe.py）——R34
    Scan-B 發現本檔（R33 DEF-101-295 新增）直接無條件呼叫
    `subprocess.run(["bash", ...])`，未比照既有慣例做 skipIf 守門，在 bash 不可用
    或為 WSL 佔位版的環境會拋出未攔截的 FileNotFoundError（ERROR 而非優雅
    SKIP）。刻意獨立複製一份而非跨檔 import 執行邏輯，維持本 repo「共用資料規格
    改走 tools/lib/bash_probe_spec.py，執行邏輯各自獨立」的既有架構決策。
    """
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        gp = Path(git).resolve()
        for up in list(gp.parents)[:4]:
            for sub in ("usr/bin/bash.exe", "bin/bash.exe"):
                c = up / sub
                if c.exists():
                    candidates.append(str(c))
    bare = shutil.which("bash")
    if bare and not any(
        part.lower() == _spec.SYSTEM32_SEGMENT for part in PureWindowsPath(bare).parts
    ):
        candidates.append(bare)
    for cand in candidates:
        try:
            r = subprocess.run(
                [cand, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
            lines = r.stdout.splitlines()
            if (
                r.returncode == 0
                and len(lines) >= 2
                and lines[0].strip() == _spec.PROBE_EXPECT_ECHO
                and lines[1].strip() == _spec.PROBE_EXPECT_DIRNAME
            ):
                return cand
        except Exception:
            continue
    return None


_BASH = _usable_bash()
_SKIP_REASON = "本測試需可用 bash（非 WSL 佔位）驗活 pre-commit 的 _ntfs_seg_bad()"


def _extract_bash_function() -> str:
    text = PRE_COMMIT_HOOK.read_text(encoding="utf-8")
    m = _FUNC_RE.search(text)
    assert m, "pre-commit 內找不到 _ntfs_seg_bad() 函式定義——本測試的抽取假設已失效"
    return m.group(0)


def _run_bash_seg_check(segment: str) -> tuple[int, str]:
    """實際執行 pre-commit 的 `_ntfs_seg_bad()`（動態抽取＋source），非靜態文字比對。"""
    func_src = _extract_bash_function()
    proc = subprocess.run(
        [_BASH, "-c", f'{func_src}\n_ntfs_seg_bad "$1"', "check", segment],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return proc.returncode, proc.stdout


class TestForbiddenCharsCrossConsistency(unittest.TestCase):
    def test_python_sets_match(self) -> None:
        self.assertEqual(
            check_ntfs_paths._FORBIDDEN_CHARS,
            set(autoclaude_logger._WIN_FORBIDDEN_CHARS),
        )

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_flags_every_char_in_python_forbidden_set(self) -> None:
        for ch in sorted(check_ntfs_paths._FORBIDDEN_CHARS):
            rc, out = _run_bash_seg_check(f"file{ch}name")
            self.assertEqual(rc, 0, f"bash 未攔下 Python 集合內的禁用字元 {ch!r}：{out!r}")
            self.assertIn("不允許字元", out)

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_does_not_flag_chars_outside_python_forbidden_set(self) -> None:
        safe_chars = [c for c in "!#$%&'()+,-.0123456789ABCabc_~" if c not in check_ntfs_paths._FORBIDDEN_CHARS]
        for ch in safe_chars:
            rc, out = _run_bash_seg_check(f"file{ch}name")
            self.assertNotIn(
                "不允許字元", out, f"bash 誤攔了不在 Python 禁用集合內的字元 {ch!r}：{out!r}"
            )


class TestReservedNameCrossConsistency(unittest.TestCase):
    def test_python_regexes_agree_on_reserved_names(self) -> None:
        for name in RESERVED_NAMES:
            self.assertTrue(check_ntfs_paths._RESERVED_RE.match(name), name)
            self.assertTrue(autoclaude_logger._WIN_RESERVED_NAME_RE.match(name), name)
            self.assertTrue(autoclaude_logger._WIN_RESERVED_NAME_RE.match(name.lower()), name)

    def test_python_regexes_agree_on_non_reserved_names(self) -> None:
        for name in NON_RESERVED_NAMES:
            self.assertFalse(check_ntfs_paths._RESERVED_RE.match(name), name)
            self.assertFalse(autoclaude_logger._WIN_RESERVED_NAME_RE.match(name), name)

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_flags_every_reserved_name_python_flags(self) -> None:
        for name in RESERVED_NAMES:
            rc, out = _run_bash_seg_check(name)
            self.assertEqual(rc, 0, f"bash 未攔下保留裝置名 {name!r}：{out!r}")
            self.assertIn("保留裝置名", out)

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_does_not_flag_non_reserved_names(self) -> None:
        for name in NON_RESERVED_NAMES:
            rc, out = _run_bash_seg_check(name)
            self.assertNotEqual(rc, 0, f"bash 誤攔了非保留名 {name!r}：{out!r}")


# R33 QA 二審發現：logger.py 原用 rsplit(".", 1) 剝副檔名（只切最後一個點），對多重
# 副檔名的保留名（如 lpt5.tar.gz）算出 stem="lpt5.tar" 而漏判；check_ntfs_paths.py／
# bash 皆用「第一個點起」剝離（split(".", 1) / ${seg%%.*}），三者對此不對稱。已改
# logger.py 為 split(".", 1) 與另兩處一致（DEF-101-295 追加修復）。
MULTI_EXTENSION_RESERVED = ["lpt5.tar.gz", "com1.a.b.c", "aux.setup.retry"]


class TestMultiExtensionReservedNameCrossConsistency(unittest.TestCase):
    def test_check_ntfs_paths_flags_multi_extension_reserved_names(self) -> None:
        for name in MULTI_EXTENSION_RESERVED:
            self.assertIsNotNone(check_ntfs_paths._ntfs_seg_bad(name), name)

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_flags_multi_extension_reserved_names(self) -> None:
        for name in MULTI_EXTENSION_RESERVED:
            rc, out = _run_bash_seg_check(name)
            self.assertEqual(rc, 0, f"bash 未攔下多重副檔名保留名 {name!r}：{out!r}")
            self.assertIn("保留裝置名", out)

    def test_logger_prefixes_multi_extension_reserved_names(self) -> None:
        for name in MULTI_EXTENSION_RESERVED:
            sanitized = autoclaude_logger._sanitize_log_filename(name)
            self.assertTrue(
                sanitized.startswith("_"),
                f"logger.py 未攔下多重副檔名保留名 {name!r}：{sanitized!r}",
            )


# R57 修正（DEF-101-B1）：「保留名 + 尾隨空白 + 副檔名」形態四處實作一致漏判。
# 四處都是先取 base（切到第一個點）再比對保留名，而 `CON .txt` 的 base 是 `"CON "`
# ——帶尾隨空白故不匹配 `^CON$`；「整段以空白/句點結尾」那條又只看整段（結尾是 `t`）
# 也不成立，兩道判準之間漏出一個縫。Win32 解析裝置名會忽略基底名後的尾隨空白，
# 故此形態在 Windows checkout 上仍會撞到裝置。
# 兩份清單定義於本檔＝SSOT：`test_ntfs_trailing_space_device_name.py`（鎖 Python CI
# 版與 bash hook 版的行為對等）反向 import 本檔取用，避免出現第五份複製；方向刻意
# 單向（本檔不 import 該檔）以免循環 import。第四處 `AISDLC_SDD/scripts/
# component_sanitizer.py` 屬子專案邊界、不可跨界 import，其鎖另置於
# `AISDLC_SDD/scripts/tests/test_component_sanitizer_reserved_trailing_space.py`。
RESERVED_TRAILING_SPACE_SEGMENTS = [
    "CON .txt",
    "NUL .log",
    "LPT1 .yaml",
    "con .txt",  # 大小寫不敏感
    "COM9   .md",  # 多個尾隨空白
    "AUX .tar.gz",  # 多重副檔名疊加尾隨空白
    "CONIN$ .log",  # R60：新納入的 CONIN$ 疊加尾隨空白（git 實測 Invalid path）
]

# 剝除尾隨空白後不得誤判成保留名（防修復引入偽陽性）
BENIGN_TRAILING_SPACE_SEGMENTS = [
    " .txt",  # 純空白 base → 剝完是空字串，不可匹配任何保留名
    "   .gitignore",
    "CONSOLE .txt",  # 非保留名
    "COM10 .txt",  # COM10 不在 COM[0-9] 內
    "my con file.txt",  # 保留名出現在中段，非 base
    "CLOCK$ .txt",  # R60：git 實測 ACCEPT + clone rc=0，故 CONIN$/CONOUT$ 的納入不得擴散到它
]

# ── R60：「保留名 + **前導**空白」＝四處實作統一決策的樣本電池 ──────────────────
# WHY 需要這一組：R57 修的是「保留名 + **尾隨**空白 + 副檔名」（DEF-101-478），本輪掃描
# 把前導空白當成它的鏡像形態回報「四處實作 1 擋 3 放」。現象為真（下方逐一釘住），但
# **方向不是「三處漏擋」而是「一處多擋」**，理由由本機實測決定，不由對稱性推論決定：
#   ① git for Windows（core.protectNTFS=true，Windows 預設）對本清單全部形態 **ACCEPT**
#      ——git 只在路徑段**起頭**比對保留名，前導空白使比對失配。只含前導形態的 repo
#      實測 `git clone` rc=0、工作樹有檔、`git status --porcelain` 空、內容讀回正確。
#      對照組（'CON .txt'／'CONIN$.log' 等 git REJECT 的形態）clone rc=128、工作樹全空。
#   ② Win32 只吞**尾隨**空白/句點，不吞前導：本機實測 ' CON.txt'／' CON'／'CON.txt'／
#      ' CON .txt' 四者同時共存於同一目錄（os.listdir 全部列出、各 10 bytes 可讀回）。
# 故兩個 **validator**（check_ntfs_paths.py／pre-commit）與 **logger**（sanitizer，但不做
# 前導正規化）一律放行＝正確；`component_sanitizer.sanitize_component()` 因 `.strip()`
# 會剝前導空白而加 `_` 前綴＝更嚴格，對「產生檔名」的 sanitizer 無害且不改既有行為，
# 刻意保留（該處註解載有兩層理由）。
#
# 本清單的作用是把這個「三放一擋」釘成**雙向**斷言而非放任：任一 validator 開始擋它會
# 翻紅（新偽陽性），`component_sanitizer` 停止前綴也會翻紅（既有行為悄悄改變）。下輪掃描
# 若再把前導空白當鏡像缺口回報，請先讀本段實測。
LEADING_SPACE_RESERVED_SEGMENTS = [
    " CON.txt",
    "  COM1.log",  # 多個前導空白
    " con.txt",  # 大小寫不敏感
    " CON",  # 無副檔名
    " NUL .log",  # 前導 + 尾隨空白疊加（git 實測仍 ACCEPT）
    " CONIN$.log",  # R60 新納入的裝置名亦同（前導空白使 git 失配 → ACCEPT）
]


class TestTrailingSpaceReservedNameCrossConsistency(unittest.TestCase):
    """本檔既有三方鎖（check_ntfs_paths／bash／logger）的第三方——logger 側。

    前兩方由 `test_ntfs_trailing_space_device_name.py` 鎖住；logger 屬 `autoclaude`
    套件、與本檔既有 `TestMultiExtensionReservedNameCrossConsistency` 同一顆
    import 來源，故第三方的鎖放在本檔與姊妹形態並列，維持「同一檔看得到三方」。
    """

    def test_logger_prefixes_reserved_names_with_trailing_space(self) -> None:
        for name in RESERVED_TRAILING_SPACE_SEGMENTS:
            with self.subTest(name=name):
                sanitized = autoclaude_logger._sanitize_log_filename(name)
                self.assertTrue(
                    sanitized.startswith("_"),
                    f"logger.py 未攔下尾隨空白保留名 {name!r}：{sanitized!r}",
                )

    def test_logger_does_not_prefix_benign_trailing_space_names(self) -> None:
        for name in BENIGN_TRAILING_SPACE_SEGMENTS:
            with self.subTest(name=name):
                sanitized = autoclaude_logger._sanitize_log_filename(name)
                self.assertFalse(
                    sanitized.startswith("_"),
                    f"logger.py 誤攔非保留名 {name!r}：{sanitized!r}",
                )

    def test_logger_does_not_prefix_leading_space_reserved_names(self) -> None:
        """R60：前導空白形態在 logger 側**必須放行**（不加 `_` 前綴）。

        理由是實測而非對稱性：git（protectNTFS=true）與 Win32 皆視 ' CON.txt' 為正常
        檔名（見 `LEADING_SPACE_RESERVED_SEGMENTS` 上方實測紀錄），logger 亦不做前導
        正規化，故輸出原樣。本斷言鎖的是「不得為了與 `component_sanitizer` 對稱而在此
        新增擋阻」——那會是純偽陽性；同時鎖住輸出**逐字不變**（`_` 前綴之外的悄悄改寫
        一樣會被抓到）。
        """
        for name in LEADING_SPACE_RESERVED_SEGMENTS:
            with self.subTest(name=name):
                self.assertEqual(
                    autoclaude_logger._sanitize_log_filename(name), name,
                    f"logger.py 對前導空白形態 {name!r} 的輸出已改變——"
                    "git 與 Win32 實測皆視其為正常檔名，不應被淨化",
                )


# R57 round 1 Architect（DEF-101-478）：四處 NTFS 實作屬「語言邊界 ×1 + 子專案邊界 ×2」
# 的必要重複（依 R56 已定案分診），**但樣本資料沒有理由分歧**。第四處
# `AISDLC_SDD/scripts/component_sanitizer.py` 的鎖住在子專案內、依既有裁定不可跨界
# import，其樣本清單於是被抄了一份——而該檔誕生的當輪就已漂移（benign 少一筆 `" .txt"`、
# docstring 自稱五筆實為四筆）。教訓是「明文承認代價」不等於「處理了代價」。
# 本鎖以 **AST 讀檔**（純讀文字、不 import 該子專案的生產程式碼，故不違反邊界裁定）
# 斷言兩份樣本逐字相同：實作可以是四份，樣本必須是一份。
_SDD_SAMPLE_FILE = (
    Path(__file__).resolve().parents[2]
    / "AISDLC_SDD/scripts/tests/test_component_sanitizer_reserved_trailing_space.py"
)


def _literal_list_from(path: Path, name: str) -> list[str]:
    """以 AST 取出模組層 `name = [...]` 的字串常數清單（不執行該模組）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return [ast.literal_eval(e) for e in node.value.elts]
    raise AssertionError(f"{path.name} 內找不到模組層常數 {name}——鎖已 stale，請同步更新")


class TestCrossSubprojectSampleParity(unittest.TestCase):
    """根層與 AISDLC_SDD 側的尾隨空白保留名樣本必須逐字相同。"""

    def test_sdd_sample_file_exists(self) -> None:
        """先鎖檔案存在——否則下面兩支會以 FileNotFoundError 而非有意義的訊號失敗。"""
        self.assertTrue(
            _SDD_SAMPLE_FILE.is_file(),
            f"找不到 {_SDD_SAMPLE_FILE}——第四處實作的鎖疑似被刪除或改名，"
            "四處樣本一致性自此無人看守",
        )

    def test_reserved_samples_identical(self) -> None:
        self.assertEqual(
            _literal_list_from(_SDD_SAMPLE_FILE, "RESERVED_TRAILING_SPACE"),
            RESERVED_TRAILING_SPACE_SEGMENTS,
            "根層與 AISDLC_SDD 側的 reserved 樣本已分歧——四處實作是必要重複，"
            "但樣本資料沒有理由不同（R57 round 1 Architect 判例）",
        )

    def test_benign_samples_identical(self) -> None:
        self.assertEqual(
            _literal_list_from(_SDD_SAMPLE_FILE, "BENIGN_TRAILING_SPACE"),
            BENIGN_TRAILING_SPACE_SEGMENTS,
            "根層與 AISDLC_SDD 側的 benign 樣本已分歧——這正是本鎖誕生的原因"
            "（該檔首版即漏抄 `\" .txt\"`）",
        )

    def test_leading_space_samples_identical(self) -> None:
        """R60 新增的第三組樣本同受本鎖保護。

        WHY 特別需要：這一組的四處**預期行為刻意不同**（validator/logger 放行、
        `sanitize_component` 加前綴），正因如此，只要兩份清單有一份被單方面增刪，
        就會出現「一側鎖住的形態另一側完全沒鎖」的沉默缺口——恰是 R57 建立本鎖時
        踩到的同一形狀（SDD 側 benign 漏抄一筆）。**行為可以分歧，樣本不可以。**
        """
        self.assertEqual(
            _literal_list_from(_SDD_SAMPLE_FILE, "LEADING_SPACE_RESERVED"),
            LEADING_SPACE_RESERVED_SEGMENTS,
            "根層與 AISDLC_SDD 側的前導空白樣本已分歧——四處實作對本形態的預期行為"
            "不同（三放一擋，理由見樣本清單上方實測），但樣本資料必須是同一份",
        )


# R33 QA 一審發現：logger.py 原本缺控制字元淨化，與 bash/check_ntfs_paths.py 不對稱
# （DEF-101-295 修復追加，關閉此維度的既有落差）。0x00 無法放進 subprocess argv，故略過。
CONTROL_CHARS = [chr(c) for c in range(0x01, 0x20)] + [chr(0x7F)]

# \n（0x0A）在 pre-commit 的 bash 版偵測不到（DEF-101-297，backlog）：
# `printf '%s' "$p" | grep '[[:cntrl:]]'` 逐行比對時，換行本身被當成行分隔符消耗掉，
# 不會出現在任一行的「內容」裡讓 [[:cntrl:]] 比對到；兩個 Python 版（`ord(ch) < 0x20`
# 逐字元比對）不受此限。CI 端 check_ntfs_paths.py 仍會擋下，非完全繞過，故不在本輪
# 改寫 bash 邏輯（範圍外），僅在此排除、避免測試本身對已知限制誤報。
#
# \r（0x0D）同理排除（R42 修復，DEF-101-350）：本機真實 Windows 11 + Git Bash 實測
# 確認 `\r` 與 `\n` 同一根因——Git Bash 的 pipe（`printf '%s' "$p" | grep`）在此環境
# 對兩者皆有等效的行終結符消耗行為，`\r` 內容同樣不會出現在 grep 看到的行內容裡。
# 已用 `check_ntfs_paths._ntfs_seg_bad()` 實測確認 CI 端 Python 版仍會擋下 `\r`，非
# 完全繞過，比照 `\n` 既有判例僅在此排除、避免測試本身對已知限制誤報。
_BASH_CONTROL_CHARS = [c for c in CONTROL_CHARS if c not in ("\n", "\r")]


class TestControlCharCrossConsistency(unittest.TestCase):
    def test_check_ntfs_paths_flags_every_control_char(self) -> None:
        for ch in CONTROL_CHARS:
            segment = f"file{ch}name"
            self.assertIsNotNone(check_ntfs_paths._ntfs_seg_bad(segment), repr(ch))

    def test_logger_sanitizes_every_control_char(self) -> None:
        for ch in CONTROL_CHARS:
            segment = f"file{ch}name"
            sanitized = autoclaude_logger._sanitize_log_filename(segment)
            self.assertNotIn(ch, sanitized, f"logger.py 未淨化控制字元 {ch!r}：{sanitized!r}")

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_flags_every_control_char(self) -> None:
        for ch in _BASH_CONTROL_CHARS:
            rc, out = _run_bash_seg_check(f"file{ch}name")
            self.assertEqual(rc, 0, f"bash 未攔下控制字元 {ch!r}：{out!r}")
            self.assertIn("控制字元", out)


class TestEscalationModulesReuseSharedSanitizer(unittest.TestCase):
    """DEF-101（後續修復）：`autoclaude.models.escalation`（EscalationDump.save 組
    escalation_*.md 檔名）與 `autoclaude.plugins.checkpoint._escalation`
    （last_log_path 顯示字串）皆消費 task.step_id（自由格式、無驗證欄位）組檔名，
    是本檔既有三處之外的第四、五個潛在消費者。兩者選擇直接 import
    `autoclaude.utils.logger._sanitize_log_filename`（同一顆函式物件）而非另寫一份
    ——本測試只做存在性檢查，鎖住這個決策不被靜默推翻（未來若有人在這兩處內嵌
    一份新的字元集合，本測試會立即失敗）。"""

    def test_escalation_model_reuses_shared_sanitizer(self) -> None:
        from autoclaude.models import escalation as autoclaude_escalation

        self.assertIs(
            autoclaude_escalation._sanitize_log_filename,
            autoclaude_logger._sanitize_log_filename,
            "escalation.py 必須 import 共用的 _sanitize_log_filename，"
            "不可另寫一份相似邏輯（DEF-101-219/DEF-101-295 反覆復發根因）",
        )

    def test_checkpoint_escalation_helper_reuses_shared_sanitizer(self) -> None:
        from autoclaude.plugins.checkpoint import _escalation as autoclaude_checkpoint_escalation

        self.assertIs(
            autoclaude_checkpoint_escalation._sanitize_log_filename,
            autoclaude_logger._sanitize_log_filename,
            "plugins/checkpoint/_escalation.py 必須 import 共用的 "
            "_sanitize_log_filename，不可另寫一份相似邏輯",
        )

    def test_rtm_file_sink_reuses_shared_sanitizer(self) -> None:
        """DEF-101-343（R42）：rtm_file_sink.py 曾獨立重寫一份限縮字元集合的
        `_sanitize_name`，缺 Windows 保留裝置名防護，改為委派共用函式。"""
        from autoclaude.infra.adapters import rtm_file_sink

        self.assertIs(
            rtm_file_sink._sanitize_log_filename,
            autoclaude_logger._sanitize_log_filename,
            "infra/adapters/rtm_file_sink.py 必須 import 共用的 "
            "_sanitize_log_filename，不可另寫一份相似邏輯",
        )

    def test_rtm_file_feedback_source_reuses_shared_sanitizer(self) -> None:
        """DEF-101-343（R42）：rtm_file_feedback_source.py 曾獨立重寫一份與
        rtm_file_sink 對稱但缺 Windows 保留裝置名防護的 `_sanitize`。"""
        from autoclaude.infra.adapters import rtm_file_feedback_source

        self.assertIs(
            rtm_file_feedback_source._sanitize_log_filename,
            autoclaude_logger._sanitize_log_filename,
            "infra/adapters/rtm_file_feedback_source.py 必須 import 共用的 "
            "_sanitize_log_filename，不可另寫一份相似邏輯",
        )

    def test_translation_learning_sink_reuses_shared_sanitizer(self) -> None:
        """DEF-101-343（R42）：translation_learning_sink.py 曾獨立重寫一份與
        rtm_file_feedback_source 對稱但缺 Windows 保留裝置名防護的 `_sanitize`。"""
        from autoclaude.infra.adapters import translation_learning_sink

        self.assertIs(
            translation_learning_sink._sanitize_log_filename,
            autoclaude_logger._sanitize_log_filename,
            "infra/adapters/translation_learning_sink.py 必須 import 共用的 "
            "_sanitize_log_filename，不可另寫一份相似邏輯",
        )


# ═══════════════════════════════════════════════════════════════════════════
# repo-wide 前瞻枚舉鎖
#
# WHY 前瞻性：以上斷言全是**具名枚舉**（逐一 import 已知 4 份再兩兩比對），只驗白名單內
# 彼此一致，對「有人新增第 5 份較弱的獨立重寫」零訊號。而「新站點」正是本家族真實的復發
# 形狀：DEF-101-219／295／343／346／349／384／390／442／478（**R59 QA 複審逐筆撈帳本原文後訂正本句原先的過度宣稱**：這 9 筆**並非全是「新增獨立重寫」**——`478` 實為**白名單內四份實作的一致行為漂移**（保留名+尾隨空白+副檔名形態四處一起逃逸），`384`／`390`／`442` 則是**新的「漏淨化呼叫點」**，那類檔案的原始碼**根本不含**保留名清單或禁用字元集合字面值，**本鎖的兩個錨結構上看不到它們**。本鎖只覆蓋「新增第 N+1 份**獨立重寫**」這一類；漏淨化呼叫點需要 AST 前瞻掃描〔`442` 原文已明講此機制〕，本輪只把 AST 掃描器當一次性前提查核用過、未機械化，見下方【已實測不涵蓋】)。此前本句原寫「共 9 筆全是新站點，無一筆是
# 白名單內漂移。`docs/06_quality/CrossPlatform_Scan_Dimensions.md` 因此把「parity 鎖須確實
# 有前瞻性（抓得到第 N+1 份）」列為必要重複家族的常設要求（R43 曾為此翻修一次）。本節補上
# 該常設要求——動工時實測**零違規**，故非修現存 bug。
#
# WHY 等值而非下限：下限只在「多一份」時說話，對「某道淨化閘被刪掉」完全沉默，且下限自身
# 會腐化（`run_root_unittests.MIN_TESTS` 連 11 輪沒人重釘的判例）。等值一次拿到兩個方向：
# 多一份＝可能有未經審的第 5 份；少一份＝某道閘消失了（stale 自檢）。等值另外免費得到
# fail-open 防護——pathspec／排除清單被改壞而掃到 0 份時 hits=[] ≠ 註冊表必然翻紅，故刻意
# **不設** `_MIN_SCANNED` 這類額外下限測試。
#
# WHY 不照抄姊妹檔：`test_windowsapps_guard_cross_consistency.py` 同款掃描段 868 行、跨
# R40→R57 翻修約 6 輪、至今掛一筆永久 open 的 P3，體積幾乎全花在「排除註解／字串內的假命中」
# （三語言剝註解、heredoc、引號配對…），而 R46 已證明那是無底洞（繞過從整行註釋→no-op
# 前綴→heredoc 逐層復發）。本節刻意反向取捨：錨保持**粗粒度、不剝註解**。代價是註解提到
# 裝置名清單也會命中（過度觸發）——但過度觸發是 fail-loud（有人得看一眼並登記），漏報才是
# fail-open。代價的**處理**方式（不只承認，見上方 R57「明文承認代價 ≠ 處理了代價」判例）＝
# 註冊表每筆必帶「角色」註記，逼登記者當場分診「是第 5 份實作，還是只是提及」。
#
# 邊界宣稱（三段式，見 CrossPlatform_Scan_Dimensions.md §「邊界宣稱必須實測」）：
#   【已實測涵蓋】① 4 份權威實作全數命中；② 第 5 份實作的三語言形態皆命中——Python
#     `set()`／`frozenset()`／`re.compile(r"^(CON|PRN|…)$")`、bash case glob（`*'<'*|*'>'*|…`
#     與 `CON|PRN|AUX|NUL|COM[0-9]`）、PowerShell `@('CON','PRN',…)` 與 `'<>:"|?*'`；
#     ③ 大小寫不敏感（`('con','prn','aux','nul')` 命中）；④ 無副檔名的 `tools/git-hooks/
#     pre-commit` 在候選面內；⑤ `git ls-files` rc≠0 → AssertionError；⑥ 掃描面塌陷為 0 份
#     → 等值斷言翻紅。
#   【已實測不涵蓋】① 測試檔內的第 5 份實作（`_is_ntfs_test_file` 排除全部 `/tests/` 與
#     `test_*.py`；測試檔出現清單是「對 SSOT 做斷言」，沿用姊妹檔 `_is_test_py` 同款判準）；
#     ② 凍結版 v0.01~v0.29（Copy-on-Evolve 不回改）——實測當前凍結版內**零**錨命中，故該
#     分支改以等價路徑實測：把 LATEST 傳成不存在的版本號後，v0.30 整棵樹 105 份候選（含真實
#     錨命中的生產檔 `counterfactual_replay.py`）全數掉出候選面；③ 尚未 `git add` 的新檔
#     （ls-files 固有性質）；④ 三種副檔名與三處 hook 目錄之外的檔案（`*.md`／`*.yml` 刻意不
#     納入：帳本與文件遍地提及——實測 tracked `*.md`/`*.yml` 中錨命中 6 份，納入只製造偽陽性）。
#     ⑤（R59 SD-R59-02 補，實測）**跨行排版與非正典順序的第 5 份實作**：兩錨都要求
#     字面依序出現且間隙 ≤5 字元，故 PEP8 4 空白縮排的「一名一行」寫法必逃（間隙 8>5）、
#     字母序 `{"AUX","CON","NUL","PRN"}` 必逃、Windows 檔案總管本身的字元順序
#     `[\/:*?"<>|]` 必逃、每項帶行內註解必逃、PowerShell 多行陣列必逃。**現實意義不低**：
#     真的第 5 份若含 COM1~9／LPT1~9，單行會超過 ruff line-length=100，幾乎必然寫成多行。
#     ⑥（R59 QA-R59-01 補，實測）**新的「漏淨化呼叫點」**（DEF-101-384／390／442 的形狀）：
#     那類檔案的原始碼根本不含任何錨字面值，兩錨結構上看不到；`442` 帳本原文已明講所需
#     機制是 AST 前瞻掃描，本輪只把 AST 掃描器當一次性前提查核用過、**未機械化**。
#   【未窮舉】**本清單並非窮舉**，只是本輪真正跑過的項目，不代表已列出全部繞過路徑：任何
#     「錨字面值被改寫但語意等價」的寫法（`CON` 拆成 `"C" + "ON"`、`chr()` 組出字元集合、
#     清單搬進 JSON/YAML 資料檔後讀取…）都在偵測範圍外。本段**不主張**殘餘風險只有某幾項。
# ═══════════════════════════════════════════════════════════════════════════
_SCAN_PATHSPECS = ("*.py", "*.sh", "*.ps1")
# 無副檔名的 hook 檔（`pre-commit` 是 4 份權威實作之一）：以目錄 pathspec 納入，
# 沿用 `tools/tests/test_extras_quoting_zsh_safety.py::_HOOK_DIRS` 既有慣例。
_NTFS_HOOK_DIRS = ("tools/git-hooks", "AutoClaude/tools/git-hooks", "AISDLC_SDD/.githooks")
# R66 ADR-XPLAT-002 Phase 2-D 收斂（DEF-101-624）：本行原是本家族的第 5 份逐字
# 複本（另四份原在 test_component_sanitizer_shared_layer_lock.py／
# test_sanitize_component_frozen_sdd_versions_lock.py／test_windowsapps_guard_bash_parity.py／
# test_windowsapps_guard_cross_consistency.py）。R59 SA-R59-03／ARCH-R59-03 就地標註
# 「收斂時五份應一併處理，勿只改本份」——本次即為該收斂：5 份改為共同 import
# `tools/lib/sdd_latest.py::FROZEN_SDD_PATH_PREFIX_RE`（單一定義，見下方
# `_ntfs_scan_candidates` 改用 `sdd_latest.exclude_frozen_sdd_versions`）。
#
# R59 當時「刻意複製而非 import」的理由——tools/tests/ 無 __init__.py，`-m unittest
# <module>` 與 run_root_unittests.py 的 discover 兩種模式下模組名不同，**跨測試檔**
# import 需 sys.path 手術（R59 主控實跑 `-m unittest tools.tests.test_dev_start` 撞
# ModuleNotFoundError: No module named _platform_helpers 坐實此限制）——不適用於本次
# 收斂：本次是各測試檔改為 import `tools/lib/` 底下的一個共用模組（同
# `bash_probe_spec`／`platform_utils` 既有慣例，走
# `sys.path.insert(0, tools/lib)` 後 `import <module>`），不是測試檔互相 import，
# 故不觸及該限制（R66 Architect 確認）。
#
# 🔴 DEF-101-500 third item（ARCH-R57R3-04）指出 `\d+\.\d+` 抓不到三段版號（如
# v1.0.1）時「N 份會同時靜默誤分類」——這個既知缺口**未隨本次收斂修復**，只是換
# 成「1 份會誤分類」（帳本 DEF-101-521，仍 open，非本輪範圍）。

# 錨①保留裝置名清單字面值：要求 CON→PRN→AUX→NUL 依序出現，之間只隔少量引號／逗號／
# 分隔符，故 regex 交替（`CON|PRN|...`）、Python set、PowerShell 陣列、bash case pattern
# 四種寫法同時涵蓋。錨②Windows 禁用字元集合字面值：同理要求 `<>:"|?*` 依序出現。
# 兩錨取**聯集**——DEF-101-343 的真實形狀是「只淨化字元、完全沒有保留名防護」，
# 那種第 5 份實作只有錨②看得到。
_NTFS_ANCHOR_GAP = r"""['"\s,|/()\[\]]{0,5}"""
_RESERVED_LIST_ANCHOR = re.compile(
    _NTFS_ANCHOR_GAP.join(("CON", "PRN", "AUX", "NUL")), re.IGNORECASE
)
_FORBIDDEN_CHARS_ANCHOR = re.compile(
    r".{0,5}".join(("<", ">", ":", '"', r"\|", r"\?", r"\*")), re.IGNORECASE
)

# R60：4 份權威實作**構造形**的保留名交替——管線分隔、四個基本裝置名之間零其他字元。
# 刻意比錨①（允許 ≤5 字元間隙的引號/逗號/斜線）更嚴，因為它要偵測的是「有人把新裝置名
# 插進基本名之間」這個具體動作，而不是「檔案裡有沒有提到這串名字」。用途與鑑別力邊界見
# `test_each_authoritative_impl_keeps_base_device_names_adjacent` docstring。
_BASE_DEVICE_NAMES_ADJACENT_RE = re.compile(r"CON\|PRN\|AUX\|NUL", re.IGNORECASE)

# 註冊表：鍵＝repo 相對路徑（LATEST 版前綴正規化為 `<LATEST>`，見 `_normalize_latest`），
# 值＝**角色**註記（登記時必須分診：是實作，還是只在註解提及）。
_KNOWN_NTFS_ANCHOR_SITES = {
    # ① 4 份權威實作（必要重複，理由見本檔檔頭：語言邊界 ×1 + 子專案邊界 ×2）
    "tools/git-hooks/pre-commit": "實作：bash 版 _ntfs_seg_bad()",
    "tools/check_ntfs_paths.py": "實作：Python CI 全量掃描版 _ntfs_seg_bad()",
    "AutoClaude/autoclaude/utils/logger.py": "實作：_sanitize_log_filename()（autoclaude 套件邊界）",
    "AISDLC_SDD/scripts/component_sanitizer.py": "實作：sanitize_component()（SDD 子專案邊界）",
    # ② 只在註解／docstring 提及清單，淨化本身走委派或不在此檔——粗粒度錨的必然命中，
    #    非第 5 份實作。這幾筆存在本身就是「錨不剝註解」這個取捨的可見成本。
    "AutoClaude/autoclaude/infra/adapters/rtm_file_sink.py": "註解：DEF-101-343 沿革；實作已委派共用函式",
    "AutoClaude/autoclaude/plugins/playbook_persistence_plugin.py": "註解：說明保留名／禁用字元語意",
    "AISDLC_SDD/<LATEST>/tools/fsm_runtime/counterfactual_replay.py": "註解：提醒組檔名前須淨化",
}


def _latest_sdd_version_name() -> str:
    """LATEST 版目錄名，取自 `sdd_version.py` SSOT（不自寫版本號正則）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_name(REPO_ROOT / "AISDLC_SDD")


def _is_ntfs_test_file(rel: str) -> bool:
    """測試檔內出現錨字面值是「對 SSOT 內容做斷言」，非生產路徑第二實作。
    判準沿用姊妹檔 `test_windowsapps_guard_cross_consistency.py::_is_test_py()`。"""
    return "/tests/" in rel or Path(rel).name.startswith("test_")


def _normalize_latest(rel: str, latest_name: str) -> str:
    """把 LATEST 版目錄名換成 `<LATEST>` 佔位。WHY：Copy-on-Evolve 每次升版都會把整棵樹
    複製到新版號，若註冊表寫死 `AISDLC_SDD_v0.30`，與本鎖無關的升版也會讓它翻紅。"""
    return rel.replace(f"AISDLC_SDD/{latest_name}/", "AISDLC_SDD/<LATEST>/", 1)


def _ntfs_scan_candidates(latest_name: str) -> list[str]:
    """候選檔＝git tracked ∩（三種副檔名 ∪ 三處 hook 目錄），扣除凍結版與測試檔。

    用 `git ls-files` 而非 `rglob`（天然排除 `.git`／`.venv`／`__pycache__`）；rc≠0 一律
    fail-loud，**不可**靜默回空——掃描邊界不得靜默縮小（姊妹檔 `_tracked_files()` 判準）。
    """
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "-c", "core.quotepath=false", "ls-files", "-z",
         "--", *_SCAN_PATHSPECS, *_NTFS_HOOK_DIRS],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——掃描邊界不得靜默縮小"
        )
    non_test = [
        rel for rel in proc.stdout.split("\0") if rel and not _is_ntfs_test_file(rel)
    ]
    # 凍結版依 Copy-on-Evolve 鐵律不回改，不被新規則追殺歷史快照。
    return sdd_latest.exclude_frozen_sdd_versions(non_test, latest_name)


class TestNtfsSanitizerSiteEnumerationIsForwardLooking(unittest.TestCase):
    """repo-wide 掃描：含 NTFS 淨化錨的生產檔集合必須與註冊表**等值**。"""

    def test_registered_sites_match_repo_scan_exactly(self) -> None:
        latest_name = _latest_sdd_version_name()
        candidates = _ntfs_scan_candidates(latest_name)
        hits = sorted(
            _normalize_latest(rel, latest_name)
            for rel in candidates
            if _RESERVED_LIST_ANCHOR.search(
                text := (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            )
            or _FORBIDDEN_CHARS_ANCHOR.search(text)
        )
        self.assertEqual(
            hits,
            sorted(_KNOWN_NTFS_ANCHOR_SITES),
            f"NTFS 淨化錨的站點集合與註冊表不符（本次實掃候選 {len(candidates)} 份）。\n"
            "  · **多出**檔案 → 新增了第 5 份實作（或新的提及）：先確認它與 4 份權威實作**等價**"
            "（保留裝置名／禁用字元／控制字元／尾隨空白或句點，四維度齊全）；能 import 委派就委派"
            "（判例見 TestEscalationModulesReuseSharedSanitizer），確定必須獨立一份時，連同"
            "「角色」註記登記進 _KNOWN_NTFS_ANCHOR_SITES 並補上行為對等斷言。\n"
            "  · **少掉**檔案 → 某份實作／某道淨化閘消失了：確認是刻意移除（而非重構時被順手刪掉、"
            "或檔案改名後淨化邏輯沒跟上），確認後同步下修 _KNOWN_NTFS_ANCHOR_SITES。",
        )

    def test_each_authoritative_impl_keeps_base_device_names_adjacent(self) -> None:
        """R60 新增：4 份權威實作的保留名**交替構造**必須讓四個基本裝置名保持相鄰。

        WHY（本輪真實踩到、且第一版鎖也真的沒鑑別力）：`test_registered_sites_match_repo_
        scan_exactly` 取兩錨**聯集**，所以只要錨②（禁用字元集合 `<>:"|?*`）還命中，某份實作
        掉出錨①也照樣全綠。R60 為納入新裝置名時把它們插進第一與第二個基本名之間，錨①要求
        四者依序且間隙 ≤5 字元，插入後間隙變 17 → 實測 `check_ntfs_paths.py`／`pre-commit`／
        `logger.py` **三處同時**掉出錨①（第四處只因既有 docstring 另有一份斜線分隔的同序
        字樣而倖存），註冊表等值斷言毫無反應。後果不是立刻壞掉，而是**未來**某天錨②被改寫、
        或新的第 5 份實作照抄這種插中間的寫法時，前瞻掃描對它靜默失明。

        WHY 本鎖不直接重用 `_RESERVED_LIST_ANCHOR`：第一版就是那樣寫，實測**注入不紅**——
        因為修法留下的那行說明註解本身含有一份管線分隔的同序字樣，剛好自我滿足了錨①
        （粗粒度錨不剝註解的既知代價，見本檔上方「WHY 不照抄姊妹檔」段）。故本鎖改認
        **構造形**：管線分隔、四名之間不得有任何其他字元。本 repo 的散文一律用斜線或頓號
        分隔，故不會誤滿足。
        **殘留 fail-open（如實揭露）**：若有人在註解裡寫出管線分隔的同序字樣，本鎖會被
        同一手法滿足。要徹底根治需剝註解／AST 解析四種語言，而 R46 已證明那是無底洞；
        本鎖的價值是攔下「無意識地插中間」這個真實發生過的動作，不主張攔下刻意偽裝。
        """
        impls = [rel for rel, role in _KNOWN_NTFS_ANCHOR_SITES.items() if role.startswith("實作")]
        self.assertEqual(
            len(impls), 4,
            f"註冊表中角色為「實作」的條目應為 4 份權威實作，實得 {impls}——"
            "本鎖的前提（檔頭所述「恰四處」）已漂移",
        )
        for rel in impls:
            with self.subTest(rel=rel):
                self.assertNotIn("<LATEST>", rel, "4 份權威實作皆不在版本化目錄下，無需正規化")
                text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
                # 刻意不用 assertRegex：失敗時它會把整個檔案內容 dump 進斷言訊息
                # （logger.py 約 170 行全灌進終端），訊號被雜訊淹沒。
                self.assertTrue(
                    _BASE_DEVICE_NAMES_ADJACENT_RE.search(text),
                    f"{rel} 的保留名交替構造已讓四個基本裝置名不再相鄰——最常見成因是把新"
                    "裝置名插進前兩者之間，這會讓本檔 repo-wide 掃描的錨① 對本檔失明"
                    "（間隙 >5 字元）。請改加在交替清單**尾端**：正則與 case 皆完全錨定，"
                    "順序不影響比對結果。",
                )


if __name__ == "__main__":
    unittest.main()
