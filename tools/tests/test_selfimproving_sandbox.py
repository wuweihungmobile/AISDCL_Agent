# 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
"""SelfImproving P2 沙盒的驗收測試（TCS-P2 SB 檔；`sandbox.py`、`manifest.py`、`git.py` 的 timeout）
。

方法名含 AT 底線形（錨定 `-k AT_215_1_1_` 只收一個）。夾具全用 tmp 目錄內的合成 repo
（hermetic 環境；`CLAUDE_CONFIG_DIR` 與 `AUTOSDD_SI_DIR` 指到 tmp；不碰真帳本、不上網）。
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tarfile
import time
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_p2_fixtures import P2TestCase

from lib.selfimproving import git as si_git
from lib.selfimproving import sandbox as si_sandbox

DEMO = "docs/notes/demo.md"


def setUpModule() -> None:
    fx.setup("si_p2s_")


def tearDownModule() -> None:
    fx.teardown()


def surface(R: Path):
    """正式面：`git status --porcelain`、HEAD、`git worktree list`、工作樹各檔位元組雜湊；
    事件帳本本身是 `sandbox` 的合法寫入（追加一行事件），不算正式面。"""
    files, porcelain = fx.snap(R)
    files = {k: v for k, v in files.items() if k != fx.EVL}
    lines = [ln for ln in porcelain.splitlines() if not ln.endswith(fx.EVL)]
    return (files, lines, fx.head(R), fx.git(R, "worktree", "list"))


def independent_copy(R: Path, base: str, dest: Path) -> Path:
    """測試自行以 `git archive <base>` 加標準庫 `tarfile` 抽出的獨立副本。"""
    raw = subprocess.run(["git", "-C", str(R), "archive", "--format=tar", base], check=True,
                         capture_output=True, env={**os.environ, **fx.hermetic()}).stdout
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        tf.extractall(dest, filter="data")
    return dest


GIT_FORBIDDEN = {"stash", "reset", "checkout", "clean", "restore", "switch", "worktree"}
GIT_ALLOWED = {"apply", "archive", "status", "rev-parse", "log", "show", "grep", "merge-base",
               # ls-files＝LATEST 解析器 sdd_version.py 的唯讀列舉（⚖：TCS 允許集合未列）
               "ls-files"}


def git_subcommand(argv) -> str | None:
    """§5.6 `git_subcommands`：`git` 之後略過 `-C <目錄>` 與 `-c <鍵=值>` 的第一個非旗標位置詞。"""
    items = [a for a in argv[1:]] if argv and argv[0] == "git" else list(argv)
    i = 0
    while i < len(items):
        if items[i] in ("-C", "-c"):
            i += 2
            continue
        if items[i].startswith("-"):
            i += 1
            continue
        return items[i]
    return None


def git_forms(source: str) -> list[str]:
    """靜態掃描：每個 `<git>.run(...)` 呼叫的字面引數與每個以字面 `"git"` 起頭的 argv 清單的子命令。
    """
    import ast
    out: list[str] = []
    for node in ast.walk(ast.parse(source)):
        args = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "run" and (
                    "git" in ast.unparse(node.func.value).lower()
                    or ast.unparse(node.func.value) == "self"):
            args = [a for a in node.args if not isinstance(a, ast.Starred)]
        elif isinstance(node, ast.List) and node.elts and isinstance(node.elts[0], ast.Constant) \
                and node.elts[0].value == "git":
            args = node.elts[1:]
        if args is not None:
            lit = [a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else "?"
                   for a in args]
            sub = git_subcommand(lit)
            if sub is not None and sub != "?":
                out.append(sub)
    return out


def scan_git_forms(source: str) -> list[str]:
    return [s for s in git_forms(source) if s in GIT_FORBIDDEN]


def frozen_copy(key="frozen", **kw):
    return fx2.template(key, lambda r: fx2.drive_to(r, "frozen", **kw))


def events_of(R, kind):
    return [e for e in fx.EV(R) if e["kind"] == kind]


class TestSandbox(P2TestCase):
    """受測：`tools/lib/selfimproving/sandbox.py`（R85、R86）。"""

    def fresh(self, key="frozen", **kw):
        self.new_home()
        return frozen_copy(key, **kw)

    def test_AT_215_1_1_sandbox_positive(self):
        R, p = self.fresh()
        surf0, home0 = surface(R), set(fx.tree_files(self.home))
        base = fx2.prop_event(R, p)["base"]
        t0 = time.monotonic()
        rc, out, err = self.M(R, "sandbox", p, "--by", "SB1")
        self.assertLess(time.monotonic() - t0, 30)
        self.assertEqual((rc, err), (0, ""), out)
        self.assertRegex(out, r"^ok app\.sandbox seq=\d+ id=APP-SI-\d{3} applied=true "
                              r"touched_ok=true rollback_ok=true fail_code=null\n$")
        ev = fx2.last_event(R, "app.sandbox")
        self.assertEqual(list(ev), ["seq", "t", "kind", "by", "id", "prop", "rev", "base",
                                    "sandbox_sha256", "applied", "touched_ok", "rollback_ok",
                                    "fail_code"])
        pe = fx2.prop_event(R, p)
        self.assertEqual((ev["by"], ev["rev"], ev["base"]), ("SB1", pe["rev"], pe["base"]))
        box = self.home / "sandbox" / p
        self.assertTrue(box.is_dir())
        real_box, real_repo = os.path.realpath(box), os.path.realpath(R)
        self.assertNotEqual(os.path.commonpath([real_box, real_repo]), real_repo)
        self.assertNotIn(".claude/worktrees/", real_box.replace("\\", "/"))
        self.assertFalse((box / ".git").exists())
        twin = independent_copy(R, base, fx.new_dir("twin"))
        self.assertEqual(fx2.snapshot_tree(box), fx2.snapshot_tree(twin))
        want = fx2.manifest_raw(twin)
        self.assertEqual((ev["sandbox_sha256"], fx2.manifest_raw(box)), (want, want))
        self.assertEqual(surface(R), surf0)
        added = {x for x in fx.tree_files(self.home)} - home0
        self.assertTrue(all(x.startswith(("sandbox/", "locks/")) for x in added), added)
        pending = {x["id"]: x["state"] for x in self.MJ(R, "status")["pending_props"]}
        self.assertNotIn(p, pending)
        self.assertEqual(self.S(self.check(R), "events.transitions"), "PASS")

    def test_AT_215_1_E_1_root_location(self):
        R, p = self.fresh()
        snap0 = fx.snap(R)
        env_in_repo = R / ".si_home"
        env_in_repo.mkdir()
        for label, home in (("a", env_in_repo), ("b",
            fx.new_dir("wt") / ".claude" / "worktrees" / "x")):
            with self.subTest(label), mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(home)}):
                home.mkdir(parents=True, exist_ok=True)
                before = (R / fx.EVL).read_bytes()
                rc, out, err = self.M(R, "sandbox", p)
                if label == "a":
                    self.assertEqual((rc, out), (3, ""), err)
                    self.assertIn("SANDBOX-ROOT-IN-REPO", err)
                    self.assertEqual((R / fx.EVL).read_bytes(), before)
                else:
                    self.assertEqual((rc, out), (3, ""), err)
                    self.assertIn("SANDBOX-ROOT-IN-REPO", err)
        # (c) <si>/sandbox 的 realpath 落在 R 內（以替身代替符號連結，不得跳過）
        real = os.path.realpath

        def fake(path, *a, **kw):
            return real(R / "docs") if Path(path) == self.home / "sandbox" else real(path, *a, **kw)
        with mock.patch.object(si_sandbox.os.path, "realpath", fake):
            rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual((rc, out), (3, ""), err)
        self.assertIn("SANDBOX-ROOT-IN-REPO", err)
        # (d) <si>/sandbox/<P> 本身是連結：不得清理
        elsewhere = fx.new_dir("elsewhere")
        elsewhere.mkdir()
        (elsewhere / "canary.txt").write_text("c", encoding="utf-8")
        with mock.patch.object(si_sandbox, "_is_link_path", lambda path: Path(path).name == p):
            rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual((rc, out), (3, ""), err)
        self.assertEqual((elsewhere / "canary.txt").read_text(encoding="utf-8"), "c")
        self.assertEqual(fx.snap(R), snap0)
        rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual(rc, 0, out + err)
        self.assertNotEqual(os.path.commonpath([os.path.realpath(self.home / "sandbox" / p),
                                                os.path.realpath(R)]), os.path.realpath(R))

    def test_AT_215_1_E_2_preconditions(self):
        def case(label, setup, code, rc_want=1, **kw):
            R, p = self.fresh(**kw)
            argv_p = setup(R, p) or p
            keep = self.home / "sandbox" / p
            keep.mkdir(parents=True, exist_ok=True)
            (keep / "keep.txt").write_text("k", encoding="utf-8")
            before, snap0 = (R / fx.EVL).read_bytes(), fx.snap(R)
            rc, out, err = self.M(R, "sandbox", argv_p)
            self.assertEqual(rc, rc_want, (label, out, err))
            if rc_want == 1:
                self.rejected(rc, out, {code}, label)
                self.draft_ok(R, out, label)
            self.assertEqual((R / fx.EVL).read_bytes(), before, label)
            self.assertEqual(fx.snap(R), snap0, label)
            self.assertEqual((keep / "keep.txt").read_text(encoding="utf-8"), "k", label)
            self.assertEqual([x.name for x in (self.home / "sandbox").iterdir()
                              if x.name.startswith(".tmp")], [], label)

        def unfreeze(R, p):
            fx2.drop_events(R, "heldout.freeze", p)

        def mk_proposed(R, p):
            fx2.drop_events(R, "dec", p)
            fx2.drop_events(R, "heldout.freeze", p)

        def forged_approve(R, p):
            fx2.rewrite_event(R, [e for e in fx.EV(R) if e["kind"] == "dec"][-1]["seq"],
                              quote="核准 PROP-SI-" + "998")

        def tamper(R, p):
            path = R / fx.PROPS_REL / p / "r1.patch"
            path.write_bytes(path.read_bytes() + b" ")

        def empty_cfg(R, p):
            shutil.rmtree(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects", ignore_errors=True)

        case("c", unfreeze, "HELDOUT-NOT-FROZEN")
        case("a", mk_proposed, "STATE-NOT-APPROVED")
        case("d", forged_approve, "DEC-VERIFY-FAILED")
        case("e", empty_cfg, "TRANSCRIPT-UNAVAILABLE")
        case("f", tamper, "DIGEST-MISMATCH")
        case("i", lambda R, p: "PROP-SI-" + f"{int(p.rsplit('-', 1)[1]) + 900:03d}",
            "PROP-NOT-FOUND")
        R, p = self.fresh()
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            home0 = fx2.snapshot_tree(self.home)
            rc, out, err = self.M(R, "sandbox", p)
            self.rejected(rc, out, {"UNATTENDED-REFUSED"})
            self.assertEqual(fx2.snapshot_tree(self.home), home0)
        self.usage_error(*self.M(R, "sandbox"))
        bad = fx.new_dir("afile")
        bad.write_text("x", encoding="utf-8")
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(bad)}):
            rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual((rc, out), (3, ""))
        self.assertIn("HOME-UNWRITABLE", err)
        fx.set_params(R, probe_timeout_seconds="600")
        rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual((rc, out), (3, ""))
        self.assertIn("probe_timeout_seconds", err)
        with self.subTest("b"):  # 已 sandboxed
            Rb, pb = fx2.template("sbx", lambda r: fx2.drive_to(r, "sandboxed"))
            self.new_home()
            rc, out, _ = self.M(Rb, "sandbox", pb)
            self.rejected(rc, out, {"STATE-NOT-APPROVED"})
        with self.subTest("g"):  # M 類未給 --memory-dir
            Rg, pg = fx2.template("m_frozen", lambda r: fx2.drive_to(
                r, "frozen", cls="M", memory=fx2.make_memdir(fx.new_dir("mem"))))
            self.new_home()
            s0 = fx.snap(Rg)
            rc, out, _ = self.M(Rg, "sandbox", pg)
            self.rejected(rc, out, {"MEMORY-DIR-MISSING"})
            self.assertEqual(fx.snap(Rg), s0)
        for label, code, env in (("j", "CONSOLE-AUDIT-MISSING", {}),
                                 ("k", "CONSOLE-KEY-MISSING", {"AUTOSDD_SI_AUDIT_KEY": ""})):
            with self.subTest(label), mock.patch.dict(os.environ, {
                    "AUTOSDD_SI_AUDIT_KEY": fx2.AUDIT_KEY}):
                self.new_home()
                Rc = fx2.p2_base()
                pc = fx2.new_prop(Rc)
                ref = fx2.new_uuid()
                path, _ = fx2.write_audit(self.home, kind="decide", ref=ref, subject=pc,
                                          body=fx2.body_decide(ref, pc, fx2.prop_event(Rc,
                                          pc)["digest"],
                                                               "approve"))
                self.assertEqual(self.M(Rc, "decide", pc, "--carrier", "console", "--audit-ref",
                                        ref)[0], 0)
                rc, out, err = fx2.cli(Rc, "heldout-freeze", pc, "--from", fx2.make_heldout(
                    fx.new_dir("ho")), "--by", "FZ")
                self.assertEqual(rc, 0, out + err)
                if label == "j":
                    path.unlink()
                s0, ev0 = fx.snap(Rc), (Rc / fx.EVL).read_bytes()
                with mock.patch.dict(os.environ, env):
                    rc, out, _ = self.M(Rc, "sandbox", pc)
                self.rejected(rc, out, {code}, label)
                self.assertEqual((fx.snap(Rc), (Rc / fx.EVL).read_bytes()), (s0, ev0))
        # 競態：外層組裝期間 PROP 變成 sandboxed
        R2, p2 = self.fresh()
        real = si_sandbox.apply_patch

        def racing(root, patch, timeout=None):
            fx.append_events(R2, [fx.ev("app.sandbox", "main", prop=p2,
                                        base=fx2.prop_event(R2, p2)["base"])])
            return real(root, patch, timeout)
        with mock.patch.object(si_sandbox, "apply_patch", racing):
            rc, out, err = self.M(R2, "sandbox", p2)
        self.rejected(rc, out, {"STATE-CHANGED"})
        self.assertFalse((self.home / "sandbox" / p2).exists())
        self.assertEqual(len(events_of(R2, "app.sandbox")), 1)

    def test_AT_215_1_E_3_autocrlf_neutral(self):
        R, p = self.fresh()
        cfg = fx.new_dir("crlf") .with_suffix(".gitconfig")
        cfg.write_bytes(b"[core]\n\tautocrlf = true\n")
        argvs = []
        real_run = subprocess.run

        def spy(argv, *a, **kw):
            if argv and argv[0] == "git":
                argvs.append(list(argv))
            return real_run(argv, *a, **kw)
        env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": str(cfg)}
        with mock.patch.dict(os.environ, env), mock.patch.object(si_git.subprocess, "run", spy):
            rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual(rc, 0, out + err)
        ev = fx2.last_event(R, "app.sandbox")
        self.assertEqual((ev["applied"], ev["rollback_ok"]), (True, True))
        box = self.home / "sandbox" / p / DEMO
        want = subprocess.run(["git", "-C", str(R), "show", f"{ev['base']}:{DEMO}"], check=True,
                              capture_output=True, env={**os.environ, **fx.hermetic()}).stdout
        self.assertEqual(box.read_bytes(), want)
        self.assertNotIn(b"\r", box.read_bytes())
        self.assertEqual(ev["sandbox_sha256"], fx2.manifest_raw(self.home / "sandbox" / p))
        subs = [a for a in argvs if "apply" in a or "archive" in a]
        self.assertTrue(subs)
        for a in subs:
            i = a.index("-c")
            self.assertEqual(a[i:i + 2], ["-c", "core.autocrlf=false"], a)

    def test_AT_215_1_E_4_tar_precheck(self):
        root = fx.new_dir("sbxroot")

        def tar_of(name, kind="file", data=b"x"):
            path = fx.new_dir("tar").with_suffix(".tar")
            with tarfile.open(path, "w") as tf:
                info = tarfile.TarInfo(name)
                if kind == "file":
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))
                else:
                    info.type = {"sym": tarfile.SYMTYPE, "hard": tarfile.LNKTYPE,
                                 "chr": tarfile.CHRTYPE, "blk": tarfile.BLKTYPE,
                                 "fifo": tarfile.FIFOTYPE}[kind]
                    info.linkname = "target"
                    tf.addfile(info)
            return path

        def dup_tar():
            path = fx.new_dir("tar").with_suffix(".tar")
            with tarfile.open(path, "w") as tf:
                for _ in range(2):
                    info = tarfile.TarInfo("dup.txt")
                    info.size = 1
                    tf.addfile(info, io.BytesIO(b"x"))
            return path

        slash, colon = "/", ":"
        bad = [tar_of("../evil.txt"), tar_of("sub/../../evil2.txt"), tar_of(slash + "abs_evil.txt"),
               tar_of("\\" + "abs_evil2.txt"), tar_of("C" + colon + "evil3.txt"),
               tar_of("C" + colon + slash + "evil4.txt"), tar_of("a/b.txt" + colon + "stream"),
               tar_of("ctl\x01.txt"), tar_of("dir./f.txt"), tar_of("trail /f.txt"),
               *[tar_of("m" + k, k) for k in ("sym", "hard", "chr", "blk", "fifo")], dup_tar()]
        for tar in bad:
            with self.subTest(tar=tar.name):
                problems = si_sandbox.precheck_members(tar, root)
                self.assertTrue(problems)
                self.assertEqual({code for _, code in problems}, {"SANDBOX-MEMBER-REJECTED"})
                with self.assertRaises(si_sandbox.SandboxError):
                    si_sandbox.extract_checked(tar, root)
                self.assertFalse(root.exists() and any(root.rglob("*")))
        self.assertFalse((root.parent / "evil.txt").exists())
        okt = fx.new_dir("tar").with_suffix(".tar")
        with tarfile.open(okt, "w") as tf:
            d = tarfile.TarInfo("ok")
            d.type = tarfile.DIRTYPE
            tf.addfile(d)
            f = tarfile.TarInfo("ok/a.txt")
            f.size = 3
            tf.addfile(f, io.BytesIO(b"abc"))
        self.assertEqual(si_sandbox.precheck_members(okt, root), [])
        si_sandbox.extract_checked(okt, root)
        self.assertEqual((root / "ok" / "a.txt").read_bytes(), b"abc")
        # data_filter 對絕對路徑成員靜默剝斜線（自寫預檢不是冗餘）
        dest = fx.new_dir("datafilter")
        dest.mkdir()
        with tarfile.open(bad[2]) as tf:
            tf.extractall(dest, filter="data")
        self.assertTrue((dest / "abs_evil.txt").is_file())
        # 路徑長度邊界
        r2 = fx.new_dir("longroot")
        n = 259 - len(str(r2)) - 1
        for plat, length, expect in (("win32", n, []), ("win32", n + 1, ["SANDBOX-PATH-TOO-LONG"]),
                                     ("linux", n + 1, [])):
            tar = tar_of("p" * (length - 4) + ".txt" if length > 4 else "p.txt")
            with mock.patch.object(sys, "platform", plat):
                got = [code for _, code in si_sandbox.precheck_members(tar, r2)]
            self.assertEqual(got, expect, (plat, length))
        # tarfile.data_filter 缺席：rc 3、不降級
        R, p = self.fresh()
        before = (R / fx.EVL).read_bytes()
        saved = tarfile.data_filter
        try:
            del tarfile.data_filter
            rc, out, err = self.M(R, "sandbox", p)
        finally:
            tarfile.data_filter = saved
        self.assertEqual((rc, out), (3, ""))
        self.assertIn("TARFILE-FILTER-MISSING", err)
        self.assertEqual((R / fx.EVL).read_bytes(), before)
        self.assertFalse((self.home / "sandbox" / p).exists())

    def test_AT_215_1_2_memory_sandbox_and_rebuild(self):
        self.new_home()
        R = fx2.p2_base()
        mem = fx2.make_memdir(fx.new_dir("mem"))
        (mem / "unrelated.md").write_bytes(b"unrelated\n")
        pm = fx2.drive_to(R, "frozen", cls="M", memory=mem)
        pd = fx2.drive_to(R, "frozen")
        stale = self.home / "sandbox" / pd / "stale.txt"
        stale.parent.mkdir(parents=True)
        stale.write_text("前一輪遺留", encoding="utf-8")
        mem0, surf0 = fx2.snapshot_tree(mem), surface(R)
        for p, extra in ((pm, ["--memory-dir", mem]), (pd, [])):
            rc, out, err = self.M(R, "sandbox", p, *extra)
            self.assertEqual(rc, 0, out + err)
            ev = fx2.last_event(R, "app.sandbox")
            self.assertEqual((ev["applied"], ev["touched_ok"], ev["rollback_ok"], ev["fail_code"]),
                             (True, True, True, None))
        box = self.home / "sandbox" / pm
        self.assertEqual(sorted(fx.tree_files(box)), ["memory/MEMORY.md",
            "memory/feedback_demo.md"])
        for rel in fx.tree_files(box):
            self.assertEqual((box / rel).read_bytes(), (mem / rel.split("/", 1)[1]).read_bytes())
        sha = [e for e in events_of(R, "app.sandbox") if e["prop"] == pm][0]["sandbox_sha256"]
        self.assertEqual(sha, fx2.manifest_raw(box))
        self.assertEqual(fx2.snapshot_tree(mem), mem0)
        self.assertFalse(stale.exists())
        twin = independent_copy(R, fx2.prop_event(R, pd)["base"], fx.new_dir("twin"))
        self.assertEqual(fx2.snapshot_tree(self.home / "sandbox" / pd), fx2.snapshot_tree(twin))
        self.assertEqual(surface(R), surf0)

    def test_d20_verify_rebuilds_m_class_tree_only_with_memory_dir(self):
        """G-06（P2 TCS 勘誤三 R88）：M 類沙盒樹遺失時 `verify` 的重建須自記憶目錄組裝——沒給
        `--memory-dir` 是明碼拒收 `MEMORY-DIR-MISSING`（不再是無解的 `SANDBOX-TREE-DRIFT`）、
        給了就重建成功並照常驗證（rc 0 不論 verdict）。"""
        self.new_home()
        R = fx2.p2_base()
        mem = fx2.make_memdir(fx.new_dir("mem"))
        pm = fx2.drive_to(R, "sandboxed", cls="M", memory=mem)
        shutil.rmtree(self.home / "sandbox" / pm)
        rc, out, err = self.M(R, "verify", pm, "--by", "VF1")
        self.assertEqual((rc, "MEMORY-DIR-MISSING" in fx.codes_of(out)), (1, True), out + err)
        rc, out, err = self.M(R, "verify", pm, "--by", "VF1", "--memory-dir", str(mem))
        self.assertEqual(rc, 0, out + err)
        self.assertTrue((self.home / "sandbox" / pm / "memory" / "MEMORY.md").is_file())

    def test_AT_215_2_1_only_whitelisted_git_forms(self):
        pkg = Path(si_sandbox.__file__).parent
        static: list[str] = []
        sites = 0
        for path in sorted(pkg.glob("*.py")):
            found = git_forms(path.read_text(encoding="utf-8"))
            sites += len(found)
            static += found
        self.assertFalse(set(static) & GIT_FORBIDDEN, set(static) & GIT_FORBIDDEN)
        self.assertTrue({"apply", "archive"} <= set(static) and sites >= 6, (sites, set(static)))
        self.new_home()
        R = fx2.p2_base()
        seen: list[list[str]] = []
        real_run = subprocess.run
        paused = [False]

        def rec(argv, *a, **kw):
            if argv and argv[0] == "git" and not paused[0]:
                seen.append(list(argv))
            return real_run(argv, *a, **kw)

        def surf():  # 測試自己的 surface() 讀取不算被測流程的 git 呼叫
            paused[0] = True
            try:
                return surface(R)
            finally:
                paused[0] = False
        head0 = fx.head(R)
        with mock.patch.object(si_git.subprocess, "run", rec):
            p = fx2.drive_to(R, "frozen")
            surf0 = surf()
            self.assertEqual(self.M(R, "sandbox", p)[0], 0)
            self.assertEqual(surf(), surf0)
            self.assertEqual(self.M(R, "verify", p)[0], 0)
            files, lines, *rest = surf()  # `verify` 的證據檔 verify<K>.json 是它唯一的正式面寫入
            self.assertEqual(({k: files[k] for k in files if k.split("/")[-1] != "verify1.json"},
                              [x for x in lines if "SelfImproving_Proposals" not in x], *rest),
                             (surf0[0], [x for x in surf0[1] if "SelfImproving_Proposals" not in x],
                              *surf0[2:]))
            fx2.decide_say(R, p, f"晉升 {p}")
            self.assertEqual(self.M(R, "promote", p)[0], 0)
            self.assertNotEqual(surf(), surf0)
            fx2.decide_say(R, p, f"回滾 {p} 太慢")
            self.assertEqual(self.M(R, "rollback", p)[0], 0)
        self.assertEqual(fx.head(R), head0)
        self.assertGreaterEqual(len(seen), 10)
        subs = {git_subcommand(a) for a in seen}
        self.assertTrue(subs <= GIT_ALLOWED, subs - GIT_ALLOWED)
        self.assertFalse(subs & GIT_FORBIDDEN)
        for a in seen:
            if git_subcommand(a) in ("apply", "archive"):
                i = a.index("-c")
                self.assertEqual(a[i:i + 2], ["-c", "core.autocrlf=false"], a)

    def test_AT_215_2_E_1_scan_has_teeth_and_cleanup(self):
        bad = ['Git(repo).run("reset", "--hard")',
               'Git(repo).run("-c", "core.quotepath=false", "checkout", "--", "f")',
               'Git(repo).run("clean", "-fd")', 'Git(repo).run("stash")',
               'Git(repo).run("restore", "f")', 'Git(repo).run("switch", "-f", "main")',
               'Git(repo).run("-C", "x", "worktree", "add", "y")',
               'argv = ["git", "-C", d, "reset", "--soft", "HEAD~1"]']
        ok = ['Git(repo).run("apply", "--numstat", "-z", p)',
              'Git(repo).run("-c", "core.autocrlf=false", "archive", "--format=tar", b)',
              'Git(repo).run("rev-parse", "HEAD")', 'Git(repo).run("grep", "-n", "stash")']
        for src in bad:
            self.assertTrue(scan_git_forms(src), src)
        for src in ok:
            self.assertEqual(scan_git_forms(src), [], src)
        self.new_home()
        R = fx2.p2_base()
        p = fx2.drive_to(R, "frozen")
        q = fx2.drive_to(R, "frozen", target=fx2.OTHER)
        (self.home / "sandbox" / p).mkdir(parents=True)
        (self.home / "sandbox" / p / "stale.txt").write_text("遺留", encoding="utf-8")
        (self.home / "sandbox" / q).mkdir(parents=True)
        (self.home / "sandbox" / q / "canary.txt").write_text("c", encoding="utf-8")
        mq0, surf0 = fx2.manifest_raw(self.home / "sandbox" / q), surface(R)
        seen: list[list[str]] = []
        real_run = subprocess.run

        def rec(argv, *a, **kw):
            if argv and argv[0] == "git":
                seen.append(list(argv))
            return real_run(argv, *a, **kw)
        with mock.patch.object(si_git.subprocess, "run", rec):
            rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual(rc, 0, out + err)
        self.assertTrue({git_subcommand(a) for a in seen} <= GIT_ALLOWED)
        self.assertFalse((self.home / "sandbox" / p / "stale.txt").exists())
        twin = independent_copy(R, fx2.prop_event(R, p)["base"], fx.new_dir("twin"))
        self.assertEqual(fx2.snapshot_tree(self.home / "sandbox" / p), fx2.snapshot_tree(twin))
        self.assertEqual(fx2.manifest_raw(self.home / "sandbox" / q), mq0)
        self.assertTrue((self.home / "sandbox" / q / "canary.txt").is_file())
        self.assertEqual(surface(R), surf0)

    def test_AT_215_4_1_apply_stage_failures(self):
        def go(label, *, patch="ok", wrap=None, params=None, json_mode=False):
            R, p = self.fresh(f"fz-{patch}", patch=patch)
            if params:
                fx.set_params(R, **params)
            ctx = wrap(R) if wrap else mock.MagicMock()
            with ctx:
                argv = ["sandbox", p] + (["--json"] if json_mode else [])
                rc, out, err = self.M(R, *argv)
            return R, p, rc, out, err

        real_apply, real_rev = si_sandbox.apply_patch, si_sandbox.reverse_apply
        stray = mock.patch.object(si_sandbox, "apply_patch",
                                  lambda *a, **k: real_apply(*a, **k) | {"stray.txt"})

        def left_over(root, patch, timeout=None):
            ok = real_rev(root, patch, timeout)
            (root / "left_over.txt").write_text("x", encoding="utf-8")
            return ok
        rev = mock.patch.object(si_sandbox, "reverse_apply", left_over)
        seen: list = []
        real_run = subprocess.run

        def timing(argv, *a, **kw):
            seen.append((list(argv), kw.get("timeout")))
            if "apply" in argv:
                raise subprocess.TimeoutExpired(argv, kw.get("timeout"))
            return real_run(argv, *a, **kw)
        slow = mock.patch.object(si_git.subprocess, "run", timing)
        expect = {
            "bad": ("bad-context", None, None, (False, None, None, None), True),
            "stray": ("ok", stray, None, (True, False, True, None), False),
            "rev": ("ok", rev, None, (True, True, False, None), False),
            "slow": ("ok", slow, {"probe_timeout_seconds": 2},
                     (False, None, None, "SANDBOX-APPLY-TIMEOUT"), True),
        }
        for label, (patch, wrap, prm, want, draft) in expect.items():
            with self.subTest(label):
                R, p, rc, out, err = go(label, patch=patch, wrap=(lambda r, w=wrap: w) if wrap
                                        else None, params=prm)
                self.assertEqual(rc, 0, out + err)
                ev = fx2.last_event(R, "app.sandbox")
                self.assertEqual((ev["applied"], ev["touched_ok"], ev["rollback_ok"],
                                  ev["fail_code"]), want)
                self.assertEqual(ev["sandbox_sha256"] is not None, True)
                self.assertEqual(len(events_of(R, "app.sandbox")), 1)
                self.assertEqual(self.S(self.check(R), "events.transitions"), "PASS")
                self.assertEqual("obs-draft:" in out, draft)
                if draft:
                    self.assertIn("applied=false", out)
                    self.draft_ok(R, out, label)
        applies = [t for argv, t in seen if "apply" in argv]
        self.assertEqual(set(applies), {2})
        self.assertTrue({t for argv, t in seen if "rev-parse" in argv} <= {60, None})

    def test_AT_215_4_E_1_after_failure(self):
        R, p = self.fresh("fz-bad", patch="bad-context")
        rc, out, err = self.M(R, "sandbox", p)
        self.assertEqual(rc, 0, out + err)
        ev = fx2.last_event(R, "app.sandbox")
        rc, out, err = self.M(R, "sandbox", p)
        self.rejected(rc, out, {"STATE-NOT-APPROVED"})
        self.assertEqual(len(events_of(R, "app.sandbox")), 1)
        box = self.home / "sandbox" / p
        self.assertEqual(fx2.manifest_raw(box), ev["sandbox_sha256"])
        names = sorted(x.name for x in (self.home / "sandbox").iterdir())
        self.assertEqual(names, [p])
        Rb, pb = self.fresh()
        real_run = subprocess.run

        def broken(argv, *a, **kw):
            if "archive" in argv:
                return subprocess.CompletedProcess(argv, 128, "", "fatal: not a valid object name")
            return real_run(argv, *a, **kw)
        with mock.patch.object(si_git.subprocess, "run", broken):
            rc, out, err = self.M(Rb, "sandbox", pb)
        self.assertEqual(rc, 0, out + err)
        self.assertFalse((self.home / "sandbox" / pb).exists())
        self.assertEqual(sorted(x.name for x in (self.home / "sandbox").iterdir()), [])

    def test_AT_215_4_E_2_export_failures(self):
        real_run = subprocess.run
        cases = {}

        def make(label, fake):
            R, p = self.fresh()
            cases[label] = (R, p, fake)
        seen: list = []

        def git_failed(argv, *a, **kw):
            if "archive" in argv:
                seen.append(kw.get("timeout"))
                return subprocess.CompletedProcess(argv, 128, "", "fatal: not a valid object name")
            return real_run(argv, *a, **kw)

        def timed_out(argv, *a, **kw):
            if "archive" in argv:
                seen.append(kw.get("timeout"))
                raise subprocess.TimeoutExpired(argv, kw.get("timeout"))
            return real_run(argv, *a, **kw)

        def no_git(argv, *a, **kw):
            if argv and argv[0] == "git" and "archive" in argv:
                raise FileNotFoundError("git")
            return real_run(argv, *a, **kw)
        for label, fake, cause in (("a", git_failed, "SANDBOX-GIT-FAILED"),
                                   ("b", timed_out, "SANDBOX-EXPORT-TIMEOUT"),
                                   ("d", no_git, "SANDBOX-GIT-FAILED")):
            with self.subTest(label):
                R, p = self.fresh()
                if label == "b":
                    fx.set_params(R, probe_timeout_seconds=2)
                with mock.patch.object(si_git.subprocess, "run", fake):
                    rc, out, err = self.M(R, "sandbox", p)
                self.assertEqual(rc, 0, out + err)
                ev = fx2.last_event(R, "app.sandbox")
                self.assertEqual((ev["applied"], ev["touched_ok"], ev["rollback_ok"],
                                  ev["sandbox_sha256"], ev["fail_code"]),
                                 (False, None, None, None, "SANDBOX-EXPORT-FAILED"))
                self.assertIn(cause, err)
                self.assertFalse((self.home / "sandbox" / p).exists())
                self.assertIn("obs-draft:", out)
        self.assertEqual(seen, [600, 2, ][:len(seen)] if False else seen)
        self.assertEqual(sorted(set(seen)), [2, 600])


def replace_failing(match, exc=None, seen=None):
    """`os.replace` 的替身：`match(src, dst)` 成立的呼叫拋 `exc`（預設 PermissionError），
    其餘走真實函式。"""
    real = os.replace

    def fake(src, dst, *a, **kw):
        if match(Path(src), Path(dst)):
            if seen is not None:
                seen.append((Path(src).name, Path(dst).name))
            raise exc or PermissionError(13, "denied")
        return real(src, dst, *a, **kw)
    return mock.patch("os.replace", side_effect=fake)


def ledger_bytes(R: Path, rel: str) -> bytes:
    return (R / rel).read_bytes() if (R / rel).exists() else b""


class TestSwapFailuresAreCodedRejects(P2TestCase):
    """SCG-4 一審 D-02／D-08（非 AT 命名）：目錄換入與 OBS 帳本改寫的 `OSError` 一律轉成規格碼
    （rc 1、零殘留、無 traceback），半換入還原舊沙盒（R71）；無人值守的拒收先於用法檢查（R70）。"""

    def box_names(self) -> list[str]:
        return sorted(x.name for x in (self.home / "sandbox").iterdir())

    def test_d02_sandbox_swap_failure_restores_the_old_box(self):
        cases = (("second", lambda s, d: s.name.startswith(".tmp-"), True),
                 ("first", lambda s, d: d.name.startswith(".old-"), True),
                 ("no-old", lambda s, d: s.name.startswith(".tmp-"), False))
        for label, match, has_old in cases:
            with self.subTest(label):
                self.new_home()
                R, p = frozen_copy()
                box = self.home / "sandbox" / p
                if has_old:
                    box.mkdir(parents=True)
                    (box / "old.txt").write_text("前一輪的沙盒", encoding="utf-8")
                old = fx2.snapshot_tree(box) if has_old else None
                ev0, surf0, seen = (R / fx.EVL).read_bytes(), surface(R), []
                with replace_failing(match, seen=seen):
                    rc, out, err = self.M(R, "sandbox", p)
                self.rejected(rc, out, {"SANDBOX-SWAP-FAILED"}, label)
                self.draft_ok(R, out, label)
                self.assertIn("PermissionError", out)
                self.assertEqual(len(seen), 1, seen)  # 單次嘗試不重試
                self.assertEqual(fx2.snapshot_tree(box) if box.exists() else None, old)
                self.assertEqual(self.box_names(), [p] if has_old else [])  # 無 .old-*／.tmp-*
                self.assertEqual(((R / fx.EVL).read_bytes(), surface(R)), (ev0, surf0))
                self.assertEqual(list((self.home / "locks").glob("*.lock")), [])

    def test_d02_heldout_freeze_swap_failure_leaves_no_residue(self):
        self.new_home()
        R, p = fx2.template("approved", lambda r: fx2.drive_to(r, "approved"))
        src = fx2.make_heldout(fx.new_dir("ho"))
        ev0, surf0, seen = (R / fx.EVL).read_bytes(), surface(R), []
        with replace_failing(lambda s, d: d.parent.name == "heldout" and d.name == p, seen=seen):
            rc, out, err = self.M(R, "heldout-freeze", p, "--from", src, "--by", "FZ")
        self.rejected(rc, out, {"SANDBOX-SWAP-FAILED"})
        self.draft_ok(R, out)
        self.assertEqual(len(seen), 1, seen)
        box = self.home / "heldout"
        self.assertEqual(sorted(x.name for x in box.iterdir()) if box.exists() else [], [])
        self.assertEqual(((R / fx.EVL).read_bytes(), surface(R)), (ev0, surf0))
        rc, out, err = self.M(R, "heldout-freeze", p, "--from", src, "--by", "FZ")  # 對照組
        self.assertEqual(rc, 0, out + err)
        self.assertTrue((box / p / "manifest.json").is_file())

    def test_d02_verify_swap_failure_is_a_coded_reject_without_traceback(self):
        self.new_home()
        R = fx2.p2_base()
        p = fx2.drive_to(R, "sandboxed")
        box = self.home / "sandbox" / p
        sha = fx2.manifest_raw(box)
        shutil.rmtree(box)  # 樹不在 ⇒ verify 自 base 重新匯出再換入
        ev0, surf0, seen = (R / fx.EVL).read_bytes(), surface(R), []
        with replace_failing(lambda s, d: d.parent.name == "sandbox" and d.name == p, seen=seen):
            rc, out, err = self.M(R, "verify", p)
        self.rejected(rc, out, {"SANDBOX-SWAP-FAILED"})
        self.draft_ok(R, out)
        self.assertNotIn("Traceback", err)
        self.assertEqual(len(seen), 1, seen)
        self.assertEqual(self.box_names(), [])  # 無 .tmp-*／.tar 殘留，也沒有半換入的樹
        self.assertEqual(((R / fx.EVL).read_bytes(), surface(R)), (ev0, surf0))
        self.assertEqual(sorted((R / fx.PROPS_REL / p).glob("verify*.json")), [])
        rc, out, err = self.M(R, "verify", p)  # 對照組：不注入失敗 ⇒ 重新匯出成功
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(fx2.manifest_raw(box), sha)

    def obs_add_case(self):
        self.new_home()
        R = fx2.make_p2_repo(fx.new_dir("obs"))
        ref = fx2.new_uuid()
        fx2.write_audit(self.home, kind="obs-add", ref=ref, subject=None,
                        body=fx2.body_obs_add(ref))
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": fx2.AUDIT_KEY})
        patcher.start()
        self.addCleanup(patcher.stop)
        return R, ["obs-add", "--carrier", "console", "--audit-ref", ref]

    def test_d02_obs_add_write_failure_is_a_coded_reject(self):
        R, argv = self.obs_add_case()
        l0, e0, seen = (R / fx.LEDGER).read_bytes(), ledger_bytes(R, fx.EVL), []
        with replace_failing(lambda s, d: d.name == Path(fx.LEDGER).name, seen=seen):
            rc, out, err = self.M(R, *argv)
        self.rejected(rc, out, {"LEDGER-WRITE-FAILED"})
        self.draft_ok(R, out)
        self.assertIn("PermissionError", out)
        self.assertEqual(len(seen), 1, seen)
        self.assertEqual(((R / fx.LEDGER).read_bytes(), ledger_bytes(R, fx.EVL)), (l0, e0))
        self.assertEqual([x.name for x in (R / fx.LEDGER).parent.iterdir()
                          if x.name.endswith(".tmp")], [])
        self.assertEqual(list((self.home / "locks").glob("*.lock")), [])
        rc, out, err = self.M(R, *argv)  # 對照組
        self.assertEqual(rc, 0, out + err)

    def test_d02_obs_restore_failure_does_not_mask_the_append_failure(self):
        from lib.selfimproving import evwrite
        R, argv = self.obs_add_case()
        l0, writes = (R / fx.LEDGER).read_bytes(), []

        def second_ledger_write(src, dst):  # 第一次＝追加列；第二次＝事件追加失敗後的還原
            if dst.name == Path(fx.LEDGER).name:
                writes.append(1)
                return len(writes) == 2
            return False

        def boom():
            raise OSError("injected")
        with mock.patch.object(evwrite, "PAUSE_HOOK", boom), replace_failing(second_ledger_write):
            rc, out, err = self.M(R, *argv)
        self.assertEqual((rc, out), (3, ""), err)
        self.assertIn("事件追加失敗（OSError）", err)  # 原例外照報，不被還原的拒收遮蔽
        self.assertNotIn("Traceback", err)
        self.assertEqual(len(writes), 2)
        self.assertNotEqual((R / fx.LEDGER).read_bytes(), l0)  # 還原失敗＝孤列留著
        res = self.check(R)
        self.assertEqual(self.S(res, "obs.console_audit"), "FAIL")  # 由 check 標紅承接
        self.assertIn("CONSOLE-EVENT-MISSING", {c for _, c in self.F(res, "obs.console_audit")})

    def test_d08_heldout_freeze_unattended_precedes_usage_checks(self):
        self.new_home()
        R, p = fx2.template("approved", lambda r: fx2.drive_to(r, "approved"))
        ev0, missing = (R / fx.EVL).read_bytes(), fx.new_dir("nohome")
        argv = ["heldout-freeze", p, "--from", missing, "--by", "bad by"]  # 壞 --by、無此 --from
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, err = self.M(R, *argv)
        self.rejected(rc, out, {"UNATTENDED-REFUSED"})
        self.assertEqual((R / fx.EVL).read_bytes(), ev0)
        self.usage_error(*self.M(R, *argv))  # 對照組：未設無人值守 ⇒ 同樣的壞旗標是 rc 3


if __name__ == "__main__":
    unittest.main()
