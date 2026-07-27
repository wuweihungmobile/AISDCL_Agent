#!/usr/bin/env python3
"""重生 `tools/tests/ps_comment_golden.json`：真 PowerShell parser 對全語料的 Comment token。

## 這支工具存在的理由（R58 落地，取代 R57 定案的 whack-a-mole）

`tools/tests/_ps_source.py::strip_ps_comments()` 用「前導字元白名單」近似判斷 `#` 是否為
PowerShell 註解。R57 以真 parser 差分量測出該近似法 **FAIL_OPEN=27/64**（其中 20 案是完全
合法的日常寫法如 `$a = 1#c`），方向是 fail-open（註解冒充功能碼 → 「錨點只認功能碼」的靜態鎖
假綠）。R57 已定案「**切勿再往集合裡補字元**，那是 whack-a-mole」，並指定正解為：把真 parser
對全語料的 Comment token 凍結成 golden fixture 做離線差分。本工具即該 golden 的產生器。

## 為什麼 ground truth 可以離線化（CI 不裝 PowerShell 也能守）

「這個 `#` 是不是註解」是**檔案文字的純函式**——同一份 bytes 餵進同一個 parser 永遠得到同一組
span。故只需在**有** PowerShell 的機器上產生一次、連同每檔 sha256 凍結，之後任何平台（含
ubuntu CI runner）都能離線比對。新鮮度由 sha256 fail-closed 守：`.ps1` 改了而 golden 未重生
即翻紅（見 `tools/tests/test_ps_comment_golden.py`）。

## 引擎選擇：為何在 Windows 上優先用出廠的 powershell.exe 而非 pwsh 7

這些 `.ps1` 的**目標執行環境**是使用者的 Windows PowerShell 5.1（repo 另有
`tools/tests/test_ps51_compat.py` 機械保證 5.1 可解析），且 5.1 是 Windows 出廠即有、pwsh 7
需另外安裝（本 repo R58 動工的真 Windows 11 Pro 實測即 `pwsh` NOT FOUND）。ground truth 取自
目標執行環境的 tokenizer 才是對的參照系。macOS/Linux 開發機只有 `pwsh`，故退而用它，並把實際
使用的引擎身分寫進 golden 的 `engine` 欄——**跨引擎量測數字不可互相比較**（R57 於 pwsh 7.6.3
計得 2,847 個 token；R58 於 5.1 計得的數字**刻意不寫死在此**，唯一真相源是 `ps_comment_golden.json`
本身〔`len(files)` 與各檔 `commentSpans` 總數〕。兩者之間同時存在「引擎差異」與「語料在兩輪之間
有變動」兩個變因，本輪無 pwsh 可用故**不歸因**，只誠實記載。R58 round 2 SD-R58R2-01 訂正：
本處原寫死 2,880，那是落地前中間版語料的值，落地後已不符）。

上述判準的**實作**不在本檔，一律委派給 SSOT `tools/tests/_platform_helpers.powershell_exe()`
（ARCH-R58R1-03：本檔原本自帶一份逐字複製的 order tuple，且找不到時 `raise` 而非回 None，
SSOT 立起來的同一輪內就 fork 成三份。判準只有一個出處、才不會下一輪各自漂移）。
本檔的差異需求（重生 golden 沒有 PowerShell 就不能繼續）由呼叫端自己 `raise`，不是靠複製實作。
呼叫端鎖見 `tools/tests/test_platform_guard_availability.py::PowerShellExeSsotCallsiteLock`。

## 用法

    python tools/gen_ps_comment_golden.py            # 重生 golden（覆寫）
    python tools/gen_ps_comment_golden.py --check     # 只檢查是否需要重生，不寫檔（rc=1 表示需要）

`--check` 供 CI／pre-push 使用：它做的是「拿現有 golden 與現況 sha 比對」，**不需要 PowerShell**。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

sys.path.insert(0, str(_REPO_ROOT / "tools" / "tests"))
from _platform_helpers import powershell_exe  # noqa: E402
from _ps_source import (  # noqa: E402
    GOLDEN_PATH,
    GOLDEN_SCHEMA_VERSION,
    normalize_ps_source,
)

# PowerShell 側取 token 的腳本。**刻意全 ASCII、且只輸出純數字**：
#   * 全 ASCII → 不受「含非 ASCII 的 .ps1 必須帶 BOM」政策與 CP950 誤讀影響，也不必為這支
#     臨時檔處理 BOM。
#   * 只輸出數字 → R58 實測踩到：PS 5.1 把非 ASCII 文字寫到 stdout 管線會按 console 輸出
#     codepage 轉碼而變成亂碼（本機 ACP=950）。故註解文字一律不經過 stdout，由 Python 端
#     自己用 offset 切片取得。
_PS_EMITTER = r"""
param([string]$ListFile, [string]$RepoRoot)
$ErrorActionPreference = 'Stop'
$paths = Get-Content -LiteralPath $ListFile -Encoding UTF8
$i = -1
foreach ($rel in $paths) {
  if ([string]::IsNullOrWhiteSpace($rel)) { continue }
  $i++
  $full = Join-Path $RepoRoot $rel
  # ReadAllText(path, UTF8) uses a StreamReader with BOM detection, so a leading BOM is
  # skipped -- matching Python's utf-8-sig decode. CRLF -> LF matches the Python side too.
  $text = ([System.IO.File]::ReadAllText($full, [System.Text.Encoding]::UTF8)) -replace "`r`n", "`n"
  $tokens = $null; $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseInput($text, [ref]$tokens, [ref]$errors)
  # F <index> <parseErrorCount> <utf16Length>
  Write-Output ("F`t{0}`t{1}`t{2}" -f $i, $errors.Count, $text.Length)
  foreach ($t in $tokens) {
    if ($t.Kind -eq 'Comment') {
      # C <index> <utf16StartOffset> <utf16EndOffset>
      Write-Output ("C`t{0}`t{1}`t{2}" -f $i, $t.Extent.StartOffset, $t.Extent.EndOffset)
    }
  }
}
Write-Output ("V`t{0}`t{1}" -f $PSVersionTable.PSVersion, $PSVersionTable.PSEdition)
"""


def tracked_ps1() -> list[str]:
    """全 repo git-tracked `.ps1` 相對路徑（排序後）。

    **刻意不排除 AISDLC_SDD 凍結版本目錄**：遵 R44/R45/R46 教訓——凍結版依 Copy-on-Evolve
    紀律不回改，但那是「不改」不是「不看」，把它們排除出掃描面等於讓 30 個版本目錄成為
    守門盲區（R44 那次的 P0 例外正是這樣長出來的）。

    **刻意 tracked-only、不走 `tools/tests/_repo_scan.scanned()`（R58 round 3 ARCH-R58R3-01
    要求記載的理由）**：`ps_comment_golden.json` 是**被提交、由所有人共用**的產物。若掃描面
    納入本機未追蹤的 `.ps1`，那些條目會被烤進共用產物，別人 checkout 後新鮮度檢查會報
    「golden 仍登記已不存在／已不 tracked 的檔案」而**集體翻紅**——把機器本地狀態污染進共用
    工件。且產生器與驗證器兩側必須用**同一個**掃描面，否則 `--check` 恆不一致。
    """
    out = subprocess.run(
        ["git", "ls-files", "*.ps1"],
        cwd=_REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return sorted(ln.strip() for ln in out.splitlines() if ln.strip())


def utf16_to_codepoint(text: str) -> list[int]:
    """建 UTF-16 code unit offset → code point index 的映射（長度 = utf16 單位數 + 1）。

    🔴 這支函式是本工具最容易被誤刪的一段，刪掉會**靜默**產生錯位的 golden：.NET 的
    `Extent.StartOffset` 以 UTF-16 code unit 計，Python 字串索引以 code point 計。本 repo 的
    `.ps1` 內含星體平面 emoji（🔴 U+1F534 等，.NET 算 2 單位、Python 算 1）。R58 實測不做轉換
    的後果：137 支中 62 支長度不符、逾半數 span 切出來不是以 `#`／`<#` 開頭（該量測取自落地前
    中間版語料，僅證明現象存在；span 總數不在此寫死，唯一真相源是 `ps_comment_golden.json`）。
    代理對的第二個單位映射到同一個 code point（span 邊界不會落在代理對中間，PowerShell 的
    token 邊界必為字元邊界）。
    """
    mapping: list[int] = []
    for i, ch in enumerate(text):
        mapping.append(i)
        if ord(ch) > 0xFFFF:
            mapping.append(i)
    mapping.append(len(text))
    return mapping


def collect_spans(rels: list[str]) -> tuple[dict[str, dict], str]:
    """呼叫真 parser 取每檔 comment span（已轉成 code point offset）與 parse error 數。"""
    # 引擎選擇一律走 SSOT（見模組 docstring〈引擎選擇〉）；本檔的差異只是「沒有就不能繼續」，
    # 故在呼叫端把 None 轉成 RuntimeError，而不是為此再抄一份選擇邏輯。
    exe = powershell_exe()
    if exe is None:
        raise RuntimeError(
            "找不到 powershell 或 pwsh——重生 golden 需要真 PowerShell parser 取 ground truth。"
            "Windows 出廠即有 powershell.exe；macOS/Linux 請安裝 pwsh。"
            "（注意：**驗證** golden 不需要 PowerShell，只有重生需要）"
        )
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        list_file = tmpdir / "ps1_list.txt"
        list_file.write_text("\n".join(rels), encoding="utf-8")
        emitter = tmpdir / "emit_spans.ps1"
        emitter.write_text(_PS_EMITTER, encoding="ascii")
        proc = subprocess.run(
            [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(emitter),
             "-ListFile", str(list_file), "-RepoRoot", str(_REPO_ROOT)],
            capture_output=True, text=True, encoding="ascii", errors="replace", check=True,
        )

    raw_spans: dict[int, list[tuple[int, int]]] = {}
    meta: dict[int, tuple[int, int]] = {}
    engine = "unknown"
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if parts[0] == "F":
            meta[int(parts[1])] = (int(parts[2]), int(parts[3]))
        elif parts[0] == "C":
            raw_spans.setdefault(int(parts[1]), []).append((int(parts[2]), int(parts[3])))
        elif parts[0] == "V":
            engine = f"{parts[2]} {parts[1]}"  # 例：Desktop 5.1.26100.8875

    if len(meta) != len(rels):
        raise RuntimeError(
            f"PowerShell 只回報 {len(meta)} 檔、清單有 {len(rels)} 檔——輸出被截斷或有檔案讀取失敗，"
            "不得產生不完整的 golden（那會讓差分保護對缺席的檔案靜默失效）"
        )

    files: dict[str, dict] = {}
    for idx, rel in enumerate(rels):
        text = normalize_ps_source((_REPO_ROOT / rel).read_bytes())
        parse_errors, ps_utf16_len = meta[idx]
        py_utf16_len = len(text.encode("utf-16-le")) // 2
        if py_utf16_len != ps_utf16_len:
            raise RuntimeError(
                f"{rel}：Python 正規化後 UTF-16 長度 {py_utf16_len} != PowerShell 讀到的 "
                f"{ps_utf16_len}——兩側正規化契約已分歧（見 _ps_source.normalize_ps_source），"
                "此時任何 offset 都不可信，拒絕產生 golden"
            )
        mapping = utf16_to_codepoint(text)
        spans: list[list[int]] = []
        for start, end in sorted(raw_spans.get(idx, [])):
            cp_start, cp_end = mapping[start], mapping[end]
            fragment = text[cp_start:cp_end]
            if not fragment.startswith(("#", "<#")):
                raise RuntimeError(
                    f"{rel}：span [{cp_start}:{cp_end}] 切出來的不是註解（{fragment[:40]!r}）"
                    "——offset 換算已失效，拒絕產生 golden"
                )
            spans.append([cp_start, cp_end])
        files[rel] = {
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "parseErrors": parse_errors,
            "commentSpans": spans,
        }
    return files, engine


def build_golden() -> dict:
    rels = tracked_ps1()
    files, engine = collect_spans(rels)
    return {
        "schemaVersion": GOLDEN_SCHEMA_VERSION,
        "engine": engine,
        "offsetUnit": "codepoint",
        "normalization": "utf-8-sig decode + CRLF->LF (see _ps_source.normalize_ps_source)",
        "files": files,
    }


def _dump(golden: dict) -> str:
    """穩定序列化：**每支 .ps1 恰佔一行**，同一份輸入 → 同一份位元組。

    刻意手工組裝而非直接 `json.dumps(indent=…)`：純 indent 會讓每個 offset 各佔一行
    （數千個 span → 上萬行、逾 130KB；實際數量見 `ps_comment_golden.json`，刻意不在此寫死——R58 round 3 SD-R58R3-01 抓到本處為該輪「數字只准住一個家」修法的殘留），任何一支 `.ps1` 的小改動都會產生巨大且無法閱讀的
    diff。每檔一行的形狀讓 diff 粒度恰好等於「哪一支 `.ps1` 的註解結構變了」，覆核者一眼
    可見。手工組裝的正確性由 `test_ps_comment_golden.py::TestGoldenSerializationIsStable`
    釘住（斷言 `json.loads(_dump(x)) == x` 且再 dump 一次位元組相同）。
    """
    head = {k: v for k, v in golden.items() if k != "files"}
    lines = ["{"]
    for key in sorted(head):
        lines.append(f" {json.dumps(key)}: {json.dumps(head[key], ensure_ascii=False)},")
    lines.append(' "files": {')
    rels = sorted(golden["files"])
    for i, rel in enumerate(rels):
        entry = json.dumps(
            golden["files"][rel], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        comma = "" if i == len(rels) - 1 else ","
        lines.append(f"  {json.dumps(rel)}: {entry}{comma}")
    lines.append(" }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def check_only() -> int:
    """不需要 PowerShell：比對現有 golden 的 sha 與檔案清單是否仍與工作樹一致。"""
    if not GOLDEN_PATH.is_file():
        print(f"❌ golden 不存在：{GOLDEN_PATH}", file=sys.stderr)
        return 1
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    recorded = golden.get("files", {})
    rels = tracked_ps1()
    problems: list[str] = []
    for rel in rels:
        entry = recorded.get(rel)
        if entry is None:
            problems.append(f"新增的 .ps1 未登記於 golden：{rel}")
            continue
        actual = hashlib.sha256(
            normalize_ps_source((_REPO_ROOT / rel).read_bytes()).encode("utf-8")
        ).hexdigest()
        if actual != entry.get("sha256"):
            problems.append(f"內容已變動但 golden 未重生：{rel}")
    for rel in sorted(set(recorded) - set(rels)):
        problems.append(f"golden 仍登記已不存在／已不 tracked 的檔案：{rel}")
    if problems:
        print(f"❌ golden 已過期（{len(problems)} 項）——請跑 "
              "`python tools/gen_ps_comment_golden.py` 重生：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"✅ golden 新鮮：{len(rels)} 支 .ps1 的 sha256 全數相符")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                       help="只檢查新鮮度（不需要 PowerShell），過期則 rc=1")
    args = parser.parse_args()
    if args.check:
        return check_only()

    golden = build_golden()
    GOLDEN_PATH.write_text(_dump(golden), encoding="utf-8")
    total_spans = sum(len(v["commentSpans"]) for v in golden["files"].values())
    bad_parse = [k for k, v in golden["files"].items() if v["parseErrors"]]
    print(f"✅ 已重生 {GOLDEN_PATH.relative_to(_REPO_ROOT)}："
          f"{len(golden['files'])} 支 .ps1、{total_spans} 個 Comment token、"
          f"引擎 {golden['engine']}")
    if bad_parse:
        print(f"⚠️  {len(bad_parse)} 支 .ps1 有 parse error（已記入 golden，差分測試會翻紅）："
              f"{bad_parse}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
