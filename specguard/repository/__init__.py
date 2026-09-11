"""
SpecGuard Local Document Comparison Repository & History Engine.
100% Offline, Immutable Comparison Sessions, Revisions, and Full-Text Search.
"""

from specguard.repository.models import RepositoryDocument, ComparisonRecord, VersionComparisonDiff
from specguard.repository.manager import RepositoryManager
from specguard.repository.search import RepositorySearchEngine
from specguard.repository.diff_engine import VersionDiffEngine
from specguard.repository.backup import RepositoryBackupEngine
