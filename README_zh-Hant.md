# GlocalText：無縫的軟體本地化工具

GlocalText 是一個功能強大的命令列工具，旨在自動化並簡化軟體本地化流程。它能從您的原始碼中提取字串，使用多種 AI 和機器翻譯服務進行翻譯，並編譯出一個包含完整翻譯的專案版本。

其核心特色是一個**「雙向同步」的工作流程**，允許您手動優化機器翻譯的結果，並將您的變更同步回系統中，確保您的編輯成果得以保存和重複使用。

## 功能特色

- **自動化字串提取**：使用可自訂的正規表示式 (regex) 規則，在任何類型的原始碼中尋找使用者可見的字串。
- **支援多種翻譯服務**：整合了現代化的 AI 服務，如 Gemini、OpenAI 和 Ollama，以及標準的 Google 翻譯服務。
- **雙向同步工作流程**：手動編輯翻譯後的檔案，然後使用 `sync` 指令將您的變更合併回翻譯快取中。您的優化成果永遠不會遺失。
- **差異化翻譯**：智慧地僅翻譯新的或已修改的字串，節省您的時間和成本。
- **狀態管理**：追蹤檔案版本以偵測原始碼與本地化檔案之間的變更和潛在衝突。
- **配置優於慣例**：透過簡單的 YAML 檔案即可進行高度自訂。

## 安裝

使用 pip 安裝 GlocalText：

```bash
pip install glocaltext
```

## 快速入門

這是一個完整的範例工作流程。

### 1. 初始化您的專案

移動到您專案的根目錄並執行：

```bash
glocaltext init
```

這會建立一個 `.ogos` 目錄，其中包含兩個設定檔：

- `i18n-rules.yaml`：定義尋找待翻譯字串的規則。
- `l10n-rules.yaml`：設定您的目標語言和翻譯服務商（例如 Gemini、OpenAI）。

### 2. 設定您的規則

- **編輯 `i18n-rules.yaml`** 來定義從您的程式碼中提取字串的正規表示式。
- **編輯 `l10n-rules.yaml`** 來設定您的目標語言，並配置您選擇的翻譯服務商，包含 API 金鑰。

### 3. 首次執行：機器翻譯

執行本地化流程：

```bash
glocaltext run .
```

GlocalText 將會：

1. 掃描您的原始碼以尋找字串。
2. 將新的字串傳送給您選擇的翻譯服務商。
3. 在 `.ogos/localized/` 目錄下建立一個已翻譯的專案複本。

### 4. 手動優化

瀏覽 `.ogos/localized/` 目錄中的檔案。您現在可以手動編輯這些檔案中的翻譯文字，以提高品質、修正特定情境下的問題，或使其符合您的品牌語氣。

例如，您可以將一個翻譯字串從 `"申請開始..."` 修改為 `"應用程式啟動中..."`。

### 5. 同步您的變更

在完成手動編輯後，將它們同步回 GlocalText 的快取中：

```bash
glocaltext sync .
```

此指令會讀取您在 `localized` 目錄中的變更，並更新翻譯快取，將您的編輯儲存為 `manual_override` (手動覆寫)。

### 6. 後續執行

現在，當您再次執行 `glocaltext run .` 時（例如，在您新增了原始碼之後），編譯器將會使用您已同步的手動覆寫內容，而不是原始的機器翻譯，確保您的優化成果總是被保留。

## 指令參考

### `glocaltext init`

在 `.ogos` 目錄中初始化設定檔。

### `glocaltext run [PATH]`

執行主要的本地化工作流程：提取、翻譯和編譯。

- **`PATH`**：要處理的專案目錄路徑（預設：目前目錄）。
- **`--force`, `-f`**：強制重新翻譯所有字串，忽略快取。
- **`--debug`, `-d`**：啟用詳細的偵錯日誌。

### `glocaltext sync [PATH]`

將 `localized` 目錄中的手動變更同步回翻譯快取。

- **`PATH`**：要同步的專案目錄路徑（預設：目前目錄）。
- **`--debug`, `-d`**：啟用詳細的偵錯日誌。

## 設定檔說明

### `i18n-rules.yaml`

控制如何尋找字串（國際化 - Internationalization）。

```yaml
source:
  include:
    - "**/*.py" # 要包含的檔案的 glob 模式
  exclude:
    - "tests/*" # 要排除的檔案的 glob 模式
rules:
  - pattern: '_\("(.*?)"\)' # 用於尋找字串的正規表示式
    capture_group: 1 # 包含文字的正規表示式捕獲組
```

### `l10n-rules.yaml`

控制如何翻譯字串（本地化 - Localization）。

```yaml
translation_settings:
  source_lang: "en"
  target_lang: ["ja", "zh-TW"]
  provider: "gemini" # 可選：gemini, openai, ollama, google

provider_configs:
  gemini:
    model: "gemini-1.5-flash"
    api_key: "您的_GEMINI_API_金鑰"
  openai:
    model: "gpt-4o"
    api_key: "您的_OPENAI_API_金鑰"
  # ... 其他服務商的設定

glossary:
  # 不應被翻譯的詞彙
  "GlocalText": "GlocalText"

protection_rules:
  # 用於保護不被翻譯的子字串的正規表示式（例如變數）
  - "{.*?}"
```

## 如何貢獻

歡迎任何形式的貢獻！請隨時提交 Pull Request 或開啟 Issue。

## 授權條款

本專案採用 MIT 授權。詳情請見 [LICENSE](LICENSE) 檔案。
