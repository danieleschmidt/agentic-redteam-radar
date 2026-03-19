"""
Tests for probe definitions — verifies structure and coverage.
"""
import pytest
from redteam_radar.probes import (
    ALL_PROBES, CATEGORIES,
    PROMPT_INJECTION_PROBES, JAILBREAK_PROBES, DATA_EXFILTRATION_PROBES,
    ROLE_CONFUSION_PROBES, MULTI_TURN_PROBES, Probe,
)

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_CATEGORIES = set(CATEGORIES.keys())


def test_at_least_20_probes():
    """Must have at least 20 probes total across all categories."""
    assert len(ALL_PROBES) >= 20, f"Only {len(ALL_PROBES)} probes defined"


def test_five_categories():
    """Must have exactly 5 categories."""
    assert len(CATEGORIES) == 5


def test_each_category_has_probes():
    """Every category must have at least 3 probes."""
    for cat, probes in CATEGORIES.items():
        assert len(probes) >= 3, f"Category {cat!r} has only {len(probes)} probes"


def test_all_probes_have_unique_ids():
    """All probe IDs must be unique."""
    ids = [p.id for p in ALL_PROBES]
    assert len(ids) == len(set(ids)), "Duplicate probe IDs found"


def test_all_probes_have_valid_severity():
    for probe in ALL_PROBES:
        assert probe.severity in VALID_SEVERITIES, f"{probe.id}: invalid severity {probe.severity!r}"


def test_all_probes_have_valid_category():
    for probe in ALL_PROBES:
        assert probe.category in VALID_CATEGORIES, f"{probe.id}: invalid category {probe.category!r}"


def test_all_probes_have_payload():
    for probe in ALL_PROBES:
        assert probe.payload and len(probe.payload) > 10, f"{probe.id}: payload too short"


def test_all_probes_have_description():
    for probe in ALL_PROBES:
        assert probe.description and len(probe.description) > 10, f"{probe.id}: description too short"


def test_all_probes_have_detection_hints():
    for probe in ALL_PROBES:
        assert len(probe.detection_hints) >= 1, f"{probe.id}: no detection hints"


@pytest.mark.parametrize("probe", ALL_PROBES, ids=[p.id for p in ALL_PROBES])
def test_probe_is_dataclass(probe: Probe):
    assert isinstance(probe, Probe)
    assert probe.id
    assert probe.name
    assert probe.payload
    assert probe.severity in VALID_SEVERITIES
    assert probe.category in VALID_CATEGORIES


def test_categories_all_have_correct_category_field():
    """Probes inside a category bucket must have matching .category field."""
    for cat_name, probes in CATEGORIES.items():
        for probe in probes:
            assert probe.category == cat_name, (
                f"Probe {probe.id} in bucket {cat_name!r} has category={probe.category!r}"
            )


def test_prompt_injection_ids_start_with_pi():
    for p in PROMPT_INJECTION_PROBES:
        assert p.id.startswith("PI-"), f"Expected PI- prefix, got {p.id!r}"


def test_jailbreak_ids_start_with_jb():
    for p in JAILBREAK_PROBES:
        assert p.id.startswith("JB-"), f"Expected JB- prefix, got {p.id!r}"


def test_data_exfil_ids_start_with_de():
    for p in DATA_EXFILTRATION_PROBES:
        assert p.id.startswith("DE-"), f"Expected DE- prefix, got {p.id!r}"


def test_role_confusion_ids_start_with_rc():
    for p in ROLE_CONFUSION_PROBES:
        assert p.id.startswith("RC-"), f"Expected RC- prefix, got {p.id!r}"


def test_multi_turn_ids_start_with_mt():
    for p in MULTI_TURN_PROBES:
        assert p.id.startswith("MT-"), f"Expected MT- prefix, got {p.id!r}"
