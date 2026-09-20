"""
Normalized Document Object Registry for DocReady.
Indexes all structured document objects (Sections, Headings, TOC entries, Figures,
Tables, Equations, References) with stable IDs and fast bi-directional lookup.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from specguard.core.models import (
    DocumentModel, PageModel, SectionNode, TOCItem,
    FigureData, TableData, EquationData, ReferenceItem,
    CrossReferenceItem, BBox
)


@dataclass
class RegisteredObject:
    """Normalized descriptor for an identifiable document object."""
    object_id: str
    object_type: str  # "section", "heading", "toc_item", "figure", "table", "equation", "reference", "page_num"
    label: str
    title_or_text: str
    page_num: int
    bbox: Optional[BBox] = None
    reading_order_idx: int = 0
    parent_id: Optional[str] = None
    target_page_num: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentObjectRegistry:
    """Central registry providing lookup and relation-graph building across document objects."""

    def __init__(self):
        self._objects_by_id: Dict[str, RegisteredObject] = {}
        self._objects_by_type: Dict[str, List[RegisteredObject]] = {}
        self._objects_by_page: Dict[int, List[RegisteredObject]] = {}
        self._heading_by_norm_title: Dict[str, RegisteredObject] = {}
        self._figure_by_num: Dict[int, RegisteredObject] = {}
        self._table_by_num: Dict[int, RegisteredObject] = {}
        self._equation_by_num: Dict[str, RegisteredObject] = {}
        self._reference_by_num: Dict[int, RegisteredObject] = {}

    def register(self, obj: RegisteredObject) -> None:
        self._objects_by_id[obj.object_id] = obj
        self._objects_by_type.setdefault(obj.object_type, []).append(obj)
        self._objects_by_page.setdefault(obj.page_num, []).append(obj)

    def get_object(self, object_id: str) -> Optional[RegisteredObject]:
        return self._objects_by_id.get(object_id)

    def get_objects_by_type(self, object_type: str) -> List[RegisteredObject]:
        return self._objects_by_type.get(object_type, [])

    def get_objects_on_page(self, page_num: int) -> List[RegisteredObject]:
        return self._objects_by_page.get(page_num, [])

    def find_heading_by_title(self, title: str) -> Optional[RegisteredObject]:
        norm = self._normalize_title(title)
        return self._heading_by_norm_title.get(norm)

    def find_figure_by_number(self, num: int) -> Optional[RegisteredObject]:
        return self._figure_by_num.get(num)

    def find_table_by_number(self, num: int) -> Optional[RegisteredObject]:
        return self._table_by_num.get(num)

    def find_equation_by_label(self, label: str) -> Optional[RegisteredObject]:
        clean_lbl = re.sub(r'[\(\)\s]', '', label)
        return self._equation_by_num.get(clean_lbl)

    def find_reference_by_number(self, num: int) -> Optional[RegisteredObject]:
        return self._reference_by_num.get(num)

    @staticmethod
    def _normalize_title(title: str) -> str:
        clean = re.sub(r'^(?:[0-9]+(?:\.[0-9]+)*\.?|[IVXLCDM]+\.?|[A-Z]\.)\s*', '', title.lower()).strip()
        clean = re.sub(r'[\s\.\-_]+', ' ', clean)
        return clean

    @classmethod
    def build_from_document(cls, doc: DocumentModel) -> 'DocumentObjectRegistry':
        registry = cls()

        # 1. Sections & Headings
        for sec in doc.sections:
            reg_obj = RegisteredObject(
                object_id=sec.section_id or f"sec_p{sec.page_num}_{sec.number_str}",
                object_type="heading",
                label=sec.number_str,
                title_or_text=sec.title,
                page_num=sec.page_num,
                bbox=sec.bbox,
                parent_id=sec.parent_id
            )
            registry.register(reg_obj)
            norm_title = registry._normalize_title(sec.title)
            if norm_title:
                registry._heading_by_norm_title[norm_title] = reg_obj

        # 2. TOC Items
        if doc.toc and doc.toc.items:
            for idx, item in enumerate(doc.toc.items):
                reg_obj = RegisteredObject(
                    object_id=f"toc_item_{idx+1}",
                    object_type="toc_item",
                    label=f"Level {item.level}",
                    title_or_text=item.title,
                    page_num=item.page_num,
                    bbox=item.bbox,
                    target_page_num=item.target_page_num,
                    metadata={"raw_text": item.raw_text}
                )
                registry.register(reg_obj)

        # 3. Figures
        for idx, fig in enumerate(doc.figures):
            fig_id = fig.figure_id or f"fig_{idx+1}"
            reg_obj = RegisteredObject(
                object_id=fig_id,
                object_type="figure",
                label=fig.label,
                title_or_text=fig.caption,
                page_num=fig.page_num,
                bbox=fig.bbox,
                metadata={"caption_position": fig.caption_position}
            )
            registry.register(reg_obj)
            m = re.search(r'\d+', fig.label or "")
            if m:
                registry._figure_by_num[int(m.group(0))] = reg_obj

        # 4. Tables
        for idx, tbl in enumerate(doc.tables):
            tbl_id = tbl.table_id or f"tbl_{idx+1}"
            reg_obj = RegisteredObject(
                object_id=tbl_id,
                object_type="table",
                label=tbl.label,
                title_or_text=tbl.caption,
                page_num=tbl.page_num,
                bbox=tbl.bbox,
                metadata={"caption_position": tbl.caption_position, "is_split": tbl.is_split}
            )
            registry.register(reg_obj)
            m = re.search(r'\d+', tbl.label or "")
            if m:
                registry._table_by_num[int(m.group(0))] = reg_obj

        # 5. Equations
        for idx, eq in enumerate(doc.equations):
            eq_id = eq.equation_id or f"eq_{idx+1}"
            clean_lbl = re.sub(r'[\(\)\s]', '', eq.label or "")
            reg_obj = RegisteredObject(
                object_id=eq_id,
                object_type="equation",
                label=eq.label,
                title_or_text=eq.text,
                page_num=eq.page_num,
                bbox=eq.bbox,
                metadata={"is_numbered": eq.is_numbered}
            )
            registry.register(reg_obj)
            if clean_lbl:
                registry._equation_by_num[clean_lbl] = reg_obj

        # 6. References / Citations
        for ref in doc.references:
            reg_obj = RegisteredObject(
                object_id=ref.ref_id,
                object_type="reference",
                label=ref.label,
                title_or_text=ref.raw_text,
                page_num=ref.page_num
            )
            registry.register(reg_obj)
            m = re.search(r'\d+', ref.label or "")
            if m:
                registry._reference_by_num[int(m.group(0))] = reg_obj

        return registry
