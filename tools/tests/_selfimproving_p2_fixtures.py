# 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
"""SelfImproving P2 測試共用夾具（TCS-SelfImproving-P2 §5；底線開頭、不被收集）。

建在 P1 夾具 `_selfimproving_fixtures.py` 之上；各 P2 測試檔的 `setUpModule` 呼叫
`fx.setup("si_p2_")`。
夾具模組自行定義判準函式與建構器，不 import 被測模組的內部私有符號。合成編號一律於執行期組出。
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
from _selfimproving_fixtures import (
    SiTestCase,
    card_ev,
    dec_ev,
    freeze_ev,
    pid,
    promote_ev,
    prop_ev,
    rollback_ev,
    run_open_ev,
    sandbox_ev,
    skip_ev,
    verify_ev,
)

DEMO_PKG = {
    "demo_pkg/__init__.py": '"""demo"""\n',
    "demo_pkg/core.py": "VALUE = 1\n",
}


def make_p2_repo(dest: Path, *, commit: bool = True, **kw) -> Path:
    """`make_p1_repo` 加 `demo_pkg/` 兩個追蹤檔（C3 內；params.json 已為 30 鍵，R107 (b)）。"""
    repo = fx.make_p1_repo(dest, commit=False, **kw)
    for rel, text in DEMO_PKG.items():
        fx.put(repo, rel, text)
    if commit:
        fx.commit_all(repo, "C3")
    return repo


def p2_base() -> Path:
    """已建好的 P2 基線 repo 的複本（每個測試檔的快取只建一次）。"""
    if "p2_base" not in fx._CACHE:
        fx._CACHE["p2_base"] = make_p2_repo(fx.TMP / "p2baseline")
    dest = fx.new_dir("v")
    shutil.copytree(fx._CACHE["p2_base"], dest)
    return dest


RUN_EVENTS = (run_open_ev(1), skip_ev(1))


def verified_chain(n: int, verdict: str = "PASS", **sandbox) -> list[dict]:
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    """單一提案到 `verified` 的事件鏈（手寫；`prop`→`card`→核准→凍結→沙盒→驗證）。"""
    return [
        prop_ev(n, 1, target=[f"docs/notes/n{n}.md"]),
        card_ev(n),
        dec_ev(n, "approve"),
        freeze_ev(n),
        sandbox_ev(n, **sandbox),
        verify_ev(n, verdict),
    ]


def promoted_chain(n: int, **kw) -> list[dict]:
    return [*verified_chain(n), dec_ev(n, "promote"), promote_ev(n, **kw)]


def sc_p2_legal() -> list[dict]:
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    """`SC-P2-LEGAL`（AT-240-2-1）：五個 PROP 各走 R75 的一條合法路徑。"""
    a = [*promoted_chain(124), dec_ev(124, "rollback"), rollback_ev(124)]
    b = [
        *verified_chain(125, "NE"),
        dec_ev(125, "promote", flags=["unverified_ack"]),
        promote_ev(125, unverified_ack=True),
    ]
    c = [
        prop_ev(126, 1, target=["docs/notes/n126.md"]),
        dec_ev(126, "approve"),
        freeze_ev(126),
        sandbox_ev(126, touched_ok=False),
        verify_ev(126, "NE", reasons=["TOUCHED-SUPERSET"]),
        dec_ev(126, "return", reason_class="工件類別錯"),
        prop_ev(126, 1, rev=2, target=["docs/notes/n126.md"]),
    ]
    d = [
        prop_ev(127, 1, target=["docs/notes/n127.md"]),
        dec_ev(127, "approve"),
        freeze_ev(127),
        sandbox_ev(127),
        verify_ev(127, "NE", probes_n=1, baseline_red=True, patched_green=True, mutated_red=None,
                  carrier_proof=True, verify_sha256=fx.H(9), heldout_digest=fx.H(7),
                  reasons=["MUTATION-ABSENT"]),
        verify_ev(127, "PASS"),
    ]
    e = [
        *verified_chain(128),
        dec_ev(128, "decline-promote", reason_class="風險過高"),
    ]
    return [*RUN_EVENTS, *a, *b, *c, *d, *e]


# --------------------------------------------------------------------------- 測試基底與 CLI 呼叫
class P2TestCase(SiTestCase):
    """P2 測試基底：在 P1 基底之上把 `CLAUDE_CONFIG_DIR` 指到 tmp 內的 `cfg/`（逐字稿根）。"""

    def setUp(self) -> None:
        super().setUp()
        self.cfg = fx.new_dir("cfg")
        self.cfg.mkdir()
        patcher = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.cfg)})
        patcher.start()
        self.addCleanup(patcher.stop)
        for k in ("AUTOSDD_UNATTENDED", "AUTOSDD_SI_AUDIT_KEY"):
            os.environ.pop(k, None)

    def new_home(self) -> Path:
        """換一個全新的家目錄（同一測試內換用不同的 repo 複本時用：家目錄是機器層的狀態）。"""
        self.home = fx.new_dir("home")
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        return self.home


def cli(R: Path, *argv) -> tuple[int, str, str]:
    """不依附 TestCase 的 CLI 呼叫（夾具函式用）；環境由呼叫端的 TestCase 設好。"""
    import selfimproving

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = selfimproving.main([*[str(a) for a in argv], "--repo", str(R)])
    return rc, out.getvalue(), err.getvalue()


# --------------------------------------------------------------------------- 逐字稿夾具（§5.3）
T0 = datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC)


def ts(seconds: int = 0) -> str:
    return (T0 + timedelta(seconds=seconds)).isoformat()


def rec_assistant_text(text: str, when: str) -> dict:
    return {"type": "assistant", "timestamp": when,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


def rec_assistant_tool_use(when: str, tool_input=None) -> dict:
    block = {"type": "tool_use", "id": "tu1", "name": "Bash", "input": tool_input or {}}
    return {"type": "assistant", "timestamp": when,
            "message": {"role": "assistant", "content": [block]}}


def rec_assistant_thinking(when: str) -> dict:
    block = {"type": "thinking", "thinking": "..."}
    return {"type": "assistant", "timestamp": when,
            "message": {"role": "assistant", "content": [block]}}


def rec_user_human(text, when: str) -> dict:
    return {"type": "user", "origin": {"kind": "human"}, "timestamp": when,
            "message": {"role": "user", "content": text}}


def rec_user_sdk(text: str, when: str) -> dict:
    return {**rec_user_human(text, when), "origin": {"kind": "sdk"}}


def rec_user_meta(text: str, when: str) -> dict:
    return {**rec_user_human(text, when), "isMeta": True}


def rec_user_tool_result(text: str, when: str) -> dict:
    block = {"type": "tool_result", "tool_use_id": "tu1", "content": text}
    return {"type": "user", "timestamp": when,
            "message": {"role": "user", "content": [block]}}


def rec_attachment(prompt: str, typed_ts, origin_kind: str, write_ts: str) -> dict:
    att = {"type": "queued_command", "prompt": prompt, "origin": {"kind": origin_kind}}
    if typed_ts is not None:
        att["timestamp"] = typed_ts
    return {"type": "attachment", "timestamp": write_ts, "attachment": att}


def transcript_dir(R: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(R.resolve()))
    return Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / slug


def transcript_path(R: Path, sid: str) -> Path:
    return transcript_dir(R) / f"{sid}.jsonl"


def make_transcript(R: Path, sid: str, records, *, bom: bool = False, crlf: bool = False) -> Path:
    path = transcript_path(R, sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    nl = "\r\n" if crlf else "\n"
    lines = [r if isinstance(r, str) else json.dumps(r, ensure_ascii=False) for r in records]
    raw = "".join(ln + nl for ln in lines).encode("utf-8")
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + raw)
    return path


def card_core(stdout: str) -> str:
    """自 `card --issue` 的 stdout 取「卡面核心區」（分界線之前的各行，以 LF 連接）。"""
    return "\n".join(stdout.split("\n--- 以下不計入核心區 ---")[0].splitlines())


_NEW_SID = [0]


def new_sid() -> str:
    _NEW_SID[0] += 1
    return f"3f2a1b4c-5d6e-4f70-8a9b-{_NEW_SID[0]:012d}"


def pc01(R: Path, core: str, quote: str, *, fillers: int = 1, crlf_core: bool = False,
         sid: str | None = None) -> tuple[str, int]:
    """PC-01：卡面 assistant 文字、0～3 則只含 tool_use 的 assistant 訊息、再 human 的決定記錄。"""
    sid = sid or new_sid()
    text = core.replace("\n", "\r\n") if crlf_core else core
    recs = [rec_assistant_text(text, ts(0))]
    recs += [rec_assistant_tool_use(ts(5 + i)) for i in range(fillers)]
    recs.append(rec_user_human(quote, ts(20)))
    make_transcript(R, sid, recs)
    return sid, len(recs)


def pc02(R: Path, core: str, quote: str, sid: str | None = None) -> tuple[str, int]:
    """PC-02：附件載體（行 2 為附件、行 3 為只含 tool_use 的 assistant 訊息）。"""
    sid = sid or new_sid()
    make_transcript(R, sid, [
        rec_assistant_text(core, ts(0)),
        rec_attachment(quote, ts(10), "human", ts(40)),
        rec_assistant_tool_use(ts(30)),
    ])
    return sid, 2


def pc03(R: Path, quote: str, sid: str | None = None) -> tuple[str, int]:
    """PC-03：只有一則 human 發言（`resume` 專用，無卡面）。"""
    sid = sid or new_sid()
    make_transcript(R, sid, [rec_user_human(quote, ts(0))])
    return sid, 1


# --------------------------------------------------------------------------- 事件帳本操作
def rewrite_event(R: Path, seq: int, **changes) -> None:
    """只改事件帳本第 `seq` 行的指定鍵（保留鍵序與其餘各行位元組）。"""
    path = R / fx.EVL
    out = []
    for raw in path.read_bytes().decode("utf-8").split("\n"):
        if raw.strip() and json.loads(raw).get("seq") == seq:
            obj = json.loads(raw)
            obj.update(changes)
            raw = fx.dumps_line(obj)
        out.append(raw)
    path.write_bytes("\n".join(out).encode("utf-8"))


def drop_events(R: Path, kind: str, prop: str | None = None) -> None:
    path = R / fx.EVL
    keep = []
    for raw in path.read_bytes().decode("utf-8").split("\n"):
        if raw.strip():
            obj = json.loads(raw)
            if obj.get("kind") == kind and (prop is None or obj.get("prop") == prop):
                continue
        keep.append(raw)
    path.write_bytes("\n".join(keep).encode("utf-8"))


def last_event(R: Path, kind: str) -> dict:
    return [e for e in fx.EV(R) if e["kind"] == kind][-1]


# --------------------------------------------------------------------------- 流程建構器（§5.2）
VERB_KIND = {"核准": "approve", "退回": "return", "晉升": "promote", "轉交": "ack-handoff",
             "不轉交": "reject", "回滾": "rollback", "解除": "unblock", "恢復": "resume"}


def open_run(R: Path) -> str:
    """回已開未關的運轉；沒有則 `run-open` 加 `research --skip offline`。"""
    events = fx.EV(R)
    closed = {e["run"] for e in events if e["kind"] == "run.close"}
    opened = [e["run"] for e in events if e["kind"] == "run.open" and e["run"] not in closed]
    if opened:
        return opened[-1]
    rc, out, err = cli(R, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main")
    assert rc == 0, out + err
    run = re.search(r"id=(\S+)", out).group(1)
    rc, out, err = cli(R, "research", "--skip", "--run", run, "--reason", "offline", "--note", "x")
    assert rc == 0, out + err
    return run


def _modify_patch(target: str) -> bytes:
    return fx.patch_insert(target, 50, ["FIXED-LINE"], old=fx.fixture_files()[target])


def _bad_context_patch(target: str) -> bytes:
    """與 `modify` 同形但上下文行與 base 不合（`git apply` 必失敗；`--numstat` 仍可解析）。"""
    wrong = "".join(f"WRONG {i}\n" for i in range(1, 101))
    return fx.patch_insert(target, 50, ["FIXED-LINE"], old=wrong)


MEM_FILES = {
    "memory/feedback_demo.md": "".join(f"note {i:02d}\n" for i in range(1, 21)),
    "memory/MEMORY.md": "".join(f"- [條目 {i}](m_{i}.md) — 說明 {i}\n" for i in range(1, 6)),
}
MEM_TARGET = "memory/feedback_demo.md"


def make_memdir(dest: Path) -> Path:
    """記憶目錄夾具（邏輯根 `memory/`）：`MEMORY.md` 與 `feedback_demo.md`；回 `dest/memory`。"""
    root = dest / "memory"
    root.mkdir(parents=True)
    for rel, text in MEM_FILES.items():
        (dest / rel).write_bytes(text.encode("utf-8"))
    return root


def _mem_patch() -> bytes:
    """M 類 PROP 的逐行 patch：`feedback_demo.md` 加 `FIXED-MEM`、`MEMORY.md` 加一行索引。"""
    return fx.patch_join(
        fx.patch_insert(MEM_TARGET, 10, ["FIXED-MEM"], old=MEM_FILES[MEM_TARGET]),
        fx.patch_insert("memory/MEMORY.md", 5, ["- [FIXED-MEM](feedback_demo.md) — 修復"],
                        old=MEM_FILES["memory/MEMORY.md"]))


def mem_heldout(dest: Path) -> Path:
    """M 類 held-out：`probe_mem.py`（`FIXED-MEM` 在則 rc 0）加移除該行的突變。"""
    ho = make_heldout(dest, probes="mem", mutation=False)
    base = MEM_FILES[MEM_TARGET]
    cur = "".join(base.splitlines(keepends=True)[:10] + ["FIXED-MEM\n"]
                  + base.splitlines(keepends=True)[10:])
    (ho / "mutation.patch").write_bytes(fx.patch_diff(MEM_TARGET, cur, base))
    mf = json.loads((ho / "manifest.json").read_text(encoding="utf-8"))
    mf["mutation"] = "mutation.patch"
    (ho / "manifest.json").write_bytes((json.dumps(mf, ensure_ascii=False, indent=2)
                                        + "\n").encode("utf-8"))
    return ho


def new_prop(R: Path, *, cls: str = "D", action: str = "modify", target: str | None = None,
             route: str = "loop", proposer: str = "SA", sources=None, patch: str = "ok",
             memory: Path | None = None, note: str | None = None) -> str:
    """`prop-new` 一個 PROP（patch 種類 `modify`／`add`；`route` 為 `handoff:<通道>` 者改走守衛路徑
    的新增 patch，其路由由 `prop-new` 自 patch 導出；M 類帶 `memory` 目錄）；回 PROP 號。"""
    run = open_run(R)
    if cls == "M":
        over = {"patch": _mem_patch(), "target": [MEM_TARGET, "memory/MEMORY.md"],
                "action": "modify", "proposer": proposer, "memory_dir": memory}
    elif route != "loop":
        _NEW_SID[0] += 1
        low, n = route.split(":", 1)[1].lower(), _NEW_SID[0]
        guard = f".claude/hooks/new_guard_{low}_{n}.py"
        patch = fx.patch_join(fx.patch_add(guard, ["x = 1"]),
                              fx.patch_add(f"docs/notes/clean_{low}_{n}.md", ["clean"]))
        over = {"patch": patch, "target": [guard], "action": "add", "proposer": proposer,
                "handoff": route.split(":", 1)[1]}
        cls = "P"
    else:
        if action == "add":
            target = target or NEW_NOTE
            patch = fx.patch_add(target, ["FIXED-LINE"])
        else:
            target = target or "docs/notes/demo.md"
            patch = _modify_patch(target) if patch == "ok" else _bad_context_patch(target)
        over = {"patch": patch, "target": [target], "action": action, "proposer": proposer}
    if sources is not None:
        over["sources"] = sources
    if note:  # 提案本文附一段散文（測試「本文字樣不影響 verdict」）
        over["body"] = fx.body_md("M" if cls == "M" else "P").rstrip("\n") + f"\n\n{note}\n"
    rc, out, err = cli(R, "prop-new", "--run", run, *fx.good_prop_args(R, cls, **over))
    assert rc == 0, out + err
    return re.search(r"id=(\S+)", out).group(1)


def issue_card(R: Path, prop: str) -> str:
    rc, out, err = cli(R, "card", prop, "--issue")
    assert rc == 0, out + err
    return out


def decide_say(R: Path, ident: str, quote: str, *, kind: str | None = None,
               reason_class: str | None = None, shape: str = "PC-01", by: str = "main",
               extra=(), issue: bool = True):
    """卡面發出後建合成逐字稿並呼叫 `decide`；回 (rc, out, err, sid, line)。"""
    is_run = ident.startswith("RUN-")
    verb = quote.split(" ", 1)[0]
    core = ""
    if not is_run and issue:
        core = card_core(issue_card(R, ident))
    elif not is_run:
        core = card_core(cli(R, "card", ident)[1])
    if is_run:
        sid, line = pc03(R, quote)
    elif shape == "PC-02":
        sid, line = pc02(R, core, quote)
    else:
        sid, line = pc01(R, core, quote)
    if kind is None:
        kind = VERB_KIND.get(verb)
        if verb == "否決":
            verified = any(e["kind"] == "app.verify" and e.get("prop") == ident
                           for e in fx.EV(R))
            kind = "decline-promote" if verified else "reject"
    argv = ["decide", ident, "--kind", kind, "--sid", sid, "--line", line, "--by", by]
    if reason_class:
        argv += ["--reason-class", reason_class]
    rc, out, err = cli(R, *argv, *extra)
    return rc, out, err, sid, line


def template(key: str, build) -> tuple[Path, object]:
    """快取樣板：第一次以 `build(R)` 備妥一份 repo，之後每次回傳它的獨立複本與 `build` 的回傳值。"""
    cache = fx._CACHE.setdefault("p2_templates", {})
    if key not in cache:
        src = p2_base()
        extra = build(src)
        store = None
        if transcript_dir(src).is_dir():  # 逐字稿依 repo 路徑 slug 定位：複本要帶一份到自己的 slug
            store = fx.TMP / f"tpl-transcripts-{len(cache)}"
            shutil.copytree(transcript_dir(src), store)
        cache[key] = (src, extra, store)
    src, extra, store = cache[key]
    dest = fx.new_dir("t")
    shutil.copytree(src, dest)
    if store is not None:
        shutil.copytree(store, transcript_dir(dest), dirs_exist_ok=True)
    return dest, extra


# --------------------------------------------------------------------------- held-out
# 與探針夾具（§5.4）
_PRELUDE = (
    "import sys\n"
    "def _count(root, target, counter=None):\n"
    "    import os\n"
    "    if counter:\n"
    "        open(counter, 'a').write('x\\n')\n"
    "    path = os.path.join(root, target)\n"
    "    text = open(path, encoding='utf-8').read() if os.path.isfile(path) else ''\n"
    "    present = 'FIXED-LINE' not in text\n"
    "    print('symptom=present' if present else 'symptom=absent')\n"
    "    return 1 if present else 0\n"
)
_HANG = (
    "import subprocess, sys, time\n"
    "hb, pidfile = sys.argv[2], sys.argv[3]\n"
    "child = subprocess.Popen([sys.executable, '-c', 'import time\\n"
    "while True:\\n open(%r,\"ab\").write(b\"x\")\\n time.sleep(0.1)' % hb])\n"
    "open(pidfile, 'w').write(str(child.pid))\n"
    "time.sleep(600)\n"
)
PROBE_SCRIPTS = {
    "probe_count.py": _PRELUDE + "sys.exit(_count(sys.argv[1], sys.argv[2], *sys.argv[3:4]))\n",
    "probe_exists.py": (
        "import os, sys\n"
        "if len(sys.argv) > 3:\n    open(sys.argv[3], 'a').write('x\\n')\n"
        "sys.exit(0 if os.path.exists(os.path.join(sys.argv[1], sys.argv[2])) else 1)\n"),
    "probe_mem.py": (
        "import os, sys\n"
        "if len(sys.argv) > 2:\n    open(sys.argv[2], 'a').write('x\\n')\n"
        "p = os.path.join(sys.argv[1], 'memory', 'feedback_demo.md')\n"
        "ok = os.path.isfile(p) and 'FIXED-MEM' in open(p, encoding='utf-8').read()\n"
        "sys.exit(0 if ok else 1)\n"),
    "probe_always_ok.py": "import sys\nsys.exit(0)\n",
    "probe_always_red.py": "import sys\nsys.exit(1)\n",
    "probe_slow.py": (_PRELUDE + "import time\ntime.sleep(float(sys.argv[3]))\n"
                      "sys.exit(_count(sys.argv[1], sys.argv[2]))\n"),
    "probe_hang.py": _HANG,
    "probe_hang_fixed.py": (
        "import os, sys\n"
        "path = os.path.join(sys.argv[1], 'docs/notes/demo.md')\n"
        "text = open(path, encoding='utf-8').read() if os.path.isfile(path) else ''\n"
        "if 'FIXED-LINE' not in text:\n    print('symptom=present')\n    sys.exit(1)\n"
    ) + _HANG.replace("hb, pidfile = sys.argv[2], sys.argv[3]",
                                               "hb, pidfile = sys.argv[3], sys.argv[4]"),
    "probe_hang_mutated.py": (
        "import os, sys\n"
        "path = os.path.join(sys.argv[1], 'docs/notes/demo.md')\n"
        "text = open(path, encoding='utf-8').read() if os.path.isfile(path) else ''\n"
        "if 'MUTATED-MARK' in text:\n    pass\n"
        "elif 'FIXED-LINE' in text:\n    sys.exit(0)\n"
        "else:\n    sys.exit(1)\n") + _HANG.replace(
            "hb, pidfile = sys.argv[2], sys.argv[3]", "hb, pidfile = sys.argv[3], sys.argv[4]"),
    "probe_flags.py": _PRELUDE + (
        "print('isolated=%s safe_path=%s'\n"
        "      % (sys.flags.isolated, getattr(sys.flags, 'safe_path', 0)))\n"
        "sys.exit(_count(sys.argv[1], sys.argv[2]))\n"),
    "probe_env.py": _PRELUDE + (
        "import os\n"
        "print('PYTHONPATH=' + os.environ.get('PYTHONPATH', ''))\n"
        "names = sorted(k for k in os.environ if k.startswith('AUTOSDD_'))\n"
        "print('AUTOSDD_NAMES=' + ','.join(names))\n"
        "print('HAS_SECRET=' + str('MY_SECRET_TOKEN' in os.environ))\n"
        "print('PYTHONUTF8=' + os.environ.get('PYTHONUTF8', ''))\n"
        "print('PYTHONDONTWRITEBYTECODE=' + os.environ.get('PYTHONDONTWRITEBYTECODE', ''))\n"
        "sys.exit(_count(sys.argv[1], sys.argv[2]))\n"),
    "probe_secrets.py": _PRELUDE + (
        "print('Authorization: Bearer abcdef0123456789abcdef')\n"
        "print('key=' + 's' + 'k-' + 'ABCDEF0123456789abcdef')\n"
        "print('Authorization: Basic dXNlcjpwYXNzd29yZA==')\n"
        "print('postgres://admin:s3cr3tpw@db.example/x')\n"
        "sys.exit(_count(sys.argv[1], sys.argv[2]))\n"),
    "probe_noisy.py": _PRELUDE + (
        "import random\n"
        "print('MIDDLE-MARKER-%d' % random.Random(7).randint(10**8, 10**9))\n"
        "print('p' * 1500)\n"
        "sys.stderr.write('stderr line\\n')\n"
        "print('結' * 133 + '束')\n"
        "sys.exit(_count(sys.argv[1], sys.argv[2]))\n"),
    "probe_big.py": ("import sys\nsys.stdout.write('A' * 2000000)\nsys.stdout.flush()\n"
                     "import os\np = os.path.join(sys.argv[1], sys.argv[2])\n"
                     "text = open(p, encoding='utf-8').read() if os.path.isfile(p) else ''\n"
                     "sys.exit(1 if 'FIXED-LINE' not in text else 0)\n"),
}


def patched_text(target: str = "docs/notes/demo.md") -> str:
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    """套用 `modify` 提案 patch（第 50 行後插入 `FIXED-LINE`）之後的 `target` 內容。"""
    lines = fx.fixture_files()[target].splitlines(keepends=True)
    return "".join(lines[:50] + ["FIXED-LINE\n"] + lines[50:])


def mutation_patch(kind, target: str = "docs/notes/demo.md") -> bytes:
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    """`True`＝移除 `FIXED-LINE` 的反向 diff；`"noop"`＝改別行；`"mark"`＝換成 `MUTATED-MARK`。"""
    cur = patched_text(target)
    if kind == "noop":
        return fx.patch_diff(target, cur, cur.replace("line 003", "line 003 noop", 1))
    base = fx.fixture_files()[target]
    if kind == "mark":
        return fx.patch_diff(target, cur, cur.replace("FIXED-LINE\n", "MUTATED-MARK\n"))
    return fx.patch_diff(target, cur, base)


def _probe_entry(name: str, probes: str, target: str, counter, delay, module, n_pop: int) -> list:
    py = "{python}"
    script = "{heldout}/" + PROBE_SCRIPTS_BY_KIND[probes]
    argv = [py, script, "{sandbox}", target]
    if probes in ("exists",):
        argv = [py, script, "{sandbox}", target]
    elif probes == "mem":
        argv = [py, script, "{sandbox}"]
    elif probes in ("always_ok", "always_red"):
        argv = [py, script]
    elif probes == "slow":
        argv = [py, script, "{sandbox}", target, str(delay)]
    elif probes == "hang":
        argv = [py, script, "{sandbox}", "{heldout}/hb", "{heldout}/pidfile"]
    elif probes in ("hang_fixed", "hang_mutated"):
        argv = [py, script, "{sandbox}", target, "{heldout}/hb", "{heldout}/pidfile"]
    if counter is not None and probes in ("count", "exists", "mem"):
        argv.append(str(counter))
    entry = {"id": f"p-{name}", "argv": argv, "n_pop": n_pop}
    if module:
        entry["module"] = module
    return [entry]


PROBE_SCRIPTS_BY_KIND = {
    "count": "probe_count.py", "exists": "probe_exists.py", "mem": "probe_mem.py",
    "always_ok": "probe_always_ok.py", "always_red": "probe_always_red.py",
    "slow": "probe_slow.py", "hang": "probe_hang.py", "hang_fixed": "probe_hang_fixed.py",
    "hang_mutated": "probe_hang_mutated.py", "flags": "probe_flags.py", "env": "probe_env.py",
    "secrets": "probe_secrets.py", "noisy": "probe_noisy.py", "big": "probe_big.py",
}


def make_heldout(dest: Path, *, cases: int = 5, probes: str = "count", mutation=True,
                 target: str = "docs/notes/demo.md", counter=None, delay: float = 1,
                 module: str | None = None, n_pop: int = 5) -> Path:
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    """在 `dest`（tmp 內、家目錄之外）寫一個 held-out 目錄：`manifest.json`、探針腳本、
    `mutation.patch` 與子目錄 `data/` 內的一個檔（供「遞迴複製」斷言）。"""
    dest.mkdir(parents=True)
    (dest / "data").mkdir()
    (dest / "data" / "sample.txt").write_bytes("樣本\r\n二".encode())
    for name, text in PROBE_SCRIPTS.items():
        (dest / name).write_bytes(text.encode("utf-8"))
    manifest = {
        "schema_rev": 1,
        "cases": [{"id": f"c{k}", "ref": fx.obs_id(1 + k % 10)} for k in range(cases)],
        "probes": ([] if probes == "none"
                   else _probe_entry("a", probes, target, counter, delay, module, n_pop)),
    }
    if mutation is not None and mutation is not False:
        kind = "mark" if probes == "hang_mutated" else mutation
        patch = (fx.patch_del(target, old="FIXED-LINE\n") if probes == "exists"
                 else mutation_patch(kind, target))
        (dest / "mutation.patch").write_bytes(patch)
        manifest["mutation"] = "mutation.patch"
    (dest / "manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return dest


def manifest_raw(root: Path) -> str:
    """R84 原始位元組式的獨立實作（不 import 被測的 `manifest.py`）。"""
    import hashlib

    rows = sorted(((p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
                   for p in root.rglob("*") if p.is_file()), key=lambda x: x[0].encode())
    text = "".join(f"{rel}\t{h}\n" for rel, h in rows)
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def snapshot_tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
            if p.is_file()}



# --------------------------------------------------------------------------- COOL-BASE（§5.2）
def cell_time(days_ago: float) -> str:
    """OBS 列 `時間` 欄（帶 offset，丟秒）：現在往前 `days_ago` 日。"""
    z = datetime.now().astimezone() - timedelta(days=days_ago)
    off = z.strftime("%z")
    return f"{z.strftime('%Y-%m-%d %H:%M')} {off[:3]}:{off[3:]}"


def obs_row(n: int, coord: str, days_ago: float = 5, disp: str = "open") -> list[str]:
    return [fx.obs_id(n), cell_time(days_ago), "夾具", f"冷卻夾具症狀 {n}", coord, "bug", "P3",
        disp,
            "面=文件;來源=代理;回報者=QA"]


DEMO = "docs/notes/demo.md"
OTHER = "docs/notes/other.md"
NEW_NOTE = "docs/notes/new_note.md"


def attr_root(R: Path, n: int, aid_n: int, cause: str = "docs/stale-note", *, confirm=True) -> None:
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    rc, out, err = cli(R, "attr", "--type", "root", "--by", "SA", "--obs", fx.obs_id(n), "--item",
                       "DOC=docs/06_quality/", "--root-cause", cause)
    assert rc == 0, out + err
    if confirm:
        rc, out, err = cli(R, "attr-confirm", "--att", fx.aid(aid_n), "--by", "QA")
        assert rc == 0, out + err


def cool_base(*, reject_class: str = "證據不足", rows=(), kind: str = "reject",
              extra_attrs=()) -> tuple[Path, str]:
    """`COOL-BASE`：O1、O2（證據 demo.md:12）與 O3（other.md:7），O1、O3 的 attr 皆已確認；
    PROP A（cls D、target demo.md、sources O1）被 `dec(reject|return)`。回 (repo, A)。"""
    base = [obs_row(11, f"{DEMO}:12"), obs_row(12, f"{DEMO}:12"), obs_row(13, f"{OTHER}:7"),
            *rows]
    R = make_p2_repo(fx.new_dir("cool"), extra_obs=base)
    run = open_run(R)
    attr_root(R, 11, 1)
    attr_root(R, 13, 2)
    for spec in extra_attrs:
        attr_root(R, *spec[:2], **(spec[2] if len(spec) > 2 else {}))
    rc, out, err = cli(R, "prop-new", "--run", run, *fx.good_prop_args(
        R, "D", patch=_modify_patch(DEMO), target=[DEMO], sources=[fx.obs_id(11)]))
    assert rc == 0, out + err
    a = re.search(r"id=(\S+)", out).group(1)
    pe = prop_event(R, a)
    body = {"prop": a, "dkind": kind, "digest": pe["digest"], "reason": "夾具理由",
            "reason_class": reject_class}
    fx.append_events(R, [fx.ev("dec", "掌舵者", **body)])
    return R, a


def new_try(R: Path, sources, *, cls: str = "D", target: str = DEMO, response: bool = False,
            run: str | None = None) -> tuple[int, str, str]:
    """對 `R` 呼叫 `prop-new`（patch 為 target 第 50 行後插入一行）。"""
    fields = {"reject_response": "逐項回應否決理由：已補上新證據"} if response else {}
    body = fx.body_md("P", **fields)
    patch = _modify_patch(target) if target in fx.fixture_files() else None
    over = {"patch": patch, "target": [target], "sources": list(sources), "body": body}
    return cli(R, "prop-new", "--run", run or open_run(R), *fx.good_prop_args(R, cls, **over))



def prop_event(R: Path, prop: str) -> dict:
    return [e for e in fx.EV(R) if e["kind"] == "prop" and e["id"] == prop][-1]


def hand_to(R: Path, prop: str, state: str, *, verdict: str = "PASS", ack: bool = False,
            rollback_ok: bool = True, touched_ok: bool = True, verify_kw=None) -> None:
    """在 CLI 建好的 PROP（內容檔與卡面皆在）之後，手寫事件把它推到 `verified`／`promoted`。

    `state`＝`verified`（核准→凍結→沙盒→驗證）或 `promoted`（再加 `dec(promote)` 與 `app.promote`）
    ；
    不跑沙盒與驗證本體（那些動詞另有 AT），故不建沙盒樹與 `verifyK.json`。"""
    pe = prop_event(R, prop)
    cards = [e for e in fx.EV(R) if e["kind"] == "card" and e["prop"] == prop]
    seq = cards[-1]["seq"] if cards else 1

    def dec(dkind: str, **kw) -> dict:
        return fx.ev("dec", "掌舵者", prop=prop, dkind=dkind, digest=pe["digest"], card_seq=seq,
                     quote=fx.std_quote(dkind, prop, kw.get("flags") or ()), **kw)

    events = [dec("approve"), fx.ev("heldout.freeze", "FZ", prop=prop),
              fx.ev("app.sandbox", "main", prop=prop, base=pe["base"],
                    rollback_ok=rollback_ok, touched_ok=touched_ok),
              fx.ev("app.verify", "main", prop=prop, verdict=verdict, **(verify_kw or {}))]
    if state == "promoted":
        flags = {"flags": ["unverified_ack"]} if ack else {}
        events += [dec("promote", **flags), fx.ev("app.promote", "main", prop=prop,
                                                  unverified_ack=ack)]
    fx.append_events(R, events)


def drive_to(R: Path, state: str, **kw) -> str:
    """把 `R` 內一個新 PROP 推進到 `state`（`proposed`／`carried`／`approved`…）；回 PROP 號。"""
    keys = ("cls", "action", "target", "route", "proposer", "sources", "patch", "memory", "note")
    prop = new_prop(R, **{k: v for k, v in kw.items() if k in keys})
    if state == "proposed":
        return prop
    issue_card(R, prop)
    if state == "carried":
        return prop
    rc, out, err, _, _ = decide_say(R, prop, f"核准 {prop}")
    assert rc == 0, out + err
    if state == "approved":
        return prop
    if kw.get("cls") == "M":
        default_src = mem_heldout(fx.new_dir("ho"))
    else:
        add = kw.get("action") == "add"
        default_src = make_heldout(fx.new_dir("ho"), probes="exists" if add else "count",
                                   target=kw.get("target") or (NEW_NOTE if add else DEMO))
    src = kw.get("heldout") or default_src
    rc, out, err = cli(R, "heldout-freeze", prop, "--from", src, "--by", "FZ")
    assert rc == 0, out + err
    if state == "frozen":
        return prop
    memory = ["--memory-dir", str(kw["memory"])] if kw.get("memory") else []
    rc, out, err = cli(R, "sandbox", prop, "--by", "SB1", *memory)
    assert rc == 0, out + err
    if state == "sandboxed":
        return prop
    rc, out, err = cli(R, "verify", prop, "--by", "VF1")
    assert rc == 0, out + err
    if state == "verified":
        return prop
    ack = last_event(R, "app.verify")["verdict"] == "NE"
    rc, out, err, _, _ = decide_say(R, prop, f"晉升 {prop}" + (" 未驗採納" if ack else ""))
    assert rc == 0, out + err
    rc, out, err = cli(R, "promote", prop, "--by", "PR1", *memory)
    assert rc == 0, out + err
    return prop  # state == "promoted"



# --------------------------------------------------------------------------- Console 稽核檔（§5.5）
AUDIT_KEY = "si-p2-vector-key-0123456789-abcdefghijklmnopqrstuvwxyz"
AUDIT_TIME = "2026-10-21T09:15:30+08:00"
_UUID_N = [0]


def new_uuid() -> str:
    _UUID_N[0] += 1
    return f"6f1c2a3e-8b4d-4e5f-9a7b-{_UUID_N[0]:012d}"


def _jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _common(ref: str, kind: str, user: str, time: str) -> dict:
    return {"schema_rev": 1, "audit_ref": ref, "kind": kind, "user": user, "role": "ADMIN",
            "time": time}


def body_decide(ref: str, target: str, digest, dkind: str, *, user: str = "ops_admin",
                time: str = AUDIT_TIME, reason_class=None, reason=None, flags=()) -> dict:
    b = _common(ref, "decide", user, time)
    b["run" if dkind == "resume" else "prop"] = target
    if digest is not None:
        b["digest"] = digest
    b["dkind"] = dkind
    for k, v in (("reason_class", reason_class), ("reason", reason)):
        if v is not None:
            b[k] = v
    b["flags"] = list(flags)
    return b


def body_obs_add(ref: str, *, user: str = "admin", time: str = AUDIT_TIME, **over) -> dict:
    b = _common(ref, "obs-add", user, time)
    b.update(context="Console・自我進化頁", symptom="待入帳徽章在入帳後仍顯示",
             evidence="AgentConsole/frontend/components/domain/si/SiView.tsx:88", category="bug",
             severity="P3", face="產品", external_derived=False)
    b.update(over)
    return b


def body_obs_close(ref: str, obs_id: str, disposition: str, *, user: str = "admin",
                   time: str = AUDIT_TIME) -> dict:
    b = _common(ref, "obs-close", user, time)
    b.update(obs_id=obs_id, disposition=disposition)
    return b


def write_audit(home: Path, *, kind: str, ref: str, subject, body, key: str = AUDIT_KEY,
                key_id=None, mac=None, name=None, outer=None):
    """寫 `<home>/console_audit/<name 或 ref>.json`；`mac` 依（變異後的）body 重算，除非明給。
    回 (路徑, audit_sha256)。"""
    import hashlib
    import hmac

    text = body if isinstance(body, str) else _jdump(body)
    kb = key.encode("utf-8")
    obj = {"schema_rev": 1, "kind": kind, "audit_ref": ref, "subject": subject, "body": text,
           "key_id": key_id or hashlib.sha256(kb).hexdigest()[:8],
           "mac": mac or hmac.new(kb, text.encode("utf-8"), hashlib.sha256).hexdigest()}
    for k, v in (outer or {}).items():
        if v is KeyError:
            obj.pop(k, None)
        else:
            obj[k] = v
    path = home / "console_audit" / f"{name or ref}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (_jdump(obj) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return path, "sha256:" + hashlib.sha256(raw).hexdigest()


def forge_dec(R: Path, prop: str, quote: str, flags=()) -> None:  # noqa: E302
    """手寫追加一筆引言可回查、欄位合法的 `dec`（略過 `decide` 的狀態層前提；逐字稿載體欄位預設）。
    """
    pe = prop_event(R, prop)
    dkind = VERB_KIND[quote.split(" ", 1)[0]]
    extra = {"flags": list(flags)} if flags else {}
    fx.append_events(R, [fx.ev("dec", "掌舵者", prop=prop, dkind=dkind, digest=pe["digest"],
                               quote=quote, **extra)])


def manifest_lf(root: Path, paths, strip: str = "") -> str:
    """R84 LF 正規化式的獨立實作（缺檔記 `absent`；`strip`＝M 類邏輯根前綴；不 import 被測模組）。
    """
    import hashlib

    rows = []
    for rel in sorted(set(paths), key=lambda x: x.encode()):
        p = root / (rel[len(strip):] if strip and rel.startswith(strip) else rel)
        h = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() \
            if p.is_file() else "absent"
        rows.append(f"{rel}\t{h}\n")
    return "sha256:" + hashlib.sha256("".join(rows).encode()).hexdigest()


def codes(res: dict, item: str) -> set[str]:
    return {code for _, code in _findings(res, item)}


def _findings(res: dict, item: str):
    return {(f["subject"], f["code"]) for f in res["_item"][item]["findings"]}


__all__ = [
    "make_p2_repo", "p2_base", "verified_chain", "promoted_chain", "sc_p2_legal", "codes", "pid",
    "RUN_EVENTS",
]
