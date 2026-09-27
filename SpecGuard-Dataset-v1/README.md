# SpecGuard Benchmark Dataset v1

Purpose:
Controlled training/validation/testing benchmark for the SpecGuard offline engineering-document inspection system.

Contents:
- 30 clean engineering documents (Mechanical, Electrical, Chemical, QA/QC)
- 330 total controlled PDFs including 300 defective variants
- 11 defect families
- OCR benchmark samples
- 14 tolerance-index cases
- Ground-truth findings with page and PDF-coordinate bounding boxes where applicable
- Leakage-safe train/validation/test manifests

Defect families:
SPELLING, GRAMMAR, FORMATTING, TOC, FIGURE_REFERENCE, TABLE_VALUE,
DOCUMENT_CONTROL, NUMBERING, MISSING_CONTENT, CONTRADICTION, MIXED

Important:
This is a synthetic controlled benchmark. It is intended to validate SpecGuard's
detection, localization, severity/category classification, viewer navigation,
highlighting, and tolerance calculations. It should not be represented as a
replacement for a large real-world engineering corpus.

Suggested evaluation:
1. Run SpecGuard on the clean documents: expected zero intentional findings.
2. Run each defective variant.
3. Match findings by category, page, text, and bounding-box IoU.
4. Check false positives on clean documents.
5. Test Finding Details -> SHOW IN DOCUMENT.
6. Test tolerance calculations independently against 05_Ground_Truth.
7. Keep test documents isolated from training/tuning.

Default illustrative severity weights:
CRITICAL=10, HIGH=5, MEDIUM=2, LOW=0.5, INFORMATIONAL=0.
The application may use different configured weights; tolerance ground truth should
therefore be treated as a reference fixture, not a hard-coded product policy.

Dataset seed: 42
Generated: 2026-09-27
