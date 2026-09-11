"""
Abstract Base Interface for all SpecGuard Analysis Engines.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from specguard.core.models import DocumentModel, Finding, FindingCategory


class BaseAnalyzer(ABC):
    """
    Abstract contract for all SpecGuard document analyzers.
    Ensures modular, independently callable analysis execution.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the analyzer."""
        pass

    @property
    @abstractmethod
    def category(self) -> FindingCategory:
        """Finding category associated with this analyzer."""
        pass

    @abstractmethod
    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        """
        Executes analysis on the document and returns explainable findings.
        Must not raise unhandled exceptions; errors should be caught and logged.
        """
        pass
