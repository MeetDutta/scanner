"""
Custom Template Management API for SpecGuard.
Provides isolated, 100% offline REST endpoints for template selection, listing,
retrieval, activation, and version rollback for document compliance analysis.
"""

from typing import Dict, Any, List, Optional
from dataclasses import asdict
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from specguard.templates.custom_manager import CustomTemplateManager

logger = logging.getLogger("SpecGuard.API.Templates")
router = APIRouter(prefix="/templates", tags=["templates"])

tmpl_mgr = CustomTemplateManager()


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


# ----------------------------------------------------
# Template Lifecycle Endpoints
# ----------------------------------------------------
@router.get("/custom")
def list_custom_templates(status: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Lists all user-defined custom templates available for document inspection."""
    templates = tmpl_mgr.list_templates(status=status)
    return [asdict(t) for t in templates]


@router.post("/custom")
def create_custom_template(req: CreateTemplateRequest) -> Dict[str, Any]:
    """Creates a new custom document compliance template."""
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
    """Retrieves custom template metadata and profile configuration."""
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
    """Permanently deletes a custom template."""
    deleted = tmpl_mgr.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
    return {"status": "success", "message": f"Template '{template_id}' deleted."}


@router.post("/custom/{template_id}/activate")
def activate_template(template_id: str) -> Dict[str, Any]:
    """Activates a template into the runtime ProfileRegistry for document inspection."""
    try:
        cfg = tmpl_mgr.activate_template(template_id)
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
