# Performance Benchmarks

## Overview

This directory contains performance benchmarks for GlocalText coverage detection functionality.

The benchmarks measure the execution time and overhead of the coverage detection mechanism implemented in Phase 2, which tracks rule coverage to determine if translation can be skipped.

## Running Benchmarks

### Quick Start

```bash
python tests/performance/benchmark_coverage.py
```

### Custom Iterations

Run with a specific number of iterations (default is 1000):

```bash
python tests/performance/benchmark_coverage.py --iterations 5000
```

### Specific Tests

Run only specific benchmark tests:

```bash
python tests/performance/benchmark_coverage.py --test small_text
python tests/performance/benchmark_coverage.py --test medium_text
python tests/performance/benchmark_coverage.py --test large_text
python tests/performance/benchmark_coverage.py --test many_rules
python tests/performance/benchmark_coverage.py --test complex_patterns
```

### Verbose Output

Enable detailed logging:

```bash
python tests/performance/benchmark_coverage.py --verbose
```

## Interpreting Results

### Performance Thresholds

-   **Mean < 0.1ms**: Excellent performance for small texts
-   **Mean < 1ms**: Good performance for medium texts
-   **Mean < 10ms**: Acceptable performance for large texts
-   **Mean > 10ms**: May require optimization

### Key Metrics

-   **Mean**: Average execution time across all iterations
-   **Median**: Middle value, less affected by outliers
-   **Std Dev**: Consistency of performance (lower is better)
-   **Min/Max**: Best and worst case scenarios
-   **Ops/sec**: Throughput (operations per second)

## Test Scenarios

### Small Text Benchmark

-   **Text size**: ~100 characters
-   **Rules**: 3-5 skip rules
-   **Expected**: < 0.1ms per operation
-   **Use case**: Individual word or short phrase translation

### Medium Text Benchmark

-   **Text size**: ~1000 characters
-   **Rules**: 5-10 skip rules
-   **Expected**: < 1ms per operation
-   **Use case**: Paragraph or section translation

### Large Text Benchmark

-   **Text size**: ~10000 characters
-   **Rules**: 10-20 skip rules
-   **Expected**: < 10ms per operation
-   **Use case**: Full document or page translation

### Many Rules Benchmark

-   **Text size**: ~1000 characters
-   **Rules**: 50 skip rules
-   **Expected**: < 5ms per operation
-   **Use case**: Complex rule sets with many patterns

### Complex Patterns Benchmark

-   **Text size**: ~1000 characters
-   **Rules**: 10 complex regex patterns
-   **Expected**: < 2ms per operation
-   **Use case**: Advanced regex with backreferences and lookaheads

## Output Files

### Console Output

Real-time progress and results are displayed in the console with:

-   Unicode box-drawing characters for visual structure
-   Color-coded status indicators (when supported)
-   Progress bars for long-running tests

### benchmark_results.md

Detailed results are automatically saved to `benchmark_results.md` after each run:

-   Timestamp and environment information
-   Complete metrics for each test scenario
-   Performance analysis and recommendations
-   Historical comparison (when available)

## Adding New Benchmarks

To add a new benchmark test:

1. **Create a new method** in the `CoverageBenchmark` class:

```python
def benchmark_your_scenario(self) -> Dict[str, Any]:
    """
    Benchmark description.

    Expected: < Xms per operation
    """
    text = "Your test text..."
    rules = [...]  # Your test rules

    times = []
    for _ in range(self.iterations):
        start = time.perf_counter()
        # Your benchmark code here
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return self._calculate_statistics(times, "Your Scenario Name")
```

2. **Register the test** in `run_all_benchmarks()`:

```python
results.append(self.benchmark_your_scenario())
```

3. **Update this README** with the new test scenario documentation.

## Performance Considerations

### What Affects Performance?

-   **Text length**: Linear relationship with execution time
-   **Number of rules**: Linear relationship with execution time
-   **Regex complexity**: Exponential impact in worst cases
-   **Match density**: More matches = more coverage tracking

### Optimization Tips

-   Use simple patterns when possible
-   Avoid catastrophic backtracking in regex
-   Consider rule ordering (most frequent matches first)
-   Cache compiled regex patterns

## Troubleshooting

### Slow Performance

If benchmarks show degraded performance:

1. Check for regex catastrophic backtracking
2. Verify rule count is reasonable (< 100)
3. Profile individual rules to identify bottlenecks
4. Consider text size and splitting strategies

### Inconsistent Results

High standard deviation may indicate:

-   System resource contention
-   JIT compilation effects (first-run penalty)
-   Memory allocation patterns
-   Background processes

**Solution**: Increase iterations or run in isolated environment.

## Related Documentation

-   Phase 2 Implementation: `../../phase2_completion_report.md`
-   Coverage Detection: `../../src/glocaltext/coverage.py`
-   Integration Tests: `../../phase2_integration_testing.md`
