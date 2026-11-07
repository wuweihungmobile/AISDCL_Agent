# Test Contract Specification — TCS 草擬夾具（五個 AC、每個一個 AT）

## 1. AC → AT 映射表

| AC | AT |
|---|---|
| AC-001-1 | AT-001-1-1 |
| AC-001-2 | AT-001-2-1 |
| AC-002-1 | AT-002-1-1 |
| AC-003-1 | AT-003-1-1 |
| AC-003-2 | AT-003-2-1 |

## 3. AT 完整清單

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1
# 判定：python -m pytest tests -k AT_001_1_1 -q

Scenario: AC-001-1 的驗收
  Given 前置條件
  When 執行動作
  Then 得到預期結果
```n
```gherkin
# AT-001-2-1
# 對應 AC: AC-001-2
# 判定：python -m pytest tests -k AT_001_2_1 -q

Scenario: AC-001-2 的驗收
  Given 前置條件
  When 執行動作
  Then 得到預期結果
```n
```gherkin
# AT-002-1-1
# 對應 AC: AC-002-1
# 判定：python -m pytest tests -k AT_002_1_1 -q

Scenario: AC-002-1 的驗收
  Given 前置條件
  When 執行動作
  Then 得到預期結果
```n
```gherkin
# AT-003-1-1
# 對應 AC: AC-003-1
# 判定：python -m pytest tests -k AT_003_1_1 -q

Scenario: AC-003-1 的驗收
  Given 前置條件
  When 執行動作
  Then 得到預期結果
```n
```gherkin
# AT-003-2-1
# 對應 AC: AC-003-2
# 判定：python -m pytest tests -k AT_003_2_1 -q

Scenario: AC-003-2 的驗收
  Given 前置條件
  When 執行動作
  Then 得到預期結果
```n
