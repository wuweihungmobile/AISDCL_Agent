# 受測面：tools/lib/selfimproving/pushguard.py（程式碼鎖，非散文）
"""SelfImproving P7 PU 前半：參數、巡邏提交的收斂（commit trailer、允許清單、紀錄、帳本差分規則）與
推送守門（TCS-SelfImproving-P7 §1 的 AC-SI-49-1～49-5；受測 `pushguard.py`、`patrolrun._commit`、
`patrolreport.record_commit`、`params.py`）。

夾具 `_selfimproving_p7_fixtures.py`（`p7x`）的 `push_repo`：真 git 暫存 repo＋本機 bare 遠端，
巡邏提交
一律於暫存 repo 內製造；**沒有任何測試對真 repo 做 commit／push**。守門的每個拒絕碼各有一條負向 AT。
AC-SI-49-6 以後（`push-run` 執行面、OS 任務）屬 PU 後半，不在本檔本半。每條 AT 的測試名帶編號
（`AT_749_<AC>_<序>`）。
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import inspect
import io
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import threading
import time
import types
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
import _selfimproving_p7_fixtures as p7x
from _selfimproving_p4_fixtures import Rig
from _selfimproving_p7_fixtures import NOW, P7TestCase

from lib.selfimproving import check as si_check
from lib.selfimproving import events as si_events
from lib.selfimproving import (
    evspec,
    nextstep,
    patrol,
    patrolpush,
    patrolreport,
    patrolrun,
    promote,
    pushcontent,
    pushguard,
    runner,
    sched,
    schedarm,
    unattended,
)
from lib.selfimproving import git as si_git
from lib.selfimproving import manifest as si_manifest
from lib.selfimproving import params as si_params
from lib.selfimproving.git import Git

ROOT = fx.ROOT
PKG = ROOT / "tools" / "lib" / "selfimproving"
PROTOCOL = ROOT / si_params.PROTOCOL_REL
BASELINE = ROOT / "docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md"
EVL, OBS, PROPS = fx.EVL, fx.LEDGER, fx.PROPS_REL
APP_T, PROP_T = pushguard.TRAILER_APP, pushguard.TRAILER_PROP
BEAT_NOW = datetime.now().astimezone().replace(microsecond=0)
ALL_BLOCKING = ("PUSH-FOREIGN-COMMITS", "PUSH-NOT-RECORDED", "PUSH-RECORD-MISMATCH",
                "PUSH-APP-KIND-INVALID", "PUSH-APP-REUSED", "PUSH-PATH-OUTSIDE",
                "PUSH-LEDGER-RULE", "PUSH-CONTENT-MISMATCH")


def setUpModule() -> None:
    fx.setup("si_p7p_")


def tearDownModule() -> None:
    fx.teardown()


def real_params() -> dict:
    return json.loads((PROTOCOL / "params.json").read_text(encoding="utf-8"))


def obs_edit(R: Path, fn) -> str:
    """OBS 帳本逐行處理後寫回工作樹；回新全文。"""
    lines = fx.read(R, OBS).split("\n")
    out = "\n".join(fn(lines))
    fx.put(R, OBS, out)
    return out


def row_index(lines: list[str], n: int) -> int:
    return next(i for i, ln in enumerate(lines) if ln.startswith(f"| {fx.obs_id(n)} |"))


def set_cell(line: str, idx: int, value: str) -> str:
    """OBS 資料列第 idx 欄（0 起算：ID=0、症狀=3、處置=7）換值；欄以 ` | ` 分隔。"""
    parts = line.split(" | ")
    parts[idx] = value
    return " | ".join(parts)


def commits_file(si: Path) -> Path:
    return si / "push" / patrolreport.COMMITS_NAME


def rewrite_first_event(text: str) -> str:
    """事件帳本既有第一行的 `by` 標籤改一個字（仍是合法事件，但不再是新帳本的位元組前綴）。"""
    first, _, rest = text.partition("\n")
    return re.sub(r'"by":"([^"]+)"', r'"by":"\1x"', first, count=1) + "\n" + rest


class GuardTestCase(P7TestCase):
    """守門測試基底（名稱含 TestCase：discover 守門不解析跨檔基底鏈）。"""

    def setUp(self) -> None:
        super().setUp()  # 暫存 repo 的 hooks 目錄不是 tools/git-hooks：替換既定值（測試縫）
        self.enterContext(mock.patch.object(si_git, "EXPECTED_HOOKS", p7x.HOOKS_DIR))

    def rr(self, **kw) -> p7x.PushRepo:
        return p7x.push_repo(self, **kw)

    DETAIL_SHAPE = {  # TCS-P7 E-9：`{detail}`＝sha8＋「卡在哪」的片段（其餘碼只有 sha8）
        "PUSH-APP-KIND-INVALID": r"APP-SI-\d+ app\.(sandbox|verify)",
        "PUSH-APP-REUSED": r"APP-SI-\d+",
        "PUSH-PATH-OUTSIDE": r"\S.*",
        "PUSH-LEDGER-RULE": r"\S.*",
        "PUSH-PROPOSAL-MISMATCH": r"\S+ (?:no-event|sha-mismatch)",
        "PUSH-FILE-MODE-INVALID": r"\S.* \d{6}",
        "PUSH-SECRET-PATTERN": r"\S.* [a-z-]+",
        "PUSH-CONTENT-MISMATCH": "事件帳本沒有該 APP 的事件行|觸及檔內容與 post_sha256 不符"}

    def blocked(self, res: dict, code: str, sha: str | None = None, msg: str = "",
                frag: str | None = None) -> None:
        self.assertEqual((res["ok"], res["code"], res["sha"]), (False, code, None), msg + str(res))
        if sha is not None:
            head8, detail = sha[:8], res["detail"]
            shape = self.DETAIL_SHAPE.get(code)
            if shape is None:
                self.assertEqual(detail, head8, msg)
            else:
                self.assertTrue(detail.startswith(head8 + " "), msg + detail)
                self.assertRegex(detail[9:], f"^(?:{shape})$", msg)
            if frag is not None:
                self.assertEqual(detail[9:], frag, msg)
            self.assertIn(head8, res["text"], msg)
        self.assertEqual(res["text"], nextstep.reason(code, res["detail"]).text, msg)


# --------------------------------------------------------------------------- AC-SI-49-1 參數
class TestParams(GuardTestCase):
    def test_AT_749_1_1_real_params_have_47_keys_and_the_new_defaults(self):
        raw = (PROTOCOL / "params.json").read_bytes()
        real = json.loads(raw)
        self.assertEqual((len(real), set(real) == set(si_params.PARAM_SPECS)), (47, True))
        self.assertEqual(list(real), sorted(real, key=lambda k: k.encode("utf-8")))
        self.assertEqual((real["sched_auto_push"], real["sched_push_wall_minutes"],
                          real["sched_push_attempts_max"], real["sched_push_retry_minutes"]),
                         (False, 45, 3, 360))  # 自動推送預設關閉：明確開啟才生效（資安審查）
        self.assertEqual(si_params.PARAM_SPECS["sched_auto_push"], "bool")
        self.assertEqual(si_params.param_findings(real), [])
        self.assertLessEqual({"sched_auto_push", "sched_push_wall_minutes",
                              "sched_push_attempts_max", "sched_push_retry_minutes"},
                             set(si_params.SCHED_KEYS))
        self.assertTrue(all(k.startswith("sched_") for k in si_params.SCHED_KEYS))
        self.assertEqual(si_params.params_file_problems(raw), [])
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(self.S(self.check(ROOT), "params.keys"), "PASS")

    def test_AT_749_1_E_1_types_ranges_and_missing_keys(self):
        base = real_params()

        def codes(**kw):
            return {(f.subject, f.code) for f in si_params.param_findings({**base, **kw})}
        self.assertEqual(codes(), set())
        self.assertEqual(codes(sched_auto_push=1), {("sched_auto_push", "PARAM-TYPE")})
        self.assertEqual((codes(sched_auto_push=True), codes(sched_auto_push=False)),
                         (set(), set()))
        self.assertEqual(codes(sched_push_wall_minutes=True),
                         {("sched_push_wall_minutes", "PARAM-TYPE")})
        self.assertEqual(codes(sched_push_wall_minutes=0),
                         {("sched_push_wall_minutes", "PARAM-RANGE")})
        self.assertEqual(codes(sched_push_wall_minutes=121),
                         {("sched_push_wall_minutes", "PARAM-RANGE")})  # 跨鍵上限 120
        self.assertEqual(codes(sched_push_wall_minutes=120), set())
        self.assertEqual(si_params.PUSH_WALL_MAX_MINUTES, 120)
        self.assertEqual(codes(sched_push_attempts_max=0),
                         {("sched_push_attempts_max", "PARAM-RANGE")})
        self.assertEqual(codes(sched_push_retry_minutes=0),
                         {("sched_push_retry_minutes", "PARAM-RANGE")})
        for key in ("sched_auto_push", "sched_push_wall_minutes", "sched_push_attempts_max",
                    "sched_push_retry_minutes"):
            gone = {k: v for k, v in base.items() if k != key}
            self.assertEqual({(f.subject, f.code) for f in si_params.param_findings(gone)},
                             {(key, "PARAM-MISSING")}, key)

    def test_AT_749_1_2_fingerprint_moves_and_the_baseline_row_is_the_live_value(self):
        self.assertNotIn("params.json", si_params.FINGERPRINT_EXCLUDED)
        fp, _ = si_params.fingerprint(ROOT, real_params())
        copy = fx.new_dir("fp")
        shutil.copytree(PROTOCOL, copy / si_params.PROTOCOL_REL)
        pj = copy / si_params.PROTOCOL_REL / "params.json"
        pj.write_bytes(
            pj.read_bytes().replace(b'"sched_auto_push": false', b'"sched_auto_push": true'))
        self.assertNotEqual(si_params.fingerprint(copy, real_params())[0], fp)
        text = BASELINE.read_text(encoding="utf-8")
        row = next(ln for ln in text.splitlines() if ln.startswith("| 協定目錄 params.json"))
        raw = (PROTOCOL / "params.json").read_bytes()
        self.assertIn(f"{len(raw)} bytes", row)
        self.assertIn(hashlib.sha256(raw).hexdigest(), row)
        self.assertIn(fp, next(ln for ln in text.splitlines() if ln.startswith("| 指紋 |")))
        for name, tail in (("metrics.md", "協定目錄 metrics.md"),
                           ("research_sources.json", "協定目錄 research_sources.json")):
            line = next(ln for ln in text.splitlines() if ln.startswith(f"| {tail}"))
            self.assertIn(hashlib.sha256((PROTOCOL / name).read_bytes()).hexdigest(), line, name)
        head = subprocess.run(["git", "-C", str(ROOT), "show",
                               f"HEAD:{si_params.PROTOCOL_REL}/research_registry.json"],
                              capture_output=True, check=False, env=fx.genv())
        if head.returncode == 0:  # 位元組不變（對 HEAD）
            self.assertEqual((PROTOCOL / "research_registry.json").read_bytes(), head.stdout)


# --------------------------------------------------------------------------- AC-SI-49-2 真心跳
class ChainTestCase(GuardTestCase):
    """真 promote／commit 鏈：一個走到 verified 的 PROP（真沙盒與驗證）、人的決定、
    會計數的 pre-commit。"""

    def beat(self, *args, **kw):
        with fx4.with_key(fx2.AUDIT_KEY):
            return super().beat(*args, **kw)

    def cdec(self, R: Path, prop: str, dkind: str, **extra) -> None:
        digest = None if dkind == "rollback" else fx2.prop_event(R, prop)["digest"]
        ref = self.audit("decide", lambda r: fx2.body_decide(r, prop, digest, dkind, **extra),
                         subject=prop)
        with fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.M(R, "decide", prop, "--carrier", "console", "--audit-ref", ref)
        self.assertEqual(rc, 0, out + err)

    def promotable(self, hook_rc: int = 0) -> tuple[Path, str, Path]:
        R = fx4.p4_base()
        prop = fx2.drive_to(R, "verified")
        self.cdec(R, prop, "promote")
        fx.commit_all(R, "pre-heartbeat")
        marker, hook = R / ".git" / "hook_calls", R / ".git" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_bytes(f"#!/bin/sh\necho x >> .git/hook_calls\nexit {hook_rc}\n".encode())
        hook.chmod(0o755)
        return R, prop, marker

    def with_remote(self, R: Path) -> Path:
        """本機 bare 遠端 `origin`，`main` 追蹤 `origin/main`（目前狀態已推上去）。"""
        fx.git(R, "branch", "-M", "main")
        bare = fx.new_dir("bare")
        fx.git(fx.TMP, "init", "-q", "--bare", str(bare))
        fx.git(R, "remote", "add", "origin", str(bare))
        fx.git(R, "push", "-q", "-u", "origin", "main")
        arm = self.home / "push" / "armed.json"  # 模擬 `sched arm` 記下的遠端網址
        arm.parent.mkdir(parents=True, exist_ok=True)
        arm.write_text(json.dumps({"remote_url": str(bare), "git": si_git.resolve_git(),
                           "config_pins": {}}), encoding="utf-8")
        fx.git(R, "config", "core.hooksPath", p7x.HOOKS_DIR)
        return bare

    def ctx(self, R: Path) -> patrol.Ctx:
        params = si_check.params_for(R, *si_params.SCHED_KEYS, "stop_after_bad")
        return patrol.Ctx(R, BEAT_NOW, False, patrol.Deps(), params)

    def promoted_tree(self) -> tuple[Path, str, patrol.Ctx]:
        """走完真 `promote`（不 commit）的 repo：供對「將要提交的差分」做各種改動後
        直接呼叫 `_commit`。"""
        R, prop, _ = self.promotable()
        with fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.M(R, "promote", prop, "--by", "patrol")
        self.assertEqual(rc, 0, out + err)
        return R, prop, self.ctx(R)

    def head(self, R: Path) -> str:
        return fx.git(R, "rev-parse", "HEAD")

    def last_msg(self, R: Path) -> str:
        return fx.git(R, "log", "-1", "--format=%B")

    def last_rows(self) -> list[dict]:
        path = commits_file(self.home)
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").split("\n") if ln]


@contextlib.contextmanager
def git_calls():
    """記錄巡邏器對 git 的每個呼叫（只記 argv，行為不變）。"""
    seen: list[tuple] = []
    orig = Git.run

    def rec(self, *args, **kw):
        seen.append(args)
        return orig(self, *args, **kw)
    with mock.patch.object(Git, "run", rec):
        yield seen


@contextlib.contextmanager
def mac_platform():
    """模擬 macOS（`sys.platform`）：本機 git 是 Windows 的 `git.exe`，`resolve_git` 的副檔名規則
    在 darwin 下找不到它，所以先解出真路徑、再把兩處解析點固定住（只換平台、不換 git）。"""
    exe = si_git.resolve_git(os.environ)
    with mock.patch.object(schedarm.sys, "platform", "darwin"), \
            mock.patch.object(si_git, "resolve_git", return_value=exe), \
            mock.patch.object(schedarm, "resolve_git", return_value=exe):
        yield


def parse_trailers(msg: str) -> list[str]:
    cp = subprocess.run(["git", "interpret-trailers", "--parse"], input=msg, capture_output=True,
                        encoding="utf-8", errors="replace", check=True, env=fx.genv())
    return [ln for ln in cp.stdout.split("\n") if ln]


class TestCommit(ChainTestCase):
    def test_AT_749_2_1_trailers_record_and_no_push_wording_for_promote_and_rollback(self):
        R, prop, _ = self.promotable()
        self.with_remote(R)
        self.assertEqual(self.beat(R, BEAT_NOW, Rig())[0], 0)
        app = [e for e in fx.EV(R) if e["kind"] == "app.promote"][-1]["id"]
        dec = [e for e in fx.EV(R) if e["kind"] == "dec" and e["dkind"] == "promote"][-1]["id"]
        msg = self.last_msg(R)
        self.assertEqual(msg.split("\n")[0],
                         f"chore(selfimproving): promote {prop}（{dec}、{app}）")
        self.assertNotIn("不 push", msg)
        trailers = [f"{APP_T}: {app}", f"{PROP_T}: {prop}"]
        self.assertEqual(msg.strip("\n").split("\n\n")[-1].split("\n"), trailers)
        self.assertEqual(parse_trailers(msg), trailers)
        rows = self.last_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0]), ["sha", "app", "prop", "at"])
        self.assertEqual((rows[0]["sha"], rows[0]["app"], rows[0]["prop"]),
                         (self.head(R), app, prop))
        self.assertIsNotNone(datetime.fromisoformat(rows[0]["at"]).utcoffset())
        self.assertNotIn(R.resolve(), commits_file(self.home).resolve().parents)  # 不在 repo 內
        # rollback 同形：APP 取 app.rollback
        self.cdec(R, prop, "rollback", reason="太慢")
        self.assertEqual(self.beat(R, BEAT_NOW + timedelta(minutes=5), Rig())[0], 0)
        app2 = [e for e in fx.EV(R) if e["kind"] == "app.rollback"][-1]["id"]
        msg2 = self.last_msg(R)
        self.assertTrue(msg2.startswith("chore(selfimproving): rollback "), msg2)
        self.assertEqual(parse_trailers(msg2), [f"{APP_T}: {app2}", f"{PROP_T}: {prop}"])
        self.assertEqual(self.last_rows()[-1]["app"], app2)
        self.assertEqual(self.last_rows()[-1]["sha"], self.head(R))

    def test_AT_749_2_E_1_old_behaviour_is_unchanged(self):
        R, prop, marker = self.promotable(hook_rc=1)
        n0 = int(fx.git(R, "rev-list", "--count", "HEAD"))
        with git_calls() as seen:
            rc, out, err = self.beat(R, BEAT_NOW, Rig())
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(int(fx.git(R, "rev-list", "--count", "HEAD")), n0)
        self.assertTrue(any("code=COMMIT-FAILED" in ln for ln in self.logs()))
        self.assertIn("obs-draft:", out)
        self.assertFalse(commits_file(self.home).exists())  # 提交失敗不寫紀錄
        self.assertFalse([a for a in seen if "--no-verify" in a])
        self.assertFalse([a for a in seen if a[:1] == ("add",) and ("-A" in a or "." in a)])
        self.new_home()
        R2, _, marker2 = self.promotable()
        fx.set_params(R2, sched_auto_commit=False)
        fx.commit_all(R2, "auto-commit-off")
        n2 = int(fx.git(R2, "rev-list", "--count", "HEAD"))
        self.assertEqual(self.beat(R2, BEAT_NOW, Rig())[0], 0)
        self.assertEqual(int(fx.git(R2, "rev-list", "--count", "HEAD")), n2)

    def test_AT_749_2_2_commit_and_guard_share_one_allow_list(self):
        R, prop, _ = self.promotable()
        fx.set_params(R, sched_auto_push=True)  # 末段 `push-run` 真推送要用；須在製造殘留檔之前提交
        fx.commit_all(R, "auto-push-on")
        other = fx.pid(77)
        fx.put(R, f"{PROPS}/{other}/x.md", "別的提案目錄的未提交檔\n")  # ① 另一個 PROP 的目錄
        reg = f"{si_params.PROTOCOL_REL}/research_registry.json"
        # ② 已暫存的 research_registry.json（在 _OWN_PREFIXES、不在 commit_allow）
        fx.put(R, reg, "{}\n")
        fx.git(R, "add", "--", reg)
        bare = self.with_remote(R)
        self.assertEqual(sched.dirty_paths(R), [])
        self.assertEqual(self.beat(R, BEAT_NOW, Rig())[0], 0)
        shown = fx.git(R, "show", "--name-only", "--format=", "HEAD").split()
        self.assertNotIn(f"{PROPS}/{other}/x.md", shown)
        self.assertNotIn(reg, shown)
        self.assertIn(EVL, shown)
        status = fx.git(R, "status", "--porcelain", "--untracked-files=all")
        self.assertIn(f"{PROPS}/{other}/x.md", status)
        self.assertIn(f"A  {reg}", status)  # 仍在 index
        row = next(r for r in self.report()["props"] if r["id"] == prop)
        self.assertEqual(row["code"], "COMMIT-LEFTOVER")
        res = pushguard.evaluate(R, {"sched_auto_push": True}, self.home, BEAT_NOW)
        self.assertTrue(res["ok"], res)
        self.assertEqual((res["ahead"], res["sha"]), (1, self.head(R)))
        # `push-run` 對本機 bare 遠端真推送成功（AT-749-2-2 的末句）：清單外的殘留檔不擋、也沒被推走
        rc, out = patrolpush.run(R, now=BEAT_NOW)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-OK", out)
        self.assertEqual(fx.git(bare, "rev-parse", "refs/heads/main"), self.head(R))
        # 允許清單是單一來源：_commit 不含字面整個提案目錄常數，且 git commit 帶 pathspec
        fn = next(n for n in ast.walk(ast.parse((PKG / "patrolrun.py").read_text(encoding="utf-8")))
                  if isinstance(n, ast.FunctionDef) and n.name == "_commit")
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        self.assertNotIn("PROPOSALS_REL", names | attrs)
        self.assertLessEqual({"commit_allow", "pending", "rule_problem"}, attrs)
        commit_calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and c.args
                        and isinstance(c.args[0], ast.Constant) and c.args[0].value == "commit"]
        self.assertTrue(commit_calls)
        self.assertTrue(any(isinstance(a, ast.Constant) and a.value == "--"
                            for c in commit_calls for a in c.args))
        # 守門的允許清單函式與提交共用（evaluate 這一側）
        src = (PKG / "pushguard.py").read_text(encoding="utf-8")
        self.assertIn("commit_allow(prop, touched", src)

    def test_AT_749_2_3_a_failed_record_is_final_and_never_pushed(self):
        R, prop, _ = self.promotable()
        fx.set_params(R, sched_auto_push=True)  # 快照的 push 區塊才會走守門
        fx.commit_all(R, "auto-push-on")
        self.with_remote(R)
        n0 = int(fx.git(R, "rev-list", "--count", "HEAD"))
        with mock.patch.object(patrolreport, "record_commit", side_effect=OSError("disk full")):
            self.assertEqual(self.beat(R, BEAT_NOW, Rig())[0], 0)
        self.assertEqual(int(fx.git(R, "rev-list", "--count", "HEAD")), n0 + 1)  # 不回滾提交
        self.assertEqual(len([ln for ln in self.logs() if "code=COMMIT-RECORD-FAILED" in ln]), 1)
        row = next(r for r in self.report()["props"] if r["id"] == prop)
        self.assertEqual((row["code"], row["who"]), ("COMMIT-RECORD-FAILED", "主機管理者"))
        self.assertFalse(commits_file(self.home).exists())
        res = pushguard.evaluate(R, {"sched_auto_push": True}, self.home, BEAT_NOW)
        self.blocked(res, "PUSH-NOT-RECORDED", self.head(R))
        self.assertEqual(self.report()["push"]["code"], "PUSH-NOT-RECORDED")

    def test_AT_749_2_4_the_recorded_sha_is_head_after_the_commit(self):
        R, prop, _ = self.promotable()
        self.with_remote(R)
        self.assertEqual(self.beat(R, BEAT_NOW, Rig())[0], 0)
        sha = self.last_rows()[-1]["sha"]
        self.assertEqual((len(sha), sha), (40, self.head(R)))
        self.assertEqual(sha, fx.git(R, "log", "-1", "--format=%H"))
        self.new_home()
        R2, prop2, _ = self.promotable()
        self.with_remote(R2)
        orig, state = Git.head, {"done": False}

        def racing_head(git_self):
            if not state["done"] and fx.git(R2, "log", "-1", "--format=%s").startswith(
                    # 只在 _commit 的 commit 成功之後、rev-parse 之前插入一次
                    "chore(selfimproving)"):
                state["done"] = True
                fx.git(R2, "commit", "-q", "--allow-empty", "-m",
                       "他人在 commit 與 rev-parse 之間的提交")
            return orig(git_self)
        with mock.patch.object(Git, "head", racing_head):
            self.assertEqual(self.beat(R2, BEAT_NOW, Rig())[0], 0)
        res = pushguard.evaluate(R2, {"sched_auto_push": True}, self.home, BEAT_NOW)
        self.assertFalse(res["ok"])  # 安全側：紀錄記到他人的 sha，守門不放行
        # TCS-P7 E-9：最早不合者定案——巡邏提交本身無紀錄，唯一確定碼
        self.assertEqual(res["code"], "PUSH-NOT-RECORDED")
        self.assertEqual(self.last_rows()[-1]["sha"], self.head(R2))

    def test_AT_749_2_5_one_ledger_rule_function_serves_commit_and_guard(self):
        R, prop, ctx = self.promoted_tree()
        self.with_remote_after_promote(R)
        # ①OBS 追加兩列＋既有 open 列處置欄轉終值、②提案目錄新增檔、③事件帳本尾端追加
        new1, new2 = (
            fx.line([fx.obs_id(n), "2026-11-11 12:00", f"追加列 {n}", "症狀",
                     "tools/lib/si_demo.py:12", "doc",
                               "P3", "open", "面=文件;來源=代理;回報者=SA"]) for n in (21, 22))
        obs_edit(R, lambda ls: [set_cell(ln, 7, "fixed@abcdef0") if ln.startswith(
            f"| {fx.obs_id(1)} |") else ln for ln in ls[:-1]] + [new1, new2, ""])
        fx.put(R, f"{PROPS}/{prop}/verify2.json", "{}\n")
        fx.append_events(R, [fx.card_ev(int(prop[-3:])),  # 第 2 筆驗證事件綁定該檔的位元組雜湊
                             fx.verify_ev(int(prop[-3:]), "PASS", verify_sha256=(
                                 "sha256:" + hashlib.sha256(b"{}\n").hexdigest()))])
        n0 = int(fx.git(R, "rev-list", "--count", "HEAD"))
        patrolrun._commit(ctx, prop, "promote")
        self.assertEqual(int(fx.git(R, "rev-list", "--count", "HEAD")), n0 + 1, ctx.notes)
        shown = fx.git(R, "show", "--name-only", "--format=", "HEAD").split()
        self.assertLessEqual({OBS, EVL, f"{PROPS}/{prop}/verify2.json"}, set(shown))
        self.assertNotIn(prop, ctx.notes)
        # 守門對同一提交（父 vs 該提交）呼叫同一個函式、全套件沒有第二份實作
        res = pushguard.evaluate(R, {"sched_auto_push": True}, self.home, BEAT_NOW)
        self.assertTrue(res["ok"], res)
        defs = [p.name for p in PKG.glob("*.py")
                if "def ledger_rule_problems" in p.read_text(encoding="utf-8")]
        self.assertEqual(defs, ["pushcontent.py"])  # 自 pushguard 拆出（LOC 分級），仍是單一處
        for name in ("_obs_problem",):
            homes = [p.name for p in PKG.glob("*.py")
                     if f"def {name}" in p.read_text(encoding="utf-8")]
            self.assertEqual(homes, ["pushcontent.py"])
        callers = set()
        for name in ("pushguard", "pushcontent"):
            tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
            callers |= {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
                        for c in ast.walk(fn) if isinstance(c, ast.Call)
                        and ast.unparse(c.func) == "content_problems"}
        # 提交側 `rule_problem`、守門側 `judge`（E-20：內容約束的單一函式 `content_problems`）
        self.assertEqual(callers, {"rule_problem", "judge"})
        inner = {fn.name for fn in ast.walk(ast.parse((PKG / "pushcontent.py").read_text(
            encoding="utf-8"))) if isinstance(fn, ast.FunctionDef) for c in ast.walk(fn)
            if isinstance(c, ast.Call) and ast.unparse(c.func) == "ledger_rule_problems"}
        self.assertEqual(inner, {"content_problems"})

    def with_remote_after_promote(self, R: Path) -> None:
        """（promoted_tree 已有未提交的 promote 改動）遠端以目前 HEAD 為基線。"""
        self.with_remote(R)

    def test_AT_749_2_E_2_ledger_rule_violation_refuses_to_commit(self):
        cases = {
            "obs-symptom": lambda R, p: obs_edit(R, lambda ls: [set_cell(ln, 3, "被改寫的症狀")
                                                                 if ln.startswith(
                                                                     f"| {fx.obs_id(1)} |")
                                                                 else ln for ln in ls]),
            "event-line": lambda R, p: fx.put(R, EVL, rewrite_first_event(fx.read(R, EVL))),
            "prop-file": lambda R, p: fx.put(R, f"{PROPS}/{p}/r1.md", "被改寫\n"),
        }
        for label, mutate in cases.items():
            with self.subTest(label):
                self.new_home()
                R, prop, ctx = self.promoted_tree()
                mutate(R, prop)
                head0 = self.head(R)
                idx0 = fx.git(R, "diff", "--cached", "--name-only")
                patrolrun._commit(ctx, prop, "promote")
                self.assertEqual((self.head(R), fx.git(R, "diff", "--cached", "--name-only")),
                                 (head0, idx0))
                self.assertFalse(commits_file(self.home).exists())
                self.assertEqual(
                    [ln for ln in self.logs() if "code=COMMIT-LEDGER-RULE" in ln].__len__(), 1)
                self.assertEqual(ctx.notes[prop][0], "COMMIT-LEDGER-RULE")
                row = next(r for r in patrolreport.build(ctx, [], [], lambda *a: False)["props"]
                           if r["id"] == prop)
                self.assertEqual((row["code"], row["who"]), ("COMMIT-LEDGER-RULE", "主機管理者"))
                self.assertIn("帳本或提案檔有不合規則的改動", row["text"])
                self.assertIn("巡邏器沒有提交", row["text"])

    def test_AT_749_2_E_2_b_measure_still_runs_and_nothing_is_retried(self):
        R, prop, _ = self.promotable()
        real = promote.promote

        def corrupting(repo, ns, as_json):
            out = real(repo, ns, as_json)
            obs_edit(repo, lambda ls: [set_cell(ln, 3, "被改寫的症狀") if ln.startswith(
                f"| {fx.obs_id(1)} |") else ln for ln in ls])
            return out
        head0, rig = self.head(R), Rig()
        with mock.patch.object(promote, "promote", corrupting):
            self.assertEqual(self.beat(R, BEAT_NOW, rig)[0], 0)
        self.assertEqual(self.head(R), head0)
        self.assertTrue(rig.verbs_named("measure"))
        self.assertEqual(len([ln for ln in self.logs() if "code=COMMIT-LEDGER-RULE" in ln]), 1)
        self.assertFalse(commits_file(self.home).exists())


class TestRecordAndClip(ChainTestCase):
    """提交紀錄不可補登與白話細節截斷（受測 tools/lib/selfimproving/pushguard.py）。"""

    def test_AT_749_4_E_16_there_is_no_way_to_backfill_a_record(self):
        # `record_commit` 只被 `patrolrun._commit` 呼叫（AST：其餘檔只有定義與 `__all__` 字串）
        callers = []
        for path in sorted(PKG.glob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("record_commit"):
                    callers.append(path.name)
        self.assertEqual(callers, ["patrolrun.py"])
        import selfimproving
        self.assertEqual([v for v in selfimproving._HELP if "record" in v or "backfill" in v], [])
        sop = (ROOT / "docs/05_development/SelfImproving_Operations_SOP.md").read_text(
            encoding="utf-8").splitlines()
        self.assertEqual([ln for ln in sop if "record-commit" in ln or "--backfill" in ln], [])
        # 提交與寫紀錄之間巡邏被殺：下一心跳 evaluate 一樣是 NOT-RECORDED（安全側）
        R, prop, _ = self.promotable()
        self.with_remote(R)
        with mock.patch.object(patrolreport, "record_commit", side_effect=RuntimeError("killed")):
            self.assertEqual(self.beat(R, BEAT_NOW, Rig())[0], 1)
        self.assertFalse(commits_file(self.home).exists())
        res = pushguard.evaluate(R, {"sched_auto_push": True}, self.home, BEAT_NOW)
        self.blocked(res, "PUSH-NOT-RECORDED", self.head(R))

    def test_main_control_ruling_detail_paths_keep_their_tail(self):
        """主控裁決（SA 補勘誤）：白話細節超長時中段省略、保留路徑尾段；總長上限不變。"""
        # 純字串截斷判準，與路徑語意無關（Windows 形路徑只是尾段保留的典型資料）
        deep = ("C:\\Users\\某人\\.claude\\projects\\"  # platform-ok: 字串截斷
                + "D--" * 20 + "slug\\memory")
        self.assertGreater(len(deep), nextstep.DETAIL_MAX)
        got = nextstep.sanitize(deep)
        self.assertEqual(len(got), nextstep.DETAIL_MAX)
        self.assertEqual(got, deep[:20] + "…" + deep[-59:])  # TCS-P7 E-14：前 20＋…＋後 59
        self.assertTrue(got.endswith("\\memory"))
        text = nextstep.reason("MEMORY-DIR-UNRESOLVED", deep).text
        self.assertLessEqual(len(text), nextstep.LINE_MAX)
        self.assertTrue(text.endswith("\\memory"), text)
        short = "C:\\x\\memory"  # platform-ok: 字串截斷
        self.assertEqual(nextstep.sanitize(short), short)
        for limit in (0, 1, 2, 5, 80):
            self.assertLessEqual(len(nextstep.clip("a" * 200, limit)), limit)


# --------------------------------------------------------------------------- AC-SI-49-3 放行
class TestGuardPasses(GuardTestCase):
    def test_AT_749_3_1_a_clean_range_of_patrol_commits_passes(self):
        rr = self.rr()
        p1, p2 = rr.patrol("promote"), rr.patrol("rollback")
        res = rr.evaluate()
        self.assertEqual((res["ok"], res["code"], res["ahead"], res["sha"]),
                         (True, None, 2, fx.git(rr.R, "rev-parse", "HEAD")), res)
        self.assertEqual((len(res["sha"]), res["head"]), (40, res["sha"]))
        self.assertNotEqual(p1.sha, p2.sha)
        rm = self.rr(cls="M")
        rm.patrol("promote")  # M 類：只有 SI_OWN_ALLOW 路徑（事件帳本新增其 APP 行）
        self.assertEqual(fx.git(rm.R, "show", "--name-only", "--format=", "HEAD").split(), [EVL])
        res_m = rm.evaluate()
        self.assertEqual((res_m["ok"], res_m["ahead"]), (True, 1), res_m)

    def test_AT_749_3_2_legal_ledger_changes_are_not_false_positives(self):
        rr = self.rr()
        extra = {}
        lines = fx.read(rr.R, OBS).rstrip("\n").split("\n")
        n1, n2 = (fx.line([fx.obs_id(n), "2026-11-11 12:00", f"追加列 {n}", "症狀",
                           "tools/lib/si_demo.py:12", "doc",
                           "P3", "open", "面=文件;來源=代理;回報者=SA"]) for n in (31, 32))
        lines = [set_cell(ln, 7, "fixed@abcdef0") if ln.startswith(f"| {fx.obs_id(1)} |") else ln
                 for ln in lines]
        extra[OBS] = "\n".join([*lines, n1, n2, ""])
        extra[f"{PROPS}/{rr.prop}/verify2.json"] = "{}\n"
        fx.append_events(rr.R, [fx.card_ev(1), fx.card_ev(1)])  # 他人寫入的合法事件（尾端追加）
        rr.patrol("promote", extra=extra)
        res = rr.evaluate()
        self.assertTrue(res["ok"], res)


# --------------------------------------------------------------------------- AC-SI-49-4 拒絕
class TestGuardRefuses(GuardTestCase):
    """守門拒絕各種旁路（受測 tools/lib/selfimproving/pushguard.py）。"""

    def test_AT_749_4_1_foreign_commits_each_bypass_is_refused(self):
        def two_trailers(app, prop):
            return f"chore: x\n\n{APP_T}: {app}\n{PROP_T}: {prop}"
        subcases = {}

        def human(rr):
            rr.patrol()
            return rr.human()

        def unknown_app(rr):
            return rr.commit([], app="APP" + "-SI-998", empty=True)

        def wrong_prop(rr):
            return rr.patrol(prop=fx.pid(9)).sha

        def one_trailer(rr):
            app = rr.app_id()
            rr.event("app.promote", app, post=rr.post())
            return rr.commit([EVL], app=app, message=f"chore: x\n\n{APP_T}: {app}")

        def trailer_mid(rr):
            app = rr.app_id()
            rr.event("app.promote", app, post=rr.post())
            return rr.commit([EVL], app=app, message=two_trailers(app, rr.prop) + "\n\n補充說明\n")

        def merge(rr):
            fx.git(rr.R, "checkout", "-q", "-b", "side")
            fx.put(rr.R, "side.txt", "側枝\n")
            fx.git(rr.R, "add", "--", "side.txt")
            fx.git(rr.R, "commit", "-q", "-m", "side")
            fx.git(rr.R, "push", "-q", "origin", "side:main")
            fx.git(rr.R, "checkout", "-q", "main")
            rr.patrol()
            fx.git(rr.R, "merge", "-q", "--no-ff", "origin/main", "-m", "merge")
            return fx.git(rr.R, "rev-parse", "HEAD")
        subcases.update({"no-trailer": human, "app-not-in-ledger": unknown_app,
                         "prop-mismatch": wrong_prop, "one-trailer": one_trailer,
                         "mid-body": trailer_mid, "merge": merge})
        for label, build in subcases.items():
            with self.subTest(label):
                rr = self.rr()
                sha = build(rr)
                self.blocked(rr.evaluate(), "PUSH-FOREIGN-COMMITS", sha if isinstance(sha, str)
                             else sha.sha, label)

    def test_AT_749_4_E_1_copying_the_format_with_a_verification_app_is_refused(self):
        rr = self.rr()
        ev = si_events.load_sound_events(rr.R / EVL)
        sandbox = next(e for e in ev if e["kind"] == "app.sandbox" and e["prop"] == rr.prop)
        self.assertNotIn(sandbox["kind"], ("app.promote", "app.rollback"))
        sha = rr.commit([], app=sandbox["id"], empty=True)
        self.blocked(rr.evaluate(), "PUSH-APP-KIND-INVALID", sha,
                     frag=f"{sandbox['id']} {sandbox['kind']}")
        self.assertEqual(evspec.APP_RE.match(sandbox["id"]) is not None, True)

    def test_AT_749_4_E_2_one_app_in_two_commits_is_refused_on_the_second(self):
        rr = self.rr()
        p = rr.patrol()
        sha2 = rr.commit([], app=p.app, empty=True)  # 含 --allow-empty 的照抄
        self.blocked(rr.evaluate(), "PUSH-APP-REUSED", sha2, frag=p.app)

    def test_AT_749_4_E_3_an_app_already_in_the_remote_history_is_refused(self):
        rr = self.rr()
        p = rr.patrol()
        rr.push()
        sha2 = rr.commit([], app=p.app, empty=True)
        self.blocked(rr.evaluate(), "PUSH-APP-REUSED", sha2, frag=p.app)

    def test_AT_749_4_E_4_a_file_outside_the_list_is_refused(self):
        rr = self.rr()
        sha = rr.patrol(extra={"README.md": "夾帶\n"}).sha
        self.blocked(rr.evaluate(), "PUSH-PATH-OUTSIDE", sha, frag="README.md")

    def test_AT_749_4_E_5_si_owned_but_not_in_the_explicit_list_is_refused(self):
        for label, rel in (("registry", f"{si_params.PROTOCOL_REL}/research_registry.json"),
                           ("other-prop", f"{PROPS}/{fx.pid(2)}/r1.md"),
                           ("params", f"{si_params.PROTOCOL_REL}/params.json")):
            with self.subTest(label):
                rr = self.rr(other_prop=True)
                text = fx.read(rr.R, rel) + "x\n" if (rr.R / rel).exists() else "{}\n"
                sha = rr.patrol(extra={rel: text}).sha
                self.blocked(rr.evaluate(), "PUSH-PATH-OUTSIDE", sha, label, frag=rel)

    def test_AT_749_4_E_6_a_memory_commit_may_not_carry_repo_paths(self):
        rr = self.rr(cls="M")
        sha = rr.patrol(extra={"memory/demo.md": "被當成 repo 內路徑\n"}).sha
        self.blocked(rr.evaluate(), "PUSH-PATH-OUTSIDE", sha, frag="memory/demo.md")
        self.assertEqual(pushguard.commit_allow(rr.prop, ["memory/demo.md"], "M"),
                         pushguard.si_own_allow(rr.prop))

    def test_AT_749_4_E_7_content_not_matching_post_sha256_is_refused(self):
        rr = self.rr()
        sha = rr.patrol(tamper="多改一行\n").sha
        self.blocked(rr.evaluate(), "PUSH-CONTENT-MISMATCH", sha,
                     frag="觸及檔內容與 post_sha256 不符")

    def test_AT_749_4_E_8_a_commit_that_adds_no_app_event_line_is_refused(self):
        rr = self.rr(dangling_app=True)
        rr.write_touched()
        sha = rr.commit(rr.touched, app=rr.dangling)  # 事件帳本沒有任何新增行
        self.blocked(rr.evaluate(), "PUSH-CONTENT-MISMATCH", sha,
                     frag="事件帳本沒有該 APP 的事件行")

    def test_AT_749_4_E_9_a_rewritten_event_ledger_is_refused(self):
        rr = self.rr()
        app = rr.app_id()
        fx.put(rr.R, EVL, rewrite_first_event(fx.read(rr.R, EVL)))
        rr.write_touched()
        rr.event("app.promote", app, post=rr.post())
        sha = rr.commit([EVL, *rr.touched], app=app)
        self.blocked(rr.evaluate(), "PUSH-LEDGER-RULE", sha,
                     frag="事件帳本既有內容被改動（只准尾端追加）")

    def test_AT_749_4_E_10_the_first_bad_commit_and_the_first_code_win(self):
        rr = self.rr()
        rr.patrol()
        bad = rr.human()
        rr.patrol()
        self.blocked(rr.evaluate(), "PUSH-FOREIGN-COMMITS", bad)
        rr2 = self.rr()
        h1 = rr2.human("a.txt")
        rr2.human("b.txt")
        self.blocked(rr2.evaluate(), "PUSH-FOREIGN-COMMITS", h1)  # 全部不符＝最早者
        # 單一提交同時多違規：碼序最前者
        pairs = (
            ("PUSH-NOT-RECORDED", dict(record=False, extra={"README.md": "x\n"})),  # + PATH-OUTSIDE
            ("PUSH-RECORD-MISMATCH", dict(rec=("APP" + "-SI-901", "PROP" + "-SI-001"),
                                          extra={"README.md": "x\n"})),
            ("PUSH-PATH-OUTSIDE", dict(extra={"README.md": "x\n"}, tamper="多\n")),  # + CONTENT
        )
        for want, kw in pairs:
            with self.subTest(want):
                rr3 = self.rr()
                sha = rr3.patrol(**kw).sha
                self.blocked(rr3.evaluate(), want, sha)
        rr4 = self.rr()
        sha = rr4.patrol(
            extra={OBS: fx.read(rr4.R, OBS).replace(fx.obs_id(1), fx.obs_id(98), 1)}).sha
        # LEDGER-RULE 先於 CONTENT（亦未多改 touched）
        self.blocked(rr4.evaluate(), "PUSH-LEDGER-RULE", sha)
        rr5 = self.rr()
        app = rr5.app_id()
        rr5.event("app.promote", app, post=rr5.post())
        fx.put(rr5.R, EVL, rewrite_first_event(fx.read(rr5.R, EVL)))
        sha = rr5.commit([EVL], app=app)  # 帳本被改寫＋未改 touched（內容不符）→ LEDGER-RULE 先
        self.blocked(rr5.evaluate(), "PUSH-LEDGER-RULE", sha)

    def test_AT_749_4_E_11_non_ascii_paths_parse_and_git_failure_fails_closed(self):
        rr = self.rr()
        rel = f"{PROPS}/{rr.prop}/中文 附件.md"
        rr.patrol(extra={rel: "附件\n"})
        res = rr.evaluate()
        # 路徑被正確解出（不是引號化形、不是 PATH-OUTSIDE）；但檔名不在封閉樣式（審查 F-03）
        self.assertEqual((res["code"], "中文 附件.md" in res["detail"]), ("PUSH-LEDGER-RULE", True))
        real = Git.run

        def broken(git_self, *args, **kw):
            if "diff-tree" in args:
                return subprocess.CompletedProcess(args, 128, "", "fatal")
            return real(git_self, *args, **kw)
        with mock.patch.object(Git, "run", broken), mock.patch.object(Git, "run_bytes", broken):
            res2 = rr.evaluate()
        self.assertEqual((res2["ok"], res2["code"]), (False, "PUSH-GIT-UNAVAILABLE"))

        def no_blob(git_self, *args, **kw):  # 取內容一律走 `cat-file blob` 位元組（審查 F-08）
            return subprocess.CompletedProcess(args, 128, b"", b"fatal")
        with mock.patch.object(Git, "run_bytes", no_blob):
            res3 = rr.evaluate()
        self.assertEqual((res3["ok"], res3["code"]), (False, "PUSH-GIT-UNAVAILABLE"))

    def test_AT_749_4_E_12_amend_cannot_rewrite_obs_rows(self):
        rr = self.rr()
        p = rr.patrol()
        def row(ls):
            return [set_cell(ln, 3, "改寫") if ln.startswith(f"| {fx.obs_id(1)} |") else ln
                    for ln in ls]

        obs_edit(rr.R, row)
        fx.git(rr.R, "add", "--", OBS)
        fx.git(rr.R, "commit", "-q", "--amend", "--no-edit")
        new = fx.git(rr.R, "rev-parse", "HEAD")
        self.assertNotEqual(new, p.sha)
        self.blocked(rr.evaluate(), "PUSH-NOT-RECORDED", new)  # 新 sha 無紀錄
        rr.record(new, p.app)  # 偽造紀錄：sha、app、prop 皆相符
        self.blocked(rr.evaluate(), "PUSH-LEDGER-RULE", new)
        illegal = (
            ("final-to-final", lambda ls: [set_cell(ln, 7, "retired；依據 x:1") if ln.startswith(
                f"| {fx.obs_id(6)} |") else ln for ln in ls]),
            ("delete-row",
             lambda ls: [ln for ln in ls if not ln.startswith(f"| {fx.obs_id(10)} |")]),
            ("header",
             lambda ls: [ln.replace("| 處置 |", "| 處理 |") if ln.startswith("| ID |") else ln
                                   for ln in ls]),
        )
        for label, fn in illegal:
            with self.subTest(label):
                rr2 = self.rr()
                text = "\n".join(fn(fx.read(rr2.R, OBS).split("\n")))
                sha = rr2.patrol(extra={OBS: text}).sha
                self.blocked(rr2.evaluate(), "PUSH-LEDGER-RULE", sha, label)

    def test_AT_749_4_E_13_amend_cannot_smuggle_files(self):
        rr = self.rr()
        p = rr.patrol()
        rel = f"{PROPS}/{rr.prop}/x.txt"
        fx.put(rr.R, rel, "夾帶\n")
        fx.git(rr.R, "add", "--", rel)
        fx.git(rr.R, "commit", "-q", "--amend", "--no-edit")
        new = fx.git(rr.R, "rev-parse", "HEAD")
        self.blocked(rr.evaluate(), "PUSH-NOT-RECORDED", new)
        rr2 = self.rr()  # 夾帶改既有提案檔（紀錄被偽造的子案）
        sha = rr2.patrol(extra={f"{PROPS}/{rr2.prop}/r1.md": "被改寫\n"}).sha
        self.blocked(rr2.evaluate(), "PUSH-LEDGER-RULE", sha)
        self.assertNotEqual(p.sha, new)

    def test_AT_749_4_E_14_a_missing_empty_or_corrupt_record_file_is_not_a_record(self):
        rr = self.rr()
        sha = rr.patrol(record=False).sha
        self.assertFalse(commits_file(rr.si).exists())
        self.blocked(rr.evaluate(), "PUSH-NOT-RECORDED", sha)
        rr.raw_record(b"")
        self.blocked(rr.evaluate(), "PUSH-NOT-RECORDED", sha)
        rr.raw_record(b"{not json\n[1,2]\n")
        self.blocked(rr.evaluate(), "PUSH-NOT-RECORDED", sha)

    def test_AT_749_4_E_15_a_record_that_disagrees_with_the_trailer_is_refused(self):
        other_app, other_prop = "APP" + "-SI-901", "PROP" + "-SI-009"
        for label, rec in (("app", (other_app, "PROP" + "-SI-001")), ("prop", (None, other_prop))):
            with self.subTest(label):
                rr = self.rr()
                app = rr.app_id()
                rec = (rec[0] or app, rec[1])
                sha = rr.patrol(app=app, rec=rec).sha
                self.blocked(rr.evaluate(), "PUSH-RECORD-MISMATCH", sha, label)
        rr = self.rr()  # 同一 sha 多筆、最後一筆不符
        p = rr.patrol()
        rr.record(p.sha, other_app)
        self.blocked(rr.evaluate(), "PUSH-RECORD-MISMATCH", p.sha)

    def test_AT_749_4_E_17_existing_proposal_files_are_immutable_and_other_props_are_outside(self):
        rr = self.rr(other_prop=True)
        sha = rr.patrol(extra={f"{PROPS}/{rr.prop}/r1.md": "被改寫\n"}).sha
        self.blocked(rr.evaluate(), "PUSH-LEDGER-RULE", sha)
        rr2 = self.rr(other_prop=True)
        sha2 = rr2.patrol(extra={f"{PROPS}/{fx.pid(2)}/r1.md": "別人的\n"}).sha
        self.blocked(rr2.evaluate(), "PUSH-PATH-OUTSIDE", sha2)  # 他 PROP 目錄＝PATH-OUTSIDE 先判


# --------------------------------------------------------------------------- AC-SI-49-5 前置序
class TestPreconditionOrder(GuardTestCase):
    def test_AT_749_5_1_each_precondition_alone_gives_its_code(self):
        rr = self.rr()
        rr.patrol()
        res = rr.evaluate(enabled=False)
        self.assertEqual((res["code"], res["ok"]), ("PUSH-OFF", False))
        rf = self.rr()
        rf.patrol()
        fx.git(rf.R, "checkout", "-q", "-b", "feature")
        self.assertEqual(rf.evaluate()["code"], "PUSH-NOT-MAIN")
        rn = self.rr()
        rn.patrol()
        fx.git(rn.R, "branch", "--unset-upstream")
        self.assertEqual(rn.evaluate()["code"], "PUSH-NOT-MAIN")
        ro = self.rr()
        ro.patrol()
        other = fx.new_dir("bare")
        fx.git(fx.TMP, "init", "-q", "--bare", str(other))
        fx.git(ro.R, "remote", "add", "up2", str(other))
        fx.git(ro.R, "push", "-q", "-u", "up2", "main")
        self.assertEqual(ro.evaluate()["code"], "PUSH-NOT-MAIN")
        rz = self.rr()
        res = rz.evaluate()
        self.assertEqual((res["code"], res["ahead"]), ("PUSH-NOT-AHEAD", 0))
        rq = self.rr()
        rq.patrol()
        cur = rq.si / "push" / "current.json"
        cur.parent.mkdir(parents=True, exist_ok=True)
        cur.write_text(json.dumps({"sha": "a" * 40, "pid": 4242, "started_at": NOW.isoformat(),
                                   "wall_due_at": (NOW + timedelta(minutes=30)).isoformat()}),
                       encoding="utf-8")
        self.assertEqual(rq.evaluate(alive=lambda pid, started, *_a: True)["code"], "PUSH-RUNNING")
        self.assertEqual(rq.evaluate(alive=lambda pid, started, *_a: False)["ok"], True)  # 行程已死
        self.assertEqual(rq.evaluate(now=NOW + timedelta(hours=2))["ok"], True)  # 牆鐘已過
        cur.unlink()  # 同一測試內的家目錄共用：清掉，免得影響後面的子案
        rd = self.rr()
        rd.patrol()
        fx.put(rd.R, "notes/dirty.txt", "未提交\n")
        self.assertEqual(rd.evaluate()["code"], "PUSH-DIRTY-TREE")
        rg = self.rr()
        rg.patrol()
        h = rg.human()
        self.blocked(rg.evaluate(), "PUSH-FOREIGN-COMMITS", h)
        self.assertEqual(len(ALL_BLOCKING), 8)
        for code in ALL_BLOCKING:  # 專屬碼皆登記、皆為主機管理者要處理的阻擋碼
            self.assertEqual(nextstep.reason(code).who, "主機管理者")

    def test_AT_749_5_E_1_first_match_wins_and_git_failure_never_raises(self):
        rr = self.rr()
        rr.patrol()
        fx.put(rr.R, "notes/dirty.txt", "未提交\n")
        self.assertEqual(rr.evaluate(enabled=False)["code"], "PUSH-OFF")  # OFF 先於 DIRTY
        fx.git(rr.R, "checkout", "-q", "-b", "feature")
        self.assertEqual(rr.evaluate()["code"], "PUSH-NOT-MAIN")  # NOT-MAIN 先於 DIRTY
        rd = self.rr()
        rd.patrol()
        rd.human()
        fx.put(rd.R, "notes/dirty.txt", "未提交\n")
        self.assertEqual(rd.evaluate()["code"], "PUSH-DIRTY-TREE")  # DIRTY 先於 FOREIGN
        with mock.patch.object(Git, "run", return_value=None):
            res = rd.evaluate()
        self.assertEqual((res["ok"], res["code"]), (False, "PUSH-GIT-UNAVAILABLE"))
        real = Git.run

        def timed_out(git_self, *args, **kw):
            if "rev-list" in args:
                git_self.timed_out = True
                return None
            return real(git_self, *args, **kw)
        with mock.patch.object(Git, "run", timed_out):
            res = rd.evaluate()
        self.assertEqual((res["ok"], res["code"]), (False, "PUSH-GIT-UNAVAILABLE"))
        with self.assertRaises(ValueError):  # now 須帶 offset（鐵律三）
            rd.evaluate(now=datetime(2026, 11, 11, 12, 0, 0))


class TestSnapshotWiring(GuardTestCase):
    """`push_inputs` 接上守門：快照 `push` 區塊的 `blocked` 來自 `pushguard.evaluate`
    （AC-SI-49-10 的接點）。"""

    def test_push_inputs_shape_and_blocked_state(self):
        rr = self.rr()
        h = rr.human()
        params = {**fx.params_dict(), "sched_auto_push": True}
        ctx = patrol.Ctx(rr.R, NOW, False, patrol.Deps(), params)
        got = patrolreport.push_inputs(ctx, lambda pid, started, *_a: False)
        self.assertEqual(list(got), ["ahead", "head", "code", "detail"])
        self.assertEqual((got["ahead"], got["head"], got["code"], got["detail"]),
                         (1, h, "PUSH-FOREIGN-COMMITS", h[:8]))
        block = patrolreport.push_block(self.home, params, NOW, True, got, lambda *a: False)
        self.assertEqual((block["state"], block["code"], block["sha"]),
                         ("blocked", "PUSH-FOREIGN-COMMITS", h))
        off = patrolreport.push_inputs(
            patrol.Ctx(rr.R, NOW, False, patrol.Deps(), fx.params_dict()))
        self.assertEqual((off["code"], off["ahead"]), (None, 0))


# =========================================================================== PU
# 後半（AC-SI-49-6～49-13）
SECRET = "SE" + "CRET"  # 合成憑證字串一律於執行期拼出（機密掃描閘）
HOOK = pushguard.HOOK_MARK


def userinfo_url() -> str:
    return "https://" + "user" + ":" + "tok" + SECRET + "@github.com/x.git"


def head_of(R: Path) -> str:
    return fx.git(R, "rev-parse", "HEAD")


def sub_of(args: tuple) -> str | None:
    """git argv 的子命令（跳過 `-c k=v` 與旗標）。"""
    it = iter(args)
    for a in it:
        if a == "-c":
            next(it, None)
        elif not str(a).startswith("-"):
            return str(a)
    return None


def sleeper_pids(tag: str) -> list[int]:
    """命令列含 `sleep <tag>` 的行程 PID（現查行程表，不看標記檔）；平台各一條。"""
    if sys.platform == "win32":
        script = ("Get-CimInstance Win32_Process -Filter \"Name='sleep.exe'\" | "
                  f"Where-Object {{ $_.CommandLine -like '*sleep*{tag}*' }} | "
                  "ForEach-Object { $_.ProcessId }")
        argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    else:
        argv = ["ps", "-axo", "pid=,command="]
    cp = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                        check=False, timeout=60)
    if sys.platform == "win32":
        return [int(x) for x in cp.stdout.split() if x.isdigit()]
    return [int(ln.split(None, 1)[0]) for ln in cp.stdout.splitlines()
            if f"sleep {tag}" in ln and "ps -axo" not in ln]


class RunTestCase(GuardTestCase):
    """`push-run` 執行面基底：自動推送開啟、基線已推上遠端的暫存 repo（只在暫存目錄動 git）。"""

    def require_sleep_tool(self) -> None:
        """hook 載具需要 `sh` 與 `sleep`；找不到＝大聲失敗（不得略過、不得靜默當成綠）。"""
        git = shutil.which("git")
        usr_bin = Path(git).parents[1] / "usr" / "bin" if git else None
        has = (shutil.which("sleep") and shutil.which("sh")) or (
            usr_bin is not None and (usr_bin / "sleep.exe").exists())
        if not has:
            self.fail("TOOL-ABSENCE: pre-push hook 載具需要 sh 與 sleep（找不到）")

    def prr(self, **kw) -> p7x.PushRepo:
        rr = self.rr(**kw)
        fx.set_params(rr.R, sched_auto_push=True)
        fx.commit_all(rr.R, "p7 enable push")
        rr.push()
        return rr

    def remote_main(self, rr: p7x.PushRepo) -> str:
        return fx.git(rr.bare, "rev-parse", "refs/heads/main")

    def result_path(self, sha: str) -> Path:
        return self.home / "push" / "results" / f"{sha[:12]}.json"

    def result(self, sha: str) -> dict:
        return json.loads(self.result_path(sha).read_text(encoding="utf-8"))

    def put_result(self, sha: str, code: str, attempts: int, finished: datetime) -> None:
        path = self.result_path(sha)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"sha": sha, "finished_at": finished.isoformat(), "rc": 1,
                                    "code": code, "text": "x", "attempts": attempts,
                                    "tree_changed": False}), encoding="utf-8")

    def go(self, rr: p7x.PushRepo, spy=None, **kw):
        return patrolpush.run(rr.R, run_argv=spy or p7x.run_argv_spy(), now=kw.pop("now", NOW),
                              **kw)

    def home_blob(self) -> str:
        return "".join(p.read_bytes().decode("utf-8", "replace") for p in self.home.rglob("*")
                       if p.is_file())


# --------------------------------------------------------------------------- AC-SI-49-6
# 推送執行形態
class TestPushExecution(RunTestCase):
    def test_AT_749_6_1_explicit_sha_argv_and_a_clean_environment(self):
        rr = self.prr()
        sha = rr.patrol().sha
        parent = {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": "RUN", "KEEP_ME": "1",
                  "AUTOCLAUDE_SKIP_HOOKS": "1", "AUTOSDD_SI_AUDIT_KEY": "k"}
        spy = p7x.run_argv_spy()
        with mock.patch.dict(os.environ, parent):
            rc, out = self.go(rr, spy)
        self.assertEqual((rc, len(spy.calls)), (0, 1), out)
        call = spy.calls[0]
        base = self.remote_main(rr)  # 推前 ls-remote 的實值；lease 把它變成伺服器端條件
        self.assertEqual(call["argv"], [si_git.resolve_git(), "-C", str(rr.R),
                                        *si_git.PIN_ARGS(rr.R), "push",
                                        f"--force-with-lease=refs/heads/main:{base}", "origin",
                                        f"{sha}:refs/heads/main"])
        for bad in ("--force", "-f", "--no-verify", "--delete", "HEAD"):
            self.assertNotIn(bad, call["argv"])
        env = call["env"]
        for name in ("AUTOCLAUDE_SKIP_HOOKS", "AUTOSDD_SI_AUDIT_KEY", "AUTOSDD_UNATTENDED",
                     "AUTOSDD_SI_PATROL_RUN", "KEEP_ME"):
            self.assertNotIn(name, env)  # 允許清單：不在清單內的變數一律不傳（E-54）
        self.assertEqual((env["GIT_TERMINAL_PROMPT"], env["GCM_INTERACTIVE"]), ("0", "never"))
        self.assertEqual((env["GIT_NO_REPLACE_OBJECTS"], env["GIT_ATTR_NOSYSTEM"]), ("1", "1"))
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT"):
            if name in os.environ:
                self.assertEqual(env[name], os.environ[name], name)
        gitenv = patrolpush.push_env({"GIT_DIR": "a", "GIT_WORK_TREE": "b", "GIT_INDEX_FILE": "c",
                                      "PATH": "p", "AUTOSDD_UNATTENDED": "1"})
        self.assertEqual(sorted(gitenv), ["GCM_INTERACTIVE", "GIT_ATTR_NOSYSTEM", "GIT_GRAFT_FILE",
                                          "GIT_NO_REPLACE_OBJECTS", "GIT_TERMINAL_PROMPT", "PATH"])
        wall = json.loads(fx.read(rr.R, fx.PARAMS))["sched_push_wall_minutes"] * 60
        self.assertEqual((call["timeout"], call["cwd"]), (wall, rr.R))

    def test_AT_749_6_2_real_git_pushes_the_guarded_sha_not_head(self):
        rr = self.prr()
        sha = rr.patrol().sha
        rc, out = patrolpush.run(rr.R, now=NOW)  # 預設 run_argv＝真的 runner
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.remote_main(rr), sha)
        self.assertEqual(self.result(sha)["code"], "PUSH-OK")
        self.new_home()
        rr2 = self.prr()
        sha2 = rr2.patrol().sha
        late: list[str] = []
        with mock.patch.object(patrolpush, "BEFORE_SEND_HOOK",  # HEAD 復查之後的殘餘極短競態
                               lambda repo: late.append(rr2.human())):
            rc, out = patrolpush.run(rr2.R, now=NOW)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.remote_main(rr2), sha2)  # 遠端只前進到判定過的 sha、不含人工提交
        self.assertNotEqual(self.remote_main(rr2), late[0])
        self.assertEqual(self.result(sha2)["code"], "PUSH-OK")
        self.assertEqual(head_of(rr2.R), late[0])

    def test_AT_749_6_3_the_tree_is_rechecked_after_the_push(self):
        rr = self.prr()
        sha = rr.patrol().sha
        spy = p7x.run_argv_spy(out="To x\n", on_call=lambda: fx.put(rr.R, "notes/mid.txt", "新\n"))
        self.assertEqual(self.go(rr, spy)[0], 0)
        got = self.result(sha)
        self.assertEqual((got["code"], got["tree_changed"]), ("PUSH-OK", True))
        self.assertTrue(got["text"].endswith("；閘門期間工作樹有變動"), got["text"])
        self.new_home()
        rr2 = self.prr()
        sha2 = rr2.patrol().sha
        self.assertEqual(self.go(rr2, p7x.run_argv_spy())[0], 0)
        self.assertFalse(self.result(sha2)["tree_changed"])
        self.new_home()
        rr3 = self.prr()
        sha3 = rr3.patrol().sha
        # SI 自有路徑不算髒（與 sched.dirty_paths 同一判準）
        own = f"{PROPS}/{rr3.prop}/extra-mid.md"
        self.go(rr3, p7x.run_argv_spy(on_call=lambda: fx.put(rr3.R, own, "自有\n")))
        self.assertFalse(self.result(sha3)["tree_changed"])
        self.assertEqual(sched.dirty_paths(rr3.R), [])

    def test_AT_749_6_E_1_git_push_literal_lives_only_in_patrolpush(self):
        def argv_pushes(path: Path) -> int:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            hits = 0
            for node in ast.walk(tree):
                elems = (node.elts if isinstance(node, (ast.List, ast.Tuple)) else
                         node.args if isinstance(node, ast.Call) else [])
                hits += sum(1 for e in elems if isinstance(e, ast.Constant) and e.value == "push")
            return hits
        for name in ("patrol", "patrolrun", "patrolbrief", "schedarm", "sched", "schedwrite",
                     "pushguard", "patrolreport"):
            self.assertEqual(argv_pushes(PKG / f"{name}.py"), 0, name)
        self.assertGreaterEqual(argv_pushes(PKG / "patrolpush.py"), 1)
        lines = (PKG / "patrolpush.py").read_text(encoding="utf-8").splitlines()
        self.assertEqual([ln for ln in lines if "subprocess" in ln], [])
        self.assertEqual(sorted(p.name for p in PKG.glob("*.py") if argv_pushes(p)),
                         ["patrolpush.py"])


# --------------------------------------------------------------------------- AC-SI-49-7 結果分類碼
PUSH_FAIL_SAMPLES = (
    ("wall", None, True, "x", "PUSH-WALL-EXCEEDED"),
    ("ok", 0, False, "To /bare\n   abc..def  main -> main\n", "PUSH-OK"),
    ("hook-only", 1, False, f"{HOOK} 範圍含 AutoClaude/\n1 failed\nerror: failed to push some "
     "refs to '/bare'\n", "PUSH-HOOK-FAILED"),
    ("hook-then-auth", 1, False, f"{HOOK} 通過\nremote: Invalid username or password.\n"
     "fatal: Authentication failed for 'https://github.com/x.git/'\n", "PUSH-AUTH"),
    ("hook-then-reject", 1, False, f"{HOOK} 通過\nTo /bare\n ! [rejected]        main -> main "
     "(fetch first)\nerror: failed to push some refs\n", "PUSH-REJECTED"),
    ("hook-then-net", 1, False, f"{HOOK} 通過\nfatal: unable to access 'https://github.com/x.git/':"
     " Could not resolve host: github.com\n", "PUSH-FAILED"),
    ("bare-auth-prompt", 128, False, "fatal: could not read Username for 'https://github.com': "
     "terminal prompts disabled\n", "PUSH-AUTH"),
    ("bare-ssh", 128, False, "git@github.com: Permission denied (publickey).\n", "PUSH-AUTH"),
    ("bare-403", 128, False, "fatal: unable to access 'https://x/': The requested URL returned "
     "error: 403\n", "PUSH-AUTH"),
    ("bare-remote-rejected", 1, False, "To x\n ! [remote rejected] main -> main (protected "
     "branch hook declined)\n", "PUSH-REJECTED"),
    ("bare-nff", 1, False, "hint: Updates were rejected because the tip is behind\n",
     "PUSH-REJECTED"),
    ("bare-net", 128, False, "fatal: unable to access 'https://x/': Connection timed out\n",
     "PUSH-FAILED"),
    ("bare-other", 128, False, "fatal: something odd\n", "PUSH-FAILED"),
)


class TestClassify(RunTestCase):
    def test_AT_749_7_1_every_sample_gets_its_code(self):
        for name, rc, timed_out, output, want in PUSH_FAIL_SAMPLES:
            with self.subTest(name):
                self.assertEqual(pushguard.classify(rc, timed_out, output), want)

    def test_AT_749_7_E_1_hook_log_words_never_decide_the_code(self):
        noisy = (
            f"{HOOK} 開始\nConnection refused\nAuthentication failed\nfatal: unable to access x\n"
                 f"{HOOK} ❌ 閘門失敗\nerror: failed to push some refs to '/bare'\n")
        self.assertEqual(pushguard.classify(1, False, noisy), "PUSH-HOOK-FAILED")
        self.assertEqual(
            pushguard.classify(1, False, f"{HOOK} 通過\nfatal: Authentication failed\n"),
                         "PUSH-AUTH")
        self.assertEqual(pushguard.classify(1, False, f"{HOOK} 通過\n ! [rejected] main -> main "
                                            "(fetch first)\n"), "PUSH-REJECTED")
        self.assertEqual(pushguard.classify(None, True, noisy), "PUSH-WALL-EXCEEDED")
        self.assertEqual(pushguard.classify(1, False, ""), "PUSH-FAILED")
        self.assertEqual(pushguard.classify(1, False, None), "PUSH-FAILED")

    def test_AT_749_7_2_masking_keeps_credentials_out_of_every_file_and_the_stdout(self):
        url = userinfo_url()
        self.assertEqual(pushguard.mask(f"see {url} now"), "see https://***@github.com/x.git now")
        self.assertEqual(pushguard.mask("token=abc123 and password: xyz"),
                         "token=*** and password: ***")
        rr = self.prr()
        sha = rr.patrol().sha
        err = f"fatal: unable to access '{url}': token=abc123 password: xyz\n"
        rc, out = self.go(rr, p7x.run_argv_spy(rc=128, err=err))
        self.assertEqual(rc, 1, out)
        got = self.result(sha)
        self.assertEqual(got["text"], "fatal: unable to access 'https://***@github.com/x.git': "
                                      "token=*** password: ***")
        self.assertLessEqual(len(got["text"]), 160)
        blob = self.home_blob() + out
        for secret in (SECRET, "abc123", "xyz"):
            self.assertNotIn(secret, blob)
        long = pushguard.last_line("x" * 500)
        self.assertEqual(len(long), 160)


# --------------------------------------------------------------------------- AC-SI-49-8 重試政策
class TestRetryPolicy(RunTestCase):
    def test_AT_749_8_1_final_failures_are_not_retried_for_the_same_sha(self):
        rr = self.prr()
        old = rr.patrol().sha
        for code in ("PUSH-HOOK-FAILED", "PUSH-REJECTED", "PUSH-AUTH"):
            with self.subTest(code):
                self.put_result(old, code, 1, NOW - timedelta(days=1))
                res = pushguard.evaluate(rr.R, {**real_params(), "sched_auto_push": True},
                                         self.home,
                                         NOW, gate_retry=True)
                self.assertEqual((res["ok"], res["code"]), (False, "PUSH-ATTEMPTS-EXHAUSTED"))
                spy = p7x.run_argv_spy()
                before = self.result_path(old).read_bytes()
                rc, out = self.go(rr, spy)
                self.assertEqual((rc, spy.calls), (0, []), out)
                self.assertIn("PUSH-ATTEMPTS-EXHAUSTED", out)
                self.assertEqual(self.result_path(old).read_bytes(), before)  # attempts 不增
        new = rr.patrol().sha  # 新的巡邏提交：新 sha 無結果檔，守門重新放行
        spy = p7x.run_argv_spy()
        self.assertEqual(self.go(rr, spy)[0], 0)
        self.assertEqual(spy.calls[0]["argv"][-1], f"{new}:refs/heads/main")

    def test_AT_749_8_2_retryable_codes_wait_then_stop_at_the_attempt_cap(self):
        rr = self.prr()
        sha = rr.patrol().sha
        prm = {**real_params(), "sched_auto_push": True}
        gap = timedelta(minutes=prm["sched_push_retry_minutes"])
        for code in ("PUSH-FAILED", "PUSH-WALL-EXCEEDED"):
            with self.subTest(code):
                self.put_result(sha, code, 1, NOW - gap + timedelta(minutes=1))
                res = pushguard.evaluate(rr.R, prm, self.home, NOW, gate_retry=True)
                self.assertEqual((res["ok"], res["code"]), (False, "PUSH-RETRY-WAIT"))
                self.put_result(sha, code, 1, NOW - gap)
                self.assertTrue(
                    pushguard.evaluate(rr.R, prm, self.home, NOW, gate_retry=True)["ok"])
                self.put_result(sha, code, prm["sched_push_attempts_max"], NOW - 2 * gap)
                res = pushguard.evaluate(rr.R, prm, self.home, NOW, gate_retry=True)
                self.assertEqual(res["code"], "PUSH-ATTEMPTS-EXHAUSTED")
        self.put_result(sha, "PUSH-FAILED", 1, NOW - 2 * gap)
        spy = p7x.run_argv_spy(rc=128, err="fatal: unable to access 'x': Could not resolve host\n")
        rc, out = self.go(rr, spy)
        self.assertEqual((rc, len(spy.calls)), (1, 1), out)
        self.assertEqual((self.result(sha)["attempts"], self.result(sha)["code"]),
                         (2, "PUSH-FAILED"))
        with self.assertRaises(ValueError):
            pushguard.evaluate(rr.R, prm, self.home, datetime(2026, 11, 11, 12, 0, 0),
                               gate_retry=True)

    def test_AT_749_8_3_success_overwrites_the_old_failure(self):
        rr = self.prr()
        sha = rr.patrol().sha
        fail = p7x.run_argv_spy(rc=128, err="fatal: unable to access 'x': Could not resolve host\n")
        self.assertEqual(self.go(rr, fail)[0], 1)
        self.assertEqual(self.result(sha)["attempts"], 1)
        later = NOW + timedelta(minutes=real_params()["sched_push_retry_minutes"] + 1)
        rc, out = patrolpush.run(rr.R, now=later)  # 真 git 推到本機 bare
        self.assertEqual(rc, 0, out)
        got = self.result(sha)
        self.assertEqual((got["code"], got["attempts"]), ("PUSH-OK", 2))
        prm = {**real_params(), "sched_auto_push": True}
        ctx = patrol.Ctx(rr.R, later, False, patrol.Deps(), prm)
        guard = patrolreport.push_inputs(ctx, lambda pid, started, *_a: False)
        block = patrolreport.push_block(self.home, prm, later, True, guard, lambda *a: False)
        self.assertEqual((block["state"], block["code"], block["attempts"]), ("ok", "PUSH-OK", 2))


# --------------------------------------------------------------------------- AC-SI-49-9 鎖、牆鐘、
# 單例
class TestLockAndWall(RunTestCase):
    def test_AT_749_9_1_a_held_lock_means_push_running_and_a_stale_lock_is_reclaimed(self):
        from lib import apply_lock
        rr = self.prr()
        sha = rr.patrol().sha
        lock = self.home / "locks" / "push.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        spy = p7x.run_argv_spy()
        with apply_lock.acquire(lock, 0, 999999):
            rc, out = self.go(rr, spy)
        self.assertEqual((rc, spy.calls), (0, []), out)
        self.assertIn("PUSH-RUNNING", out)
        self.assertFalse(self.result_path(sha).exists())
        self.assertEqual(self.go(rr, spy)[0], 0)  # 持鎖者結束後可推
        self.assertEqual(len(spy.calls), 1)
        self.assertFalse(lock.exists())
        lock.write_text("99999999\n2020-01-01T00:00:00+00:00\n", encoding="utf-8")  # 陳舊鎖
        old = time.time() - 100000
        os.utime(lock, (old, old))
        self.put_result(sha, "PUSH-FAILED", 1, NOW - timedelta(days=1))
        rc, out = self.go(rr, spy)
        self.assertEqual((rc, len(spy.calls)), (0, 2), out)

    def test_AT_749_9_2_wall_clock_kills_the_whole_process_tree(self):
        rr = self.prr()
        sha = rr.patrol().sha
        rc, out = self.go(rr, p7x.run_argv_spy(timed_out=True, rc=None))
        self.assertEqual(rc, 1, out)
        got = self.result(sha)
        self.assertEqual((got["code"], got["attempts"]), ("PUSH-WALL-EXCEEDED", 1))
        self.assertFalse((self.home / "push" / "current.json").exists())
        self.new_home()
        rr2 = self.prr()
        sha2 = rr2.patrol().sha
        nap = [sys.executable, "-c", "import time; time.sleep(30)"]
        wants = "job-unavailable:boom taskkill-fallback:boom"
        posix = "killpg"  # POSIX：行程自成群組、整群 SIGKILL，note 如實報告所用手法
        for patched, want in ((None, "job-terminated"), ((None, "boom"), wants)):
            t1 = time.monotonic()
            with (mock.patch.object(runner, "_job_open", return_value=patched) if patched
                  else contextlib.nullcontext()):
                res = runner.run_argv(nap, env=dict(os.environ), timeout=1)
            self.assertTrue(res.timed_out)
            self.assertLess(time.monotonic() - t1, 1 + runner.KILL_GRACE_SECONDS)
            # 可查字樣、不靜默
            self.assertEqual(res.note, want if sys.platform == "win32" else posix)
        self.require_sleep_tool()
        tag, wall = "27.31", 3
        started = fx.new_dir("hookstarted")
        hook = rr2.R / ".git" / "hooks" / "pre-push"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_bytes(f"#!/bin/sh\necho s > '{started.as_posix()}'\nsleep {tag}\n".encode())
        hook.chmod(0o755)
        seen: set[int] = set()
        stop = threading.Event()

        def watch() -> None:
            while not stop.is_set():
                seen.update(sleeper_pids(tag))
                stop.wait(0.5)
        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        spans: list[float] = []  # 牆鐘那一次 `run_argv` 自己的耗時（不含守門的 git 呼叫與收尾）
        real_run = runner.run_argv

        def timed(*a, **kw):
            t_in = time.monotonic()
            try:
                return real_run(*a, **kw)
            finally:
                if kw.get("timeout") == wall:
                    spans.append(time.monotonic() - t_in)
        try:
            with (mock.patch.object(patrolpush, "WALL_SECONDS_OVERRIDE", wall),
                  mock.patch.object(runner, "run_argv", timed)):
                rc, out = patrolpush.run(rr2.R, now=NOW)
        finally:
            stop.set()
            watcher.join(5)
        survivors = sleeper_pids(tag)
        for pid in survivors:  # 先清掉再斷言，免得紅燈留下孤兒
            with contextlib.suppress(OSError):
                os.kill(pid, 15)
        self.assertEqual(rc, 1, out)
        self.assertEqual(self.result(sha2)["code"], "PUSH-WALL-EXCEEDED")
        self.assertTrue(started.exists())  # hook 真的跑起來了
        self.assertTrue(seen, "測試載具沒看到 hook 的孫行程（sleep），鑑別力不成立")
        self.assertEqual(survivors, [], "逾時後孫行程仍在")  # (i) 整棵樹都被收掉
        grace = getattr(runner, "KILL_GRACE_SECONDS", 5)
        # (ii) 量 run_argv 自己：整段 patrolpush.run 還含守門的數十次 git 呼叫（共用 runner 上
        # 這部分不受本實作控制）；砍樹沒生效時 run_argv 會再等滿 grace，必 ≥ wall + grace
        self.assertEqual(len(spans), 1, spans)
        self.assertLess(spans[0], wall + grace, "run_argv 沒在逾時＋寬限內返回")
        self.assertNotEqual(self.remote_main(rr2), sha2)
        self.normal_completion_leaves_background_alone()  # (iii)

    def normal_completion_leaves_background_alone(self) -> None:
        """(iii) 正常路徑不變：沒逾時時，子行程留下的背景行程不被殺（Job 只在逾時才終止）。"""
        self.new_home()
        rr = self.prr()
        sha = rr.patrol().sha
        tag = "31.41"
        hook = rr.R / ".git" / "hooks" / "pre-push"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_bytes(f"#!/bin/sh\nsleep {tag} >/dev/null 2>&1 &\nexit 0\n".encode())
        hook.chmod(0o755)
        try:
            rc, out = patrolpush.run(rr.R, now=NOW)
            self.assertEqual(rc, 0, out)
            self.assertEqual(self.result(sha)["code"], "PUSH-OK")
            alive = sleeper_pids(tag)
            self.assertTrue(alive, "正常結束後背景行程被殺了")
        finally:
            for pid in sleeper_pids(tag):
                with contextlib.suppress(OSError):
                    os.kill(pid, 15)

    def test_AT_749_9_3_a_crashed_run_never_pins_the_push_forever(self):
        rr = self.prr()
        sha = rr.patrol().sha
        cur = self.home / "push" / "current.json"
        cur.parent.mkdir(parents=True, exist_ok=True)

        def residue(wall_min: int = 30, pid: int = 4242) -> None:
            cur.write_text(json.dumps({"sha": sha, "pid": pid, "started_at": NOW.isoformat(),
                                       "wall_due_at": (NOW + timedelta(minutes=wall_min)
                                                       ).isoformat()}), encoding="utf-8")
        prm = {**real_params(), "sched_auto_push": True}
        residue()
        spy = p7x.run_argv_spy()
        rc, out = self.go(rr, spy, alive=lambda pid, started, *_a: True)  # 存活且未逾牆
        self.assertEqual((rc, spy.calls), (0, []), out)
        self.assertIn("PUSH-RUNNING", out)
        residue()
        self.assertEqual(self.go(rr, spy, alive=lambda pid, started, *_a: False)[0], 0)  # 行程已死
        self.assertEqual(len(spy.calls), 1)
        self.assertFalse(cur.exists())  # 覆寫後一律刪除
        self.put_result(sha, "PUSH-FAILED", 1, NOW - timedelta(days=1))
        residue(wall_min=30)
        later = NOW + timedelta(hours=2)  # pid 存活但已逾 wall_due_at：視為不在跑，且不殺他人行程
        self.assertTrue(pushguard.evaluate(rr.R, prm, self.home, later,
                                           alive=lambda pid, started, *_a: True)["ok"])
        cur.write_text("{ 損壞", encoding="utf-8")
        self.assertTrue(pushguard.evaluate(rr.R, prm, self.home, NOW,
                                           alive=lambda pid, started, *_a: True)["ok"])
        self.assertEqual(self.go(rr, spy, alive=lambda pid, started, *_a: True)[0], 0)

    def test_AT_749_9_E_1_a_failed_result_write_never_re_pushes(self):
        rr = self.prr()
        sha = rr.patrol().sha
        real = os.replace

        def selective(src, dst, *a, **kw):
            if "results" in Path(dst).parts:
                raise OSError("disk full")
            return real(src, dst, *a, **kw)
        spy = p7x.run_argv_spy()
        with mock.patch.object(patrolpush.os, "replace", selective):
            rc, out = self.go(rr, spy)
        self.assertEqual((rc, len(spy.calls)), (1, 1), out)
        self.assertIn("PUSH-RESULT-WRITE-FAILED", out)
        self.assertFalse((self.home / "push" / "current.json").exists())
        self.assertFalse(self.result_path(sha).exists())

    def test_AT_749_9_4_an_unhandled_exception_leaves_a_trace_and_releases_everything(self):
        rr = self.prr()
        sha = rr.patrol().sha
        boom = RuntimeError("boom token=" + "abc123")
        spy = p7x.run_argv_spy(raises=boom)
        rc, out = self.go(rr, spy)
        self.assertEqual((rc, len(spy.calls)), (1, 1), out)
        self.assertIn("PUSH-INTERNAL-ERROR", out)
        err = json.loads((self.home / "push" / "last_error.json").read_text(encoding="utf-8"))
        self.assertEqual(list(err), ["at", "code", "text"])
        self.assertEqual((err["code"], err["text"]),
                         ("PUSH-INTERNAL-ERROR", "RuntimeError: boom token=***"))
        self.assertIsNotNone(datetime.fromisoformat(err["at"]).utcoffset())
        self.assertFalse((self.home / "push" / "current.json").exists())
        self.assertFalse((self.home / "locks" / "push.lock").exists())
        self.assertNotIn("abc123", self.home_blob() + out)
        prm = {**real_params(), "sched_auto_push": True}
        ctx = patrol.Ctx(rr.R, NOW, False, patrol.Deps(), prm)
        guard = patrolreport.push_inputs(ctx, lambda pid, started, *_a: False)
        block = patrolreport.push_block(self.home, prm, NOW, True, guard, lambda *a: False)
        self.assertEqual((block["state"], block["code"]), ("failed", "PUSH-INTERNAL-ERROR"))
        # 守門本身拋
        with mock.patch.object(pushguard, "evaluate", side_effect=RuntimeError("boom2")):
            rc2, out2 = self.go(rr, p7x.run_argv_spy())
        self.assertEqual(rc2, 1, out2)
        later = NOW + timedelta(minutes=1)  # 之後成功：結果比 last_error 晚，錯誤檔不再影響狀態
        self.assertEqual(self.go(rr, p7x.run_argv_spy(), now=later)[0], 0)
        self.put_result(sha, "PUSH-FAILED", 1, later + timedelta(minutes=1))
        block = patrolreport.push_block(self.home, prm, later + timedelta(minutes=5), True, guard,
                                        lambda *a: False)
        self.assertNotEqual(block["code"], "PUSH-INTERNAL-ERROR")


# --------------------------------------------------------------------------- AC-SI-49-10 快照 push
# 區塊
SHA_X = "a" * 40
BLOCKING = ("PUSH-NOT-MAIN", "PUSH-DIRTY-TREE", "PUSH-FOREIGN-COMMITS", "PUSH-APP-KIND-INVALID",
            "PUSH-APP-REUSED", "PUSH-PATH-OUTSIDE", "PUSH-CONTENT-MISMATCH", "PUSH-NOT-RECORDED",
            "PUSH-RECORD-MISMATCH", "PUSH-LEDGER-RULE", "PUSH-GIT-UNAVAILABLE")
STATES = ("off", "idle", "pending", "waiting-login", "running", "ok", "failed", "blocked")


class TestSnapshotPushBlock(ChainTestCase):
    def block(self, *, enabled=True, ahead=1, code=None, detail=None, cur=None, last=None, err=None,
              tick=None, ok_result=None, alive=False, now=NOW, params=None, guard=True,
              blocked=None) -> dict:
        folder = self.home / "push"
        shutil.rmtree(folder, ignore_errors=True)
        (folder / "results").mkdir(parents=True)
        for name, obj in (("current.json", cur), ("last_error.json", err), ("tick.json", tick),
                          ("blocked.json", blocked)):
            if obj is not None:
                (folder / name).write_text(json.dumps(obj), encoding="utf-8")
        for obj in (last, ok_result):
            if obj is not None:
                (folder / "results" / f"{obj['sha'][:12]}.json").write_text(json.dumps(obj),
                                                                           encoding="utf-8")
        gd = {"ahead": ahead, "head": SHA_X, "code": code, "detail": detail} if guard else None
        prm = params or {**fx.params_dict(), "sched_auto_push": True}
        return patrolreport.push_block(self.home, prm, now, enabled, gd, lambda *a: alive)

    @staticmethod
    def res(code: str, attempts: int, finished: datetime, sha: str = SHA_X) -> dict:
        return {"sha": sha, "finished_at": finished.isoformat(), "rc": 1, "code": code, "text": "x",
                "attempts": attempts, "tree_changed": False}

    def text_of(self, code: str, detail=None) -> str:
        return sched.line1(nextstep.reason(code, detail or None).text, patrolreport.TEXT_MAX)

    def test_AT_749_10_1_the_heartbeat_never_pushes_and_uses_only_read_git(self):
        R, prop, _ = self.promotable()
        fx.set_params(R, sched_auto_push=True)
        fx.commit_all(R, "auto-push-on")
        self.with_remote(R)
        with git_calls() as seen:
            # 推進類動詞以替身：只量巡邏器自己的 git
            rc, out, err = self.beat(R, BEAT_NOW, p7x.Rig7())
        self.assertEqual(rc, 0, out + err)
        subs = {sub_of(a) for a in seen}
        allowed = {"status", "add", "commit", "rev-parse", "diff", "log", "show", "rev-list",
                   "diff-tree", "symbolic-ref", "for-each-ref", "config", "ls-files"}
        self.assertNotIn("push", subs)
        self.assertLessEqual(subs - {None}, allowed)
        tree = ast.parse((PKG / "patrol.py").read_text(encoding="utf-8"))
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                    for a in n.names}
        self.assertNotIn("patrolpush", imported)
        self.assertEqual(self.report()["push"]["enabled"], True)

    def test_AT_749_10_2_the_state_table_is_exclusive_and_texts_come_from_the_table(self):
        rows = []
        rows.append(("off", self.block(enabled=False)))
        rows.append(
            ("running", self.block(cur={"sha": SHA_X, "pid": 1, "started_at": NOW.isoformat(),
                                                "wall_due_at": (NOW + 30 * MINUTE).isoformat()},
                                           alive=True)))
        rows.append(("ok", self.block(ahead=0, ok_result=self.res("PUSH-OK", 2, NOW, "b" * 40))))
        rows.append(("idle", self.block(ahead=0)))
        for code in BLOCKING:
            rows.append(("blocked", self.block(code=code, detail=SHA_X[:8])))
        for code in ("PUSH-HOOK-FAILED", "PUSH-REJECTED", "PUSH-AUTH"):
            rows.append(("failed", self.block(last=self.res(code, 1, NOW))))
        prm = {**fx.params_dict(), "sched_auto_push": True}
        gap = timedelta(minutes=prm["sched_push_retry_minutes"])
        for code in ("PUSH-WALL-EXCEEDED", "PUSH-FAILED"):
            rows.append(("failed", self.block(last=self.res(code, prm["sched_push_attempts_max"],
                                                            NOW - 2 * gap))))
            rows.append(("failed", self.block(last=self.res(code, 1, NOW - gap + 1 * MINUTE))))
        rows.append(("failed", self.block(err={"at": NOW.isoformat(), "code": "PUSH-INTERNAL-ERROR",
                                               "text": "RuntimeError: x"})))
        hb = prm["sched_heartbeat_minutes"]
        tick = lambda delta: {"tick_at": (NOW - delta).isoformat(), "by": "push-run"}  # noqa: E731
        rows.append(("pending", self.block(tick=tick(timedelta(minutes=2 * hb + 5)))))  # 恰在界上
        rows.append(("waiting-login", self.block(tick=tick(timedelta(minutes=2 * hb + 6)))))
        rows.append(("waiting-login", self.block()))
        rows.append(("waiting-login", self.block(tick={"tick_at": "不是 ISO", "by": "x"})))
        for want, got in rows:
            with self.subTest(want=want, code=got["code"]):
                self.assertEqual(got["state"], want)
                self.assertIn(got["state"], STATES)
                self.assertEqual(list(got), list(patrolreport._PUSH_KEYS))  # noqa: SLF001
                self.assertTrue(got["code"] and got["text"])
                if want != "failed":
                    self.assertIsNone(got["retry"])
        by = {r[1]["code"]: r[1] for r in rows}
        self.assertEqual(by["PUSH-OFF"]["text"], self.text_of("PUSH-OFF"))
        for code in BLOCKING:
            got = next(g for w, g in rows if g["code"] == code)
            self.assertEqual(got["text"], self.text_of(code, SHA_X[:8]), code)
        retries = [g["retry"] for w, g in rows if w == "failed"]
        self.assertEqual(retries, ["never"] * 3 + ["exhausted", "wait", "exhausted", "wait", None])
        pending = next(g for w, g in rows if w == "pending")
        self.assertEqual((pending["code"], pending["sha"]), ("PUSH-PENDING", SHA_X))
        # last_error 比最近結果舊 ⇒ 不算失敗（A.4b 第 6 條）
        older = self.block(last=self.res("PUSH-FAILED", 1, NOW - 2 * gap),
                           err={"at": (NOW - 3 * gap).isoformat(), "code": "PUSH-INTERNAL-ERROR",
                                "text": "x"})
        self.assertEqual(older["state"], "waiting-login")
        self.assertEqual(self.block(ahead=3)["ahead"], 3)

    def test_AT_749_10_4_snapshot_shows_the_off_state_blocked_file_and_runner_note(self):
        hb = fx.params_dict()["sched_heartbeat_minutes"]
        for off_flag in (False, True):  # ①預設關閉（巡邏 OFF 與否皆同）：state off、固定白話句
            got = self.block(enabled=False, params={**fx.params_dict(),
                                                    "sched_auto_push": off_flag})
            self.assertEqual((got["enabled"], got["state"], got["code"]), (False, "off",
                                                                           "PUSH-OFF"))
            self.assertEqual((got["retry"], got["sha"], got["finished_at"]), (None, None, None))
            self.assertIn("未啟用", got["text"])
            self.assertIn("預設關閉", got["text"])
        tick = {"tick_at": NOW.isoformat(), "by": "push-run"}
        for code in ("PUSH-REMOTE-DRIFT", "PUSH-REMOTE-DIVERGED"):  # ②blocked.json
            blocked = {"code": code, "detail": "aaaaaaaa bbbbbbbb", "head": SHA_X,
                       "at": NOW.isoformat()}
            got = self.block(blocked=blocked, tick=tick)
            self.assertEqual((got["state"], got["code"], got["sha"]), ("blocked", code, SHA_X))
            self.assertEqual(got["text"], self.text_of(code, "aaaaaaaa bbbbbbbb"))
        stale = timedelta(minutes=2 * hb + 6)
        for label, kw, state in (
                ("other-head", dict(blocked={**blocked, "head": "c" * 40}, tick=tick), "pending"),
                ("stale-tick", dict(blocked=blocked,
                                    tick={"tick_at": (NOW - stale).isoformat(), "by": "x"}),
                 "waiting-login"),
                ("no-tick", dict(blocked=blocked), "waiting-login")):
            # 忽略該檔（落入 A.4b 後面幾項）
            self.assertEqual(self.block(**kw)["state"], state, label)
        self.assertEqual(self.block(blocked=blocked, tick=tick, guard=True,
                                    code="PUSH-PATH-OUTSIDE", detail=SHA_X[:8])["code"],
                         "PUSH-PATH-OUTSIDE")  # 守門自己的碼先判（blocked.json 排在其後）
        note = "job-unavailable:boom；output-incomplete"  # ③runner_note 接在固定句後（總長 ≤130）
        last = {**self.res("PUSH-WALL-EXCEEDED", 1, NOW - 1 * MINUTE), "runner_note": note}
        got = self.block(last=last)
        self.assertTrue(got["text"].startswith(self.text_of("PUSH-WALL-EXCEEDED")[:20]))
        self.assertIn("（備註：", got["text"])
        self.assertNotIn("\n", got["text"])
        self.assertLessEqual(len(got["text"]), 130)
        keys = patrolreport._PUSH_KEYS  # noqa: SLF001  # 鍵集合與鍵序不變
        self.assertEqual(list(got), list(keys))
        self.assertEqual(self.block(last=self.res("PUSH-FAILED", 1, NOW - 1 * MINUTE))["text"],
                         self.text_of("PUSH-FAILED"))  # 無備註＝只有固定句

    def test_AT_749_10_3_no_promote_while_a_push_is_running(self):
        R, prop, _ = self.promotable()
        self.with_remote(R)
        cur = self.home / "push" / "current.json"
        cur.parent.mkdir(parents=True, exist_ok=True)
        wall = datetime.now().astimezone() + timedelta(minutes=30)
        cur.write_text(json.dumps({"sha": SHA_X, "pid": 4242, "started_at": BEAT_NOW.isoformat(),
                                   "wall_due_at": wall.isoformat()}), encoding="utf-8")
        rig = Rig()
        rig.live.add(4242)
        self.assertEqual(self.beat(R, BEAT_NOW, rig)[0], 0)
        self.assertEqual([e for e in fx.EV(R) if e["kind"] == "app.promote"], [])
        row = next(r for r in self.report()["props"] if r["id"] == prop)
        self.assertEqual((row["code"], row["who"]), ("PUSH-IN-PROGRESS", "巡邏器"))
        self.assertTrue(any("PUSH-IN-PROGRESS" in ln for ln in self.logs()))
        cur.unlink()  # 推送結束後下一心跳照常 promote
        self.assertEqual(self.beat(R, BEAT_NOW + timedelta(minutes=5), Rig())[0], 0)
        self.assertTrue([e for e in fx.EV(R) if e["kind"] == "app.promote"])

    def test_AT_749_10_E_1_git_trouble_blocks_the_push_block_only(self):
        self.assertEqual((pushguard.CALL_TIMEOUT, pushguard.TOTAL_BUDGET), (20, 60))
        got = self.block(guard=False)
        self.assertEqual((got["state"], got["code"]), ("blocked", "PUSH-GIT-UNAVAILABLE"))
        rr = p7x.push_repo(self)
        rr.patrol()
        seen: list[tuple] = []
        orig = Git.run

        def rec(git_self, *args, **kw):
            seen.append((args, kw.get("timeout")))
            return orig(git_self, *args, **kw)
        with mock.patch.object(Git, "run", rec):
            self.assertTrue(rr.evaluate()["ok"])
        for args, timeout in seen:
            if sub_of(args) in ("rev-list", "diff-tree", "show", "symbolic-ref"):
                self.assertEqual(timeout, 20, args)
        prm = {**real_params(), "sched_auto_push": True}
        ctx = patrol.Ctx(rr.R, NOW, False, patrol.Deps(), prm)
        with mock.patch.object(pushguard, "evaluate", wraps=pushguard.evaluate) as spy:
            patrolreport.push_inputs(ctx)
        self.assertEqual(spy.call_count, 1)  # 每心跳一次
        with mock.patch.object(Git, "run", return_value=None):
            res = patrolreport.push_inputs(ctx)
        self.assertEqual(res["code"], "PUSH-GIT-UNAVAILABLE")  # 不拋例外


MINUTE = timedelta(minutes=1)


# --------------------------------------------------------------------------- AC-SI-49-11 授權與 rc
class TestAuthAndRc(RunTestCase):
    def test_AT_749_11_1_unattended_environments_are_refused_with_zero_writes(self):
        self.assertIn("push-run", unattended.C_CLASS)
        self.assertEqual(len(unattended.C_CLASS), 16)
        self.assertEqual(unattended.gate("push-run", None, {}), [])
        self.assertNotIn("push-run", unattended.READONLY)
        rr = self.prr()
        rr.patrol()
        spy = p7x.run_argv_spy()
        for value in ("1", "0"):  # 字面 0 也算有設
            with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": value}), mock.patch.object(
                    runner, "run_argv", spy):
                rc, out, err = self.M(rr.R, "push-run")
            self.assertEqual(rc, 1, out + err)
            self.assertIn("UNATTENDED-REFUSED", out)
        self.assertEqual(spy.calls, [])
        self.assertEqual(sorted(p.name for p in (self.home / "push").iterdir()),
                         ["armed.json", "commits.jsonl"])  # 只有夾具留下的紀錄；tick.json 也沒寫

    def test_AT_749_11_2_rc_contract(self):
        rr = self.prr()
        sha = rr.patrol().sha
        spy = p7x.run_argv_spy()
        rc, out = self.go(rr, spy, dry_run=True)
        self.assertEqual((rc, spy.calls), (0, []), out)
        self.assertEqual(sorted(p.name for p in (self.home / "push").iterdir()),
                         ["armed.json", "commits.jsonl"])
        self.assertEqual(self.go(rr, spy)[0], 0)  # 推成功
        self.assertTrue((self.home / "push" / "tick.json").exists())
        tick = json.loads((self.home / "push" / "tick.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(datetime.fromisoformat(tick["tick_at"]).utcoffset())
        for code, err in (("PUSH-AUTH", "fatal: Authentication failed\n"),
                          ("PUSH-REJECTED", " ! [rejected] main -> main (fetch first)\n"),
                          ("PUSH-HOOK-FAILED", f"{HOOK} ❌\nerror: failed to push some refs\n"),
                          ("PUSH-FAILED", "fatal: unable to access 'x': Could not resolve host\n")):
            with self.subTest(code):
                self.new_home()
                r2 = self.prr()
                r2.patrol()
                rc, out = self.go(r2, p7x.run_argv_spy(rc=1, err=err))
                self.assertEqual(rc, 1, out)
                self.assertIn(code, out)
        self.new_home()
        r3 = self.prr()
        r3.patrol()
        rc, out = self.go(r3, p7x.run_argv_spy(timed_out=True, rc=None))
        self.assertEqual(rc, 1, out)
        self.assertIn("PUSH-WALL-EXCEEDED", out)
        spy2 = p7x.run_argv_spy()  # 無事可做＝0 且印碼
        self.new_home()
        r4 = self.prr()
        rc, out = self.go(r4, spy2)  # 領先 0
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-NOT-AHEAD", out)
        self.new_home()
        r5 = self.prr()
        r5.patrol()
        fx.set_params(r5.R, sched_auto_push=False)
        fx.git(r5.R, "add", "--", fx.PARAMS)
        fx.git(r5.R, "commit", "-q", "-m", "off")  # 非巡邏提交，但 OFF 先於一切判準
        rc, out = self.go(r5, spy2)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-OFF", out)
        self.assertEqual(spy2.calls, [])
        rc, out, err = self.M(rr.R, "push-run", "--bogus")
        self.assertEqual(rc, 3, out + err)
        self.assertTrue(sha)

    def test_AT_749_11_E_1_entry_shell_flags_json_and_verb_count(self):
        import selfimproving
        rc, out, err = self.run_main(["push-run", "--help"])
        self.assertEqual(rc, 0, err)
        for flag in ("--repo", "--json", "--dry-run"):
            self.assertIn(flag, out)
        self.assertEqual(len(selfimproving._HELP), 30)  # noqa: SLF001
        self.assertIn("push-run", selfimproving._HELP)  # noqa: SLF001
        rr = self.prr()
        rr.patrol()
        spy = p7x.run_argv_spy(out=f"{self.remote_main(rr)}\trefs/heads/main\n")  # ls-remote 實值
        with mock.patch.object(runner, "run_argv", spy):
            rc, out, err = self.M(rr.R, "push-run", "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        self.assertEqual(list(obj), ["ok", "kind", "code", "sha", "ahead", "attempts"])
        self.assertEqual((obj["ok"], obj["kind"], obj["code"], obj["attempts"]),
                         (True, "push-run", "PUSH-OK", 1))
        self.assertEqual(len(spy.calls), 2)  # ls-remote＋push；入口走呼叫當下的 runner.run_argv
        self.new_home()  # `pythonw` 沒有 stdout：照樣 rc 0，不因印出而崩
        r2 = self.prr()
        r2.patrol()
        with mock.patch.object(runner, "run_argv", p7x.run_argv_spy()), mock.patch.object(
                sys, "stdout", None):
            self.assertEqual(selfimproving.main(["push-run", "--repo", str(r2.R)]), 0)


# --------------------------------------------------------------------------- AC-SI-49-12 OS 任務
class OsFake:
    """`runner.run_argv` 的替身：兩支任務各自的註冊、移除、現查（Windows）與 launchctl（macOS）。"""

    USER = "TESTDOM" + "\\" + "tester"
    SID, OTHER_SID = "S-1-5-21-111-222-333-1001", "S-1-5-21-111-222-333-2002"

    def __init__(self, *, patrol_rc=0, patrol_err="", push_rc=0, push_err="", push_user=None,
                 push_next="2026-11-11T12:15:00+08:00", stuck_push=False, push_present=False,
                 patrol_present=True, owner=None, owner_sid=None, mine_sid=None,
                 patrol_sid=None, push_sid=None, sessions=None, cur_session=1) -> None:
        self.owner = owner or self.USER  # 互動桌面（explorer.exe）的擁有者
        self.owner_sid, self.mine_sid = owner_sid or self.SID, mine_sid or self.SID
        # {工作階段: [(帳號, SID), …]}：每個工作階段的 explorer.exe 擁有者；
        # `cur_session`＝本行程所在
        self.sessions = sessions or {cur_session: [(self.owner, self.owner_sid)]}
        self.cur_session = cur_session
        self.patrol_sid = patrol_sid or self.SID
        self.push_sid = push_sid or (self.OTHER_SID if push_user else self.SID)
        self.calls: list[list[str]] = []
        self.patrol_rc, self.patrol_err = patrol_rc, patrol_err
        self.push_rc, self.push_err = push_rc, push_err
        self.push_user, self.push_next = push_user or self.USER, push_next
        self.stuck_push = stuck_push
        self.push_present, self.patrol_present = push_present, patrol_present
        self.loaded: set[str] = set()

    def script(self) -> list[str]:
        return [c[-1] for c in self.calls if c and c[0] == "powershell.exe" and "-Command" in c]

    def __call__(self, argv, *, env, timeout, cwd=None):
        self.calls.append(list(argv))
        out, rc, err = "", 0, ""
        if argv[0] == "launchctl":
            sub = argv[1]
            label = Path(argv[-1]).stem if sub == "bootstrap" else argv[-1].split("/")[-1]
            if sub == "bootstrap":
                self.loaded.add(label)
            elif sub == "bootout":
                self.loaded.discard(label)
            else:
                rc = 0 if label in self.loaded else 113
        elif "-File" in argv:
            rc, err = self.patrol_rc, self.patrol_err
            self.patrol_present = rc == 0
        else:
            text = argv[-1]
            if "GetOwner" in text:
                # PowerShell 端依 SessionId 過濾後的結果
                owners = "".join(f"NAME={n}\nOWNERSID={s}\n"
                                 for n, s in self.sessions.get(self.cur_session, []))
                out = (f"SESSIONID={self.cur_session}\n{owners}MINESID={self.mine_sid}\n"
                       + (f"PATROLSID={self.patrol_sid}\n" if self.patrol_present else ""))
            elif "New-ScheduledTaskAction" in text:
                rc, err = self.push_rc, self.push_err
                self.push_present = rc == 0
            elif text.startswith("Unregister-ScheduledTask -TaskName 'AutoSDD_SI_Push'"):
                self.push_present = self.push_present and self.stuck_push
            elif text.startswith("Unregister-ScheduledTask"):
                self.patrol_present = False
            elif "TaskName 'AutoSDD_SI_Push'" in text:
                out = (f"NEXT={self.push_next}\nUSER={self.push_user}\nSID={self.push_sid}\n"
                       if self.push_present
                       else "ABSENT")
            else:
                out = "2026-11-09T00:15:00+08:00" if self.patrol_present else "ABSENT"
        return types.SimpleNamespace(rc=rc, out=out, err=err, timed_out=False)


class TestOsTasks(RunTestCase):
    ENV = {"USERDOMAIN": "TESTDOM", "USERNAME": "tester"}

    def repo(self, push: bool = True) -> Path:
        R = fx4.p4_base()
        fx.set_params(R, sched_auto_push=push)
        return R

    @contextlib.contextmanager
    def win(self):
        """把 `sys.platform` 偽成 win32（`schedarm.sys` 即全域 `sys`）；`resolve_git` 依該值改找
        `git.com`／`.exe`…，在 POSIX 上會解析不到 git 而讓 arm 誤報設定讀取失敗，所以先解析真實
        git 再釘住：本組要驗的是排程註冊流程，不是 git 的尋找。"""
        real_git = si_git.resolve_git(os.environ)
        with mock.patch.object(schedarm.sys, "platform", "win32"), \
                mock.patch.object(si_git, "resolve_git", return_value=real_git):
            yield

    def arm(self, R, fake, **kw):
        with self.win(), mock.patch.dict(os.environ, self.ENV):
            return schedarm.arm(R, fake, as_json=False, **kw)

    def test_AT_749_12_1_windows_registers_an_interactive_task_and_checks_the_credential(self):
        R = self.repo()
        fake = OsFake()
        rc, text = self.arm(R, fake)
        self.assertEqual(rc, 0, text)
        self.assertIn("push_task_credential=2026-11-11T12:15:00+08:00", text)
        script = next(s for s in fake.script() if "New-ScheduledTaskAction" in s)
        pyw = str(R / ".venv" / "Scripts" / "pythonw.exe")
        hb = json.loads(fx.read(R, fx.PARAMS))["sched_heartbeat_minutes"]
        for needle in ("Register-ScheduledTask", "'AutoSDD_SI_Push'", "-LogonType Interactive",
                       "-RunLevel Limited", "-UserId", r"$env:USERDOMAIN\$env:USERNAME", pyw,
                       str(R / "tools" / "selfimproving.py"), "push-run", f"-Minutes {hb}",
                       "-MultipleInstances IgnoreNew", "-Hours 3", "-StartWhenAvailable",
                       "DisallowStartIfOnBatteries = $false", "StopIfGoingOnBatteries = $false"):
            self.assertIn(needle, script, needle)
        for bad in ("-WakeToRun", "S4U"):
            self.assertNotIn(bad, script)
        self.assertFalse(any("install_windows_nightly" in " ".join(c) and "Push" in " ".join(c)
                             for c in fake.calls))
        bare = OsFake(push_next="NONEXT")  # 取不到憑證：不得宣稱已建立
        rc, text = self.arm(R, bare)
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-NO-CREDENTIAL", text)
        self.assertNotIn("push_task_credential=", text)

    def test_AT_749_12_2_disabled_push_removes_the_task_and_disarm_removes_both(self):
        R = self.repo(push=False)
        fake = OsFake(push_present=True)
        rc, text = self.arm(R, fake)
        self.assertEqual(rc, 0, text)
        self.assertTrue(any(s.startswith("Unregister-ScheduledTask -TaskName 'AutoSDD_SI_Push'")
                            for s in fake.script()))
        self.assertFalse(any("New-ScheduledTaskAction" in s for s in fake.script()))
        absent = OsFake()
        self.assertEqual(self.arm(R, absent)[0], 0)
        self.assertFalse(any(s.startswith("Unregister-ScheduledTask -TaskName 'AutoSDD_SI_Push'")
                             for s in absent.script()))
        for push in (True, False):
            R2 = self.repo(push=push)
            gone = OsFake(push_present=True)
            with self.win():
                rc, text = schedarm.disarm(R2, gone, as_json=False)
            self.assertEqual(rc, 0, text)
            flat = " ".join(" ".join(c) for c in gone.calls)
            self.assertIn("AutoSDD_SI_Patrol", flat)
            self.assertIn("AutoSDD_SI_Push", flat)
            for bad in ("AutoClaude_Nightly", "AutoClaude_WindowsSmoke", "-Uninstall"):
                self.assertNotIn(bad, flat)
        stuck = OsFake(push_present=True, stuck_push=True)
        with self.win():
            rc, text = schedarm.disarm(self.repo(), stuck, as_json=False)
        self.assertEqual(rc, 1)
        self.assertIn("AutoSDD_SI_Push", text)

    def test_AT_749_12_3_failure_codes_and_independent_segments(self):
        R = self.repo()
        rc, text = self.arm(R, OsFake(push_rc=1, push_err="Access is denied"))
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-ELEVATION-REQUIRED", text)
        self.assertIn("系統管理員", text)
        self.assertIn("互動登入型", text)
        rc, text = self.arm(R, OsFake(push_rc=1, push_err="boom"))
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-PUSH-TASK-FAILED", text)
        self.assertIn("巡邏任務已安裝", text)
        rc, text = self.arm(R, OsFake(patrol_rc=1, patrol_err="Access is denied"))
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-ELEVATION-REQUIRED", text)
        self.assertIn("巡邏任務：SCHED-ELEVATION-REQUIRED", text)
        self.assertIn("推送任務：已建立", text)  # 巡邏段失敗不牽連推送段
        self.assertIn("push_task_credential=2026-11-11T12:15:00+08:00", text)
        rc, text = self.arm(R, OsFake(push_user="OTHER" + "\\" + "someone"))
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-PUSH-USER-MISMATCH", text)  # UserId 與註冊者不同
        fake = OsFake()
        rc, text = self.arm(self.repo(push=False), fake, push_only=True)
        self.assertEqual((rc, fake.calls), (1, []))
        self.assertIn("SCHED-PUSH-OFF", text)

    def test_AT_749_12_4_macos_writes_a_launchd_agent_and_keeps_windows_literals_out(self):
        R = self.repo()
        plist_dir = fx.new_dir("plist")
        fake = OsFake()
        with mac_platform():
            rc, text = schedarm.arm(R, fake, as_json=False, plist_dir=plist_dir)
        self.assertEqual(rc, 0, text)
        data = plistlib.loads((plist_dir / "AutoSDD_SI_Push.plist").read_bytes())
        hb = json.loads(fx.read(R, fx.PARAMS))["sched_heartbeat_minutes"]
        self.assertEqual((data["Label"], data["StartInterval"], data["RunAtLoad"]),
                         ("AutoSDD_SI_Push", hb * 60, False))
        self.assertEqual(data["ProgramArguments"], [str(R / ".venv" / "bin" / "python"),
                                                    str(R / "tools" / "selfimproving.py"),
                                                        "push-run",
                                                    "--repo", str(R)])
        self.assertIn("push_task_credential=launchctl-rc-0", text)
        self.assertTrue(all(c[0] == "launchctl" for c in fake.calls))
        self.assertTrue(
            any(c[1] == "bootstrap" and "AutoSDD_SI_Push.plist" in c[-1] for c in fake.calls))
        flat = " ".join(" ".join(c) for c in fake.calls)
        for bad in ("powershell.exe", "Register-ScheduledTask"):
            self.assertNotIn(bad, flat)
        with mock.patch.object(schedarm.sys, "platform", "darwin"):
            rc, text = schedarm.disarm(R, fake, as_json=False, plist_dir=plist_dir)
        self.assertEqual(rc, 0, text)
        self.assertFalse((plist_dir / "AutoSDD_SI_Push.plist").exists())

    def test_AT_749_12_5_why_interactive_and_the_nightly_ssot_is_untouched(self):
        src = (PKG / "schedarm.py").read_text(encoding="utf-8")
        self.assertIn("Interactive", src)
        self.assertIn("S4U", src)
        cp = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--",
                             "tools/scheduled_task_expectations.json",
                             "tools/install_windows_nightly.ps1"], capture_output=True,
                            encoding="utf-8", check=False, env=fx.genv())
        self.assertEqual((cp.returncode, cp.stdout.strip()), (0, ""))
        spec = json.loads((ROOT / "tools" / "scheduled_task_expectations.json").read_text(
            encoding="utf-8"))
        self.assertNotIn("AutoSDD_SI_Push", json.dumps(spec))

    def test_AT_749_12_6_push_only_and_independence(self):
        R = self.repo()
        fake = OsFake()
        rc, text = self.arm(R, fake, push_only=True)
        self.assertEqual(rc, 0, text)
        self.assertEqual([c[0] for c in fake.calls[:1]], ["powershell.exe"])
        self.assertFalse(any("-File" in c for c in fake.calls))
        self.assertEqual(sum(1 for s in fake.script() if "New-ScheduledTaskAction" in s), 1)
        rc, text = self.arm(R, OsFake(patrol_rc=1, patrol_err="Access is denied"))
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-ELEVATION-REQUIRED", text)
        self.assertIn("push_task_credential", text)
        rc, text = self.arm(R, OsFake(push_rc=1, push_err="boom"))  # 巡邏成功、推送失敗
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-PUSH-TASK-FAILED", text)
        self.assertIn("巡邏任務已安裝", text)
        gone = OsFake(push_present=True)
        with self.win():
            rc, text = schedarm.disarm(R, gone, as_json=False, push_only=True)
        self.assertEqual(rc, 0, text)
        flat = " ".join(" ".join(c) for c in gone.calls)
        self.assertNotIn("AutoSDD_SI_Patrol", flat)
        self.assertEqual(sum(1 for s in gone.script() if s.startswith("Unregister")), 1)


# --------------------------------------------------------------------------- AC-SI-49-13 憑證不落地
class TestNoCredentialsOnDisk(RunTestCase):
    def test_AT_749_13_1_planted_secrets_never_reach_a_file_or_the_output(self):
        planted = {name: name + "-" + SECRET + str(i) for i, name in enumerate(
            ("GITHUB_TOKEN", "GH_TOKEN", "AUTOSDD_SI_AUDIT_KEY"))}
        url = userinfo_url()
        rr = self.prr()
        sha = rr.patrol().sha
        outs = []
        with mock.patch.dict(os.environ, planted):
            for spy in (p7x.run_argv_spy(rc=128, err=f"fatal: unable to access '{url}': x\n"),
                        p7x.run_argv_spy(raises=RuntimeError(f"fail {url}"))):
                outs.append(self.go(rr, spy)[1])
            spy = p7x.run_argv_spy()
            outs.append(self.go(rr, spy, now=NOW + timedelta(days=1))[1])
            # git 要用
            self.assertNotIn("GITHUB_TOKEN", spy.calls[0]["env"])  # 允許清單：憑證走 helper
            self.assertNotIn("AUTOSDD_SI_AUDIT_KEY", spy.calls[0]["env"])
            fake = OsFake()
            with mock.patch.object(schedarm.sys, "platform", "win32"):
                outs.append(schedarm.arm(fx4.p4_base(), fake, as_json=False)[1])
        prm = {**real_params(), "sched_auto_push": True}
        ctx = patrol.Ctx(rr.R, NOW, False, patrol.Deps(), prm)
        snap = patrolreport.push_block(self.home, prm, NOW, True,
                                       patrolreport.push_inputs(ctx), lambda *a: False)
        blob = self.home_blob() + "".join(outs) + json.dumps(snap, ensure_ascii=False)
        for value in (*planted.values(), SECRET):
            self.assertNotIn(value, blob)
        self.assertTrue(sha)
        tree = ast.parse((PKG / "patrolpush.py").read_text(encoding="utf-8"))
        writes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute)
                      and n.func.attr in ("write_text", "write_bytes")]
        self.assertEqual(len(writes), 1)  # 唯一寫檔站點是 `_put`
        owner = next(f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and writes[0] in
                     list(ast.walk(f)))
        self.assertEqual(owner.name, "_put")
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)
                 and n.func.id == "_put"]
        for call in calls:  # 內容只來自 tick／current／結果／錯誤四種 dict
            arg = call.args[1]
            self.assertTrue(isinstance(arg, ast.Dict) or (isinstance(arg, ast.Name) and arg.id in (
                "current", "result", "err")), ast.dump(arg))
        self.assertEqual(len(calls), 5)  # tick／current／結果／錯誤＋blocked（遠端不符）

    def test_AT_749_13_E_1_the_audit_key_never_reaches_git(self):
        env = patrolpush.push_env({"AUTOSDD_SI_AUDIT_KEY": "k", "AUTOSDD_X_AUDIT_KEY_2": "k2",
                                   "AUTOSDD_SI_DIR": "v", "AUTOSDD_KEEP": "w", "GIT_ASKPASS": "a",
                                   "SSH_ASKPASS": "b", "GITHUB_TOKEN": "t"})
        self.assertFalse([k for k in env if "AUDIT_KEY" in k])
        self.assertEqual(env["AUTOSDD_SI_DIR"], "v")  # push profile：閘門用的 AUTOSDD_* 逐一列名
        self.assertNotIn("AUTOSDD_KEEP", env)  # 沒列名的一律不傳（E-67）
        for name in ("GIT_ASKPASS", "SSH_ASKPASS", "GITHUB_TOKEN"):
            self.assertNotIn(name, env)  # 憑證類變數不再傳（走 credential helper）


# ==================== 資安審查修復（SECREVIEW_ROOT_PUSH）
def mask_samples() -> tuple[list[str], list[str]]:
    """（含機密的樣本行, 機密值）；一律執行期拼出（機密掃描閘）。"""
    tok = "tok" + SECRET + "x1y2z3"
    ghp = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    fine = "github_" + "pat_" + "11AAAA" + "B" * 30
    b64 = "dXNl" + "cjpwYXNz" + "d29yZA=="
    lines = [f"GITHUB_TOKEN={tok}", f"GH_TOKEN: {tok}", f"AUTOSDD_SI_AUDIT_KEY={tok}",
             f"access_token={tok}", f"api_key={tok}", f"Authorization: Basic {b64}",
             f"Authorization: token {tok}", f"fatal: bad {ghp} here", f"fatal: bad {fine} here",
             f"password%3D{tok}", f"x-access-token%3A{tok}", f"url https://u:{tok}@h/x.git"]
    return lines, [tok, ghp, fine, b64]


class TestSecMask(RunTestCase):
    def test_AT_749_7_3_one_mask_implementation_covers_the_leaky_shapes(self):
        lines, secrets = mask_samples()
        prefixes = ["gh" + p + "_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4" for p in "ousr"]
        lines += [f"x {p} y" for p in prefixes] + [f"Authorization: Bearer {secrets[0]}"]
        for fn in (pushguard.mask, runner.mask):
            for line in lines:
                got = fn(line)
                for secret in (*secrets, *prefixes):
                    self.assertNotIn(secret, got, f"{fn.__module__}: {line}")
                # 預設標記 `***` 冪等（runner 的 `[REDACTED]` 含 `]`，不在此列）
                if fn is pushguard.mask:
                    self.assertEqual(fn(got), got)  # 冪等：遮兩次＝遮一次
        for prose in ("請設定 token", "password policy", "path: /usr/bin and patch applied"):
            self.assertEqual(pushguard.mask(prose), prose)  # 不含值的散文不被改寫
        self.assertIs(pushguard.mask, si_git.mask)  # 同一個函式物件
        self.assertIs(pushguard.SECRET_PATTERNS, si_git.SECRET_PATTERNS)
        defining = [p.name for p in PKG.glob("*.py")
                    if "SECRET_PATTERNS = (" in p.read_text(encoding="utf-8")]
        self.assertEqual(defining, ["git.py"])  # 全套件只有一處定義樣式表
        word = re.compile(r"(?i)\[=:\]|authorization|sk-|ghp_|gh\[pousr\]")  # 遮罩樣式的特徵
        rx_files = []  # 含這些字樣的遮罩正規式：除 git.py 外一律沒有（runner 不得另有一套）
        for path in PKG.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Call) and ast.unparse(node.func) in ("re.compile",
                                                                              "re.sub")
                        and node.args and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value,
                                       str) and word.search(node.args[0].value)):
                    rx_files.append(path.name)
        self.assertEqual(sorted(set(rx_files) - {"git.py"}), [])

    def test_SEC_F14_guard_and_push_share_one_git_env_function(self):
        parent = {k: "x" for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                                   "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_SSH_COMMAND",
                                   "GIT_NAMESPACE", "GIT_EXEC_PATH", "GIT_CONFIG_KEY_0",
                                   "GIT_CONFIG_VALUE_0", "GIT_ASKPASS")}
        parent["PATH"] = "p"
        pushed = sorted(patrolpush.push_env(parent))
        self.assertEqual(pushed, ["GCM_INTERACTIVE", "GIT_ATTR_NOSYSTEM", "GIT_GRAFT_FILE",
                                  "GIT_NO_REPLACE_OBJECTS", "GIT_TERMINAL_PROMPT", "PATH"])
        with mock.patch.dict(os.environ, parent, clear=True), \
                mock.patch.object(si_git, "ENV_TEST_PASSTHROUGH", ()):
            env = Git(fx.new_dir("g"), "git")._env()  # noqa: SLF001  # 守門用的 git 環境
        self.assertEqual(sorted(env), ["GIT_ATTR_NOSYSTEM", "GIT_GRAFT_FILE",
                                       "GIT_NO_REPLACE_OBJECTS", "GIT_OPTIONAL_LOCKS",
                                       "GIT_TERMINAL_PROMPT", "PATH"])


class TestSecRunner(RunTestCase):
    def test_AT_749_9_5_runner_notes_are_never_dropped(self):
        planted = "tok" + SECRET + "x1y2z3"
        for label, note, want in (
                ("job-assign-failed", f"job-unavailable:boom token={planted}",
                 "job-unavailable:boom"),
                ("taskkill-fallback", "taskkill-fallback:terminate-failed", "taskkill-fallback"),
                ("output-incomplete", "output-incomplete", "output-incomplete")):
            with self.subTest(label):
                self.new_home()
                rr = self.prr()
                sha = rr.patrol().sha
                self.go(rr, p7x.run_argv_spy(timed_out=label != "job-assign-failed",
                                             rc=None if label != "job-assign-failed" else 0,
                                             note=note))
                got = self.result(sha)["runner_note"]
                self.assertIn(want, got)
                self.assertLessEqual(len(got), patrolpush.RUNNER_NOTE_MAX)
                self.assertNotIn(planted, got)  # 說明經遮罩
        self.new_home()
        rr = self.prr()
        sha = rr.patrol().sha
        self.go(rr, p7x.run_argv_spy())  # 無說明＝null，PUSH-OK 也有這欄
        self.assertIsNone(self.result(sha)["runner_note"])
        self.assertIn("runner_note", self.result(sha))
        if sys.platform == "win32":  # Job 沒建起來：未逾時也要留下字樣（真 runner）
            with mock.patch.object(runner, "_job_open", return_value=(None, "boom")):
                res = runner.run_argv([sys.executable, "-c", "print(1)"], env=dict(os.environ),
                                      timeout=60)
            self.assertEqual((res.rc, res.timed_out, res.note), (0, False, "job-unavailable:boom"))
        res = runner.run_argv([sys.executable, "-c", "import time; time.sleep(30)"],
                              env=dict(os.environ), timeout=1)  # 逾時走終止路徑：說明非空
        self.assertTrue(res.timed_out)
        self.assertRegex(res.note, r"job-terminated|taskkill-fallback|killpg")


class TestSecIdentityAndLock(RunTestCase):
    def test_AT_749_9_E_2_a_reused_pid_is_never_killed_and_the_skip_is_surfaced(self):
        real = runner.pid_started_at(os.getpid())
        self.assertIsNotNone(real)
        tol = runner.IDENTITY_TOLERANCE_SECONDS
        self.assertEqual(tol, 5)
        near = datetime.fromtimestamp(real - 3, UTC).isoformat()  # 差 3 秒＝相符；差 6 秒＝不符
        far6 = datetime.fromtimestamp(real - 6, UTC).isoformat()
        def ident(*a, **kw):
            return runner.process_identity(os.getpid(), *a, window_seconds=None, **kw)
        self.assertEqual(ident(NOW.isoformat(), near), "match")
        self.assertEqual(ident(NOW.isoformat(), far6), "mismatch")
        self.assertEqual(ident(NOW.isoformat(), None), "unverified")  # 缺值：不退回寬鬆窗
        started = datetime.fromtimestamp(real - 60, UTC)  # 落在窗內
        exact = datetime.fromtimestamp(real, UTC).isoformat()
        far = datetime.fromtimestamp(real + 3000, UTC).isoformat()  # 窗內、但不是這個行程
        self.assertEqual(ident(started.isoformat(), exact), "match")
        self.assertEqual(ident(started.isoformat(), far), "mismatch")
        self.assertEqual(runner.process_identity(os.getpid(), started.isoformat(),
                                                 # 舊檔：窗口由呼叫端給
                                                 window_seconds=3300), "match")
        rr = self.rr()
        prm = fx.params_dict()
        for label, created, killed in (("exact", exact, [os.getpid()]), ("reused", far, [])):
            tdir = self.home / "patrol" / "RUN-SI-001"
            tdir.mkdir(parents=True, exist_ok=True)
            (tdir / "spawn.json").write_text(json.dumps({
                "pid": os.getpid(), "started_at": started.isoformat(),
                "wall_due_at": (started - timedelta(minutes=5)).isoformat(),
                "process_started_utc": created}), encoding="utf-8")
            kills: list[int] = []
            ctx = patrol.Ctx(rr.R, started + timedelta(hours=5), False,
                             patrol.Deps(kill_tree=kills.append), prm)
            patrolrun.watch(ctx)
            self.assertEqual(kills, killed, label)
            if not killed:
                log = (self.home / "patrol" / "patrol.log").read_text(encoding="utf-8")
                self.assertIn("code=RUN-KILL-SKIPPED", log)
                self.assertEqual(ctx.notes.get(fx.pid(1)), ("RUN-KILL-SKIPPED", ""))
                row = next(r for r in patrolreport.build(ctx, [], [], lambda *a: False)["props"]
                           if r["id"] == fx.pid(1))  # 快照 props[] 帶出
                self.assertEqual((row["code"], row["who"]), ("RUN-KILL-SKIPPED", "主機管理者"))
                self.assertIn("沒有終止它", row["text"])
        rec = runner.spawn_record(os.getpid(), NOW, NOW + timedelta(hours=4))
        self.assertEqual(list(rec), ["pid", "started_at", "wall_due_at", "process_started_utc"])
        self.assertIsNotNone(datetime.fromisoformat(rec["process_started_utc"]).utcoffset())

    def test_SEC_F13_a_stale_lock_with_a_live_holder_is_kept_and_a_fresh_one_is_never_deleted(self):
        from lib import apply_lock
        lock = self.home / "locks" / "x.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)

        def write_old() -> None:
            lock.write_text("4242\n2020-01-01T00:00:00+00:00\n", encoding="utf-8")
            old = time.time() - 100000
            os.utime(lock, (old, old))
        write_old()
        with self.assertRaises(apply_lock.LockBusyError):  # 陳舊但持鎖行程還活著：不回收
            with apply_lock.acquire_guarded(lock, 0.3, 10,
                                            holder_alive=lambda info: info.get("pid") == 4242):
                pass
        self.assertTrue(lock.exists())
        with apply_lock.acquire_guarded(lock, 5, 10, poll_interval=0.01,  # 持鎖行程已死：回收
                                        holder_alive=lambda info: False):
            pass
        write_old()
        fresh = "999\n2099-01-01T00:00:00+00:00\n"

        def swapped(path):  # 別人在我們判陳舊與刪除之間重建了新鎖
            path.write_text(fresh, encoding="utf-8")
            return None
        with mock.patch.object(apply_lock, "_holder_info", swapped):
            apply_lock._reap_if_stale(lock, 10)  # noqa: SLF001
        self.assertEqual(lock.read_text(encoding="utf-8"), fresh)  # 新鎖還在，沒被刪


# ==================== OS 任務：驗證失敗回復、SID 比對、macOS 環境
class TestSecOsTasks(RunTestCase):
    ENV = TestOsTasks.ENV
    repo = TestOsTasks.repo
    win = TestOsTasks.win
    arm = TestOsTasks.arm

    def test_AT_749_12_E_1_a_failed_verification_is_rolled_back_to_not_installed(self):
        R = self.repo()
        armed = self.home / "push" / "armed.json"
        for label, fake, code in (
                ("no-next-run", OsFake(push_next="NONEXT"), "SCHED-NO-CREDENTIAL"),
                ("wrong-sid", OsFake(push_sid=OsFake.OTHER_SID), "SCHED-PUSH-USER-MISMATCH")):
            rc, text = self.arm(R, fake, push_only=True)
            self.assertEqual(rc, 1, label)
            self.assertIn(code, text, label)
            self.assertFalse(fake.push_present, label)  # 同一次呼叫內已移除並現查不見
            self.assertFalse(armed.exists(), label)
            self.assertIn("推送任務已回復為未安裝", text, label)
        broken = OsFake()
        with mock.patch.object(schedarm, "_write_armed", side_effect=OSError("disk full")):
            rc, text = self.arm(R, broken, push_only=True)
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-PUSH-TASK-FAILED", text)
        self.assertFalse(broken.push_present)
        self.assertIn("推送任務已回復為未安裝", text)
        stuck = OsFake(push_next="NONEXT", stuck_push=True)  # 回復不成也如實說，不假稱乾淨
        rc, text = self.arm(R, stuck, push_only=True)
        self.assertEqual(rc, 1)
        self.assertIn("可能仍存在，請手動 sched disarm --push-only", text)
        rc, text = self.arm(R, OsFake(push_rc=1, push_err="boom"), push_only=True)
        self.assertIn("先前的推送任務（若有）已被移除", text)  # 非原子的重註冊：不假裝保留舊任務
        # 回讀的帳號不帶網域：以 SID 比，不以字串比
        ok = OsFake(push_user="tester", push_sid=OsFake.SID)
        self.assertEqual(self.arm(R, ok, push_only=True)[0], 0)
        doc = json.loads(armed.read_text(encoding="utf-8"))
        self.assertEqual(list(doc), ["remote_url", "git", "armed_at", "config_pins"])
        self.assertIsNotNone(datetime.fromisoformat(doc["armed_at"]).utcoffset())

    def test_AT_749_12_E_2_another_admin_account_or_a_foreign_patrol_principal_is_refused(self):
        R = self.repo()
        for label, kw in (("elevated-as-another-admin", {"mine_sid": OsFake.OTHER_SID}),
                          ("patrol-task-has-another-principal", {"patrol_sid": OsFake.OTHER_SID})):
            for push_only in (True, False):
                fake = OsFake(**kw)
                rc, text = self.arm(R, fake, push_only=push_only)
                self.assertEqual(rc, 1, f"{label} {push_only}")
                self.assertIn("SCHED-PUSH-USER-MISMATCH", text)
                self.assertIn("互動登入的同一個使用者", text)
                self.assertFalse(any("New-ScheduledTaskAction" in s or "Register-ScheduledTask" in s
                                     for s in fake.script()), label)  # 沒有註冊
        with self.win():
            probe = schedarm._session_argv()[-1]  # noqa: SLF001  # 以 SID 比：三個值在同一次現查裡
        for needle in ("GetOwnerSid", "WindowsIdentity", "AutoSDD_SI_Patrol", "SecurityIdentifier"):
            self.assertIn(needle, probe)

    def test_AT_749_12_7_macos_agent_carries_path_and_the_si_dir(self):
        R = self.repo()
        plist_dir = fx.new_dir("plist")
        # 安裝時要讀 git 設定：真 git 的目錄在 PATH 內
        gitdir = str(Path(si_git.resolve_git()).parent)
        outside = [str(fx.new_dir(f"bin{n}")) for n in range(4)] + [gitdir]
        env_path = os.pathsep.join([str(ROOT / ".venv" / "bin"), outside[0], outside[1],
                                    str(ROOT / "tools"), outside[2], outside[3], gitdir])
        with mock.patch.dict(os.environ, {"PATH": env_path}), mac_platform():
            rc, text = schedarm.arm(R, OsFake(), as_json=False, plist_dir=plist_dir)
        self.assertEqual(rc, 0, text)
        data = plistlib.loads((plist_dir / "AutoSDD_SI_Push.plist").read_bytes())
        env = data["EnvironmentVariables"]
        self.assertEqual(env["PATH"], os.pathsep.join(outside))  # repo 根與 .venv 之下的目錄已排除
        self.assertEqual(env["AUTOSDD_SI_DIR"], str(self.home))
        self.assertFalse([k for k in env if re.search(r"(?i)token|key|secret|passw", k)])
        self.assertNotIn("StandardOutPath", data)  # 不新增 log 檔
        self.assertIn("push_task_path=5-dirs:" + os.pathsep.join(outside[:3]), text)
        self.assertIn(f"push_task_si_dir={self.home}", text)


# ==================== 遠端核對、設定、內容約束（真 git、本機 bare）
def secret_samples() -> dict[str, str]:
    """（樣式名→含機密的字串）；一律執行期拼出（機密掃描閘）。"""
    tok = "tok" + SECRET + "x1y2z3"
    return {"github-token": "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4",
            "key-value": "api_" + "key=" + tok,
            "auth-header": "Authorization: Basic " + "dXNl" + "cjpwYXNz" + "d29yZA==",
            "private-key": "-----BEGIN RSA " + "PRIVATE KEY-----",
            "url-userinfo": "https://" + "u" + ":" + tok + "@h.example/x.git"}


class TestSecAcceptance(RunTestCase):
    """資安審查修復的驗收測試（真本機 bare 遠端；對應 TCS-P7 勘誤 E-17～E-27 新增的 AT）。"""

    def clone_advance(self, rr: p7x.PushRepo) -> str:
        """另一份複本把遠端 main 推前進一個提交（模擬別人推過）；回新的遠端 sha。"""
        other = fx.new_dir("clone")
        fx.git(fx.TMP, "clone", "-q", "-b", "main", str(rr.bare), str(other))
        fx.put(other, "elsewhere.txt", "別人的提交\n")
        fx.git(other, "add", "--", "elsewhere.txt")
        fx.git(other, "-c", "user.name=o", "-c", "user.email=o@x", "commit", "-q", "-m", "other")
        fx.git(other, "push", "-q", "origin", "HEAD:main")
        return self.remote_main(rr)

    def manual(self, rr: p7x.PushRepo, files=None, touched_extra: str = "", stage=None,
               claims=None, touched_bytes: bytes | None = None) -> str:
        """合規巡邏提交的骨架（touched＋事件行），可再夾帶檔案（str／bytes）與索引動作；回 sha。
        提案目錄的新檔一律補上綁定雜湊的事件（`claims` 可改宣稱的位元組）；`touched_bytes`＝以位元組
        寫入 touched 檔。"""
        app = rr.app_id()
        if touched_bytes is not None:
            fx.putb(rr.R, rr.touched[0], touched_bytes)
        elif rr.touched:
            rr.write_touched(fx.read(rr.R, rr.touched[0]) + f"patrol {rr.k}\n" + touched_extra)
        rr.event("promote", app, post=rr.post())
        rr.bind(files or {}, claims)
        paths = [EVL, *rr.touched]
        for rel, data in (files or {}).items():
            (fx.putb if isinstance(data, bytes) else fx.put)(rr.R, rel, data)
            paths.append(rel)
        fx.git(rr.R, "add", "--", *paths)
        if stage is not None:
            stage()
        return rr.commit([], app=app)

    def pdir(self, rr: p7x.PushRepo) -> str:
        return f"{PROPS}/{rr.prop}"

    # ---- AC-SI-49-1：預設關閉
    def test_AT_749_1_3_default_off_means_no_action_at_all(self):
        rr = self.rr()
        fx.set_params(rr.R, sched_auto_push=False)
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy()
        with git_calls() as seen:
            rc, out = self.go(rr, push, remote_run=ls)
            rc2, out2 = patrolpush.run(rr.R, dry_run=True, now=NOW)
        self.assertEqual((rc, rc2), (0, 0))
        self.assertIn("PUSH-OFF", out)
        self.assertIn("PUSH-OFF", out2)
        # 零呼叫：不連網、不讀 git 設定
        self.assertEqual((push.calls, ls.calls, seen), ([], [], []))
        self.assertFalse((self.home / "locks" / "push.lock").exists())  # 不取鎖
        names = {p.name for p in (self.home / "push").iterdir()}
        self.assertEqual(names - {"armed.json"}, {"tick.json"})  # 只寫 tick（armed 是夾具記的網址）
        for module in ("patrolpush", "schedarm", "pushguard"):  # 預設值只有 params.json 一處
            src = (PKG / f"{module}.py").read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"sched_auto_push[\"']?\s*(?:,|=)\s*True", src), module)
        R = TestOsTasks.repo(self, push=False)
        fake = OsFake()
        with mock.patch.object(schedarm.sys, "platform", "win32"), mock.patch.dict(
                os.environ, TestOsTasks.ENV):
            rc, text = schedarm.arm(R, fake, as_json=False)
            rc2, text2 = schedarm.arm(R, OsFake(), as_json=False, push_only=True)
        self.assertEqual(rc, 0, text)
        self.assertIn("自動推送未啟用，未安裝推送任務", text)
        self.assertFalse(any("New-ScheduledTaskAction" in s for s in fake.script()))
        self.assertEqual(rc2, 1)
        self.assertIn("SCHED-PUSH-OFF", text2)
        for needle in ("sched_auto_push", "true", "提交", "SOP", "自動推送（P7）", "殘餘風險",
                       "sched arm --push-only"):
            self.assertIn(needle, text2)

    # ---- AC-SI-49-3：內容約束的正向（防假紅）
    def test_AT_749_3_3_legal_content_is_not_a_false_positive(self):
        rr = self.rr()
        rel, d = rr.touched[0], self.pdir(rr)
        fx.git(rr.R, "update-index", "--chmod=+x", "--", rel)  # 既有可執行位元的檔
        fx.git(rr.R, "commit", "-q", "-m", "exec bit")
        rr.push()
        row = fx.line([fx.obs_id(41), "2026-11-11 12:00", "追加列 41", "症狀",
                       "tools/lib/si_demo.py:12",
                       "doc", "P3", "open", "面=文件;來源=代理;回報者=SA"])
        text = fx.read(rr.R, OBS).rstrip("\n") + "\n" + row + "\n"
        files = {f"{d}/r2.patch": "x\n", f"{d}/r2.md": "說明\n", f"{d}/verify3.json": "{}\n",
                 OBS: text}
        self.manual(rr, files, touched_extra="# token 的用法；password: str；secret 規則\n")
        res = rr.evaluate()
        self.assertTrue(res["ok"], res)  # 模式不變的 100755 修改、封閉樣式檔名、散文字樣皆放行

    # ---- AC-SI-49-2：`_commit` 先擋（單一函式）見 TestSecCommitSide；以下為守門端
    def test_AT_749_4_E_18_symlinks_gitlinks_and_mode_changes_are_refused(self):
        def build(label):
            rr = self.rr()
            rel, d = rr.touched[0], self.pdir(rr)
            blob = fx.git(rr.R, "rev-parse", f"HEAD:{rel}")
            head = fx.git(rr.R, "rev-parse", "HEAD")
            add = lambda mode, ref, path: lambda: fx.git(  # noqa: E731
                rr.R, "update-index", "--add", "--cacheinfo", f"{mode},{ref},{path}")
            plans = {
                "symlink": (f"{d}/r2.md", "120000", add("120000", blob, f"{d}/r2.md"), None),
                "gitlink": (f"{d}/r3.md", "160000", add("160000", head, f"{d}/r3.md"), None),
                "touched-to-exec": (rel, "100755", lambda: fx.git(
                    rr.R, "update-index", "--chmod=+x", "--", rel), None),
                "new-exec": (f"{d}/r4.md", "100755", lambda: fx.git(
                    rr.R, "update-index", "--chmod=+x", "--", f"{d}/r4.md"), {f"{d}/r4.md": "x\n"}),
                "type-change": (rel, "120000", add("120000", blob, rel), None)}
            path, mode, stage, files = plans[label]
            sha = self.manual(rr, files, stage=stage)
            fx.git(rr.R, "reset", "-q", "--hard", "HEAD")  # 工作樹回到提交內容（避免髒樹先擋）
            return rr, sha, path, mode
        for label in ("symlink", "gitlink", "touched-to-exec", "new-exec", "type-change"):
            with self.subTest(label):
                rr, sha, path, mode = build(label)
                self.blocked(rr.evaluate(), "PUSH-FILE-MODE-INVALID", sha, label,
                             frag=f"{path} {mode}")

    def test_AT_749_4_E_19_proposal_file_names_and_sizes_are_closed(self):
        for name in ("x.txt", "r2.patch.exe", "sub/r2.md"):
            with self.subTest(name=name):
                rr = self.rr()
                sha = rr.patrol(extra={f"{self.pdir(rr)}/{name}": "a\n"}).sha
                res = rr.evaluate()
                self.blocked(res, "PUSH-LEDGER-RULE", sha, name)
                self.assertIn(f"提案檔 {name} 檔名不在封閉樣式", res["detail"])
        self.assertEqual(pushcontent.PROPOSAL_FILE_MAX_BYTES, 1048576)
        for size, passes in ((1048576, True), (1048577, False)):
            with self.subTest(size=size):
                rr = self.rr()
                sha = rr.patrol(extra={f"{self.pdir(rr)}/r2.patch": "a" * size}).sha
                res = rr.evaluate()
                if passes:
                    self.assertTrue(res["ok"], res)
                else:
                    self.blocked(res, "PUSH-LEDGER-RULE", sha, frag="提案檔 r2.patch 超過大小上限")

    def test_AT_749_4_E_20_appended_ledger_lines_must_pass_the_check_validation(self):
        def event_case(mutate):
            rr = self.rr()
            app = rr.app_id()
            if rr.touched:
                rr.write_touched()
            rr.event("promote", app, post=rr.post())
            good = fx.read(rr.R, EVL)
            lines = good.rstrip("\n").split("\n")
            fx.put(rr.R, EVL, good + mutate(json.loads(lines[-1]), lines[-1]))
            sha = rr.commit([EVL, *rr.touched], app=app)
            fx.put(rr.R, EVL, good)  # 工作樹的帳本維持健全（守門的事件清單來自工作樹）
            return rr, sha

        def tweak(delta, **chg):
            def build(obj, _raw):
                obj = {k: v for k, v in {**obj, "seq": obj["seq"] + delta, **chg}.items()
                       if v is not None}
                seen.append(obj)
                return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
            return build
        seen: list[dict] = []
        cases = {
            "not-json": lambda obj, raw: "這不是 JSON\n",
            "bad-kind": tweak(1, kind="bogus.kind"),
            "gap-seq": tweak(6),
            "missing-key": tweak(1, t=None)}
        for label, mutate in cases.items():
            with self.subTest(label):
                rr, sha = event_case(mutate)
                self.blocked(rr.evaluate(), "PUSH-LEDGER-RULE", sha, label)
        for bad in (seen[0], seen[2]):  # `check` 現用的同一個驗證函式對這兩行也判紅
            self.assertTrue(si_events.validate(bad), bad)

        def obs_case(make_row):
            rr = self.rr()
            text = fx.read(rr.R, OBS).rstrip("\n") + "\n" + make_row() + "\n"
            return rr, rr.patrol(extra={OBS: text}).sha
        cells = [fx.obs_id(42), "2026-11-11 12:00", "追加列 42", "症狀", "tools/lib/si_demo.py:12",
                 "doc",
                 "P3", "open", "面=文件;來源=代理;回報者=SA"]
        obs = {"cells-short": lambda: fx.line(cells[:-1]),
               "bad-id": lambda: fx.line(["OBS" + "-SI-" + "zz9", *cells[1:]]),
               "bad-disposition": lambda: fx.line([*cells[:7], "bogus", cells[8]])}
        for label, make in obs.items():
            with self.subTest(label):
                rr, sha = obs_case(make)
                self.blocked(rr.evaluate(), "PUSH-LEDGER-RULE", sha, label)

    def test_AT_749_4_E_21_secret_patterns_in_added_content_are_refused_without_the_value(self):
        samples = secret_samples()
        for name, text in samples.items():  # ①提案檔（新增檔全文）
            with self.subTest(where="proposal", name=name):
                rr = self.rr()
                rel = f"{self.pdir(rr)}/r2.md"
                sha = self.manual(rr, {rel: f"說明 {text}\n"})
                res = rr.evaluate()
                self.blocked(res, "PUSH-SECRET-PATTERN", sha, name, frag=f"{rel} {name}")
                self.assertNotIn(text, json.dumps(res, ensure_ascii=False))
                self.assertEqual(pushguard.mask(res["text"]), res["text"])
        rr = self.rr()  # ②OBS 新列
        row = fx.line([fx.obs_id(43), "2026-11-11 12:00", "追加 " + samples["key-value"], "症狀",
                       "tools/lib/si_demo.py:12", "doc", "P3", "open",
                       "面=文件;來源=代理;回報者=SA"])
        sha = self.manual(rr, {OBS: fx.read(rr.R, OBS).rstrip("\n") + "\n" + row + "\n"})
        self.blocked(rr.evaluate(), "PUSH-SECRET-PATTERN", sha, frag=f"{OBS} key-value")
        rr = self.rr()  # ③touched 程式檔的新增行
        sha = self.manual(rr, touched_extra=f"# {samples['github-token']}\n")
        res = rr.evaluate()
        self.blocked(res, "PUSH-SECRET-PATTERN", sha, frag=f"{rr.touched[0]} github-token")
        rr = self.rr()  # 既有行含同樣字樣、新增行乾淨＝不算命中（只掃新增的行）
        fx.put(rr.R, rr.touched[0], fx.read(rr.R, rr.touched[0]) + f"# {samples['github-token']}\n")
        fx.git(rr.R, "add", "--", rr.touched[0])
        fx.git(rr.R, "commit", "-q", "-m", "舊行")
        rr.push()
        self.manual(rr)
        self.assertTrue(rr.evaluate()["ok"])
        rr = self.rr()  # 契約上的文字檔無法解碼＝fail-closed
        rel = f"{self.pdir(rr)}/r2.md"
        sha = self.manual(rr, {rel: b"\xff\xfe\x00bad"})
        self.blocked(rr.evaluate(), "PUSH-SECRET-PATTERN", sha, frag=f"{rel} undecodable")

    def test_AT_749_4_E_22_content_is_compared_byte_exact(self):
        for label, was, now in (("lone-cr", b"a\nb\n", b"a\rb\n"),
                                ("non-utf8", "a�b\n".encode(), b"a\xffb\n")):
            with self.subTest(label):
                rr = self.rr()
                rel, app = rr.touched[0], rr.app_id()
                base = (rr.R / rel).read_bytes()
                fx.putb(rr.R, rel, base + was)
                rr.event("promote", app, post=rr.post())  # 結果摘要依「晉升當下」的位元組
                fx.putb(rr.R, rel, base + now)
                sha = rr.commit([EVL, rel], app=app)
                if label == "lone-cr":
                    self.blocked(rr.evaluate(), "PUSH-CONTENT-MISMATCH", sha, label,
                                 frag="觸及檔內容與 post_sha256 不符")
                else:  # E-31 取代 E-28：非 UTF-8 的 touched 檔先判無法解碼（判序先於內容比對）
                    self.blocked(rr.evaluate(), "PUSH-SECRET-PATTERN", sha, label,
                                 frag=f"{rel} undecodable")
        repo = fx.new_dir("textconv")  # textconv 與 .gitattributes 命中，取到的仍是原始位元組
        fx.git(fx.TMP, "init", "-q", str(repo))
        fx.put(repo, ".gitattributes", "*.md diff=x\n")
        fx.putb(repo, "a.md", b"raw\rbytes\xff\n")
        fx.git(repo, "add", "-A")
        fx.git(repo, "-c", "user.name=o", "-c", "user.email=o@x", "commit", "-q", "-m", "x")
        fx.git(repo, "config", "diff.x.textconv", "echo converted")
        judge = pushguard._Judge(repo, self.home, [])  # noqa: SLF001
        self.assertEqual(judge.raw_blob("HEAD", "a.md"), b"raw\rbytes\xff\n")

    # ---- AC-SI-49-5：git 設定、遠端網址、絕對路徑
    def test_AT_749_5_E_2_dangerous_local_git_config_blocks_before_any_config_driven_command(self):
        rr = self.prr()
        rr.patrol()
        secret = "tok" + "en-value-" + "x" * 12
        cases = (
            ("credential.helper", f"store --file={secret}", "credential.helper"),
            ("credential.https://h.example.helper", "store", "credential.*.helper"),
            ("core.askpass", secret, "core.askpass"), ("core.gitProxy", secret, "core.gitproxy"),
            ("core.sshCommand", secret, "core.sshcommand"), ("core.fsmonitor", "true",
                                                             "core.fsmonitor"),
            ("http.proxy", "http://p:1", "http.proxy"),
            ("remote.origin.proxy", "http://p:1", "remote.*.proxy"),
            ("remote.origin.pushurl", "https://x/y.git", "remote.*.pushurl"),
            ("url.https://z/.insteadOf", "https://a/", "url.*.insteadof"),
            ("url.https://z/.pushInsteadOf", "https://a/", "url.*.pushinsteadof"),
            ("http.sslCAPath", "x", "http.sslcapath"), ("http.sslBackend", "x", "http.sslbackend"))
        for key, value, shown in cases:
            with self.subTest(key=key):
                fx.git(rr.R, "config", "--local", key, value)
                with git_calls() as seen:
                    res = rr.evaluate()
                self.assertEqual((res["ok"], res["code"], res["detail"]),
                                 (False, "PUSH-GIT-CONFIG-UNSAFE", shown), res)
                self.assertNotIn(secret, json.dumps(res, ensure_ascii=False))
                self.assertNotIn("status", {sub_of(a) for a in seen})  # 先擋、後才可能執行設定程式
                fx.git(rr.R, "config", "--local", "--unset-all", key)
        self.assertTrue(rr.evaluate()["ok"])
        for key, value in (("core.fsmonitor", "false"), ("user.name", "x"), ("core.autocrlf",
                                                                             "false")):
            fx.git(rr.R, "config", "--local", key, value)  # 合法設定不擋
        self.assertTrue(rr.evaluate()["ok"])
        for label, how in (("absent", lambda: fx.git(rr.R, "config", "--unset", "core.hooksPath")),
                           ("other", lambda: fx.git(rr.R, "config", "core.hooksPath",
                                                    "elsewhere"))):
            how()
            res = rr.evaluate()
            self.assertEqual((res["code"], res["detail"]), ("PUSH-GIT-CONFIG-UNSAFE",
                                                            "core.hookspath"),
                             label)
            fx.git(rr.R, "config", "core.hooksPath", p7x.HOOKS_DIR)
        self.assertEqual(rr.evaluate(enabled=False)["code"], "PUSH-OFF")  # OFF 先於設定檢查
        fx.git(rr.R, "config", "--local", "core.sshCommand", "ssh")
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy()
        rc, out = self.go(rr, push, remote_run=ls)
        self.assertEqual((rc, push.calls, ls.calls), (0, [], []))  # 連 ls-remote 也不發
        self.assertIn("PUSH-GIT-CONFIG-UNSAFE", out)

    def test_AT_749_5_E_3_the_remote_url_is_bound_to_the_one_recorded_at_arm_time(self):
        rr = self.prr()
        rr.patrol()
        rr.arm_url(None)
        res = rr.evaluate()
        self.assertEqual(res["code"], "PUSH-REMOTE-URL-CHANGED")
        self.assertTrue(res["detail"].startswith("未記錄 "), res["detail"])
        tok = "tok" + SECRET + "x1y2z3"
        rr.arm_url("https://" + "u:" + tok + "@old.example.com:8443/x/y.git")
        res = rr.evaluate()
        self.assertEqual((res["code"], res["detail"]),
                         ("PUSH-REMOTE-URL-CHANGED", "https://old.example.com:8443 本機路徑"))
        self.assertNotIn(tok, json.dumps(res, ensure_ascii=False))
        fx.git(rr.R, "remote", "set-url", "origin",
               "https://" + "u:" + tok + "@example.com/x/y.git")
        schedarm._write_armed(rr.R)  # noqa: SLF001  # `sched arm` 成功安裝時寫的檔
        path = self.home / "push" / "armed.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(list(doc), ["remote_url", "git", "armed_at", "config_pins"])
        self.assertEqual((doc["remote_url"], doc["git"]),
                         ("https://example.com/x/y.git", si_git.resolve_git()))
        self.assertEqual([ln for ln in path.read_text(encoding="utf-8").splitlines() if tok in ln],
                         [])  # 帳密零命中
        rr.arm_url("https://" + "u2:" + "p" + "@example.com/x/y")  # 僅差 userinfo 與 .git ＝ 不擋
        self.assertTrue(rr.evaluate()["ok"])
        fx.git(rr.R, "remote", "set-url", "origin", "https://evil.example.org/x/y.git")
        res = rr.evaluate()
        self.assertEqual((res["code"], res["detail"]), (
            "PUSH-REMOTE-URL-CHANGED", "https://example.com https://evil.example.org"))

    def test_AT_749_5_E_4_git_is_resolved_to_an_absolute_path_outside_the_repo(self):
        fake_repo = fx.new_dir("fakerepo")
        exe = "git.exe" if sys.platform == "win32" else "git"
        dirs = [fake_repo / ".venv" / ("Scripts" if sys.platform == "win32" else "bin"), fake_repo]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            (d / exe).write_bytes(b"not git")
            (d / exe).chmod(0o755)
        marker = fake_repo / "tools" / "lib" / "selfimproving" / "git.py"
        marker.parent.mkdir(parents=True, exist_ok=True)
        real = si_git.resolve_git()
        self.assertTrue(real and os.path.isabs(real), real)
        path = os.pathsep.join([*(str(d) for d in dirs), str(Path(real).parent)])
        with mock.patch.object(si_git, "__file__", str(marker)):  # 假 repo 根：其下的 git 一律排除
            got = si_git.resolve_git({"PATH": path})
            nothing = si_git.resolve_git({"PATH": os.pathsep.join(str(d) for d in dirs)})
        self.assertEqual(Path(got).parent, Path(real).parent)
        self.assertIsNone(nothing)  # 全被排除＝解析不到（守門與 push-run fail-closed）
        rr = self.prr()
        sha = rr.patrol().sha
        with mock.patch.object(pushguard, "resolve_git", return_value=None):
            self.assertEqual(rr.evaluate()["code"], "PUSH-GIT-UNAVAILABLE")
        push = p7x.run_argv_spy()
        ls = p7x.run_argv_spy(out=f"{self.remote_main(rr)}\trefs/heads/main\n")
        self.assertEqual(self.go(rr, push, remote_run=ls)[0], 0)
        self.assertEqual((push.calls[0]["argv"][0], ls.calls[0]["argv"][0]), (real, real))
        self.assertEqual(push.calls[0]["argv"][-1], f"{sha}:refs/heads/main")
        for name in ("patrolpush", "pushguard", "pushcontent", "runner", "schedarm"):
            tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
            bare = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.List) and n.elts
                    and isinstance(n.elts[0], ast.Constant)
                    and n.elts[0].value in ("git", "taskkill", "taskkill.exe")]
            self.assertEqual(bare, [], name)  # 沒有 argv[0] 為裸名的呼叫

    def test_AT_749_5_E_4_b_taskkill_is_windowless_absolute_and_the_job_handle_closes_once(self):
        # 以平台替身走 Windows 分支（各平台皆可驗）
        fake = types.SimpleNamespace(pid=1, kill=lambda: None)
        with (mock.patch.object(runner.sys, "platform", "win32"),
              mock.patch.dict(os.environ, {"SystemRoot": "C:" + "\\" + "WinX"}),
              mock.patch.object(runner.subprocess, "run") as sub):
            runner._kill_tree(fake)  # noqa: SLF001
            runner.kill_pid_tree(7)
        self.assertEqual(sub.call_count, 2)
        for call in sub.call_args_list:
            exe = str(call.args[0][0]).replace("\\", "/").lower()
            self.assertTrue(exe.endswith("system32/taskkill.exe"), call)
            self.assertEqual(call.kwargs.get("creationflags"), getattr(subprocess,
                                                                       "CREATE_NO_WINDOW", 0))
        ends: list = []
        with (mock.patch.object(runner.sys, "platform", "win32"),
              mock.patch.object(runner, "_job_open", return_value=("H", "")),
              mock.patch.object(runner, "_job_end",
                                side_effect=lambda job, terminate: ends.append(job) and False),
              mock.patch.object(runner.subprocess, "run", side_effect=OSError("no taskkill"))):
            res = runner.run_argv([sys.executable, "-c", "import time; time.sleep(30)"],
                                  env=dict(os.environ), timeout=1)
        self.assertTrue(res.timed_out)
        self.assertEqual([j for j in ends if j is not None], ["H"])  # 句柄只交出去一次

    # ---- AC-SI-49-6：推送前綁定遠端實值
    def test_AT_749_6_4_push_binds_to_the_remote_value_in_a_fixed_order(self):
        rr = self.prr()
        sha = rr.patrol().sha
        base = self.remote_main(rr)
        order: list[tuple] = []
        orig, origb = Git.run, Git.run_bytes

        def rec(git_self, *a, **kw):
            order.append(("git", a))
            return orig(git_self, *a, **kw)

        def recb(git_self, *a, **kw):
            order.append(("git", a))
            return origb(git_self, *a, **kw)
        ls = p7x.run_argv_spy(out=f"{base}\trefs/heads/main\n",
                              on_call=lambda: order.append(("ls",)))
        push = p7x.run_argv_spy(on_call=lambda: order.append(("push",)))
        with mock.patch.object(Git, "run", rec), mock.patch.object(Git, "run_bytes", recb):
            rc, out = self.go(rr, push, remote_run=ls)
        self.assertEqual(rc, 0, out)
        i_ls, i_push = order.index(("ls",)), order.index(("push",))
        self.assertLess(i_ls, i_push)
        pre = [o[1] for o in order[:i_ls]]
        mid = [o[1] for o in order[i_ls + 1:i_push]]
        self.assertIn(("rev-parse", "--verify", "-q", "refs/remotes/origin/main^{commit}"), pre)
        for sub in ("--count", "--reverse"):  # 範圍字面為 <base>..<head>
            self.assertTrue(any(a[:1] == ("rev-list",) and sub in a and a[-1] == f"{base}..{sha}"
                                for a in pre), sub)
        for a in (*pre, *mid):
            if sub_of(a) in ("rev-list", "diff-tree", "show", "cat-file", "log"):
                self.assertIsNone(re.search(r"(?<![0-9a-f])HEAD|origin/main", " ".join(a)), a)
            self.assertNotEqual(sub_of(a), "fetch")  # 全程不改本機追蹤參照
        call = ls.calls[0]
        self.assertEqual(call["argv"][1:], ["-C", str(rr.R), *si_git.PIN_ARGS(rr.R),
                                            "ls-remote", "origin", "refs/heads/main"])
        self.assertEqual(call["timeout"], patrolpush.LS_REMOTE_SECONDS)
        # 祖先檢查→最後一道 HEAD 復查→送出前的設定再驗（兩次 config）與 repo 狀態再驗（replace、
        # 共用目錄／shallow／attributes 路徑、hooks 目錄 ls-files；E-65）→push
        self.assertEqual([sub_of(a) for a in mid[-8:]],
                         ["merge-base", "symbolic-ref", "rev-parse", "config", "config",
                          "for-each-ref", "rev-parse", "ls-files"])
        self.assertEqual(mid[-8], ("merge-base", "--is-ancestor", base, sha))

    def test_AT_749_6_5_head_moved_while_judging_is_judged_against_fixed_shas(self):
        rr = self.prr()
        p = rr.patrol().sha
        h = rr.human()
        state, seen = {"done": False}, []
        orig, origb = Git.run, Git.run_bytes

        def rec(git_self, *a, **kw):
            if "rev-list" in a and not state["done"]:
                state["done"] = True
                fx.git(rr.R, "reset", "-q", "--hard", "HEAD~1")  # 判定途中把 HEAD 往回移
            seen.append(a)
            return orig(git_self, *a, **kw)

        def recb(git_self, *a, **kw):
            seen.append(a)
            return origb(git_self, *a, **kw)
        with mock.patch.object(Git, "run", rec), mock.patch.object(Git, "run_bytes", recb):
            res = rr.evaluate()
        self.assertEqual(head_of(rr.R), p)  # 注入確實發生
        self.blocked(res, "PUSH-FOREIGN-COMMITS", h)  # 範圍仍是 <base>..<H>，人工提交 H 不得放行
        for a in seen:
            if sub_of(a) in ("rev-list", "diff-tree", "show", "cat-file", "log"):
                self.assertIsNone(re.search(r"(?<![0-9a-f])HEAD|origin/main", " ".join(a)), a)

    def test_AT_749_6_E_2_a_rewound_remote_is_never_pushed_over(self):
        rr = self.prr()
        sha = rr.patrol().sha
        r1 = self.remote_main(rr)
        r0 = fx.git(rr.R, "rev-parse", "refs/remotes/origin/main~1")
        fx.git(rr.bare, "update-ref", "refs/heads/main", r0)  # 遠端被刻意倒回
        rc, out = patrolpush.run(rr.R, now=NOW)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-REMOTE-DRIFT", out)
        self.assertEqual(self.remote_main(rr), r0)  # 被移除的提交沒被推回
        self.assertFalse(self.result_path(sha).exists())
        blocked = json.loads((self.home / "push" / "blocked.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(blocked), ["at", "code", "detail", "head"])
        self.assertEqual((blocked["code"], blocked["head"], blocked["detail"]),
                         ("PUSH-REMOTE-DRIFT", sha, f"{r0[:8]} {r1[:8]}"))
        block = patrolreport.push_block(
            self.home, fx.params_dict(), NOW, True,
            {"ahead": 1, "head": sha, "code": None, "detail": None}, lambda *a: False)
        self.assertEqual((block["state"], block["code"]), ("blocked", "PUSH-REMOTE-DRIFT"))

    def test_AT_749_6_E_3_a_tracking_ref_moved_forward_does_not_smuggle_commits(self):
        rr = self.prr()
        a = rr.human()
        fx.git(rr.R, "update-ref", "refs/remotes/origin/main", a)  # 追蹤參照被往前移
        sha = rr.patrol().sha
        self.assertTrue(rr.evaluate()["ok"])  # 守門的範圍 <A>..<P> 本身合規
        before = self.remote_main(rr)
        rc, out = patrolpush.run(rr.R, now=NOW)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-REMOTE-DRIFT", out)
        self.assertEqual(self.remote_main(rr), before)
        cp = subprocess.run(["git", "-C", str(rr.bare), "cat-file", "-e", a], capture_output=True,
                            check=False, env=fx.genv())
        self.assertNotEqual(cp.returncode, 0)  # A 的內容沒有隨 P 推出
        self.assertFalse(self.result_path(sha).exists())

    def test_AT_749_6_E_4_a_remote_that_is_not_an_ancestor_is_diverged(self):
        rr = self.prr()
        sha = rr.patrol().sha
        x = self.clone_advance(rr)  # 別人推進到與本機分叉的提交
        fx.git(rr.R, "fetch", "-q", "origin")  # 本機追蹤參照也到 X：R == base
        rc, out = patrolpush.run(rr.R, now=NOW)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-REMOTE-DIVERGED", out)
        self.assertEqual(self.remote_main(rr), x)
        blocked = json.loads((self.home / "push" / "blocked.json").read_text(encoding="utf-8"))
        self.assertEqual((blocked["code"], blocked["detail"]), ("PUSH-REMOTE-DIVERGED",
                                                                f"{x[:8]} {sha[:8]}"))
        ghost = "f" * 40  # 遠端物件不在本機：merge-base 無法判定，同樣不放行
        self.assertEqual(patrolpush.pre_push_problem(rr.R, {"sha": sha, "base": ghost}, ghost),
                         ("PUSH-REMOTE-DIVERGED", f"{ghost[:8]} {sha[:8]}"))

    def test_AT_749_6_E_5_a_remote_advanced_between_ls_remote_and_push_is_not_overwritten(self):
        rr = self.prr()
        sha = rr.patrol().sha
        moved: dict[str, str] = {}
        with mock.patch.object(patrolpush, "AFTER_LSREMOTE_HOOK",
                               lambda repo: moved.setdefault("x", self.clone_advance(rr))):
            rc, out = patrolpush.run(rr.R, now=NOW)
        got = self.result(sha)
        self.assertEqual((got["code"], got["attempts"]), ("PUSH-REJECTED", 1), out)
        self.assertEqual(rc, 1)
        self.assertEqual(self.remote_main(rr), moved["x"])  # 保持被推進後的值、沒被覆寫
        self.assertNotEqual(self.remote_main(rr), sha)

    def test_AT_749_6_E_6_head_changed_before_sending_never_pushes_and_leaves_no_trace(self):
        moves = (("AFTER_GUARD_HOOK", "human", lambda rr: rr.human()),
                 ("AFTER_GUARD_HOOK", "reset", lambda rr: fx.git(rr.R, "reset", "-q", "--hard",
                                                                 "HEAD~1")),
                 ("AFTER_GUARD_HOOK", "branch", lambda rr: fx.git(rr.R, "checkout", "-q", "-b",
                                                                  "other")),
                 ("AFTER_LSREMOTE_HOOK", "human", lambda rr: rr.human()))
        for seam, label, move in moves:
            with self.subTest(seam=seam, move=label):
                self.new_home()
                rr = self.prr()
                sha = rr.patrol().sha
                base = self.remote_main(rr)
                with mock.patch.object(patrolpush, seam, lambda repo: move(rr)):
                    rc, out = patrolpush.run(rr.R, now=NOW)
                self.assertEqual(rc, 0, out)
                self.assertIn("PUSH-HEAD-MOVED", out)
                self.assertEqual(self.remote_main(rr), base)
                push = self.home / "push"
                self.assertFalse(self.result_path(sha).exists())
                self.assertFalse((push / "blocked.json").exists())
                self.assertFalse((push / "current.json").exists())

    def test_AT_749_6_E_7_ls_remote_failures_are_classified_and_never_pushed_over(self):
        base_of = lambda rr: self.remote_main(rr)  # noqa: E731
        failures = (("auth", dict(rc=128, err="fatal: Authentication failed for 'x'"), "PUSH-AUTH"),
                    ("network", dict(rc=128,
                                     err="fatal: unable to access 'x': Could not resolve host: h"),
                     "PUSH-FAILED"),
                    ("timeout", dict(rc=None, timed_out=True), "PUSH-WALL-EXCEEDED"))
        for label, kw, code in failures:
            with self.subTest(label):
                self.new_home()
                rr = self.prr()
                sha = rr.patrol().sha
                push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(**kw)
                self.go(rr, push, remote_run=ls)
                self.assertEqual(push.calls, [])
                self.assertEqual((self.result(sha)["code"], self.result(sha)["attempts"]), (code,
                                                                                            1))
        self.new_home()
        rr = self.prr()
        rr.patrol()
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(rc=0, out="")  # 遠端沒有 refs/heads/main
        rc, out = self.go(rr, push, remote_run=ls)
        self.assertEqual((rc, push.calls), (0, []))
        self.assertIn(f"<空> {base_of(rr)[:8]}", out)
        self.assertIn("PUSH-REMOTE-DRIFT", out)


# ===================== 第三輪勘誤（E-29～E-47）的驗收測試 =====================
def global_cfg(case, text: str) -> Path:
    """寫一份使用者層（`GIT_CONFIG_GLOBAL`）設定檔，回路徑。"""
    folder = fx.new_dir("gcfg")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "global.cfg"
    path.write_text(text, encoding="utf-8")
    return path


class TestSecRound3(RunTestCase):
    """TCS-P7 E-29～E-46 新增的 AT（受測 tools/lib/selfimproving/
    {git,pushcontent,pushguard,patrolpush,
    apply_lock,runner,schedarm}.py）。"""

    ENV = TestOsTasks.ENV
    win = TestOsTasks.win

    def pdir(self, rr: p7x.PushRepo) -> str:
        return f"{PROPS}/{rr.prop}"

    def manual(self, rr, files=None, **kw) -> str:
        return TestSecAcceptance.manual(self, rr, files, **kw)

    def unsafe(self, rr) -> tuple[str | None, str | None]:
        res = rr.evaluate()
        return res["code"], res["detail"]

    def with_global(self, text: str):
        return mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(global_cfg(self, text))})

    @contextlib.contextmanager
    def with_system(self, text: str):
        """系統層設定（`GIT_CONFIG_SYSTEM`）；夾具預設的 `GIT_CONFIG_NOSYSTEM` 會讓它被忽略。"""
        path = str(global_cfg(self, text))
        with mock.patch.dict(os.environ, {"GIT_CONFIG_SYSTEM": path}):
            os.environ.pop("GIT_CONFIG_NOSYSTEM", None)
            yield

    def arm_now(self, rr) -> None:
        """模擬 `sched arm` 成功後寫的 `armed.json`：記下當下 system＋global 的乙類鍵有效值。"""
        record, why = si_git.arm_record(rr.R)
        self.assertIsNotNone(record, why)
        schedarm._write_armed(rr.R, record)  # noqa: SLF001

    # ---- E-29：git 設定全層、環境變數、釘定、送出前復驗、安裝時記錄
    def test_AT_749_5_E_5_config_is_checked_in_every_layer(self):
        rr = self.prr()
        rr.patrol()
        git_dir = rr.R / ".git"
        fx.git(rr.R, "config", "extensions.worktreeConfig", "true")  # ①worktree 層
        (git_dir / "config.worktree").write_text(
            "[credential]\n\thelper = !evil\n", encoding="utf-8")
        self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "credential.helper"))
        (git_dir / "config.worktree").unlink()
        fx.git(rr.R, "config", "--unset", "extensions.worktreeConfig")
        # ②不可釘定：任何層都擋
        with self.with_global('[url "https://x/"]\n\tinsteadOf = https://y/\n'):
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "url.*.insteadof"))
        with self.with_global("[credential]\n\thelper = manager\n"):  # ③全域層：arm 時記下才放行
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "credential.helper"))
            self.arm_now(rr)
            self.assertTrue(rr.evaluate()["ok"])
        for bad in ("!evil", "C" + ":/tools/git-credential-x.exe", "store"):
            with self.with_global(f"[credential]\n\thelper = {bad}\n"):
                self.assertEqual(self.unsafe(rr),
                    ("PUSH-GIT-CONFIG-UNSAFE", "credential.helper"), bad)
        self.arm_now(rr)  # 回到「沒有 helper」的記錄
        with self.with_global("[http]\n\tsslVerify = false\n"):  # ④全域層的甲類鍵被釘成安全值：不擋
            self.assertTrue(rr.evaluate()["ok"])
        # 乙類：arm 時沒有值，任何層出現即擋
        for text, shown in (("[core]\n\tsshCommand = evil\n", "core.sshcommand"),
                            ("[http]\n\tproxy = http://p:1\n", "http.proxy")):
            with self.with_global(text):
                self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown))
        for key, value, shown in (("core.sshCommand", "evil", "core.sshcommand"),
                                  ("http.sslVerify", "false", "http.sslverify"),
                                  ("http.proxy", "http://p:1", "http.proxy")):
            fx.git(rr.R, "config", "--local", key, value)  # 同鍵在 local 層：擋
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown), key)
            fx.git(rr.R, "config", "--local", "--unset-all", key)
        for key, value, shown in (  # ⑤補齊的危險鍵（local 層）
                ("http.https://h.example.proxy", "http://p:1", "http.*.proxy"),
                ("http.sslCAInfo", "x.crt", "http.sslcainfo"),
                ("http.sslCAPath", "x", "http.sslcapath"),
                ("http.sslBackend", "x", "http.sslbackend"),
                ("remote.origin.vcs", "evil", "remote.*.vcs"),
                ("remote.origin.uploadpack", "evil", "remote.*.uploadpack"),
                ("remote.origin.receivepack", "evil", "remote.*.receivepack"),
                ("push.gpgSign", "true", "push.gpgsign")):
            fx.git(rr.R, "config", "--local", key, value)
            res = rr.evaluate()
            self.assertEqual((res["code"], res["detail"]), ("PUSH-GIT-CONFIG-UNSAFE", shown), key)
            fx.git(rr.R, "config", "--local", "--unset-all", key)
        secret = "tok" + "en-value-" + "q" * 12  # 偵測訊息不含值
        fx.git(rr.R, "config", "--local", "http.proxy", f"http://u:{secret}@p:1")
        self.assertNotIn(secret, json.dumps(rr.evaluate(), ensure_ascii=False))
        fx.git(rr.R, "config", "--local", "--unset-all", "http.proxy")
        self.assertTrue(rr.evaluate()["ok"])

    def test_AT_749_5_E_6_config_injected_through_the_environment_is_refused(self):
        rr = self.prr()
        rr.patrol()
        for name in ("GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_KEY_0",
                     "GIT_CONFIG_VALUE_0"):
            with mock.patch.dict(os.environ, {name: "1"}), git_calls() as seen:
                res = rr.evaluate()
            self.assertEqual((res["code"], res["detail"]),
                ("PUSH-GIT-CONFIG-UNSAFE", f"env:{name}"))
            self.assertEqual(seen, [], name)  # 不呼叫任何 git
            # 傳給 git 的環境仍剔除
            self.assertNotIn(name, si_git.env_for_git({name: "1", "PATH": "p"}, "read"))
            with mock.patch.dict(os.environ, {name: "1"}):
                self.assertNotIn(name, Git(rr.R)._env())  # noqa: SLF001
        quiet = {"GIT_CONFIG_SYSTEM": str(global_cfg(self, "")), "GIT_ASKPASS": "echo"}
        with mock.patch.dict(os.environ, quiet):  # 使用者既有的設定來源：不擋（經所有層檢查把關）
            self.assertTrue(rr.evaluate()["ok"])

    def test_AT_749_6_E_8_every_git_call_carries_the_pinned_overrides(self):
        rr = self.prr()
        sha = rr.patrol().sha
        exe, pin = si_git.resolve_git(os.environ), si_git.PIN_ARGS(rr.R)
        self.assertEqual(pin[:2], ["-c", "credential.helper="])  # 清空在最前
        self.assertEqual(si_git.PIN_ARGS(rr.R, {"credential.helper": ["manager", "cache"]})[2:6],
                         ["-c", "credential.helper=manager", "-c", "credential.helper=cache"])
        for key in ("http.sslVerify=true", "push.gpgSign=false", "core.fsmonitor=false",
                    "protocol.ext.allow=never", "core.gitProxy=", "core.askPass="):
            self.assertIn(key, pin)  # 甲類
        # 空值會讓 git 找名為空字串的 helper（vcs），或蓋掉合法的 CA／ssh／proxy（乙類不釘空值）；
        # 丙類（pushurl／proxy）只偵測不釘
        self.assertIn("http.proxy=", pin)  # 例外：arm 無代理記錄＝釘空值（空字串＝不用代理，E-54）
        for key in ("remote.origin.vcs=", "core.sshCommand=", "http.sslCAInfo=",
                    "http.sslBackend=", "http.sslCAPath=", "remote.origin.pushurl=",
                    "remote.origin.proxy=", "diff.external=", "gpg.program="):
            self.assertNotIn(key, pin)
        argvs: list[list[str]] = []
        real = subprocess.run

        def rec(argv, *a, **kw):
            argvs.append(list(argv))
            return real(argv, *a, **kw)
        with self.with_global("[http]\n\tsslVerify = false\n"), \
                mock.patch.object(si_git.subprocess, "run", rec):
            res = rr.evaluate()
            self.assertTrue(res["ok"], res)  # 全域層 sslVerify 不被擋（甲類，推送端釘回 true）
        for argv in argvs:
            self.assertEqual(argv[:3], [exe, "-C", str(rr.R.resolve())])
            if argv[3] == "config":  # 設定檢查的兩次讀取不帶覆寫（看見真實設定）
                self.assertIn(argv[3:5], (["config", "--list"], ["config", "--get"]))
                if argv[4] == "--list":
                    self.assertEqual(argv[3:7], ["config", "--list", "--show-scope", "--includes"])
            else:
                self.assertEqual(argv[3:3 + len(pin)], pin, argv)
        with self.with_global("[core]\n\tsshCommand = ssh -i k\n[http]\n\tsslVerify = false\n"):
            self.arm_now(rr)  # 乙類 sshCommand：以 arm 時的記錄值釘定（不釘空值）
            pin = si_git.PIN_ARGS(rr.R, si_git.armed_pins(json.loads(
                (self.home / "push" / "armed.json").read_text(encoding="utf-8"))))
            self.assertIn("core.sshCommand=ssh -i k", pin)

            def effective(key):  # 釘定後實際生效的值（沒有釘定時 sslVerify 會是 false）
                cp = real([exe, "-C", str(rr.R), *pin, "config", "--get", key], capture_output=True,
                          encoding="utf-8", check=False)
                return cp.stdout.strip()
            self.assertEqual((effective("core.sshCommand"), effective("http.sslVerify")),
                ("ssh -i k", "true"))
            push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(
                out=f"{self.remote_main(rr)}\trefs/heads/main\n")
            self.go(rr, push, remote_run=ls)
        self.assertEqual(push.calls[0]["argv"], patrolpush.push_argv(
            rr.R, sha, self.remote_main(rr), exe, tuple(pin)))
        self.assertEqual(push.calls[0]["argv"][3:3 + len(pin)], pin)
        self.assertEqual(ls.calls[0]["argv"][3:3 + len(pin)], pin)

    # ---- E-48：git 設定三類（甲＝可釘定、乙＝arm 時記錄有效值、丙＝任何層出現即擋）
    TYPICAL_SYSTEM = (
        "[http]\n\tsslcainfo = " + "C" + ":/Git/mingw64/etc/ssl/certs/ca-bundle.crt\n"
        "\tsslbackend = schannel\n"
        '[filter "lfs"]\n\tclean = git-lfs clean -- %f\n\tsmudge = git-lfs smudge -- %f\n'
        "\tprocess = git-lfs filter-process\n\trequired = true\n"
        '[diff "astextplain"]\n\ttextconv = astextplain\n[credential]\n\thelper = manager\n'
        '[credential "https://dev.azure.com"]\n\tuseHttpPath = true\n'
        "[core]\n\tautocrlf = true\n\tsymlinks = false\n\tfscache = true\n")
    TYPICAL_KEYS = [  # 上列 system 層在 arm 時會記下的乙類鍵（排序）
        "credential.helper", "credential.https://dev.azure.com.usehttppath", "filter.lfs.clean",
        "filter.lfs.process", "filter.lfs.required", "filter.lfs.smudge", "http.sslbackend",
        "http.sslcainfo"]

    def test_AT_749_5_9_typical_git_for_windows_system_layer_passes_after_arm(self):
        rr = self.prr()
        rr.patrol()
        with self.with_system(self.TYPICAL_SYSTEM):
            # arm 之前：乙類鍵（CA、credential.*、filter.*）沒有記錄，出現即擋；textconv 不納管
            self.assertEqual(self.unsafe(rr)[0], "PUSH-GIT-CONFIG-UNSAFE")
            self.arm_now(rr)
            doc = json.loads((self.home / "push" / "armed.json").read_text(encoding="utf-8"))
            pins = doc["config_pins"]
            self.assertEqual(pins["credential.helper"], ["manager"])
            self.assertEqual(sorted(pins), self.TYPICAL_KEYS)
            res = rr.evaluate()
            # 典型系統層不再讓自動推送恆被擋（兩個 UNSAFE 碼都不回）
            self.assertTrue(res["ok"], res)
            pin = si_git.PIN_ARGS(rr.R, si_git.armed_pins(doc))
            low = [a.lower() for a in pin]
            self.assertIn("http.sslcainfo=" + pins["http.sslcainfo"][0].lower(), low)
            for want in ("http.sslbackend=schannel", "log.showsignature=false",
                         "core.usereplacerefs=false", "http.proxy=",
                         "credential.https://dev.azure.com.usehttppath=true",
                         "filter.lfs.required=true", "credential.helper=manager"):
                self.assertIn(want, low)
            self.assertEqual(pin[:2], ["-c", "credential.helper="])
            # 除 http.proxy 與 helper 清空（及甲類既有的空值）外，不含任何值為空的乙類 -c
            empties = {a for a in pin if a.endswith("=")}
            self.assertEqual(empties - {"credential.helper=", "http.proxy=", "core.gitProxy=",
                                        "core.askPass="}, set())

    def test_AT_749_5_E_9_recorded_keys_changed_after_arm_are_refused(self):
        rr = self.prr()
        rr.patrol()
        with self.with_system(self.TYPICAL_SYSTEM):
            self.arm_now(rr)
            for label, text, shown in (
                    ("global-cainfo", "[http]\n\tsslCAInfo = other.crt\n", "http.sslcainfo"),
                    ("global-backend", "[http]\n\tsslBackend = openssl\n", "http.sslbackend"),
                    ("global-helper", "[credential]\n\thelper = cache\n", "credential.helper"),
                    ("global-ssh", "[core]\n\tsshCommand = ssh -i k\n", "core.sshcommand"),
                    ("global-proxy", "[http]\n\tproxy = http://p:1\n", "http.proxy")):
                with self.subTest(label), self.with_global(text):
                    self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown))
        other = self.TYPICAL_SYSTEM.replace("ca-bundle.crt", "other-bundle.crt")
        with self.with_system(other):  # 系統層的值本身被換掉：現值與記錄不同
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "http.sslcainfo"))
        with self.with_system(self.TYPICAL_SYSTEM):
            self.assertTrue(rr.evaluate()["ok"])  # 回到記錄值即放行
        # 記錄檔被改成不安全的 helper、現值也一致：helper 仍須屬安全清單
        schedarm._write_armed(rr.R, {"credential.helper": ["store"]})  # noqa: SLF001
        with self.with_global("[credential]\n\thelper = store\n"):
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "credential.helper"))

    def test_AT_749_5_E_5_b_class_c_keys_are_refused_in_every_layer_and_arm_repo_layer(self):
        rr = self.prr()
        rr.patrol()
        with self.with_system('[url "https://x/"]\n\tinsteadOf = https://y/\n'):
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "url.*.insteadof"))
        with self.with_global('[url "https://x/"]\n\tpushInsteadOf = https://y/\n'):
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "url.*.pushinsteadof"))
        for scope_ctx in (self.with_system, self.with_global):
            for body, shown in (('[remote "origin"]\n\tvcs = evil\n', "remote.*.vcs"),
                                ('[remote "origin"]\n\tpushurl = https://x/y\n',
                                 "remote.*.pushurl"),
                                ('[remote "origin"]\n\tproxy = http://p:1\n', "remote.*.proxy")):
                with scope_ctx(body):
                    self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown))
        for key in ("http.sslCAInfo", "core.sshCommand", "http.sslBackend", "credential.helper"):
            fx.git(rr.R, "config", "--local", key, "manager" if "helper" in key else "x")
            record, why = si_git.arm_record(rr.R)  # arm 時 repo 層出現乙類鍵：拒絕
            self.assertEqual((record, why), (None, key.lower()), key)
            fx.git(rr.R, "config", "--local", "--unset-all", key)
        with self.with_system(self.TYPICAL_SYSTEM):
            record, why = si_git.arm_record(rr.R)
        self.assertEqual((sorted(record), why), (self.TYPICAL_KEYS, ""))

    # ---- E-53～E-61：替換物件、環境允許清單、credential.*／filter.*／屬性來源（皆用真 git）
    def replaced_repo(self):
        """P＝合規巡邏提交；H＝base 上的任意提交（含 evil.txt）；main 指向 H；`git replace H P`。"""
        rr = self.prr()
        patrol = rr.patrol()
        R, base = rr.R, fx.git(rr.R, "rev-parse", "origin/main")
        fx.git(R, "checkout", "-q", "-b", "side", base)
        fx.put(R, "evil.txt", "EVIL\n")
        fx.git(R, "add", "--", "evil.txt")
        fx.git(R, "commit", "-q", "-m", "H arbitrary content")
        h = head_of(R)
        fx.git(R, "checkout", "-q", "main")
        fx.git(R, "update-ref", "refs/heads/main", h)
        fx.git(R, "reset", "-q", "--hard")
        fx.git(R, "branch", "-q", "-D", "side")
        rr.record(h, patrol.app)
        fx.git(R, "replace", h, patrol.sha)
        return rr, h, patrol, base

    def real_git(self, rr, *args, env=None, repo=None):
        """不經套件的對照呼叫（只加 `env` 覆寫）。"""
        return subprocess.run([si_git.resolve_git(os.environ), "-C", str(repo or rr.R), *args],
                              capture_output=True, encoding="utf-8", check=False,
                              env={**fx.genv(), **(env or {})}).stdout.strip()

    def test_AT_749_5_E_10_replace_refs_grafts_shallow_and_attributes_are_detected(self):
        rr, h, patrol, base = self.replaced_repo()
        res = rr.evaluate()
        self.assertEqual((res["ok"], res["code"], res["detail"]),
                         (False, "PUSH-REPO-STATE-UNSAFE", "refs/replace"))
        with git_calls() as seen:  # 偵測在任何讀物件的呼叫之前（呼叫次序斷言）
            rr.evaluate()
        reads = ("rev-list", "show", "cat-file", "diff-tree", "log", "merge-base")
        self.assertEqual([s for s in (sub_of(a) for a in seen) if s in reads], [])
        self.assertIn("for-each-ref", [sub_of(a) for a in seen])
        fx.git(rr.R, "replace", "-d", h)
        info = rr.R / ".git" / "info"
        for label, rel, text in (("grafts", "grafts", f"{h} {base}\n"),
                                 ("shallow", "../shallow", f"{base}\n"),
                                 ("attributes", "attributes", "* filter=x\n")):
            path = info / rel
            path.write_text(text, encoding="utf-8")
            res = rr.evaluate()
            want = {"grafts": "info/grafts", "shallow": "shallow",
                    "attributes": "info/attributes"}[label]
            self.assertEqual((res["code"], res["detail"]), ("PUSH-REPO-STATE-UNSAFE", want), label)
            path.unlink()
        other = self.prr()  # ⑤四者皆不存在 ⇒ 放行（防假紅）
        other.patrol()
        self.assertTrue(other.evaluate()["ok"])

    def test_AT_749_5_E_2_b_hooks_path_may_be_the_absolute_form_of_the_expected_directory(self):
        rr = self.prr()
        rr.patrol()
        fx.git(rr.R, "config", "core.hooksPath", str(rr.R / si_git.EXPECTED_HOOKS))
        self.assertTrue(rr.evaluate()["ok"])  # 安裝腳本寫的是絕對路徑：等同既定目錄
        fx.git(rr.R, "config", "core.hooksPath", str(rr.R / "elsewhere"))
        self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "core.hookspath"))
        fx.git(rr.R, "config", "core.hooksPath", p7x.HOOKS_DIR)

    @unittest.skipUnless(sys.platform == "win32", "[WINDOWS-NATIVE-ONLY] 8.3 短檔名與長度前綴")
    def test_AT_749_5_E_2_c_hooks_path_in_windows_alias_forms_is_the_same_directory(self):
        import ctypes
        rr = self.prr()
        rr.patrol()
        hooks = rr.R / si_git.EXPECTED_HOOKS
        buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetShortPathNameW(str(rr.R), buf, 1024)
        forms = [str(Path(buf.value) / si_git.EXPECTED_HOOKS),  # 8.3 短名（runner 的 RUNNER~1）
                 "\\\\?\\" + str(hooks), str(hooks).upper(), str(hooks).replace("\\", "/")]
        for form in forms:
            fx.git(rr.R, "config", "core.hooksPath", form)
            self.assertTrue(rr.evaluate()["ok"], form)  # 解析後同一目錄＝接受
        fx.git(rr.R, "config", "core.hooksPath", str(rr.R / "elsewhere"))
        self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "core.hookspath"))
        fx.git(rr.R, "config", "core.hooksPath", p7x.HOOKS_DIR)

    def test_AT_749_6_E_12_the_guard_reads_the_real_objects_even_with_detection_off(self):
        rr, h, patrol, _base = self.replaced_repo()
        shown = lambda **kw: self.real_git(rr, "show", "-s", "--format=%s", h, **kw)  # noqa: E731
        self.assertNotEqual(shown(), "H arbitrary content")  # 夾具真的造出了替換
        self.assertEqual(shown(env={"GIT_NO_REPLACE_OBJECTS": "1"}), "H arbitrary content")
        with mock.patch.object(pushcontent, "repo_state_problem", return_value=None):
            res = rr.evaluate()  # 第二道防線：環境＋core.useReplaceRefs=false
        self.assertEqual((res["ok"], res["code"]), (False, "PUSH-FOREIGN-COMMITS"), res)

    def test_AT_749_6_6_the_push_sends_the_real_object_not_the_replacement(self):
        rr, h, patrol, base = self.replaced_repo()
        exe, pin = si_git.resolve_git(os.environ), tuple(si_git.PIN_ARGS(rr.R))
        env = patrolpush.push_env(os.environ)
        self.assertEqual(env["GIT_NO_REPLACE_OBJECTS"], "1")
        cp = subprocess.run(patrolpush.push_argv(rr.R, h, base, exe, pin), env=env, cwd=rr.R,
                            capture_output=True, encoding="utf-8", check=False)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        remote = lambda *a: self.real_git(rr, *a, repo=rr.bare)  # noqa: E731
        self.assertEqual(remote("rev-parse", "refs/heads/main"), h)
        self.assertEqual(remote("show", "-s", "--format=%s", "refs/heads/main"),
                         "H arbitrary content")  # 遠端的是 H 自己的訊息與樹（不是 P′）
        self.assertIn("evil.txt", remote("ls-tree", "--name-only", "refs/heads/main"))
        # 探針（E-61 ①）：不帶 GIT_NO_REPLACE_OBJECTS 時 pack-objects 同樣送真物件
        fx.git(rr.bare, "update-ref", "refs/heads/main", base)
        env.pop("GIT_NO_REPLACE_OBJECTS")
        cp = subprocess.run(patrolpush.push_argv(rr.R, h, base, exe, pin), env=env, cwd=rr.R,
                            capture_output=True, encoding="utf-8", check=False)
        self.assertEqual((cp.returncode, remote("rev-parse", "refs/heads/main")), (0, h))

    def allow_names(self, platform: str, profile: str) -> set[str]:
        win = platform == "win32"
        names = {n.upper() if win else n for n in si_git.ENV_ALLOW["win32" if win else "posix"]}
        names |= {"PATH", *si_git.ENV_FIXED, *si_git._PROFILE_FIXED[profile]}  # noqa: SLF001
        return names

    def test_AT_749_5_10_git_child_environments_are_subsets_of_the_allow_list(self):
        planted = {"GIT_SSL_NO_VERIFY": "1", "HTTPS_PROXY": "http://x", "GCM_TRACE": "1",
                   "GIT_ASKPASS": "a", "SSH_ASKPASS": "b",
                   "GITHUB_TOKEN": "t", "CURL_CA_BUNDLE": "c",
                   "SSL_CERT_FILE": "d", "GIT_CONFIG_GLOBAL": "e", "AUTOSDD_UNATTENDED": "1",
                   "AUTOSDD_SI_PATROL_RUN": "r", "AUTOSDD_X_AUDIT_KEY": "k", "AUTOSDD_OK": "v",
                   "PYTHONUTF8": "1", "LC_ALL": "C", "LC_TIME": "C"}
        parent = {**os.environ, **planted}
        fixed = {"GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
                 "GIT_ATTR_NOSYSTEM": "1"}
        roots = (fx.ROOT.resolve(), Path(sys.prefix).resolve(), Path.cwd().resolve())
        with mock.patch.object(si_git, "ENV_TEST_PASSTHROUGH", ()):
            for platform in ("win32", "linux"):
                for profile in ("read", "push"):
                    env = si_git.env_for_git(parent, profile, platform=platform)
                    win = platform == "win32"
                    ok = self.allow_names(platform, profile)
                    if profile == "push":
                        ok |= {"PYTHONUTF8", "PYTHONIOENCODING"}
                        ok |= set(si_git._PUSH_AUTOSDD)  # noqa: SLF001  # 逐一列名（E-67）
                    if not win:
                        ok |= {k for k in env if k.startswith("LC_")}
                    extra = {k for k in env if (k.upper() if win else k) not in ok}
                    self.assertEqual(extra, set(), (platform, profile))
                    for key, value in fixed.items():
                        self.assertEqual(env[key], value)
                    locks, gcm = ("0", None) if profile == "read" else (None, "never")
                    self.assertEqual((env.get("GIT_OPTIONAL_LOCKS"), env.get("GCM_INTERACTIVE")),
                                     (locks, gcm))
                    for seg in env["PATH"].split(os.pathsep):
                        inside = any(Path(seg).resolve().is_relative_to(r)
                                     for r in roots if r.parent != r)
                        self.assertFalse(inside, seg)
        for writable in (False, True):  # E-21③：前綴不可寫（POSIX /usr）不排除、可寫才排除
            with (mock.patch.object(si_git.os, "access", return_value=writable),
                  mock.patch.object(si_git.sys, "prefix", sys.base_prefix)):  # venv 根在 repo 內
                self.assertEqual(si_git.safe_path({"PATH": sys.base_prefix}) == "", writable)
        recorded: list[dict] = []  # 實際 spawn（夾具的隔離變數經測試縫放行，下面併入允許集合）
        real = subprocess.run

        def rec(argv, *a, **kw):
            recorded.append({"argv": list(argv), "env": dict(kw.get("env") or {})})
            return real(argv, *a, **kw)
        rr = self.prr()
        rr.patrol()
        with mock.patch.object(si_git.subprocess, "run", rec), mock.patch.dict(os.environ, planted):
            rr.evaluate()
            si_git.arm_record(rr.R)
            push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(out="x")
            self.go(rr, push, remote_run=ls)
        envs = [c["env"] for c in recorded] + [c["env"] for c in push.calls + ls.calls]
        self.assertTrue(len(envs) > 5)
        plat = "win32" if sys.platform.startswith("win") else "linux"
        allowed = (self.allow_names(plat, "read") | self.allow_names(plat, "push")
                   | {"PYTHONUTF8", "PYTHONIOENCODING", "LC_ALL", "LC_TIME"}
                   | set(si_git.ENV_TEST_PASSTHROUGH) | set(si_git._PUSH_AUTOSDD))  # noqa: SLF001
        for env in envs:
            fold = (lambda k: k.upper()) if plat == "win32" else (lambda k: k)
            lc = () if plat == "win32" else si_git._ENV_PREFIX["posix"]  # noqa: SLF001  # LC_* 前綴
            self.assertEqual({k for k in env if fold(k) not in allowed
                              and not k.startswith(lc)}, set())
        # 結構鎖：git 子行程的 env 引數來源只有 env_for_git（直接、或經 push_env／self._env）
        calls = []
        for name in ("git.py", "patrolpush.py"):
            for node in ast.walk(ast.parse((PKG / name).read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and ast.unparse(node.func) in (
                        "subprocess.run", "run_argv"):
                    kw = {k.arg: ast.unparse(k.value) for k in node.keywords}
                    calls.append((name, kw.get("env")))
        self.assertTrue(calls)
        for name, src in calls:
            self.assertIn(src, ("self._env()", "env"), name)

    def test_AT_749_5_10_b_path_segments_under_cwd_and_the_proxy_warning(self):
        tmp = fx.new_dir("cwdbin")
        (tmp / "bin").mkdir(parents=True)
        here = os.getcwd()
        os.chdir(tmp)
        try:
            with mock.patch.object(si_git, "ENV_TEST_PASSTHROUGH", ()):
                env = si_git.env_for_git({"PATH": os.pathsep.join([str(tmp / "bin"), here])},
                    "read")
        finally:
            os.chdir(here)
        self.assertNotIn(str(tmp / "bin"), env["PATH"].split(os.pathsep))  # cwd 之下的段被排除
        rr = self.prr()  # arm 行程環境含 *_PROXY：印警告（推送任務不使用環境代理）
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy.example:3128"}), \
                contextlib.redirect_stderr(err):
            self.assertIsNotNone(si_git.arm_record(rr.R)[0])
        self.assertIn("*_PROXY", err.getvalue())
        self.assertNotIn("proxy.example", err.getvalue())  # 不印值

    def test_AT_749_5_E_11_dangerous_parent_variables_never_reach_git(self):
        names = ("GIT_SSL_NO_VERIFY", "GIT_SSL_CAINFO", "GIT_SSL_CAPATH", "HTTPS_PROXY",
                 "https_proxy", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY", "GCM_TRACE",
                 "GCM_TRACE_SECRETS", "GCM_CREDENTIAL_STORE", "GCM_PLAINTEXT_STORE_PATH",
                 "GIT_ASKPASS", "SSH_ASKPASS", "GIT_TRACE_CURL", "GIT_TRACE_REDACT",
                 "GIT_TRACE_PACKET", "GIT_ATTR_SOURCE", "GIT_CONFIG_GLOBAL", "GIT_REPLACE_REF_BASE",
                 "CURL_CA_BUNDLE", "SSL_CERT_FILE")
        planted = {n: "1" for n in names}
        with mock.patch.object(si_git, "ENV_TEST_PASSTHROUGH", ()):
            for profile in ("read", "push"):
                env = si_git.env_for_git({**os.environ, **planted}, profile)
                self.assertEqual([n for n in names if n in env or n.upper() in env], [], profile)
        rr = self.prr()
        rr.patrol()
        push = p7x.run_argv_spy()
        ls = p7x.run_argv_spy(out=f"{self.remote_main(rr)}\trefs/heads/main\n")
        with mock.patch.dict(os.environ, planted):
            self.go(rr, push, remote_run=ls)
        for call in push.calls + ls.calls:  # GIT_CONFIG_GLOBAL 只經夾具的測試縫（正式環境恆空）
            self.assertEqual([n for n in names if n in call["env"]
                and n != "GIT_CONFIG_GLOBAL"], [])
        pin = si_git.PIN_ARGS(rr.R, {})  # arm 時無代理記錄：釘空值（空字串＝不用代理；E-61 ②實測）
        self.assertEqual(pin[pin.index("http.proxy=") - 1], "-c")
        pin = si_git.PIN_ARGS(rr.R, {"http.proxy": ["http://proxy.example:8080"]})
        self.assertIn("http.proxy=http://proxy.example:8080", pin)
        self.assertNotIn("http.proxy=", pin)

    def test_AT_749_5_E_12_every_credential_key_is_recorded_and_compared(self):
        rr = self.prr()
        rr.patrol()
        with self.with_system(self.TYPICAL_SYSTEM):
            self.arm_now(rr)
            for label, text, shown in (
                    ("username", "[credential]\n\tusername = u\n", "credential.username"),
                    ("sub-username", '[credential "https://h.example"]\n\tusername = u\n',
                     "credential.*.username"),
                    ("usehttppath", '[credential "https://dev.azure.com"]\n'
                     "\tuseHttpPath = false\n", "credential.*.usehttppath"),
                    ("plaintext", "[credential]\n\tcredentialStore = plaintext\n",
                     "credential.credentialstore")):
                with self.subTest(label), self.with_global(text):
                    self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown))
            self.assertTrue(rr.evaluate()["ok"])
        worktree = rr.R / ".git" / "config.worktree"
        with self.with_system(self.TYPICAL_SYSTEM):  # local／worktree 出現任何 credential.* 一律擋
            fx.git(rr.R, "config", "--local", "credential.username", "u")
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "credential.username"))
            fx.git(rr.R, "config", "--local", "--unset-all", "credential.username")
            fx.git(rr.R, "config", "extensions.worktreeConfig", "true")
            worktree.write_text("[credential]\n\tusername = u\n", encoding="utf-8")
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "credential.username"))
            worktree.unlink()
            fx.git(rr.R, "config", "--unset", "extensions.worktreeConfig")
        pins = {"credential.helper": ["manager"], "credential.username": ["u"],
                "credential.https://dev.azure.com.usehttppath": ["true"]}
        pin = si_git.PIN_ARGS(rr.R, pins)
        self.assertIn("credential.username=u", pin)
        self.assertIn("credential.https://dev.azure.com.usehttppath=true", pin)

    def test_AT_749_5_E_13_filter_attribute_and_signature_sources_are_governed(self):
        rr = self.prr()
        rr.patrol()
        marker = fx.new_dir("marker")
        prog = fx.new_dir("fakeprog")
        marker.mkdir(parents=True, exist_ok=True)
        prog.mkdir(parents=True, exist_ok=True)
        clean = prog / "clean.py"
        clean.write_text("import sys\nopen(sys.argv[1], 'a').write('x')\n"
                         "sys.stdout.write(sys.stdin.read())\n", encoding="utf-8")
        ran = marker / "clean_ran"
        cmd = f'"{sys.executable}" "{clean}" "{ran}"'
        fx.git(rr.R, "config", "--local", "filter.x.clean", cmd)
        attrs = rr.R / ".git" / "info" / "attributes"
        attrs.parent.mkdir(parents=True, exist_ok=True)
        attrs.write_text("* filter=x\n", encoding="utf-8")
        with git_calls() as seen:  # ①local filter＋info/attributes：設定先擋、不跑任何 status
            res = self.unsafe(rr)
        self.assertEqual(res, ("PUSH-GIT-CONFIG-UNSAFE", "filter.*.clean"))
        self.assertNotIn("status", {sub_of(a) for a in seen})
        fx.git(rr.R, "config", "--local", "--unset-all", "filter.x.clean")
        self.assertEqual(self.unsafe(rr), ("PUSH-REPO-STATE-UNSAFE", "info/attributes"))
        self.assertFalse(ran.exists())  # 假濾鏡從未被執行
        # 探針（E-61 ④⑤）：不加釘定、stat 與 index 不符時，git status 確實呼叫
        # info/attributes 指定的濾鏡
        fx.git(rr.R, "config", "--local", "filter.x.clean", cmd)
        target = rr.R / rr.touched[0]
        stat = target.stat()
        os.utime(target, (stat.st_atime + 7, stat.st_mtime + 7))
        self.real_git(rr, "status", "--porcelain")
        self.assertTrue(ran.exists())
        fx.git(rr.R, "config", "--local", "--unset-all", "filter.x.clean")
        attrs.unlink()
        # ②arm 記錄的 filter.lfs.* 不變 ⇒ 放行；global 新增另一個 filter.y.clean 或改 lfs 值 ⇒ 擋
        with self.with_system(self.TYPICAL_SYSTEM):
            self.arm_now(rr)
            self.assertTrue(rr.evaluate()["ok"])
            with self.with_global('[filter "y"]\n\tclean = cat\n'):
                self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "filter.*.clean"))
            with self.with_global('[filter "lfs"]\n\tclean = other\n'):
                self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "filter.*.clean"))
        # ③core.attributesFile：記錄後不變放行、值變或 local 出現擋
        with self.with_global("[core]\n\tattributesFile = /x/attrs\n"):
            self.arm_now(rr)
            self.assertTrue(rr.evaluate()["ok"])
            fx.git(rr.R, "config", "--local", "core.attributesFile", "/x/attrs")
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "core.attributesfile"))
            fx.git(rr.R, "config", "--local", "--unset-all", "core.attributesFile")
        with self.with_global("[core]\n\tattributesFile = /y/attrs\n"):
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "core.attributesfile"))
        # ④log.showSignature 在 global：不擋、但釘 false；驗章程式（gpg.program 不納管）不被呼叫
        self.arm_now(rr)
        gpg = prog / "gpg.py"
        gmark = marker / "gpg_ran"
        gpg.write_text(f"import sys\nopen(r'{gmark}', 'a').write('x')\nsys.exit(1)\n",
                       encoding="utf-8")
        if os.name == "nt":  # 假驗章程式：Windows 用 .cmd、POSIX 用有執行位的 sh 腳本
            gcmd = prog / "fakegpg.cmd"
            gcmd.write_text(f'@"{sys.executable}" "{gpg}" %*\r\n', encoding="utf-8")
        else:
            gcmd = prog / "fakegpg"
            gcmd.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{gpg}" "$@"\n', encoding="utf-8")
            gcmd.chmod(0o755)
        tree = fx.git(rr.R, "rev-parse", "HEAD^{tree}")
        raw = (f"tree {tree}\nauthor t <t@x> 1700000000 +0000\ncommitter t <t@x> 1700000000 +0000\n"
               "gpgsig -----BEGIN PGP SIGNATURE-----\n \n abc\n -----END PGP SIGNATURE-----\n\n"
               "signed\n").encode()
        signed = subprocess.run([si_git.resolve_git(os.environ), "-C", str(rr.R), "hash-object",
                                 "-t", "commit", "-w", "--stdin"], input=raw, capture_output=True,
                                env=fx.genv(), check=True).stdout.decode().strip()
        text = f"[log]\n\tshowSignature = true\n[gpg]\n\tprogram = {Path(gcmd).as_posix()}\n"
        with self.with_global(text):
            self.assertIn("log.showSignature=false", si_git.PIN_ARGS(rr.R))
            self.real_git(rr, "-c", "log.showSignature=true", "-c",
                          f"gpg.program={Path(gcmd).as_posix()}",
                              "show", "-s", "--format=%B", signed)
            self.assertTrue(gmark.exists())  # 探針：不釘時 --format=%B 也會呼叫 gpg
            gmark.unlink()
            judge = pushguard._Judge(  # noqa: SLF001  # 守門的讀取面（帶釘定）
                rr.R, self.home, [], si_git.resolve_git(os.environ), tuple(si_git.PIN_ARGS(rr.R)))
            judge.run("show", "-s", "--format=%B", signed)
            judge.run("log", "-n", "1", "--format=%H", signed)
            self.assertFalse(gmark.exists())
            self.assertNotIn(rr.evaluate()["code"],  # 全域 showSignature／gpg.program 不擋
                             ("PUSH-GIT-CONFIG-UNSAFE", "PUSH-REPO-STATE-UNSAFE"))

    def test_AT_749_6_E_14_url_scoped_helpers_are_restored_from_the_record(self):
        url = "credential.https://dev.azure.com.helper"
        pin = si_git.PIN_ARGS(fx.new_dir("pin"), {"credential.helper": ["manager"],
                                                  url: ["manager"]})
        self.assertEqual(pin[:2], ["-c", "credential.helper="])
        i = pin.index("credential.helper=manager")
        self.assertEqual(pin[i - 1], "-c")
        j = pin.index(f"{url}=")
        self.assertEqual(pin[j - 1:j + 3], ["-c", f"{url}=", "-c", f"{url}=manager"])
        self.assertNotIn(f"{url}=", pin[j + 1:])  # 清空只出現一次，其後只有補回

    def test_AT_749_12_E_5_arm_refuses_plaintext_and_trace_credential_settings(self):
        arm = TestOsTasks.arm
        R = TestOsTasks.repo(self)
        armed = self.home / "push" / "armed.json"
        refused = (("plaintext-store", "[credential]\n\tcredentialStore = plaintext\n"),
                   ("plaintext-path", "[credential]\n\tplaintextStorePath = /x/c\n"),
                   ("trace", "[credential]\n\ttrace = /x/t.log\n"),
                   ("trace-secrets", "[credential]\n\ttraceSecrets = true\n"),
                   ("trace-ms-auth", "[credential]\n\ttraceMsAuth = 1\n"))
        for label, text in refused:
            with self.with_global(text):
                fake = OsFake()
                rc, out = arm(self, R, fake, push_only=True)
            self.assertEqual(rc, 1, label)
            self.assertIn("SCHED-PUSH-CONFIG-UNSAFE", out)
            self.assertFalse(any("Register-ScheduledTask" in s for s in fake.script()), label)
            self.assertFalse(armed.exists(), label)
        ok = "[credential]\n\tcredentialStore = secretservice\n\tusername = me\n\ttrace = false\n"
        with self.with_global(ok):
            recorded: list[tuple] = []
            real = subprocess.run

            def rec(argv, *a, **kw):
                recorded.append((argv[0], sorted(kw.get("env") or {})))
                return real(argv, *a, **kw)
            with mock.patch.object(si_git.subprocess, "run", rec):
                self.assertEqual(arm(self, R, OsFake(), push_only=True)[0], 0)
        pins = json.loads(armed.read_text(encoding="utf-8"))["config_pins"]
        self.assertEqual(sorted(pins), ["credential.credentialstore", "credential.trace",
                                        "credential.username"])
        self.assertTrue(recorded)
        for exe, keys in recorded:  # 讀取走絕對路徑 git 與允許清單環境
            self.assertEqual(exe, si_git.resolve_git(os.environ))
            self.assertIn("GIT_NO_REPLACE_OBJECTS", keys)

    def test_AT_790_7_1_no_bare_git_spawn_in_the_package(self):
        names = {"git", "git.exe", "git.cmd", "git.bat"}
        hits = []
        for path in [*PKG.glob("*.py"), ROOT / "tools" / "lib" / "apply_lock.py"]:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.List) and node.elts
                    and isinstance(node.elts[0], ast.Constant)
                        and isinstance(node.elts[0].value, str)
                            and node.elts[0].value.lower() in names):
                    hits.append(f"{path.name}:{node.lineno}")
        self.assertEqual(hits, [])  # 封閉豁免表：現行為空
        init = next(n for n in ast.walk(ast.parse((PKG / "git.py").read_text(encoding="utf-8")))
                    if isinstance(n, ast.FunctionDef) and n.name == "__init__"
                    and n.args.args and n.args.args[1].arg == "repo")
        arg_names = [a.arg for a in init.args.args]
        defaults = dict(zip(arg_names[-len(init.args.defaults):],
                            map(ast.unparse, init.args.defaults)))
        self.assertEqual(defaults["exe"], "None")  # 不是字面 "git"
        rr = self.prr()
        argv0: list[str] = []
        real = subprocess.run

        def rec(argv, *a, **kw):
            argv0.append(argv[0])
            return real(argv, *a, **kw)
        exe = si_git.resolve_git(os.environ)
        with mock.patch.object(si_git.subprocess, "run", rec):
            schedarm._write_armed(rr.R)  # noqa: SLF001
            pushcontent._head_mode(Git(rr.R), "README.md")  # noqa: SLF001
            pushcontent.rule_problem(Git(rr.R), rr.R, rr.prop, [("README.md", "M")])
            Git(rr.R).head()
        self.assertTrue(argv0)
        self.assertEqual(set(argv0), {exe})
        with mock.patch.object(si_git, "resolve_git", return_value=None), \
                mock.patch.object(si_git.subprocess, "run") as spawn:
            self.assertIsNone(Git(rr.R).run("rev-parse", "HEAD"))  # 解析不到：回 None、不退回裸名
        self.assertEqual(spawn.call_count, 0)

    def test_AT_749_6_E_9_config_changed_after_the_remote_query_is_caught_before_sending(self):
        rr = self.prr()
        sha = rr.patrol().sha
        base = self.remote_main(rr)
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(out=f"{base}\trefs/heads/main\n")
        def hook(repo):
            return fx.git(rr.R, "config", "--local", "credential.helper", "!evil")
        with mock.patch.object(patrolpush, "AFTER_LSREMOTE_HOOK", hook):
            rc, out = self.go(rr, push, remote_run=ls)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-GIT-CONFIG-UNSAFE", out)
        self.assertEqual(push.calls, [])  # 不 push
        self.assertFalse(self.result_path(sha).exists())  # 不寫結果檔、不計 attempts
        self.assertFalse((self.home / "push" / "blocked.json").exists())  # 下一心跳由 evaluate 顯示

    # ---- E-65～E-67：網址限定 http 鍵、送出前復驗 repo 狀態、git 子行程環境（第五輪）
    def test_AT_749_6_E_15_url_scoped_http_keys_and_curlopt_resolve_are_refused(self):
        rr = self.prr()
        rr.patrol()
        url = "https://h.example/"
        cases = (("sslVerify", "false", "http.*.sslverify"),
                 ("sslVerify", "true", "http.*.sslverify"),
                 ("sslCAInfo", "x.crt", "http.*.sslcainfo"),
                 ("proxy", "http://p:1", "http.*.proxy"),
                 ("followRedirects", "true", "http.*.followredirects"))
        for var, value, shown in cases:  # 值為 true 也擋：網址限定的鍵沒有「安全覆寫」這回事
            fx.git(rr.R, "config", "--local", f"http.{url}.{var}", value)
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown), ("local", var))
            fx.git(rr.R, "config", "--local", "--unset-all", f"http.{url}.{var}")
            with self.with_global(f'[http "{url}"]\n\t{var} = {value}\n'):
                self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", shown), var)
                self.assertEqual(si_git.arm_record(rr.R), (None, shown), ("arm", var))
        resolve = "h.example:443:127.0.0.1"
        fx.git(rr.R, "config", "--local", "http.curloptResolve", resolve)
        self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "http.curloptresolve"))
        fx.git(rr.R, "config", "--local", "--unset-all", "http.curloptResolve")
        with self.with_global(f"[http]\n\tcurloptResolve = {resolve}\n"):
            self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "http.curloptresolve"))
            self.assertEqual(si_git.arm_record(rr.R), (None, "http.curloptresolve"))
        self.assertTrue(rr.evaluate()["ok"])  # 防假紅：不帶網址的 http 鍵（甲類、已釘定）照舊放行
        with self.with_global("[http]\n\tsslVerify = false\n\tpostBuffer = 524288000\n"):
            self.assertTrue(rr.evaluate()["ok"])
            self.assertIsNotNone(si_git.arm_record(rr.R)[0])

    def test_AT_749_6_E_16_repo_state_is_rechecked_right_before_sending(self):
        rr = self.prr()
        sha = rr.patrol().sha
        base = self.remote_main(rr)
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(out=f"{base}\trefs/heads/main\n")
        grafts = rr.R / ".git" / "info" / "grafts"

        def hook(repo):  # 遠端查詢之後才出現的狀態：evaluate 看不到、只有送出前的復驗看得到
            grafts.parent.mkdir(exist_ok=True)
            grafts.write_text(f"{sha} {base}\n", encoding="utf-8")
        try:
            with mock.patch.object(patrolpush, "AFTER_LSREMOTE_HOOK", hook):
                rc, out = self.go(rr, push, remote_run=ls)
        finally:
            grafts.unlink(missing_ok=True)
        self.assertEqual(rc, 0, out)
        self.assertIn("PUSH-REPO-STATE-UNSAFE", out)
        self.assertEqual(push.calls, [])
        self.assertFalse(self.result_path(sha).exists())

    def test_AT_749_6_E_17_hidden_or_untracked_files_in_the_hooks_directory_are_refused(self):
        rr = self.prr()
        with mock.patch.object(si_git, "EXPECTED_HOOKS", "hk"):  # 暫存 repo 的 hooks 目錄放進工作樹
            fx.git(rr.R, "config", "core.hooksPath", "hk")
            fx.put(rr.R, "hk/pre-push", "#!/bin/sh\nexit 0\n")
            fx.commit_all(rr.R, "hooks dir")
            rr.push()
            rr.patrol()
            self.assertTrue(rr.evaluate()["ok"])  # 防假紅：追蹤、未隱藏、目錄內沒有別的檔
            expect = ("PUSH-REPO-STATE-UNSAFE", "hooks")
            for flag in ("skip-worktree", "assume-unchanged"):
                fx.git(rr.R, "update-index", f"--{flag}", "--", "hk/pre-push")
                self.assertEqual(self.unsafe(rr), expect, flag)
                fx.git(rr.R, "update-index", f"--no-{flag}", "--", "hk/pre-push")
            self.assertTrue(rr.evaluate()["ok"])
            (rr.R / "hk" / "extra-hook").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            self.assertEqual(self.unsafe(rr), expect, "untracked")
            (rr.R / "hk" / "extra-hook").unlink()
            fx.git(rr.R, "config", "core.hooksPath", p7x.HOOKS_DIR)

    def test_AT_749_5_E_14_git_child_env_neutralises_grafts_and_names_each_autosdd_variable(self):
        self.assertEqual(si_git.ENV_FIXED["GIT_GRAFT_FILE"], si_git.NO_GRAFTS)
        self.assertTrue(Path(si_git.NO_GRAFTS).parent.is_file())  # 父層是一般檔案＝這個路徑建不出來
        parent = {"AUTOSDD_PREPUSH_SERIAL_LEGS": "1", "AUTOSDD_PARALLEL_TESTS_WORKERS": "4",
                  "AUTOSDD_CPU_HEADLESS": "1", "AUTOSDD_SI_DIR": "x", "AUTOSDD_OTHER": "v",
                  "AUTOSDD_UNATTENDED": "1", "GIT_GRAFT_FILE": "evil"}
        with mock.patch.object(si_git, "ENV_TEST_PASSTHROUGH", ()):
            for platform in ("win32", "linux"):
                read = si_git.env_for_git(parent, "read", platform=platform)
                push = si_git.env_for_git(parent, "push", platform=platform)
                self.assertEqual({k for k in read if k.startswith("AUTOSDD_")}, set(), platform)
                self.assertEqual({k for k in push if k.startswith("AUTOSDD_")},
                                 set(si_git._PUSH_AUTOSDD), platform)  # noqa: SLF001
                for env in (read, push):
                    self.assertEqual(env["GIT_GRAFT_FILE"], si_git.NO_GRAFTS, platform)
        rr = self.prr()  # 真 git：嫁接檔存在時，帶此環境的 git 看不到它（不帶則看得到＝探針有效）
        grafts = rr.R / ".git" / "info" / "grafts"
        head = fx.git(rr.R, "rev-parse", "HEAD")
        grafts.parent.mkdir(exist_ok=True)
        grafts.write_text(f"{head}\n", encoding="utf-8")  # 把 HEAD 嫁接成沒有父提交
        try:
            exe = si_git.resolve_git(os.environ)
            count = lambda env: subprocess.run(  # noqa: E731
                [exe, "-C", str(rr.R), "rev-list", "--count", head], env=env, capture_output=True,
                encoding="utf-8", check=True).stdout.strip()
            bare = {k: v for k, v in os.environ.items() if k != "GIT_NO_REPLACE_OBJECTS"}
            self.assertEqual(count(bare), "1")
            self.assertGreater(int(count({**bare, "GIT_GRAFT_FILE": si_git.NO_GRAFTS})), 1)
        finally:
            grafts.unlink(missing_ok=True)

    # ---- E-68：SCG-4 二審補的斷言（P2-1～3、P3-1～3）
    def test_AT_749_4_E_33_covered_is_exact_for_files_and_prefix_for_directories(self):
        allow = ["docs/L.md", "docs/props/PROP-1/"]
        for path, want in (("docs/L.md", True), ("docs/L.md.bak", False), ("docs/L.mdx", False),
                           ("docs/props/PROP-1/r1.md", True), ("docs/props/PROP-10/r1.md", False),
                           ("docs/props/PROP-1", False), ("other/L.md", False)):
            self.assertEqual(pushguard.covered(path, allow), want, path)

    def test_AT_749_4_E_34_content_binding_digest_is_the_manifest_formula(self):
        rr = self.rr()
        root = fx.new_dir("p23")
        root.mkdir(parents=True, exist_ok=True)
        files = {"a.txt": b"alpha\n", "crlf.txt": b"x\r\ny\r\n"}  # gone.txt 沒有檔（已刪除）
        for name, data in files.items():
            (root / name).write_bytes(data)
        touched = ["a.txt", "crlf.txt", "gone.txt"]
        ev = {"id": "APP-1", "kind": "app.promote"}
        rows = [(EVL, "M", "", json.dumps(ev) + "\n")]
        exe = si_git.resolve_git(os.environ)
        judge = pushguard._Judge(rr.R, self.home, [], exe)  # noqa: SLF001
        judge.raw_blob = lambda rev, rel: files.get(rel)
        want = si_manifest.paths_manifest(root, touched, lf=True)
        mismatch = "觸及檔內容與 post_sha256 不符"

        def verdict(digest: str):
            return judge.content_problem("s", {**ev, "post_sha256": digest}, {"cls": "P"}, touched,
                                         rows)
        self.assertIsNone(verdict(want))  # 缺檔記 absent、CRLF 先換成 LF：與 manifest 同值
        self.assertEqual(verdict(si_manifest.paths_manifest(root, touched, lf=False)), mismatch)
        self.assertEqual(verdict(si_manifest.paths_manifest(root, touched[:2], lf=True)), mismatch)
        self.assertEqual(verdict("sha256:" + "0" * 64), mismatch)

    def test_AT_749_4_E_35_the_row_bytes_parameter_reaches_the_new_row_check(self):
        rr = self.rr()
        row = fx.line([fx.obs_id(21), "2026-11-11 12:00", "長列 " + "字" * 200, "症狀",
                       "tools/lib/si_demo.py:12", "doc", "P3", "open",
                       "面=文件;來源=代理;回報者=SA"])
        text = obs_edit(rr.R, lambda ls: ls[:-1] + [row, ""])
        sha = self.manual(rr, {OBS: text})
        loose = pushguard.evaluate(rr.R, {"sched_auto_push": True}, rr.si, NOW)
        self.assertTrue(loose["ok"], loose)  # 沒設上限：不驗位元組
        params = {"sched_auto_push": True, "row_max_bytes": 100}
        tight = pushguard.evaluate(rr.R, params, rr.si, NOW)
        self.blocked(tight, "PUSH-LEDGER-RULE", sha)
        self.assertIn("ROW-BYTES-OVER", tight["detail"])

    def test_AT_749_5_E_15_single_key_rules_judge_the_right_direction(self):
        hit = si_git.config_rule_hit
        for key, bad, good in (("core.usereplacerefs", "true", "false"),
                               ("protocol.ext.allow", "always", "never"),
                               ("log.showsignature", "true", "false"),
                               ("push.gpgsign", "true", "false")):
            self.assertIsNotNone(hit("local", key, bad), key)  # 回要顯示的鍵名（子區段以 * 代）
            self.assertIsNone(hit("local", key, good), key)
            self.assertIsNone(hit("global", key, bad), key)  # 甲類：system／global 層被釘定、不擋
        for var in ("COUNT", "PARAMETERS", "KEY_0", "VALUE_0"):
            self.assertIsNotNone(si_git.ENV_RULES.match(f"GIT_CONFIG_{var}"), var)

    def test_AT_749_5_E_16_pins_take_the_last_value_and_keys_normalise_by_segment(self):
        pin = si_git.PIN_ARGS(fx.new_dir("pin2"), {"http.sslcainfo": ["first.crt", "last.crt"]})
        self.assertIn("http.sslCAInfo=last.crt", pin)
        self.assertNotIn("http.sslCAInfo=first.crt", pin)
        norm = si_git._norm_key  # noqa: SLF001
        self.assertEqual(norm("Core.SshCommand"), "core.sshcommand")
        self.assertEqual(norm("Remote.Origin.URL"), "remote.Origin.url")
        self.assertEqual(norm("http.HTTPS://H.Ex/.SslVerify"), "http.HTTPS://H.Ex/.sslverify")

    def test_AT_749_5_E_17_arm_stops_when_the_config_cannot_be_read(self):
        rr = self.prr()
        for fake in (None, types.SimpleNamespace(returncode=128, stdout="")):
            with mock.patch.object(Git, "run", return_value=fake):
                self.assertEqual(si_git.arm_record(rr.R), (None, "git 設定讀取失敗"))

    def test_AT_749_5_E_18_safe_path_drops_directories_that_cannot_be_resolved(self):
        real = Path.resolve

        def resolve(self, *a, **kw):
            if self.name == "unresolvable-dir":
                raise OSError("boom")
            return real(self, *a, **kw)
        env = {"PATH": os.pathsep.join(["unresolvable-dir", str(Path(sys.base_prefix) / "keep")])}
        with mock.patch.object(Path, "resolve", resolve):
            kept = si_git.safe_path(env).split(os.pathsep)
        self.assertNotIn("unresolvable-dir", kept)

    def test_AT_749_5_E_19_a_duplicated_hooks_path_is_refused(self):
        rr = self.prr()
        rr.patrol()
        fx.git(rr.R, "config", "--add", "core.hooksPath", p7x.HOOKS_DIR)  # 兩筆都等於既定值
        self.assertEqual(self.unsafe(rr), ("PUSH-GIT-CONFIG-UNSAFE", "core.hookspath"))
        fx.git(rr.R, "config", "--unset-all", "core.hooksPath")
        fx.git(rr.R, "config", "core.hooksPath", p7x.HOOKS_DIR)
        self.assertTrue(rr.evaluate()["ok"])

    def test_AT_749_2_E_4_markdown_proposals_are_hashed_after_crlf_normalisation(self):
        prop = "PROP-001"
        body = b"line one\nline two\n"
        sha = lambda raw: "sha256:" + hashlib.sha256(raw).hexdigest()  # noqa: E731
        pdir = f"{si_events.PROPOSALS_REL}/{prop}/"
        events = [{"kind": "prop", "id": prop, "rev": 1, "body_sha256": sha(body),
                   "patch_sha256": sha(body)}]
        check = lambda name, raw: pushcontent._proposal_problem(  # noqa: E731, SLF001
            prop, [(pdir + name, "A", "100644", True, None, None, raw)], events)
        self.assertIsNone(check("r1.md", b"line one\r\nline two\r\n"))  # .md：CRLF 先正規化
        self.assertEqual(check("r1.patch", b"line one\r\nline two\r\n"), "r1.patch sha-mismatch")
        self.assertEqual(check("r1.md", b"line one\r\nline 2\r\n"), "r1.md sha-mismatch")

    def test_AT_749_6_E_18_runner_grace_and_job_termination_contract(self):
        self.assertLessEqual(runner.KILL_GRACE_SECONDS, 10)  # 寬限遠小於推送牆鐘與 hook 預算
        timeouts, kills = [], []

        class Proc:
            pid, returncode = 4321, None

            def communicate(self, timeout=None):
                timeouts.append(timeout)
                raise subprocess.TimeoutExpired("x", timeout)

            def kill(self):
                kills.append(1)
        with (mock.patch.object(runner.subprocess, "Popen", return_value=Proc()),
              mock.patch.object(runner, "_job_open", return_value=(object(), "")),
              mock.patch.object(runner, "_job_end", return_value=True),
              mock.patch.object(runner, "_kill_tree") as tree):
            res = runner.run_argv(["x"], env={}, timeout=3)
        self.assertEqual(timeouts, [3, runner.KILL_GRACE_SECONDS])  # 收輸出有上界
        self.assertEqual(kills, [1])  # Job 終結成功後仍殺父行程
        tree.assert_not_called()
        self.assertTrue(res.timed_out)
        self.assertEqual(res.note, "job-terminated output-incomplete")

    def test_AT_749_6_E_19_naive_timestamps_are_not_accepted_by_the_guard(self):
        self.assertIsNone(pushguard._t("2026-11-11T12:00:00"))  # noqa: SLF001
        self.assertIsNone(pushguard._t(None))  # noqa: SLF001
        self.assertIsNotNone(pushguard._t("2026-11-11T12:00:00+08:00"))  # noqa: SLF001

    def test_AT_749_12_E_4_credential_helpers_are_recorded_and_limited_at_arm_time(self):
        arm = TestOsTasks.arm
        R = TestOsTasks.repo(self)
        armed = self.home / "push" / "armed.json"
        with self.with_global("[credential]\n\thelper = manager\n\thelper = cache\n"):
            fake = OsFake()
            self.assertEqual(arm(self, R, fake, push_only=True)[0], 0)
        self.assertEqual(json.loads(armed.read_text(encoding="utf-8"))["config_pins"],
                         {"credential.helper": ["manager", "cache"]})  # 保留順序
        armed.unlink()
        with self.with_system(self.TYPICAL_SYSTEM), \
                self.with_global("[core]\n\tsshCommand = ssh -i k\n"):  # 其餘乙類鍵一併記錄
            self.assertEqual(arm(self, R, OsFake(), push_only=True)[0], 0)
        self.assertEqual(
            sorted(json.loads(armed.read_text(encoding="utf-8"))["config_pins"]),
            sorted(["core.sshcommand", *self.TYPICAL_KEYS]))
        armed.unlink()
        for label, text in (("bang", "!evil"), ("absolute", "C" + ":/x/git-credential-x.exe"),
                            ("store", "store")):
            with self.with_global(f"[credential]\n\thelper = {text}\n"):
                fake = OsFake()
                rc, out = arm(self, R, fake, push_only=True)
            self.assertEqual(rc, 1, label)
            self.assertIn("SCHED-PUSH-CONFIG-UNSAFE", out)
            self.assertIn("改用 manager 或系統鑰匙圈", out)
            self.assertFalse(any("Register-ScheduledTask" in s for s in fake.script()), label)
            self.assertFalse(armed.exists(), label)
        fx.git(R, "config", "--local", "credential.helper", "manager")  # local 層有 helper 一律不合
        fake = OsFake()
        self.assertEqual(arm(self, R, fake, push_only=True)[0], 1)
        self.assertFalse(any("Register-ScheduledTask" in s for s in fake.script()))

    # ---- E-30、E-31、E-36、E-41、E-42：內容約束
    def test_AT_749_4_E_23_proposal_files_are_bound_to_the_event_hashes(self):
        good = {"r2.patch": b"diff content\n", "r2.md": b"body\n", "verify2.json": b'{"a": 1}\n'}
        cases = (("no-event-rev", {"r9.md": b"x\n"}, {}, "r9.md no-event"),
                 ("no-event-verify", {"verify7.json": b"{}\n"}, {}, "verify7.json no-event"),
                 ("patch-differs", {"r2.patch": b"diff content!\n"}, {"r2.patch": good["r2.patch"]},
                  "r2.patch sha-mismatch"),
                 ("body-differs", {"r2.md": b"body?\n"}, {"r2.md": good["r2.md"]},
                     "r2.md sha-mismatch"),
                 ("verify-differs", {"verify2.json": b'{"a": 2}\n'},
                     {"verify2.json": good["verify2.json"]},
                  "verify2.json sha-mismatch"))
        for label, files, claims, frag in cases:
            with self.subTest(label):
                rr = self.rr()
                d = self.pdir(rr)
                data = {f"{d}/{n}": v for n, v in files.items()}
                if label.startswith("no-event"):  # 沒有對應事件：不補綁定事件
                    rr_events = lambda *a, **k: None  # noqa: E731
                    with mock.patch.object(rr, "bind", rr_events):
                        sha = self.manual(rr, data)
                else:
                    sha = self.manual(rr, data, claims=claims)
                self.blocked(rr.evaluate(), "PUSH-PROPOSAL-MISMATCH", sha, label, frag=frag)
        rr = self.rr()  # ⑤正向：三種檔的位元組都與事件相符
        d = self.pdir(rr)
        self.manual(rr, {f"{d}/{n}": v for n, v in good.items()})
        self.assertTrue(rr.evaluate()["ok"])

    def test_AT_749_4_E_24_undecodable_binary_and_obs_disposition(self):
        rr = self.rr()  # ①既有 touched 檔改成非 UTF-8
        sha = self.manual(rr, touched_bytes=(rr.R / rr.touched[0]).read_bytes() + b"\xff\xfe")
        self.blocked(rr.evaluate(), "PUSH-SECRET-PATTERN", sha, frag=f"{rr.touched[0]} undecodable")
        for label, name, data in (("nul-in-proposal", "r2.patch", b"a\x00b\n"),
                                   ("bad-utf8-in-proposal", "r2.md", b"\xff\xfe bad")):
            rr = self.rr()  # ②含 NUL、③無法解碼的新增檔（雜湊綁定通過，才輪到解碼判準）
            rel = f"{self.pdir(rr)}/{name}"
            sha = self.manual(rr, {rel: data})
            self.blocked(rr.evaluate(), "PUSH-SECRET-PATTERN", sha, label,
                frag=f"{rel} undecodable")
        rr = self.rr()  # ④處置欄寫入任意文字
        text = obs_edit(rr.R, lambda ls: [set_cell(ln, 7, "隨便寫的字") if ln.startswith(
            f"| {fx.obs_id(1)} |") else ln for ln in ls])
        sha = self.manual(rr, {OBS: text})
        res = rr.evaluate()
        self.blocked(res, "PUSH-LEDGER-RULE", sha)
        self.assertIn("處置欄", res["detail"])
        self.assertIn(fx.obs_id(1), res["detail"])
        rr = self.rr()  # ⑤處置欄格式合規（retired＋座標）、但寫入植入的機密樣式（值為權杖）
        token = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
        text = obs_edit(rr.R, lambda ls: [set_cell(ln, 7,
                f"retired；依據 tools/lib/si_demo.py:12 {token}") if ln.startswith(
            f"| {fx.obs_id(1)} |") else ln for ln in ls])
        sha = self.manual(rr, {OBS: text})
        res = rr.evaluate()
        self.assertEqual(res["code"], "PUSH-SECRET-PATTERN", res)
        self.assertNotIn(token, json.dumps(res, ensure_ascii=False))
        rr = self.rr()  # ⑥處置欄格式不合、也不含權杖：碼恆為 PUSH-LEDGER-RULE（兩條判準各自獨立）
        text = obs_edit(rr.R, lambda ls: [set_cell(ln, 7, "retired；沒有座標") if ln.startswith(
            f"| {fx.obs_id(1)} |") else ln for ln in ls])
        sha = self.manual(rr, {OBS: text})
        self.blocked(rr.evaluate(), "PUSH-LEDGER-RULE", sha)

    def test_AT_749_4_E_25_mode_verdict_is_one_function_for_commit_and_guard(self):
        table = (("D", "100644", "000000", True), ("A", None, "100644", True),
                 ("A", None, "100755", False),
                 ("M", "100644", "100644", True), ("M", "100755", "100755", True),
                 ("M", "100644", "100755", False), ("M", "100755", "100644", True),
                 ("A", None, "120000", False), ("T", "100644", "120000", False),
                 ("A", None, "160000", False))
        for status, old, new, want in table:
            self.assertEqual(pushcontent.mode_verdict(status, old, new), want, (status, old, new))
        callers = set()
        for name in ("pushguard", "pushcontent"):
            tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
            callers |= {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
                        for c in ast.walk(fn) if isinstance(c, ast.Call)
                        and ast.unparse(c.func) == "mode_verdict"}
        self.assertEqual(callers, {"rule_problem", "judge"})
        rr = self.rr()  # 提交端：既有 100755 的 touched 檔只改內容 ⇒ 放行（真變體與替身變體皆跑）
        rel = rr.touched[0]
        fx.git(rr.R, "update-index", "--chmod=+x", "--", rel)
        fx.git(rr.R, "commit", "-q", "-m", "exec bit")
        rr.push()
        fx.put(rr.R, rel, fx.read(rr.R, rel) + "改內容\n")
        if sys.platform != "win32":
            os.chmod(rr.R / rel, 0o755)  # POSIX 的真檔：可執行位元隨檔案
        git = Git(rr.R)
        self.assertIsNone(pushcontent.rule_problem(git, rr.R, rr.prop, [(rel, "M")]))
        with mock.patch.object(pushcontent, "_wt_mode", lambda path, old=None: "100755"):
            self.assertIsNone(pushcontent.rule_problem(git, rr.R, rr.prop, [(rel, "M")]))  # 替身
            new = f"{self.pdir(rr)}/r4.md"
            fx.put(rr.R, new, "x\n")
            problem = pushcontent.rule_problem(git, rr.R, rr.prop, [(new, "A")])  # ③新增 100755
            self.assertIn("100755", problem or "")
        fx.git(rr.R, "checkout", "-q", "--", rel)  # 回到乾淨再造 100644→100755
        rr2 = self.rr()
        fx.put(rr2.R, rr2.touched[0], fx.read(rr2.R, rr2.touched[0]) + "x\n")
        with mock.patch.object(pushcontent, "_wt_mode", lambda path, old=None: "100755"):
            self.assertIn("100755", pushcontent.rule_problem(
                Git(rr2.R), rr2.R, rr2.prop, [(rr2.touched[0], "M")]) or "")  # ②兩邊皆拒
        fake_reg = types.SimpleNamespace(st_mode=0o100755)  # ④Windows 規則：新模式取舊模式
        with mock.patch.object(pushcontent, "_lstat", lambda p: fake_reg), \
                mock.patch.object(pushcontent.sys, "platform", "win32"):
            self.assertEqual(pushcontent._wt_mode(Path("x"), "100644"), "100644")  # noqa: SLF001
            self.assertEqual(pushcontent._wt_mode(Path("x"), None), "100644")  # noqa: SLF001
            self.assertEqual(pushcontent._wt_mode(Path("x"), "100755"), "100755")  # noqa: SLF001
        with mock.patch.object(pushcontent, "_lstat", lambda p: fake_reg), \
                mock.patch.object(pushcontent.sys, "platform", "linux"):
            self.assertEqual(pushcontent._wt_mode(Path("x"), "100644"), "100755")  # noqa: SLF001

    def test_AT_749_4_E_31_quoted_and_json_forms_are_scanned_and_masked_alike(self):
        v = "AbCdEf0123456789xyzQ"
        hits = (f'api_key = "{v}"', f"SECRET_KEY='{v}'", f'"token":"{v}"', f'"token": "{v}",',
                f'key: "{v}"', f"password = {v};", f"secret={v},")
        for text in hits:
            self.assertIn("key-value", si_git.scan_names(text), text)
            masked = si_git.mask(text)
            self.assertNotIn(v, masked, text)
            self.assertIn("***", masked)
            self.assertEqual(si_git.mask(masked), masked)  # 冪等
        self.assertEqual(si_git.mask('"token": "' + v + '",'), '"token": "***",')  # 引號與標點保留
        for text in ("token: str", '"token": null', 'password = ""', "key: Optional[str]",
                     'api_key = os.environ["X"]'):
            self.assertEqual(si_git.scan_names(text), [], text)
            self.assertEqual(si_git.mask(text), text, text)  # 不命中、不改寫

    def test_AT_749_4_E_32_aws_and_sk_patterns_have_scan_samples(self):
        aws = "AKI" + "A" + "ABCDEFGH" + "IJKLMNOP"
        sk = "sk" + "-" + "A1b2C3d4E5f6G7h8I9j0K1"
        for name, secret in (("aws-key", aws), ("sk-token", sk)):
            rr = self.rr()
            rel = f"{self.pdir(rr)}/r2.md"
            sha = self.manual(rr, {rel: f"說明 {secret}\n"})
            res = rr.evaluate()
            self.blocked(res, "PUSH-SECRET-PATTERN", sha, frag=f"{rel} {name}")
            self.assertNotIn(secret, json.dumps(res, ensure_ascii=False))
            self.assertEqual(si_git.mask(f"x {secret} y"), "x *** y")  # 遮罩輸出皆為 ***
            self.assertIn(name, si_git.scan_names(secret))
        # 15 字元：不命中
        self.assertEqual(si_git.scan_names("AKI" + "A" + "ABCDEFGH" + "IJKLMNO"), [])
        # 19 字元
        self.assertEqual(si_git.scan_names("sk" + "-" + "A1b2C3d4E5f6G7h8I9j0K"[:19]), [])

    def test_AT_749_7_4_mask_shapes_are_a_closed_list_with_legacy_regression(self):
        names = {name for name, *_rest in si_git.SECRET_PATTERNS}
        self.assertEqual(names, {"key-value", "auth-header", "bearer", "basic", "github-token",
                                 "sk-token", "aws-key", "private-key", "url-userinfo"})
        tcs = (ROOT / "docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md").read_text(
            encoding="utf-8")
        section = tcs.split("### A.8", 1)[1].split("### A.9", 1)[0]
        listed = {m for m in re.findall(r"^\| `([a-z-]+)` \|", section, re.M)}
        self.assertEqual(listed, names)  # 附錄 A.8 的樣式名集合逐字相等
        b64 = "dXNl" + "cjpwYXNz" + "d29yZA=="
        tok = "tok" + SECRET + "x1y2z3"
        legacy = (  # 子案 a～n：舊 pushguard／runner 兩套 _MASKS 的每一條樣式各構造一個輸入
            ("a", f"https://u:{tok}@h/x.git", tok), ("b", f"ssh://{tok}@h/x.git", tok),
            ("c", f"token={tok}", tok), ("d", f"password: {tok}", tok), ("e", f"passwd={tok}", tok),
            ("f", f"secret = {tok}", tok), ("g", f"key={tok}", tok), ("h", f"Bearer {tok}", tok),
            ("i", f"bearer {tok}", tok), ("j", f"Authorization: Bearer {tok}", tok),
            ("k", f"Authorization: Basic {b64}", b64), ("l", f"Authorization: Digest {tok}", tok),
            ("m", "sk" + "-" + "A1b2C3d4E5f6G7h8I9j0K1", "A1b2C3d4E5f6G7h8I9j0K1"),
            ("n", f"curl -H 'Authorization: token {tok}' x", tok))
        for label, text, secret in legacy:
            got = si_git.mask(text)
            self.assertNotIn(secret, got, label)
            self.assertEqual(si_git.mask(got), got, label)  # 冪等
        # 不帶 Authorization 前綴、保留字樣
        self.assertEqual(si_git.mask(f"Bearer {tok}"), "Bearer ***")
        self.assertEqual(si_git.mask(f"Basic {b64} z"), "Basic *** z")
        self.assertEqual(si_git.mask(f"Authorization: Bearer {tok}"), "Authorization: Bearer ***")

    # ---- E-33、E-34、E-35、E-38、E-46
    def test_AT_749_5_E_7_guard_reads_use_the_absolute_git_path(self):
        rr = self.prr()
        rr.patrol()
        exe = si_git.resolve_git(os.environ)
        argvs: list[list[str]] = []
        real = subprocess.run

        def rec(argv, *a, **kw):
            argvs.append(list(argv))
            return real(argv, *a, **kw)
        with mock.patch.object(si_git.subprocess, "run", rec):
            self.assertTrue(rr.evaluate()["ok"])
        subs = {sub_of(tuple(a[3:])) for a in argvs}
        self.assertLessEqual({"rev-parse", "rev-list", "diff-tree", "cat-file",
            "symbolic-ref", "status",
                              "config"}, subs | {"config"})
        self.assertEqual({a[0] for a in argvs}, {exe})  # argv[0] 全為 exe
        for name in ("git", "pushguard", "pushcontent", "patrolpush", "runner", "schedarm"):
            tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
            bare = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.List) and n.elts
                    and isinstance(n.elts[0], ast.Constant)
                    and n.elts[0].value in ("git", "taskkill")]
            self.assertEqual(bare, [], name)
        rows = (PKG / "git.py").read_text(encoding="utf-8").splitlines()
        # 不用 shutil.which（逐行判定，不對整份檔案斷言缺席）
        self.assertEqual([ln for ln in rows if "which(" in ln or "import shutil" in ln], [])
        cwd_repo = fx.new_dir("cwdrepo")  # 任務 cwd 放假 git：不被選中
        cwd_repo.mkdir(parents=True, exist_ok=True)
        for fake in ("git.bat", "git.cmd", "git"):
            (cwd_repo / fake).write_text("echo evil\n", encoding="utf-8")
            (cwd_repo / fake).chmod(0o755)
        old = os.getcwd()
        self.addCleanup(os.chdir, old)
        os.chdir(cwd_repo)
        path = os.pathsep.join([str(cwd_repo), os.environ.get("PATH", "")])
        got = si_git.resolve_git({"PATH": path,
            "PATHEXT": os.environ.get("PATHEXT", ".EXE;.BAT;.CMD")})
        self.assertTrue(got and not Path(got).resolve().is_relative_to(cwd_repo.resolve()), got)
        with mock.patch.object(pushguard, "resolve_git",
            return_value=str(Path(exe).with_name("git2"))):
            res = rr.evaluate()  # armed.json 記錄的 git 與解析出的不同
        self.assertEqual((res["code"], res["detail"]),
            ("PUSH-GIT-UNAVAILABLE", "git 路徑與安裝時記錄不同"))
        shouted = exe.upper() if sys.platform == "win32" else exe
        with mock.patch.object(pushguard, "resolve_git", return_value=shouted):
            self.assertTrue(rr.evaluate()["ok"])  # Windows 不分大小寫；POSIX 本來就相同

    def test_AT_749_9_E_3_lock_liveness_uses_process_identity(self):
        from lib import apply_lock
        wall = fx.params_dict()["sched_push_wall_minutes"] * 60
        real = runner.pid_started_at(os.getpid())
        iso = lambda off: datetime.fromtimestamp(real + off, UTC).isoformat()  # noqa: E731
        stale = wall + patrolpush.LOCK_SLACK_SECONDS + 400
        cases = (("reused-pid-and-old", iso(-6), stale, True),
                 ("same-process", iso(-3), stale, False),
                 ("legacy-format", None, stale, False), ("not-old-enough", iso(-6), 5, False))
        for label, created, age, reclaimed in cases:
            with self.subTest(label):
                self.new_home()
                rr = self.prr()
                rr.patrol()
                lock = self.home / "locks" / "push.lock"
                lock.parent.mkdir(parents=True, exist_ok=True)
                body = {"pid": os.getpid(), "acquired_at": iso(-stale)}
                if created is not None:
                    body["process_started_utc"] = created
                if label == "legacy-format":  # 舊格式：兩行 `<pid>\n<時間>`，沒有建立時間欄
                    lock.write_text(f"{os.getpid()}\n{iso(-stale)}\n", encoding="utf-8")
                else:
                    lock.write_text(json.dumps(body), encoding="utf-8")
                old = time.time() - age
                os.utime(lock, (old, old))
                push = p7x.run_argv_spy()
                ls = p7x.run_argv_spy(out=f"{self.remote_main(rr)}\trefs/heads/main\n")
                rc, out = self.go(rr, push, remote_run=ls)
                self.assertEqual(rc, 0, out)
                self.assertEqual(len(push.calls), 1 if reclaimed else 0, out)
                if not reclaimed:
                    self.assertIn("PUSH-RUNNING", out)
        path = self.home / "locks" / "fmt.lock"
        with apply_lock.acquire_guarded(path, 1, 10, holder_alive=lambda info: False,
                                        process_started_utc="2026-01-01T00:00:00+00:00"):
            doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(sorted(doc), ["acquired_at", "pid", "process_started_utc"])
        self.assertEqual(doc["pid"], os.getpid())

    def test_AT_749_9_6_the_running_window_comes_from_the_record_not_a_constant(self):
        sig = inspect.signature(runner.process_identity)
        self.assertEqual(sig.parameters["window_seconds"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(sig.parameters["window_seconds"].default, inspect.Parameter.empty)
        for name in ("pushguard", "patrolpush", "patrolrun", "runner"):
            src = (PKG / f"{name}.py").read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?<![0-9.])3600(?![0-9])", src), name)  # 沒有寫死的一小時
        real = runner.pid_started_at(os.getpid())
        wall = 45 * 60
        cur = self.home / "push" / "current.json"
        cur.parent.mkdir(parents=True, exist_ok=True)

        def put(started_off, created=None):
            started = datetime.fromtimestamp(real + started_off, UTC)
            doc = {"sha": "a" * 40, "pid": os.getpid(), "started_at": started.isoformat(),
                   "wall_due_at": (started + timedelta(seconds=wall)).isoformat()}
            if created is not None:
                doc["process_started_utc"] = datetime.fromtimestamp(real + created, UTC).isoformat()
            cur.write_text(json.dumps(doc), encoding="utf-8")
            return started + timedelta(seconds=60)
        alive = patrolrun._alive  # noqa: SLF001
        now = put(-60, created=0)
        self.assertTrue(pushguard.running(self.home, now, alive))  # 有建立時間：身分相符
        now = put(-60, created=100)
        self.assertFalse(pushguard.running(self.home, now, alive))  # 差 >5 秒＝pid 被重用
        now = put(-60)
        self.assertTrue(pushguard.running(self.home, now, alive))  # 無建立時間：窗口內
        now = put(500)
        self.assertFalse(pushguard.running(self.home, now, alive))  # 行程早於 started_at−120
        now = put(-(wall + 600 + 100))  # 行程晚於 started_at＋牆鐘＋600
        self.assertFalse(pushguard.running(self.home, now, alive))
        self.assertEqual(pushguard.record_window("2026-01-01T00:00:00+00:00",
                                                 "2026-01-01T00:10:00+00:00"), 600 + 600)

    def test_AT_749_6_E_10_ls_remote_lines_are_matched_by_ref_name(self):
        rr = self.prr()
        sha = rr.patrol().sha
        base = self.remote_main(rr)
        other = "b" * 40

        def ask(out):
            got, _run = patrolpush.remote_main(rr.R, {}, p7x.run_argv_spy(out=out), "git")
            return got
        decoy = f"{other}\trefs/heads/x/refs/heads/main\n"
        self.assertEqual(ask(decoy + f"{base}\trefs/heads/main\n"), base)  # ①取正確那一行
        self.assertEqual(ask(decoy), "")  # ②只有誘餌＝遠端沒有該分支
        self.assertEqual(ask(f"{base}\trefs/heads/main\n{other} refs/heads/main\n"),
            patrolpush.MULTI)
        for bad in ("G" * 40, "A" * 40, "a" * 39, "a" * 41):  # ④sha 欄不是 40 碼小寫十六進位
            self.assertEqual(ask(f"{bad}\trefs/heads/main\n"), "", bad)
        res = {"sha": sha, "base": base}
        self.assertEqual(patrolpush.pre_push_problem(rr.R, res, ""), ("PUSH-REMOTE-DRIFT",
                                                                       f"<空> {base[:8]}"))
        self.assertEqual(patrolpush.pre_push_problem(rr.R, res, patrolpush.MULTI),
                         ("PUSH-REMOTE-DRIFT", f"<多筆> {base[:8]}"))
        push = p7x.run_argv_spy()
        rc, out = self.go(rr, push, remote_run=p7x.run_argv_spy(out=decoy))
        self.assertEqual((rc, push.calls), (0, []))
        self.assertIn("PUSH-REMOTE-DRIFT", out)

    def test_AT_749_12_E_3_the_owner_comes_from_the_current_interactive_session(self):
        arm = TestOsTasks.arm
        R = TestOsTasks.repo(self)
        a = ("TESTDOM" + "\\" + "alice", OsFake.SID)
        b = ("TESTDOM" + "\\" + "bob", OsFake.OTHER_SID)
        fake = OsFake(sessions={1: [a], 2: [b]}, cur_session=2, mine_sid=OsFake.OTHER_SID,
                      patrol_sid=OsFake.OTHER_SID, push_user="x", push_sid=OsFake.OTHER_SID)
        # ①預期 SID 為本工作階段的擁有者 B
        self.assertEqual(arm(self, R, fake, push_only=True)[0], 0)
        with self.win():
            script = schedarm._session_argv()[-1]  # noqa: SLF001
        for needle in ("GetCurrentProcess().SessionId", "Where-Object { $_.SessionId -eq $cur }"):
            self.assertIn(needle, script)
        refused = (("session-3-has-no-explorer", dict(sessions={1: [a], 2: [b]}, cur_session=3)),
                   ("two-owners-in-one-session", dict(sessions={2: [a, b]}, cur_session=2)),
                   ("session-zero", dict(sessions={0: [a]}, cur_session=0)),
                   ("elevated-as-another-account", dict(sessions={1: [a]}, cur_session=1,
                                                        mine_sid=OsFake.OTHER_SID)))
        for label, kw in refused:
            fake = OsFake(**kw)
            rc, out = arm(self, R, fake, push_only=True)
            self.assertEqual(rc, 1, label)
            self.assertIn("SCHED-PUSH-USER-MISMATCH", out, label)
            self.assertFalse(any("Register-ScheduledTask" in s for s in fake.script()), label)
            if label != "elevated-as-another-account":
                self.assertIn("無法判定當前互動工作階段的擁有者", out, label)
        same_name = OsFake(push_user=OsFake.USER, push_sid=OsFake.OTHER_SID)  # 名稱相同、SID 不同
        rc, out = arm(self, R, same_name, push_only=True)
        self.assertEqual(rc, 1)
        self.assertIn("SCHED-PUSH-USER-MISMATCH", out)
        self.assertFalse(same_name.push_present)  # 回復為未安裝
        spelled = OsFake(owner="TESTDOM" + "\\" + "Tester", push_user="testdom" + "\\" + "TESTER",
                         push_sid=OsFake.SID)  # SID 相同、拼法不同：通過
        self.assertEqual(arm(self, R, spelled, push_only=True)[0], 0)

    def test_AT_749_9_E_4_malformed_identity_strings_never_raise_and_fail_closed(self):
        from lib import apply_lock
        pid, ok_iso = os.getpid(), datetime.now(UTC).isoformat()
        for bad in ("garbage", "", 123, None, ["x"]):
            for created, started in ((bad, ok_iso), (ok_iso, bad), (bad, bad)):
                if created is None and started is not None:
                    continue  # created 缺席是合法的另一條路
                got = runner.process_identity(pid, started, created, window_seconds=100)
                self.assertEqual(got, "unverified", (created, started))
        self.assertIn(runner.process_identity(2 ** 31 - 7, ok_iso, ok_iso, window_seconds=1),
                      ("gone", "unverified"))
        self.assertEqual(runner.process_identity("x", ok_iso, window_seconds=1), "unverified")
        rr = self.rr()  # ①patrolrun 逾牆：不殺、記 RUN-KILL-SKIPPED
        tdir = self.home / "patrol" / "RUN-SI-001"
        tdir.mkdir(parents=True, exist_ok=True)
        started = datetime.now(UTC) - timedelta(hours=6)
        (tdir / "spawn.json").write_text(json.dumps({
            "pid": pid, "started_at": started.isoformat(), "wall_due_at": "也不是時間",
            "process_started_utc": "garbage"}), encoding="utf-8")
        kills: list[int] = []
        ctx = patrol.Ctx(rr.R, datetime.now(UTC), False, patrol.Deps(kill_tree=kills.append),
                         fx.params_dict())
        patrolrun.watch(ctx)
        self.assertEqual(kills, [])
        self.assertIn("code=RUN-KILL-SKIPPED", (self.home / "patrol" / "patrol.log").read_text(
            encoding="utf-8"))
        lock = self.home / "locks" / "bad.lock"  # ②acquire_guarded：視為活著、不回收
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(json.dumps({"pid": pid, "process_started_utc": "garbage",
                                    "acquired_at": ok_iso}), encoding="utf-8")
        old = time.time() - 100000
        os.utime(lock, (old, old))
        alive = lambda info: runner.process_identity(  # noqa: E731
            info.get("pid"), info.get("acquired_at"), info.get("process_started_utc"),
            window_seconds=10) in ("match", "unverified")
        with self.assertRaises(apply_lock.LockBusyError), apply_lock.acquire_guarded(
                lock, 0.3, 10, holder_alive=alive):
            pass
        cur = self.home / "push" / "current.json"  # ③pushguard._running：視為推送中
        cur.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        cur.write_text(json.dumps({"sha": "a" * 40, "pid": pid, "started_at": "壞的",
                                   "wall_due_at": (now + timedelta(minutes=30)).isoformat(),
                                   "process_started_utc": "garbage"}), encoding="utf-8")
        self.assertTrue(pushguard.running(self.home, now, patrolrun._alive))  # noqa: SLF001

    # ---- E-39：trailer／紀錄綁定的判別測試
    def test_AT_749_4_E_26_the_trailer_prop_must_equal_the_event_prop(self):
        rr = self.rr(other_prop=True)
        app = rr.app_id()
        rr.write_touched()
        rr.event("promote", app, post=rr.post())
        other = fx.pid(2)
        # trailer 與紀錄皆寫 B，事件的 prop 是 A
        sha = rr.commit([EVL, *rr.touched], app=app, prop=other)
        res = rr.evaluate()
        self.blocked(res, "PUSH-FOREIGN-COMMITS", sha)

    def test_AT_749_4_E_27_the_last_record_wins_not_the_first(self):
        for label, order, ok in (("first-ok-last-bad", ("good", "bad"), False),
                                 ("first-bad-last-ok", ("bad", "good"), True)):
            with self.subTest(label):
                rr = self.rr()
                p = rr.patrol(record=False)
                rows = {"good": {"sha": p.sha, "app": p.app, "prop": rr.prop},
                        "bad": {"sha": p.sha, "app": p.app, "prop": fx.pid(9)}}
                for key in order:
                    rr.raw_record((json.dumps(rows[key]) + "\n").encode("utf-8"))
                res = rr.evaluate()
                if ok:
                    self.assertTrue(res["ok"], res)
                else:
                    self.blocked(res, "PUSH-RECORD-MISMATCH", p.sha)

    def test_AT_749_4_E_28_a_merge_commit_is_always_foreign(self):
        rr = self.rr()
        fx.git(rr.R, "checkout", "-q", "-b", "side")
        fx.put(rr.R, "side.txt", "側枝\n")
        fx.git(rr.R, "add", "--", "side.txt")
        fx.git(rr.R, "commit", "-q", "-m", "side")
        fx.git(rr.R, "push", "-q", "origin", "side:main")
        fx.git(rr.R, "checkout", "-q", "main")
        p = rr.patrol()
        msg = pushguard.commit_message("promote", rr.prop, p7x.DEC_ID, p.app)  # 合法的兩行 trailer
        fx.git(rr.R, "merge", "-q", "--no-ff", "origin/main", "-m", msg)
        merged = head_of(rr.R)
        rr.record(merged, p.app)  # 紀錄與事件皆合法
        self.assertEqual(len(fx.git(rr.R, "log", "-1", "--format=%P").split()), 2)
        self.blocked(rr.evaluate(), "PUSH-FOREIGN-COMMITS", merged)

    def test_AT_749_4_E_29_trailer_shapes_are_closed_and_never_raise(self):
        app, prop = "APP" + "-SI-123", "PROP" + "-SI-001"
        shapes = {
            "foreign-key": f"chore: x\n\n{APP_T}: {app}\nSigned-off-by: A <a@x>",
            "other-key": f"chore: x\n\n{APP_T}: {app}\nSI-Patrol-Other: {prop}",
            "three-lines": f"chore: x\n\n{APP_T}: {app}\n{PROP_T}: {prop}\nExtra: y",
            "three-same-keys": f"chore: x\n\n{APP_T}: {app}\n{PROP_T}: {prop}\n{APP_T}: {app}",
            "single-paragraph": f"{APP_T}: {app}\n{PROP_T}: {prop}",
            "blank-between": f"chore: x\n\n{APP_T}: {app}\n\n{PROP_T}: {prop}",
            "duplicate-key": f"chore: x\n\n{APP_T}: {app}\n{APP_T}: {app}",
            "one-line": f"chore: x\n\n{APP_T}: {app}"}
        for label, msg in shapes.items():
            self.assertIsNone(pushguard.parse_trailers(msg), label)
        for order in (f"{APP_T}: {app}\n{PROP_T}: {prop}", f"{PROP_T}: {prop}\n{APP_T}: {app}"):
            self.assertEqual(pushguard.parse_trailers(f"chore: x\n\n{order}"), (app, prop))
        for label, make in shapes.items():
            with self.subTest(label):  # 經守門：外來提交，不是 PUSH-GIT-UNAVAILABLE
                rr = self.rr()
                real_app = rr.app_id()
                rr.write_touched()
                rr.event("promote", real_app, post=rr.post())
                msg = make.replace(app, real_app).replace(prop, rr.prop)
                sha = rr.commit([EVL, *rr.touched], app=real_app, message=msg)
                self.blocked(rr.evaluate(), "PUSH-FOREIGN-COMMITS", sha, label)
        rr = self.rr()  # 正向：兩個次序都放行
        for order in (0, 1):
            real_app = rr.app_id()
            rr.write_touched()
            rr.event("promote", real_app, post=rr.post())
            lines = [f"{APP_T}: {real_app}", f"{PROP_T}: {rr.prop}"][::1 if order == 0 else -1]
            rr.commit([EVL, *rr.touched], app=real_app, message="chore: x\n\n" + "\n".join(lines))
        self.assertTrue(rr.evaluate()["ok"])

    # ---- E-40：fail-closed 分支
    def test_AT_749_5_E_8_failures_never_become_a_pass(self):
        rr = self.prr()
        rr.patrol()
        real, calls = Git.run, []

        def count(git_self, *a, **kw):
            calls.append(a)
            return real(git_self, *a, **kw)
        with mock.patch.object(Git, "run", count):
            self.assertTrue(rr.evaluate()["ok"])
        normal = len(calls)

        def failing(match, result):
            def run(git_self, *a, **kw):
                if match(a):
                    return result
                return real(git_self, *a, **kw)
            return run
        bad_rc = subprocess.CompletedProcess([], 128, "", "fatal")
        for label, match, result in (
                ("rev-list-rc", lambda a: "rev-list" in a, bad_rc),
                ("rev-list-timeout", lambda a: "rev-list" in a, None),
                ("rev-list-list-rc", lambda a: "--reverse" in a, bad_rc),  # 只壞「列提交」那一次
                ("config-rc-2", lambda a: a[:1] == ("config",) and "--list" in a,
                 subprocess.CompletedProcess([], 2, "", "x")),
                ("config-none", lambda a: a[:1] == ("config",) and "--list" in a, None)):
            with self.subTest(label), mock.patch.object(Git, "run", failing(match, result)):
                res = rr.evaluate()  # 不拋例外
            self.assertEqual((res["ok"], res["code"]), (False, "PUSH-GIT-UNAVAILABLE"), label)
        seen = []

        def slow(git_self, *a, **kw):  # 第 3 次呼叫後總預算用盡
            seen.append(a)
            if len(seen) == 3:
                time.sleep(0.6)
            return real(git_self, *a, **kw)
        with mock.patch.object(pushguard, "TOTAL_BUDGET", 0.5), mock.patch.object(Git, "run", slow):
            res = rr.evaluate()
        self.assertEqual((res["ok"], res["code"]), (False, "PUSH-GIT-UNAVAILABLE"))
        self.assertEqual(len(seen), 3)  # 其後不再呼叫 git
        self.assertLess(len(seen), normal)

    # ---- E-44：單點斷言
    def test_AT_749_1_E_2_default_off_touches_nothing(self):
        rr = self.rr()
        fx.set_params(rr.R, sched_auto_push=False)
        rr.arm_url(None)  # 夾具記的網址檔不算「推送寫的」
        rr.patrol()
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy()
        with mock.patch.object(patrolpush, "resolve_git", wraps=patrolpush.resolve_git) as rg, \
                mock.patch.object(patrolpush.apply_lock, "acquire_guarded") as lock:
            rc, out = self.go(rr, push, remote_run=ls)
        self.assertEqual((rc, push.calls, ls.calls, rg.call_count, lock.call_count),
            (0, [], [], 0, 0))
        self.assertIn("PUSH-OFF", out)
        self.assertFalse((self.home / "locks" / "push.lock").exists())
        names = sorted(p.name for p in (self.home / "push").iterdir() if p.name != "commits.jsonl")
        self.assertEqual(names, ["tick.json"])

    def test_AT_749_6_E_11_pre_send_checks_each_have_a_witness(self):
        rr = self.prr()
        sha = rr.patrol().sha
        base = self.remote_main(rr)
        blocked = self.home / "push" / "blocked.json"
        blocked.parent.mkdir(parents=True, exist_ok=True)
        blocked.write_text(json.dumps({"code": "PUSH-REMOTE-DRIFT", "head": sha}), encoding="utf-8")
        push = p7x.run_argv_spy()
        ls = p7x.run_argv_spy(out=f"{base}\trefs/heads/main\n")
        self.assertEqual(self.go(rr, push, remote_run=ls)[0], 0)
        self.assertFalse(blocked.exists())  # ①預檢通過後舊的 blocked.json 被刪
        self.new_home()
        rr = self.prr()
        sha = rr.patrol().sha
        push = p7x.run_argv_spy()
        ls = p7x.run_argv_spy(out=f"{self.remote_main(rr)}\trefs/heads/main\n")
        with mock.patch.object(patrolpush, "AFTER_LSREMOTE_HOOK", lambda repo: rr.human()):
            rc, out = self.go(rr, push, remote_run=ls)  # ②ls-remote 之後 HEAD 移動
        self.assertIn("PUSH-HEAD-MOVED", out)
        self.assertEqual(push.calls, [])
        self.new_home()
        rr = self.prr()  # ②b遠端也漂移時 HEAD 移動優先：不寫 blocked.json（排除只靠最後一道復查）
        rr.patrol()
        push, ls = p7x.run_argv_spy(), p7x.run_argv_spy(out="a" * 40 + "\trefs/heads/main\n")
        with mock.patch.object(patrolpush, "AFTER_LSREMOTE_HOOK", lambda repo: rr.human()):
            rc, out = self.go(rr, push, remote_run=ls)
        self.assertIn("PUSH-HEAD-MOVED", out)
        self.assertFalse((self.home / "push" / "blocked.json").exists())
        self.assertEqual(push.calls, [])
        self.new_home()
        rr = self.prr()
        rr.patrol()
        push = p7x.run_argv_spy()
        rc, out = self.go(rr, push,
            remote_run=p7x.run_argv_spy(out="g" * 40 + "\trefs/heads/main\n"))
        self.assertIn("PUSH-REMOTE-DRIFT", out)  # ③sha 欄不是 40 碼十六進位＝視為沒有該分支
        self.assertIn("<空>", out)  # 說明寫「遠端為空」，而不是把那串非十六進位字元當成遠端值
        self.assertNotIn("gggg", out)
        self.assertEqual(push.calls, [])

    def test_AT_749_9_7_runner_notes_are_masked_and_last_line_is_the_last_nonblank(self):
        rr = self.prr()
        sha = rr.patrol().sha
        planted = "tok" + SECRET + "x1y2z3"
        self.go(rr, p7x.run_argv_spy(note=f"job-unavailable:boom token={planted}"))
        note = self.result(sha)["runner_note"]
        self.assertNotIn(planted, note)
        self.assertIn("token=***", note)
        text = "第一行不同\n\n最後一行含 token=" + planted + " 尾巴\n\n"
        got = pushguard.last_line(text)
        self.assertTrue(got.startswith("最後一行含 token=***"), got)
        self.assertNotIn(planted, got)
        self.assertNotIn("第一行", got)
        self.assertEqual(len(pushguard.last_line("x" * 500)), 160)

    def test_AT_749_10_5_commit_records_and_running_state_are_strict(self):
        si = self.home
        for bad in ("abc123", "G" * 40, "A" * 40, "a" * 41):  # ①短 sha／非小寫十六進位：拒收
            with self.assertRaises(OSError, msg=bad):
                patrolreport.record_commit(si, bad, "APP" + "-SI-123", fx.pid(1), NOW)
        self.assertFalse(commits_file(si).exists())
        flags: list[int] = []
        real_open = os.open

        def rec(path, fl, *a, **kw):
            flags.append(fl)
            return real_open(path, fl, *a, **kw)
        with mock.patch.object(patrolreport.os, "open", rec):
            patrolreport.record_commit(si, "a" * 40, "APP" + "-SI-123", fx.pid(1), NOW)
        self.assertTrue(flags and flags[-1] & os.O_APPEND)  # 以 O_APPEND 單行追加
        self.assertEqual(len(commits_file(si).read_text(encoding="utf-8").splitlines()), 1)
        prm = {**fx.params_dict(), "sched_auto_push": True}
        cur = {"sha": "b" * 40, "pid": os.getpid(), "started_at": NOW.isoformat()}
        folder = si / "push"
        folder.mkdir(parents=True, exist_ok=True)
        guard = {"ahead": 1, "head": "b" * 40, "code": None, "detail": None}

        def state(due_off):
            (folder / "current.json").write_text(json.dumps(
                {**cur, "wall_due_at": (NOW + timedelta(minutes=due_off)).isoformat()}),
                encoding="utf-8")
            return patrolreport.push_block(si, prm, NOW, True, guard, lambda *a: True)["state"]
        self.assertEqual(state(30), "running")  # ②牆鐘未到且存活
        self.assertNotEqual(state(-1), "running")  # 牆鐘已到
        (folder / "current.json").unlink()
        idle = patrolreport.push_block(si, prm, NOW, True, {**guard, "ahead": 0}, lambda *a: False)
        self.assertEqual((idle["state"], idle["code"]), ("idle", "PUSH-NOT-AHEAD"))  # ③不是 blocked

    def test_AT_790_6_1_constants_and_predicates_have_a_single_home(self):
        trees = {p.name: ast.parse(p.read_text(encoding="utf-8")) for p in PKG.glob("*.py")}

        def defined(name, kinds=(ast.Assign, ast.AnnAssign, ast.FunctionDef)):
            out = []
            for fname, tree in trees.items():
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == name:
                        out.append(fname)
                    elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                            out.append(fname)
            return out
        for name in ("_KINDS", "_LEDGERS", "_CELL_RE"):  # 本套件的推送面：pushcontent 一家
            homes = set(defined(name))
            self.assertIn("pushcontent.py", homes, name)
            self.assertFalse(homes & {"pushguard.py", "patrolpush.py", "patrolreport.py"}, name)
        for name in ("NEVER_RETRY", "RETRYABLE", "BLOCK_CODES"):
            self.assertEqual(defined(name), ["pushguard.py"], name)
        self.assertEqual(defined("SECRET_PATTERNS"), ["git.py"])
        self.assertIn("git.py", defined("ENV_ALLOW"))  # patrolrun 另有自己的子行程環境表（非 git）
        self.assertEqual(defined("env_for_git"), ["git.py"])
        self.assertEqual([f for f in defined("mask") if f != "runner.py"], ["git.py"])
        for name in ("mode_verdict", "content_problems", "ledger_rule_problems"):
            self.assertEqual(defined(name), ["pushcontent.py"], name)
        guard = {tuple(getattr(pushguard, n)) for n in ("NEVER_RETRY", "RETRYABLE", "BLOCK_CODES")}
        # 這兩檔沒有同值的 tuple／set／frozenset 定義
        for fname in ("patrolreport.py", "patrolpush.py"):
            for node in ast.walk(trees[fname]):
                if isinstance(node, (ast.Tuple, ast.Set)) and node.elts and all(
                        isinstance(e, ast.Constant) and isinstance(e.value, str)
                        for e in node.elts):
                    self.assertNotIn(tuple(e.value for e in node.elts), guard, fname)


class TestSecCommitSide(ChainTestCase):
    """`_commit` 與守門共用同一個內容約束函式（AC-SI-49-2；受測 tools/lib/selfimproving/
    pushcontent.py）。"""

    def test_AT_749_2_E_3_commit_refuses_content_violations_before_committing(self):
        samples = secret_samples()
        cases = {
            "bad-file-name": lambda R, p: fx.put(R, f"{PROPS}/{p}/x.txt", "a\n"),
            "too-big": lambda R, p: fx.put(R, f"{PROPS}/{p}/r9.patch",
                                           "a" * (pushcontent.PROPOSAL_FILE_MAX_BYTES + 1)),
            "bad-event-line": lambda R, p: fx.put(R, EVL, fx.read(R, EVL) + "這不是 JSON\n"),
            "secret": lambda R, p: fx.put(R, f"{PROPS}/{p}/r9.md", samples["github-token"] + "\n")}
        if sys.platform != "win32":  # 符號連結：Windows 預設沒有建立權限
            cases["symlink"] = lambda R, p: os.symlink("r1.md", R / PROPS / p / "r9.md")
        for label, mutate in cases.items():
            with self.subTest(label):
                self.new_home()
                R, prop, ctx = self.promoted_tree()
                mutate(R, prop)
                head0 = self.head(R)
                patrolrun._commit(ctx, prop, "promote")  # noqa: SLF001
                self.assertEqual(self.head(R), head0)
                self.assertFalse(commits_file(self.home).exists())
                hits = [ln for ln in self.logs() if "code=COMMIT-LEDGER-RULE" in ln]
                self.assertEqual(len(hits), 1)
                self.assertEqual(ctx.notes[prop][0], "COMMIT-LEDGER-RULE")
                self.assertNotIn(samples["github-token"], ctx.notes[prop][1])  # 描述不含值
        calls = {fn.name for p in ("pushguard", "pushcontent")
                 for fn in ast.walk(ast.parse((PKG / f"{p}.py").read_text(encoding="utf-8")))
                 if isinstance(fn, ast.FunctionDef) for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and ast.unparse(c.func) == "content_problems"}
        self.assertEqual(calls, {"rule_problem", "judge"})  # 全套件單一函式，沒有第二份

    # ---- E-41：提交端符號連結（真變體與替身變體都跑）
    def test_AT_749_4_E_30_commit_side_refuses_links_on_every_platform(self):
        ran = []

        def attempt(label, mutate, expect_mode):
            self.new_home()
            R, prop, ctx = self.promoted_tree()
            mutate(R, prop)
            head0 = self.head(R)
            patrolrun._commit(ctx, prop, "promote")  # noqa: SLF001
            self.assertEqual(self.head(R), head0, label)
            self.assertEqual(ctx.notes[prop][0], "COMMIT-LEDGER-RULE", label)
            self.assertIn(expect_mode, ctx.notes[prop][1], label)
            ran.append(label)
        real_lstat = os.lstat

        def real_link(R, prop):
            (R / PROPS / prop / "r9.md").symlink_to("r1.md")
        try:
            tmp = fx.new_dir("symprobe")
            tmp.mkdir(parents=True, exist_ok=True)
            (tmp / "l").symlink_to("x")
            (tmp / "l").unlink()
            can_link = True
        except (OSError, NotImplementedError):
            can_link = False  # 建立失敗（Windows 無權限）：不略過，改走替身變體
        if can_link:
            attempt("real-symlink", real_link, "120000")

        def fake_link(R, prop):
            fx.put(R, f"{PROPS}/{prop}/r9.md", "x\n")
            self.enterContext(mock.patch.object(pushcontent, "_lstat", lambda p: (
                types.SimpleNamespace(st_mode=0o120777)
                    if str(p).endswith("r9.md") else real_lstat(p))))
        attempt("fake-S_IFLNK", fake_link, "120000")

        def fake_reparse(R, prop):
            fx.put(R, f"{PROPS}/{prop}/r9.md", "x\n")
            self.enterContext(mock.patch.object(pushcontent, "_lstat", lambda p: (
                types.SimpleNamespace(st_mode=0o100644, st_file_attributes=0x400)
                if str(p).endswith("r9.md") else real_lstat(p))))
        attempt("fake-reparse-point", fake_reparse, "120000")
        self.assertIn("fake-S_IFLNK", ran)
        self.assertIn("fake-reparse-point", ran)


if __name__ == "__main__":
    sys.exit(unittest.main())
