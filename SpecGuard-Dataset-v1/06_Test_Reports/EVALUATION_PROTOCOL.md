# Evaluation Protocol

## Detection
- True Positive: expected defect is detected with correct category.
- False Positive: finding reported on a clean control document or outside expected defect scope.
- False Negative: expected defect not detected.

## Localization
For findings with bbox:
- page must match ground truth
- calculate Intersection over Union (IoU)
- recommended pass threshold for localization QA: IoU >= 0.50
- exact-coordinate tests should also inspect visual alignment manually

## Text
Compare detected_text against expected_text using normalized string comparison,
then allow domain-specific OCR tolerance for OCR benchmark cases.

## Severity
Verify configured severity matches the ground-truth fixture.

## Viewer
For every localized finding:
finding -> Finding Details -> SHOW IN DOCUMENT -> correct page -> correct
highlight/marker -> normal scrolling remains available.

## Clean controls
All clean documents are negative controls for intentional defects.

## Tolerance
Do not hard-code the example weights. Read the configured weights from SpecGuard,
then compare the application's calculated value to a separately calculated expected
value using the same configuration.
