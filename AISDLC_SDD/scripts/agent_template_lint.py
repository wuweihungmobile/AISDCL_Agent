#!/usr/bin/env python3
"""Agent template 路徑存在性 lint（DEF-AGTREV-002 機械強制）。

版本無關 shared infra、read-only 純觀察者。掃磁碟最新演化版的
agent/core/*.yaml + agent/specialized/*.yaml，檢查所有 `template_path:` /
`template:` / `dependencies.templates` 清單項所引用的 `docs_template/...` 路徑是否
實際存在於該版本 docs_template/ 下，並強制「框架根相對」慣例（不得帶 ../）。

緣由：SDD 轉型只往前加 sdd_skills 新接線、未回填舊 document_responsibilities /
dependencies.templates → ~75 條 broken template_path 長期潛伏（v0.17 審查揭露）。
v0.18 全面重新接線（方案一）後，加此 lint 杜絕再生。

判準（任一即非零硬閘擋下）：
  1. 引用的 docs_template/ 路徑（去 ../ 正規化後）在磁碟不存在。
  2. 引用帶 ../ 前綴（違反「框架根相對」單一慣例）。
註解行（# 開頭）一律忽略（模板示例 / 說明文字非功能性引用）。

用法：python scripts/agent_template_lint.py <REPO_ROOT>
Exit：0 全部解析且根相對；1 任一 broken 或非根相對。
"""
import os
import re
import sys
import glob

try:  # Windows cp950 console 下仍能輸出中文/emoji（與 ci-gate.sh bash 環境相容）
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TOK = re.compile(r'(\.\./)*docs_template/[^\s"\'\]]+')


def detect_latest(repo_root):
    cands = []
    for p in glob.glob(os.path.join(repo_root, "AISDLC_SDD_v0.0*")) + \
             glob.glob(os.path.join(repo_root, "AISDLC_SDD_v0.[1-9]*")):
        if os.path.isdir(p):
            cands.append(os.path.basename(p))
    # sort -V 等價：以 (major, minor) 數值排序
    def key(name):
        m = re.search(r'v0\.(\d+)$', name)
        return int(m.group(1)) if m else -1
    cands.sort(key=key)
    return cands[-1] if cands else None


def main():
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    ver = detect_latest(repo_root)
    if not ver:
        print("::error:: 找不到任何 AISDLC_SDD_v0.* 版本目錄")
        return 1
    base = os.path.join(repo_root, ver)
    tmpl_root = os.path.join(base, "docs_template")
    pool = set()
    for dp, _, fs in os.walk(tmpl_root):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), base).replace("\\", "/")
            pool.add(rel)

    broken = []
    nonrootrel = []
    files = sorted(glob.glob(os.path.join(base, "agent/core/*.yaml")) +
                   glob.glob(os.path.join(base, "agent/specialized/*.yaml")))
    for fp in files:
        rels = os.path.relpath(fp, base).replace("\\", "/")
        for i, line in enumerate(open(fp, encoding="utf-8"), 1):
            if line.lstrip().startswith("#"):
                continue
            for m in TOK.finditer(line):
                tok = m.group(0)
                norm = re.sub(r'^(\.\./)+', '', tok)
                if tok != norm:
                    nonrootrel.append(f"{rels}:{i} {tok}")
                if norm not in pool:
                    broken.append(f"{rels}:{i} {norm}")

    if not broken and not nonrootrel:
        print(f"✅ agent template lint：{ver} 全部 template 引用解析成功且根相對")
        return 0
    print(f"::error:: agent template lint 失敗（{ver}）")
    for b in broken:
        print(f"  BROKEN  {b}")
    for n in nonrootrel:
        print(f"  NON-ROOT-RELATIVE(../)  {n}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
