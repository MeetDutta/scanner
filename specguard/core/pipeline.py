"""
SpecGuard Master Analysis Pipeline Orchestrator.
Coordinates document ingestion, computer vision preprocessing, and all 10 analysis engines.
Provides fine-grained stage progress events for background worker threads.
"""

import time
import uuid
import gc
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Callable, Any
import logging

from specguard.core.models import DocumentModel, Finding
from specguard.core.document_parser import DocumentParser
from specguard.analyzers.formatting import FormattingAnalyzer
from specguard.analyzers.structure import StructureAnalyzer
from specguard.analyzers.toc import TOCAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.analyzers.figures import FigureAnalyzer
from specguard.analyzers.equations import EquationAnalyzer
from specguard.analyzers.cross_references import CrossReferenceAnalyzer
from specguard.analyzers.ieee import IEEEAnalyzer
from specguard.analyzers.grammar import GrammarAnalyzer
from specguard.analyzers.engineering import EngineeringAnalyzer
from specguard.analyzers.semantic import SemanticAnalyzer
from specguard.analyzers.logical import LogicalAnalyzer
from specguard.analyzers.standards import StandardsAnalyzer
from specguard.analyzers.severity import SeverityEngine
from specguard.analyzers.template_analyzer import TemplateAnalyzer
from specguard.templates.manager import TemplateManager
from specguard.core.profiles import ProfileRegistry
from specguard.storage.database import DatabaseManager
from specguard.storage.repositories import DocumentRepository, SessionRepository
from specguard.security.audit import AuditLogger
from specguard.repository.manager import RepositoryManager

from specguard.analyzers.custom_template_analyzer import CustomTemplateAnalyzer

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Executes full or selective engineering document quality and compliance analysis."""

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        custom_template_manager: Optional[Any] = None
    ):
        self.db = db or DatabaseManager()
        self.doc_repo = DocumentRepository(self.db)
        self.session_repo = SessionRepository(self.db)
        self.audit = AuditLogger(self.db)
        self.repo_manager = RepositoryManager(db=self.db)

        # Initialize analyzers
        self.template_analyzer = TemplateAnalyzer()
        self.custom_template_analyzer = CustomTemplateAnalyzer(template_manager=custom_template_manager)
        self.formatting_analyzer = FormattingAnalyzer()
        self.structure_analyzer = StructureAnalyzer()
        self.toc_analyzer = TOCAnalyzer()
        self.table_analyzer = TableAnalyzer()
        self.figure_analyzer = FigureAnalyzer()
        self.equation_analyzer = EquationAnalyzer()
        self.cross_ref_analyzer = CrossReferenceAnalyzer()
        self.ieee_analyzer = IEEEAnalyzer()
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
        profile: Optional[str] = None,
        selected_standards: Optional[List[str]] = None,
        enabled_modules: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        cancellation_token: Optional[Any] = None,
        deep_analysis: bool = False
    ) -> Tuple[DocumentModel, List[Finding], str]:
        """
        Runs analysis pipeline with progress reporting and cancellation support.
        Returns: (document_model, ranked_findings, session_id)
        """
        start_time = time.time()
        analysis_started_at = datetime.now(timezone.utc).isoformat()
        session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"

        profile_id = (profile or domain).lower().strip()
        profile_config = ProfileRegistry.get_profile(profile_id)

        def check_cancellation():
            if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                raise InterruptedError("Analysis was cancelled by user.")

        def report(stage: str, pct: int):
            check_cancellation()
            if progress_callback:
                progress_callback(stage, pct)
            logger.info("[%3d%%] %s", pct, stage)

        # 1. Document Acquisition & Parsing
        report("Acquiring and parsing document...", 5)
        def parse_progress(cur, tot, msg):
            pct = 5 + int((cur / max(1, tot)) * 15)
            report(f"Parsing page {cur}/{tot}...", pct)

        doc = DocumentParser.parse_file(
            file_path,
            progress_callback=parse_progress,
            cancellation_token=cancellation_token,
            deep_analysis=deep_analysis
        )
        doc.profile_name = profile_config.profile_id
        self.doc_repo.save_document(doc)

        template = TemplateManager.get_template(domain)

        all_findings: List[Finding] = []
        context: Dict[str, Any] = {
            "domain": profile_config.domain.lower(),
            "profile": profile_config.profile_id,
            "selected_standards": selected_standards or [],
            "session_id": session_id,
            "template": template
        }

        # 2. Document Layout & Formatting Analysis
        report("Executing formatting analysis...", 22)
        try:
            all_findings.extend(self.formatting_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("FormattingAnalyzer failed: %s", e)
        check_cancellation()

        # 3. Structure & Outline Hierarchy Analysis
        report("Analyzing structural outline & section hierarchy...", 28)
        try:
            all_findings.extend(self.structure_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("StructureAnalyzer failed: %s", e)
        check_cancellation()

        # 4. Table of Contents Cross-Validation
        report("Cross-checking Table of Contents...", 35)
        try:
            all_findings.extend(self.toc_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("TOCAnalyzer failed: %s", e)
        check_cancellation()

        # 5. Tables Inspection & Continuity
        report("Analyzing tabular data and cell synchronicity...", 42)
        try:
            all_findings.extend(self.table_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("TableAnalyzer failed: %s", e)
        check_cancellation()

        # 6. Figures & Diagrams Validation
        report("Analyzing figures, charts, and diagrams...", 50)
        try:
            all_findings.extend(self.figure_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("FigureAnalyzer failed: %s", e)
        check_cancellation()

        # 7. Mathematical Equations Inspection
        report("Inspecting mathematical equations & labels...", 56)
        try:
            all_findings.extend(self.equation_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("EquationAnalyzer failed: %s", e)
        check_cancellation()

        # 8. Document-Wide Citation & Cross-Reference Resolution
        report("Resolving document-wide citation & cross-reference graph...", 64)
        try:
            all_findings.extend(self.cross_ref_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("CrossReferenceAnalyzer failed: %s", e)
        check_cancellation()

        # 9. Technical Grammar & Terminology Whitelist
        report("Evaluating grammar, syntax & technical vocabulary...", 70)
        try:
            all_findings.extend(self.grammar_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("GrammarAnalyzer failed: %s", e)
        check_cancellation()

        # 10. Engineering Parameter Extraction & Normalization
        report("Extracting domain-specific engineering parameters...", 76)
        try:
            eng_findings = self.engineering_analyzer.analyze(doc, context)
            all_findings.extend(eng_findings)
            context["parameters"] = getattr(self.engineering_analyzer, "extract_parameters", lambda d: [])(doc)
        except Exception as e:
            logger.error("EngineeringAnalyzer failed: %s", e)
        check_cancellation()

        # 11. Template Validation (if applicable)
        report("Validating fixed engineering template...", 80)
        try:
            all_findings.extend(self.template_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("TemplateAnalyzer failed: %s", e)
        check_cancellation()

        # 12. IEEE Research Paper Compliance (if IEEE profile)
        if profile_config.profile_id == "ieee_research":
            report("Validating IEEE research paper formatting & style...", 84)
            try:
                all_findings.extend(self.ieee_analyzer.analyze(doc, context))
            except Exception as e:
                logger.error("IEEEAnalyzer failed: %s", e)
            check_cancellation()

        # 13. Custom Template Compliance & Drift (if custom profile)
        if profile_config.custom_rules.get("custom_template_id"):
            report("Evaluating custom template compliance & drift...", 86)
            try:
                all_findings.extend(self.custom_template_analyzer.analyze(doc, profile_config))
            except Exception as e:
                logger.error("CustomTemplateAnalyzer failed: %s", e)
            check_cancellation()

        # 14. Semantic Propositions & Logical Consistency
        report("Detecting semantic propositions & cross-document contradictions...", 88)
        try:
            all_findings.extend(self.semantic_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("SemanticAnalyzer failed: %s", e)

        try:
            all_findings.extend(self.logical_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("LogicalAnalyzer failed: %s", e)
        check_cancellation()

        # 14. Local Standards Knowledge Base Evaluation
        report("Comparing parameters against local engineering standards...", 93)
        try:
            all_findings.extend(self.standards_analyzer.analyze(doc, context))
        except Exception as e:
            logger.error("StandardsAnalyzer failed: %s", e)
        check_cancellation()

        # 15. Severity Prioritization & Ranking
        report("Computing severity scores and ranking critical issues...", 98)
        ranked_findings = self.severity_engine.rank_findings(all_findings)

        duration_ms = max(1, int((time.time() - start_time) * 1000))
        analysis_completed_at = datetime.now(timezone.utc).isoformat()

        # Archive immutable comparison into Repository
        try:
            cmp_record = self.repo_manager.archive_comparison(
                doc_model=doc,
                findings=ranked_findings,
                domain=profile_config.domain,
                standards=selected_standards or [],
                duration_ms=duration_ms,
                analysis_started_at=analysis_started_at,
                analysis_completed_at=analysis_completed_at
            )
            session_id = cmp_record.comparison_id
        except Exception as repo_err:
            logger.error("Failed archiving comparison into repository: %s", repo_err)

        # Save to SQLite database
        self.session_repo.save_session(
            session_id=session_id,
            doc_hash=doc.file_hash,
            domain=profile_config.domain,
            standards=selected_standards or [],
            findings=ranked_findings,
            duration_ms=duration_ms
        )

        # Record audit log
        self.audit.log(
            user_action="ANALYZE_DOCUMENT",
            document_hash=doc.file_hash,
            details=f"Session {session_id}, Profile: {profile_config.profile_id}, Findings: {len(ranked_findings)}, Duration: {duration_ms}ms"
        )

        # Force resource cleanup
        gc.collect()

        report("Analysis complete.", 100)
        return doc, ranked_findings, session_id

