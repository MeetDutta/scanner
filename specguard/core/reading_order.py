"""
Geometric Reading Order Reconstruction Engine.

Reconstructs human reading order using geometric layout analysis.
Correctly handles:
- Single-column documents
- Two-column documents (IEEE style)
- Multi-column documents
- Mixed layouts (e.g., full-width title/abstract, 2-column body, full-width figure/table spanning columns, resuming 2 columns)
- Sidebars and margin notes
- Spanning figures and tables
"""

from typing import List, Tuple, Optional, Dict, Any
from specguard.core.models import TextBlock, BBox, FigureData, TableData


class ReadingOrderEngine:
    """
    Reconstructs the true reading order of page elements using
    geometric column detection and vertical segmentation.
    """

    def __init__(
        self,
        column_gutter_min_width: float = 12.0,
        spanning_threshold_ratio: float = 0.65,
        header_margin_ratio: float = 0.08,
        footer_margin_ratio: float = 0.92,
    ):
        self.column_gutter_min_width = column_gutter_min_width
        self.spanning_threshold_ratio = spanning_threshold_ratio
        self.header_margin_ratio = header_margin_ratio
        self.footer_margin_ratio = footer_margin_ratio

    def analyze_page_layout(
        self,
        blocks: List[TextBlock],
        page_width: float,
        page_height: float,
        figures: Optional[List[FigureData]] = None,
        tables: Optional[List[TableData]] = None,
    ) -> Tuple[List[TextBlock], List[int], List[BBox], str]:
        """
        Analyzes page geometry and returns:
        1. Ordered list of TextBlocks
        2. Ordered block indices (relative to original list)
        3. Detected column bounding boxes
        4. Layout type ("single_column", "two_column", "multi_column", "mixed")
        """
        if not blocks:
            return [], [], [], "single_column"

        indexed_blocks = list(enumerate(blocks))

        # Check for headers and footers based on geometric margins
        header_y_max = page_height * self.header_margin_ratio
        footer_y_min = page_height * self.footer_margin_ratio

        # Determine column geometry for body content (excluding headers/footers)
        body_blocks = [
            (idx, b) for idx, b in indexed_blocks
            if b.bbox.y0 >= header_y_max and b.bbox.y1 <= footer_y_min
        ]
        if not body_blocks:
            body_blocks = indexed_blocks

        # Detect columns and layout type
        columns, layout_type = self._detect_columns(body_blocks, page_width, page_height)

        if layout_type == "single_column":
            # Simple top-to-bottom reading order
            sorted_indices = sorted(
                indexed_blocks,
                key=lambda item: (round(item[1].bbox.y0 / 4.0) * 4.0, item[1].bbox.x0)
            )
            ordered_blocks = [b for _, b in sorted_indices]
            ordered_idx_map = [idx for idx, _ in sorted_indices]
            for b in ordered_blocks:
                b.column_id = 0
            return ordered_blocks, ordered_idx_map, columns, layout_type

        # For multi-column or mixed layouts, segment page into vertical bands
        # (Spanning sections vs Column sections)
        ordered_indices = self._order_multicolumn_blocks(
            indexed_blocks=indexed_blocks,
            columns=columns,
            page_width=page_width,
            page_height=page_height,
            header_y_max=header_y_max,
            footer_y_min=footer_y_min
        )

        ordered_blocks = [blocks[idx] for idx in ordered_indices]
        return ordered_blocks, ordered_indices, columns, layout_type

    def _detect_columns(
        self,
        indexed_blocks: List[Tuple[int, TextBlock]],
        page_width: float,
        page_height: float,
    ) -> Tuple[List[BBox], str]:
        """
        Identifies column regions using horizontal projection and block bounding boxes.
        """
        if len(indexed_blocks) < 3:
            return [BBox(0.0, 0.0, page_width, page_height)], "single_column"

        # Separate blocks into potential column elements vs spanning elements
        spanning_width = page_width * self.spanning_threshold_ratio
        column_candidates = [
            b for _, b in indexed_blocks
            if b.bbox.width < spanning_width and len(b.text.strip()) > 3
        ]

        if len(column_candidates) < 4:
            return [BBox(0.0, 0.0, page_width, page_height)], "single_column"

        # Check for 2-column layout by examining center line and x-intervals
        center_x = page_width / 2.0
        left_col_blocks = [
            b for b in column_candidates
            if b.bbox.x1 <= center_x + (self.column_gutter_min_width / 2.0)
        ]
        right_col_blocks = [
            b for b in column_candidates
            if b.bbox.x0 >= center_x - (self.column_gutter_min_width / 2.0)
        ]
        straddling_blocks = [
            b for b in column_candidates
            if b.bbox.x0 < center_x and b.bbox.x1 > center_x
        ]

        # In a genuine 2-column layout, left and right have significant counts,
        # and few blocks straddle the middle without spanning full width
        total_cand = len(column_candidates)
        left_ratio = len(left_col_blocks) / total_cand
        right_ratio = len(right_col_blocks) / total_cand
        straddle_ratio = len(straddling_blocks) / total_cand

        if left_ratio >= 0.25 and right_ratio >= 0.25 and straddle_ratio < 0.20:
            # Two-column layout confirmed
            left_x0 = min(b.bbox.x0 for b in left_col_blocks)
            left_x1 = max(b.bbox.x1 for b in left_col_blocks)
            right_x0 = min(b.bbox.x0 for b in right_col_blocks)
            right_x1 = max(b.bbox.x1 for b in right_col_blocks)

            col1 = BBox(left_x0, 0.0, left_x1, page_height)
            col2 = BBox(right_x0, 0.0, right_x1, page_height)

            # Check if there are also spanning elements (title, figures, abstract) -> mixed
            has_spanning = any(b.bbox.width >= spanning_width for _, b in indexed_blocks)
            layout_type = "mixed" if has_spanning else "two_column"

            return [col1, col2], layout_type

        # Check for 3-column layout
        one_third = page_width / 3.0
        two_thirds = 2.0 * page_width / 3.0
        col1_blocks = [b for b in column_candidates if b.bbox.x1 <= one_third + 15.0]
        col2_blocks = [
            b for b in column_candidates
            if b.bbox.x0 >= one_third - 15.0 and b.bbox.x1 <= two_thirds + 15.0
        ]
        col3_blocks = [b for b in column_candidates if b.bbox.x0 >= two_thirds - 15.0]

        if (len(col1_blocks) / total_cand >= 0.2 and
            len(col2_blocks) / total_cand >= 0.2 and
            len(col3_blocks) / total_cand >= 0.2):
            col1 = BBox(0.0, 0.0, one_third, page_height)
            col2 = BBox(one_third, 0.0, two_thirds, page_height)
            col3 = BBox(two_thirds, 0.0, page_width, page_height)
            return [col1, col2, col3], "multi_column"

        return [BBox(0.0, 0.0, page_width, page_height)], "single_column"

    def _order_multicolumn_blocks(
        self,
        indexed_blocks: List[Tuple[int, TextBlock]],
        columns: List[BBox],
        page_width: float,
        page_height: float,
        header_y_max: float,
        footer_y_min: float,
    ) -> List[int]:
        """
        Orders blocks geometrically across multi-column / mixed layout:
        1. Running headers (y < header_y_max)
        2. Vertical bands sorted top to bottom:
           - Spanning blocks (e.g. Title, Abstract, Full-width Fig/Table)
           - Multi-column regions (Column 1 top-to-bottom, then Column 2 top-to-bottom)
        3. Running footers (y > footer_y_min)
        """
        spanning_width = page_width * self.spanning_threshold_ratio

        # Separate headers and footers
        headers: List[Tuple[int, TextBlock]] = []
        footers: List[Tuple[int, TextBlock]] = []
        body: List[Tuple[int, TextBlock]] = []

        for idx, b in indexed_blocks:
            if b.bbox.y1 <= header_y_max:
                headers.append((idx, b))
            elif b.bbox.y0 >= footer_y_min:
                footers.append((idx, b))
            else:
                body.append((idx, b))

        # Sort headers top to bottom, left to right
        headers_sorted = [
            idx for idx, _ in sorted(headers, key=lambda it: (it[1].bbox.y0, it[1].bbox.x0))
        ]
        # Sort footers top to bottom, left to right
        footers_sorted = [
            idx for idx, _ in sorted(footers, key=lambda it: (it[1].bbox.y0, it[1].bbox.x0))
        ]

        if not body:
            return headers_sorted + footers_sorted

        # Group body into spanning elements vs column-confined elements
        # Identify vertical break lines introduced by full-width spanning elements
        spanning_bands: List[Tuple[float, float, Tuple[int, TextBlock]]] = []
        column_elements: List[Tuple[int, TextBlock]] = []

        for idx, b in body:
            # A block is spanning if it is wide or crosses the gutter significantly
            is_spanning = b.bbox.width >= spanning_width
            if not is_spanning and len(columns) >= 2:
                # Check if it crosses the gutter between col1 and col2
                col1, col2 = columns[0], columns[1]
                gutter_x0 = col1.x1
                gutter_x1 = col2.x0
                if b.bbox.x0 < gutter_x0 and b.bbox.x1 > gutter_x1:
                    is_spanning = True

            if is_spanning:
                spanning_bands.append((b.bbox.y0, b.bbox.y1, (idx, b)))
            else:
                column_elements.append((idx, b))

        # If there are no spanning elements in body, simply process columns left-to-right
        if not spanning_bands:
            body_ordered = self._order_pure_columns(column_elements, columns)
            return headers_sorted + body_ordered + footers_sorted

        # Otherwise, partition the page into horizontal slices by spanning bands
        # Sort spanning bands top to bottom
        spanning_bands.sort(key=lambda s: s[0])

        # Merge overlapping or close spanning bands into single zones
        merged_spanning_zones: List[Tuple[float, float, List[Tuple[int, TextBlock]]]] = []
        for y0, y1, item in spanning_bands:
            if not merged_spanning_zones:
                merged_spanning_zones.append((y0, y1, [item]))
            else:
                last_y0, last_y1, items = merged_spanning_zones[-1]
                if y0 <= last_y1 + 10.0:  # Within 10 pts, merge into same spanning zone
                    merged_spanning_zones[-1] = (
                        last_y0,
                        max(last_y1, y1),
                        items + [item]
                    )
                else:
                    merged_spanning_zones.append((y0, y1, [item]))

        # Interleave column slices with spanning zones
        body_ordered: List[int] = []
        current_y = 0.0

        for span_y0, span_y1, span_items in merged_spanning_zones:
            # Find column elements that sit above this spanning zone
            slice_col_items = [
                item for item in column_elements
                if item[1].bbox.y1 <= span_y0 + 5.0 and item[1].bbox.y0 >= current_y - 5.0
            ]
            if slice_col_items:
                body_ordered.extend(self._order_pure_columns(slice_col_items, columns))

            # Add the spanning items in this zone (sorted top-to-bottom)
            span_items_sorted = sorted(span_items, key=lambda it: (it[1].bbox.y0, it[1].bbox.x0))
            for idx, b in span_items_sorted:
                b.column_id = 0
                body_ordered.append(idx)

            current_y = span_y1

        # Process any remaining column elements below the last spanning zone
        remaining_col_items = [
            item for item in column_elements
            if item[1].bbox.y0 >= current_y - 5.0
        ]
        if remaining_col_items:
            body_ordered.extend(self._order_pure_columns(remaining_col_items, columns))

        # Catch any stray elements not included yet
        included_set = set(body_ordered)
        stray_items = [idx for idx, _ in body if idx not in included_set]
        if stray_items:
            stray_sorted = sorted(
                [item for item in body if item[0] in stray_items],
                key=lambda it: (it[1].bbox.y0, it[1].bbox.x0)
            )
            body_ordered.extend([idx for idx, _ in stray_sorted])

        return headers_sorted + body_ordered + footers_sorted

    def _order_pure_columns(
        self,
        col_items: List[Tuple[int, TextBlock]],
        columns: List[BBox]
    ) -> List[int]:
        """
        Orders blocks within discrete columns: Column 0 top-to-bottom, Column 1 top-to-bottom, etc.
        """
        if not col_items:
            return []

        col_buckets: Dict[int, List[Tuple[int, TextBlock]]] = {i: [] for i in range(len(columns))}

        for idx, b in col_items:
            block_center_x = (b.bbox.x0 + b.bbox.x1) / 2.0
            assigned = False
            for col_idx, col_box in enumerate(columns):
                # Tolerance around column borders
                if col_box.x0 - 20.0 <= block_center_x <= col_box.x1 + 20.0:
                    col_buckets[col_idx].append((idx, b))
                    b.column_id = col_idx + 1
                    assigned = True
                    break
            if not assigned:
                # Closest column by center distance
                best_col = min(
                    range(len(columns)),
                    key=lambda ci: abs(block_center_x - (columns[ci].x0 + columns[ci].x1) / 2.0)
                )
                col_buckets[best_col].append((idx, b))
                b.column_id = best_col + 1

        ordered: List[int] = []
        for col_idx in range(len(columns)):
            items = col_buckets[col_idx]
            # Sort top to bottom within column; if vertically close (within 4pt), sort left to right
            items_sorted = sorted(
                items,
                key=lambda it: (round(it[1].bbox.y0 / 4.0) * 4.0, it[1].bbox.x0)
            )
            ordered.extend([idx for idx, _ in items_sorted])

        return ordered
