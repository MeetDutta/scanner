"""
DocReady — An Offline Intranet Platform for Template-Aware Document Formatting Analysis and Readiness Verification.

This package provides top-level access to all DocReady document intelligence modules
while maintaining 100% backward compatibility with existing specguard namespaces.
"""

import sys
import importlib

__version__ = "1.0.0"
__author__ = "DocReady Engineering & Quality Intelligence Team"
__title__ = "DocReady — Offline Intranet Platform for Template-Aware Document Formatting Analysis and Readiness Verification"

# Subpackages to alias
_SUBPACKAGES = [
    "core",
    "analyzers",
    "templates",
    "server",
    "export",
    "storage",
    "training",
    "models",
    "repository",
    "security",
    "gui",
    "web",
]

# Ensure specguard is imported
import specguard

# Automatically map docready.<subpackage> to specguard.<subpackage> in sys.modules
for subpkg in _SUBPACKAGES:
    target_name = f"specguard.{subpkg}"
    alias_name = f"docready.{subpkg}"
    try:
        mod = importlib.import_module(target_name)
        sys.modules[alias_name] = mod
        globals()[subpkg] = mod
    except Exception:
        pass


def __getattr__(name: str):
    """Fallback dynamic attribute lookup delegating to specguard."""
    if hasattr(specguard, name):
        return getattr(specguard, name)
    try:
        return importlib.import_module(f"specguard.{name}")
    except ImportError:
        raise AttributeError(f"module 'docready' has no attribute '{name}'")
