#!/usr/bin/env bash
# ============================================================
# AISDLC 追溯鏈驗證工具 (Traceability Chain Verification Tool)
# ============================================================
# 版本: v1.1-SDD
# 建立日期: 2026-02-11
# 更新日期: 2026-04-16（更新為 SDD v0.01 路徑）
# 用途: 驗證 docs/ 目錄中 ID 引用的完整性和一致性
# 使用方式: bash AISDLC_SDD_v0.01/tools/verify_traceability.sh [docs_path]
# docs_path 預設為 AISDLC_SDD_v0.01/docs/（含 01_requirements/, 02_architecture/, 03_testing/ 等子目錄）
# ============================================================

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 計數器
TOTAL_CHECKS=0
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# 預設 docs 目錄
DOCS_DIR="${1:-docs}"

echo "============================================================"
echo "  AISDLC-SDD 追溯鏈驗證工具 v1.1-SDD"
echo "============================================================"
echo ""

# 檢查 docs 目錄是否存在
if [ ! -d "$DOCS_DIR" ]; then
    echo -e "${RED}[ERROR] docs 目錄不存在: $DOCS_DIR${NC}"
    echo "用法: bash verify_traceability.sh [docs_path]"
    echo "範例: bash verify_traceability.sh docs"
    exit 1
fi

echo -e "${BLUE}[INFO] 掃描目錄: $DOCS_DIR${NC}"
echo ""

# ============================================================
# 1. 掃描所有 ID 定義和引用
# ============================================================
echo "--- 1. 掃描 ID 定義與引用 ---"
echo ""

# ID 模式定義 (AISDLC 標準)
# F-XXX, BR-XXX, EPIC-XXX, US-XXX, AC-XXX-Y, API-XXX, TC-XXX-Y-Z, BUG-XXX, NFR-XXX
# bash 3.2 相容（macOS 內建 bash 無 declare -A 關聯陣列）：改用「名稱|模式」平行清單
ID_PATTERNS=(
    "Feature|F-[0-9]{3}"
    "BusinessRule|BR-[0-9]{3}"
    "Epic|EPIC-[0-9]{3}"
    "UserStory|US-[0-9]{3}"
    "AcceptanceCriteria|AC-[0-9]{3}-[0-9]+"
    "API|API-[0-9]{3}"
    "TestCase|TC-[0-9]{3}-[0-9]+-[0-9]+"
    "Bug|BUG-[0-9]{3}"
    "NonFunctional|NFR-[A-Z]+-[0-9]{3}"
)

# 掃描各類型 ID
echo -e "${BLUE}[掃描] 各類型 ID 統計：${NC}"
echo ""

for entry in "${ID_PATTERNS[@]}"; do
    id_type="${entry%%|*}"
    pattern="${entry#*|}"
    count=$(grep -rhoE "$pattern" "$DOCS_DIR" 2>/dev/null | sort -u | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        echo -e "  ${GREEN}✅${NC} $id_type ($pattern): $count 個唯一 ID"
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "  ${YELLOW}⚠️${NC} $id_type ($pattern): 未找到（可能尚未建立）"
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
done

echo ""

# ============================================================
# 2. 追溯鏈完整性檢查
# ============================================================
echo "--- 2. 追溯鏈完整性檢查 ---"
echo ""

# 檢查 F-XXX → US-XXX 追溯
echo -e "${BLUE}[檢查] Feature → User Story 追溯鏈：${NC}"
feature_ids=$(grep -rhoE "F-[0-9]{3}" "$DOCS_DIR" 2>/dev/null | sort -u)
if [ -n "$feature_ids" ]; then
    while IFS= read -r fid; do
        # 檢查該 Feature 是否被任何 User Story 引用
        us_refs=$(grep -rl "$fid" "$DOCS_DIR" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$us_refs" -gt 1 ]; then
            echo -e "  ${GREEN}✅${NC} $fid - 在 $us_refs 個文件中被引用"
            PASS_COUNT=$((PASS_COUNT + 1))
        elif [ "$us_refs" -eq 1 ]; then
            echo -e "  ${YELLOW}⚠️${NC} $fid - 僅在 1 個文件中出現（可能缺少下游追溯）"
            WARN_COUNT=$((WARN_COUNT + 1))
        else
            echo -e "  ${RED}❌${NC} $fid - 未被任何文件引用"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    done <<< "$feature_ids"
else
    echo -e "  ${YELLOW}⚠️${NC} 未找到 Feature ID (F-XXX)"
    WARN_COUNT=$((WARN_COUNT + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi
echo ""

# 檢查 US-XXX → AC-XXX-Y 追溯
echo -e "${BLUE}[檢查] User Story → Acceptance Criteria 追溯鏈：${NC}"
us_ids=$(grep -rhoE "US-[0-9]{3}" "$DOCS_DIR" 2>/dev/null | sort -u)
if [ -n "$us_ids" ]; then
    while IFS= read -r usid; do
        us_num=$(echo "$usid" | grep -oE "[0-9]{3}")
        ac_count=$(grep -rhoE "AC-${us_num}-[0-9]+" "$DOCS_DIR" 2>/dev/null | sort -u | wc -l | tr -d ' ')
        if [ "$ac_count" -gt 0 ]; then
            echo -e "  ${GREEN}✅${NC} $usid → $ac_count 個 AC"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo -e "  ${RED}❌${NC} $usid → 0 個 AC（缺少驗收標準）"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    done <<< "$us_ids"
else
    echo -e "  ${YELLOW}⚠️${NC} 未找到 User Story ID (US-XXX)"
    WARN_COUNT=$((WARN_COUNT + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi
echo ""

# 檢查 API-XXX 是否在 SRD 或 API Spec 中定義
echo -e "${BLUE}[檢查] API ID 定義與引用：${NC}"
api_ids=$(grep -rhoE "API-[0-9]{3}" "$DOCS_DIR" 2>/dev/null | sort -u)
if [ -n "$api_ids" ]; then
    while IFS= read -r apiid; do
        api_files=$(grep -rl "$apiid" "$DOCS_DIR" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$api_files" -gt 1 ]; then
            echo -e "  ${GREEN}✅${NC} $apiid - 在 $api_files 個文件中引用（含定義和使用）"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo -e "  ${YELLOW}⚠️${NC} $apiid - 僅在 1 個文件中出現"
            WARN_COUNT=$((WARN_COUNT + 1))
        fi
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    done <<< "$api_ids"
else
    echo -e "  ${YELLOW}⚠️${NC} 未找到 API ID (API-XXX)"
    WARN_COUNT=$((WARN_COUNT + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi
echo ""

# ============================================================
# 3. 孤立 ID 檢查（定義但未被引用）
# ============================================================
echo "--- 3. 孤立 ID 檢查 ---"
echo ""

echo -e "${BLUE}[檢查] 尋找僅出現一次的 ID（可能為孤立定義）：${NC}"
all_ids=$(grep -rhoE "(F|BR|EPIC|US|AC|API|TC|BUG|NFR)-[A-Z]*-?[0-9]{3}(-[0-9]+)*" "$DOCS_DIR" 2>/dev/null | sort | uniq -c | sort -rn)
orphan_count=0
if [ -n "$all_ids" ]; then
    while IFS= read -r line; do
        count=$(echo "$line" | awk '{print $1}')
        id=$(echo "$line" | awk '{print $2}')
        if [ "$count" -eq 1 ]; then
            orphan_count=$((orphan_count + 1))
            if [ "$orphan_count" -le 10 ]; then
                echo -e "  ${YELLOW}⚠️${NC} $id - 僅出現 1 次（可能缺少追溯連結）"
            fi
        fi
    done <<< "$all_ids"
    if [ "$orphan_count" -gt 10 ]; then
        echo -e "  ${YELLOW}⚠️${NC} ... 還有 $((orphan_count - 10)) 個孤立 ID（省略顯示）"
    fi
    if [ "$orphan_count" -eq 0 ]; then
        echo -e "  ${GREEN}✅${NC} 所有 ID 至少在 2 個文件中被引用"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "  ${YELLOW}⚠️${NC} 共 $orphan_count 個孤立 ID"
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
else
    echo -e "  ${YELLOW}⚠️${NC} 未找到任何 AISDLC ID"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo ""

# ============================================================
# 4. 文件間交叉引用檢查
# ============================================================
echo "--- 4. 文件間交叉引用檢查 ---"
echo ""

# 檢查 PRD 是否存在
echo -e "${BLUE}[檢查] 核心文件存在性：${NC}"
for doc_type in "PRD" "FRD" "SRD"; do
    found=$(find "$DOCS_DIR" -iname "*${doc_type}*" -type f 2>/dev/null | head -1)
    if [ -n "$found" ]; then
        echo -e "  ${GREEN}✅${NC} $doc_type 文件存在: $(basename "$found")"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "  ${YELLOW}⚠️${NC} $doc_type 文件未找到"
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
done
echo ""

# 檢查 Markdown 內部連結
echo -e "${BLUE}[檢查] Markdown 內部連結有效性：${NC}"
broken_links=0
total_links=0
while IFS= read -r file; do
    # 提取 Markdown 連結中的相對路徑
    links=$(grep -oE '\[.*?\]\([^)#]+\)' "$file" 2>/dev/null | grep -oE '\(([^)#]+)\)' | tr -d '()' | grep -v '^http' | grep -v '^mailto')
    if [ -n "$links" ]; then
        dir=$(dirname "$file")
        while IFS= read -r link; do
            total_links=$((total_links + 1))
            target="$dir/$link"
            if [ ! -e "$target" ]; then
                broken_links=$((broken_links + 1))
                if [ "$broken_links" -le 5 ]; then
                    echo -e "  ${RED}❌${NC} 斷連: $file → $link"
                fi
            fi
        done <<< "$links"
    fi
done < <(find "$DOCS_DIR" -name "*.md" -type f 2>/dev/null)

if [ "$broken_links" -eq 0 ] && [ "$total_links" -gt 0 ]; then
    echo -e "  ${GREEN}✅${NC} 所有 $total_links 個內部連結有效"
    PASS_COUNT=$((PASS_COUNT + 1))
elif [ "$broken_links" -gt 5 ]; then
    echo -e "  ${RED}❌${NC} ... 還有 $((broken_links - 5)) 個斷連（省略顯示）"
    echo -e "  ${RED}❌${NC} 共 $broken_links/$total_links 個連結失效"
    FAIL_COUNT=$((FAIL_COUNT + 1))
elif [ "$broken_links" -gt 0 ]; then
    echo -e "  ${RED}❌${NC} 共 $broken_links/$total_links 個連結失效"
    FAIL_COUNT=$((FAIL_COUNT + 1))
elif [ "$total_links" -eq 0 ]; then
    echo -e "  ${YELLOW}⚠️${NC} 未找到內部連結"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
echo ""

# ============================================================
# 5. 結果報告
# ============================================================
echo "============================================================"
echo "  驗證結果報告"
echo "============================================================"
echo ""
echo -e "  總檢查項目: $TOTAL_CHECKS"
echo -e "  ${GREEN}✅ 通過: $PASS_COUNT${NC}"
echo -e "  ${YELLOW}⚠️  警告: $WARN_COUNT${NC}"
echo -e "  ${RED}❌ 失敗: $FAIL_COUNT${NC}"
echo ""

if [ "$FAIL_COUNT" -eq 0 ] && [ "$WARN_COUNT" -eq 0 ]; then
    echo -e "${GREEN}🎉 追溯鏈驗證全部通過！${NC}"
    exit 0
elif [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  追溯鏈基本完整，但有 $WARN_COUNT 個警告需注意。${NC}"
    exit 0
else
    echo -e "${RED}❌ 追溯鏈有 $FAIL_COUNT 個問題需修復！${NC}"
    exit 1
fi
