"""tools/lib/suite_shard.py — `tools/run_root_unittests.py` 的跨機分片（DEF-200-593）。

WHY：windows-compat-ci 的 tools/tests 步驟在 4 核 runner 上要 45 分鐘以上（總工作量約
10,294 s、多 CPU 已吃滿），整支 workflow 逼近 `timeout-minutes: 60`。單機再怎麼平行都吃不到
多台 runner 的核數，故把「派工單位」切成 N 片、各片跑在各自的 runner 上。**不減任何測試、
不放寬任何門檻**：全集級的守門（`MIN_TESTS`、收集面盤存／缺口、discovery 佔位測試）每片都
對全集做；全集級的 skip 判準（天花板、M6 id 集合、豁免表 stale）在分片下無法成立，改由
`tools/shard_census.py` 對各片留下的紀錄**合併後**判（CI 的彙總 job；本機未分片時仍照舊在
runner 內判）。

介面（環境變數，不加旗標：`run_root_unittests.py` 的 CLI 契約是零旗標）：
  AUTOSDD_TEST_SHARD=i/N      只跑第 i 片（1 起算、共 N 片）；未設＝現行行為逐字不變。
  AUTOSDD_TEST_SHARD_OUT=dir  分片模式下，該片跑完把紀錄寫成 `shard-<i>-of-<N>.json`。

切分必須**確定性**（各片在不同機器上各自算、結果必須完全一致，否則聯集≠全集）：
  ① 只對**靜態派工單位**切（`dispatch_granularity.suite_dispatch_units`：人工白名單，
     與計時快取、worker 數無關）；片內再各自做自動細分（只會把單位拆成子單位，不跨片）。
  ② 權重只用 git 追蹤的種子檔，**不讀本機活體快取**（各機活體快取不同 ⇒ 切分不一致）。
  ③ LPT（權重遞減、同權重以單位鍵字典序破平手），貪婪塞進目前總量最小的片（同量取編號小者）；
     單位權重在單位內（子鍵加總、按比例分攤、平均值）以浮點算完後立刻取整數毫秒，跨單位的
     負載加總一律用整數，避免跨單位浮點加總順序造成跨平台差異。
  ④ 種子沒有的單位：先看子鍵（類別級鍵）加總、再看母模組鍵按測試數比例分攤、最後用種子
     自己的「秒／測試」平均乘測試數（種子全空則 1.0）——全部由（單位集合、種子檔）決定。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from pathlib import Path

import dispatch_granularity
import parallel_timing_cache

ENV = "AUTOSDD_TEST_SHARD"
ENV_OUT = "AUTOSDD_TEST_SHARD_OUT"
_SPEC_RE = re.compile(r"([1-9][0-9]*)/([1-9][0-9]*)")
#: 本次 `restrict()` 的結果（供 `record()` 寫紀錄）；`None`＝未分片或不是真實樹。
_LAST: dict | None = None


def parse(raw: str | None) -> tuple[int, int] | None:
    """`"i/N"` → `(i, N)`；未設或空字串 → `None`（＝不分片）；其餘格式／越界一律
    `ValueError`（fail-loud：寫錯的分片參數若靜默退回「全跑」，三片各跑全集只是浪費，
    但若退回「不跑」就是假綠，故兩個方向都不准默默處理）。"""
    if raw is None or raw == "":
        return None
    m = _SPEC_RE.fullmatch(raw)
    if m is None or int(m.group(1)) > int(m.group(2)):
        raise ValueError(
            f"{ENV}={raw!r} 格式錯誤：須為 i/N（1 <= i <= N，例如 2/3）")
    return int(m.group(1)), int(m.group(2))


def is_sharded() -> bool:
    """本行程目前是否處於「真實樹且分片中」（`restrict()` 已落 `_LAST`）。"""
    return _LAST is not None


def spec_problem() -> bool:
    """`main()` 的早退判準：分片參數格式錯誤 → 印 ❌ 並回 True（呼叫端 `_bail`）。"""
    try:
        parse(os.environ.get(ENV))
    except ValueError as exc:
        import sys
        print(f"❌ {exc}", file=sys.stderr)
        return True
    return False


def _weights(units: dict[str, int], hints: dict[str, float]) -> dict[str, int]:
    """單位 → 權重（整數毫秒）；見檔頭 ④。"""
    known = [k for k in units if k in hints]
    n_known = sum(units[k] for k in known)
    mean = (sum(hints[k] for k in known) / n_known) if n_known else 1.0
    module_total: dict[str, int] = {}
    for k, n in units.items():
        module_total[k.split(".", 1)[0]] = module_total.get(k.split(".", 1)[0], 0) + n
    out: dict[str, int] = {}
    for k, n in units.items():
        if k in hints:
            sec = hints[k]
        else:
            kids = [h for h in hints if h.startswith(k + ".")]
            minimal = [h for h in kids if not any(h.startswith(o + ".") for o in kids)]
            mod = k.split(".", 1)[0]
            if minimal:
                sec = sum(hints[h] for h in minimal)
            elif mod in hints and mod != k:
                sec = hints[mod] * n / module_total[mod]
            else:
                sec = mean * n
        out[k] = max(1, round(sec * 1000))
    return out


def plan(units: dict[str, int], n: int, hints: dict[str, float] | None = None) -> dict[str, int]:
    """單位 → 片號（1 起算）；純函式，輸入相同則輸出相同。`hints=None`＝讀種子檔。"""
    if hints is None:
        hints = parallel_timing_cache.read_json(parallel_timing_cache.SEED_PATH)
    weight = _weights(units, hints)
    load = [0] * n
    out: dict[str, int] = {}
    for key in sorted(units, key=lambda k: (-weight[k], k)):
        idx = min(range(n), key=lambda s: (load[s], s))
        load[idx] += weight[key]
        out[key] = idx + 1
    return out


def plan_digest(assignment: dict[str, int]) -> str:
    blob = "\n".join(f"{k}\t{v}" for k, v in sorted(assignment.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    out: list[unittest.TestCase] = []
    for item in suite:
        out.extend(_flatten(item) if isinstance(item, unittest.TestSuite) else [item])
    return out


def restrict(
    suite: unittest.TestSuite, start_dir: Path, real_dir: Path,
) -> tuple[unittest.TestSuite, int]:
    """`run_with_floor` 的接線點：回 `(本片的 suite, 本片應跑測試數)`。

    未設 `AUTOSDD_TEST_SHARD` 或 `start_dir` 不是真實 `tools/tests`（單元測試餵的合成樹）
    ⇒ 原 suite 與其全數測試數，行為與修前逐字相同。分片模式下回的 suite 只含本片的測試，
    之後的自動細分、`known_ids` 以外的所有執行端邏輯都只看到本片（全集級守門須在呼叫本函式
    **之前**做完，`run_with_floor` 的順序即如此）。"""
    global _LAST
    _LAST = None
    tests = _flatten(suite)
    spec = parse(os.environ.get(ENV))
    if spec is None or start_dir.resolve() != real_dir.resolve():
        return suite, len(tests)
    idx, total = spec
    units = dispatch_granularity.suite_dispatch_units(tests)
    assignment = plan(units, total)
    mine = [t for t in tests if assignment[dispatch_granularity.dispatch_key(t)] == idx]
    if not mine:
        raise ValueError(f"{ENV}={idx}/{total}：本片沒有任何測試（分片數超過派工單位數？）")
    _LAST = {"shard": [idx, total], "plan_sha": plan_digest(assignment),
             "planned_ids": sorted(t.id() for t in mine)}
    print(f"[suite_shard] 本片 {idx}/{total}：{len(mine)}／{len(tests)} 支測試、"
          f"{sum(1 for v in assignment.values() if v == idx)}／{len(units)} 個派工單位"
          f"（plan_sha={_LAST['plan_sha']}）")
    return unittest.TestSuite(mine), len(mine)


def record(ran: int, result: unittest.TestResult) -> int:
    """跑完後呼叫；分片模式且設了 `AUTOSDD_TEST_SHARD_OUT` 時落該片紀錄（供彙總判準）。
    原樣回傳 `ran`，讓呼叫端可直接嵌在 `report_execution_gap(...)` 的參數位。"""
    out = os.environ.get(ENV_OUT)
    if _LAST is not None and out:
        import skip_runtime_report
        body = dict(_LAST, tests_run=result.testsRun,
                    skipped=[list(s) for s in skip_runtime_report.all_skips(result)])
        path = Path(out) / f"shard-{_LAST['shard'][0]}-of-{_LAST['shard'][1]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        print(f"[suite_shard] 分片紀錄已落檔：{path}")
    return ran


def judge(fn, empty, *args, **kwargs):
    """分片模式下**無法成立**的全集級判準（skip 天花板、M6 id 集合、豁免表 stale）：
    不分片 ⇒ 照舊呼叫 `fn`；分片 ⇒ 只印一行說明並回 `empty`（判準改由彙總 job 對合併後
    的紀錄判，見 `tools/shard_census.py`）。只有「真實樹且分片中」才延後，合成樹照判。"""
    if _LAST is None:
        return fn(*args, **kwargs)
    print(f"[suite_shard] {getattr(fn, '__name__', fn)}：全集級判準，分片模式下延後到彙總步驟"
          "（tools/shard_census.py）")
    return empty


def merge_records(directory: Path, tests: list[unittest.TestCase]):
    """彙總 job 用：讀 `directory` 下全部分片紀錄 → `(合併 result, problems)`。

    problems 非空 ⇒ 呼叫端必須 rc=1：缺片、片數不一致、切分摘要與本機重算不符、各片計畫
    測試集合有交集、或聯集≠全集（＝分片機制本身壞了，這是它存在的**前提**，不是附帶檢查）。

    前提（F4）：呼叫端的 discovery 必須與各片**同條件**（同一份 checkout 深度、同一組第三方
    相依）；`tests` 若因環境而異，重算的摘要與全集 id 就與各片不同 ⇒ 假紅（不是假綠）。CI 彙總
    job 的對齊由 test_suite_shard.py::CensusJobMatchesShardCollectionConditionsTest 機械鎖住。"""
    import parallel_shard
    recs = [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(Path(directory).glob("shard-*-of-*.json"))]
    problems: list[str] = []
    if not recs:
        return None, [f"{directory} 沒有任何分片紀錄（shard-*-of-*.json）"]
    total = recs[0]["shard"][1]
    got = sorted(r["shard"][0] for r in recs)
    if any(r["shard"][1] != total for r in recs) or got != list(range(1, total + 1)):
        problems.append(f"分片紀錄不完整或 N 不一致：預期 1..{total}，實得 {got}")
    units = dispatch_granularity.suite_dispatch_units(tests)
    sha = plan_digest(plan(units, total))
    for r in recs:
        if r["plan_sha"] != sha:
            problems.append(f"片 {r['shard']} 的切分摘要 {r['plan_sha']} ≠ 本機重算 {sha}"
                            "（兩邊看到的測試集合或種子檔不同）")
    seen: dict[str, int] = {}
    for r in recs:
        for tid in r["planned_ids"]:
            if tid in seen:
                problems.append(f"{tid} 同時屬於片 {seen[tid]} 與片 {r['shard'][0]}")
            seen[tid] = r["shard"][0]
    full = {t.id() for t in tests}
    if set(seen) != full:
        missing, extra = full - set(seen), set(seen) - full
        problems.append(f"各片聯集 ≠ 全集：缺 {len(missing)} 支、多 {len(extra)} 支"
                        f"（例：{sorted(missing)[:3]}）")
    for r in recs:
        # 每片「計畫跑的」與「實際跑的」必須對上（DEF-200-593 P2-2）：分片 runner 自己的
        # `report_execution_gap` 已判一次，這裡是不依賴它的第二道——拿掉那個呼叫，census 仍紅。
        # 與 runner 同一條規則：差額必須能由 class／module 層 fixture 條目（`setUpClass (…)`／
        # `setUpModule (…)`，`_ErrorHolder.id()` 的描述字串）歸因，否則整類測試靜默沒跑。
        gap = len(r["planned_ids"]) - r["tests_run"]
        fixture_lvl = any(str(i).startswith(("setUpClass (", "setUpModule ("))
                          for i, _why in r["skipped"])
        if gap < 0 or (gap > 0 and not fixture_lvl):
            problems.append(f"片 {r['shard']} 計畫 {len(r['planned_ids'])} 支、實跑 "
                            f"{r['tests_run']} 支，差額 {gap} 無 fixture 層條目可歸因")
    merged = parallel_shard._MergedResult()
    for r in recs:
        merged.testsRun += r["tests_run"]
        merged.skipped += [(parallel_shard._FixtureStub(i), why) for i, why in r["skipped"]]
    return merged, problems
