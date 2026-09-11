"""
SpecGuard Master Analysis Pipeline Orchestrator.
Coordinates document ingestion, computer vision preprocessing, and all 10 analysis engines.
Provides fine-grained stage progress events for background worker threads.
"""

import time
import uuid
from typing import List, Dict, Tuple, Optional, Callable, Any
import logging

from specguard.core.models import DocumentModel, Finding
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.formatting import FormattingAnalyzer
from specguard.analyzers.structure import StructureAnalyzer
from specguard.analyzers.toc import TOCAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.analyzers.grammar import GrammarAnalyzer
from specguard.analyzers.engineering import EngineeringAnalyzer
from specguard.analyzers.semantic import SemanticAnalyzer
from specguard.analyzers.logical import LogicalAnalyzer
from specguard.analyzers.standards import StandardsAnalyzer
from specguard.analyzers.severity import SeverityEngine
from specguard.storage.database import DatabaseManager
from specguard.storage.repositories import DocumentRepository, SessionRepository
from specguard.security.audit import AuditLogger
from specguard.repository.manager import RepositoryManager

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Executes full or selective engineering document quality and compliance analysis."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self.doc_repo = DocumentRepository(self.db)
        self.session_repo = SessionRepository(self.db)
        self.audit = AuditLogger(self.db)
        self.repo_manager = RepositoryManager(db=self.db)


        # Initialize analyzers
        self.formatting_analyzer = FormattingAnalyzer()
        self.structure_analyzer = StructureAnalyzer()
        self.toc_analyzer = TOCAnalyzer()
        self.table_analyzer = TableAnalyzer()
        self.grammar_analyzer = GrammarAnalyzer()
        self.engineering_analyzer = EngineeringAnalyzer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.logical_analyzer = LogicalAnalyzer()
        self.standards_analyzer = StandardsAnalyzer()
        self.severity_engine = SeverityEngine()

    def run_analysis(
        self,
        file_path: str,
        domain: str = "mechanical",
        selected_standards: Optional[List[str]] = None,
        enabled_modules: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Tuple[DocumentModel, List[Finding], str]:
        """
        Runs analysis pipeline with progress reporting.
        Returns: (document_model, ranked_findings, session_id)
        """
        start_time = time.time()
        session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"

        def report(stage: str, pct: int):
            if progress_callback:
                progress_callback(stage, pct)
            logger.info("[%3d%%] %s", pct, stage)

        # 1. Document Acquisition & Parsing
        report("Acquiring and parsing document...", 10)
        doc = DocumentParser.parse_file(file_path)
        self.doc_repo.save_document(doc)

        all_findings: List[Finding] = []
        context: Dict[str, Any] = {
            "domain": domain.lower(),
            "selected_standards": selected_standards or [],
            "session_id": session_id
        }

        # 2. Document Layout & Formatting Analysis
        report("Executing formatting analysis...", 25)
        try:
            fmt_findings = self.formatting_analyzer.analyze(doc, context)
            all_findings.extend(fmt_findings)
        except Exception as e:
            logger.error("FormattingAnalyzer failed: %s", e)

        # 3. Structure & Outline Hierarchy Analysis
        report("Analyzing structural outline & section hierarchy...", 35)
        try:
            str_findings = self.structure_analyzer.analyze(doc, context)
            all_findings.extend(str_findings)
        except Exception as e:
            logger.error("StructureAnalyzer failed: %s", e)

        # 4. Table of Contents Cross-Validation
        report("Cross-checking Table of Contents...", 45)
        try:
            toc_findings = self.toc_analyzer.analyze(doc, context)
            all_findings.extend(toc_findings)
        except Exception as e:
            logger.error("TOCAnalyzer failed: %s", e)

        # 5. Engineering Tables Inspection
        report("Analyzing tabular data and cell synchronicity...", 55)
        try:
            tbl_findings = self.table_analyzer.analyze(doc, context)
            all_findings.extend(tbl_findings)
        except Exception as e:
            logger.error("TableAnalyzer failed: %s", e)

        # 6. Technical Grammar & Terminology Whitelist
        report("Evaluating grammar, syntax & technical vocabulary...", 65)
        try:
            grm_findings = self.grammar_analyzer.analyze(doc, context)
            all_findings.extend(grm_findings)
        except Exception as e:
            logger.error("GrammarAnalyzer failed: %s", e)

        # 7. Engineering Parameter Extraction & Normalization
        report("Extracting domain-specific engineering parameters...", 75)
        try:
            eng_findings = self.engineering_analyzer.analyze(doc, context)
            all_findings.extend(eng_findings)
        except Exception as e:
            logger.error("EngineeringAnalyzer failed: %s", e)

        # 8. Semantic Propositions & Logical Consistency
        report("Detecting semantic propositions & cross-document contradictions...", 85)
        try:
            sem_findings = self.semantic_analyzer.analyze(doc, context)
            all_findings.extend(sem_findings)
        except Exception as e:
            logger.error("SemanticAnalyzer failed: %s", e)

        try:
            log_findings = self.logical_analyzer.analyze(doc, context)
            all_findings.extend(log_findings)
        except Exception as e:
            logger.error("LogicalAnalyzer failed: %s", e)

        # 9. Local Standards Knowledge Base Evaluation
        report("Comparing parameters against local engineering standards...", 92)
        try:
            std_findings = self.standards_analyzer.analyze(doc, context)
            all_findings.extend(std_findings)
        except Exception as e:
            logger.error("StandardsAnalyzer failed: %s", e)

        # 10. Severity Prioritization & Ranking
        report("Computing severity scores and ranking critical issues...", 98)
        ranked_findings = self.severity_engine.rank_findings(all_findings)

        duration_ms = int((time.time() - start_time) * 1000)

        # Archive immutable comparison into Repository
        try:
            cmp_record = self.repo_manager.archive_comparison(
                doc_model=doc,
                findings=ranked_findings,
                domain=domain,
                standards=selected_standards or [],
                duration_ms=duration_ms
            )
            session_id = cmp_record.comparison_id
        except Exception as repo_err:
            logger.error("Failed archiving comparison into repository: %s", repo_err)

        # Save to SQLite database
        self.session_repo.save_session(
            session_id=session_id,
            doc_hash=doc.file_hash,
            domain=domain,
            standards=selected_standards or [],
            findings=ranked_findings,
            duration_ms=duration_ms
        )

        # Record audit log
        self.audit.log(
            user_action="ANALYZE_DOCUMENT",
            document_hash=doc.file_hash,
            details=f"Session {session_id}, Domain: {domain}, Findings: {len(ranked_findings)}, Duration: {duration_ms}ms"
        )

        report("Analysis complete.", 100)
        return doc, ranked_findings, session_id

