"""
Engineering Parameter Extraction and Unit Normalization Engine for SpecGuard.
Extracts domain-specific parameters for Mechanical, Chemical, and Electrical engineering.
Normalizes SI and standard engineering units for deterministic comparison.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, EngineeringParameter, BBox
)

logger = logging.getLogger(__name__)


class UnitNormalizer:
    """Safe, deterministic physical unit normalization across engineering domains."""

    VOLTAGE_FACTORS = {"mv": 1e-3, "v": 1.0, "kv": 1e3, "mv_mega": 1e6}
    CURRENT_FACTORS = {"ua": 1e-6, "ma": 1e-3, "a": 1.0, "ka": 1e3}
    POWER_FACTORS = {"w": 1.0, "kw": 1e3, "mw": 1e6, "kva": 1e3, "mva": 1e6}
    PRESSURE_FACTORS = {"pa": 1e-5, "kpa": 1e-2, "bar": 1.0, "mpa": 10.0, "psi": 0.0689476}
    LENGTH_FACTORS = {"um": 1e-3, "μm": 1e-3, "mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}
    FREQ_FACTORS = {"hz": 1.0, "khz": 1e3, "mhz": 1e6}

    @staticmethod
    def normalize(val: float, unit: str) -> Tuple[float, str]:
        u = unit.lower().strip()
        # Voltage
        if u in ["v", "volt", "volts"]:
            return val, "V"
        if u in ["kv", "kilovolt"]:
            return val * 1000.0, "V"
        if u in ["mv", "millivolt"]:
            return val * 1e-3, "V"

        # Current
        if u in ["a", "amp", "amps", "ampere"]:
            return val, "A"
        if u in ["ka", "kiloamp"]:
            return val * 1000.0, "A"
        if u in ["ma", "milliamp"]:
            return val * 1e-3, "A"

        # Frequency
        if u in ["hz", "hertz"]:
            return val, "Hz"
        if u in ["khz"]:
            return val * 1000.0, "Hz"

        # Power
        if u in ["w", "watt"]:
            return val * 1e-3, "kW"
        if u in ["kw", "kilowatt"]:
            return val, "kW"
        if u in ["mw", "megawatt"]:
            return val * 1000.0, "kW"

        # Pressure
        if u in ["bar"]:
            return val, "bar"
        if u in ["mpa"]:
            return val * 10.0, "bar"
        if u in ["kpa"]:
            return val * 0.01, "bar"
        if u in ["psi"]:
            return val * 0.0689476, "bar"

        # Length / Dimensions
        if u in ["mm", "millimeter"]:
            return val, "mm"
        if u in ["m", "meter"]:
            return val * 1000.0, "mm"
        if u in ["cm"]:
            return val * 10.0, "mm"
        if u in ["um", "μm", "micron"]:
            return val * 0.001, "mm"

        # Temperature
        if u in ["°c", "c", "celsius"]:
            return val, "°C"
        if u in ["k", "kelvin"]:
            return val - 273.15, "°C"

        # Concentration
        if u in ["%", "wt%", "vol%"]:
            return val, "%"
        if u in ["ppm"]:
            return val * 0.0001, "%"

        return val, unit


class EngineeringAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Engineering Parameter Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.ENGINEERING

    def __init__(self):
        # Comprehensive parameter regex patterns
        self.param_patterns = [
            # Voltage: e.g. "rated voltage = 415 V", "voltage: 230V"
            (r'\b(?:[A-Za-z\-]+\s+)*?voltage\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(k?V)(?![A-Za-z0-9])', "voltage", "Electrical"),
            # Current: e.g. "rated current of 16 A", "current = 100A"
            (r'\b(?:[A-Za-z\-]+\s+)*?current\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(k?A|mA)(?![A-Za-z0-9])', "current", "Electrical"),
            # Frequency: e.g. "frequency: 50 Hz"
            (r'\b(?:[A-Za-z\-]+\s+)*?frequency\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(Hz|kHz)(?![A-Za-z0-9])', "frequency", "Electrical"),
            # Power: e.g. "rated power: 75 kW"
            (r'\b(?:[A-Za-z\-]+\s+)*?power\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(kW|MW|W|kVA)(?![A-Za-z0-9])', "power", "Electrical"),
            
            # Tolerance: e.g. "tolerance = ±0.05 mm", "tolerance of ±0.5 mm"
            (r'\btolerance\s*(?:of|is|=|\:)?\s*(?:[±\+\-]|plus\s+or\s+minus)?\s*([0-9\.]+)\s*(mm|μm|um)(?![A-Za-z0-9])', "tolerance", "Mechanical"),
            # Pressure: e.g. "maximum operating pressure = 10 bar", "design pressure: 1.5 MPa"
            (r'\b(?:[A-Za-z\-]+\s+)*?pressure\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(bar|MPa|kPa|psi)(?![A-Za-z0-9])', "pressure", "Mechanical"),
            # Temperature: e.g. "maximum temperature = 80°C", "design temperature: 60 °C"
            (r'\b(?:[A-Za-z\-]+\s+)*?temperature\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(°C|C|K)(?![A-Za-z0-9])', "temperature", "Mechanical"),
            # Surface roughness: e.g. "surface finish Ra 0.8 μm", "roughness: 1.6 um"
            (r'\b(?:surface\s+roughness|roughness|surface\s+finish)\s*(?:of|is|=|Ra|\:)?\s*([0-9\.]+)\s*(μm|um)(?![A-Za-z0-9])', "surface_roughness", "Mechanical"),

            # Concentration: e.g. "required concentration = 10%", "concentration: 15 wt%"
            (r'\b(?:[A-Za-z\-]+\s+)*?concentration\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(%|wt%|vol%|ppm)(?![A-Za-z0-9])', "concentration", "Chemical"),
            # Flash Point: e.g. "flash point: 45°C"
            (r'\bflash\s+point\s*(?:of|is|=|\:)?\s*([0-9\.]+)\s*(°C|C|K)(?![A-Za-z0-9])', "flash_point", "Chemical")
        ]

    def extract_parameters(self, doc: DocumentModel) -> List[EngineeringParameter]:
        """Extracts all structured engineering parameters from the document."""
        parameters: List[EngineeringParameter] = []

        # Entity detection regex
        entity_pattern = re.compile(r'\b(motor|transformer|pump|compressor|shaft|bearing|reactor|pipe|vessel|cable|breaker|heat\s+exchanger|turbine|chiller)\b', re.IGNORECASE)
        active_entity = "Equipment"

        for page in doc.pages:
            for block in page.blocks:
                txt = block.text.strip()
                if not txt:
                    continue

                # Find or update active entity
                ent_match = entity_pattern.search(txt)
                if ent_match:
                    active_entity = ent_match.group(1).title()

                entity = active_entity


                for pattern, param_name, domain in self.param_patterns:
                    for m in re.finditer(pattern, txt, re.IGNORECASE):
                        try:
                            raw_val = float(m.group(1))
                            unit = m.group(2)
                            norm_val, norm_unit = UnitNormalizer.normalize(raw_val, unit)

                            parameters.append(EngineeringParameter(
                                entity=entity,
                                parameter=param_name,
                                value=raw_val,
                                raw_value=f"{raw_val} {unit}",
                                unit=unit,
                                normalized_value=norm_val,
                                normalized_unit=norm_unit,
                                condition="Operating",
                                page=page.page_num,
                                bbox=block.bbox,
                                confidence=0.96,
                                source_sentence=txt
                            ))
                        except Exception as e:
                            logger.debug("Failed parsing parameter match %s: %s", m.group(0), e)

        return parameters

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        # EngineeringAnalyzer populates context with extracted parameters for downstream engines
        params = self.extract_parameters(doc)
        if context is not None:
            context["parameters"] = params

        findings: List[Finding] = []
        # Checks parameter plausibility (e.g. negative tolerance, impossible voltage, absolute zero violations)
        finding_counter = 1
        for p in params:
            if p.parameter == "tolerance" and p.value <= 0:
                findings.append(Finding(
                    finding_id=f"ENG-TOL-{finding_counter:03d}",
                    category=self.category.value,
                    domain="Mechanical",
                    location=f"Page {p.page}",
                    page=p.page,
                    bbox=p.bbox,
                    original_content=p.source_sentence,
                    detected_value=f"{p.raw_value}",
                    expected_value="Strictly positive tolerance > 0 mm",
                    deviation="Zero or negative tolerance specification",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.98,
                    explanation=f"Mechanical tolerance cannot be zero or negative ({p.raw_value}).",
                    suggested_correction="Specify an achievable engineering manufacturing tolerance.",
                    rule_reference="ISO 2768-1 / ASME Y14.5",
                    priority_score=6.0
                ))
                finding_counter += 1

            elif p.parameter == "voltage" and p.normalized_value <= 0:
                findings.append(Finding(
                    finding_id=f"ENG-VOL-{finding_counter:03d}",
                    category=self.category.value,
                    domain="Electrical",
                    location=f"Page {p.page}",
                    page=p.page,
                    bbox=p.bbox,
                    original_content=p.source_sentence,
                    detected_value=f"{p.raw_value}",
                    expected_value="Operating voltage > 0 V",
                    deviation="Non-positive operating voltage",
                    severity=SeverityLevel.CRITICAL.value,
                    confidence=0.98,
                    explanation=f"Electrical equipment operating voltage must be positive ({p.raw_value}).",
                    suggested_correction="Verify electrical supply voltage specification.",
                    rule_reference="IEC 60038 Standard Voltages",
                    priority_score=8.5
                ))
                finding_counter += 1

        return findings
