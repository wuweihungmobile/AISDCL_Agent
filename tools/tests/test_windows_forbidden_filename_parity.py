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

_AUTOCLAUDE_DIR = REPO_ROOT / "AutoClaude"
if str(_AUTOCLAUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTOCLAUDE_DIR))
from autoclaude.utils import logger as autoclaude_logger  # noqa: E402

PRE_COMMIT_HOOK = REPO_ROOT / "tools" / "git-hooks" / "pre-commit"

_FUNC_RE = re.compile(r"^_ntfs_seg_bad\(\)\s*\{.*?^\}\s*$", re.MULTILINE | re.DOTALL)

RESERVED_NAMES = ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"]
NON_RESERVED_NAMES = ["CONSOLE", "PRINTER", "COM10", "LPTX", "NULLABLE", "hello"]


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
]

# 剝除尾隨空白後不得誤判成保留名（防修復引入偽陽性）
BENIGN_TRAILING_SPACE_SEGMENTS = [
    " .txt",  # 純空白 base → 剝完是空字串，不可匹配任何保留名
    "   .gitignore",
    "CONSOLE .txt",  # 非保留名
    "COM10 .txt",  # COM10 不在 COM[0-9] 內
    "my con file.txt",  # 保留名出現在中段，非 base
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


if __name__ == "__main__":
    unittest.main()
