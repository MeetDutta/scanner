"""
Application configuration and directory management for SpecGuard.
Strictly 100% offline.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any

# Root application directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application storage paths
DATA_DIR = BASE_DIR / "data"
STANDARDS_DIR = BASE_DIR / "standards"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
DATASETS_DIR = BASE_DIR / "datasets"
DEMO_SAMPLES_DIR = BASE_DIR / "demo_samples"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "specguard.db"

# Ensure essential runtime directories exist
for directory in [DATA_DIR, STANDARDS_DIR, MODELS_DIR, REPORTS_DIR, DATASETS_DIR, DEMO_SAMPLES_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


@dataclass
class SeverityWeights:
    """Weights for calculating priority score of detected findings."""
    severity: float = 3.0
    safety_impact: float = 2.5
    deviation_magnitude: float = 2.0
    standard_criticality: float = 2.0
    confidence: float = 1.0
    cross_document_impact: float = 1.5


@dataclass
class AppConfig:
    """SpecGuard core application runtime configuration."""
    app_name: str = "SpecGuard"
    version: str = "1.0.0"
    offline_mode: bool = True  # NON-NEGOTIABLE: Always True
    min_confidence_threshold: float = 0.50
    active_domain: str = "mechanical"  # 'mechanical', 'chemical', 'electrical'
    selected_standards: list = field(default_factory=list)
    weights: SeverityWeights = field(default_factory=SeverityWeights)
    highlight_colors: Dict[str, str] = field(default_factory=lambda: {
        "Critical": "#DC2626",      # Vibrant red
        "High": "#EA580C",          # High-visibility orange
        "Medium": "#EAB308",        # Amber yellow
        "Low": "#3B82F6",           # Blue
        "Informational": "#6B7280"  # Gray
    })


# Global default configuration instance
DEFAULT_CONFIG = AppConfig()
