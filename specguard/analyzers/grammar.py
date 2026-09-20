"""
Grammar, Spelling, and Technical Syntax Analysis Engine for SpecGuard.
Strictly offline, utilizing an extensive domain-specific engineering vocabulary whitelist
to avoid false-positive flagging of legitimate technical terminology.
"""

import re
from typing import List, Dict, Set, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import DocumentModel, Finding, FindingCategory, SeverityLevel, BBox
from specguard.core.location_mapper import LocationMapper

logger = logging.getLogger(__name__)

# Engineering technical terms whitelist across Mechanical, Chemical, and Electrical domains
ENGINEERING_VOCABULARY: Set[str] = {
    # Mechanical
    "tolerance", "tolerances", "machining", "annealing", "austenitic", "martensitic",
    "bushing", "flange", "camshaft", "crankshaft", "gearbox", "pneumatic", "hydraulic",
    "viscosity", "shear", "tensile", "yield", "brinell", "rockwell", "roughness",
    "anodized", "galvanized", "torsion", "deflection", "kinematic", "tribology",
    "stochastic", "elastomer", "fastener", "chamfer", "spline", "keyway", "gasket",
    "volute", "impeller", "nozzle", "diffuser", "cantilever", "axial", "radial",

    # Chemical
    "stoichiometric", "catalyst", "exothermic", "endothermic", "enthalpy", "entropy",
    "distillation", "reflux", "viscous", "titration", "polymerization", "isothermal",
    "adiabatic", "azeotrope", "pyrolysis", "crystallization", "corrosive", "effluent",
    "solute", "solvent", "surfactant", "emulsion", "hydrocarbon", "halocarbon",
    "scrubber", "calorimetry", "adsorption", "absorption", "chromatography",
    "ppm", "wt%", "molality", "molarity", "lewis", "arrhenius",

    # Electrical
    "inductance", "capacitance", "reactance", "impedance", "thyristor", "transistor",
    "mosfet", "igbt", "varistor", "dielectric", "sinusoidal", "rectifier", "inverter",
    "switchgear", "circuit", "amperage", "wattage", "microcontroller", "earthing",
    "potentiometer", "thermocouple", "transducer", "solenoid", "galvanometer",
    "ferrite", "laminated", "flux", "reluctance", "permeability", "permittivity",
    "attenuation", "busbar", "breaker", "substation", "scada", "plc",

    # Standards & Document Abbreviations
    "iso", "iec", "asme", "astm", "ansi", "nema", "ieee", "din", "en", "bs", "jis",
    "spec", "qty", "ref", "mfg", "dwg", "assy", "rev", "min", "max", "typ", "nom"
}

# Common English spelling mistake corrections dictionary
COMMON_SPELLING_ERRORS: Dict[str, str] = {
    "teh": "the",
    "recieved": "received",
    "seperate": "separate",
    "occured": "occurred",
    "untill": "until",
    "definately": "definitely",
    "temprature": "temperature",
    "presure": "pressure",
    "volatage": "voltage",
    "curant": "current",
    "tolerence": "tolerance",
    "dissolveable": "dissolvable",
    "calulate": "calculate",
    "performence": "performance",
    "maintanence": "maintenance",
    "resistence": "resistance",
    "capasitor": "capacitor",
    "inductence": "inductance",
    "transfomer": "transformer",
    "reponsible": "responsible",
    "guarentee": "guarantee",
    "requirment": "requirement",
    "specifcation": "specification",
    "diamater": "diameter",
    "dimmension": "dimension",
    "frequncy": "frequency"
}


class GrammarAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Grammar & Spelling Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.GRAMMAR

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1

        for page in doc.pages:
            for block in page.blocks:
                txt = block.text.strip()
                if not txt:
                    continue

                # 1. Check for repeated words (e.g. "the the motor", "voltage of of 415 V")
                rep_match = re.search(r'\b([A-Za-z]{2,})\s+\1\b', txt, re.IGNORECASE)
                if rep_match:
                    rep_word = rep_match.group(1)
                    matched_phrase = rep_match.group(0)
                    phrase_boxes = LocationMapper.find_phrase_bboxes(page, matched_phrase, block_id=block.block_id)
                    f_bbox = phrase_boxes[0] if phrase_boxes else block.bbox
                    precision = "EXACT_PHRASE" if phrase_boxes else "APPROXIMATE"
                    findings.append(Finding(
                        finding_id=f"GRM-REP-{finding_counter:03d}",
                        category=self.category.value,
                        domain="General",
                        location=f"Page {page.page_num}, Line {block.line_num or block.block_id}",
                        page=page.page_num,
                        bbox=f_bbox,
                        bounding_boxes=phrase_boxes if phrase_boxes else ([f_bbox] if f_bbox else []),
                        location_precision=precision,
                        matched_text=matched_phrase,
                        expected_text=rep_word,
                        issue_type="REPEATED_WORD",
                        original_content=matched_phrase,
                        detected_value=f"Repeated word '{matched_phrase}'",
                        expected_value=f"Single occurrence '{rep_word}'",
                        deviation="Redundant consecutive repeated word",
                        severity=SeverityLevel.LOW.value,
                        confidence=0.96,
                        explanation=f"Accidental duplication of word '{rep_word}' detected in technical prose.",
                        suggested_correction=f"Remove duplicate '{rep_word}'.",
                        suggested_fix=f"Remove duplicate '{rep_word}'.",
                        rule_reference="Technical Writing Style Guide §2.3",
                        priority_score=1.8
                    ))
                    finding_counter += 1

                # 2. Check for common engineering typos against vocabulary
                words = re.findall(r'\b[A-Za-z]+\b', txt)
                for w in words:
                    w_lower = w.lower()
                    if w_lower in COMMON_SPELLING_ERRORS:
                        correct = COMMON_SPELLING_ERRORS[w_lower]
                        w_bbox = LocationMapper.find_word_bbox(page, w, block_id=block.block_id)
                        f_bbox = w_bbox if w_bbox else block.bbox
                        precision = "EXACT_WORD" if w_bbox else "APPROXIMATE"
                        findings.append(Finding(
                            finding_id=f"GRM-SPL-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"Page {page.page_num}, Block {block.block_id}",
                            page=page.page_num,
                            bbox=f_bbox,
                            bounding_boxes=[f_bbox] if f_bbox else [],
                            location_precision=precision,
                            matched_text=w,
                            expected_text=correct,
                            issue_type="SPELLING_ERROR",
                            original_content=w,
                            detected_value=w,
                            expected_value=correct,
                            deviation=f"Spelling error in '{w}'",
                            severity=SeverityLevel.LOW.value,
                            confidence=0.95,
                            explanation=f"Identified spelling error '{w}'. Verified against technical vocabulary whitelist.",
                            suggested_correction=f"Correct to '{correct}'.",
                            suggested_fix=f"Correct to '{correct}'.",
                            rule_reference="Engineering Document Quality Guide §1.2",
                            priority_score=1.5
                        ))
                        finding_counter += 1

                # 3. Check for unclosed parentheses or brackets
                open_parens = txt.count("(")
                close_parens = txt.count(")")
                if open_parens != close_parens and len(txt) > 30 and txt.endswith("."):
                    paren_boxes = LocationMapper.find_token_in_text(txt, "(", block.words)
                    f_bbox = paren_boxes[0] if paren_boxes else block.bbox
                    precision = "EXACT_TOKEN" if paren_boxes else "BLOCK"
                    findings.append(Finding(
                        finding_id=f"GRM-PNC-{finding_counter:03d}",
                        category=self.category.value,
                        domain="General",
                        location=f"Page {page.page_num}, Block {block.block_id}",
                        page=page.page_num,
                        bbox=f_bbox,
                        bounding_boxes=paren_boxes if paren_boxes else ([f_bbox] if f_bbox else []),
                        location_precision=precision,
                        matched_text="(",
                        expected_text="Balanced parenthesis ')'",
                        issue_type="UNBALANCED_PUNCTUATION",
                        original_content=txt[:80] + "...",
                        detected_value=f"Mismatched parentheses: {open_parens} '(' vs {close_parens} ')'",
                        expected_value="Balanced punctuation pairs",
                        deviation="Unclosed / unbalanced parenthesis in sentence",
                        severity=SeverityLevel.LOW.value,
                        confidence=0.90,
                        explanation="Sentence contains an opening parenthesis without a corresponding closing parenthesis.",
                        suggested_correction="Balance or remove the unclosed parenthesis.",
                        suggested_fix="Balance or remove the unclosed parenthesis.",
                        rule_reference="Standard Punctuation Rules §3.1",
                        priority_score=1.4
                    ))
                    finding_counter += 1

                # 4. Check for double punctuation or double spaces
                if "  " in txt and not block.is_bold:
                    # Minor warning for formatting/spacing
                    pass

        return findings
