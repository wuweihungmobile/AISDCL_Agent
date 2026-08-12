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
  3. （DEF-AGTREV-005 盲區封閉）`template_path:` / `template:` 值為「裸檔名」
     （非 docs_template/ 根相對前綴，如 `user-story-template.md`）。原 TOK regex 只認
     帶 `docs_template/` 前綴的 token，使核心 agent 內 12 條短名 broken template_path
     長期假綠潛伏（v0.18 重審揭露）；此判準強制所有 template_path 一律根相對，杜絕再生。
  4. （AGT-11 / R85 擴面）`dependencies` 的 **`data` / `tasks` / `checklists` / `tools`**
     四桶清單項，正規化（剝 ../）後必須能在**版本樹內**解析，且必須是框架根相對。

🔴 判準 4 的立案事實（R85 實測；數字經 F2 複審訂正，見下）：本 lint 在此之前只驗
   `dependencies.templates` **一個**桶，而 `dependencies` 實際有五個桶。另四桶在 HEAD
   實測共 **302 條**（data 79／tasks 97／checklists 75／tools 51），其中 **301 條**是裸檔名、
   在版本樹內解析 0 命中（唯一的例外是一條帶 `../` 的真實引用，它解析得到、只是前綴違規）
   ⇒ 「鎖在、但只守五分之一」，分母被常數窄化而失效是靜默的：lint 照跑、照綠、照回報
   命中數，只有那四桶從來不在分母裡。與本檔既有的 DEF-AGTREV-005 盲區**同型**，
   只是那次窄化的是 regex、這次窄化的是桶名。

   🔴 **被訂正的原文逐字保留（訂正協議：禁止靜默覆寫）**：「另四桶當回合實測共 **199 條**，
      其中 **198 條**是裸檔名」。**兩個數字都假**（真值 302／301，低報約三分之一），且同一組
      假數字當輪被複製到**三個家**——本檔、`tests/test_agent_template_lint.py`、
      `AISDLC_SDD_v<LATEST>/agent/core/05.sd-architect-zh.yaml` 的 AGT-11 註解區——
      三份都不會因為彼此不一致而轉紅。取數管道（可重跑，不依賴任何快照）：
      `git archive HEAD <LATEST 版本目錄>` 抽一份 HEAD 副本，以**本 lint 自己的判準**跑它，
      findings 逐行按 `dependencies.<bucket>:` 分桶計數。

   判準 4 刻意**不要求** `docs_template/` 前綴（那四桶的合法標的可以是 `guides/` 等任何
   版本樹內資產），只要求「解析得到」＋「根相對」——把 templates 桶那條更嚴的前綴規則
   外推到這四桶會製造假紅，而那種鎖活不過一輪。

🔴 **判準 4 今天的活分母是 1，不是 302**（F2 複審實測；寫在這裡是為了讓下一輪的人不會
   誤以為它在守 300 條）：301 條幽靈依賴已於同輪清除，四桶現存 entry 為
   **data 1／tasks 0／checklists 0／tools 0**——`tasks`／`checklists`／`tools` 三桶
   **結構上沒有東西可判**，唯一的活條目是 `06.dev-developer-zh.yaml` 那條（已修正前綴）。

   ⇒ 裁決：判準 4 是**純寫入面判準**（存量已清空，守的是「下一個人寫出違規時當場紅」），
   **不是恆綠裝飾品**。兩者分得開，判別方式是合成注入自證——對拋棄式真實樹副本逐桶注入
   一條 `ghost-<bucket>-asset.md`，四桶**皆 rc=1 且命中該桶**、還原後**皆 rc=0**
   （F2 當回合實測 8 個 rc 全數符合）。回歸鎖＝`tests/test_agent_template_lint.py` 的
   `test_ghost_bare_name_in_each_dep_bucket_fails`（逐桶迴圈，不是只驗一桶）。
   **這條自證必須留著**：活分母為 0／1 的判準一旦失去鑑別力，它的失效表徵與「全部通過」
   完全相同——這正是本檔判準 4 當初要治的那個病，只是換到判準自己身上。

註解行（# 開頭）一律忽略（模板示例 / 說明文字非功能性引用）。

用法：python scripts/agent_template_lint.py <REPO_ROOT>
Exit：0 全部解析且根相對；1 任一 broken 或非根相對。
"""
import os
import re
import sys
import glob

import yaml

try:  # Windows cp950 console 下仍能輸出中文/emoji（與 ci-gate.sh bash 環境相容）
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TOK = re.compile(r'(\.\./)*docs_template/[^\s"\'\]]+')
# DEF-AGTREV-005：擷取 template_path/template 的值，封閉「裸檔名 / 誤指 docs/」盲區（非 docs_template/ 前綴）。
# DEF-AGTREV-008（QA 閉環複審補抓）：副檔名不限 .md，須涵蓋 .yaml/.yml/.json（sdd_skills 的
# API CONTRACT template 為 .yaml，原 `\.md` 規格漏抓 2 條誤指 docs/ 的 .yaml template）。
BARE = re.compile(r'(?:template_path|template)\s*:\s*["\']([^"\']+)["\']')
_TMPL_EXT = re.compile(r'\.(md|ya?ml|json)$', re.IGNORECASE)
# AGT-11（R85）：`dependencies` 的非-templates 四桶。與 `templates` 分開列是刻意的——
# 那一桶另有更嚴的 `docs_template/` 前綴規則（見判準 3），兩者不可互相外推。
DEP_ASSET_BUCKETS = ("data", "tasks", "checklists", "tools")


def detect_latest(repo_root):
    cands = []
    for p in glob.glob(os.path.join(repo_root, "AISDLC_SDD_v0.0*")) + \
             glob.glob(os.path.join(repo_root, "AISDLC_SDD_v0.[1-9]*")):
        if os.path.isdir(p):
            cands.append(os.path.basename(p))
    # 數值排序取最高（排序語意對齊 scripts/sdd_version.py SSOT；本 lint 為磁碟掃描面）
    def key(name):
        m = re.search(r'v0\.(\d+)$', name)
        return int(m.group(1)) if m else -1
    cands.sort(key=key)
    return cands[-1] if cands else None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else "."
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
    # AGT-11：判準 4 的解析面是**整個版本樹**，不是 docs_template/ 那一角
    # （四桶的合法標的可以是 guides/ 等任何版本樹內資產）。
    treepool = set()
    for dp, _, fs in os.walk(base):
        for f in fs:
            treepool.add(os.path.relpath(os.path.join(dp, f), base).replace("\\", "/"))

    broken = []
    nonrootrel = []
    barename = []
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
            # DEF-AGTREV-005/008：裸檔名 / 誤指 docs/ 的 template（非 docs_template/ 前綴）盲區封閉
            for m in BARE.finditer(line):
                val = m.group(1)
                norm = re.sub(r'^(\.\./)+', '', val)
                if not _TMPL_EXT.search(norm):
                    continue  # 非檔案引用（描述性文字）→ 略過，避免誤報
                if not norm.startswith("docs_template/"):
                    barename.append(f"{rels}:{i} {val}")
        # DEF-AGTREV-005：dependencies.templates 清單項（line-based regex 看不到）以 YAML 精確檢查
        try:
            with open(fp, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
            for tmpl in ((doc.get("dependencies") or {}).get("templates") or []):
                if not isinstance(tmpl, str):
                    continue
                norm = re.sub(r'^(\.\./)+', '', tmpl)
                if not _TMPL_EXT.search(norm):
                    continue
                if not norm.startswith("docs_template/"):
                    barename.append(f"{rels} dependencies.templates: {tmpl}")
                elif norm not in pool:
                    broken.append(f"{rels} dependencies.templates: {norm}")
            # AGT-11（R85）判準 4：另四桶——只要求「版本樹內解析得到」＋「根相對」。
            deps = doc.get("dependencies") or {}
            if isinstance(deps, dict):
                for bucket in DEP_ASSET_BUCKETS:
                    for dep in (deps.get(bucket) or []):
                        if not isinstance(dep, str):
                            continue
                        norm = re.sub(r'^(\.\./)+', '', dep.strip())
                        if not _TMPL_EXT.search(norm):
                            continue  # 非檔案引用（描述性文字）→ 略過，同 templates 桶慣例
                        if norm != dep.strip():
                            nonrootrel.append(f"{rels} dependencies.{bucket}: {dep}")
                        if norm not in treepool:
                            broken.append(f"{rels} dependencies.{bucket}: {norm}")
        except yaml.YAMLError:
            pass

    if not broken and not nonrootrel and not barename:
        print(f"✅ agent template lint：{ver} 全部 template 引用解析成功且根相對")
        return 0
    print(f"::error:: agent template lint 失敗（{ver}）")
    for b in broken:
        print(f"  BROKEN  {b}")
    for n in nonrootrel:
        print(f"  NON-ROOT-RELATIVE(../)  {n}")
    for b in barename:
        print(f"  BARE-NAME(非 docs_template/ 根相對)  {b}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
