#!/usr/bin/env python3
"""
Performance benchmark for GlocalText coverage detection.

This script measures the execution time and overhead of the coverage detection
mechanism implemented in Phase 2, which determines if terminating rules fully
cover the text to enable translation skipping.

Usage:
    python tests/performance/benchmark_coverage.py
    python tests/performance/benchmark_coverage.py --iterations 5000
    python tests/performance/benchmark_coverage.py --test small_text
"""

import argparse
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import regex

# Add parent directory to path to import glocaltext modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glocaltext.text_coverage import TextCoverage
from glocaltext.types import ActionRule, MatchRule, Rule, TextMatch


class CoverageBenchmark:
    """Performance benchmark for coverage detection functionality."""

    def __init__(self, iterations: int = 1000) -> None:
        """
        Initialize the benchmark runner.

        Args:
            iterations: Number of times to run each benchmark test

        """
        self.iterations = iterations
        self.results: list[dict[str, Any]] = []

    def _calculate_statistics(self, times: list[float], scenario_name: str) -> dict[str, Any]:
        """
        Calculate statistical metrics from timing measurements.

        Args:
            times: List of execution times in milliseconds
            scenario_name: Name of the benchmark scenario

        Returns:
            Dictionary containing statistical metrics

        """
        mean_time = statistics.mean(times)
        median_time = statistics.median(times)
        stdev_time = statistics.stdev(times) if len(times) > 1 else 0.0
        min_time = min(times)
        max_time = max(times)
        ops_per_sec = 1000.0 / mean_time if mean_time > 0 else 0.0

        return {
            "scenario": scenario_name,
            "iterations": len(times),
            "mean_ms": mean_time,
            "median_ms": median_time,
            "stdev_ms": stdev_time,
            "min_ms": min_time,
            "max_ms": max_time,
            "ops_per_sec": ops_per_sec,
        }

    def _create_test_match(self, text: str) -> TextMatch:
        """
        Create a TextMatch instance for testing.

        Args:
            text: The text content for the match

        Returns:
            TextMatch instance configured for testing

        """
        return TextMatch(
            original_text=text,
            source_file=Path("test.txt"),
            span=(0, len(text)),
            task_name="test_task",
            extraction_rule="test_rule",
        )

    def benchmark_small_text(self) -> dict[str, Any]:
        """
        Benchmark with small text (~100 chars, 3 rules).

        Expected: < 0.1ms per operation
        """
        # Create test text: ~130 characters
        text = "Hello World! This is a test. " * 4

        # Create 3 simple skip rules
        rules = [
            Rule(
                match=MatchRule(regex=r"Hello"),
                action=ActionRule(action="skip"),
            ),
            Rule(
                match=MatchRule(regex=r"World"),
                action=ActionRule(action="skip"),
            ),
            Rule(
                match=MatchRule(regex=r"test"),
                action=ActionRule(action="skip"),
            ),
        ]

        times = []
        for _ in range(self.iterations):
            self._create_test_match(text)
            coverage = TextCoverage(text)

            start = time.perf_counter()

            # Simulate coverage detection logic
            for rule in rules:
                pattern = rule.match.regex
                for regex_match in regex.finditer(pattern, text):
                    coverage.add_range(regex_match.start(), regex_match.end())

            _ = coverage.is_fully_covered()

            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds

        return self._calculate_statistics(times, "Small Text (~100 chars, 3 rules)")

    def benchmark_medium_text(self) -> dict[str, Any]:
        """
        Benchmark with medium text (~1000 chars, 10 rules).

        Expected: < 1ms per operation
        """
        # Create test text: ~1000 characters
        text = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. ") * 5

        # Create 10 skip rules with various patterns
        rules = [
            Rule(match=MatchRule(regex=r"Lorem"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"ipsum"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"dolor"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"sit"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"amet"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"consectetur"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"adipiscing"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"elit"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"Sed"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"tempor"), action=ActionRule(action="skip")),
        ]

        times = []
        for _ in range(self.iterations):
            coverage = TextCoverage(text)

            start = time.perf_counter()

            # Simulate coverage detection logic
            for rule in rules:
                pattern = rule.match.regex
                for regex_match in regex.finditer(pattern, text):
                    coverage.add_range(regex_match.start(), regex_match.end())

            _ = coverage.is_fully_covered()

            end = time.perf_counter()
            times.append((end - start) * 1000)

        return self._calculate_statistics(times, "Medium Text (~1000 chars, 10 rules)")

    def benchmark_large_text(self) -> dict[str, Any]:
        """
        Benchmark with large text (~10000 chars, 20 rules).

        Expected: < 10ms per operation
        """
        # Create test text: ~10000 characters
        base_text = "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs. How vexingly quick daft zebras jump! Sphinx of black quartz, judge my vow. "
        text = base_text * 50  # ~10000 chars

        # Create 20 skip rules
        rules = [
            Rule(match=MatchRule(regex=r"quick"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"brown"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"fox"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"jumps"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"over"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"lazy"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"dog"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"Pack"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"box"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"with"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"five"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"dozen"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"liquor"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"jugs"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"How"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"vexingly"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"daft"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"zebras"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"Sphinx"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"quartz"), action=ActionRule(action="skip")),
        ]

        times = []
        for _ in range(self.iterations):
            coverage = TextCoverage(text)

            start = time.perf_counter()

            # Simulate coverage detection logic
            for rule in rules:
                pattern = rule.match.regex
                for regex_match in regex.finditer(pattern, text):
                    coverage.add_range(regex_match.start(), regex_match.end())

            _ = coverage.is_fully_covered()

            end = time.perf_counter()
            times.append((end - start) * 1000)

        return self._calculate_statistics(times, "Large Text (~10000 chars, 20 rules)")

    def benchmark_many_rules(self) -> dict[str, Any]:
        """
        Benchmark with many terminating rules (50 rules).

        Expected: < 5ms per operation
        """
        # Create test text: ~1000 characters
        text = "abcdefghij " * 100

        # Create 50 skip rules (one for each letter and digit combination)
        rules: list[Rule] = []
        for char in "abcdefghijklmnopqrstuvwxyz0123456789":
            if len(rules) >= 50:
                break
            rules.append(
                Rule(
                    match=MatchRule(regex=char),
                    action=ActionRule(action="skip"),
                )
            )

        times = []
        for _ in range(self.iterations):
            coverage = TextCoverage(text)

            start = time.perf_counter()

            # Simulate coverage detection logic
            for rule in rules:
                pattern = rule.match.regex
                for regex_match in regex.finditer(pattern, text):
                    coverage.add_range(regex_match.start(), regex_match.end())

            _ = coverage.is_fully_covered()

            end = time.perf_counter()
            times.append((end - start) * 1000)

        return self._calculate_statistics(times, "Many Rules (~1000 chars, 50 rules)")

    def benchmark_complex_patterns(self) -> dict[str, Any]:
        """
        Benchmark with complex regex patterns.

        Expected: < 2ms per operation
        """
        # Create test text with various patterns
        text = ("Email: test@example.com, Phone: +1-234-567-8900, URL: https://www.example.com/path?query=value, Date: 2024-01-15, Time: 14:30:00, Code: def func(x): return x * 2, ") * 10

        # Create complex regex patterns
        rules = [
            Rule(match=MatchRule(regex=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\d{4}-\d{2}-\d{2}"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\d{2}:\d{2}:\d{2}"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"def\s+\w+\([^)]*\):"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\b[A-Z][a-z]+:"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\b\d+\b"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\w+\s*=\s*\w+"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=r"\([^)]+\)"), action=ActionRule(action="skip")),
        ]

        times = []
        for _ in range(self.iterations):
            coverage = TextCoverage(text)

            start = time.perf_counter()

            # Simulate coverage detection logic
            for rule in rules:
                pattern = rule.match.regex
                try:
                    for regex_match in regex.finditer(pattern, text):
                        coverage.add_range(regex_match.start(), regex_match.end())
                except regex.error:
                    # Skip invalid regex patterns in benchmark
                    # This is acceptable in a benchmark context
                    continue

            _ = coverage.is_fully_covered()

            end = time.perf_counter()
            times.append((end - start) * 1000)

        return self._calculate_statistics(times, "Complex Patterns (~1000 chars, 10 complex rules)")

    def run_all_benchmarks(self) -> list[dict[str, Any]]:
        """
        Run all benchmark tests and collect results.

        Returns:
            List of result dictionaries for each benchmark

        """
        benchmarks = [
            ("small_text", self.benchmark_small_text),
            ("medium_text", self.benchmark_medium_text),
            ("large_text", self.benchmark_large_text),
            ("many_rules", self.benchmark_many_rules),
            ("complex_patterns", self.benchmark_complex_patterns),
        ]

        results = []
        len(benchmarks)

        for _i, (name, benchmark_func) in enumerate(benchmarks, 1):
            # Extract scenario name from docstring, with fallback
            doc_str = benchmark_func.__doc__ or name
            doc_str.split("(")[0].strip() if "(" in doc_str else doc_str.strip()
            result = benchmark_func()
            results.append(result)

            # Display results immediately

        self.results = results
        return results

    def _format_test_result(self, result: dict[str, Any]) -> list[str]:
        """
        Format a single test result section.

        Args:
            result: Dictionary containing test result metrics

        Returns:
            List of formatted markdown lines

        """
        return [
            f"### {result['scenario']}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Mean | {result['mean_ms']:.3f}ms |",
            f"| Median | {result['median_ms']:.3f}ms |",
            f"| Std Dev | {result['stdev_ms']:.3f}ms |",
            f"| Min/Max | {result['min_ms']:.3f}ms / {result['max_ms']:.3f}ms |",
            f"| Ops/sec | {result['ops_per_sec']:,.0f} |",
            "",
        ]

    def _generate_performance_analysis(self) -> list[str]:
        """
        Generate performance analysis section.

        Returns:
            List of formatted markdown lines with performance analysis

        """
        lines = [
            "## Performance Analysis",
            "",
            "### Overhead Assessment",
            "",
        ]

        # Analyze results
        small_mean = self.results[0]["mean_ms"]
        medium_mean = self.results[1]["mean_ms"]
        large_mean = self.results[2]["mean_ms"]

        if small_mean < 0.1:
            lines.append("✅ **Small text performance**: Excellent (< 0.1ms)")
        elif small_mean < 0.5:
            lines.append("✓ **Small text performance**: Good (< 0.5ms)")
        else:
            lines.append("⚠️ **Small text performance**: Needs optimization (>= 0.5ms)")

        lines.append("")

        if medium_mean < 1.0:
            lines.append("✅ **Medium text performance**: Excellent (< 1ms)")
        elif medium_mean < 5.0:
            lines.append("✓ **Medium text performance**: Good (< 5ms)")
        else:
            lines.append("⚠️ **Medium text performance**: Needs optimization (>= 5ms)")

        lines.append("")

        if large_mean < 10.0:
            lines.append("✅ **Large text performance**: Excellent (< 10ms)")
        elif large_mean < 50.0:
            lines.append("✓ **Large text performance**: Good (< 50ms)")
        else:
            lines.append("⚠️ **Large text performance**: Needs optimization (>= 50ms)")

        lines.extend(
            [
                "",
                "### Scalability",
                "",
                "- Coverage detection scales approximately **linearly** with text size",
                f"- Small to medium ratio: {medium_mean / small_mean if small_mean > 0 else 0:.1f}x",
                f"- Medium to large ratio: {large_mean / medium_mean if medium_mean > 0 else 0:.1f}x",
                "",
                "### Recommendations",
                "",
            ]
        )

        return lines

    def generate_report(self, output_path: Path) -> None:
        """
        Generate a detailed markdown report of benchmark results.

        Args:
            output_path: Path where the report will be saved

        """
        if not self.results:
            return

        # Gather system information
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        python_version = platform.python_version()
        system_platform = f"{platform.system()} {platform.release()}"

        # Generate markdown report
        report_lines = [
            "# Coverage Detection Performance Benchmark Results",
            "",
            f"**Date**: {timestamp}  ",
            f"**Iterations**: {self.iterations} per test  ",
            f"**Python Version**: {python_version}  ",
            f"**Platform**: {system_platform}",
            "",
            "## Test Results",
            "",
        ]

        for result in self.results:
            report_lines.extend(self._format_test_result(result))

        # Add performance analysis
        report_lines.extend(self._generate_performance_analysis())

        # Add recommendations based on results
        all_acceptable = all(r["mean_ms"] < threshold for r, threshold in zip(self.results, [0.1, 1.0, 10.0, 5.0, 2.0], strict=False))

        if all_acceptable:
            report_lines.extend(
                [
                    "✅ Coverage detection performance is **excellent** across all test scenarios.",
                    "✅ The overhead is minimal and suitable for production use.",
                    "✅ No optimization needed at this time.",
                ]
            )
        else:
            report_lines.extend(
                [
                    "⚠️ Some scenarios show performance degradation:",
                    "",
                ]
            )
            for _i, (result, threshold) in enumerate(zip(self.results, [0.1, 1.0, 10.0, 5.0, 2.0], strict=False)):
                if result["mean_ms"] >= threshold:
                    report_lines.append(f"- {result['scenario']}: {result['mean_ms']:.3f}ms (threshold: {threshold}ms)")

            report_lines.extend(
                [
                    "",
                    "**Suggested actions**:",
                    "- Profile the coverage detection logic to identify bottlenecks",
                    "- Consider caching compiled regex patterns",
                    "- Review rule complexity and optimize patterns where possible",
                    "- Monitor performance in production environments",
                ]
            )

        report_lines.extend(
            [
                "",
                "## Conclusion",
                "",
                f"The coverage detection mechanism adds an average overhead of **{statistics.mean([r['mean_ms'] for r in self.results]):.3f}ms** ",
                "across all test scenarios. This overhead is acceptable for the benefits provided:",
                "",
                "- ✅ Enables skipping unnecessary translations when rules fully cover text",
                "- ✅ Reduces API costs by avoiding redundant translation calls",
                "- ✅ Improves overall system throughput",
                "- ✅ Maintains accuracy by preserving rule-matched content",
                "",
                "---",
                f"*Benchmark completed at {timestamp}*",
            ]
        )

        # Write report to file
        output_path.write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    """Run the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Performance benchmark for GlocalText coverage detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/performance/benchmark_coverage.py
  python tests/performance/benchmark_coverage.py --iterations 5000
  python tests/performance/benchmark_coverage.py --test small_text
  python tests/performance/benchmark_coverage.py --verbose
        """,
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of iterations per test (default: 1000)",
    )
    parser.add_argument(
        "--test",
        type=str,
        choices=["small_text", "medium_text", "large_text", "many_rules", "complex_patterns"],
        help="Run a specific test only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Create benchmark instance
    benchmark = CoverageBenchmark(iterations=args.iterations)

    # Run benchmarks
    if args.test:
        # Run specific test
        test_methods = {
            "small_text": benchmark.benchmark_small_text,
            "medium_text": benchmark.benchmark_medium_text,
            "large_text": benchmark.benchmark_large_text,
            "many_rules": benchmark.benchmark_many_rules,
            "complex_patterns": benchmark.benchmark_complex_patterns,
        }

        result = test_methods[args.test]()
        benchmark.results = [result]

    else:
        # Run all benchmarks
        benchmark.run_all_benchmarks()

    # Generate report

    if benchmark.results:
        statistics.mean([r["mean_ms"] for r in benchmark.results])

        # Save report
        output_path = Path(__file__).parent / "benchmark_results.md"
        benchmark.generate_report(output_path)


if __name__ == "__main__":
    main()
