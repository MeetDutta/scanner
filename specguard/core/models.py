"""
Core domain models and dataclasses for SpecGuard.
Defines normalized structures for documents, pages, blocks, parameters, and findings.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import json


class SeverityLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class FindingCategory(str, Enum):
    FORMATTING = "Formatting"
    STRUCTURE = "Structure"
    TOC = "Table of Contents"
    TABLE = "Table"
    GRAMMAR = "Grammar & Spelling"
    SEMANTIC = "Semantic Inconsistency"
    LOGICAL = "Logical Contradiction"
    ENGINEERING = "Engineering Parameter"
    STANDARDS = "Standards Deviation"
    FIGURE = "Figure"
    EQUATION = "Equation"
    CROSS_REFERENCE = "Cross-Reference"
    IEEE_COMPLIANCE = "IEEE Compliance"


@dataclass
class BBox:
    """Normalized or absolute bounding box (x0, y0, x1, y1)."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    def to_dict(self) -> Dict[str, float]:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional['BBox']:
        if not data:
            return None
        return cls(
            x0=float(data.get("x0", 0.0)),
            y0=float(data.get("y0", 0.0)),
            x1=float(data.get("x1", 0.0)),
            y1=float(data.get("y1", 0.0)),
        )


@dataclass
class WordModel:
    """Individual extracted word with source coordinates and font information."""
    text: str
    bbox: BBox
    font_name: str = "Unknown"
    font_size: float = 11.0
    is_bold: bool = False
    is_italic: bool = False


@dataclass
class LineModel:
    """A line of text composed of words."""
    words: List[WordModel] = field(default_factory=list)
    text: str = ""
    bbox: Optional[BBox] = None
    font_size: float = 11.0


@dataclass
class TextBlock:
    """Individual extracted text block or span with coordinates and typography."""
    text: str
    bbox: BBox
    font_name: str = "Unknown"
    font_size: float = 11.0
    is_bold: bool = False
    is_italic: bool = False
    line_spacing: float = 1.15
    line_num: int = 0
    block_id: int = 0
    column_id: int = 0
    words: List[WordModel] = field(default_factory=list)
    lines: List[LineModel] = field(default_factory=list)


@dataclass
class TableData:
    """Extracted tabular structure."""
    rows: List[List[str]] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    bbox: Optional[BBox] = None
    page_num: int = 1
    page_end: Optional[int] = None
    caption: str = ""
    caption_position: str = "above"  # "above", "below", "none"
    table_id: str = ""
    label: str = ""  # e.g., "Table 1", "TABLE I"
    is_split: bool = False
    confidence: float = 1.0


@dataclass
class FigureData:
    """Extracted drawing, figure, or schematic region."""
    bbox: Optional[BBox] = None
    page_num: int = 1
    page_end: Optional[int] = None
    caption: str = ""
    caption_position: str = "below"  # "below", "above", "none"
    figure_type: str = "diagram"  # diagram, chart, technical_drawing, raster, vector
    figure_id: str = ""
    label: str = ""  # e.g., "Fig. 1", "Figure 2"
    confidence: float = 1.0


@dataclass
class EquationData:
    """Extracted mathematical expression or display equation."""
    equation_id: str
    page_num: int
    bbox: BBox
    text: str = ""
    label: str = ""  # e.g. "(1)", "(2.3)"
    is_inline: bool = False
    is_numbered: bool = False
    confidence: float = 1.0


@dataclass
class TOCItem:
    """Single item in a document's Table of Contents."""
    level: int
    title: str
    page_num: int  # Page on which the TOC item is located
    target_page_num: Optional[int] = None  # Page the TOC item points to
    bbox: Optional[BBox] = None
    raw_text: str = ""


@dataclass
class TOCModel:
    """Document Table of Contents structure."""
    items: List[TOCItem] = field(default_factory=list)
    page_num: int = 1
    exists: bool = False
    is_genuine: bool = False
    title: str = "Table of Contents"


@dataclass
class SectionNode:
    """Hierarchical section node (e.g. 1. Introduction, 1.1 Background, I. METHODOLOGY)."""
    section_id: str
    title: str
    level: int
    number_str: str = ""
    page_num: int = 1
    bbox: Optional[BBox] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)


@dataclass
class ReferenceItem:
    """Bibliography reference entry (e.g. [1] J. Doe, ...)."""
    ref_id: str
    label: str  # "[1]", "Smith et al."
    raw_text: str
    page_num: int = 1
    authors: List[str] = field(default_factory=list)
    title: str = ""
    year: Optional[str] = None


@dataclass
class CrossReferenceItem:
    """Cross-reference link within the document (e.g. Fig. 1, Table II, Eq. 4, [3])."""
    ref_type: str  # "figure", "table", "equation", "section", "citation"
    source_page: int
    source_bbox: Optional[BBox] = None
    mention_text: str = ""
    target_id: str = ""
    is_resolved: bool = False


@dataclass
class PageModel:
    """Normalized page representation."""
    page_num: int
    width: float = 612.0  # Default standard Letter width
    height: float = 792.0  # Default standard Letter height
    blocks: List[TextBlock] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    figures: List[FigureData] = field(default_factory=list)
    equations: List[EquationData] = field(default_factory=list)
    headers: List[TextBlock] = field(default_factory=list)
    footers: List[TextBlock] = field(default_factory=list)
    text: str = ""
    reading_order: List[int] = field(default_factory=list)
    columns: List[BBox] = field(default_factory=list)
    layout_type: str = "single_column"  # single_column, two_column, multi_column, mixed
    rotation: int = 0


@dataclass
class DocumentModel:
    """Complete document representation across PDF, DOCX, XLSX, TXT, Images."""
    file_path: str
    file_type: str
    file_hash: str
    file_size: int
    page_count: int
    pages: List[PageModel] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[SectionNode] = field(default_factory=list)
    toc: Optional[TOCModel] = None
    figures: List[FigureData] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    equations: List[EquationData] = field(default_factory=list)
    references: List[ReferenceItem] = field(default_factory=list)
    cross_references: List[CrossReferenceItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    profile_name: str = "general"
    processing_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


@dataclass
class EngineeringParameter:
    """Structured engineering proposition extracted by semantic & domain analyzers."""
    entity: str
    parameter: str
    value: float
    raw_value: str
    unit: str
    normalized_value: float
    normalized_unit: str
    condition: str = "Operating"
    page: int = 1
    section: str = ""
    location: str = ""
    bbox: Optional[BBox] = None
    confidence: float = 0.95
    source_sentence: str = ""


@dataclass
class Finding:
    """
    Standardized, explainable finding object generated by all SpecGuard analyzers.
    Strictly adheres to research & compliance criteria.
    """
    finding_id: str
    category: str
    domain: str
    location: str
    page: int
    bbox: Optional[BBox] = None
    original_content: str = ""
    detected_value: Any = ""
    expected_value: Any = ""
    deviation: Optional[str] = None
    severity: str = "Medium"
    confidence: float = 1.0
    explanation: str = ""
    suggested_correction: str = ""
    rule_reference: Optional[str] = None
    priority_score: float = 0.0
    evidence: str = ""
    detection_method: str = "deterministic"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.bbox:
            data["bbox"] = self.bbox.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Finding':
        bbox_data = data.get("bbox")
        bbox = BBox.from_dict(bbox_data) if bbox_data else None
        return cls(
            finding_id=data["finding_id"],
            category=data["category"],
            domain=data.get("domain", "General"),
            location=data.get("location", ""),
            page=int(data.get("page", 1)),
            bbox=bbox,
            original_content=data.get("original_content", ""),
            detected_value=data.get("detected_value", ""),
            expected_value=data.get("expected_value", ""),
            deviation=data.get("deviation"),
            severity=data.get("severity", "Medium"),
            confidence=float(data.get("confidence", 1.0)),
            explanation=data.get("explanation", ""),
            suggested_correction=data.get("suggested_correction", ""),
            rule_reference=data.get("rule_reference"),
            priority_score=float(data.get("priority_score", 0.0)),
            evidence=data.get("evidence", ""),
            detection_method=data.get("detection_method", "deterministic")
        )
