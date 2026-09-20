"""
Multi-Page Document Comparison Engine for SpecGuard.

Performs deep structural, textual, layout, table, and figure diffing between two documents:
- Page additions, deletions, and count shifts
- Section additions, removals, and structural moves
- Textual changes and modified paragraphs (using difflib sequence matching)
- Added, removed, or shifted figures and tables
- Caption changes
- Configurable comparison sensitivity (low, medium, high)
"""

import difflib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.core.models import DocumentModel, SectionNode, FigureData, TableData

logger = logging.getLogger(__name__)


@dataclass
class DocumentDiffItem:
    diff_type: str  # "page", "section", "text", "table", "figure", "metadata"
    change_type: str  # "added", "removed", "modified", "moved"
    identifier: str
    doc1_location: str
    doc2_location: str
    description: str
    doc1_content: Optional[str] = None
    doc2_content: Optional[str] = None
    similarity: float = 0.0


@dataclass
class DocumentComparisonReport:
    doc1_path: str
    doc2_path: str
    doc1_pages: int
    doc2_pages: int
    overall_similarity: float
    added_pages: int
    removed_pages: int
    sections_changed: int
    tables_changed: int
    figures_changed: int
    text_changes: int
    diff_items: List[DocumentDiffItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc1_path": self.doc1_path,
            "doc2_path": self.doc2_path,
            "doc1_pages": self.doc1_pages,
            "doc2_pages": self.doc2_pages,
            "overall_similarity": round(self.overall_similarity, 3),
            "added_pages": self.added_pages,
            "removed_pages": self.removed_pages,
            "sections_changed": self.sections_changed,
            "tables_changed": self.tables_changed,
            "figures_changed": self.figures_changed,
            "text_changes": self.text_changes,
            "diff_items": [asdict(item) for item in self.diff_items]
        }


class DocumentComparator:
    """
    Compares two multi-page DocumentModels across structure, content, and visual assets.
    """

    def __init__(self, sensitivity: str = "medium"):
        # sensitivity: "high" (strict), "medium" (normal), "low" (tolerant)
        self.sensitivity = sensitivity
        if sensitivity == "high":
            self.text_sim_threshold = 0.90
            self.min_text_change_len = 10
        elif sensitivity == "low":
            self.text_sim_threshold = 0.70
            self.min_text_change_len = 40
        else:  # medium
            self.text_sim_threshold = 0.80
            self.min_text_change_len = 20

    def compare(self, doc1: DocumentModel, doc2: DocumentModel) -> DocumentComparisonReport:
        diff_items: List[DocumentDiffItem] = []

        # 1. Page Count & Additions / Removals
        p1_count = len(doc1.pages)
        p2_count = len(doc2.pages)

        added_pages = max(0, p2_count - p1_count)
        removed_pages = max(0, p1_count - p2_count)

        if p1_count != p2_count:
            diff_items.append(DocumentDiffItem(
                diff_type="page",
                change_type="modified",
                identifier="page_count",
                doc1_location=f"Total {p1_count} pages",
                doc2_location=f"Total {p2_count} pages",
                description=f"Page count changed from {p1_count} to {p2_count} ({p2_count - p1_count:+d} pages)",
                doc1_content=str(p1_count),
                doc2_content=str(p2_count)
            ))

        # 2. Structural Section Comparison (by section title / numbering)
        sec1_map: Dict[str, SectionNode] = {
            s.title.lower().strip(): s for s in doc1.sections if s.title
        }
        sec2_map: Dict[str, SectionNode] = {
            s.title.lower().strip(): s for s in doc2.sections if s.title
        }

        sections_changed_cnt = 0

        # Check removed or moved sections
        for title, s1 in sec1_map.items():
            if title not in sec2_map:
                diff_items.append(DocumentDiffItem(
                    diff_type="section",
                    change_type="removed",
                    identifier=s1.section_id,
                    doc1_location=f"Page {s1.page_num}",
                    doc2_location="Not present",
                    description=f"Section '{s1.title}' was removed in revision",
                    doc1_content=s1.title,
                    doc2_content=None
                ))
                sections_changed_cnt += 1
            else:
                s2 = sec2_map[title]
                if s1.page_num != s2.page_num:
                    diff_items.append(DocumentDiffItem(
                        diff_type="section",
                        change_type="moved",
                        identifier=s1.section_id,
                        doc1_location=f"Page {s1.page_num}",
                        doc2_location=f"Page {s2.page_num}",
                        description=f"Section '{s1.title}' moved from Page {s1.page_num} to Page {s2.page_num}",
                        doc1_content=f"Page {s1.page_num}",
                        doc2_content=f"Page {s2.page_num}"
                    ))
                    sections_changed_cnt += 1

        # Check added sections
        for title, s2 in sec2_map.items():
            if title not in sec1_map:
                diff_items.append(DocumentDiffItem(
                    diff_type="section",
                    change_type="added",
                    identifier=s2.section_id,
                    doc1_location="Not present",
                    doc2_location=f"Page {s2.page_num}",
                    description=f"New section '{s2.title}' added on Page {s2.page_num}",
                    doc1_content=None,
                    doc2_content=s2.title
                ))
                sections_changed_cnt += 1

        # 3. Table Comparison
        t1_labels = {t.label.lower().strip(): t for t in doc1.tables if t.label}
        t2_labels = {t.label.lower().strip(): t for t in doc2.tables if t.label}
        tables_changed_cnt = 0

        for lbl, t1 in t1_labels.items():
            if lbl not in t2_labels:
                diff_items.append(DocumentDiffItem(
                    diff_type="table",
                    change_type="removed",
                    identifier=t1.table_id or lbl,
                    doc1_location=f"Page {t1.page_num}",
                    doc2_location="Not present",
                    description=f"{t1.label} removed in revision",
                    doc1_content=t1.caption or t1.label
                ))
                tables_changed_cnt += 1
            else:
                t2 = t2_labels[lbl]
                if t1.caption != t2.caption and t1.caption and t2.caption:
                    diff_items.append(DocumentDiffItem(
                        diff_type="table",
                        change_type="modified",
                        identifier=t1.table_id or lbl,
                        doc1_location=f"Page {t1.page_num}",
                        doc2_location=f"Page {t2.page_num}",
                        description=f"Caption of {t1.label} modified",
                        doc1_content=t1.caption,
                        doc2_content=t2.caption
                    ))
                    tables_changed_cnt += 1

        for lbl, t2 in t2_labels.items():
            if lbl not in t1_labels:
                diff_items.append(DocumentDiffItem(
                    diff_type="table",
                    change_type="added",
                    identifier=t2.table_id or lbl,
                    doc1_location="Not present",
                    doc2_location=f"Page {t2.page_num}",
                    description=f"New table {t2.label} added on Page {t2.page_num}",
                    doc2_content=t2.caption or t2.label
                ))
                tables_changed_cnt += 1

        # 4. Figure Comparison
        f1_labels = {f.label.lower().strip(): f for f in doc1.figures if f.label}
        f2_labels = {f.label.lower().strip(): f for f in doc2.figures if f.label}
        figures_changed_cnt = 0

        for lbl, f1 in f1_labels.items():
            if lbl not in f2_labels:
                diff_items.append(DocumentDiffItem(
                    diff_type="figure",
                    change_type="removed",
                    identifier=f1.figure_id or lbl,
                    doc1_location=f"Page {f1.page_num}",
                    doc2_location="Not present",
                    description=f"{f1.label} removed in revision",
                    doc1_content=f1.caption or f1.label
                ))
                figures_changed_cnt += 1
            else:
                f2 = f2_labels[lbl]
                if f1.caption != f2.caption and f1.caption and f2.caption:
                    diff_items.append(DocumentDiffItem(
                        diff_type="figure",
                        change_type="modified",
                        identifier=f1.figure_id or lbl,
                        doc1_location=f"Page {f1.page_num}",
                        doc2_location=f"Page {f2.page_num}",
                        description=f"Caption of {f1.label} modified",
                        doc1_content=f1.caption,
                        doc2_content=f2.caption
                    ))
                    figures_changed_cnt += 1

        for lbl, f2 in f2_labels.items():
            if lbl not in f1_labels:
                diff_items.append(DocumentDiffItem(
                    diff_type="figure",
                    change_type="added",
                    identifier=f2.figure_id or lbl,
                    doc1_location="Not present",
                    doc2_location=f"Page {f2.page_num}",
                    description=f"New figure {f2.label} added on Page {f2.page_num}",
                    doc2_content=f2.caption or f2.label
                ))
                figures_changed_cnt += 1

        # 5. Textual Comparison (Page by Page or Paragraph by Paragraph)
        t1_full = doc1.full_text
        t2_full = doc2.full_text
        matcher = difflib.SequenceMatcher(None, t1_full, t2_full)
        overall_similarity = matcher.ratio()

        text_changes_cnt = 0
        p1_paras = [b.text.strip() for page in doc1.pages for b in page.blocks if len(b.text.strip()) > self.min_text_change_len]
        p2_paras = [b.text.strip() for page in doc2.pages for b in page.blocks if len(b.text.strip()) > self.min_text_change_len]

        para_matcher = difflib.SequenceMatcher(None, p1_paras, p2_paras)
        for tag, i1, i2, j1, j2 in para_matcher.get_opcodes():
            if tag == 'replace':
                diff_items.append(DocumentDiffItem(
                    diff_type="text",
                    change_type="modified",
                    identifier=f"para_replace_{i1}",
                    doc1_location=f"Block {i1+1}",
                    doc2_location=f"Block {j1+1}",
                    description=f"Modified text block ({i2 - i1} blocks replaced by {j2 - j1} blocks)",
                    doc1_content=p1_paras[i1][:120] + ("..." if len(p1_paras[i1]) > 120 else ""),
                    doc2_content=p2_paras[j1][:120] + ("..." if len(p2_paras[j1]) > 120 else ""),
                    similarity=difflib.SequenceMatcher(None, p1_paras[i1], p2_paras[j1]).ratio()
                ))
                text_changes_cnt += 1
            elif tag == 'delete':
                diff_items.append(DocumentDiffItem(
                    diff_type="text",
                    change_type="removed",
                    identifier=f"para_del_{i1}",
                    doc1_location=f"Block {i1+1}",
                    doc2_location="Not present",
                    description="Text paragraph deleted in revision",
                    doc1_content=p1_paras[i1][:120] + ("..." if len(p1_paras[i1]) > 120 else "")
                ))
                text_changes_cnt += 1
            elif tag == 'insert':
                diff_items.append(DocumentDiffItem(
                    diff_type="text",
                    change_type="added",
                    identifier=f"para_ins_{j1}",
                    doc1_location="Not present",
                    doc2_location=f"Block {j1+1}",
                    description="New text paragraph inserted in revision",
                    doc2_content=p2_paras[j1][:120] + ("..." if len(p2_paras[j1]) > 120 else "")
                ))
                text_changes_cnt += 1

        return DocumentComparisonReport(
            doc1_path=doc1.file_path,
            doc2_path=doc2.file_path,
            doc1_pages=p1_count,
            doc2_pages=p2_count,
            overall_similarity=overall_similarity,
            added_pages=added_pages,
            removed_pages=removed_pages,
            sections_changed=sections_changed_cnt,
            tables_changed=tables_changed_cnt,
            figures_changed=figures_changed_cnt,
            text_changes=text_changes_cnt,
            diff_items=diff_items
        )
