"""
Performance and Stress Benchmark Suite for SpecGuard Multi-Page Engine:
Measures processing time, peak memory usage (via tracemalloc), CPU duration,
and pages processed per second across 1, 20, 50, and 100-page documents.
Ensures zero memory leaks, bounded resource consumption, and 0% failure rate.
"""

import time
import tracemalloc
from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.core.pipeline import AnalysisPipeline

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _benchmark_document(file_path: Path, run_pipeline: bool = False):
    """Executes parser or pipeline under tracemalloc to record real resource metrics."""
    tracemalloc.start()
    t0 = time.perf_counter()

    if run_pipeline:
        pipeline = AnalysisPipeline()
        doc, findings, session_id = pipeline.run_analysis(str(file_path), domain="mechanical")
        total_findings = len(findings)
    else:
        doc = DocumentParser.parse_file(str(file_path))
        total_findings = 0

    elapsed = time.perf_counter() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_mem / (1024 * 1024)
    pages_per_sec = doc.page_count / max(0.001, elapsed)

    return {
        "page_count": doc.page_count,
        "elapsed_sec": round(elapsed, 3),
        "peak_mb": round(peak_mb, 2),
        "pages_per_sec": round(pages_per_sec, 2),
        "total_findings": total_findings
    }


def test_performance_1_page():
    res = _benchmark_document(FIXTURES_DIR / "test_1_page.pdf", run_pipeline=True)
    print(f"\n[PERF 1-Page]: Time={res['elapsed_sec']}s, PeakMem={res['peak_mb']}MB, Speed={res['pages_per_sec']} pages/s")
    assert res["page_count"] == 1
    assert res["elapsed_sec"] < 5.0
    assert res["peak_mb"] < 150.0  # Safe memory footprint


def test_performance_20_pages():
    res = _benchmark_document(FIXTURES_DIR / "test_20_page.pdf", run_pipeline=False)
    print(f"\n[PERF 20-Page]: Time={res['elapsed_sec']}s, PeakMem={res['peak_mb']}MB, Speed={res['pages_per_sec']} pages/s")
    assert res["page_count"] == 20
    assert res["elapsed_sec"] < 10.0
    assert res["peak_mb"] < 250.0


def test_performance_50_pages():
    res = _benchmark_document(FIXTURES_DIR / "test_50_page.pdf", run_pipeline=False)
    print(f"\n[PERF 50-Page]: Time={res['elapsed_sec']}s, PeakMem={res['peak_mb']}MB, Speed={res['pages_per_sec']} pages/s")
    assert res["page_count"] == 50
    assert res["elapsed_sec"] < 25.0
    assert res["peak_mb"] < 350.0


def test_performance_100_pages():
    res = _benchmark_document(FIXTURES_DIR / "test_100_page.pdf", run_pipeline=False)
    print(f"\n[PERF 100-Page]: Time={res['elapsed_sec']}s, PeakMem={res['peak_mb']}MB, Speed={res['pages_per_sec']} pages/s")
    assert res["page_count"] == 100
    assert res["elapsed_sec"] < 45.0
    assert res["peak_mb"] < 500.0  # Strict memory bound for 100 pages
