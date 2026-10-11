"""額度參數檔的分層載入（env.shared → .env → 行程 env）與維護指令 `--env-doctor`。

載入鏈（高→低）：行程 env > AutoClaude/.env（僅引擎 3 鍵）> 根 .env（本機）> 根 env.shared
（git 追蹤、跨機同步）> 出廠 `ENV_SPEC`。解析器只有 `quota_policy_env.parse_env_text` 一個家，
本檔不寫第二份；本檔也不 import `quota_policy`（直接執行 quota_policy.py 時 `__main__`
不以該名註冊，回頭 import 會重跑一次——見 quota_policy_env.py 檔頭 R98 訂正）。

【重要】兩側讀者必須同序：harness 側（`quota_gate.policy_env`）讀本檔的 `merged_file_env`；
引擎側（`autoclaude/utils/config.py::_ENV_FILES`）AutoClaude 不能 import tools/ ⇒ 兩邊各自寫序、
由 `tools/tests/test_quota_env_layers.py` 以同一組合成語料雙邊對跑釘住（鏡子破了會紅）。
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import quota_policy_env as qpe

SHARED_NAME = "env.shared"
LOCAL_NAME = ".env"
ENGINE_DIR = "AutoClaude"
#: 與 `autoclaude/utils/config.py::_OVERRIDE_MARK` 同字（行尾 `# override-ok: <WHY>`＝明示覆寫）。
OVERRIDE_MARK = "override-ok:"
#: 引擎真的讀的鍵（`config.py` 內 `_quota_env(...)` 的呼叫點；測試以 AST 對照）。
ENGINE_KEYS = ("AUTOSDD_QUOTA_CONVERGE_PCT", "AUTOSDD_QUOTA_HALT_PCT", "AUTOSDD_QUOTA_DEGRADED_CAP")
#: 會讓 rc=1 的旗標；其餘（override／local／stale-copy／foreign）只是資訊。
ERROR_FLAGS = ("unknown", "bad-value", "duplicate", "dead", "redundant", "shadows-shared",
               "engine≠harness", "unreadable", "missing-shared", "bom")
_LABEL = {"process": "process-env", "engine": "AutoClaude/.env", "local": ".env",
          "shared": SHARED_NAME, "factory": "factory"}
_SPEC = {s.name: s for s in qpe.ENV_SPEC}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> tuple[str | None, str]:
    """回 `(文字, 狀態)`；狀態＝ok／absent／unreadable。壞編碼以 U+FFFD 取代照讀——與引擎
    `config.py::_env_file_value` 同一種容錯（cp950 存檔的 ASCII 鍵值兩側都讀得到）；
    只有 OSError（權限等）才是 unreadable。"""
    try:
        return path.read_text(encoding="utf-8", errors="replace"), "ok"
    except FileNotFoundError:
        return None, "absent"
    except OSError:
        return None, "unreadable"


def merged_file_env(root: Path) -> dict[str, str]:
    """harness 側的檔案層合併：env.shared（低）→ .env（高）。空白值**不遮蔽**下層（
    `KEY=` 在本 repo 的語意是「沒設」，舊版 .env.example 複本滿是這種行）；但鍵本身仍列出，
    與舊版單檔 `parse_env_text` 的鍵集合一致。呼叫端再疊 `os.environ`（行程 env 永遠最高）。"""
    merged: dict[str, str] = {}
    for name in (SHARED_NAME, LOCAL_NAME):
        text, _ = _read(root / name)
        for key, value in (qpe.parse_env_text(text) if text else {}).items():
            if value.strip() or key not in merged:
                merged[key] = value
    return merged


class Line(NamedTuple):
    no: int      # 1 起算
    key: str
    value: str   # 已剝行內註解
    raw: str     # 原行（不含行尾）；`override-ok:` 標記住在這裡


def _lines(text: str | None) -> list[Line]:
    return [Line(no, key, value, raw)
            for no, raw in enumerate((text or "").splitlines(), start=1)
            for key, value in qpe.parse_env_text(raw).items()]


def _same(key: str, a: str, b: str) -> bool:
    a, b = a.strip(), b.strip()
    if _SPEC[key].kind in ("float", "int"):
        try:
            return float(a) == float(b)
        except ValueError:
            return a == b
    return a == b


class Report(NamedTuple):
    out: list[str]
    errors: int
    fixable: dict[str, list[int]]   # 層名（local／engine）→ 可由 --fix 刪除的行號


def _factory(key: str) -> str:
    return qpe._fmt_default(_SPEC[key].default)


def diagnose(root: Path, environ: Mapping[str, str]) -> Report:
    paths = {"shared": root / SHARED_NAME, "local": root / LOCAL_NAME,
             "engine": root / ENGINE_DIR / LOCAL_NAME}
    status = {n: _read(p) for n, p in paths.items()}
    ents = {n: _lines(status[n][0]) for n in paths}
    last = {n: {x.key: x.value for x in ents[n]} for n in paths}      # harness：重複鍵取最後
    first: dict[str, dict[str, str]] = {n: {} for n in paths}          # 引擎：重複鍵取第一行
    for n in paths:
        for x in ents[n]:
            first[n].setdefault(x.key, x.value)

    def live(layer: str, key: str, table=last) -> str:
        v = table[layer].get(key, "").split("#")[0].strip()
        return v

    def harness(key: str) -> tuple[str, str]:
        if str(environ.get(key, "")).strip():
            return str(environ[key]).strip(), "process"
        return next(((live(n, key), n) for n in ("local", "shared") if live(n, key)),
                    (_factory(key), "factory"))

    def engine(key: str) -> tuple[str, str]:
        if str(environ.get(key, "")).split("#")[0].strip():
            return str(environ[key]).split("#")[0].strip(), "process"
        return next(((live(n, key, first), n) for n in ("engine", "local", "shared")
                     if live(n, key, first)), (_factory(key), "factory"))

    found: list[tuple[str, str]] = []          # (旗標, 說明)
    fixable: dict[str, list[int]] = {"local": [], "engine": []}
    # 本機層「--fix 之後仍會留下」的值：引擎層以它為下一層（否則判定順序會決定答案）。
    kept_local: dict[str, str] = {}
    if status["shared"][1] == "absent":
        found.append(("missing-shared", f"{SHARED_NAME} 不存在（它是追蹤檔：git pull 了嗎？）"))
    for n in paths:
        if status[n][1] == "unreadable":
            found.append(("unreadable", f"{_LABEL[n]} 讀不出來（權限／I/O）⇒ 該層被當成不存在"))
        if (status[n][0] or "").startswith("\ufeff"):
            found.append(("bom", f"{_LABEL[n]} 檔首有 UTF-8 BOM ⇒ 首行的鍵讀不到（鍵名前多一個"
                          "隱形字元）；請另存為 UTF-8（無 BOM）"))
        seen: dict[str, int] = {}
        for x in ents[n]:
            if x.key not in _SPEC:
                if x.key.startswith("AUTOSDD_"):   # 只點名自家命名空間；機密鍵（MINIMAX_* 等）不碰
                    found.append(("unknown", f"{_LABEL[n]}:{x.no} {x.key}（不在 ENV_SPEC 白名單 ⇒ "
                                  "檔案層讀不到；該鍵只認真環境變數，或是打錯字）"))
            elif x.key in seen:
                found.append(("duplicate", f"{_LABEL[n]}:{x.no} {x.key} 與第 {seen[x.key]} 行重複"
                              "（harness 取最後一行、引擎取第一行 ⇒ 兩側可能吃不同值）"))
            seen.setdefault(x.key, x.no)

    def judge(n: str, x: Line) -> None:
        where = f"{_LABEL[n]}:{x.no} {x.key}={x.value}"
        if n == "engine" and x.key not in ENGINE_KEYS:
            found.append(("dead", f"{where}（引擎只讀 {len(ENGINE_KEYS)} 個鍵、"
                          "harness 不讀本檔 ⇒ 沒有讀者）"))
            fixable[n].append(x.no)
            return
        chain = (("local", kept_local.get(x.key, "")), ("shared", live("shared", x.key)),
                 ("factory", _factory(x.key))) if n == "engine" else \
            (("shared", live("shared", x.key)), ("factory", _factory(x.key)))
        src, below = next(((a, b) for a, b in chain if b), ("factory", ""))
        if _same(x.key, x.value, below):
            flag, why = "redundant", f"與下一層相同（{below}）⇒ 多餘，且會遮住日後下一層的變更"
        elif n == "engine":
            flag, why = "engine≠harness", (f"引擎吃 {x.value}；本機層修好後 harness 吃 {below}"
                                           f"（{_LABEL[src]}）⇒ 兩側對同一額度池用不同門檻")
        elif live("shared", x.key):
            flag, why = "shadows-shared", f"遮住 {SHARED_NAME} 的 {live('shared', x.key)}"
        else:
            found.append(("local", f"{where}（本機專屬覆寫，沒有共享值可遮）"))
            kept_local[x.key] = x.value
            return
        if OVERRIDE_MARK in x.raw:
            found.append(("override", f"{where}（有 {OVERRIDE_MARK} 標記，視為刻意：{flag}）"))
            if n == "local":
                kept_local[x.key] = x.value
        else:
            found.append((flag, f"{where}：{why}"))
            fixable[n].append(x.no)

    for n in ("local", "engine"):             # 本機層先判：引擎層的「下一層」要吃它修復後的樣子
        for x in ents[n]:
            if x.key in _SPEC and x.value.strip():
                judge(n, x)

    env_for_load = {**{k: v for n in ("shared", "local") for k, v in last[n].items()
                       if v.strip() or k not in last["shared"]},
                    **{k: str(v) for k, v in environ.items()}}
    found += [("bad-value", p) for p in qpe.load_policy(env_for_load)[1]]
    try:
        import model_roles
        found += [("bad-value", p) for p in model_roles.load_model_roles(env_for_load)[1]]
    except ImportError:
        pass
    missing = [k for k in _SPEC if k not in last["local"]]
    if status["local"][1] == "ok" and missing and any(f == "redundant" for f, _ in found):
        found.append(("stale-copy", f".env 看起來是舊版 .env.example 複本（缺 {len(missing)} 鍵；"
                      "缺鍵無害，退回 env.shared／出廠值，功能上無差）"))
    clean = not fixable["local"] and not any(f in ERROR_FLAGS for f, _ in found)
    if status["local"][1] == "ok" and clean and not any(x.value.strip() for x in ents["local"]):
        found.append(("empty-local", ".env 已無任何有值的行（只剩註解／空白鍵）⇒ 可直接刪除該檔"))
    foreign = sum(1 for n in paths for x in ents[n]
                  if x.key not in _SPEC and not x.key.startswith("AUTOSDD_"))
    if foreign:
        found.append(("foreign", f"另有 {foreign} 行非 AUTOSDD_ 鍵（機密／他用）：不檢查、不印值"))

    out = [f"env-doctor  根目錄：{root}",
           "載入鏈（高→低）：行程 env > AutoClaude/.env（引擎 3 鍵）> .env（本機）> "
           f"{SHARED_NAME}（共享）> 出廠"]
    for n in ("shared", "local", "engine"):
        st = status[n][1]
        out.append(f"  {_LABEL[n]:<16} " + (f"存在，{len(last[n])} 鍵" if st == "ok"
                                           else "不存在" if st == "absent" else "讀不出來"))
    out.append("鍵 → 生效值〔來源〕（harness 側；引擎 3 鍵若與 harness 不同另列一行）")
    for key in _SPEC:
        v, layer = harness(key)
        out.append(f"  {key:<44} = {v or '（空）'}〔{_LABEL[layer]}〕")
        ev, el = engine(key) if key in ENGINE_KEYS else (v, layer)
        if key in ENGINE_KEYS and not _same(key, ev, v):
            out.append(f"  {'':<44}   引擎側 = {ev}〔{_LABEL[el]}〕  [engine≠harness]")
    errors = sum(1 for f, _ in found if f in ERROR_FLAGS)
    out.append("問題與提示：" + ("" if found else "無"))
    out += [f"  [{f}] {t}" for f, t in found]
    hint = "　修復：python tools/lib/quota_policy.py --env-doctor --fix"
    hint = hint if any(fixable.values()) else ""
    out.append(f"結論：{errors} 個問題 ⇒ rc={1 if errors else 0}{hint}")
    return Report(out, errors, fixable)


def _fix_one(path: Path, linenos: list[int]) -> list[str]:
    import difflib  # 只有 --fix 用得到：hook 鏈每次都 import 本檔，別讓它多付載入成本
    import shutil

    kept = path.read_bytes().decode("utf-8").splitlines(keepends=True)
    drop = {no - 1 for no in linenos}
    after = [ln for i, ln in enumerate(kept) if i not in drop]
    # UTC：備份檔名不帶 naive 本地時間；`timezone.utc`＋noqa：hook 鏈須能在 mac 預設 3.9 載入
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: UP017
    bak = path.with_name(f"{path.name}.bak.{stamp}")
    if not bak.exists():  # 同秒的第二輪修復不得用「已改過的檔」蓋掉第一輪的原檔備份
        shutil.copy2(path, bak)
    path.write_bytes("".join(after).encode("utf-8"))
    # n=0：不印鄰近行（AutoClaude/.env 的鄰行可能是機密）；被刪的行必為 ENV_SPEC 鍵，不含機密。
    diff = difflib.unified_diff(kept, after, f"{path.name}（修復前；備份＝{bak.name}）",
                                f"{path.name}（修復後）", n=0)
    return [ln.rstrip("\r\n") for ln in diff]


def doctor_cli(argv: Sequence[str]) -> int:
    root, fix, args = repo_root(), False, list(argv)
    while args:
        a = args.pop(0)
        if a == "--fix":
            fix = True
        elif a == "--root" and args:
            root = Path(args.pop(0))
        else:
            sys.stderr.write("用法：python tools/lib/quota_policy.py --env-doctor [--fix]\n")
            return 2
    rep = diagnose(root, os.environ)
    print("\n".join(rep.out))
    if not fix or not any(rep.fixable.values()):
        return 1 if rep.errors else 0
    for _ in range(3):                         # 引擎層的判定依賴本機層的修復結果 ⇒ 重驗到不動點
        for layer, nos in rep.fixable.items():
            if nos:
                path = root / LOCAL_NAME if layer == "local" else root / ENGINE_DIR / LOCAL_NAME
                print(f"\n--fix {path}")
                try:
                    print("\n".join(_fix_one(path, nos)))
                except (OSError, UnicodeDecodeError) as exc:   # 非 UTF-8 檔：解碼先於備份與寫入
                    print("[錯誤] 修復失敗（原檔未動或已有 .bak 備份）；非 UTF-8 檔請先另存 UTF-8："
                          f"{exc}")
                    return 2
        rep = diagnose(root, os.environ)
        if not any(rep.fixable.values()):
            break
    print("\n── 修復後重驗 ──\n" + "\n".join(rep.out))
    return 1 if rep.errors else 0
