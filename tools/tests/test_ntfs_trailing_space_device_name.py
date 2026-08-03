"""R57 回歸鎖：Windows 保留裝置名「保留名 + 尾隨空白 + 副檔名」形態不得逃逸。

缺陷（R57 掃描 B1）：`tools/check_ntfs_paths.py` 與 `tools/git-hooks/pre-commit`
的 `_ntfs_seg_bad()` 都以「切到第一個點」取 base 後直接比對保留名清單——
`CON .txt` 的 base 是 `"CON "`（帶尾隨空白），`^(CON|...)$` / case pattern `CON`
皆不匹配；而「整段以空白或句點結尾」那一條只看整段（`CON .txt` 結尾是 `t`）也
不成立 → 兩道判準之間漏出一個縫，`CON .txt`／`NUL .log`／`LPT1 .yaml` 全數放行。
Windows 實情：Win32 解析裝置名時會忽略基底名後的尾隨空白，此形態在 Windows
checkout 仍會撞到裝置名。

本檔只鎖 monorepo 根層兩處實作（Python CI 版 + bash hook 版）的**行為對等**。
同一缺陷形態另存在於兩處，**R57 主控收尾時已一併修復並各自設鎖**：
`AutoClaude/autoclaude/utils/logger.py._sanitize_log_filename`（第三方，鎖在
`test_windows_forbidden_filename_parity.py::TestTrailingSpaceReservedNameCrossConsistency`）
與 `AISDLC_SDD/scripts/component_sanitizer.py.sanitize_component`（第四處，屬子專案
邊界不可跨界 import，鎖在 `AISDLC_SDD/scripts/tests/
test_component_sanitizer_reserved_trailing_space.py`）。四處成因相同：都是
`rstrip(" .")` 作用於整串、之後才 `split(".", 1)[0]`，故 `CON .txt` 的 stem 皆為 `"CON "`。

────────────────────────────────────────────────────────────────────────────
## R67 併入：目錄段大小寫碰撞（A2）／文件引用大小寫（A15）／Unicode NFC 正規化（B16）

**為何併進本檔而不另開一支**：`tools/tests/` 有一道護欄層檔數棘輪
（`test_adr_xplat001_c1c2_lock.py::TestGuardFileCountShrinkOnlyRatchet`，機械承載
DEF-101-561③／DEF-101-565 的架構級裁決）——「R61 開輪即禁止新增鎖檔、只准合併／刪除」，
理由是護欄層已比它所護的生產碼還大。R67 初版確實另開了一支獨立鎖檔
（`test_path_segment_case_and_nfc_collision.py`），**當場被該棘輪擋下**；依其明示的合法作法
（「把新判準擴充進既有鎖檔」）改為併入本檔。本檔是最貼近的宿主：它既有的職責就是
「monorepo 根層兩處 NTFS 實作（Python CI 版 + bash hook 版）的行為對等」，
R67 三軸全部落在同兩處實作上。**檔名比內容窄是刻意承受的代價**（改名屬另一種變更、
且會打斷既有引用），讀者請以本段為準。

### R67-A2 — 目錄段層級碰撞
`check_ntfs_paths.py` 的碰撞檢查用**整條路徑**做分群鍵、`pre-commit` 的 A3 閘用
`grep -iFx` 做**整行**比對，兩者對「目錄段拼法不同、basename 完全不重複」結構上失明。
本 repo 就是這樣長出 `docs/04_planning/{Archive,archive}/` 與
`docs/06_quality/{Archive,archive}/` 兩對 index 目錄並靜默共存 6 週
（`f81ad94` 用大寫收 improving_01–31、`22782fe` 改小寫收 32–50）。
mac(APFS)／Win(NTFS) 上兩拼法**塌縮成同一個磁碟目錄**、`git status` 全綠＝本機零訊號；
同一 commit 在 Linux CI／github.com 上卻是**兩個獨立目錄**（R67 以 `hdiutil` 建
case-sensitive APFS 卷實測坐實）。危害不是立即覆蓋（basename 不重疊時不會），而是
**同一份程式碼在兩平台掃到不同的檔案集合**，以及交叉引用在 Linux 變死連結。

### R67-A15 — 文件交叉引用大小寫
上述漂移的第一個已實體化症狀：3 處文件把 improving_39 的出處寫成
`docs/04_planning/Archive/AutoSDD_improving_39.md`，而該檔當時實住小寫 `archive/`。
R67 的修法是**收斂目錄拼法為大寫 `Archive/`**（全 repo 外部引用清一色用大寫、兩支
`README.md` 也住大寫側），使這 3 處原地變正確——**一個字都不用改**，因而不必改寫
逐字保全的歷史歸檔帳本 `docs/06_quality/AutoSDD_Defect_Log_archive_02.md`。

### R67-B16 — Unicode NFC 正規化
整組檔名衛生鎖的設計標的清一色是「Windows/NTFS 簽出會不會炸」，沒有一項守
「macOS 簽出會不會炸」。macOS(APFS/HFS+) 對檔名做 NFD、Windows(NTFS) 用 NFC，
git 以 `core.precomposeunicode` 在 macOS readdir 端轉回 NFC；一旦 index 內存的是 NFD
位元組，macOS clone 後該檔即永久呈現「index 一份 NFD、工作樹一份 NFC 未追蹤」的雙重
身影：`git status` 恆不乾淨，且 `git clean -fd` 清掉 phantom 會直接變成 tracked 檔遺失
（兩種不乾淨狀態互斥，無常規手段回到乾淨——R67 實測）。
"""

import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import unittest
from pathlib import Path

# 共用「pre-commit `_ntfs_seg_bad()` 動態抽取 + bash 可用性探測」的既有實作，
# 不再照抄一份（照抄正是本 repo 反覆修同一缺陷多處的根因）。
import test_windows_forbidden_filename_parity as _parity  # noqa: E402

check_ntfs_paths = _parity.check_ntfs_paths

# R57 收尾：兩份樣本清單已上移至 `test_windows_forbidden_filename_parity.py` 作為
# SSOT（該檔同時承載 logger 側第三方鎖，樣本必須同一份才叫「交叉一致」），本檔
# 改為 import 取用。方向單向（parity 檔不 import 本檔）以免循環 import。
RESERVED_TRAILING_SPACE_SEGMENTS = _parity.RESERVED_TRAILING_SPACE_SEGMENTS
BENIGN_TRAILING_SPACE_SEGMENTS = _parity.BENIGN_TRAILING_SPACE_SEGMENTS
LEADING_SPACE_RESERVED_SEGMENTS = _parity.LEADING_SPACE_RESERVED_SEGMENTS


class TestPythonCiChecker(unittest.TestCase):
    """`tools/check_ntfs_paths.py::_ntfs_seg_bad()`（CI 全量 tracked 掃描版）。"""

    def test_flags_reserved_name_with_trailing_space_before_extension(self) -> None:
        for seg in RESERVED_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                reason = check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}")
                self.assertIsNotNone(reason, f"未攔下保留裝置名形態 {seg!r}")
                self.assertIn("保留裝置名", reason)

    def test_does_not_flag_benign_trailing_space_segments(self) -> None:
        for seg in BENIGN_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                reason = check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}")
                self.assertIsNone(reason, f"誤判良性路徑段 {seg!r}：{reason}")

    def test_does_not_flag_leading_space_reserved_segments(self) -> None:
        """R60：validator 側對「保留名 + **前導**空白」必須放行。

        鑑別力方向刻意是**反向**的（斷言「不得攔」而非「必須攔」）：git for Windows 的
        `core.protectNTFS`（＝決定 Windows checkout 會不會整棵樹開不出來的權威模型）
        對本清單全部形態 ACCEPT、clone rc=0，Win32 亦視為普通檔案，故在此攔下＝純偽陽性。
        本斷言存在的理由是這道決策**每輪都會被重新質疑**（前導空白看起來就是 R57 尾隨
        空白形態的鏡像），沒有鎖就會有人「補齊對稱性」而引入偽陽性。
        """
        for seg in LEADING_SPACE_RESERVED_SEGMENTS:
            with self.subTest(seg=seg):
                reason = check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}")
                self.assertIsNone(
                    reason,
                    f"validator 攔下了 git 與 Win32 都接受的前導空白形態 {seg!r}：{reason}",
                )


@unittest.skipIf(_parity._BASH is None, _parity._SKIP_REASON)
class TestBashHookChecker(unittest.TestCase):
    """`tools/git-hooks/pre-commit::_ntfs_seg_bad()`（本機 commit 閘版）——
    動態抽取真實函式原始碼執行，非靜態文字比對。"""

    def test_flags_reserved_name_with_trailing_space_before_extension(self) -> None:
        for seg in RESERVED_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _parity._run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(rc, 0, f"bash 版未攔下保留裝置名形態 {seg!r}（rc={rc}）")
                self.assertIn("保留裝置名", out)

    def test_does_not_flag_benign_trailing_space_segments(self) -> None:
        for seg in BENIGN_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _parity._run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(rc, 1, f"bash 版誤判良性路徑段 {seg!r}：{out.strip()}")

    def test_does_not_flag_leading_space_reserved_segments(self) -> None:
        """R60：bash hook 側與 Python CI 側對前導空白形態必須**同時**放行。

        兩側同步是本檔的存在理由——只有一側改變就會出現「本機 commit 過得去、CI 擋下」
        （或反之）的分裂，而這種分裂比單側偽陽性更難診斷。
        """
        for seg in LEADING_SPACE_RESERVED_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _parity._run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(
                    rc, 1,
                    f"bash 版攔下了 git 與 Win32 都接受的前導空白形態 {seg!r}：{out.strip()}",
                )



REPO_ROOT = _parity.REPO_ROOT
PRE_COMMIT_HOOK = _parity.PRE_COMMIT_HOOK

# NFD／NFC 樣本：'café.md'。NFC = 'caf' + U+00E9；NFD = 'cafe' + U+0301。
_CAFE_NFC = unicodedata.normalize("NFC", "café.md")
_CAFE_NFD = unicodedata.normalize("NFD", "café.md")


def _dir_seg_violations(files: list[str]) -> list[str]:
    """只取「目錄段碰撞」那一類違規（第 5 項）。"""
    violations, _ = check_ntfs_paths._scan_violations(files)
    return [v for v in violations if "目錄段" in v]


def _nfc_violations(files: list[str]) -> list[str]:
    """只取「Unicode 正規化」那一類違規（第 6 項）。"""
    violations, _ = check_ntfs_paths._scan_violations(files)
    return [v for v in violations if "正規化違規" in v]


def _hook_code_lines() -> list[str]:
    """pre-commit 的**可執行程式碼行**（濾掉整行註解與空行）。

    存在理由見 `TestNfcAxisScopeIsCiOnlyByDesign` 內的說明：該 hook 的註解合法地
    談論 NFC/precompose，拿整份檔案比對會把「決策有寫下來」誤判成「決策被違反」。
    """
    text = PRE_COMMIT_HOOK.read_text(encoding="utf-8")
    return [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def _full_path_violations(files: list[str]) -> list[str]:
    """只取「整路徑大小寫碰撞」那一類違規（第 3 項，本輪之前就存在的舊軸）。"""
    violations, _ = check_ntfs_paths._scan_violations(files)
    return [v for v in violations if "大小寫碰撞" in v]


class TestDirSegmentCollisionAxis(unittest.TestCase):
    """R67-A2 判準層：目錄段碰撞軸必須抓得到、且不得誤傷乾淨樹。"""

    def test_flags_dir_segment_collision_with_disjoint_basenames(self) -> None:
        """本缺陷的**確切形態**：目錄段拼法不同，basename 完全不重複。

        這正是本 repo 真實漂移的形狀（Archive/improving_01-31 vs archive/32-50，
        basename 交集為空），也正是舊的整路徑軸抓不到的形狀。
        """
        files = ["docs/x/Foo/a.md", "docs/x/foo/b.md"]
        hits = _dir_seg_violations(files)
        self.assertEqual(len(hits), 1, f"未攔下目錄段碰撞：{files}")
        self.assertIn("docs/x/Foo", hits[0])
        self.assertIn("docs/x/foo", hits[0])

    def test_old_full_path_axis_is_structurally_blind_to_it(self) -> None:
        """反向斷言：舊的整路徑軸對同一組輸入**必須**無感。

        鑑別力方向刻意是反的——若哪天有人把第 5 項刪掉並宣稱「第 3 項已經涵蓋了」，
        這條會證明那是假的。缺了本條，上一條測試無法區分「新軸有效」與
        「本來就抓得到、新軸是裝飾」。
        """
        files = ["docs/x/Foo/a.md", "docs/x/foo/b.md"]
        self.assertEqual(
            _full_path_violations(files),
            [],
            "整路徑軸竟抓到目錄段碰撞——本測試的前提（兩軸正交）已失效，請重讀 R67-A2",
        )

    def test_flags_collision_at_first_segment(self) -> None:
        files = ["Docs/a.md", "docs/b.md"]
        self.assertEqual(len(_dir_seg_violations(files)), 1, "頂層目錄段碰撞未攔下")

    def test_flags_collision_at_deep_nested_segment(self) -> None:
        """深層碰撞會連帶讓其下每一層都成為獨立碰撞群——這是正確行為，不是重複報。

        `a/b/C/d` 與 `a/b/c/d` 在 case-sensitive FS 上確實是兩個不同的目錄，
        與 `a/b/C` vs `a/b/c` 是**不同的兩件事**（各自可能還有別的子項），
        故兩群都要現形。若哪天被「去重」成只報最淺一層，本條會紅。
        """
        files = ["a/b/C/d/e.md", "a/b/c/d/f.md"]
        hits = _dir_seg_violations(files)
        self.assertEqual(len(hits), 2, f"深層目錄段碰撞層數不符：{hits}")
        joined = "\n".join(hits)
        self.assertIn("a/b/C", joined)
        self.assertIn("a/b/C/d", joined)

    def test_clean_tree_has_no_false_positive(self) -> None:
        files = ["docs/x/Foo/a.md", "docs/x/Foo/b.md", "tools/y.py", "README.md"]
        self.assertEqual(_dir_seg_violations(files), [], "乾淨樹被誤判為目錄段碰撞")

    def test_same_dir_repeated_is_not_self_collision(self) -> None:
        """同一個目錄前綴被 N 個檔案重複貢獻，不得自己跟自己碰撞（set 語意）。"""
        files = [f"docs/x/Foo/f{i}.md" for i in range(5)]
        self.assertEqual(_dir_seg_violations(files), [], "同拼法目錄被誤報為碰撞")

    def test_dir_prefixes_excludes_path_itself(self) -> None:
        """`_dir_prefixes` 只回目錄段，不含 path 自身——否則第 5、3 項會重複報同一件事。"""
        self.assertEqual(check_ntfs_paths._dir_prefixes("a/b/c.md"), ["a", "a/b"])
        self.assertEqual(check_ntfs_paths._dir_prefixes("x.md"), [])

    def test_file_vs_dir_same_name_is_not_reported_as_dir_collision(self) -> None:
        """`docs/Foo`（檔）與 `docs/foo/x.md`（目錄）不由第 5 項負責。

        第 5 項的集合只收目錄前綴，故此形態不進入目錄段分群；它是否該被擋屬另一議題
        （git 本身即不允許同名 blob/tree 並存於同一 tree），此處只釘住**不重複報**。
        """
        files = ["docs/Foo", "docs/foo/x.md"]
        self.assertEqual(_dir_seg_violations(files), [], "檔案 vs 目錄同名被誤入目錄段軸")


class TestNfcNormalizationAxis(unittest.TestCase):
    """R67-B16 判準層：NFC 正規化軸。"""

    def test_flags_nfd_index_path(self) -> None:
        hits = _nfc_violations([f"docs/{_CAFE_NFD}"])
        self.assertEqual(len(hits), 1, "NFD 索引路徑未被攔下")
        self.assertIn("phantom", hits[0])

    def test_nfc_path_is_clean(self) -> None:
        self.assertEqual(_nfc_violations([f"docs/{_CAFE_NFC}"]), [], "NFC 路徑被誤判")

    def test_ascii_and_cjk_paths_are_clean(self) -> None:
        """零偽陽性下限：全 ASCII 與 CJK（本身無正規化分解）恆須放行。

        本 repo 文件通篇繁中，若這條會紅，等於加一支中文檔名就被擋——那不是守門，
        是把工具變成障礙物。
        """
        files = ["docs/06_quality/AutoSDD_Defect_Log.md", "docs/測試/繁體中文檔名.md"]
        self.assertEqual(_nfc_violations(files), [], "ASCII/CJK 路徑被誤判為非 NFC")

    def test_collision_key_unifies_nfd_and_nfc_forms(self) -> None:
        """NFD 與 NFC 兩形態在 macOS 上指向同一個磁碟項目 → 必須歸為同一碰撞群。"""
        self.assertEqual(
            check_ntfs_paths._collision_key(f"docs/{_CAFE_NFD}"),
            check_ntfs_paths._collision_key(f"docs/{_CAFE_NFC}"),
            "NFD/NFC 未歸為同鍵——混合形態會從碰撞檢查兩邊漏出去",
        )

    def test_mixed_case_and_normalization_collision_is_caught(self) -> None:
        """「大寫 + NFD」對上「小寫 + NFC」——分成兩把鍵時正是兩邊都漏的形態。"""
        files = [
            f"docs/{unicodedata.normalize('NFD', 'CAFÉ.md')}",
            f"docs/{unicodedata.normalize('NFC', 'café.md')}",
        ]
        self.assertTrue(_full_path_violations(files), "大小寫 × 正規化混合碰撞未被攔下")

    def test_nfd_dir_segment_collides_with_nfc_dir_segment(self) -> None:
        """目錄段軸同樣走正規化鍵——NFD 目錄與 NFC 目錄是同一個磁碟目錄。"""
        files = [
            f"docs/{unicodedata.normalize('NFD', 'café')}/a.md",
            f"docs/{unicodedata.normalize('NFC', 'café')}/b.md",
        ]
        self.assertTrue(_dir_seg_violations(files), "NFD/NFC 目錄段碰撞未被攔下")


class TestNfcAxisScopeIsCiOnlyByDesign(unittest.TestCase):
    """R67-B16 範圍決策鎖：NFC 軸**刻意只在 CI 版實作、不鏡射進 hook 版**。

    這條的鑑別力方向是**反向**的（斷言「hook 不該有」而非「必須有」），理由與
    `test_ntfs_trailing_space_device_name.py` 的前導空白鎖同型：本 repo 的守門慣例是
    「hook 與 CI 版行為對等」，故下一輪掃描者看到「CI 有六項、hook 只有五項」時，
    幾乎必然會把它當成缺口而「補齊對稱性」。實測結論是補了等於加死碼——

      · macOS 端 `git add` 走 argv 有 `precompose_argv`、走目錄走訪有 readdir
        precompose（R67 實測：磁碟 NFD 檔名 `63616665cc812e6d64` 經 `git add .`
        後 index 記為 NFC `636166c3a92e6d64`）；
      · Windows/NTFS 本身即 NFC。

    ⇒ NFD index 項只能由 Linux 貢獻者／GitHub web／plumbing 進來，**那三條路都不經過
    pre-commit**；而它們全都會被 CI 版的全量 tracked 掃描網住。
    """

    def test_ci_version_implements_the_nfc_axis(self) -> None:
        self.assertTrue(
            _nfc_violations([f"docs/{_CAFE_NFD}"]),
            "CI 版失去 NFC 軸——本決策的前提（CI 側兜底）已不成立",
        )

    def test_hook_version_deliberately_omits_the_nfc_axis(self) -> None:
        """只對 hook 的**可執行程式碼行**斷言，不拿整份文件當 haystack。

        取樣必須收窄的理由是實證的：本 hook 的註解**合法地**談論 NFC／precompose
        （就在 A3 閘檔頭的「範圍差異」段，說明為什麼刻意不實作）。拿整份檔案比對會讓
        「把決策寫清楚」這件事本身觸發假紅——正是
        `test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale`
        這道紀律鎖要擋的形態（本測試初版即被它當場攔下）。
        """
        code = _hook_code_lines()
        for marker in ("unicodedata", "is_normalized", "iconv", "uconv"):
            hits = [ln for ln in code if marker in ln]
            self.assertEqual(
                hits, [],
                f"pre-commit 的程式碼（非註解）出現正規化實作痕跡 {marker!r}：{hits}\n"
                "若這是刻意新增，請先讀本測試的 docstring 並更新 "
                "tools/check_ntfs_paths.py 檔頭的『範圍決策』段，不要只是為了對稱而加",
            )

    def test_rationale_is_recorded_where_the_next_scanner_will_look(self) -> None:
        """理由必須留在 CI 版檔頭——決策沒有寫下來就等於沒有做過。"""
        doc = check_ntfs_paths.__doc__ or ""
        self.assertIn("範圍決策", doc, "check_ntfs_paths 檔頭缺少 NFC 軸範圍決策說明")
        self.assertIn("precompose", doc, "範圍決策未載明 precompose 這個關鍵實測依據")


@unittest.skipIf(_parity._BASH is None, _parity._SKIP_REASON)
class TestPreCommitHookDirSegmentCollision(unittest.TestCase):
    """R67-A2 載具層：真 git repo ＋ 真 dispatcher hook 端到端。

    刻意**不**做靜態文字比對——「hook 裡有那段字串」不等於「commit 真的被擋下來」。
    路徑一律用 `docs/…`（不碰 `AutoClaude/`、`AISDLC_SDD/`、`tools/`），使 dispatcher
    只跑 A3 閘、不進任何子專案 leg，測試才不依賴子 hook 是否存在。
    """

    def setUp(self) -> None:
        self.assertTrue(PRE_COMMIT_HOOK.is_file(), f"dispatcher 不存在：{PRE_COMMIT_HOOK}")
        self.tmp = Path(tempfile.mkdtemp(prefix="r67_dirseg_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self._git("init", "-q")
        hooks_dir = self.repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        shutil.copy(PRE_COMMIT_HOOK, hooks_dir / "pre-commit")
        os.chmod(hooks_dir / "pre-commit", 0o755)
        self._git("config", "core.hooksPath", str(hooks_dir))
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")
        # 基線：既有 tracked 目錄 docs/x/Foo/（大寫拼法）。以 --no-verify 建立，
        # 避免基線 commit 自己去跑 A3 閘（此時 tools/ 也在暫存區，會觸發 root-infra leg）。
        self._write("docs/x/Foo/a.md", "a\n")
        self._git("add", "-A")
        r = self._git("commit", "-q", "--no-verify", "-m", "baseline")
        self.assertEqual(r.returncode, 0, r.stderr)

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=str(self.repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )

    def _write(self, rel: str, body: str) -> None:
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")

    def _stage_as(self, index_path: str, body: str) -> None:
        """把內容以**指定的 index 路徑字串**暫存。

        走 plumbing 而非 `git add`：在 case-insensitive FS（本機 macOS）上
        `docs/x/foo/` 與 `docs/x/Foo/` 是同一個磁碟目錄，`git add` 記到哪個拼法取決於
        使用者怎麼打字；用 plumbing 直接指定 index 路徑，使本測試在 case-sensitive
        （Linux CI）與 case-insensitive（mac/Win）兩種 FS 上**行為完全相同**。
        """
        h = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=str(self.repo), input=body, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        self.assertEqual(h.returncode, 0, h.stderr)
        blob = h.stdout.strip()
        r = self._git(
            "-c", "core.ignorecase=false", "update-index", "--add",
            "--cacheinfo", f"100644,{blob},{index_path}",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_hook_blocks_commit_adding_case_variant_directory(self) -> None:
        """注入組：新增 `docs/x/foo/b.md`（小寫）而 `docs/x/Foo/` 已在庫 → 必須擋下。"""
        self._stage_as("docs/x/foo/b.md", "b\n")
        r = self._git("commit", "-m", "inject lowercase dir")
        self.assertNotEqual(r.returncode, 0, f"hook 放行了目錄段碰撞：\n{r.stdout}\n{r.stderr}")
        combined = r.stdout + r.stderr
        self.assertIn("目錄段大小寫碰撞", combined, f"擋下了但訊息不對：\n{combined}")
        self.assertIn("docs/x/foo", combined)
        self.assertIn("docs/x/Foo", combined)

    def test_hook_allows_commit_reusing_existing_directory_spelling(self) -> None:
        """控制組：沿用既有拼法 `docs/x/Foo/c.md` → 必須放行（否則是偽陽性）。"""
        self._stage_as("docs/x/Foo/c.md", "c\n")
        r = self._git("commit", "-m", "same spelling")
        self.assertEqual(r.returncode, 0, f"hook 誤擋同拼法新增：\n{r.stdout}\n{r.stderr}")

    def test_hook_reports_each_colliding_directory_once(self) -> None:
        """同一次 commit 新增 N 檔不得噴 N 次同一則（`seen_dirs` 去重）。"""
        for i in range(3):
            self._stage_as(f"docs/x/foo/m{i}.md", f"m{i}\n")
        r = self._git("commit", "-m", "multi")
        self.assertNotEqual(r.returncode, 0)
        combined = r.stdout + r.stderr
        self.assertEqual(
            combined.count("目錄段大小寫碰撞"), 1,
            f"同一目錄碰撞被重複回報：\n{combined}",
        )


def git_tracked() -> list[str]:
    """本 repo git index 的全部路徑（posix 拼法、byte-exact）。

    抽成模組級唯一實作：本檔有三處判準都以 index 為真相源（目錄段碰撞、路徑引用
    大小寫、歸檔轉址解析），各自複製一份 `ls-files` 呼叫正是本 repo 反覆在治的
    複本型缺陷——觀測同一對象的複本不產生鑑別力。
    """
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True, timeout=120,
    ).stdout
    return [p for p in out.split("\0") if p]


class TestRepoIndexIsConverged(unittest.TestCase):
    """R67-A2 資料層：本 repo 的 index 現況必須維持收斂。"""

    @staticmethod
    def _tracked() -> list[str]:
        return git_tracked()

    def test_index_has_no_directory_segment_collision(self) -> None:
        hits = _dir_seg_violations(self._tracked())
        self.assertEqual(hits, [], "index 內又出現目錄段大小寫碰撞：\n" + "\n".join(hits))

    def test_index_has_no_non_nfc_path(self) -> None:
        hits = _nfc_violations(self._tracked())
        self.assertEqual(hits, [], "index 內出現非 NFC 路徑：\n" + "\n".join(hits))

    def test_archive_dirs_use_the_single_agreed_spelling(self) -> None:
        """收斂結果本身要有鎖：小寫拼法必須歸零、大寫拼法必須有內容。

        `git ls-files` 的 pathspec 在 `core.ignorecase=true` 下會同時匹配兩拼法，
        故一律用 byte-exact 前綴比對，不靠 pathspec。
        """
        tracked = self._tracked()
        for parent in ("docs/04_planning", "docs/06_quality"):
            upper = sum(1 for p in tracked if p.startswith(f"{parent}/Archive/"))
            lower = sum(1 for p in tracked if p.startswith(f"{parent}/archive/"))
            with self.subTest(parent=parent):
                self.assertEqual(lower, 0, f"{parent}/archive/（小寫）復活了 {lower} 筆")
                self.assertGreater(upper, 0, f"{parent}/Archive/（大寫）竟為空")


# 路徑引用抽取樣式：只認「看得出是 repo 相對路徑」且以 .md 結尾者。
# 刻意不認裸 basename（如 `README.md`）——那會把大量散文誤判成路徑引用。
_MD_PATH_REF_RE = re.compile(r"(?:docs|tools|AutoClaude|AISDLC_SDD)/[A-Za-z0-9_./-]*\.md")


def _wrong_case_refs(doc_rel: str, text: str, tracked: set[str],
                     lower_index: dict[str, set[str]]) -> list[tuple[str, str, list[str]]]:
    """回傳 [(來源檔, 被引用路徑, 實際拼法)]——僅限「小寫形式存在、精確拼法不存在」者。

    三分法刻意如此：
      · 精確命中 tracked → 正確，放行；
      · 精確不中、但 lowercase 索引命中 → **大小寫寫錯**，這才是本函式要抓的；
      · 兩者皆不中 → 該路徑根本不是 tracked 檔（模板佔位、外部路徑、已刪檔），
        屬另一類議題（死連結偵測），本鎖**刻意不管**以免變成噪音來源。

    真相源是 **git index**，不是 `Path.exists()`——後者在 macOS/Windows 的
    case-insensitive FS 上對錯誤拼法一樣回 True，那種鎖只會在 Linux 才有牙，
    正是本輪要消滅的形態。
    """
    out = []
    for cand in sorted(set(_MD_PATH_REF_RE.findall(text))):
        if cand in tracked:
            continue
        alts = lower_index.get(cand.lower())
        if alts:
            out.append((doc_rel, cand, sorted(alts)))
    return out


class TestRootDocsPathRefsAreCaseExact(unittest.TestCase):
    """R67-A15 資料層：根層 `docs/` 的 .md 路徑引用必須大小寫精確。

    掃描面刻意限縮在**根層 `docs/`**（軌道① 整合層，即 A15 三處死連結的所在地）：
    範圍小、偽陽性可控、跑得快。子專案文件樹的同類掃描屬另一筆待評估工作，
    如實揭露而非假裝已涵蓋。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.tracked = set(git_tracked())
        cls.lower_index: dict[str, set[str]] = {}
        for p in cls.tracked:
            cls.lower_index.setdefault(p.lower(), set()).add(p)
        cls.root_docs = sorted(
            p for p in cls.tracked if p.startswith("docs/") and p.endswith(".md")
        )

    def test_scan_surface_is_non_empty(self) -> None:
        """掃描面塌成 0 檔時本鎖會靜默全綠——先釘住它真的有東西可掃。"""
        self.assertGreater(len(self.root_docs), 50, "根層 docs/ 的 .md 掃描面異常縮小")

    def test_no_wrong_case_md_path_reference(self) -> None:
        problems: list[tuple[str, str, list[str]]] = []
        for rel in self.root_docs:
            try:
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            problems.extend(_wrong_case_refs(rel, text, self.tracked, self.lower_index))
        self.assertEqual(
            problems, [],
            "文件路徑引用大小寫與 git index 不符（mac/Win 上點得開、Linux/github.com 404）：\n"
            + "\n".join(f"  {d} -> {c}  實際：{a}" for d, c, a in problems),
        )

    def test_scanner_has_discriminating_power(self) -> None:
        """鑑別力自證：同一支判準對「錯拼法」必紅、對「正確拼法」必綠。

        沒有這條，上一條測試在判準壞掉（例如樣式再也匹配不到東西）時會靜默全綠。
        """
        tracked = {"docs/04_planning/Archive/AutoSDD_improving_39.md"}
        lower_index = {p.lower(): {p} for p in tracked}
        bad = _wrong_case_refs(
            "x.md", "見 `docs/04_planning/archive/AutoSDD_improving_39.md` §2",
            tracked, lower_index,
        )
        self.assertEqual(len(bad), 1, "錯拼法引用未被抓出")
        good = _wrong_case_refs(
            "x.md", "見 `docs/04_planning/Archive/AutoSDD_improving_39.md` §2",
            tracked, lower_index,
        )
        self.assertEqual(good, [], "正確拼法引用被誤報")

    def test_the_three_r67_a15_citation_sites_resolve_exactly(self) -> None:
        """點名釘住 R67-A15 的 3 處引用——它們現在靠「目錄收斂為大寫」而成立。

        若未來有人把目錄改回小寫卻沒動這 3 行（或反之），本條會紅。

        🔴 R72 訂正：清單裡的**站點路徑**原本寫死在上層（`docs/04_planning/
        AutoSDD_improving_54.md`），而該檔本輪依歸檔慣例搬進了 `Archive/`
        ⇒ `read_text()` 當場 FileNotFoundError。這正是本 repo 反覆在治的
        「會過期的站點」：鎖以為自己在守引用，其實還多守了一個檔案位置。
        改為經 `resolve_doc_ref()` 解析——清單指名的是**文件**，不是它今天住哪。
        """
        sites = [
            "docs/04_planning/AutoSDD_improving_54.md",
            "docs/06_quality/AutoSDD_ZeroTrust_Audit_54.md",
            "docs/06_quality/AutoSDD_Defect_Log_archive_02.md",
        ]
        target = "docs/04_planning/Archive/AutoSDD_improving_39.md"
        self.assertIn(target, self.tracked, f"{target} 不在 index —— 3 處引用全部變死連結")
        for rel in sites:
            with self.subTest(site=rel):
                actual = resolve_doc_ref(rel, self.tracked)
                self.assertIsNotNone(
                    actual, f"引用站點 {rel} 在上層與 Archive/ 皆查無此檔"
                )
                assert actual is not None
                text = (REPO_ROOT / actual).read_text(encoding="utf-8")
                self.assertIn(target, text, f"{actual} 已不再引用 {target}（引用漂移）")


# ------------------------------------- R72／DEF-101-770：迭代四件套歸檔的轉址解析
# 慣例（兩支 `Archive/README.md`）：整合迭代（軌道①）的計畫 `AutoSDD_improving_<N>.md`
# 與審計 `AutoSDD_ZeroTrust_Audit_<N>.md` 結案後搬進**同層** `Archive/`，只留最新一輪。
#
# 🔴 為何不「搬檔同時把引用一起改掉」（R72 逐案評比後的裁決）：
# 斷鏈引用的持有者有兩類是**明文禁止就地改寫**的，而且兩類都非空——
#   · `docs/06_quality/AutoSDD_Defect_Log_archive_*.md`
#     ——`DEF-101-633` 明訂歷史歸檔帳本逐字保全、不得改寫其散文；
#   · `AISDLC_SDD/AISDLC_SDD_v0.XX/` 凍結版 ——受 Copy-on-Evolve 禁止就地改寫。
# 兩類各只要有一處，「同步更新引用」就在規則上不可能做完；而「留轉址 stub」會憑空
# 長出上百個必須跟著搬檔維護的新檔案（＝新的會過期站點）。
# 規模是**會漂移的量測值，刻意不寫進註解**（初稿寫死的四個數字同輪複查即全部對不上）——
# dated snapshot 與複查方法見 `docs/04_planning/Archive/README.md`。
#
# 採用的是**可推導的轉址規則**而非列舉式映射表：`<dir>/<name>` → `<dir>/Archive/<name>`。
# 表要有人維護、會 stale；規則不用維護，且下面三支鎖讓它「成不成立」變成機械事實。
_ARCHIVABLE_DOC_RE = re.compile(
    r"^docs/(?P<dir>04_planning|06_quality)/(?:Archive/)?"
    r"(?P<name>AutoSDD_improving_\d+(?:_backlog)?\.md"
    r"|AutoSDD_ZeroTrust_Audit_\d+\.md)$"
)
# 從 basename 取輪號（`_backlog` 這類尾綴屬同一輪）。
_ROUND_NO_RE = re.compile(r"_(\d+)(?:_backlog)?\.md$")


def archive_fallback(ref: str) -> str | None:
    """把「上層」引用改寫成同層 `Archive/` 路徑；非可歸檔形態回 `None`。

    刻意**只**對迭代四件套的兩種檔名生效：對任意 `docs/**.md` 都套 Archive 回退
    等於發明一條「找不到就往 Archive 再找一次」的萬用規則，那會把真死連結
    洗成看似可解析，鎖就沒有鑑別力了。
    """
    m = _ARCHIVABLE_DOC_RE.match(ref)
    if m is None:
        return None
    return f"docs/{m.group('dir')}/Archive/{m.group('name')}"


def resolve_doc_ref(ref: str, tracked: set[str]) -> str | None:
    """解析一個 repo 相對 .md 路徑引用；上層與 `Archive/` 皆不中回 `None`。

    真相源是 **git index**，不是 `Path.exists()`——理由同 `_wrong_case_refs()`。
    """
    if ref in tracked:
        return ref
    alt = archive_fallback(ref)
    return alt if alt is not None and alt in tracked else None


def _round_no(path: str) -> int | None:
    m = _ROUND_NO_RE.search(path)
    return int(m.group(1)) if m else None


class TestArchivedIterationDocRefsResolve(unittest.TestCase):
    """R72 資料層：歸檔後，根層 `docs/` 對四件套的引用必須仍解析得到。

    掃描面與 `TestRootDocsPathRefsAreCaseExact` 同（根層 `docs/` 的 .md），
    但問的是**另一個問題**：那道鎖三分法裡「上層與 lowercase 索引皆不中」的那一支
    是**刻意放行**的（避免死連結偵測變噪音來源），於是搬檔造成的斷鏈對它完全隱形。
    本類把「四件套」這個**檔名形態明確、轉址規則明確**的子集從那個縫裡撿回來守。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.tracked = set(git_tracked())
        cls.root_docs = sorted(
            p for p in cls.tracked if p.startswith("docs/") and p.endswith(".md")
        )
        cls.refs: list[tuple[str, str]] = []
        for rel in cls.root_docs:
            try:
                text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for cand in sorted(set(_MD_PATH_REF_RE.findall(text))):
                if _ARCHIVABLE_DOC_RE.match(cand):
                    cls.refs.append((rel, cand))

    def test_scan_surface_is_non_empty(self) -> None:
        """掃描面塌成 0 時本鎖會靜默全綠——先釘住它真的有東西可掃。"""
        self.assertGreater(len(self.root_docs), 50, "根層 docs/ 掃描面異常縮小")
        self.assertGreater(len(self.refs), 40, "四件套路徑引用異常縮小")

    def test_the_fallback_rule_is_actually_load_bearing(self) -> None:
        """至少一處引用**非靠**轉址規則不可解析——否則本鎖是裝飾品。

        鑑別力方向刻意是反的：若哪天有人把歷史引用全部就地改寫成 Archive 路徑
        （＝違反 DEF-101-633 逐字保全），這條會紅並要求先重讀那筆裁決。
        """
        needs = [(d, c) for d, c in self.refs if c not in self.tracked]
        self.assertTrue(
            needs,
            "沒有任何引用需要 Archive 轉址 —— 要嘛歸檔慣例已廢止、"
            "要嘛歷史引用被就地改寫（DEF-101-633 逐字保全被違反）",
        )

    def test_every_archivable_reference_resolves(self) -> None:
        """零白名單上線：實查全部可解析，故不需要任何存量豁免清單。"""
        dead = [
            f"  {d} -> {c}" for d, c in self.refs
            if resolve_doc_ref(c, self.tracked) is None
        ]
        self.assertEqual(
            dead, [],
            "以下四件套引用在上層與 Archive/ 皆查無此檔（真死連結）：\n"
            + "\n".join(dead)
            + "\n合法出口：把檔案搬回慣例位置（上層或同層 Archive/），"
            "**不要**改寫歷史文件的引用——歷史歸檔帳本逐字保全見 DEF-101-633",
        )

    def test_resolver_has_discriminating_power(self) -> None:
        """鑑別力自證：四種輸入各自必須得到不同結果（合成 index，不依賴現況）。"""
        tracked = {
            "docs/04_planning/Archive/AutoSDD_improving_39.md",
            "docs/04_planning/AutoSDD_improving_103.md",
            "docs/06_quality/AutoSDD_Defect_Log_archive_02.md",
        }
        self.assertEqual(
            resolve_doc_ref("docs/04_planning/AutoSDD_improving_39.md", tracked),
            "docs/04_planning/Archive/AutoSDD_improving_39.md",
            "已歸檔的四件套引用未經轉址規則解析到",
        )
        self.assertEqual(
            resolve_doc_ref("docs/04_planning/AutoSDD_improving_103.md", tracked),
            "docs/04_planning/AutoSDD_improving_103.md",
            "仍在上層的引用不該被改寫成 Archive 路徑",
        )
        self.assertIsNone(
            resolve_doc_ref("docs/04_planning/AutoSDD_improving_9999.md", tracked),
            "指向不存在輪號的引用竟被判為可解析 —— 轉址規則太寬",
        )
        self.assertIsNone(
            archive_fallback("docs/06_quality/AutoSDD_Defect_Log_archive_02.md"),
            "轉址規則射程外溢到帳本家族 —— 那個家族不歸檔進 Archive/",
        )

    def test_archive_and_active_round_ranges_do_not_interleave(self) -> None:
        """歸檔一律由最舊往下搬：已歸檔輪號必須全部小於仍在上層的輪號。

        WHY：本區積壓 53 輪的成因之一是「歸檔沒有可機械檢查的完成定義」，
        於是每次都只搬一部分、號段交錯，下一個人看不出還剩哪些該搬。
        本條把「上層只留最新」變成 index 上的可驗事實。
        """
        for parent in ("docs/04_planning", "docs/06_quality"):
            active, archived = [], []
            for p in self.tracked:
                m = _ARCHIVABLE_DOC_RE.match(p)
                if m is None or not p.startswith(f"{parent}/"):
                    continue
                n = _round_no(p)
                if n is None:
                    continue
                (archived if "/Archive/" in p else active).append(n)
            with self.subTest(parent=parent):
                if not active or not archived:
                    continue
                self.assertGreater(
                    min(active), max(archived),
                    f"{parent}：上層仍留著第 {min(active)} 輪，"
                    f"但第 {max(archived)} 輪已歸檔 —— 號段交錯代表歸檔只做一半",
                )


if __name__ == "__main__":
    unittest.main()
