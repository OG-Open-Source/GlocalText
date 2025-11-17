# Python regex 模塊測試套件

## 目的

這個測試套件全面驗證 Python `regex` 庫（第三方庫，非標準庫的 `re`）在 GlocalText 項目中的行為。測試套件專注於：

1. **驗證基本功能**：確保 regex 模塊的核心功能正常運作
2. **重現用戶報告的問題**：特別是 `who: are` 替換規則在 shell 命令中的行為
3. **邊界條件測試**：確保在特殊情況下的穩定性
4. **Unicode 支持**：驗證中文和混合語言文本的處理

## 測試結構

```
regex_tests/
├── __init__.py                 # 套件初始化
├── README.md                   # 本文檔
├── test_basic_matching.py      # 基本匹配功能 (14 測試)
├── test_substitution.py        # 替換功能 (20 測試) ⭐ 重點
├── test_patterns.py            # 正則表達式模式 (28 測試)
├── test_flags.py               # 標誌選項 (17 測試)
├── test_unicode.py             # Unicode 支持 (18 測試)
└── test_edge_cases.py          # 邊界情況 (28 測試)
```

**總計**：125+ 個測試案例

## 如何運行測試

### 運行所有測試

```bash
pytest regex_tests/ -v
```

### 運行特定測試文件

```bash
# 只運行替換測試（包含 who:are 問題重現）
pytest regex_tests/test_substitution.py -v

# 只運行 Unicode 測試
pytest regex_tests/test_unicode.py -v
```

### 運行特定測試函數

```bash
# 運行 who:are 問題的專門測試
pytest regex_tests/test_substitution.py::test_who_are_replacement_in_shell_command -v
```

### 顯示詳細輸出

```bash
pytest regex_tests/ -v -s
```

### 生成覆蓋率報告

```bash
pytest regex_tests/ --cov=regex --cov-report=html
```

## 測試覆蓋範圍

### 1. test_basic_matching.py

-   `regex.search()` - 部分匹配
-   `regex.match()` - 從頭匹配
-   `regex.fullmatch()` - 完整匹配
-   字面字符串匹配
-   大小寫敏感性
-   特殊字符轉義
-   Match 對象屬性（start, end, span, group）

### 2. test_substitution.py ⭐

**這是最重要的測試文件**，包含：

-   `regex.sub()` - 基本替換
-   `regex.subn()` - 替換並返回計數
-   **關鍵測試**：`test_who_are_replacement_in_shell_command()`
    -   重現用戶報告的問題
    -   測試在 shell 命令中的字面字符串替換
    -   驗證特殊字符（$, |, (), {}, 等）不影響替換

### 3. test_patterns.py

-   單詞邊界 `\b`
-   字符類 `[...]`, `\d`, `\w`, `\s`
-   量詞 `*`, `+`, `?`, `{n,m}`
-   捕獲分組 `(...)`
-   非捕獲分組 `(?:...)`
-   交替 `|`
-   錨點 `^`, `$`
-   點元字符 `.`
-   貪婪 vs 非貪婪
-   `regex.split()`, `regex.finditer()`

### 4. test_flags.py

-   `regex.IGNORECASE` / `regex.I` - 忽略大小寫
-   `regex.MULTILINE` / `regex.M` - 多行模式
-   `regex.DOTALL` / `regex.S` - 點匹配換行
-   `regex.VERBOSE` / `regex.X` - 詳細模式
-   標誌組合（使用 `|`）
-   內聯標誌語法 `(?i)`, `(?m)`, `(?s)`, `(?x)`

### 5. test_unicode.py

-   中文字符匹配（繁體/簡體）
-   混合語言文本（中英文）
-   Emoji 支持
-   Unicode 屬性 `\p{Han}`（如果支持）
-   中文字符在 shell 命令中的替換
-   中文單詞邊界

### 6. test_edge_cases.py

-   空字符串處理
-   特殊字符：`|`, `$`, `(`, `)`, `{`, `}`, `[`, `]`, `*`, `+`, `?`, `.`, `^`, `\`
-   轉義序列
-   長文本性能
-   無效正則表達式錯誤處理
-   嵌套分組
-   Null 字節
-   Unicode 轉義
-   零寬斷言
-   重疊匹配（如果支持）

## GlocalText 實際使用場景

這些測試特別關注 GlocalText 項目的實際需求：

1. **Shell 命令中的替換**

    ```python
    # 測試文本示例
    text = "- 啟動時間：${CLR2}$(who -b | awk '{print $3, $4}')${CLR0}"
    # 應該將 "who" 替換為 "are"，不影響 shell 語法
    ```

2. **混合語言文本**

    ```python
    # 中英混合
    text = "歡迎使用 GlocalText 進行翻譯"
    ```

3. **特殊字符處理**
    - 不需要轉義字面字符串中的特殊字符
    - 在複雜文本中進行部分匹配替換

## regex 庫特性

### 與標準 `re` 的區別

Python `regex` 庫是 `re` 的增強版本，提供：

1. **更好的 Unicode 支持**

    - Unicode 屬性 `\p{...}`
    - Unicode 腳本 `\p{Script=...}`

2. **附加功能**

    - 重疊匹配 `overlapped=True`
    - 模糊匹配
    - 更豐富的零寬斷言

3. **向後兼容**
    - 可以作為 `re` 的替代品
    - API 基本相同

### 安裝

```bash
pip install regex
```

或使用 poetry（GlocalText 項目）：

```bash
poetry add regex
```

當前項目使用版本：`^2025.10.23`（見 `pyproject.toml`）

## 參考資源

-   **regex 庫 PyPI**: https://pypi.org/project/regex/
-   **regex 庫 GitHub**: https://github.com/mrabarnett/mrab-regex
-   **Python re 文檔**: https://docs.python.org/3/library/re.html
-   **正則表達式語法**: https://www.regular-expressions.info/

## 故障排除

### Pylance 警告

如果 IDE 顯示 `"search" 不是模組 "regex" 的已知屬性`，這是靜態分析工具的誤報。`regex` 庫在運行時動態提供這些屬性，測試會正常執行。

### 測試失敗

如果測試失敗，請檢查：

1. **regex 庫是否已安裝**

    ```bash
    pip show regex
    ```

2. **版本兼容性**

    ```bash
    pip list | grep regex
    ```

3. **運行詳細模式查看錯誤**
    ```bash
    pytest regex_tests/test_substitution.py::test_who_are_replacement_in_shell_command -v -s
    ```

## 維護建議

1. **添加新測試**：當發現新的邊界情況或用戶報告問題時，添加相應的測試案例
2. **保持更新**：當 regex 庫更新時，驗證所有測試仍然通過
3. **文檔同步**：新增測試時更新本 README
4. **回歸測試**：任何 bug 修復都應該添加對應的回歸測試

## 貢獻

添加新測試時，請遵循：

1. 清晰的測試函數名稱（`test_<描述>`）
2. 完整的文檔字符串說明測試目的
3. 包含正面和負面測試案例
4. 使用有意義的測試數據
5. 添加註釋解釋複雜的正則表達式

---

**最後更新**：2025-11-07  
**維護者**：GlocalText 開發團隊
