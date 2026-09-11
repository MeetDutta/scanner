"""
OpenCV-based Scanned Document Preprocessing and Enhancement Pipeline.
Noise removal, deskew, contrast enhancement (CLAHE), adaptive binarization, and local OCR.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, List, Dict, Optional
from specguard.core.models import BBox

logger = logging.getLogger(__name__)


class ScannedDocumentPipeline:
    """
    End-to-end local computer vision pipeline for scanned documents and images.
    Enhances visual quality and extracts bounding-box coordinates.
    """

    @staticmethod
    def preprocess_image(image: np.ndarray) -> np.ndarray:
        """Runs grayscale, noise reduction, and contrast enhancement."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Denoise using bilateral filter to preserve sharp technical edges
        denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

        # Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        return enhanced

    @staticmethod
    def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Calculates skew angle and deskews the page image."""
        # Convert to binary
        thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Find coordinates of all foreground pixels
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return image, 0.0

        # Minimum bounding rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        # Normalize angle
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # If angle is very small, skip rotation
        if abs(angle) < 0.2:
            return image, 0.0

        # Rotate image around center
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        logger.debug("Deskewed image with angle: %.2f degrees", angle)
        return deskewed, angle

    @staticmethod
    def binarize(image: np.ndarray) -> np.ndarray:
        """Adaptive Gaussian thresholding for crisp text segmentation."""
        return cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )

    @staticmethod
    def extract_text_regions(binary_image: np.ndarray) -> List[BBox]:
        """Uses morphological dilation to find word/line bounding regions."""
        # Invert so text is white
        inv = 255 - binary_image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(inv, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        h, w = binary_image.shape[:2]

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            # Filter out tiny noise and full-page borders
            if bw > 20 and bh > 8 and (bw < w * 0.98 or bh < h * 0.98):
                boxes.append(BBox(x0=float(x), y0=float(y), x1=float(x + bw), y1=float(y + bh)))

        # Sort top-to-bottom, left-to-right
        boxes.sort(key=lambda b: (b.y0 // 20, b.x0))
        return boxes
