"""
OpenCV Document Layout Analysis.
Extracts visual elements: table grids, lines, figures, drawings, margins, and column alignment.
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from specguard.core.models import BBox, TableData, FigureData

logger = logging.getLogger(__name__)


class LayoutAnalyzerCV:
    """
    Analyzes visual page geometry using OpenCV morphological transformations and contour hierarchy.
    Identifies non-text visual structures, diagrams, tables, and margins.
    """

    @staticmethod
    def detect_lines_and_tables(gray_image: np.ndarray, page_num: int = 1) -> Tuple[List[BBox], List[TableData]]:
        """
        Detects horizontal and vertical engineering lines to locate table grids and borders.
        """
        h, w = gray_image.shape[:2]
        thresh = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4
        )

        # Detect horizontal lines
        scale = max(20, w // 40)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (scale, 1))
        h_lines = cv2.erode(thresh, h_kernel, iterations=1)
        h_lines = cv2.dilate(h_lines, h_kernel, iterations=1)

        # Detect vertical lines
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, scale))
        v_lines = cv2.erode(thresh, v_kernel, iterations=1)
        v_lines = cv2.dilate(v_lines, v_kernel, iterations=1)

        # Combine table grid mask
        table_mask = cv2.add(h_lines, v_lines)
        grid_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        table_mask = cv2.dilate(table_mask, grid_kernel, iterations=2)

        # Find table contours
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        table_boxes = []
        tables = []

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            # A valid table typically spans a noticeable width and height
            if bw > w * 0.25 and bh > h * 0.05:
                bbox = BBox(x0=float(x), y0=float(y), x1=float(x + bw), y1=float(y + bh))
                table_boxes.append(bbox)
                tables.append(TableData(rows=[], headers=[], bbox=bbox, page_num=page_num))

        return table_boxes, tables

    @staticmethod
    def detect_figures_and_drawings(gray_image: np.ndarray, table_boxes: List[BBox], page_num: int = 1) -> List[FigureData]:
        """
        Detects figures, schematics, engineering drawings, and diagrams.
        Filters out known text blocks and table areas.
        """
        h, w = gray_image.shape[:2]
        # Invert and blur
        thresh = cv2.threshold(gray_image, 240, 255, cv2.THRESH_BINARY_INV)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        figures = []

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            # Minimum figure size threshold (e.g. at least 5% of page area, not entire page)
            if area > (w * h * 0.04) and area < (w * h * 0.85):
                fig_bbox = BBox(x0=float(x), y0=float(y), x1=float(x + bw), y1=float(y + bh))
                
                # Check if it overlaps heavily with detected tables
                is_table = False
                for tb in table_boxes:
                    if (abs(fig_bbox.x0 - tb.x0) < 30 and abs(fig_bbox.y0 - tb.y0) < 30 and
                            abs(fig_bbox.x1 - tb.x1) < 30 and abs(fig_bbox.y1 - tb.y1) < 30):
                        is_table = True
                        break
                
                if not is_table:
                    figures.append(FigureData(
                        bbox=fig_bbox,
                        page_num=page_num,
                        figure_type="engineering_drawing" if bw > w * 0.5 else "diagram"
                    ))

        return figures

    @staticmethod
    def analyze_page_margins(text_bboxes: List[BBox], page_width: float, page_height: float) -> Dict[str, float]:
        """Calculates page margins based on outermost text bounding boxes."""
        if not text_bboxes:
            return {"left": 72.0, "right": 72.0, "top": 72.0, "bottom": 72.0}

        left_margin = min(b.x0 for b in text_bboxes)
        right_margin = max(0.0, page_width - max(b.x1 for b in text_bboxes))
        top_margin = min(b.y0 for b in text_bboxes)
        bottom_margin = max(0.0, page_height - max(b.y1 for b in text_bboxes))

        return {
            "left": round(left_margin, 1),
            "right": round(right_margin, 1),
            "top": round(top_margin, 1),
            "bottom": round(bottom_margin, 1)
        }
