<!-- You cannot delete 3 items in the part of the table of contents, Introduction, Contributing, License -->

# GlocalText

GlocalText 是一個功能強大的命令列工具，旨在自動化和簡化軟體本地化流程。它能從您的原始碼中提取字串，使用各種 AI 和機器翻譯服務進行翻譯，並編譯出一個完全翻譯好的專案版本。

其主要特色是**雙向同步工作流程**，允許您手動優化機器翻譯的結果，並將您的變更同步回系統中，確保您的編輯得以保存和重複使用。

---

## 目錄

- [簡介](#簡介)
- [功能特色](#功能特色)
- [安裝](#安裝)
- [快速入門](#快速入門)
- [指令參考](#指令參考)
- [設定](#設定)
- [貢獻](#貢獻)
- [授權](#授權)

---

## 簡介

GlocalText 是一個功能強大的命令列工具，旨在自動化和簡化軟體本地化流程。它能從您的原始碼中提取字串，使用各種 AI 和機器翻譯服務進行翻譯，並編譯出一個完全翻譯好的專案版本。

其主要特色是**雙向同步工作流程**，允許您手動優化機器翻譯的結果，並將您的變更同步回系統中，確保您的編輯得以保存和重複使用。

## 功能特色

- **自動化字串提取**：使用可自訂的正規表示式規則，在任何類型的原始碼中尋找使用者可見的字串。
- **支援多種翻譯服務**：整合了如 Gemini、OpenAI 和 Ollama 等現代 AI 服務，以及 Google 翻譯等標準服務。
- **雙向同步工作流程**：手動編輯翻譯後的檔案，並使用 `sync` 指令將您的變更合併回翻譯快取中。您的優化永不遺失。
- **差異化翻譯**：智慧地僅翻譯新增或修改過的字串，節省時間和成本。
- **狀態管理**：追蹤檔案版本以偵測原始檔案和本地化檔案之間的變更和潛在衝突。
- **設定優於慣例**：透過簡單的 YAML 檔案進行高度自訂。

## 安裝

使用 pip 安裝 GlocalText：

```bash
pip install glocaltext
```

## 快速入門

這是一個完整的工作流程範例。

### 1. 初始化您的專案

導覽至您專案的根目錄並執行：

```bash
glocaltext init
```

這會在 `.ogos` 目錄中建立兩個設定檔：

- `i18n-rules.yaml`：定義尋找待翻譯字串的規則。
- `l10n-rules.yaml`：設定您的目標語言和翻譯服務提供者（例如 Gemini、OpenAI）。

### 2. 設定您的規則

- **編輯 `i18n-rules.yaml`** 來定義從您的程式碼中提取字串的正規表示式模式。
- **編輯 `l10n-rules.yaml`** 來設定您的目標語言並配置您選擇的翻譯服務提供者，包括 API 金鑰。

### 3. 首次執行：機器翻譯

執行本地化流程：

```bash
glocaltext run .
```

GlocalText 將會：

1. 掃描您的原始碼以尋找字串。
2. 將新的字串傳送給您選擇的翻譯服務提供者。
3. 在 `.ogos/localized/` 中建立一個翻譯好的專案副本。

### 4. 手動優化

瀏覽 `.ogos/localized/` 目錄中的檔案。您現在可以手動編輯這些檔案中的翻譯文字，以提高品質、修正特定情境的問題，或符合您品牌的語氣。

例如，您可能會將一個翻譯字串從 `"申請開始..."` 改為 `"應用程式啟動中..."`。

### 5. 同步您的變更

在進行手動編輯後，將它們同步回 GlocalText 快取：

```bash
glocaltext sync .
```

此指令會從 `localized` 目錄中讀取您的變更，並更新翻譯快取，將您的編輯儲存為 `manual_override`。

### 6. 後續執行

現在，當您再次執行 `glocaltext run .`（例如，在新增原始碼後），編譯器將會使用您已同步的手動覆寫，而不是原始的機器翻譯，確保您的優化始終被保留。

## 指令參考

### `glocaltext init`

在 `.ogos` 目錄中初始化設定檔。

### `glocaltext run [PATH]`

執行主要的本地化工作流程：提取、翻譯和編譯。

- **`PATH`**：要處理的專案目錄路徑（預設為目前目錄）。
- **`--force`, `-f`**：強制重新翻譯所有字串，忽略快取。
- **`--debug`, `-d`**：啟用詳細的偵錯日誌。

### `glocaltext sync [PATH]`

將 `localized` 目錄中的手動變更同步回翻譯快取。

- **`PATH`**：要同步的專案目錄路徑（預設為目前目錄）。
- **`--debug`, `-d`**：啟用詳細的偵錯日誌。

## 設定

### `i18n-rules.yaml`

控制如何尋找字串（國際化）。

```yaml
source:
  include:
    - "**/*.py" # 要包含的檔案的 Glob 模式
  exclude:
    - "tests/*" # 要排除的檔案的 Glob 模式
capture_rules:
  - pattern: '_\("(.*?)"\)' # 尋找字串的正規表示式
    capture_group: 1 # 包含文字的正規表示式捕獲組
ignore_rules:
  - pattern: "<code>.*?</code>" # 要忽略的整個區塊的正規表示式
```

### `l10n-rules.yaml`

控制如何翻譯字串（本地化）。

```yaml
translation_settings:
  source_lang: "en"
  target_lang: ["ja", "zh-TW"]
  provider: "gemini" # gemini, openai, ollama, 或 google

provider_configs:
  gemini:
    model: "gemini-1.5-flash"
    api_key: "YOUR_GEMINI_API_KEY"
  openai:
    model: "gpt-4o"
    api_key: "YOUR_OPENAI_API_KEY"
  # ... 其他提供者的設定

glossary:
  # 不應被翻譯的術語
  "GlocalText": "GlocalText"

protection_rules:
  # 保護不被翻譯的子字串的正規表示式模式（例如，變數）
  - "{.*?}"
```

## 貢獻

1. Fork 該儲存庫
2. 建立一個功能分支
3. 提交您的變更
4. 開啟一個 Pull Request

## 授權

本儲存庫採用 [MIT 授權](https://opensource.org/license/MIT)。

---

© 2025 [OG-Open-Source](https://github.com/OG-Open-Source). All rights reserved.
