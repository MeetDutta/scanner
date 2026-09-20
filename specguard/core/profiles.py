"""
Document Profiles and Standards Configuration for SpecGuard.

Defines rules, section expectations, layout constraints, and compliance criteria
for Mechanical, Electrical, Chemical, IEEE Research Papers, and Generic Academic documents.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ProfileConfig:
    profile_id: str
    display_name: str
    domain: str  # Mechanical, Electrical, Chemical, Academic, General
    description: str
    requires_toc: bool = False
    toc_min_pages: int = 5  # Only recommend TOC if page count >= this
    required_sections: List[str] = field(default_factory=list)
    optional_sections: List[str] = field(default_factory=list)
    section_numbering_style: str = "numeric"  # "numeric" (1., 1.1), "roman" (I., A.), "any"
    expected_layout: str = "any"  # "single_column", "two_column", "any"
    citation_style: str = "any"  # "ieee" ([1]), "author_year" (Smith et al.), "any"
    table_caption_position: str = "above"  # "above", "below", "any"
    figure_caption_position: str = "below"  # "below", "above", "any"
    validate_equations: bool = False
    validate_cross_references: bool = True
    custom_rules: Dict[str, Any] = field(default_factory=dict)


PROFILES: Dict[str, ProfileConfig] = {
    "mechanical": ProfileConfig(
        profile_id="mechanical",
        display_name="Mechanical Engineering Specification",
        domain="Mechanical",
        description="Specifications for mechanical parts, tolerances, fabrication, and assemblies (ASME/ISO).",
        requires_toc=False,
        toc_min_pages=5,
        required_sections=["Scope", "Requirements", "Testing"],
        optional_sections=["Materials", "Tolerances", "Fabrication", "Quality Assurance", "References"],
        section_numbering_style="numeric",
        expected_layout="single_column",
        citation_style="any",
        table_caption_position="above",
        figure_caption_position="below",
        validate_cross_references=True
    ),
    "electrical": ProfileConfig(
        profile_id="electrical",
        display_name="Electrical Engineering Specification",
        domain="Electrical",
        description="Power systems, circuits, schematics, voltage/frequency ratings (IEEE 315 / IEC 60617).",
        requires_toc=False,
        toc_min_pages=5,
        required_sections=["Scope", "Requirements", "Testing"],
        optional_sections=["System Architecture", "Power Ratings", "Safety & Protection", "Verification"],
        section_numbering_style="numeric",
        expected_layout="single_column",
        citation_style="any",
        table_caption_position="above",
        figure_caption_position="below",
        validate_cross_references=True
    ),
    "chemical": ProfileConfig(
        profile_id="chemical",
        display_name="Chemical Engineering Specification",
        domain="Chemical",
        description="Process specifications, P&ID, mass & energy balances, operating limits (ISA-5.1).",
        requires_toc=False,
        toc_min_pages=5,
        required_sections=["Scope", "Requirements", "Testing"],
        optional_sections=["Process Description", "Mass & Energy Balance", "Operating Conditions", "Safety & Environmental"],
        section_numbering_style="numeric",
        expected_layout="single_column",
        citation_style="any",
        table_caption_position="above",
        figure_caption_position="below",
        validate_cross_references=True
    ),
    "ieee_research": ProfileConfig(
        profile_id="ieee_research",
        display_name="IEEE Research Paper",
        domain="Academic",
        description="IEEE Journal and Conference paper formats with two-column layout, Roman headings, and bracket citations.",
        requires_toc=False,  # IEEE papers specifically do not have a conventional TOC
        toc_min_pages=9999,
        required_sections=["Abstract", "Introduction", "Conclusion", "References"],
        optional_sections=["Related Work", "Methodology", "System Model", "Proposed Architecture", "Results", "Discussion", "Acknowledgment", "Appendix"],
        section_numbering_style="roman",
        expected_layout="two_column",
        citation_style="ieee",
        table_caption_position="above",
        figure_caption_position="below",
        validate_equations=True,
        validate_cross_references=True,
        custom_rules={
            "ieee_format": "conference_or_journal",
            "require_abstract": True,
            "require_keywords": False,
            "table_label_prefix": "TABLE",
            "figure_label_prefix": "Fig.",
            "equation_label_pattern": r"\(\d+\)"
        }
    ),
    "generic_academic": ProfileConfig(
        profile_id="generic_academic",
        display_name="Generic Academic Document",
        domain="Academic",
        description="Academic theses, manuscripts, and reports requiring abstracts, literature review, and formal citations.",
        requires_toc=False,
        toc_min_pages=8,
        required_sections=["Abstract", "Introduction", "References"],
        optional_sections=["Literature Review", "Methodology", "Results", "Discussion", "Conclusion"],
        section_numbering_style="any",
        expected_layout="any",
        citation_style="any",
        table_caption_position="above",
        figure_caption_position="below",
        validate_equations=True,
        validate_cross_references=True
    ),
    "custom": ProfileConfig(
        profile_id="custom",
        display_name="Custom Engineering Document",
        domain="General",
        description="Configurable rule set for proprietary engineering documents and templates.",
        requires_toc=False,
        toc_min_pages=10,
        required_sections=[],
        optional_sections=[],
        section_numbering_style="any",
        expected_layout="any",
        citation_style="any",
        validate_cross_references=True
    )
}


class ProfileRegistry:
    """Provides access and resolution for document compliance profiles."""

    @classmethod
    def get_profile(cls, profile_id: Optional[str] = None) -> ProfileConfig:
        if not profile_id:
            return PROFILES["mechanical"]
        pid = profile_id.lower().strip()
        return PROFILES.get(pid, PROFILES["mechanical"])

    @classmethod
    def list_profiles(cls) -> List[Dict[str, Any]]:
        return [
            {
                "profile_id": p.profile_id,
                "display_name": p.display_name,
                "domain": p.domain,
                "description": p.description,
                "requires_toc": p.requires_toc,
                "expected_layout": p.expected_layout,
                "citation_style": p.citation_style,
                "required_sections": p.required_sections
            }
            for p in PROFILES.values()
        ]
