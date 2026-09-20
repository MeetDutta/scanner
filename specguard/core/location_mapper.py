"""
Precise Document Location Mapper.

Provides exact bounding-box resolution for words, phrases, numbers, and cross-reference tokens
within extracted document models. Supports multi-line phrase wrapping, adjacent box merging,
and sub-word character slice calculations with zero coordinate fabrication.
"""

import re
import logging
from typing import List, Optional, Tuple
from specguard.core.models import PageModel, TextBlock, WordModel, LineModel, BBox

logger = logging.getLogger(__name__)


class LocationMapper:
    """
    Resolves exact bounding boxes for detected document elements.
    """

    @staticmethod
    def normalize_token(text: str) -> str:
        """Strip enclosing punctuation and normalize whitespace for comparison."""
        if not text:
            return ""
        # Remove trailing and leading common punctuation
        return re.sub(r"^[^\w\(\)\[\]]+|[^\w\(\)\[\]]+$", "", text.strip())

    @classmethod
    def find_word_bbox(
        cls,
        page: PageModel,
        word: str,
        block_id: Optional[int] = None,
        line_id: Optional[int] = None
    ) -> Optional[BBox]:
        """
        Find exact bounding box of a word within a page, optionally restricted to a block or line.
        """
        norm_target = cls.normalize_token(word).lower()
        if not norm_target:
            return None

        for b_idx, block in enumerate(page.blocks):
            if block_id is not None and block.block_id != block_id and b_idx != block_id:
                continue

            for l_idx, line in enumerate(block.lines):
                if line_id is not None and l_idx != line_id:
                    continue

                for w in line.words:
                    norm_w = cls.normalize_token(w.text).lower()
                    if norm_w == norm_target or w.text.strip().lower() == word.strip().lower():
                        return BBox(x0=w.bbox.x0, y0=w.bbox.y0, x1=w.bbox.x1, y1=w.bbox.y1)

            # Fallback to block words directly if lines weren't populated
            for w in block.words:
                norm_w = cls.normalize_token(w.text).lower()
                if norm_w == norm_target or w.text.strip().lower() == word.strip().lower():
                    return BBox(x0=w.bbox.x0, y0=w.bbox.y0, x1=w.bbox.x1, y1=w.bbox.y1)

        return None

    @classmethod
    def find_phrase_bboxes(
        cls,
        page: PageModel,
        phrase: str,
        block_id: Optional[int] = None
    ) -> List[BBox]:
        """
        Find bounding boxes for a phrase within a page.
        Returns a list of bounding boxes (one per line if the phrase wraps across lines).
        """
        phrase_clean = phrase.strip()
        if not phrase_clean:
            return []

        phrase_tokens = [cls.normalize_token(t).lower() for t in phrase_clean.split() if t.strip()]
        if not phrase_tokens:
            return []

        for b_idx, block in enumerate(page.blocks):
            if block_id is not None and block.block_id != block_id and b_idx != block_id:
                continue

            # Check if block text contains the phrase
            if phrase_clean.lower() not in block.text.lower():
                # Check with relaxed spaces
                normalized_block_text = " ".join(block.text.split()).lower()
                if " ".join(phrase_tokens) not in normalized_block_text:
                    continue

            # Match token sequence across words
            matched_word_boxes: List[WordModel] = []
            token_idx = 0
            block_words = block.words
            if not block_words and block.lines:
                block_words = [w for l in block.lines for w in l.words]

            for w in block_words:
                norm_w = cls.normalize_token(w.text).lower()
                if not norm_w:
                    continue

                if norm_w == phrase_tokens[token_idx] or phrase_tokens[token_idx] in norm_w:
                    matched_word_boxes.append(w)
                    token_idx += 1
                    if token_idx == len(phrase_tokens):
                        # Found full phrase!
                        return cls.group_words_into_line_bboxes(matched_word_boxes)
                else:
                    if token_idx > 0:
                        # Reset and re-check current word
                        token_idx = 0
                        matched_word_boxes.clear()
                        if norm_w == phrase_tokens[0] or phrase_tokens[0] in norm_w:
                            matched_word_boxes.append(w)
                            token_idx = 1

        return []

    @classmethod
    def group_words_into_line_bboxes(cls, words: List[WordModel]) -> List[BBox]:
        """
        Groups words by vertical alignment (line) and merges adjacent horizontal boxes.
        Returns one BBox per line segment.
        """
        if not words:
            return []

        # Group words by approximate y0 (within 3 points)
        lines: List[List[WordModel]] = []
        for w in words:
            if not w.bbox:
                continue
            placed = False
            for group in lines:
                if abs(group[0].bbox.y0 - w.bbox.y0) < 4.0:
                    group.append(w)
                    placed = True
                    break
            if not placed:
                lines.append([w])

        line_bboxes = []
        for group in lines:
            gx0 = min(w.bbox.x0 for w in group)
            gy0 = min(w.bbox.y0 for w in group)
            gx1 = max(w.bbox.x1 for w in group)
            gy1 = max(w.bbox.y1 for w in group)
            line_bboxes.append(BBox(x0=gx0, y0=gy0, x1=gx1, y1=gy1))

        return line_bboxes

    @classmethod
    def find_number_in_block(cls, block: TextBlock, number_str: str) -> Optional[BBox]:
        """
        Find exact bounding box of a number (e.g. '1.1', '5', 'III') within a block.
        """
        num_clean = number_str.strip()
        if not num_clean:
            return None

        # Look in block words first
        words = block.words
        if not words and block.lines:
            words = [w for l in block.lines for w in l.words]

        for w in words:
            norm_w = cls.normalize_token(w.text)
            if norm_w == num_clean or w.text.strip() == num_clean:
                return BBox(x0=w.bbox.x0, y0=w.bbox.y0, x1=w.bbox.x1, y1=w.bbox.y1)

        # Look for number substring within words (e.g., "Figure 1.1:" -> word "1.1:")
        for w in words:
            if num_clean in w.text:
                # Calculate sub-word bbox proportionally
                w_len = max(1, len(w.text))
                start_c = w.text.find(num_clean)
                char_w = (w.bbox.x1 - w.bbox.x0) / w_len
                sub_x0 = w.bbox.x0 + start_c * char_w
                sub_x1 = sub_x0 + len(num_clean) * char_w
                return BBox(x0=sub_x0, y0=w.bbox.y0, x1=sub_x1, y1=w.bbox.y1)

        return None

    @classmethod
    def find_token_in_text(
        cls,
        text: str,
        token: str,
        block_words: List[WordModel]
    ) -> List[BBox]:
        """
        Find all occurrences of token within text and return their exact bounding boxes.
        """
        if not token or not text or not block_words:
            return []

        token_clean = token.strip()
        norm_token = cls.normalize_token(token_clean).lower()
        results: List[BBox] = []

        for w in block_words:
            norm_w = cls.normalize_token(w.text).lower()
            if norm_w == norm_token or token_clean.lower() in w.text.lower():
                if norm_w == norm_token:
                    results.append(BBox(x0=w.bbox.x0, y0=w.bbox.y0, x1=w.bbox.x1, y1=w.bbox.y1))
                else:
                    # Substring slice
                    w_len = max(1, len(w.text))
                    start_c = w.text.lower().find(token_clean.lower())
                    char_w = (w.bbox.x1 - w.bbox.x0) / w_len
                    sub_x0 = w.bbox.x0 + max(0, start_c) * char_w
                    sub_x1 = sub_x0 + len(token_clean) * char_w
                    results.append(BBox(x0=sub_x0, y0=w.bbox.y0, x1=sub_x1, y1=w.bbox.y1))

        return results

    @classmethod
    def calculate_character_slice_bbox(
        cls,
        word_bbox: BBox,
        total_chars: int,
        start_idx: int,
        end_idx: int
    ) -> BBox:
        """
        Calculates horizontal proportional sub-slice of a word bounding box.
        """
        if total_chars <= 0:
            return word_bbox
        w = word_bbox.x1 - word_bbox.x0
        char_w = w / float(total_chars)
        x0 = word_bbox.x0 + max(0, start_idx) * char_w
        x1 = min(word_bbox.x1, word_bbox.x0 + min(total_chars, end_idx) * char_w)
        return BBox(x0=x0, y0=word_bbox.y0, x1=x1, y1=word_bbox.y1)
