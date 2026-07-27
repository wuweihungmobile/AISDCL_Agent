#!/usr/bin/env python3
"""NTFS 敵意檔名 CI 閘 — tools/git-hooks/pre-commit「NTFS 敵意檔名防護閘（A3）」的 CI 對等。

為何需要：A3 閘只活在本機 pre-commit，`git commit --no-verify`、GitHub web 編輯、
未裝 hooks 的 clone 都可繞過；敵意檔名一旦入庫，所有 Windows(NTFS) checkout 直接
炸掉（無法建檔）或靜默大小寫碰撞覆蓋。本腳本供 root-infra-ci 在雲端複核。

範圍差異（by design）：hook 版只掃「本次 commit 新增（A/C）」路徑；本 CI 版掃
`git ls-files` **全量 tracked 路徑**——已入庫的違規也要現形。

檢查邏輯與 hook 版一致（tools/git-hooks/pre-commit `_ntfs_seg_bad` + 大小寫碰撞 + 長度閘）：
  1. 路徑含控制字元（C locale [:cntrl:]＝0x00-0x1F + 0x7F），或任一路徑段含
     Windows 不允許字元 < > : " | ? * \\，或以空白/句點結尾（見下方〈實測機制〉②）
  2. 任一段去（第一個點起的）副檔名、再剝除尾隨空白後（不分大小寫）為 Windows 保留裝置名
     CON / PRN / AUX / NUL / COM0~9 / LPT0~9 / CONIN$ / CONOUT$（COM0 非 Microsoft
     官方保留名、且實測 Git for Windows 亦接受它，比照
     sindresorhus/filename-reserved-regex 等業界防禦性實作採保守納入）
  3. 大小寫碰撞：兩 tracked 路徑 lowercase 後相同但原字串不同
     （NTFS 大小寫不敏感 → checkout 時互相覆蓋）
  4. MAX_PATH 保守長度閘（DEF-101-039）：Windows 未開 core.longpaths 時絕對路徑上限
     MAX_PATH=260 UTF-16 單位（含結尾 NUL，可用 259）；預留 clone 前綴 59 字元＋NUL
     （C:\\Users\\<user>\\...\\<repo>\\，259−200＝59）→ repo 相對路徑 >200 字元 fail、
     >180 字元 warn（不影響退出碼）。長度＝Unicode code point 數（len()；BMP 字元＝
     1 UTF-16 單位；hook 版以「刪 UTF-8 連續位元組計數」達成同語意且 locale 無關；
     astral 字元低估 1 單位屬可忽略邊角）。

〈實測機制〉—— 真正會壞的層是 **Git for Windows**，不是 NTFS/Win32 拒絕建檔
（R58 訂正 DEF-101-B3／B13。本節每一句都在原生 Windows 11 + git 2.51.0.windows.1
以 raw Win32〔ctypes CreateFileW + GetFileType，restype 須顯式設 HANDLE，否則 64-bit
handle 被截成 c_int、失敗會被誤讀成 FILE_TYPE_UNKNOWN〕與系統暫存目錄內的一次性
git repo 實測取得；覆核指令見本節末）：
  ① 保留裝置名：**帶目錄前綴**時 Win32 一律建成普通檔案——`<dir>\\CON`、`<dir>\\AUX`、
     `<dir>\\PRN`、`<dir>\\COM1`、`<dir>\\LPT1`、`<dir>\\CONIN$`、`<dir>\\CON .txt`、
     `<dir>\\NUL .log` 實測皆 FILE_TYPE_DISK 且真的出現在 listdir 裡。唯一例外是
     **`NUL`：帶目錄前綴仍是裝置**（`<dir>\\NUL` → FILE_TYPE_CHAR、listdir 無此檔）。
     裸名（無目錄前綴）則分三種：`NUL`／`CON`／`CONIN$`／`CONOUT$` → FILE_TYPE_CHAR
     （裝置）；`AUX`／`PRN`／`COM1`／`LPT1` → CreateFileW 直接失敗
     ERROR_FILE_NOT_FOUND(2)（裝置命名空間查得到但機器上無此裝置）；`CONERR$`／
     `COM0`／`LPT0`／`NUL.log`／`CON .txt` → FILE_TYPE_DISK（普通檔案）。
     真正的危害在 git：**檔案建得起來但 git 開不了、進不了 index**——
     `git add` 實測 rc=128 `error: open("<path>"): No such file or directory` +
     `unable to index file`，該產物在 Windows 上永久無法提交，而以 git 為載具的
     CI／dogfooding 取證會出現「檔案明明在、git 說不存在」的難診斷失效。
     成因是 Git for Windows 的 `is_valid_win32_path()` / `mingw_open()` 自帶一份
     DOS 裝置名黑名單，與 Win32 的實際解析結果**不是同一套**。
  ② 尾隨空白／句點：Win32 **不是拒絕，而是靜默剝除改名**——實測 `'trail_space '`
     落地成 `trail_space`、`'trail_dot.'` → `trail_dot`、`'dots...'` → `dots`
     （CreateFileW 皆回 FILE_TYPE_DISK，listdir 顯示已改名）。危害因此是「要的檔名
     跟拿到的檔名不同」而非「建不起來」；git 這一側則明確拒絕：
     `git update-index --add --cacheinfo 100644,<sha>,'trailing '` 實測 rc=128
     `error: Invalid path 'trailing '`（`'trailingdot.'` 同）。故本閘的兩項判準都
     成立，只是**理由**是 git 相容性 + 檔名靜默改名，不是「NTFS 不允許」。
  ③ 本清單與 git 黑名單的**已實測差集**（刻意不對齊，方向皆為本閘更嚴）：
     git 拒絕 COM1~9 但**接受 COM0**；git 拒絕 LPT0~9（含 LPT0）；git **接受
     `CONERR$`／`CONPRN$`**（且 `CONERR$` 裸名實測為 FILE_TYPE_DISK＝根本不是裝置，
     故本清單刻意**不收** `CONERR$`——R58 掃描員原提案含它，經實測證偽）。
  ④ 覆核指令（任一 Windows 機器可重跑；請勿在工作樹跑 git 寫指令，repo 建在暫存目錄）：
       python -c "import ctypes,ctypes.wintypes as w;k=ctypes.WinDLL('kernel32',use_last_error=True);\\
       k.CreateFileW.restype=w.HANDLE;h=k.CreateFileW(r'C:\\Temp\\d\\CON',0x40000000,0,None,2,0x80,None);\\
       print(h, k.GetFileType(h))"
       git init %TEMP%\\p && python -c "open(r'%TEMP%\\p\\CONIN$','w').close()" && \\
       git -C %TEMP%\\p add -- "CONIN$"   # 預期 rc=128
     完整量測腳本形態見 tools/tests/test_ntfs_trailing_space_device_name.py 檔頭。
  涵蓋面（三段式）：**已實測涵蓋**＝上列各具名字面（CON/PRN/AUX/NUL/COM0~9/LPT0~9/
  CONIN$/CONOUT$/CONERR$/CONPRN$ ×〔裸名｜帶目錄前綴〕×〔無副檔名｜.txt｜尾隨空白
  +.txt〕）於本機 git 2.51.0.windows.1；**已實測不涵蓋**＝`CONERR$`／`CONPRN$`／`COM0`
  （git 接受，本閘仍擋 COM0，故較嚴）；**未窮舉**＝其他 git 版本的黑名單差異、
  `\\\\?\\` 長路徑前綴語法、非 NTFS 檔系（FAT32/exFAT/網路磁碟）行為。

已知侷限：大小寫折疊用 str.lower()（hook 的 grep -iFx 在 UTF-8 locale 亦
fold 非 ASCII 字母，方向一致）。檔名內嵌換行/控制字元非缺口：git 對含控制字元
路徑恆 C-quote（不受 core.quotepath=false 影響），hook 逐行讀所見之引號化表徵
含 " 與 \\ 觸發第 1 項攔截；本腳本 -z 讀原始路徑由控制字元檢查攔截——兩側皆
封閉（第五輪 SD/QA 雙實證）。`_tracked_files()` 對 `git ls-files` 輸出以
`errors="replace"` 解碼：tracked 路徑若真含非法 UTF-8 位元組序列，違規清單印出的
檔名會混入 U+FFFD 替代字元、人類辨識度打折，但偵測本身不受影響（違規仍會被列出、
exit 1 仍正確觸發，R25 複審確認）。

使用：
  python3 tools/check_ntfs_paths.py   # 於 repo 內任意 cwd；違規印明細並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_CHARS = set('<>:"|?*\\')
# R58 修正（DEF-101-B3）：補 `CONIN$`／`CONOUT$`。原清單只收
# `CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]`，是照「Win32 裝置名解析」推導出來的——而真正
# 拒絕的層是 Git for Windows，它的黑名單另含這兩個帶 `$` 的 console handle 名。實測
# （原生 Windows 11 + git 2.51.0.windows.1）：`CONIN$`／`CONOUT$` 檔案能在 NTFS 上
# 建立（os.path.isfile=True）但 `git add` rc=128（`open(...): No such file or directory`
# + `unable to index file`），該產物在 Windows 上永久無法提交。
# 刻意**不收** `CONERR$`：掃描員原提案把它與上兩者並列，經實測證偽——裸名
# `CONERR$` 是 FILE_TYPE_DISK（普通檔案、不是裝置），且 `git add` rc=0 並成功進 index。
# 收它等於無害名誤擋。詳見檔頭〈實測機制〉①③。
# `$` 在正則需轉義成 `\$`；`CON` 這個較短的替代分支不會搶先匹配 `CONIN$`——整個
# pattern 以 `$` 錨定結尾，`CON` 分支匹配後錨定失敗會回溯到後面的分支（已實測）。
_RESERVED_RE = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$)$")

# MAX_PATH 保守長度閘（DEF-101-039）：
# 可用 259（260 含 NUL）− 59（clone 前綴預留）＝ 200 fail；180 warn
_LEN_FAIL = 200
_LEN_WARN = 180


def _length_level(path: str) -> str | None:
    """路徑長度分級：>200 → "fail"、>180 → "warn"、其餘 → None（單位＝code point）。"""
    n = len(path)
    if n > _LEN_FAIL:
        return "fail"
    if n > _LEN_WARN:
        return "warn"
    return None


def _ntfs_seg_bad(path: str) -> str | None:
    """路徑在 Windows 上有相容性問題 → 回傳原因字串；乾淨 → None（對齊 hook 版同名函式）。

    R58 訂正（DEF-101-B13）：原文寫「NTFS 相容性問題」。函式名 `_ntfs_seg_bad` 因兩處
    實作對齊 + 既有測試以正則抽取而保留不改名，但**判準的真正依據是 Git for Windows
    的路徑合法性檢查**（`is_valid_win32_path()`／`mingw_open()`）與 Win32 的靜默改名
    行為，不是 NTFS 拒絕建檔——NTFS/Win32 對大多數這些檔名其實建得起來。詳見檔頭
    〈實測機制〉。
    """
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
        return "含控制字元"
    for seg in path.split("/"):
        bad = _FORBIDDEN_CHARS.intersection(seg)
        if bad:
            return f'路徑段「{seg}」含 Windows 不允許字元（< > : " | ? * \\）'
        if seg.endswith((" ", ".")):
            # R58 訂正（DEF-101-B13）：原訊息寫「NTFS 不允許」＝機制誤植。實測 Win32
            # **不拒絕**，而是靜默剝除改名（`'trail_space '` 落地成 `trail_space`）；
            # 真正拒絕的是 git（`update-index --cacheinfo` rc=128 `Invalid path`）。
            # 判準本身不變，只改述理由。詳見檔頭〈實測機制〉②。
            return f"路徑段「{seg}」以空白或句點結尾（Win32 會靜默剝除改名，git 拒絕入 index）"
        # R57 修正（DEF-101-B1）：base 需先剝除尾隨空白再比對保留名。原本
        # `seg.split(".", 1)[0]` 對 `CON .txt` 得到 `"CON "`，`^(CON|...)$` 不匹配
        # 而放行；上面「整段以空白/句點結尾」那條也不成立（結尾是 t）→ 完全逃逸。
        # R58 訂正（DEF-101-B13）：本處原寫「Win32 解析裝置名時會忽略基底名後的尾隨
        # 空白，故此形態在 Windows 上仍會撞到裝置名」——**實測證偽**：`<dir>\CON .txt`
        # 是 FILE_TYPE_DISK 的普通檔案，沒有撞到任何裝置。真正的危害在 git：
        # `git add "<dir>/CON .txt"` 實測 rc=128（Git for Windows 的
        # `is_valid_win32_path()` 在比對 DOS 裝置名前會忽略基底名後的尾隨空白/句點），
        # 檔案建得起來卻永遠進不了 index。攔截行為不變，只改述理由。
        # 剝除後 `" .txt"` 這類純空白 base 退化為空字串，`^(CON|...)$` 不匹配空字串，
        # 不會誤判。（僅剝空白：base 已在第一個點處切斷故不含句點；tab 等其他空白屬
        # 控制字元，已由本函式開頭的控制字元檢查攔下。）
        base = seg.split(".", 1)[0].rstrip(" ")  # 去（第一個點起的）副檔名；CON.txt 一樣是保留名
        if _RESERVED_RE.match(base.upper()):
            return f"路徑段「{seg}」為 Windows 保留裝置名（{base.upper()}）"
    return None


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def main() -> int:
    files = _tracked_files()
    violations: list[str] = []
    warnings: list[str] = []

    for f in files:
        reason = _ntfs_seg_bad(f)
        if reason:
            violations.append(f"NTFS 不相容檔名：{f} — {reason}")
        level = _length_level(f)
        if level == "fail":
            violations.append(
                f"路徑過長：{f}（{len(f)} > {_LEN_FAIL} 字元；"
                f"Windows MAX_PATH=260 扣除 clone 前綴預留後超限）"
            )
        elif level == "warn":
            warnings.append(f"路徑偏長：{f}（{len(f)} > {_LEN_WARN} 字元，>{_LEN_FAIL} 將擋下）")

    # 大小寫碰撞：全量 tracked 路徑 lowercase 分組，同組 >1 即互撞
    by_lower: dict[str, list[str]] = {}
    for f in files:
        by_lower.setdefault(f.lower(), []).append(f)
    for group in by_lower.values():
        if len(group) > 1:
            joined = "」「".join(sorted(group))
            violations.append(f"NTFS 大小寫碰撞：「{joined}」僅大小寫不同（checkout 互相覆蓋）")

    for w in warnings:
        print(f"⚠ {w}", file=sys.stderr)

    if violations:
        for v in violations:
            print(f"❌ {v}", file=sys.stderr)
        print(
            f"\n共 {len(violations)} 筆違規 — 修法：改名後重新提交"
            "（對齊 tools/git-hooks/pre-commit A3 閘）",
            file=sys.stderr,
        )
        return 1

    max_len = max((len(f) for f in files), default=0)
    print(
        f"✅ NTFS 檔名檢查通過（{len(files)} 個 tracked 路徑，0 違規；"
        f"最長 {max_len} 字元，warn>{_LEN_WARN}/fail>{_LEN_FAIL}）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
