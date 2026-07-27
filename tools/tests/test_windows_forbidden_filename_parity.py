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

**R58 訂正（DEF-101-B13）：本家族宣稱的機制原為「NTFS／Win32 裝置名解析」，已被實測
證偽**。原生 Windows 11 + git 2.51.0.windows.1、以 raw Win32（ctypes CreateFileW +
GetFileType）與系統暫存目錄內的一次性 git repo 量測：帶目錄前綴的 `CON`／`AUX`／
`CON .txt`／`NUL .log`／`CONIN$` 一律被 Win32 建成**普通檔案**（FILE_TYPE_DISK、
listdir 看得到），並沒有「撞到裝置」；尾隨空白/句點也**不是不允許，而是被靜默剝除
改名**（`'trail_space '` 落地成 `trail_space`）。真正拒絕的層是 **Git for Windows**
（`is_valid_win32_path()` / `mingw_open()` 的 DOS 裝置名黑名單）：`git add` 對這些路徑
rc=128 `open(...): No such file or directory` + `unable to index file`。
誤植的機制造成過實害——四處清單照「Win32 裝置名解析」推導，於是漏掉真正會讓 git
失效的 `CONIN$`／`CONOUT$`（DEF-101-B3，R58 同輪修復）。完整量測、三段式涵蓋面宣稱
與覆核指令收斂在 `tools/check_ntfs_paths.py` 檔頭〈實測機制〉一節（本檔不重抄，免漂移）。

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry_hygiene import empty_reason_keys  # noqa: E402  名冊衛生判準 SSOT

sys.path.insert(0, str(_TOOLS_DIR / "lib"))
import bash_probe_spec as _spec  # noqa: E402

_AUTOCLAUDE_DIR = REPO_ROOT / "AutoClaude"
if str(_AUTOCLAUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTOCLAUDE_DIR))
from autoclaude.utils import logger as autoclaude_logger  # noqa: E402

PRE_COMMIT_HOOK = REPO_ROOT / "tools" / "git-hooks" / "pre-commit"

_FUNC_RE = re.compile(r"^_ntfs_seg_bad\(\)\s*\{.*?^\}\s*$", re.MULTILINE | re.DOTALL)

# R58（DEF-101-B3）：`CONIN$`／`CONOUT$` 為 Git for Windows 黑名單成員（實測 git add
# rc=128），R58 補進四處清單，故一併納入本組正樣本。
RESERVED_NAMES = ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9",
                  "CONIN$", "CONOUT$"]
# R58（DEF-101-B3）：`CONERR$` 是**證偽樣本**——掃描員原提案把它與 CONIN$/CONOUT$ 並列，
# 但實測裸名 `CONERR$` 是 FILE_TYPE_DISK 普通檔案（不是裝置）且 `git add` rc=0 成功入
# index；`CONPRN$` 同。`CONIN`／`CONOUT`（少了 `$`）實測 git 亦接受（rc=0）。四處都不得
# 誤擋這些名字，否則等於憑推導而非量測擴大封鎖面（本鎖即為此把證偽結論釘死）。
NON_RESERVED_NAMES = ["CONSOLE", "PRINTER", "COM10", "LPTX", "NULLABLE", "hello",
                      "CONERR$", "CONPRN$", "CONIN", "CONOUT"]


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
    "CONIN$ .txt",  # R58：console handle 名疊加尾隨空白（實測 git add rc=128）
]

# 剝除尾隨空白後不得誤判成保留名（防修復引入偽陽性）
BENIGN_TRAILING_SPACE_SEGMENTS = [
    " .txt",  # 純空白 base → 剝完是空字串，不可匹配任何保留名
    "   .gitignore",
    "CONSOLE .txt",  # 非保留名
    "COM10 .txt",  # COM10 不在 COM[0-9] 內
    "my con file.txt",  # 保留名出現在中段，非 base
    "CONERR$ .txt",  # R58 證偽樣本：git 實測接受 CONERR$（rc=0），不得因形似而誤擋
]

# R58（DEF-101-B3）：console handle 保留名的**無尾隨空白**基本形態。與上兩組分開列，
# 因為缺陷成因不同——上兩組是「判定順序缺口」（rstrip 作用於整串），本組是「清單本身
# 缺項」（四處都只收 CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]，照 Win32 裝置名解析推導而漏掉
# git 黑名單獨有的兩個帶 `$` 名）。本組同樣是跨子專案 SSOT，由
# `TestCrossSubprojectSampleParity` 鎖住與 AISDLC_SDD 側逐字相同。
CONSOLE_HANDLE_RESERVED_SEGMENTS = [
    "CONIN$",
    "CONOUT$",
    "conin$",  # 大小寫不敏感（實測 git 對小寫同樣 rc=128）
    "CONIN$.txt",  # 帶副檔名（實測 git 同樣 rc=128）
    "CONOUT$.tar.gz",  # 多重副檔名
]

# 形似但實測 git 接受（rc=0、成功入 index）→ 四處皆不得誤擋
CONSOLE_HANDLE_BENIGN_SEGMENTS = [
    "CONERR$",  # 裸名實測 FILE_TYPE_DISK＝根本不是裝置；掃描員原提案含它，經實測證偽
    "CONPRN$",  # 同上（不在 Git for Windows 黑名單內）
    "CONIN",  # 少了 `$` 即非保留名
    "CONOUT",
    "CONINX",  # `$` 位置換成其他字元
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


class TestConsoleHandleReservedNameCrossConsistency(unittest.TestCase):
    """R58（DEF-101-B3）：`CONIN$`／`CONOUT$` 三方（check_ntfs_paths／logger／bash）同擋。

    為何重要（Rule 9 — 測意圖）：這一格的危害不是「open() 炸掉」，而是**git 靜默失效**
    ——實測檔案能在 NTFS 建立（`os.path.isfile()` 為 True）但 `git add` rc=128
    （`open(...): No such file or directory` + `unable to index file`），於是產物「明明
    在磁碟上、git 卻說不存在」。任何以 git 為載具的 CI／dogfooding 取證撞到這格都會
    得到極難診斷的失效，且該檔在 Windows 上**永久無法提交**。

    負樣本同等重要：`CONERR$`／`CONPRN$` 實測 git **接受**（rc=0 並成功入 index），
    掃描員原提案要把 `CONERR$` 與另兩者並列封鎖，經實測證偽。本測試把「證偽結論」
    也釘死，避免下一輪有人憑形似再把它加回去（本 repo 反覆吃過「憑推導而非量測」的虧
    ——`CONIN$` 之所以會漏，正是因為清單當初照 Win32 裝置名解析推導出來的）。
    """

    def test_check_ntfs_paths_flags_console_handle_names(self) -> None:
        for seg in CONSOLE_HANDLE_RESERVED_SEGMENTS:
            with self.subTest(seg=seg):
                reason = check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}")
                self.assertIsNotNone(reason, f"未攔下 console handle 保留名 {seg!r}")
                self.assertIn("保留裝置名", reason)

    def test_check_ntfs_paths_does_not_flag_benign_lookalikes(self) -> None:
        for seg in CONSOLE_HANDLE_BENIGN_SEGMENTS:
            with self.subTest(seg=seg):
                self.assertIsNone(
                    check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}"),
                    f"誤擋 git 實測接受的名字 {seg!r}",
                )

    def test_logger_prefixes_console_handle_names(self) -> None:
        for seg in CONSOLE_HANDLE_RESERVED_SEGMENTS:
            with self.subTest(seg=seg):
                sanitized = autoclaude_logger._sanitize_log_filename(seg)
                self.assertTrue(
                    sanitized.startswith("_"),
                    f"logger.py 未攔下 console handle 保留名 {seg!r}：{sanitized!r}",
                )

    def test_logger_does_not_prefix_benign_lookalikes(self) -> None:
        for seg in CONSOLE_HANDLE_BENIGN_SEGMENTS:
            with self.subTest(seg=seg):
                sanitized = autoclaude_logger._sanitize_log_filename(seg)
                self.assertFalse(
                    sanitized.startswith("_"),
                    f"logger.py 誤擋 git 實測接受的名字 {seg!r}：{sanitized!r}",
                )

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_flags_console_handle_names(self) -> None:
        for seg in CONSOLE_HANDLE_RESERVED_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(rc, 0, f"bash 未攔下 console handle 保留名 {seg!r}：{out!r}")
                self.assertIn("保留裝置名", out)

    @unittest.skipIf(_BASH is None, _SKIP_REASON)
    def test_bash_does_not_flag_benign_lookalikes(self) -> None:
        for seg in CONSOLE_HANDLE_BENIGN_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(rc, 1, f"bash 誤擋 git 實測接受的名字 {seg!r}：{out.strip()!r}")


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

    def test_console_handle_reserved_samples_identical(self) -> None:
        """R58（DEF-101-B3）：新增第三組樣本時同步納入本鎖，不讓「四處樣本一份」的
        既有判例只涵蓋 R57 那兩組——新組若不入鎖，就會重演該判例誕生的原因。"""
        self.assertEqual(
            _literal_list_from(_SDD_SAMPLE_FILE, "CONSOLE_HANDLE_RESERVED"),
            CONSOLE_HANDLE_RESERVED_SEGMENTS,
            "根層與 AISDLC_SDD 側的 console handle reserved 樣本已分歧",
        )

    def test_console_handle_benign_samples_identical(self) -> None:
        self.assertEqual(
            _literal_list_from(_SDD_SAMPLE_FILE, "CONSOLE_HANDLE_BENIGN"),
            CONSOLE_HANDLE_BENIGN_SEGMENTS,
            "根層與 AISDLC_SDD 側的 console handle benign（證偽）樣本已分歧",
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


# ---------------------------------------------------------------------------
# R58（DEF-101-B14）：repo-wide **前瞻**防增生鎖 —— 不得出現第 5 份 forbidden-filename
# 獨立實作而無人知曉。
#
# 缺口：本檔在 R58 之前完全沒有 `git ls-files`／`rglob`——只驗「寫死的 4 處實作 + 5 個
# 具名消費者」。第 5 份實作出現在任何**沒被具名**的檔案裡時，本檔全綠、零訊號。這違反
# `docs/06_quality/CrossPlatform_Scan_Dimensions.md` 本 repo 自訂的架構判例第 (3) 條：
# 走「不收斂＋機械 parity 鎖」路線者，須確認 parity 鎖確實有前瞻性（能抓到新增第 N+1
# 份）。同 repo 的 `test_windowsapps_guard_cross_consistency.py::
# test_windows_apps_predicate_impls_are_all_registered` 已有正確做法，本節比照。
#
# 掃描面（刻意與 WindowsApps 那支的政策對齊，但**不排除** AISDLC_SDD 凍結版）：
#   - `git ls-files` 取 tracked 檔（天然排除 .git／.venv／__pycache__／未提交產物）。
#   - 副檔名面＝可能承載此邏輯的程式語言 + 無副檔名的 git hook 檔。
#     實測依據（2026-07-27，本機原生 Windows 11）：把兩錨對**全部 27,439 個 tracked
#     檔**跑一遍（含 .md／.yml／.json），命中集合與本節限定副檔名後**完全相同**，
#     即限定副檔名目前零代價；而全量掃描耗時 17.5s vs 限定後 0.5s（5,744 檔），
#     差 35 倍，在單元測試裡不可接受。
#   - **凍結版 `AISDLC_SDD_v0.01`~`v0.29` 刻意留在掃描面內**（與 WindowsApps 那支相反，
#     此處差異是刻意的）：R45（DEF-101-358）把淨化邏輯抽成 `AISDLC_SDD/scripts/
#     component_sanitizer.py` 共享層後，30 個版本目錄的 `state_loader.py` 全部改為薄
#     委派、**自己不再持有任何保留名/禁用字元字面**。實測確認凍結版目前對兩錨零命中，
#     故把它們留在掃描面內零代價，且正好構成「有人往凍結版塞回一份複本」的回歸鎖
#     ——凍結版不回改（Copy-on-Evolve 鐵律）指的是「不追殺歷史快照的既有內容」，
#     不等於「允許未來往裡面新增違規」。既有 `tools/tests/
#     test_sanitize_component_frozen_sdd_versions_lock.py` 鎖的是委派仍在，方向互補。
#
# 兩錨（聯集）與為何這樣挑：
#   錨 A＝**保留名清單以 `|` 相連的程式碼形態**（`CON|PRN`、`NUL|COM[0-9]`、bash case
#     pattern 亦同）。關鍵鑑別力來自分隔符：本 repo 的**散文/註解**一律寫成斜線
#     （`CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]`），只有真的在寫 regex／case pattern 的
#     程式碼才會用 `|`。實測：錨 A 對 27,439 個 tracked 檔命中 5 支＝4 處生產實作
#     ＋本檔，零偽陽性；若改用寬錨（同檔同時出現 `PRN` 與 `AUX` 兩個 token）則命中
#     12 支，多出的 7 支全是散文提及或測試樣本。
#   錨 B＝**禁用字元集合的連續字面** `<>:"|?*`。補位理由：一個新實作可能只抄字元集合
#     而不抄保留名（DEF-101-343 的 `rtm_file_sink._sanitize_name` 正是這種形狀——
#     「限縮字元集合、缺保留裝置名防護」）。bash 版逐字元寫 case pattern、不含連續
#     字面，故錨 B 抓不到它——這正是要用聯集而非單錨的原因。
#
# 涵蓋面（三段式，Rule 12 fail-loud，勿留「已涵蓋全類別」錯覺）：
#   - **已實測涵蓋**：把 4 處生產實作任一份的 regex 或字元集合字面**整行複製**到
#     掃描面內的新檔（bug-injection 實測，見 `Nightly_Forensic_Discipline` 紀律的
#     紅/綠對照要求）→ 本鎖翻紅。
#   - **已實測不涵蓋**：測試檔（`*/tests/*`、`test_*.py`）刻意排除——測試檔內出現同
#     一字面是「對 SSOT 內容做斷言」而非生產路徑第二實作，比照 WindowsApps 那支的
#     `_is_test_py` 既有慣例。故藏在測試檔名底下的第 5 份實作本鎖看不見。
#   - **未窮舉**：兩錨皆避開者仍逃得掉——保留名改用 tuple/set 字面
#     （`("CON", "PRN", ...)`）、以斜線散文形式寫進 `in` 判斷、或字元集合逐字元展開
#     成 bash 式 case pattern。這是逐行正則相對於 AST 解析的結構性天花板（同
#     DEF-101-333 四方一致裁定），誠實記載而不追殺。
# ---------------------------------------------------------------------------
_SCAN_PATHSPECS = (
    "*.py", "*.sh", "*.bash", "*.ps1", "*.psm1", "*.bat", "*.cmd",
    "tools/git-hooks/*",
)

# device token 的**程式碼形態**：含 `COM[0-9]`／`LPT[0-9]` 這種 regex 字元類寫法，
# 以及 `COM1`～`LPT9` 這種展開寫法，和 R58 新增的 `CONIN$`／`CONOUT$`／`CONERR$`。
_DEVICE_TOKEN = r"(?:CON(?:IN|OUT|ERR)?\$?|PRN|AUX|NUL|COM\[0-9\]|LPT\[0-9\]|COM\d|LPT\d)"
# 兩個 device token 以 `|` 相連（中間容許引號，涵蓋 bash `'CONIN$'|'CONOUT$'` 寫法）。
_RESERVED_ALTERNATION_RE = re.compile(
    rf"{_DEVICE_TOKEN}['\"]?\s*\|\s*['\"]?{_DEVICE_TOKEN}", re.IGNORECASE
)
# 禁用字元集合的連續字面（`'<>:"|?*\\'`；反斜線可有可無，末尾 `\\` 位置不強制）。
_FORBIDDEN_CHARSET_LITERAL_RE = re.compile(r"""<>:\\?"\|\?\*""")

# 已知合法站點（附理由白名單，比照 `_APPROVED_SECOND_IMPLS` 既有慣例）。
# 等值斷言天然含 stale 自檢：登記項若被刪除／改寫成不再命中任一錨，`hits` 就不會包含
# 它而使本鎖翻紅，不會靜默留著死條目。
_APPROVED_FILENAME_RULE_SITES = {
    "tools/check_ntfs_paths.py": "生產實作 ①（Python，CI 全量 tracked 掃描版）",
    "tools/git-hooks/pre-commit": "生產實作 ②（bash，本機 commit 閘；語言邊界）",
    "AutoClaude/autoclaude/utils/logger.py": (
        "生產實作 ③（`autoclaude` 為可獨立 pip 安裝套件，不可依賴 monorepo 根層 "
        "tools/lib/*.py；子專案邊界）"
    ),
    "AISDLC_SDD/scripts/component_sanitizer.py": (
        "生產實作 ④（AISDLC_SDD 可獨立 checkout；同時是 30 個版本目錄的共享 SSOT，"
        "R45 DEF-101-358）"
    ),
    "AutoClaude/autoclaude/plugins/playbook_persistence_plugin.py": (
        "**非**第二實作——`_mutated_path_for()` 委派 SSOT `_sanitize_log_filename`"
        "（DEF-101-442 / R56），只是註解裡逐字提到 `<>:\"|?*` 字元集合而命中錨 B。"
        "由 `TestApprovedSitesActuallyDelegate` 機械確認它真的有委派、不是內嵌一份"
    ),
}


def _scan_candidate_files() -> list[str]:
    """掃描面：tracked 且副檔名在 `_SCAN_PATHSPECS` 內的 repo-relative 路徑（fail-loud）。

    `git ls-files` 失敗一律 AssertionError，不得靜默把掃描面縮成空集合而假綠
    （比照 `test_windowsapps_guard_cross_consistency._tracked_files()` 既有慣例）。
    """
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "-c", "core.quotePath=false", "ls-files", "-z",
         "--", *_SCAN_PATHSPECS],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——掃描邊界不得靜默縮小"
        )
    return sorted({p for p in proc.stdout.split("\0") if p})


def _is_test_file(rel: str) -> bool:
    """測試檔判定（`*/tests/*` 或檔名以 `test_` 開頭）——比照
    `test_windowsapps_guard_cross_consistency._is_test_py()` 既有慣例。"""
    return "/tests/" in rel or Path(rel).name.startswith("test_")


def _matches_filename_rule_anchor(text: str) -> bool:
    """兩錨的**聯集**——任一命中即視為「疑似持有一份 forbidden-filename 判準」。

    抽成純函式（而非內聯在掃描迴圈裡）是刻意的：R56 round 6 在姊妹鎖上以
    bug-injection 證實過，把 `or` 改成 `and`（3 個字元）能讓整組繞過而所有測試維持
    全綠——因為當時「聯集」這個核心交付物本身無鎖。`TestAnchorDiscriminatingPower`
    的兩支單錨樣本在 `and` 語意下必死，即為此設鎖。
    """
    return bool(
        _RESERVED_ALTERNATION_RE.search(text)
        or _FORBIDDEN_CHARSET_LITERAL_RE.search(text)
    )


class TestAnchorDiscriminatingPower(unittest.TestCase):
    """兩錨各自的鑑別力 + 聯集運算子不得被收緊成交集。"""

    def test_union_catches_reserved_alternation_only(self) -> None:
        """只抄保留名 regex（不抄字元集合）→ 錨 A 命中；`and` 語意下必死。"""
        self.assertTrue(_matches_filename_rule_anchor(
            'BAD = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])$")'
        ))

    def test_union_catches_forbidden_charset_only(self) -> None:
        """只抄字元集合（DEF-101-343 `rtm_file_sink._sanitize_name` 的真實形狀）
        → 錨 B 命中；`and` 語意下必死。"""
        self.assertTrue(_matches_filename_rule_anchor("BAD = frozenset('<>:\"|?*')"))

    def test_bash_case_pattern_form_is_caught(self) -> None:
        """bash case pattern（含 R58 新增的引號包住 `$` 寫法）須被錨 A 收攏。"""
        self.assertTrue(_matches_filename_rule_anchor(
            "    CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|'CONIN$'|'CONOUT$')"
        ))

    def test_slash_separated_prose_is_not_flagged(self) -> None:
        """散文/註解慣用斜線分隔 → 不得命中（否則白名單會被偽陽性淹沒，
        而偽陽性壓力正是「有人把鎖放寬」的起點）。"""
        self.assertFalse(_matches_filename_rule_anchor(
            "# 保留裝置名（CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]）防護——舊版僅限縮字元集合"
        ))

    def test_unrelated_alternation_is_not_flagged(self) -> None:
        self.assertFalse(_matches_filename_rule_anchor('re.compile(r"^(foo|bar)$")'))


class TestNoUnregisteredForbiddenFilenameImplementation(unittest.TestCase):
    """repo-wide 前瞻掃描：命中集合必須恰為白名單（多出＝新實作，少掉＝白名單腐化）。"""

    def test_scan_face_is_not_empty(self) -> None:
        """先鎖掃描面非空——否則下面那支會以「零命中 == 零登記」的方式假綠。"""
        candidates = [rel for rel in _scan_candidate_files() if not _is_test_file(rel)]
        self.assertGreater(
            len(candidates), 100,
            f"掃描面只有 {len(candidates)} 支候選檔，遠低於預期量級——`_SCAN_PATHSPECS` "
            "或 git ls-files 行為疑似變更，本鎖可能已零訊號",
        )

    def test_filename_rule_sites_are_all_registered(self) -> None:
        hits = []
        for rel in _scan_candidate_files():
            if _is_test_file(rel):
                continue
            path = REPO_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _matches_filename_rule_anchor(text):
                hits.append(rel)

        self.assertEqual(
            sorted(hits), sorted(_APPROVED_FILENAME_RULE_SITES),
            "forbidden-filename 判準的站點與登記不符——實測："
            f"{sorted(hits)}；登記：{sorted(_APPROVED_FILENAME_RULE_SITES)}。\n"
            "多出的站點代表**掃描面內**出現新的一份保留名清單／禁用字元集合實作："
            "請先確認能否直接委派既有 SSOT（`autoclaude.utils.logger."
            "_sanitize_log_filename` 或 `AISDLC_SDD/scripts/component_sanitizer."
            "sanitize_component`）；確有語言/套件邊界理由才在 "
            "`_APPROVED_FILENAME_RULE_SITES` **附理由**登記，並同步為它加行為鎖。\n"
            "少掉的站點代表登記已腐化（檔案被刪/改名，或該處已不再持有字面）——"
            "請同步清單，勿留死條目。",
        )

    def test_approved_filename_rule_sites_reasons_are_not_blank(self) -> None:
        """登記項的**理由**不得空白（R58 round 7 QA-R58R7-01 落地）。

        為什麼上面那條等值斷言不夠：它比對 `sorted(hits)` vs `sorted(_APPROVED_...)`，而
        **`sorted(dict)` 只列 keys** ⇒ 理由字串完全不在斷言面內。R58 round 6 的收輪紀錄曾
        宣稱這類等值斷言「比 `stale_problems` 更強、結構性在射程外」，round 7 QA **以注入
        證偽**：把既有條目的理由改成純空白，本模組全套仍 `fail=0` 全綠，而同一輸入餵
        `empty_reason_keys()` 立刻具名（Architect 與 SD 兩方當輪都以讀碼背書了那個錯誤宣稱，
        只有做注入的 QA 抓到——**看碼推論輸給實測**）。
        等值斷言在 stale（存在性）那一半確實**更強**（雙向釘鍵，連「新出現而未登記」都抓），
        **但在理由那一半是零**，不是超集。而上一支的失敗訊息就要求「**附理由**登記」：理由
        空白卻永久靜默，正是 `tools/tests/_registry_hygiene.py` docstring 明文譴責的
        「先加豁免再補理由變永久 TODO」。
        """
        self.assertEqual(
            empty_reason_keys(_APPROVED_FILENAME_RULE_SITES), [],
            "下列 `_APPROVED_FILENAME_RULE_SITES` 登記項的理由為空白（或純空白字元）——"
            "上一支的失敗訊息要求「附理由登記」，空白理由等於沒登記理由，會變成永久 TODO",
        )

    def test_scan_loop_goes_through_the_union_helper(self) -> None:
        """掃描端本身必須走 `_matches_filename_rule_anchor()`，不得內聯裸錨。

        WHY（R56 round 6 在姊妹鎖上以 bug-injection 證實過的形狀）：把上一支測試裡的
        helper 呼叫換回內聯 `if _RESERVED_ALTERNATION_RE.search(text) and
        _FORBIDDEN_CHARSET_LITERAL_RE.search(text):`（繞過 helper ＋ 翻運算子的複合
        動作），helper 的單錨測試依然全綠，而 bash 版（只命中錨 A）與任何只抄字元集合
        的新實作（只命中錨 B）會整組逃逸。本斷言直接讀本檔原始碼設鎖。
        """
        src = Path(__file__).read_text(encoding="utf-8")
        body = src.split("def test_filename_rule_sites_are_all_registered", 1)[1]
        body = body.split("\n    def ", 1)[0]
        self.assertIn(
            "_matches_filename_rule_anchor(text)", body,
            "掃描迴圈未呼叫聯集 helper——請勿內聯裸錨",
        )
        for bare in ("_RESERVED_ALTERNATION_RE", "_FORBIDDEN_CHARSET_LITERAL_RE"):
            self.assertNotIn(
                bare, body, f"掃描迴圈內聯了裸錨 {bare}，聯集語意可被靜默翻成交集",
            )


class TestApprovedSitesActuallyDelegate(unittest.TestCase):
    """白名單裡宣稱「非第二實作、只是註解命中」的登記項必須真的委派 SSOT。

    WHY：白名單是本鎖唯一的逃生口。若登記理由寫「它有委派」而實際沒有，本鎖就成了
    「把真正的第 5 份實作正式登記放行」的機制——比沒有鎖更糟（會給出安全的錯覺）。
    故對這類登記項機械覆核委派事實，不憑登記時的文字自述。
    """

    def test_playbook_persistence_plugin_delegates_shared_sanitizer(self) -> None:
        from autoclaude.plugins import playbook_persistence_plugin

        self.assertIs(
            playbook_persistence_plugin._sanitize_log_filename,
            autoclaude_logger._sanitize_log_filename,
            "playbook_persistence_plugin.py 的白名單登記理由是「委派 SSOT、只是註解"
            "命中錨 B」——該委派已不成立，登記理由失效，請重新分診",
        )


if __name__ == "__main__":
    unittest.main()
