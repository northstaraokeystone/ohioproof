"""
Tests for Charter domain module.
"""

import pytest

from src.domains.charter import (
    verify_enrollment,
    detect_attendance_anomaly,
    compute_per_pupil_risk,
    flag_related_party,
    get_ecot_case_data
)


class TestCharterDomain:
    """Tests for charter school ECOT-pattern detection."""

    def test_verify_enrollment_accurate(self):
        """Test enrollment verification with accurate data."""
        school = {
            "name": "Good School",
            "claimed_enrollment": 100,
            "verified_enrollment": 100
        }
        ratio = verify_enrollment(school)
        assert ratio == 1.0

    def test_verify_enrollment_inflated(self, sample_school):
        """Test enrollment verification with inflation."""
        ratio = verify_enrollment(sample_school)
        assert ratio == 0.8  # 800/1000

    def test_detect_attendance_anomaly(self, sample_school):
        """Test attendance anomaly detection."""
        result = detect_attendance_anomaly(sample_school)
        assert result["anomaly_detected"] is True
        assert result["ecot_pattern_match"] is True  # ratio < 0.5

    def test_compute_per_pupil_risk(self, sample_school):
        """Test per-pupil risk computation."""
        risk = compute_per_pupil_risk(sample_school)
        # 200 inflated students * $7000 per pupil
        assert risk == 1400000

    def test_flag_related_party_founder_overlap(self):
        """Test related party detection with founder overlap."""
        vendor = {
            "name": "Vendor Corp",
            "owners": ["John Smith"]
        }
        school = {
            "name": "School",
            "founders": ["John Smith"]
        }
        assert flag_related_party(vendor, school) is True

    def test_flag_related_party_no_overlap(self):
        """Test related party detection with no overlap."""
        vendor = {
            "name": "Vendor Corp",
            "owners": ["Jane Doe"]
        }
        school = {
            "name": "School",
            "founders": ["John Smith"]
        }
        assert flag_related_party(vendor, school) is False

    def test_get_ecot_data(self):
        """Test ECOT case data retrieval."""
        data = get_ecot_case_data()
        assert data["finding_for_recovery"] == 117000000
        assert data["years_operating"] == 18
