# GlocalText 規則系統測試

本目錄包含 GlocalText 規則系統的所有相關測試。

## 📋 測試文件組織

### 核心規則測試

-   `test_replace_rules.py` - Replace 規則測試
-   `test_protect_rules.py` - Protect 規則測試
-   `test_skip_rules.py` - Skip 規則測試

### 規則行為驗證

-   `test_rules_original_text.py` - 驗證所有規則都檢查原始文本
-   `test_rules_independence.py` - 驗證規則之間的獨立性

### Coverage 與 Cache

-   `test_coverage.py` - Coverage 計算邏輯測試
-   `test_cache_protection.py` - Cache 和保護機制測試

## 🎯 設計原則

### 統一架構原則

所有規則（Replace、Protect、Skip）都應該：

1. **檢查原始文本** - 不受其他規則處理結果影響
2. **規則獨立性** - 規則之間不相互依賴
3. **Coverage 參與** - 所有規則都參與 Coverage 計算

### 執行流程

```
階段 A - Coverage 計算:
  ├─ Replace: 匹配範圍計入 Coverage
  ├─ Protect: 匹配範圍計入 Coverage
  └─ Skip: 必須完全覆蓋才計入 Coverage

階段 B - 翻譯處理:
  ├─ Replace: 在原始文本中替換
  ├─ Protect: 在原始文本中查找，當前文本中替換為佔位符
  └─ 翻譯並還原
```

## 🧪 執行測試

### 執行所有規則測試

```bash
pytest tests/rules/ -v
```

### 執行特定測試文件

```bash
# Replace 規則
pytest tests/rules/test_replace_rules.py -v

# 規則獨立性
pytest tests/rules/test_rules_independence.py -v
```

### 執行特定測試

```bash
pytest tests/rules/test_rules_original_text.py::TestRulesCheckOriginalText::test_replace_rule_checks_original_text -v
```

## 📚 相關文檔

-   [完整執行計劃](.ogos/alpha_coder/COMPLETE_EXECUTION_PLAN.md)
-   [設計理解](.ogos/alpha_coder/CORRECT_UNDERSTANDING_V3.md)
-   [測試目錄分析](.ogos/alpha_coder/TEST_DIRECTORY_ANALYSIS.md)
