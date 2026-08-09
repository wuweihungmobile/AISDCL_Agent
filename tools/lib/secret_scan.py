#!/usr/bin/env python3
"""機密外洩偵測的**唯一判準層**（R82；掌舵者紅線「`.env` 有私密 KEY，不要推上 GitHub」）。

🔴 立案理由：`.gitignore` 只有一層，而它擋不住下面三條**實際可走**的路——
  ① `git add -f AutoClaude/.env` —— 忽略規則對「已明示暫存」完全不生效；
  ② 有人把真 key 貼進**已被追蹤**的 `.env.example`（範本本來就該入庫，於是任何以
     「檔名」為判準的守衛對它結構上失明）；
  ③ 新開一棵子樹自帶 `.gitignore` 卻漏抄那三行。
本模組只負責 ②③ 的**內容判準**。① 是純路徑形態，由 `tools/git-hooks/pre-commit`
以零依賴的 bash 就地擋下——那一層刻意**不**依賴本模組，因為「python 能不能 import
成功」不該成為機密外洩防線的前提。

🔴 判準方向刻意是**寧可漏報也不要假報**（本 repo 判例：誤報比漏擋更糟——一道天天
假紅的守衛會被整個關掉，那才是真正的零防護）。三條具體收窄：
  · 佔位符一律放行（`your_..._here`／`<...>`／`changeme`／`mock`…）；
  · 高熵判準**只**套在「名字本身就是機密」的賦值上（`*_KEY`／`*_TOKEN`／`*_PASSWORD`…），
    不對整份檔案的長字串一視同仁——那會把 sha256／UUID／base64 資產整片判紅；
  · DSN 密碼只在**主機不是本機**時才算機密：`postgres://autoclaude:autoclaude@localhost`
    是本機 dev 容器的密碼，入庫是刻意的（見 `AutoClaude/.env.example`）。

行內豁免出口：**行尾**加 `# secret-scan-ok: <WHY>`（獨立註解行無效——同 repo 既有
`# ps-lint-ok:`／`# platform-ok:` 體例，掃描器只認行尾）。存在理由是本檔與其回歸鎖
自己就必須寫出合成樣本，沒有出口的話判準無法自證。

CLI：
    python tools/lib/secret_scan.py --staged     # 暫存區 blob（pre-commit 用）
    python tools/lib/secret_scan.py --tracked    # 全 tracked 檔（普查／量假紅用）
    python tools/lib/secret_scan.py --paths a b  # 指定檔（工作樹）
rc: 0＝乾淨、1＝有命中、2＝取數管道壞掉（「無法驗證」與「驗證通過」不是同一件事）。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

#: 行尾豁免標記（同 repo 既有體例：只認行尾，獨立註解行無效）。
EXEMPT_MARKER = "secret-scan-ok:"

#: 值裡出現任一即視為佔位符 → 放行。刻意**不**收 `test`／`key` 這種太常見的字：
#: 它們會把真 key 的一大類（含 `test` 字樣的環境憑證）一起放行，而放行是不可逆的方向。
_PLACEHOLDER_TOKENS: tuple[str, ...] = (
    "your_", "your-", "_here", "-here", "changeme", "change_me", "change-me",
    "placeholder", "example", "sample", "dummy", "mock", "fake", "redacted",
    "xxxx", "...", "<", ">", "${", "$(", "todo", "n/a", "notset", "unset",
    "replace_me", "replace-me", "fill_in", "fill-in",
)

#: 被視為「本機」的 DSN 主機。裸主機名（不含 `.`）一併視為本機——那幾乎必然是
#: docker-compose 服務名（`db`／`postgres`／`redis`），不是會外洩的 production 端點。
_LOCAL_HOSTS: frozenset[str] = frozenset(
    {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}
)

#: 已知供應商的憑證前綴。這一族**零假陽性風險**（前綴＋長度都是供應商規定的形狀），
#: 故全檔生效（不像下方 `_SECRET_ASSIGN_RE` 只在 `.env` 形態的檔上生效）。
_VENDOR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai/minimax 形態 key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
)

#: PEM 私鑰：**標頭不等於私鑰**。判準要求標頭之後鄰近幾行真的有 key material，
#: 否則 `-----BEGIN PRIVATE KEY-----` 這種寫在安全基線**模板**裡的示意字串會被判紅
#: （落地當回合實測：這一條在 30 個凍結版本樹裡各命中一次，全是模板示意）。
_PEM_HEADER_RE = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")
_PEM_BODY_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
#: 標頭之後往下看幾行找 key material。PEM 標頭與內文之間至多隔一行空白。
_PEM_LOOKAHEAD = 3

#: 帶密碼的連線字串。`user:pass@host` 三段齊全才算——只有 `scheme://host` 不算機密。
_DSN_RE = re.compile(
    r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.\-]*)://"
    r"(?P<user>[^:/\s@]+):(?P<pw>[^@/\s]+)@(?P<host>[^/\s:?#]+)"
)

#: 「名字本身就是機密」的賦值。高熵判準只在這個面上生效（見檔頭第二條收窄）。
_SECRET_ASSIGN_RE = re.compile(
    r"(?P<name>[A-Za-z0-9_.\-]*"
    r"(?:API[_\-]?KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|PRIVATE[_\-]?KEY"
    r"|ACCESS[_\-]?KEY|AUTH[_\-]?KEY)"
    r"[A-Za-z0-9_.\-]*)\s*[:=]\s*(?P<value>\S.*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    """一筆命中。

    🔴 `excerpt` **一律是遮蔽過的**（`mask()`）：這道守衛的失敗會被寫進 hook 輸出、
    CI log 與終端 scrollback，若診斷訊息逐字印出命中的字串，守衛自己就成了第二個
    外洩管道——而且是使用者最不會察覺的那一個（他以為自己被保護了）。故只留可辨識
    的前綴與長度，足以讓人找到那一行，不足以讓人重建那把 key。
    """

    path: str
    lineno: int
    rule: str
    excerpt: str

    def render(self) -> str:
        return f"{self.path}:{self.lineno}: [{self.rule}] {self.excerpt}"


def mask(secret: str, keep: int = 4) -> str:
    """`sk-abcd…（共 51 字元）`——留得下線索，重建不了憑證。"""
    head = secret[:keep]
    return f"{head}…（共 {len(secret)} 字元）"


def _clean_value(raw: str) -> str:
    """剝掉引號與行尾註解，取出真正的值。

    `KEY=abc  # 說明` 的註解若不剝掉，會讓值長度虛胖而誤觸長度門檻；反之
    `KEY="abc"` 的引號不剝掉則會讓佔位符比對錯過。兩個方向都會讓判準失準。
    """
    value = raw.strip()
    value = re.sub(r"\s+#.*$", "", value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.strip()


def is_placeholder(value: str) -> bool:
    """佔位符 → 放行。空值也算（`KEY=` 是「還沒填」，不是機密）。"""
    low = value.strip().lower()
    if not low:
        return True
    return any(token in low for token in _PLACEHOLDER_TOKENS)


def looks_like_credential(value: str) -> bool:
    """值的形狀像不像一把真憑證。**只**被 `_SECRET_ASSIGN_RE` 那個面呼叫。

    三條各自獨立的形狀（任一成立即算），刻意都帶長度下限——短值幾乎必然是
    `autoclaude` 這種本機 dev 密碼或列舉常數，判紅只會製造要逐一辯護的假紅。
    """
    if len(value) < 16 or re.search(r"\s", value):
        return False
    if re.fullmatch(r"[0-9a-fA-F]{32,}", value):
        return True  # 長 hex（token／hash 形態）
    if (
        len(value) >= 24
        and re.fullmatch(r"[A-Za-z0-9+/=_\-]{24,}", value)
        and re.search(r"[0-9]", value)
        and re.search(r"[A-Za-z]", value)
    ):
        return True  # base64／隨機串
    classes = sum(
        bool(re.search(pattern, value))
        for pattern in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]")
    )
    return classes >= 3


def is_env_shaped(path: str) -> bool:
    """這個路徑是不是 `.env` 形態的設定檔。

    🔴 這支函式決定「高熵賦值」判準的射程，而**射程就是這道守衛能不能活下來**。
    落地當回合的實測：把 `NAME=<高熵值>` 判準套在全 repo 27,541 支檔上得到
    **1,525 筆**命中，其中壓倒性多數是**文件裡的範例程式碼**（`password=`／
    `token=`／`apiKey=` 出現在 Markdown 的 code block 裡），再被 30 個凍結版本樹
    各複製一份放大。那種守衛第一天就會被整個關掉，而被關掉的守衛＝零防護。
    ⇒ 高熵判準只在真正承載憑證的檔案形態上生效；跨檔的那一族改由零假陽性的
    供應商前綴（`_VENDOR_PATTERNS`）與非本機 DSN 負責，那兩條全檔生效。
    """
    name = PurePosixPath(path.replace("\\", "/")).name
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def scan_line(line: str, *, env_shaped: bool = False) -> list[tuple[str, str]]:
    """單行判準，回傳 `[(rule, excerpt), ...]`。純函式——供測試直接餵合成語料。

    `env_shaped` 為真時才加掛「機密名賦值帶高熵值」那一條（射程理由見
    `is_env_shaped`）。預設 False＝保守：呼叫端沒表態就只跑零假陽性的那幾條。
    """
    if EXEMPT_MARKER in line:
        return []
    hits: list[tuple[str, str]] = []

    for rule, pattern in _VENDOR_PATTERNS:
        match = pattern.search(line)
        if match and not is_placeholder(match.group(0)):
            hits.append((rule, mask(match.group(0))))

    for match in _DSN_RE.finditer(line):
        host = match.group("host").lower()
        # 主機也要吃佔位符判準：`postgres://u:p@${container.getHost()}` 是文件裡的
        # 範例插值，不是端點（落地當回合實測命中，屬假紅）。
        if host in _LOCAL_HOSTS or "." not in host or is_placeholder(host):
            continue  # 本機／docker 服務名／插值 → 不是會外洩的 production 憑證
        if is_placeholder(match.group("pw")):
            continue
        hits.append((
            "帶密碼的非本機 DSN",
            f"{match.group('scheme')}://{match.group('user')}:***@{host}",
        ))

    if env_shaped:
        match = _SECRET_ASSIGN_RE.search(line)
        if match:
            value = _clean_value(match.group("value"))
            if not is_placeholder(value) and looks_like_credential(value):
                hits.append(
                    ("機密名賦值帶高熵值", f"{match.group('name')}=<{len(value)} 字元>")
                )

    return hits


def _pem_findings(lines: list[str], path: str) -> list[Finding]:
    """PEM 私鑰：標頭 ＋ 鄰近幾行內真的有 key material 才算（見 `_PEM_HEADER_RE`）。"""
    findings: list[Finding] = []
    for index, line in enumerate(lines):
        if EXEMPT_MARKER in line or not _PEM_HEADER_RE.search(line):
            continue
        window = lines[index:index + 1 + _PEM_LOOKAHEAD]
        body = "\n".join(window)[len(line.split("-----")[0]):]
        if _PEM_BODY_RE.search(body):
            findings.append(Finding(path, index + 1, "PEM 私鑰", "私鑰內文（已遮蔽）"))
    return findings


def scan_text(text: str, path: str) -> list[Finding]:
    """整份文字的判準。行號自 1 起算，與編輯器一致。"""
    env_shaped = is_env_shaped(path)
    lines = text.splitlines()
    findings: list[Finding] = []
    for lineno, line in enumerate(lines, start=1):
        findings.extend(
            Finding(path, lineno, rule, excerpt)
            for rule, excerpt in scan_line(line, env_shaped=env_shaped)
        )
    findings.extend(_pem_findings(lines, path))
    return findings


# ── 取數層（git）────────────────────────────────────────────────────────────
# 一律帶 `-c core.quotepath=false`：非 ASCII 路徑預設會被 C-quoted 成
# `"a/\346\211\213..."`，那種 key 拿去開檔一律失敗 ⇒ 檔案**靜默掉出掃描面**，
# 而縮面的表徵是「看起來更乾淨」。同 tools/lib/git_paths.py 的立案理由。
_QUOTEPATH_OFF = ("-c", "core.quotepath=false")

#: 二進位／過大檔不進掃描面。1 MiB 以上的文字檔在本 repo 不存在憑證形態的內容，
#: 而逐行 regex 掃大檔會讓 pre-commit 慢到有人想繞過它。
_MAX_BYTES = 1024 * 1024


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *_QUOTEPATH_OFF, *args],
        capture_output=True,
        timeout=300,
    )


def _decode_content(raw: bytes) -> str | None:
    """檔案**內容**的解碼。解不開＝二進位；過大＝不進掃描面（見 `_MAX_BYTES`）。"""
    if len(raw) > _MAX_BYTES or b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _decode_listing(raw: bytes) -> str:
    """git **路徑清單**的解碼。

    🔴 這支函式與 `_decode_content` 分家，是因為兩者合用一支時踩到過一個會靜默
    歸零的缺陷（R82 落地當回合實測，本判準自己的第一版）：清單套用了內容那條
    `_MAX_BYTES` 上限，而本 repo 的 `git ls-files` 輸出是 27,566 條路徑、遠超
    1 MiB ⇒ 清單被判成「二進位」而回 None，掃描面塌成空集合、`--tracked` 回
    **rc=0 全綠**。失效方向正是本 repo 反覆記載的那一種：**縮面的表徵是「看起來
    更乾淨」**，沒有任何東西會轉紅。清單不設上限、且以 `replace` 解碼（寧可讓一
    條路徑變成問號，也不要整批消失）。
    """
    return raw.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class ScanResult:
    """`listed`／`scanned` 是**反空轉憑證**，不是統計裝飾。

    見 `_decode_listing` 記載的那個缺陷：掃描面塌成空集合時，命中數 0 與「真的乾淨」
    的 rc 完全相同。呼叫端（CLI 與回歸鎖）一律要拿 `scanned` 去證明「這次真的有掃到
    東西」，否則綠燈沒有鑑別力。
    """

    findings: list[Finding]
    error: str | None
    listed: int = 0
    scanned: int = 0


def scan_staged(repo_root: Path) -> ScanResult:
    """掃暫存區 blob（不是工作樹檔案）。

    🔴 為何看 blob：決定「GitHub 上會出現什麼」的是入庫內容。工作樹已改回佔位符、
    暫存區仍是真 key，是一個真實可達的狀態，而看工作樹的守衛對它完全失明。
    `error` 非 None＝取數管道壞掉，呼叫端須 fail-loud（「無法驗證」≠「驗證通過」）。
    """
    listing = _git(
        repo_root, "diff", "--cached", "--name-only", "--no-renames", "--diff-filter=ACM"
    )
    if listing.returncode != 0:
        return ScanResult([], "git diff --cached 失敗（無法取得暫存清單）")
    rels = [r for r in _decode_listing(listing.stdout).splitlines() if r]
    findings: list[Finding] = []
    scanned = 0
    for rel in rels:
        blob = _git(repo_root, "show", f":{rel}")
        if blob.returncode != 0:
            return ScanResult([], f"git show :{rel} 失敗（無法讀取暫存區內容）")
        text = _decode_content(blob.stdout)
        if text is not None:
            scanned += 1
            findings.extend(scan_text(text, rel))
    return ScanResult(findings, None, len(rels), scanned)


def scan_tracked(repo_root: Path, *pathspec: str) -> ScanResult:
    """掃全部（或指定 pathspec 的）tracked 檔的**工作樹**內容。"""
    args = ["ls-files", "--", *pathspec] if pathspec else ["ls-files"]
    listing = _git(repo_root, *args)
    if listing.returncode != 0:
        return ScanResult([], "git ls-files 失敗（無法取得 tracked 清單）")
    rels = [r for r in _decode_listing(listing.stdout).splitlines() if r]
    findings: list[Finding] = []
    scanned = 0
    for rel in rels:
        try:
            raw = (repo_root / rel).read_bytes()
        except OSError:
            continue  # 已刪除／不可讀：由其他閘門管，不是本判準的射程
        text = _decode_content(raw)
        if text is not None:
            scanned += 1
            findings.extend(scan_text(text, rel))
    return ScanResult(findings, None, len(rels), scanned)


def main(argv: list[str] | None = None) -> int:
    # 🔴 入口點必須先把 stdio 掰成 UTF-8：本函式的診斷訊息全是中文，而 Windows 主控台
    # 預設是 CP950／非 CJK 機器上是 cp1252——`sys.stderr` 的預設 errors 會讓訊息降解，
    # 而這道守衛的**訊息就是它的產出**（使用者要照著訊息去修）。同 DEF-101-798 那一族。
    #
    # 🔴 取不到就**靜默不動**，絕不讓它把行程弄掛（落地當回合被自己的回歸鎖抓到）：
    #   初版是裸 import，於是 `platform_utils` 不在 sys.path 時（本模組被單獨複製出去用、
    #   或呼叫端只搬了這一支檔）整支掃描器 `ModuleNotFoundError` 收場 ⇒ rc=1 ⇒ **pre-commit
    #   把「掃描器自己崩了」讀成「發現機密」而擋下每一次 commit**。守衛因為保護件缺席
    #   而全面誤擋，是最糟的失敗模式；`platform_utils.init_utf8_streams` 自己的 docstring
    #   也正是這麼寫的（保護件不該把行程弄掛）。
    try:
        from platform_utils import init_utf8_streams  # noqa: PLC0415

        init_utf8_streams()
    except Exception:  # noqa: BLE001 — 保護性前置，任何失敗都不得影響判準本身
        pass
    parser = argparse.ArgumentParser(description="機密外洩內容掃描（R82）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="掃暫存區 blob")
    group.add_argument("--tracked", action="store_true", help="掃全部 tracked 檔")
    group.add_argument("--paths", nargs="+", metavar="PATH", help="掃指定檔（工作樹）")
    parser.add_argument("--repo-root", default=None, help="repo 根（預設由 git 推導）")
    args = parser.parse_args(argv)

    if args.repo_root:
        repo_root = Path(args.repo_root)
    else:
        repo_root = Path(__file__).resolve().parents[2]

    if args.paths:
        findings = []
        scanned = 0
        for raw_path in args.paths:
            path = Path(raw_path)
            text = _decode_content(path.read_bytes()) if path.is_file() else None
            if text is not None:
                scanned += 1
                findings.extend(scan_text(text, raw_path))
        result = ScanResult(findings, None, len(args.paths), scanned)
    elif args.staged:
        result = scan_staged(repo_root)
    else:
        result = scan_tracked(repo_root)
    findings = result.findings

    if result.error:
        print(f"[secret-scan] ❌ {result.error} → 無法驗證，視同不通過", file=sys.stderr)
        return 2
    # 反空轉：清單有東西、卻一個檔都沒進掃描面 ⇒ 取數／解碼層壞了，不是「乾淨」。
    # 這一條是本判準第一版真的踩過的洞（見 `_decode_listing`），故做成 rc 而非註解。
    if result.listed and not result.scanned:
        print(
            f"[secret-scan] ❌ 清單有 {result.listed} 條路徑、卻 0 個檔進到掃描面 "
            "⇒ 掃描面已塌陷（不是「乾淨」）",
            file=sys.stderr,
        )
        return 2
    for finding in findings:
        print(f"[secret-scan] ❌ {finding.render()}", file=sys.stderr)
    if findings:
        print(
            f"[secret-scan] 共 {len(findings)} 筆疑似機密。修法：換成佔位符"
            "（`your_xxx_here`）並把真值移到 .env（已被 .gitignore 排除）；"
            f"確定是誤判時於**行尾**加 `# {EXEMPT_MARKER} <理由>`",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
