# Markdown Linting 規則指南

**文檔類型**: 文檔品質工具
**版本**: v0.01
**最後更新**: 2025-11-27
**適用範圍**: AISDLC 所有 Markdown 文檔

---

## 🎯 目的

本指南定義 AISDLC 框架中所有 Markdown 文檔的 Linting 規則，確保：
- 文檔格式一致性
- 可讀性最佳化
- 避免常見的 Markdown 錯誤
- 提升文檔專業度

---

## 📋 Linting 工具

**推薦工具**: [markdownlint](https://github.com/DavidAnson/markdownlint)

**安裝方式**:
```bash
# NPM
npm install -g markdownlint-cli

# Yarn
yarn global add markdownlint-cli

# 或使用 VS Code 擴充功能
# 搜尋: markdownlint (David Anson)
```

**使用方式**:
```bash
# 檢查單一檔案
markdownlint README.md

# 檢查整個目錄
markdownlint **/*.md

# 使用配置檔案
markdownlint -c .markdownlint.json **/*.md

# 自動修復
markdownlint --fix **/*.md
```

---

## 🔧 規則配置 (.markdownlint.json)

配置檔案位置: `scenarios/greenfield/checklists/.markdownlint.json`

### 啟用的核心規則

#### MD001 - Heading levels should only increment by one level at a time
**說明**: 標題層級應逐級遞增（不能從 H1 直接跳到 H3）

**正確**:
```markdown
# H1
## H2
### H3
```

**錯誤**:
```markdown
# H1
### H3  ❌ 跳過 H2
```

---

#### MD003 - Heading style (ATX)
**說明**: 使用 ATX 風格標題（# 符號）

**正確**:
```markdown
# 標題
## 副標題
```

**錯誤**:
```markdown
標題
====  ❌ Setext 風格
```

---

#### MD004 - Unordered list style (dash)
**說明**: 無序列表統一使用 `-`

**正確**:
```markdown
- 項目 1
- 項目 2
```

**錯誤**:
```markdown
* 項目 1  ❌ 使用 *
+ 項目 2  ❌ 使用 +
```

---

#### MD007 - Unordered list indentation (2 spaces)
**說明**: 無序列表縮排 2 個空格

**正確**:
```markdown
- 項目 1
  - 子項目 1
  - 子項目 2
```

**錯誤**:
```markdown
- 項目 1
    - 子項目 1  ❌ 4 個空格
```

---

#### MD009 - Trailing spaces
**說明**: 行尾空格處理

**配置**:
- `br_spaces`: 2 - 允許行尾 2 個空格（用於換行）
- `list_item_empty_lines`: false - 列表項之間不要求空行
- `strict`: false - 寬鬆模式

**正確**:
```markdown
這是一行文字
這是下一行（使用 2 個空格換行）
```

---

#### MD010 - Hard tabs (4 spaces per tab)
**說明**: 用空格替代 Tab（程式碼區塊除外）

**配置**:
- `code_blocks`: false - 程式碼區塊內允許 Tab
- `spaces_per_tab`: 4

---

#### MD012 - Multiple consecutive blank lines (最多 2 行)
**說明**: 連續空行最多 2 行

**正確**:
```markdown
段落 1


段落 2  ✅ 最多 2 個空行
```

---

#### MD013 - Line length (禁用)
**說明**: 行長度限制 **已禁用**

**原因**:
- 中文文檔不適合嚴格的行長度限制
- 表格和程式碼區塊可能需要較長行
- 避免過度格式化

---

#### MD024 - Multiple headings with the same content (siblings_only)
**說明**: 同一層級不允許相同標題

**配置**:
- `siblings_only`: true - 僅檢查同一層級

**正確**:
```markdown
# 文檔 A
## 概述

# 文檔 B
## 概述  ✅ 不同父級下可以重複
```

---

#### MD025 - Multiple top-level headings
**說明**: 每個檔案只能有一個 H1 標題

---

#### MD026 - Trailing punctuation in heading
**說明**: 標題結尾不使用標點符號

**配置**: 禁止 `.,;:!`

**正確**:
```markdown
## 安裝指南
```

**錯誤**:
```markdown
## 安裝指南。  ❌
```

---

#### MD029 - Ordered list item prefix (ordered)
**說明**: 有序列表使用遞增數字

**正確**:
```markdown
1. 第一步
2. 第二步
3. 第三步
```

**錯誤**:
```markdown
1. 第一步
1. 第二步  ❌ 全部使用 1
1. 第三步
```

---

#### MD030 - Spaces after list markers
**說明**: 列表標記後的空格數量

**配置**: 所有情況使用 1 個空格

**正確**:
```markdown
- 項目
1. 項目
```

---

#### MD033 - Inline HTML (允許部分標籤)
**說明**: 限制 HTML 標籤使用

**允許的標籤**:
- `<br>` - 換行
- `<sub>`, `<sup>` - 上下標
- `<details>`, `<summary>` - 摺疊內容

**範例**:
```markdown
H<sub>2</sub>O  ✅
E=mc<sup>2</sup>  ✅

<details>
<summary>點擊展開</summary>
詳細內容
</details>  ✅

<div>...</div>  ❌ 不允許其他 HTML 標籤
```

---

#### MD034 - Bare URLs (禁用)
**說明**: 裸 URL 檢查 **已禁用**

**原因**: 允許直接顯示 URL 而不強制使用連結語法

---

#### MD036 - Emphasis used instead of heading
**說明**: 不要用粗體/斜體替代標題

**正確**:
```markdown
## 標題
```

**錯誤**:
```markdown
**這不是標題**  ❌
```

---

#### MD040 - Fenced code blocks should have a language specified
**說明**: 程式碼區塊必須指定語言

**正確**:
````markdown
```javascript
console.log('Hello');
```
````

**錯誤**:
````markdown
```
console.log('Hello');  ❌ 未指定語言
```
````

---

#### MD041 - First line in a file should be a top-level heading (禁用)
**說明**: 檔案首行必須為 H1 標題 **已禁用**

**原因**: AISDLC 文檔可能包含 frontmatter 或說明文字

---

#### MD046 - Code block style (fenced)
**說明**: 使用圍欄式程式碼區塊（\`\`\`）

**正確**:
````markdown
```javascript
code here
```
````

**錯誤**:
```markdown
    code here  ❌ 縮排式
```

---

#### MD047 - Files should end with a single newline character
**說明**: 檔案結尾必須有一個換行符

---

#### MD048 - Code fence style (backtick)
**說明**: 使用反引號（\`）作為程式碼圍欄

**正確**:
````markdown
```javascript
code
```
````

**錯誤**:
```markdown
~~~javascript  ❌ 使用 ~
code
~~~
```

---

#### MD049 - Emphasis style (asterisk)
**說明**: 使用星號（*）表示斜體

**正確**:
```markdown
*斜體*
```

**錯誤**:
```markdown
_斜體_  ❌ 使用底線
```

---

#### MD050 - Strong style (asterisk)
**說明**: 使用雙星號（**）表示粗體

**正確**:
```markdown
**粗體**
```

**錯誤**:
```markdown
__粗體__  ❌ 使用雙底線
```

---

## 🔍 整合到開發流程

### 1. Pre-commit Hook

使用 Git Hook 在 commit 前自動檢查：

**安裝 husky**:
```bash
npm install --save-dev husky lint-staged
```

**配置 .husky/pre-commit**:
```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npx lint-staged
```

**配置 package.json**:
```json
{
  "lint-staged": {
    "*.md": [
      "markdownlint --fix",
      "git add"
    ]
  }
}
```

---

### 2. CI/CD 整合

**GitHub Actions 範例**:
```yaml
name: Markdown Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Markdown Lint
        uses: avto-dev/markdown-lint@v1
        with:
          config: '.markdownlint.json'
          args: '**/*.md'
```

---

### 3. VS Code 整合

**安裝擴充功能**:
1. 開啟 VS Code
2. 搜尋 "markdownlint" (by David Anson)
3. 安裝並重新載入

**配置 settings.json**:
```json
{
  "markdownlint.config": {
    "extends": ".markdownlint.json"
  }
}
```

---

## 📝 常見問題處理

### Q1: 如何忽略特定規則？

在檔案中使用註解：
```markdown
<!-- markdownlint-disable MD013 -->
這行很長很長很長...
<!-- markdownlint-enable MD013 -->
```

---

### Q2: 如何忽略整個檔案？

在檔案開頭加入：
```markdown
<!-- markdownlint-disable-file -->
```

---

### Q3: 舊文檔如何處理？

**建議步驟**:
1. 執行 `markdownlint --fix` 自動修復
2. 手動檢查無法自動修復的問題
3. 對於複雜文檔，可暫時禁用部分規則

---

### Q4: 表格格式化問題？

表格可能因 MD013（行長度）產生警告，已禁用此規則。

如需要對齊表格：
```bash
# 使用 prettier
npm install --save-dev prettier
npx prettier --write **/*.md
```

---

## 🎯 最佳實踐

### 1. 新文檔建立

✅ **推薦流程**:
1. 使用模板建立文檔
2. 編寫內容
3. 執行 `markdownlint --fix` 自動修復
4. 手動檢查修復結果
5. Commit 前再次檢查

---

### 2. 程式碼區塊語言標記

**常用語言標記**:
- `javascript` / `js`
- `typescript` / `ts`
- `python`
- `bash` / `shell`
- `yaml`
- `json`
- `markdown` / `md`
- `plaintext` / `text` (純文字)

---

### 3. 中英文混排

**標點符號規則**:
- 中文使用全形標點：，。！？
- 英文使用半形標點：, . ! ?
- 中英文之間建議加空格

**範例**:
```markdown
✅ 使用 AISDLC 框架，可以提升 50% 的開發效率。
❌ 使用AISDLC框架,可以提升50%的開發效率.
```

---

### 4. 連結與圖片

**相對路徑規範**:
```markdown
✅ [文檔](../docs/README.md)
✅ ![圖片](./images/diagram.png)
❌ [文檔](/absolute/path/README.md)  (避免絕對路徑)
```

---

## 🔄 規則更新流程

當需要調整 Linting 規則時：

1. **討論提案**: 在團隊中討論規則變更的必要性
2. **更新配置**: 修改 `.markdownlint.json`
3. **測試影響**: 在少量檔案上測試新規則
4. **批次修復**: 使用 `--fix` 批次修復現有文檔
5. **文檔更新**: 更新本指南說明
6. **團隊通知**: 通知所有成員新規則

---

## 📚 參考資源

- **markdownlint 官方文檔**: https://github.com/DavidAnson/markdownlint
- **規則列表**: https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md
- **CommonMark 規範**: https://commonmark.org/
- **GitHub Flavored Markdown**: https://github.github.com/gfm/

---

## ✅ 檢查清單

使用此檢查清單確保文檔符合 Linting 規則：

- [ ] 檔案只有一個 H1 標題
- [ ] 標題層級逐級遞增（無跳級）
- [ ] 無序列表使用 `-`
- [ ] 列表縮排 2 個空格
- [ ] 程式碼區塊指定語言
- [ ] 使用 ATX 風格標題（# 符號）
- [ ] 連續空行不超過 2 行
- [ ] 標題結尾無標點符號
- [ ] 檔案結尾有換行符
- [ ] 無行尾多餘空格（除非用於換行）
- [ ] 執行 `markdownlint` 無錯誤

---

**維護人員**: AISDLC 維護團隊
**相關文檔**: [Document_Quality_Checklist.md](../../../guides/system/quality/Document_Quality_Checklist.md)
