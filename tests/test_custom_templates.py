"""
Unit and Integration Tests for SpecGuard Custom Template Engine,
Profile Storage, Dynamic Activation, and Version Rollback.
Strictly 100% offline.
"""

import pytest
from pathlib import Path

from specguard.templates.custom_manager import CustomTemplateManager, CustomTemplateMetadata
from specguard.core.profiles import ProfileRegistry, PROFILES


@pytest.fixture
def temp_custom_dir(tmp_path):
    custom_dir = tmp_path / "templates" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    return custom_dir


@pytest.fixture
def custom_mgr(temp_custom_dir):
    return CustomTemplateManager(base_dir=temp_custom_dir)


def test_custom_template_lifecycle(custom_mgr):
    """Verifies template creation, path traversal protection, and uniqueness."""
    # 1. Successful creation
    meta = custom_mgr.create_template(
        template_id="actuator_spec",
        name="Hydraulic Actuator Specification",
        description="Standard rules for hydraulic actuator validation.",
        category="Mechanical"
    )
    assert meta.template_id == "actuator_spec"
    assert meta.status == "DRAFT"

    # 2. Duplicate prevention
    with pytest.raises(FileExistsError):
        custom_mgr.create_template(
            template_id="actuator_spec",
            name="Duplicate Spec",
            description="Duplicate"
        )

    # 3. Path traversal attack protection
    with pytest.raises(ValueError):
        custom_mgr.create_template(
            template_id="../../etc/passwd",
            name="Malicious Template",
            description="Exploit attempt"
        )

    # 4. Reserved name protection
    with pytest.raises(ValueError):
        custom_mgr.create_template(
            template_id="mechanical",
            name="Override Built-in",
            description="Should fail"
        )


def test_dynamic_activation_into_profile_registry(custom_mgr):
    """Verifies that custom templates activate dynamically into ProfileRegistry."""
    custom_mgr.create_template(
        template_id="pump_spec",
        name="Pump Spec",
        description="Pump Inspection Standard"
    )

    prof = custom_mgr.get_profile("pump_spec")
    prof["summary_rules"] = {
        "structure": {"required_sections": ["Scope", "Specifications"]},
        "layout": {"expected_layout": "single_column"}
    }
    custom_mgr.save_profile("pump_spec", prof)

    # Activate
    cfg = custom_mgr.activate_template("pump_spec")
    assert cfg.profile_id == "pump_spec"
    assert "pump_spec" in PROFILES

    retrieved = ProfileRegistry.get_profile("pump_spec")
    assert retrieved is not None
    assert retrieved.display_name == "Pump Spec"


def test_version_snapshot_and_rollback(custom_mgr):
    """Verifies that custom template profiles can be snapshotted and rolled back."""
    custom_mgr.create_template(template_id="heat_exchanger", name="HX Spec", description="Test")

    # Modify profile
    prof = custom_mgr.get_profile("heat_exchanger")
    prof["tolerances"]["font_size_pt"] = 0.5
    custom_mgr.save_profile("heat_exchanger", prof)
    tag1 = custom_mgr.create_version_snapshot("heat_exchanger", note="Tighter font tolerance")

    # Change again
    prof["tolerances"]["font_size_pt"] = 2.5
    custom_mgr.save_profile("heat_exchanger", prof)
    assert custom_mgr.get_profile("heat_exchanger")["tolerances"]["font_size_pt"] == 2.5

    # Rollback to tag1
    custom_mgr.rollback_version("heat_exchanger", tag1)
    restored_prof = custom_mgr.get_profile("heat_exchanger")
    assert restored_prof["tolerances"]["font_size_pt"] == 0.5
