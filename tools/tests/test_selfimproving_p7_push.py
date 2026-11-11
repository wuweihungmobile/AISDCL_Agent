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
from datetime import datetime, timedelta
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
    pushguard,
    runner,
    sched,
    schedarm,
    unattended,
)
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

    def rr(self, **kw) -> p7x.PushRepo:
        return p7x.push_repo(self, **kw)

    DETAIL_SHAPE = {  # TCS-P7 E-9：`{detail}`＝sha8＋「卡在哪」的片段（其餘碼只有 sha8）
        "PUSH-APP-KIND-INVALID": r"APP-SI-\d+ app\.(sandbox|verify)",
        "PUSH-APP-REUSED": r"APP-SI-\d+",
        "PUSH-PATH-OUTSIDE": r"\S.*",
        "PUSH-LEDGER-RULE": r"\S.*",
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
                         (True, 45, 3, 360))
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
            pj.read_bytes().replace(b'"sched_auto_push": true', b'"sched_auto_push": false'))
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
            fx.line([fx.obs_id(n), "2026-11-11 12:00", f"追加列 {n}", "症狀", "x:1", "doc",
                               "P3", "open", "面=文件;來源=代理;回報者=SA"]) for n in (21, 22))
        obs_edit(R, lambda ls: [set_cell(ln, 7, "fixed@abcdef0") if ln.startswith(
            f"| {fx.obs_id(1)} |") else ln for ln in ls[:-1]] + [new1, new2, ""])
        fx.put(R, f"{PROPS}/{prop}/verify2.json", "{}\n")
        fx.append_events(R, [fx.card_ev(int(prop[-3:]))])
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
        self.assertEqual(defs, ["pushguard.py"])
        for name in ("_obs_problem",):
            self.assertEqual([p.name for p in PKG.glob("*.py")
                              if f"def {name}" in p.read_text(encoding="utf-8")], ["pushguard.py"])
        tree = ast.parse((PKG / "pushguard.py").read_text(encoding="utf-8"))
        callers = {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
                   for c in ast.walk(fn) if isinstance(c, ast.Call)
                   and ast.unparse(c.func) == "ledger_rule_problems"}
        # 提交側 `rule_problem`、守門側 `judge`
        self.assertEqual(callers, {"rule_problem", "judge"})

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
        n1, n2 = (fx.line([fx.obs_id(n), "2026-11-11 12:00", f"追加列 {n}", "症狀", "x:1", "doc",
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
        self.assertTrue(res["ok"], res)  # 引號化路徑若被誤判就會 PATH-OUTSIDE
        real = Git.run

        def broken(git_self, *args, **kw):
            if "diff-tree" in args:
                return subprocess.CompletedProcess(args, 128, "", "fatal")
            return real(git_self, *args, **kw)
        with mock.patch.object(Git, "run", broken):
            res2 = rr.evaluate()
        self.assertEqual((res2["ok"], res2["code"]), (False, "PUSH-GIT-UNAVAILABLE"))

        def no_show(git_self, *args, **kw):
            if args[:1] == ("show",) and ":" in args[-1]:
                return subprocess.CompletedProcess(args, 128, "", "fatal")
            return real(git_self, *args, **kw)
        with mock.patch.object(Git, "run", no_show):
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
        self.assertEqual(rq.evaluate(alive=lambda pid, started: True)["code"], "PUSH-RUNNING")
        self.assertEqual(rq.evaluate(alive=lambda pid, started: False)["ok"], True)  # 行程已死
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
        got = patrolreport.push_inputs(ctx, lambda pid, started: False)
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
        self.assertEqual(call["argv"], ["git", "-C", str(rr.R), "push", "origin",
                                        f"{sha}:refs/heads/main"])
        for bad in ("--force", "-f", "--force-with-lease", "--no-verify", "--delete", "HEAD"):
            self.assertNotIn(bad, call["argv"])
        env = call["env"]
        for name in (*patrolpush.DROP_ENV, "AUTOSDD_SI_AUDIT_KEY", "AUTOSDD_UNATTENDED",
                     "AUTOSDD_SI_PATROL_RUN"):
            self.assertNotIn(name, env)
        self.assertEqual((env["GIT_TERMINAL_PROMPT"], env["GCM_INTERACTIVE"]), ("0", "never"))
        self.assertEqual(env["KEEP_ME"], "1")
        for name in ("PATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT"):
            if name in os.environ:
                self.assertEqual(env[name], os.environ[name], name)
        gitenv = patrolpush.push_env({"GIT_DIR": "a", "GIT_WORK_TREE": "b", "GIT_INDEX_FILE": "c",
                                      "PATH": "p", "AUTOSDD_UNATTENDED": "1"})
        self.assertEqual(sorted(gitenv), ["GCM_INTERACTIVE", "GIT_TERMINAL_PROMPT", "PATH"])
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
        with mock.patch.object(patrolpush, "AFTER_GUARD_HOOK",
                               lambda repo: late.append(rr2.human())):
            rc, out = patrolpush.run(rr2.R, now=NOW)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.remote_main(rr2), sha2)  # 只前進到守門當下的 sha
        self.assertNotEqual(self.remote_main(rr2), head_of(rr2.R))
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
        guard = patrolreport.push_inputs(ctx, lambda pid, started: False)
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
        for patched, want in ((None, "job-terminated"), ((None, "boom"), "taskkill-fallback:boom")):
            t1 = time.monotonic()
            with (mock.patch.object(runner, "_job_open", return_value=patched) if patched
                  else contextlib.nullcontext()):
                res = runner.run_argv(nap, env=dict(os.environ), timeout=1)
            self.assertTrue(res.timed_out)
            self.assertLess(time.monotonic() - t1, 1 + runner.KILL_GRACE_SECONDS)
            self.assertEqual(res.note, want if sys.platform == "win32" else "")  # 可查字樣、不靜默
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
        t0 = time.monotonic()
        try:
            with mock.patch.object(patrolpush, "WALL_SECONDS_OVERRIDE", wall):
                rc, out = patrolpush.run(rr2.R, now=NOW)
        finally:
            elapsed = time.monotonic() - t0
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
        self.assertLess(elapsed, wall + grace, "run_argv 沒在逾時＋寬限內返回")  # (ii)
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
        rc, out = self.go(rr, spy, alive=lambda pid, started: True)  # 存活且未逾牆
        self.assertEqual((rc, spy.calls), (0, []), out)
        self.assertIn("PUSH-RUNNING", out)
        residue()
        self.assertEqual(self.go(rr, spy, alive=lambda pid, started: False)[0], 0)  # 行程已死
        self.assertEqual(len(spy.calls), 1)
        self.assertFalse(cur.exists())  # 覆寫後一律刪除
        self.put_result(sha, "PUSH-FAILED", 1, NOW - timedelta(days=1))
        residue(wall_min=30)
        later = NOW + timedelta(hours=2)  # pid 存活但已逾 wall_due_at：視為不在跑，且不殺他人行程
        self.assertTrue(pushguard.evaluate(rr.R, prm, self.home, later,
                                           alive=lambda pid, started: True)["ok"])
        cur.write_text("{ 損壞", encoding="utf-8")
        self.assertTrue(pushguard.evaluate(rr.R, prm, self.home, NOW,
                                           alive=lambda pid, started: True)["ok"])
        self.assertEqual(self.go(rr, spy, alive=lambda pid, started: True)[0], 0)

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
        guard = patrolreport.push_inputs(ctx, lambda pid, started: False)
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
              tick=None, ok_result=None, alive=False, now=NOW, params=None, guard=True) -> dict:
        folder = self.home / "push"
        shutil.rmtree(folder, ignore_errors=True)
        (folder / "results").mkdir(parents=True)
        for name, obj in (("current.json", cur), ("last_error.json", err), ("tick.json", tick)):
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
                   "diff-tree", "symbolic-ref", "for-each-ref"}
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
                         ["commits.jsonl"])  # 只有夾具造提交時留下的紀錄；tick.json 也沒寫

    def test_AT_749_11_2_rc_contract(self):
        rr = self.prr()
        sha = rr.patrol().sha
        spy = p7x.run_argv_spy()
        rc, out = self.go(rr, spy, dry_run=True)
        self.assertEqual((rc, spy.calls), (0, []), out)
        self.assertEqual(sorted(p.name for p in (self.home / "push").iterdir()), ["commits.jsonl"])
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
        spy = p7x.run_argv_spy()
        with mock.patch.object(runner, "run_argv", spy):
            rc, out, err = self.M(rr.R, "push-run", "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        self.assertEqual(list(obj), ["ok", "kind", "code", "sha", "ahead", "attempts"])
        self.assertEqual((obj["ok"], obj["kind"], obj["code"], obj["attempts"]),
                         (True, "push-run", "PUSH-OK", 1))
        self.assertEqual(len(spy.calls), 1)  # 入口走呼叫當下的 runner.run_argv
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

    def __init__(self, *, patrol_rc=0, patrol_err="", push_rc=0, push_err="", push_user=None,
                 push_next="2026-11-11T12:15:00+08:00", stuck_push=False, push_present=False,
                 patrol_present=True) -> None:
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
            if "New-ScheduledTaskAction" in text:
                rc, err = self.push_rc, self.push_err
                self.push_present = rc == 0
            elif text.startswith("Unregister-ScheduledTask -TaskName 'AutoSDD_SI_Push'"):
                self.push_present = self.push_present and self.stuck_push
            elif text.startswith("Unregister-ScheduledTask"):
                self.patrol_present = False
            elif "TaskName 'AutoSDD_SI_Push'" in text:
                out = (f"NEXT={self.push_next}\nUSER={self.push_user}\n" if self.push_present
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

    def win(self):
        return mock.patch.object(schedarm.sys, "platform", "win32")

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
        self.assertIn("SCHED-PUSH-TASK-FAILED", text)  # UserId 與註冊者不同
        fake = OsFake()
        rc, text = self.arm(self.repo(push=False), fake, push_only=True)
        self.assertEqual((rc, fake.calls), (1, []))
        self.assertIn("SCHED-PUSH-OFF", text)

    def test_AT_749_12_4_macos_writes_a_launchd_agent_and_keeps_windows_literals_out(self):
        R = self.repo()
        plist_dir = fx.new_dir("plist")
        fake = OsFake()
        with mock.patch.object(schedarm.sys, "platform", "darwin"):
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
            self.assertEqual(spy.calls[0]["env"]["GITHUB_TOKEN"], planted["GITHUB_TOKEN"])
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
        self.assertEqual(len(calls), 4)

    def test_AT_749_13_E_1_the_audit_key_never_reaches_git(self):
        env = patrolpush.push_env({"AUTOSDD_SI_AUDIT_KEY": "k", "X_AUDIT_KEY_2": "k2",
                                   "GIT_ASKPASS": "a", "SSH_ASKPASS": "b", "GITHUB_TOKEN": "t"})
        self.assertFalse([k for k in env if "AUDIT_KEY" in k])
        self.assertEqual((env["GIT_ASKPASS"], env["SSH_ASKPASS"], env["GITHUB_TOKEN"]),
                         ("a", "b", "t"))


if __name__ == "__main__":
    sys.exit(unittest.main())
