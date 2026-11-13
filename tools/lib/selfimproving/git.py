"""SelfImproving `check` 唯一的子行程出口：環境被淨化的 `git`（TCS-SelfImproving-P0 R8 (c)）。

每個呼叫一律 `subprocess.run`、`shell` 不為真、argv 以 `git -C <repo>` 起頭、帶 timeout
與 UTF-8 解碼；列舉路徑的呼叫另帶 `-c core.quotepath=false`。git 不可用（找不到執行檔、
不是工作樹、逾時）一律回 None／False，由呼叫端判成 blocking NE，不以預設值頂替。
console-free：SessionStart 簡報（`session_brief.si_status_line`）在 pythonw 載具下呼叫本類，
spawn 不帶 `CREATE_NO_WINDOW` 時 Windows 每次開視窗都閃一個黑框；POSIX 上該常數不存在、取 0。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

_TIMEOUT = 60
_VALUE_CHARS = re.compile(r"[A-Za-z0-9+/_.=\-]{12,}")
# 值＝連續的非空白、非引號、非 `,;)}]` 字元；鍵後允許閉合引號（JSON 形）、值前允許開頭引號（E-42）
_KV = (r"(?i)\b([A-Z0-9_]*(?:token|password|passwd|secret|key|(?<![a-z])pat(?![a-z]))[A-Z0-9_]*)"
       r"([\"']?\s*[=:]\s*[\"']?)([^\s\"',;)}\]]+)")
#: 程式碼形的值：不遮罩、不掃描（型別標註、null、讀環境變數）
_CODE_FORM = re.compile(r"(?i)^(?:null|none|str|int|bool|true|false|optional\[.*|os\.environ.*"
                        r"|os\.getenv.*|getenv.*)$")


def _kv_hit(m: re.Match) -> bool:
    value = m.group(3)
    return not _CODE_FORM.match(value) and bool(_VALUE_CHARS.fullmatch(value))


def _kv_mask(m: re.Match, mark: str) -> str:
    if _CODE_FORM.match(m.group(3)):
        return m.group(0)
    return f"{m.group(1)}{m.group(2)}{mark}"


def _auth_hit(m: re.Match) -> bool:
    return len(m.group(2)) >= 12


#: 機密樣式表（TCS-P7 附錄 A.8；**全套件唯一定義**，封閉九式，`pushguard.SECRET_PATTERNS` 為其
#: 別名）：（樣式名, 比對式, 遮罩函式 `(match, mark)→str`, 掃描時要再過的條件或 None＝命中即算）。
SECRET_PATTERNS = (
    ("key-value", re.compile(_KV), _kv_mask, _kv_hit),
    ("bearer", re.compile(r"(?i)\b(Bearer\s+)([^\s\"',;)}\]]+)"),
     lambda m, k: m.group(1) + k, lambda m: len(m.group(2)) >= 20),
    ("basic", re.compile(r"\b(Basic\s+)((?=[A-Za-z0-9+/]*[0-9+/])[A-Za-z0-9+/]{12,}={0,2})"),
     lambda m, k: m.group(1) + k, lambda m: False),  # 僅遮罩、不掃描（避免把散文判成機密）
    ("auth-header", re.compile(r"(?i)\bAuthorization:\s*(\S+)\s+(\S+)"),
     lambda m, k: f"Authorization: {m.group(1)} {k}", _auth_hit),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
     lambda m, k: k, None),
    ("sk-token", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), lambda m, k: k, None),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), lambda m, k: k, None),
    ("private-key", re.compile(r"-----BEGIN[^\r\n]*PRIVATE KEY-----"), lambda m, k: k, None),
    ("url-userinfo", re.compile(r"://[^/\s]*@"), lambda m, k: f"://{k}@", None),
)


def _decoded(text: str) -> str:
    """`%xx` 解碼（只解 ASCII 位元組，不 import 網路模組）；非法序列原樣保留。"""
    if "%" not in text:
        return text
    return re.sub(r"(?:%[0-9A-Fa-f]{2})+",
                  lambda m: bytes.fromhex(m.group().replace("%", "")).decode("utf-8", "replace"),
                  text)


def mask(text: str, mark: str = "***") -> str:
    """機密遮罩的**單一實作**（推送結果、`last_error`、探針輸出尾段共用；審查 F-09）：依
    `SECRET_PATTERNS` 把值換成 `mark`；先對輸入做一次 `%xx` 解碼（URL 編碼形不漏）。"""
    text = _decoded(text)
    for _name, rx, repl, _cond in SECRET_PATTERNS:
        text = rx.sub(lambda m, r=repl: r(m, mark), text)
    return text


def scan_names(text: str) -> list[str]:
    """`text` 命中的樣式名（掃描規則比遮罩嚴：`key-value` 須值 ≥12 字元且只含值字元，避免把散文與
    型別標註判成機密）；不含命中的值。"""
    text = _decoded(text)
    out = []
    for name, rx, _repl, cond in SECRET_PATTERNS:
        if any(cond is None or cond(m) for m in rx.finditer(text)):
            out.append(name)
    return out


# ── git 子行程環境：允許清單（TCS-P7 附錄 A.10、勘誤 E-54）─────────────────────────────────
#: 允許清單（鍵名；win32 大小寫不分）。`-c` 蓋不過環境變數（`GIT_SSL_NO_VERIFY`、`*_PROXY`、
#: `GIT_TRACE*`、`GCM_*`、`GIT_ASKPASS`…，實測 E-61），所以環境用允許清單而不是黑名單剔除。
ENV_ALLOW = {
    "win32": (
        "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT", "OS", "COMPUTERNAME",
        "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROGRAMDATA", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "PROGRAMW6432", "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)",
        "COMMONPROGRAMW6432", "USERNAME", "USERDOMAIN", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "HOME", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE"),
    "posix": (
        "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "TZ", "LANG", "XDG_CONFIG_HOME",
        "XDG_DATA_HOME", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "SSH_AUTH_SOCK"),
}
_ENV_PREFIX = {"win32": (), "posix": ("LC_",)}
#: 只在 push profile（pre-push 閘門要用的變數）：名稱、前綴（前綴另排除名稱含下列字樣者：無人值守
#: 自述、運轉範圍、稽核金鑰；整個套件讀前兩個變數名的站點只有 `unattended.py`，這裡只用字樣）
_PUSH_NAMES = ("PYTHONUTF8", "PYTHONIOENCODING")
_PUSH_PREFIX = "AUTOSDD_"
_PUSH_EXCLUDE_WORDS = ("UNATTENDED", "PATROL_RUN", "AUDIT_KEY")
#: 固定值（覆寫）；各 profile 另加
ENV_FIXED = {"GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_ATTR_NOSYSTEM": "1"}
_PROFILE_FIXED = {"read": {"GIT_OPTIONAL_LOCKS": "0"}, "push": {"GCM_INTERACTIVE": "never"}}
#: 測試縫：額外放行的變數名（測試夾具用它把 `GIT_CONFIG_GLOBAL` 等隔離變數傳給 git）；正式環境恆空
ENV_TEST_PASSTHROUGH: tuple[str, ...] = ()


def env_for_git(parent, profile: str, *, platform: str | None = None,
                extra: tuple[str, ...] | None = None) -> dict[str, str]:
    """套件內**所有** git 子行程的環境（單一函式）：只從 `parent` 取 `ENV_ALLOW` 內的變數，`PATH`
    取 `safe_path` 結果（再去掉 cwd 之下的段），加固定值；`profile`＝`read`／`push`；`platform`
    ＝`win32` 或其他（posix），預設取目前平台；`extra` 缺省＝測試縫 `ENV_TEST_PASSTHROUGH`
    （正式環境恆空）。其餘一律不傳。"""
    extra = ENV_TEST_PASSTHROUGH if extra is None else extra
    win = (platform or ("win32" if os.name == "nt" else "posix")).startswith("win")
    plat = "win32" if win else "posix"
    names = set(ENV_ALLOW[plat]) | {n.upper() if win else n for n in extra}
    if profile == "push":
        names |= set(_PUSH_NAMES)
    out: dict[str, str] = {}
    path_value = ""
    for key, value in parent.items():
        kk = key.upper() if win else key
        if kk == "PATH":
            path_value = value
        elif kk in names or kk.startswith(_ENV_PREFIX[plat]):
            out[key] = value
        elif (profile == "push" and kk.startswith(_PUSH_PREFIX)
              and not any(w in kk for w in _PUSH_EXCLUDE_WORDS)):
            out[key] = value
    segments = []
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        cwd = None
    for seg in safe_path({"PATH": path_value}).split(os.pathsep):
        try:
            under = (cwd is not None and cwd.parent != cwd
                     and Path(seg).resolve().is_relative_to(cwd))
        except OSError:
            under = True
        if seg and not under:
            segments.append(seg)
    out["PATH"] = os.pathsep.join(segments)
    out.update(ENV_FIXED)
    out.update(_PROFILE_FIXED[profile])
    return out


# ── git 設定規則：全套件唯一宣告表（TCS-P7 附錄 A.9、勘誤 E-29、E-49、E-55、E-56） ─────────────
#: 推送守門認可的憑證輔助程式（system／global 層只准這些；`sched arm` 記入 `armed.json`）
SAFE_HELPERS = ("manager", "manager-core", "osxkeychain", "wincred", "libsecret", "cache")
#: repo 既定的 hooks 目錄（`core.hookspath` 須存在且等於它；測試縫：夾具以 mock 替換）
EXPECTED_HOOKS = "tools/git-hooks"
LOCAL_LAYERS = frozenset(("local", "worktree", "command"))  # 可被 repo 內行為改寫的層
_FALSY = ("false", "0", "no", "off")


class Rule(NamedTuple):
    """`match`＝鍵（小寫）的完整比對式（`.+` 代子區段）；`layers`＝檢查的層（None＝全部）；
    `bad(scope, value)`＝判不合；`pins`＝推送端釘定的（鍵, 值）。"""
    match: str
    layers: frozenset | None
    bad: Callable[[str, str], bool]
    pins: tuple = ()


def _any(_scope: str, _val: str) -> bool:
    return True


# 三類：甲＝可釘定且無副作用（每次呼叫 -c 釘安全值；system／global 層出現不擋，local／worktree／
# command 層與 GIT_CONFIG_* 環境變數出現仍擋）；乙＝不能釘固定值但有合法值（`RECORDED_PATTERN`：
# arm 時記下 system＋global 的有效值到 `armed.json` 的 `config_pins`、推送時以記錄值釘定、現值與
# 記錄不同即擋、arm 時沒有值則不釘且任何層出現即擋、不釘空值〔`http.proxy` 與 helper 清空例外〕；
# local 層出現一律擋）；丙＝不可釘定且無合法用途（任何層出現即擋，只偵測不釘）。
CONFIG_RULES: tuple[Rule, ...] = (
    # ── 乙（local 層一律擋；system／global 層由 `recorded_problems` 比對記錄）
    Rule(r"credential\.helper", LOCAL_LAYERS, _any, (("credential.helper", ""),)),  # 清空後接記錄值
    Rule(r"credential\..+", LOCAL_LAYERS, _any),  # 前綴涵蓋全部鍵與子區段（E-55）
    Rule(r"core\.sshcommand", LOCAL_LAYERS, _any),
    Rule(r"core\.attributesfile", LOCAL_LAYERS, _any),
    Rule(r"filter\..+", LOCAL_LAYERS, _any),  # clean／smudge／process／required（E-56）
    Rule(r"http\.sslcainfo", LOCAL_LAYERS, _any),
    Rule(r"http\.sslcapath", LOCAL_LAYERS, _any),
    Rule(r"http\.sslbackend", LOCAL_LAYERS, _any),
    Rule(r"http\.proxy", LOCAL_LAYERS, _any),
    Rule(r"http\..+\.proxy", LOCAL_LAYERS, _any),
    # ── 甲
    Rule(r"core\.hookspath", LOCAL_LAYERS, _any, (("core.hooksPath", "<hooks>"),)),
    Rule(r"core\.fsmonitor", LOCAL_LAYERS, lambda s, v: v.strip().lower() not in ("false", ""),
         (("core.fsmonitor", "false"),)),
    Rule(r"core\.gitproxy", LOCAL_LAYERS, _any, (("core.gitProxy", ""),)),
    Rule(r"core\.askpass", LOCAL_LAYERS, _any, (("core.askPass", ""),)),
    Rule(r"core\.usereplacerefs", LOCAL_LAYERS, lambda s, v: v.strip().lower() not in _FALSY,
         (("core.useReplaceRefs", "false"),)),
    Rule(r"log\.showsignature", LOCAL_LAYERS, lambda s, v: v.strip().lower() not in _FALSY,
         (("log.showSignature", "false"),)),
    Rule(r"http\.sslverify", LOCAL_LAYERS, lambda s, v: v.strip().lower() in _FALSY,
         (("http.sslVerify", "true"),)),
    Rule(r"remote\..+\.uploadpack", LOCAL_LAYERS, _any,
         (("remote.origin.uploadpack", "git-upload-pack"),)),
    Rule(r"remote\..+\.receivepack", LOCAL_LAYERS, _any,
         (("remote.origin.receivepack", "git-receive-pack"),)),
    Rule(r"push\.gpgsign", LOCAL_LAYERS, lambda s, v: v.strip().lower() not in _FALSY + ("",),
         (("push.gpgSign", "false"),)),
    Rule(r"protocol\.ext\.allow", LOCAL_LAYERS, lambda s, v: v.strip().lower() != "never",
         (("protocol.ext.allow", "never"),)),
    # ── 丙（任何層；`remote.*.vcs` 空值會讓 git 找名為空字串的 helper、所有推送失敗，故只偵測不釘）
    Rule(r"url\..+\.(?:push)?insteadof", None, _any),
    Rule(r"remote\..+\.pushurl", None, _any),
    Rule(r"remote\..+\.proxy", None, _any),
    Rule(r"remote\..+\.vcs", None, _any),
)
#: 行程環境中任一存在即不合的變數（`detail`＝`env:<名>`）
ENV_RULES = re.compile(r"^GIT_CONFIG_(?:COUNT|PARAMETERS|KEY_.*|VALUE_.*)$")
#: 乙類鍵的比對式（鍵＝小寫的段與變數名、子區段保留原大小寫）；`PINNABLE`＝可用標準大小寫寫法
#: 釘定的單一鍵（其餘乙類鍵以原鍵名釘定）
RECORDED_PATTERN = re.compile(
    r"credential\..+|core\.sshcommand|core\.attributesfile|filter\..+|http\.sslcainfo"
    r"|http\.sslcapath|http\.sslbackend|http\.proxy|http\..+\.proxy")
PINNABLE = {"http.sslcainfo": "http.sslCAInfo", "http.sslcapath": "http.sslCAPath",
            "http.sslbackend": "http.sslBackend", "core.sshcommand": "core.sshCommand",
            "http.proxy": "http.proxy", "core.attributesfile": "core.attributesFile"}


def _shown(key: str) -> str:
    """要顯示的鍵名（子區段以 `*` 代替，不含值）。"""
    parts = key.split(".")
    return f"{parts[0]}.*.{parts[-1]}" if len(parts) > 2 else key


def config_rule_hit(scope: str, key: str, val: str) -> str | None:
    """依 `CONFIG_RULES` 判一筆設定（`key` 的段與變數名小寫）：不合回要顯示的鍵名；合規回 None。
    `core.hookspath` 由呼叫端另判（存在、唯一、等於既定值）。"""
    for rule in CONFIG_RULES:
        if not re.fullmatch(rule.match, key.lower()) or rule.match == r"core\.hookspath":
            continue
        if rule.layers is not None and scope not in rule.layers:
            continue
        if rule.bad(scope, val):
            return _shown(key)
    return None


def _norm_key(key: str) -> str:
    """段與變數名轉小寫、子區段（網址等，區分大小寫）保留原樣。"""
    parts = key.split(".")
    if len(parts) < 3:
        return key.lower()
    return ".".join([parts[0].lower(), *parts[1:-1], parts[-1].lower()])


def parse_config_list(raw: str) -> list[tuple[str, str, str]]:
    """`git config --list --show-scope --includes -z` 的輸出→[(層, 鍵, 值)]（鍵見 `_norm_key`）。"""
    toks, out = raw.split("\0"), []  # `-z` 格式：`<scope>\0<key>\n<value>\0`（scope 自成一段）
    for i in range(0, len(toks) - 1, 2):
        key, _, val = toks[i + 1].partition("\n")
        out.append((toks[i], _norm_key(key), val))
    return out


def _is_recorded(key: str) -> bool:
    return RECORDED_PATTERN.fullmatch(key.lower()) is not None


def _is_helper(key: str) -> bool:
    return key.startswith("credential.") and key.rsplit(".", 1)[-1] == "helper"


def _arm_refused(key: str, val: str) -> bool:
    """讓權杖明文落地或寫追蹤檔的值（E-55）：`credentialStore=plaintext`、任何 `plaintext*`、
    非空且非 false 的 `trace*`；`helper` 值須屬 `SAFE_HELPERS`。"""
    if not key.startswith("credential."):
        return False
    var, val = key.rsplit(".", 1)[-1], val.strip().lower()
    return ((var == "credentialstore" and val == "plaintext") or var.startswith("plaintext")
            or (var.startswith("trace") and val not in ("", *_FALSY))
            or (var == "helper" and val not in SAFE_HELPERS))


def arm_record(repo: Path) -> tuple[dict | None, str]:
    """`sched arm` 時記下乙類鍵的有效值（system＋global 層）：回（`armed.json` 的 `config_pins`
    ＝{鍵: [值…]}, ""）；local／worktree／command 層出現乙類鍵、或值屬明文儲存／追蹤設定／不安全
    helper ⇒（None, 鍵名）。沒有值的鍵不記、之後任何層出現即擋。arm 行程環境含 `*_PROXY` 時印
    警告（推送任務不使用環境代理）。"""
    cp = Git(repo).run("config", "--list", "--show-scope", "--includes", "-z")
    if cp is None or cp.returncode not in (0, 1):
        return None, "git 設定讀取失敗"
    pins: dict[str, list[str]] = {}
    for scope, key, val in parse_config_list(cp.stdout):
        if not _is_recorded(key):
            continue
        val = val.strip()
        if scope in LOCAL_LAYERS or _arm_refused(key, val):
            return None, _shown(key).replace("\n", " ")
        if val:
            pins.setdefault(key, []).append(val)
    if any(k.upper().endswith("_PROXY") for k in os.environ):
        sys.stderr.write("警告：目前環境含 *_PROXY；推送任務不使用環境代理，需代理請改設 global "
                         "http.proxy 後重新 sched arm\n")
    return pins, ""


def recorded_problems(entries, armed: dict | None) -> list[str]:
    """乙類鍵：現行 system／global 有效值須等於 `armed.json` 的 `config_pins`（沒記＝須沒有）；
    回不合的鍵（顯示形）。"""
    pins = armed_pins(armed)
    seen: dict[str, list[str]] = {}
    for scope, key, val in entries:
        if _is_recorded(key) and scope not in LOCAL_LAYERS:
            seen.setdefault(key, []).append(val.strip())
    return sorted({_shown(k) for k in seen.keys() | pins.keys()
                   if seen.get(k, []) != pins.get(k, [])
                   or (_is_helper(k) and any(v not in SAFE_HELPERS for v in seen.get(k, [])))})


def armed_pins(armed: dict | None) -> dict[str, list[str]]:
    """`armed.json` 的 `config_pins`→{鍵: [值…]}；形態不對的項一律當沒記。"""
    raw = (armed or {}).get("config_pins")
    return {k: [x for x in v if isinstance(x, str)] for k, v in (raw.items() if isinstance(
        raw, dict) else ()) if isinstance(k, str) and isinstance(v, list)}


def PIN_ARGS(repo: Path, pins=None) -> list[str]:  # noqa: N802  # 規格名稱
    """推送端釘定序列（最高優先序的 `-c`）：甲類固定值依 `CONFIG_RULES` 由上而下，
    `credential.helper=` 清空在最前、後接記錄的 helper 各一個；其後乙類記錄值——helper 類
    （含網址限定）先清空再依序補、
    單值鍵以記錄值釘定、不釘空值；`http.proxy` 無記錄時釘空值（空字串＝不用代理，E-54 例外）。
    除設定檢查那一次外，守門與推送的每個 git 呼叫在子命令之前帶它（勘誤 E-29、E-60）。"""
    pins = pins or {}
    hooks = EXPECTED_HOOKS
    if not os.path.isabs(hooks):
        hooks = f"{Path(repo).as_posix()}/{hooks}"
    out: list[str] = []
    for rule in CONFIG_RULES:
        for key, value in rule.pins:
            out += ["-c", f"{key}={hooks if value == '<hooks>' else value}"]
            if key == "credential.helper":
                for helper in pins.get("credential.helper", ()):
                    out += ["-c", f"credential.helper={helper}"]
    for key in sorted(pins):
        vals = [v for v in pins[key] if v.strip()]
        if key == "credential.helper" or not vals:
            continue
        if _is_helper(key):
            out += ["-c", f"{key}="] + [a for v in vals for a in ("-c", f"{key}={v}")]
        else:
            out += ["-c", f"{PINNABLE.get(key, key)}={vals[-1]}"]
    if not any(pins.get("http.proxy", ())):
        out += ["-c", "http.proxy="]
    return out


def safe_path(env=None) -> str:
    """`PATH` 去掉 repo 與虛擬環境之下的目錄（審查 F-10／F-16：那裡的 `git` 是被攻擊面）。"""
    env = os.environ if env is None else env
    repo = Path(__file__).resolve().parents[3]
    # `sys.prefix`（venv 根、pyenv 版本目錄）目前使用者可寫才排除（E-21 ③）：防有人放假 `git`，
    # 不可寫的系統前綴（POSIX `/usr`）放不進東西、排除它會讓 `/usr/bin/git` 找不到
    prefix = Path(sys.prefix).resolve()
    banned = [repo, prefix] if os.access(prefix, os.W_OK) else [repo]
    keep = []
    for d in (env.get("PATH") or "").split(os.pathsep):
        try:
            inside = bool(d) and any(Path(d).resolve().is_relative_to(b) for b in banned)
        except OSError:
            inside = True
        if d and not inside:
            keep.append(d)
    return os.pathsep.join(keep)


def resolve_git(env=None) -> str | None:
    """git 執行檔的絕對路徑（審查 F-10；E-33）：逐段掃 `safe_path`＋`PATHEXT` 檔案存在，**不用
    標準庫的 which**（其 Windows 版先查目前目錄）；結果不在 repo 根、`sys.prefix`、目前工作目錄
    之下；解析不到＝None（呼叫端 fail-closed）。"""
    env = os.environ if env is None else env
    exts = [""] if not sys.platform.startswith("win") else [
        e.lower() for e in (env.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD").split(";") if e]
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        return None
    for d in safe_path(env).split(os.pathsep):
        try:
            if d and Path(d).resolve().is_relative_to(cwd) and cwd.parent != cwd:
                continue
        except OSError:
            continue
        for ext in exts:
            cand = Path(d) / f"git{ext}"
            if cand.is_file() and (sys.platform.startswith("win") or os.access(cand, os.X_OK)):
                return str(cand)
    return None


_GREP_LINE_RE = re.compile(r"^(.*?):(\d+):(.*)$")


def apply_numstat(repo: Path, patch_file: Path) -> list[str]:
    """`git apply --numstat -z` 看到的路徑（改名／複製兩端皆列）；git 不可用拋 OSError。
    只能檢查、不能當 `touched` 的來源（R51 (b)）；測試以 mock.patch.object 模擬漏看。"""
    cp = Git(repo).run("-c", "core.autocrlf=false", "apply", "--numstat", "-z", str(patch_file))
    if cp is None or cp.returncode != 0:
        raise OSError("git apply --numstat 失敗或 git 不可用")
    toks = cp.stdout.split("\0")
    out, i = [], 0
    while i < len(toks):
        parts = toks[i].split("\t", 2)
        if len(parts) == 3 and parts[2] == "" and i + 2 < len(toks):
            out += [toks[i + 1], toks[i + 2]]
            i += 3
            continue
        if len(parts) == 3:
            out.append(parts[2])
        i += 1
    return [p for p in out if p]


class Git:
    def __init__(self, repo: Path, exe: str | None = None, pin: tuple[str, ...] = ()) -> None:
        """`exe`＝git 的絕對路徑；未傳即 `resolve_git` 解析，解析不到則 `run` 回 None（呼叫端
        fail-closed），**絕不退回裸名 `git`**（E-57）；`pin`＝每個呼叫在子命令之前帶的 `-c`
        釘定序列（`PIN_ARGS`）。"""
        self.repo = repo.resolve()
        self.exe, self.pin = exe or resolve_git(os.environ), tuple(pin)
        self._ok: bool | None = None
        self.timed_out = False  # 最近一次 `run` 是否因逾時而回 None（分辨逾時與 git 不可用）

    def _env(self) -> dict[str, str]:
        return env_for_git(os.environ, "read")

    def run(self, *args: str, timeout: int | None = None) -> subprocess.CompletedProcess | None:
        """`timeout` 選用（牆鐘秒數；預設仍為 60 秒，P1 的呼叫不變）。"""
        if self.exe is None:
            return None
        argv = [self.exe, "-C", str(self.repo), *self.pin, *args]
        self.timed_out = False
        try:
            return subprocess.run(
                argv, capture_output=True, encoding="utf-8", errors="replace",
                timeout=_TIMEOUT if timeout is None else timeout, shell=False, env=self._env(),
                check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            self.timed_out = True
            return None
        except (OSError, subprocess.SubprocessError):
            return None

    def run_bytes(self, *args: str,
                  timeout: int | None = None) -> subprocess.CompletedProcess | None:
        """同 `run`，但 stdout／stderr 原樣回位元組（不解碼、不換行轉換）。"""
        if self.exe is None:
            return None
        argv = [self.exe, "-C", str(self.repo), *self.pin, *args]
        self.timed_out = False
        try:
            return subprocess.run(
                argv, capture_output=True, timeout=_TIMEOUT if timeout is None else timeout,
                shell=False, env=self._env(), check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            self.timed_out = True
            return None
        except (OSError, subprocess.SubprocessError):
            return None

    @property
    def available(self) -> bool:
        if self._ok is None:
            cp = self.run("rev-parse", "--is-inside-work-tree")
            self._ok = bool(cp and cp.returncode == 0 and cp.stdout.strip() == "true")
        return self._ok

    def is_commit(self, sha: str) -> bool:
        cp = self.run("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
        return bool(cp and cp.returncode == 0)

    def is_ancestor(self, sha: str) -> bool:
        cp = self.run("merge-base", "--is-ancestor", sha, "HEAD")
        return bool(cp and cp.returncode == 0)

    def log_first_parent(self, rel: str, rev_range: str | None = None) -> list[str] | None:
        args = ["-c", "core.quotepath=false", "log", "--first-parent", "--reverse", "--format=%H"]
        if rev_range:
            args.append(rev_range)
        cp = self.run(*args, "--", rel)
        if cp is None or cp.returncode != 0:
            return None
        return [ln.strip() for ln in cp.stdout.split("\n") if ln.strip()]

    def show(self, commit: str, rel: str) -> str | None:
        cp = self.run("show", f"{commit}:{rel}")
        return cp.stdout if cp is not None and cp.returncode == 0 else None

    def head(self) -> str | None:
        cp = self.run("rev-parse", "HEAD")
        sha = cp.stdout.strip() if cp is not None and cp.returncode == 0 else ""
        return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None

    def log_times(self, rel: str) -> list[tuple[str, int]] | None:
        """動過 `rel` 的 commit：(sha, committer 時間 epoch)，git 的預設走訪序（新→舊）。"""
        cp = self.run("-c", "core.quotepath=false", "log", "--format=%H %ct", "--", rel)
        if cp is None or cp.returncode != 0:
            return None
        pairs = [ln.split() for ln in cp.stdout.split("\n") if ln.strip()]
        return [(a, int(b)) for a, b in pairs]

    def commit_time(self, sha: str) -> int | None:
        cp = self.run("show", "-s", "--format=%ct", sha)
        txt = cp.stdout.strip() if cp is not None and cp.returncode == 0 else ""
        return int(txt) if txt.isdigit() else None

    def grep_only(self, pattern: str) -> list[tuple[str, int, str]] | None:
        """整個 repo（含未追蹤但未被忽略的檔）的 `-o` 命中：(相對路徑, 行號, 命中片段)。"""
        cp = self.run("-c", "core.quotepath=false", "grep", "-I", "-n", "-o", "--untracked",
                      "-E", pattern)
        if cp is None or cp.returncode not in (0, 1):
            return None
        hits = []
        for ln in cp.stdout.split("\n"):
            m = _GREP_LINE_RE.match(ln.rstrip("\r"))
            if m:
                hits.append((m.group(1), int(m.group(2)), m.group(3)))
        return hits
