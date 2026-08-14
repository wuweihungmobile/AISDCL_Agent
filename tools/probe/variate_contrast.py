#!/usr/bin/env python3
"""落款逐欄變因對照器：**這個欄位是不是常數？它區不區分得開兩組？**

WHY 這支檔存在（R89 `DEF-200-123` 的另一半）
------------------------------------------
事故：13 個 subagent 死於 `You've hit your monthly spend limit`，而主控把**錯誤訊息的
字面**當成根因，宣稱保險池（`spend`／`extra_usage`）撞頂擋住了 agent。掌舵者一句話戳破：
那個池**本來就滿**——`~/.autosdd/traces/quota_burn.jsonl` 逐列實證它連續 15 列都是 100.0
⇒ **常數，數學上不可能是變因**。真變因是訂閱窗（`five_hour` 0↔84 反覆、`seven_day`
單調 0→86）。整件事的證據**當時就躺在磁碟上**，只是沒有人花那 10 秒去看。

配套的攔截器（`.claude/hooks/check_claim_provenance.py::error_literal_mechanism_hits`）
治的是**形態**（把機器的話當成自己的結論）；本檔治的是**內容**（那個量到底變了沒）。
兩者刻意分工：普查實測「常數／變因」這條軸在**散文平面**上做不出鑑別力（判準無從知道
句子裡的識別字是不是被當成原因，實測精確率 33%／0%），但在**落款平面**上它是精確的
——欄位與值都是結構化的，不必猜主詞。⇒ 那一半不做成警報，做成這支「查證比宣稱便宜」
的工具，並由攔截器的訊息指著它。

用法
----
    python tools/probe/variate_contrast.py ~/.autosdd/traces/quota_burn.jsonl
    python tools/probe/variate_contrast.py <落款.jsonl> --split-at 2026-08-13T22:29
    python tools/probe/variate_contrast.py <落款.jsonl> --split-at <ts> --key ts

`--split-at` 把列切成「之前／之後」兩組（＝成功組／失敗組的近似），逐欄印出兩組各自的
值集合，並標記 **DISCRIMINATES**（兩組值域不相交＝這個欄位真的區分得開兩組，是變因候選）
或 **CONSTANT**（全表只有一個值＝不可能是任何事情的變因）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def flatten(obj: object, prefix: str = "") -> dict:
    """巢狀 dict 攤平成 `a.b.c` → 純量。落款慣例是巢狀的（`pct.five_hour`）。"""
    flat: dict = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            flat.update(flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    elif prefix:
        flat[prefix] = obj
    return flat


def read_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue  # 落款是邊寫邊讀的，尾列半截是常態
            if isinstance(record, dict):
                rows.append(flatten(record))
    return rows


def contrast(rows: list[dict], split_at: str | None, key: str) -> list[dict]:
    """逐欄的變因判定。回傳可直接列印／序列化的 dict 列。"""
    fields = sorted({name for row in rows for name in row})
    report = []
    for name in fields:
        seen = [row[name] for row in rows if name in row]
        distinct = sorted({repr(v) for v in seen})
        entry = {"field": name, "n": len(seen), "distinct": len(distinct),
                 "values": distinct[:6],
                 "verdict": "CONSTANT" if len(distinct) == 1 else "varies"}
        if split_at:
            before = {repr(r[name]) for r in rows
                      if name in r and str(r.get(key, "")) < split_at}
            after = {repr(r[name]) for r in rows
                     if name in r and str(r.get(key, "")) >= split_at}
            entry["before"] = sorted(before)[:4]
            entry["after"] = sorted(after)[:4]
            # 🔴 兩組**都非空**才談得上「區分得開」——有一組是空的時候值域必然不相交，
            # 那是缺資料，不是鑑別力。少了這個前提會把每一個只出現在單邊的欄位都
            # 誤報成變因候選，而那正是本檔要防的那種便宜結論。
            if before and after and not (before & after):
                entry["verdict"] = "DISCRIMINATES"
            elif len(distinct) == 1:
                entry["verdict"] = "CONSTANT"
        report.append(entry)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", help="JSONL 落款路徑")
    parser.add_argument("--split-at", help="切成兩組的門檻值（與 --key 欄位做字串比較）")
    parser.add_argument("--key", default="ts", help="切組所依據的欄位（預設 ts）")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 而非表格")
    args = parser.parse_args(argv)

    path = Path(args.trace).expanduser()
    if not path.is_file():
        print(f"落款不存在：{path}", file=sys.stderr)
        return 2
    rows = read_rows(path)
    if not rows:
        print(f"落款沒有可解析的列：{path}", file=sys.stderr)
        return 2
    report = contrast(rows, args.split_at, args.key)
    if args.json:
        print(json.dumps({"trace": str(path), "rows": len(rows), "fields": report},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"落款 {path}｜{len(rows)} 列"
          + (f"｜切點 {args.key} >= {args.split_at}" if args.split_at else ""))
    print(f"{'欄位':<28}{'n':>5}{'相異':>5}  判定")
    for entry in report:
        print(f"{entry['field']:<28}{entry['n']:>5}{entry['distinct']:>5}  "
              f"{entry['verdict']}")
        if entry["verdict"] == "CONSTANT":
            print(f"{'':<28}     └ 值恆為 {entry['values'][0]}"
                  f" ⇒ **不可能是任何事情的變因**")
        elif args.split_at and entry["verdict"] == "DISCRIMINATES":
            print(f"{'':<28}     └ 前 {entry['before']} ／ 後 {entry['after']}"
                  f" ⇒ 變因候選")
    print("\n🔴 CONSTANT 的欄位不必再辯論——一個沒有變過的量解釋不了任何變化。"
          "\n   先看 DISCRIMINATES 那幾欄，那才是兩組真正的差異所在。")
    return 0


if __name__ == "__main__":
    # UTF-8 stdio 保護：本檔的輸出全是中文，非 UTF-8 locale 下 stdout 會直接
    # UnicodeEncodeError、stderr 印成 \uXXXX（DEF-101-789 逐字重現）。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main())
