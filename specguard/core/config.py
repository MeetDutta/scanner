"""
Application configuration and directory management for SpecGuard.
Strictly 100% offline.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any

from specguard.core.runtime_paths import (
    get_app_dir,
    get_data_dir,
    get_resource_dir,
    get_database_path,
    get_reports_dir,
    get_uploads_dir,
    get_log_file_path,
    get_web_dir,
    get_repository_dir,
    is_frozen,
)

# Root application directory (frozen-aware)
BASE_DIR = get_app_dir()

# Persistent user data paths
DATA_DIR = get_data_dir()
REPORTS_DIR = get_reports_dir()
LOGS_DIR = get_data_dir("logs")
UPLOADS_DIR = get_uploads_dir()
DB_PATH = get_database_path()
REPO_DIR = get_repository_dir()

# Bundled application resource paths
STANDARDS_DIR = get_resource_dir("standards")
MODELS_DIR = get_resource_dir("models")
DATASETS_DIR = get_resource_dir("datasets")
DEMO_SAMPLES_DIR = get_resource_dir("demo_samples")
TEMPLATES_DIR = get_resource_dir("templates")
RULES_DIR = get_resource_dir("rules")
WEB_DIR = get_web_dir()

# Ensure writable runtime directories exist
for directory in [DATA_DIR, REPORTS_DIR, LOGS_DIR, UPLOADS_DIR]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


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
