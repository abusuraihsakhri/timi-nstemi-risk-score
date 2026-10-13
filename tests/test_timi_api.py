"""API contract and HMAC verification tests without network calls."""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from agents.api import TimiRequest, api_audit_logs, score_timi
from agents.base import AuditTrail

VALID = {
    "age": 65, "cad_risk_factors": 3, "known_cad": True,
    "aspirin_last_7_days": False, "anginal_events_24h": 2,
    "st_deviation": False, "elevated_biomarkers": True,
}


def test_api_returns_published_score():
    result = score_timi(TimiRequest(**VALID))
    assert result["score"] == 5
    assert result["event_rate_14d_pct"] == 26.2


def test_api_rejects_unknown_fields_and_unassessed_factors():
    with pytest.raises(ValidationError):
        TimiRequest(**{**VALID, "patient_name": "Example"})
    with pytest.raises(ValidationError):
        TimiRequest(age=65)
    with pytest.raises(ValidationError):
        TimiRequest(**{**VALID, "st_deviation": "maybe"})


def test_hmac_rejects_modified_entries():
    trail = AuditTrail(secret_key="test-secret")
    trail.log("unit-test", "tester", "TEST", {"case": "EXAMPLE-001"})
    assert trail.verify_integrity()
    snapshot = trail.get_trail()
    snapshot[0]["event_type"] = "CHANGED"
    assert trail.verify_integrity(), "The public snapshot must not modify internal state"
    trail.logs[0]["event_type"] = "CHANGED"
    assert not trail.verify_integrity()


def test_hmac_rejects_invalid_signature_and_missing_fields():
    trail = AuditTrail(secret_key="test-secret")
    trail.log("unit-test", "tester", "TEST", {"case": "EXAMPLE-001"})
    trail.logs[0]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()
    trail.logs[0].pop("payload_hash")
    assert not trail.verify_integrity()


def test_production_requires_real_audit_secret(monkeypatch):
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="AUDIT_SECRET_KEY"):
        AuditTrail()


def test_audit_log_endpoint_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AUDIT_LOG_READ_TOKEN", raising=False)
    with pytest.raises(HTTPException) as err:
        api_audit_logs()
    assert err.value.status_code == 404


def test_audit_log_endpoint_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_READ_TOKEN", "example-test-token")
    with pytest.raises(HTTPException) as err:
        api_audit_logs("Bearer wrong")
    assert err.value.status_code == 401
    assert api_audit_logs("Bearer example-test-token")["verified"]
