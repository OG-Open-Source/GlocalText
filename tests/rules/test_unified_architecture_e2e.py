"""
端到端測試：驗證統一規則架構的正確性。.

此測試套件驗證階段 1-3 修復後的統一架構是否按設計意圖運作：
1. Replace 規則在原始文本上匹配並計入 Coverage
2. Protect 規則在原始文本上匹配並計入 Coverage
3. Skip 規則在原始文本上匹配並正確跳過
4. 所有規則統一檢查原始文本，規則之間不相互影響

Architecture Context:
- Phase 1 (Coverage Calculation): All rules check original_text
- Phase 2 (Translation Processing): Replace modifies text, Protect adds placeholders
- Replace rules must track coverage after Phase 1 fix (removed early return)
- Protect rules must check original_text after Phase 2 fix (dual-text architecture)
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.match_state import MatchLifecycle
from glocaltext.models import ExecutionContext
from glocaltext.processing import TerminatingRuleProcessor
from glocaltext.translate import process_matches
from glocaltext.translators.base import TranslationResult
from glocaltext.translators.mock_translator import MockTranslator
from glocaltext.types import ActionRule, MatchRule, Rule, Source, TextMatch, TranslationTask


class RecordingMockTranslator(MockTranslator):
    """擴展 MockTranslator 以記錄實際接收到的翻譯文本。."""

    def __init__(self, settings: ProviderSettings) -> None:
        """初始化帶記錄功能的 Mock 翻譯器。."""
        super().__init__(settings)
        self.received_texts: list[str] = []

    def translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None = None,
        *,
        debug: bool = False,
        prompts: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """記錄接收到的文本並返回 Mock 翻譯結果。."""
        self.received_texts.extend(texts)
        return super().translate(texts, target_language, source_language, debug=debug, prompts=prompts)


class TestUnifiedArchitectureE2E(unittest.TestCase):
    """端到端測試：驗證統一規則架構。."""

    def setUp(self) -> None:
        """設置測試環境。."""
        self.config = GlocalConfig()
        self.config.providers["mock"] = ProviderSettings()
        self.source_file = Path("test.txt")
        self.mock_translator = RecordingMockTranslator(ProviderSettings())

    def _process_with_pipeline(self, matches: list[TextMatch], task: TranslationTask) -> None:
        """
        使用完整的 Pipeline 階段處理 matches。.

        這個輔助方法模擬 Workflow Pipeline 的關鍵階段：
        1. TerminatingRuleProcessor - 執行 Replace/Skip/Protect 規則
        2. TranslationProcessor - 調用 process_matches() 進行翻譯

        Args:
            matches: 要處理的 TextMatch 列表
            task: 翻譯任務配置

        """
        # 創建執行上下文
        context = ExecutionContext(
            task=task,
            config=self.config,
            project_root=Path.cwd(),
            is_dry_run=False,
            is_incremental=False,
            is_debug=False,
        )
        context.all_matches = matches
        context.matches_to_translate = matches.copy()

        # 階段 3: 執行 Terminating Rules (Replace/Skip/Protect)
        terminating_processor = TerminatingRuleProcessor()
        terminating_processor.process(context)

        # 階段 4: 翻譯處理
        # 使用 context.matches_to_translate（已經過 TerminatingRuleProcessor 處理）
        with patch("glocaltext.translate.get_translator", return_value=self.mock_translator):
            process_matches(
                matches=context.matches_to_translate,
                task=task,
                config=self.config,
                debug=False,
            )

    def test_replace_rule_checks_original_text_and_tracks_coverage(self) -> None:
        """
        驗證 Replace 規則在原始文本上匹配並正確追蹤 Coverage。.

        測試場景：
        - 原始文本: "系統資訊(未知)"
        - Replace 規則: "未知" -> "Unknown"
        - 預期: 規則在原始文本上匹配並計入 Coverage
        - 預期: 翻譯器接收到處理後的文本 "系統資訊(Unknown)"
        """
        # 創建 Task with Replace 規則
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(
                    match=MatchRule(regex=r"未知"),
                    action=ActionRule(action="replace", value="Unknown"),
                ),
            ],
        )

        # 創建 TextMatch
        match = TextMatch(
            original_text="系統資訊(未知)",
            source_file=self.source_file,
            span=(0, 14),
            task_name="test_task",
            extraction_rule="test_rule",
        )

        # 處理 Match - 使用完整的 Pipeline
        self._process_with_pipeline([match], task)

        # 驗證：Match 應該被翻譯（因為 Replace 規則計入 Coverage）
        assert match.translated_text is not None, "Match 應該被翻譯"
        assert match.lifecycle == MatchLifecycle.TRANSLATED, "Lifecycle 應該是 TRANSLATED"

        # 驗證：翻譯器接收到處理後的文本
        assert len(self.mock_translator.received_texts) > 0, "翻譯器應該接收到文本"
        assert "系統資訊(Unknown)" in self.mock_translator.received_texts, "翻譯器應該接收到 Replace 規則處理後的文本"

    def test_protect_rule_checks_original_text_and_tracks_coverage(self) -> None:
        """
        驗證 Protect 規則在原始文本上匹配並正確追蹤 Coverage。.

        測試場景：
        - 原始文本: "CPU 使用率: 50%"
        - Protect 規則: 保護 "50%"
        - 預期: 規則在原始文本上匹配並計入 Coverage
        - 預期: 翻譯時保護的內容被替換為佔位符
        """
        # 創建 Task with Protect 規則
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(
                    match=MatchRule(regex=r"\d+%"),
                    action=ActionRule(action="protect"),
                ),
            ],
        )

        # 創建 TextMatch
        match = TextMatch(
            original_text="CPU 使用率: 50%",
            source_file=self.source_file,
            span=(0, 14),
            task_name="test_task",
            extraction_rule="test_rule",
        )

        # 處理 Match - 使用完整的 Pipeline
        self._process_with_pipeline([match], task)

        # 驗證：Match 應該被翻譯（因為 Protect 規則計入 Coverage）
        assert match.translated_text is not None, "Match 應該被翻譯"
        assert match.lifecycle == MatchLifecycle.TRANSLATED, "Lifecycle 應該是 TRANSLATED"

        # 驗證：最終結果中保護的內容被正確還原
        assert match.translated_text is not None  # Type narrowing
        assert "50%" in match.translated_text, "翻譯結果應該包含還原後的保護內容"

    def test_skip_rule_checks_original_text_with_full_coverage(self) -> None:
        """
        驗證 Skip 規則在原始文本上匹配並在完全覆蓋時跳過翻譯。.

        測試場景：
        - 原始文本: "192.168.1.1"
        - Skip 規則: 完全覆蓋 IP 地址
        - 預期: 規則在原始文本上匹配
        - 預期: 因為完全覆蓋而跳過翻譯
        """
        # 創建 Task with Skip 規則
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(
                    match=MatchRule(regex=r"^\d+\.\d+\.\d+\.\d+$"),
                    action=ActionRule(action="skip"),
                ),
            ],
        )

        # 創建 TextMatch
        match = TextMatch(
            original_text="192.168.1.1",
            source_file=self.source_file,
            span=(0, 11),
            task_name="test_task",
            extraction_rule="test_rule",
        )

        # 處理 Match - 使用完整的 Pipeline
        self._process_with_pipeline([match], task)

        # 驗證：Match 被標記為 SKIPPED（不調用翻譯 API）
        assert match.lifecycle == MatchLifecycle.SKIPPED, "Skip 規則完全覆蓋時應該標記為 SKIPPED"
        # translated_text 應該保留原始文本（用於寫回文件）
        assert match.translated_text == "192.168.1.1", "SKIPPED match 應該保留原始文本"

        # 驗證：翻譯器不應該接收到任何文本
        assert len(self.mock_translator.received_texts) == 0, "Skip 規則完全覆蓋時翻譯器不應該接收到任何文本"

    def test_skip_rule_partial_coverage_does_not_skip(self) -> None:
        """
        驗證 Skip 規則部分覆蓋時不跳過翻譯。.

        測試場景：
        - 原始文本: "伺服器 IP: 192.168.1.1"
        - Skip 規則: 只覆蓋 IP 部分
        - 預期: 規則在原始文本上匹配
        - 預期: 因為只是部分覆蓋，不跳過翻譯
        """
        # 創建 Task with Skip 規則（只匹配 IP，不匹配整個文本）
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(
                    match=MatchRule(regex=r"\d+\.\d+\.\d+\.\d+"),
                    action=ActionRule(action="skip"),
                ),
            ],
        )

        # 創建 TextMatch
        match = TextMatch(
            original_text="伺服器 IP: 192.168.1.1",
            source_file=self.source_file,
            span=(0, 20),
            task_name="test_task",
            extraction_rule="test_rule",
        )

        # 處理 Match - 使用完整的 Pipeline
        self._process_with_pipeline([match], task)

        # 驗證：Match 應該被翻譯（因為 Skip 規則只部分覆蓋）
        assert match.translated_text is not None, "Skip 規則部分覆蓋時 Match 應該被翻譯"

    def test_replace_and_protect_rules_both_check_original_text(self) -> None:
        """
        驗證 Replace 和 Protect 規則同時存在時都檢查原始文本。.

        測試場景：
        - 原始文本: "CPU 使用率: 50% (未知狀態)"
        - Replace 規則: "未知" -> "Unknown"
        - Protect 規則: 保護 "50%"
        - 預期: 兩個規則都在原始文本上匹配
        - 預期: Replace 先處理，Protect 在處理後的文本上應用保護
        """
        # 創建 Task with Replace 和 Protect 規則
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(
                    match=MatchRule(regex=r"未知"),
                    action=ActionRule(action="replace", value="Unknown"),
                ),
                Rule(
                    match=MatchRule(regex=r"\d+%"),
                    action=ActionRule(action="protect"),
                ),
            ],
        )

        # 創建 TextMatch
        match = TextMatch(
            original_text="CPU 使用率: 50% (未知狀態)",
            source_file=self.source_file,
            span=(0, 24),
            task_name="test_task",
            extraction_rule="test_rule",
        )

        # 處理 Match - 使用完整的 Pipeline
        self._process_with_pipeline([match], task)

        # 驗證：Match 應該被翻譯
        assert match.translated_text is not None, "Match 應該被翻譯"

        # 驗證：最終結果包含 Replace 的修改和 Protect 的還原
        assert match.translated_text is not None  # Type narrowing
        assert "Unknown" in match.translated_text, "應該包含 Replace 規則的替換結果"
        assert "50%" in match.translated_text, "應該包含 Protect 規則還原的內容"

    def test_all_rules_contribute_to_coverage_calculation(self) -> None:
        """
        驗證所有規則類型都正確計入 Coverage 計算。.

        測試場景：
        - 原始文本: "系統: OK (100%)"
        - Replace 規則: "OK" -> "SUCCESS"
        - Protect 規則: 保護 "100%"
        - Skip 規則: 嘗試跳過 "系統"
        - 預期: 所有規則都參與 Coverage 計算
        - 預期: Coverage 總和影響是否跳過翻譯的決策
        """
        # 創建帶有多種規則的 Task
        task = TranslationTask(
            name="test_all_rules_coverage",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(
                    match=MatchRule(regex=r"OK"),
                    action=ActionRule(action="replace", value="SUCCESS"),
                ),
                Rule(
                    match=MatchRule(regex=r"\d+%"),
                    action=ActionRule(action="protect"),
                ),
                Rule(
                    match=MatchRule(regex=r"系統"),
                    action=ActionRule(action="skip"),
                ),
            ],
        )

        # 創建 TextMatch
        match = TextMatch(
            original_text="系統: OK (100%)",
            source_file=self.source_file,
            span=(0, 14),
            task_name="test_task",
            extraction_rule="test_rule",
        )

        # 處理 Match - 使用完整的 Pipeline
        self._process_with_pipeline([match], task)

        # 驗證：Match 應該被翻譯（因為 Skip 規則未完全覆蓋）
        assert match.translated_text is not None, "所有規則組合應該允許翻譯繼續"

        # 驗證：最終結果反映了所有規則的效果
        assert match.translated_text is not None  # Type narrowing
        assert "SUCCESS" in match.translated_text, "應該包含 Replace 規則的替換"
        assert "100%" in match.translated_text, "應該包含 Protect 規則還原的內容"


if __name__ == "__main__":
    unittest.main()
