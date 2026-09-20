"""
Profile Review, User Customization, and Approval Engine for SpecGuard.
Enforces explicit human approval, rule categorization (Learned vs Configured vs Uncertain),
tolerance configuration, and dynamic registration into the ProfileRegistry.
Strictly 100% offline.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from specguard.templates.custom_manager import CustomTemplateManager
from specguard.core.profiles import ProfileConfig, PROFILES

logger = logging.getLogger(__name__)


class ProfileApprover:
    """Handles review, property customization, and approval gating for custom templates."""

    def __init__(self, template_manager: Optional[CustomTemplateManager] = None):
        self.template_manager = template_manager or CustomTemplateManager()

    def get_review_summary(self, template_id: str) -> Dict[str, Any]:
        """Categorizes profile properties into Learned, User-Configured, and Uncertain."""
        profile = self.template_manager.get_profile(template_id)
        if not profile:
            raise FileNotFoundError(f"Template profile for '{template_id}' not found.")

        meta = self.template_manager.get_template(template_id)
        learned_props = profile.get("learned_properties", {})
        user_rules = profile.get("user_rules", {})
        tolerances = profile.get("tolerances", {
            "font_size_pt": 1.0,
            "margin_mm": 5.0,
            "column_width_mm": 10.0
        })

        categorized = {
            "template_id": template_id,
            "version": profile.get("version", "1.0.0"),
            "status": meta.status if meta else "DRAFT",
            "is_approved": profile.get("is_approved", False),
            "approved_by": profile.get("approved_by"),
            "approved_at": profile.get("approved_at"),
            "overall_confidence": profile.get("overall_confidence", 0.0),
            "learned_properties": [],
            "user_configured_rules": user_rules,
            "uncertain_properties": [],
            "tolerances": tolerances,
            "summary_rules": profile.get("summary_rules", {})
        }

        for prop_name, prop_data in learned_props.items():
            entry = {
                "property_name": prop_name,
                "learned_value": prop_data.get("learned_value"),
                "confidence": prop_data.get("confidence", 1.0),
                "is_locked": prop_data.get("is_locked", False),
                "rule_type": prop_data.get("rule_type", "mandatory"),  # mandatory, warning, optional, ignore
                "extraction_method": prop_data.get("extraction_method", ""),
                "distribution": prop_data.get("distribution", {})
            }
            if prop_data.get("is_uncertain") or prop_data.get("confidence", 1.0) < 0.7:
                categorized["uncertain_properties"].append(entry)
            else:
                categorized["learned_properties"].append(entry)

        return categorized

    def update_property(
        self,
        template_id: str,
        property_name: str,
        new_value: Any,
        rule_type: str = "mandatory",
        is_locked: bool = True
    ) -> Dict[str, Any]:
        """Edits or locks a specific property in the profile."""
        profile = self.template_manager.get_profile(template_id)
        if not profile:
            raise FileNotFoundError(f"Template profile for '{template_id}' not found.")

        learned_props = profile.setdefault("learned_properties", {})
        if property_name not in learned_props:
            learned_props[property_name] = {
                "property_name": property_name,
                "learned_value": new_value,
                "confidence": 1.0,
                "sample_count": 0,
                "distribution": {},
                "extraction_method": "user_configured"
            }

        learned_props[property_name]["learned_value"] = new_value
        learned_props[property_name]["rule_type"] = rule_type
        learned_props[property_name]["is_locked"] = is_locked
        learned_props[property_name]["is_uncertain"] = False

        # Also reflect in summary_rules if relevant
        summary_rules = profile.setdefault("summary_rules", {})
        if "." in property_name:
            category, key = property_name.split(".", 1)
            summary_rules.setdefault(category, {})[key] = new_value

        self.template_manager.save_profile(template_id, profile)
        logger.info("Updated property '%s' for template '%s'", property_name, template_id)
        return profile

    def update_tolerances(self, template_id: str, tolerances: Dict[str, float]) -> Dict[str, Any]:
        """Configures allowable margins and font variances."""
        profile = self.template_manager.get_profile(template_id)
        if not profile:
            raise FileNotFoundError(f"Template profile for '{template_id}' not found.")
        profile["tolerances"] = tolerances
        self.template_manager.save_profile(template_id, profile)
        return profile

    def approve_profile(self, template_id: str, approver_name: str = "Administrator") -> Dict[str, Any]:
        """Explicitly approves the template profile."""
        profile = self.template_manager.get_profile(template_id)
        if not profile:
            raise FileNotFoundError(f"Template profile for '{template_id}' not found.")

        profile["is_approved"] = True
        profile["approved_by"] = approver_name
        profile["approved_at"] = datetime.now().isoformat()
        profile["status"] = "APPROVED"

        self.template_manager.save_profile(template_id, profile)
        self.template_manager.update_status(template_id, "APPROVED")
        self.template_manager.create_version_snapshot(
            template_id, note=f"Profile approved by {approver_name}"
        )
        logger.info("Template '%s' approved by %s", template_id, approver_name)
        return profile

    def activate_template(self, template_id: str) -> ProfileConfig:
        """
        Activates an approved template and dynamically registers it into the global ProfileRegistry
        so that it is immediately selectable in New Analysis.
        """
        profile = self.template_manager.get_profile(template_id)
        if not profile:
            raise FileNotFoundError(f"Template profile for '{template_id}' not found.")

        if not profile.get("is_approved", False):
            raise ValueError(
                f"Cannot activate template '{template_id}'. Profile has not been approved. "
                f"Review and approve the profile first."
            )

        meta = self.template_manager.get_template(template_id)
        name = meta.name if meta else template_id
        summary_rules = profile.get("summary_rules", {})
        layout = summary_rules.get("layout", {})
        structure = summary_rules.get("structure", {})
        objects = summary_rules.get("objects", {})

        # Create ProfileConfig
        dyn_config = ProfileConfig(
            profile_id=template_id,
            display_name=name,
            domain=meta.category if meta else "Custom",
            description=meta.description if meta else f"Custom template {template_id}",
            requires_toc=structure.get("requires_toc", False),
            toc_min_pages=5,
            required_sections=structure.get("required_sections", []),
            optional_sections=structure.get("optional_sections", []),
            section_numbering_style=structure.get("numbering_style", "any"),
            expected_layout=layout.get("expected_layout", "any"),
            table_caption_position=objects.get("table_caption_position", "above"),
            figure_caption_position=objects.get("figure_caption_position", "below"),
            validate_equations=objects.get("has_equations", False),
            validate_cross_references=True,
            custom_rules={
                "custom_template_id": template_id,
                "tolerances": profile.get("tolerances", {}),
                "summary_rules": summary_rules
            }
        )

        # Register in PROFILES
        PROFILES[template_id] = dyn_config

        self.template_manager.update_status(template_id, "ACTIVE")
        logger.info("Activated custom template '%s' in ProfileRegistry", template_id)
        return dyn_config
