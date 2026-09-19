"""
Custom Template & Profile Learning Management API for SpecGuard.
Provides isolated, 100% offline REST endpoints for template creation, sample ingestion,
statistical profile learning, human review/approval, region annotations, local ML training,
and version rollback.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel

from specguard.templates.custom_manager import CustomTemplateManager, CustomTemplateMetadata
from specguard.templates.sample_manager import SampleManager
from specguard.templates.profile_learner import ProfileLearner
from specguard.templates.profile_approver import ProfileApprover
from specguard.templates.region_annotator import RegionAnnotator
from specguard.templates.layout_trainer import LayoutTrainer
from specguard.core.runtime_paths import get_uploads_dir

logger = logging.getLogger("DocReady.API.Templates")
router = APIRouter(prefix="/templates", tags=["templates"])

tmpl_mgr = CustomTemplateManager()
sample_mgr = SampleManager(tmpl_mgr)
learner = ProfileLearner(tmpl_mgr, sample_mgr)
approver = ProfileApprover(tmpl_mgr)
annotator = RegionAnnotator(tmpl_mgr)
trainer = LayoutTrainer(tmpl_mgr, annotator)


# ----------------------------------------------------
# Request Models
# ----------------------------------------------------
class CreateTemplateRequest(BaseModel):
    template_id: str
    name: str
    description: str
    category: str = "Engineering Specification"
    supported_file_types: List[str] = ["pdf", "docx"]
    organization: Optional[str] = None
    version: str = "1.0.0"


class UpdatePropertyRequest(BaseModel):
    property_name: str
    new_value: Any
    rule_type: str = "mandatory"
    is_locked: bool = True


class UpdateTolerancesRequest(BaseModel):
    tolerances: Dict[str, float]


class ApproveProfileRequest(BaseModel):
    approver_name: str = "Quality Engineer"


class AddAnnotationRequest(BaseModel):
    sample_id: str
    page_number: int
    label: str
    bbox: Dict[str, float]
    text_content: Optional[str] = None
    annotator: str = "engineer"


class TrainMLRequest(BaseModel):
    epochs: int = 15
    learning_rate: float = 0.01
    user_name: str = "engineer"


# ----------------------------------------------------
# Template Lifecycle Endpoints
# ----------------------------------------------------
@router.get("/custom")
def list_custom_templates(status: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Lists all user-defined custom templates."""
    templates = tmpl_mgr.list_templates(status=status)
    return [asdict(t) for t in templates]


@router.post("/custom")
def create_custom_template(req: CreateTemplateRequest) -> Dict[str, Any]:
    """Creates a new custom document compliance template in an isolated directory."""
    try:
        meta = tmpl_mgr.create_template(
            template_id=req.template_id,
            name=req.name,
            description=req.description,
            category=req.category,
            supported_file_types=req.supported_file_types,
            organization=req.organization,
            version=req.version
        )
        return {"status": "success", "template": asdict(meta)}
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/custom/{template_id}")
def get_custom_template(template_id: str) -> Dict[str, Any]:
    """Retrieves custom template metadata and profile status."""
    meta = tmpl_mgr.get_template(template_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
    profile = tmpl_mgr.get_profile(template_id)
    return {
        "metadata": asdict(meta),
        "profile": profile
    }


@router.delete("/custom/{template_id}")
def delete_custom_template(template_id: str) -> Dict[str, Any]:
    """Permanently deletes a custom template and its samples/models."""
    deleted = tmpl_mgr.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
    return {"status": "success", "message": f"Template '{template_id}' deleted."}


# ----------------------------------------------------
# Sample Document Management
# ----------------------------------------------------
@router.get("/custom/{template_id}/samples")
def list_samples(template_id: str) -> List[Dict[str, Any]]:
    """Lists all sample documents ingested for this template."""
    samples = sample_mgr.list_samples(template_id)
    return [asdict(s) for s in samples]


@router.post("/custom/{template_id}/samples")
async def upload_sample(
    template_id: str,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """Uploads and ingests a sample document with SHA-256 deduplication and parsing."""
    temp_dir = get_uploads_dir() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / (file.filename or "upload.pdf")

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        info = sample_mgr.ingest_sample(
            template_id=template_id,
            source_file_path=temp_path,
            original_filename=file.filename
        )
        return {"status": "success", "sample": asdict(info)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Sample upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to process sample: {str(e)}")
    finally:
        temp_path.unlink(missing_ok=True)


@router.delete("/custom/{template_id}/samples/{sample_id}")
def delete_sample(template_id: str, sample_id: str) -> Dict[str, Any]:
    """Removes a sample document."""
    removed = sample_mgr.remove_sample(template_id, sample_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found.")
    return {"status": "success", "message": f"Sample '{sample_id}' removed."}


@router.get("/custom/{template_id}/sample-variations")
def check_sample_variations(template_id: str) -> Dict[str, Any]:
    """Detects structural variance across uploaded samples."""
    warnings = sample_mgr.check_sample_variations(template_id)
    return {"warnings": warnings, "has_conflicts": len(warnings) > 0}


# ----------------------------------------------------
# Profile Learning & Review
# ----------------------------------------------------
@router.post("/custom/{template_id}/learn")
def learn_profile(template_id: str) -> Dict[str, Any]:
    """Runs local statistical profile learning across all processed samples."""
    try:
        learned = learner.learn_profile(template_id)
        return {
            "status": "success",
            "overall_confidence": learned.overall_confidence,
            "sample_count": learned.sample_count,
            "warnings": learned.warnings,
            "summary_rules": learned.summary_rules
        }
    except Exception as e:
        logger.error("Profile learning failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/custom/{template_id}/review")
def get_profile_review(template_id: str) -> Dict[str, Any]:
    """Returns categorized profile review (Learned, User-Configured, Uncertain, Tolerances)."""
    try:
        return approver.get_review_summary(template_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/custom/{template_id}/property")
def update_profile_property(template_id: str, req: UpdatePropertyRequest) -> Dict[str, Any]:
    """Customizes or locks a specific rule in the template profile."""
    try:
        updated = approver.update_property(
            template_id=template_id,
            property_name=req.property_name,
            new_value=req.new_value,
            rule_type=req.rule_type,
            is_locked=req.is_locked
        )
        return {"status": "success", "profile": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/custom/{template_id}/tolerances")
def update_profile_tolerances(template_id: str, req: UpdateTolerancesRequest) -> Dict[str, Any]:
    """Updates tolerance margins and font variations."""
    try:
        updated = approver.update_tolerances(template_id, req.tolerances)
        return {"status": "success", "tolerances": updated.get("tolerances", {})}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/custom/{template_id}/approve")
def approve_profile(template_id: str, req: ApproveProfileRequest) -> Dict[str, Any]:
    """Explicitly approves the template profile."""
    try:
        updated = approver.approve_profile(template_id, approver_name=req.approver_name)
        return {"status": "success", "message": f"Profile approved by {req.approver_name}."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/custom/{template_id}/activate")
def activate_template(template_id: str) -> Dict[str, Any]:
    """Activates an approved template into the runtime ProfileRegistry."""
    try:
        cfg = approver.activate_template(template_id)
        return {
            "status": "success",
            "message": f"Template '{template_id}' activated in ProfileRegistry.",
            "profile_id": cfg.profile_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------
# Versioning & Rollback
# ----------------------------------------------------
@router.get("/custom/{template_id}/versions")
def list_versions(template_id: str) -> List[Dict[str, Any]]:
    """Lists immutable historical version snapshots."""
    return tmpl_mgr.list_versions(template_id)


@router.post("/custom/{template_id}/rollback/{version_tag}")
def rollback_version(template_id: str, version_tag: str) -> Dict[str, Any]:
    """Restores an earlier version snapshot."""
    try:
        meta = tmpl_mgr.rollback_version(template_id, version_tag)
        return {"status": "success", "message": f"Restored version {version_tag}.", "metadata": asdict(meta)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------
# Region Annotations
# ----------------------------------------------------
@router.get("/custom/{template_id}/annotations")
def list_annotations(
    template_id: str,
    sample_id: Optional[str] = Query(None),
    page_number: Optional[int] = Query(None)
) -> List[Dict[str, Any]]:
    """Lists bounding-box region annotations."""
    annots = annotator.list_annotations(template_id, sample_id=sample_id, page_number=page_number)
    return [asdict(a) for a in annots]


@router.post("/custom/{template_id}/annotations")
def add_annotation(template_id: str, req: AddAnnotationRequest) -> Dict[str, Any]:
    """Adds a bounding-box region annotation for supervised learning."""
    try:
        annot = annotator.add_annotation(
            template_id=template_id,
            sample_id=req.sample_id,
            page_number=req.page_number,
            label=req.label,
            bbox=req.bbox,
            text_content=req.text_content,
            annotator=req.annotator
        )
        return {"status": "success", "annotation": asdict(annot)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/custom/{template_id}/annotations/{annotation_id}")
def delete_annotation(template_id: str, annotation_id: str) -> Dict[str, Any]:
    """Deletes an annotation."""
    deleted = annotator.delete_annotation(template_id, annotation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return {"status": "success", "message": f"Annotation {annotation_id} deleted."}


@router.get("/custom/{template_id}/dataset-summary")
def get_dataset_summary(template_id: str) -> Dict[str, Any]:
    """Evaluates annotated dataset health, class balance, and ML training readiness."""
    return annotator.get_dataset_summary(template_id)


# ----------------------------------------------------
# Optional Local Supervised Machine Learning
# ----------------------------------------------------
@router.post("/custom/{template_id}/train-ml")
def train_layout_model(template_id: str, req: TrainMLRequest) -> Dict[str, Any]:
    """Trains a local layout region classification model using document-level splitting."""
    try:
        report = trainer.train_model(
            template_id=template_id,
            epochs=req.epochs,
            learning_rate=req.learning_rate,
            user_name=req.user_name
        )
        return {"status": "success", "report": report}
    except Exception as e:
        logger.error("ML training failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
