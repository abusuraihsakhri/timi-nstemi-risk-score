"""
FastAPI REST API Server for Timi Nstemi Risk Score.
"""
import os
import secrets
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field, ConfigDict, StrictBool
from .base import AuditLogger, PHIGuard
from timi_nstemi import calculate_metrics
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

_supervisor = None

def _get_supervisor():
    global _supervisor
    if _supervisor is None:
        provider = os.getenv("MODEL_PROVIDER", "mock")
        _supervisor = SystemSupervisor(model_provider=provider)
    return _supervisor

app = FastAPI(
    title="Timi Nstemi Risk Score API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str



class TimiRequest(BaseModel):
    """The seven required original TIMI UA/NSTEMI factors."""
    model_config = ConfigDict(extra="forbid")
    age: int = Field(ge=0, le=120)
    cad_risk_factors: int = Field(ge=0, le=5)
    known_cad: StrictBool
    aspirin_last_7_days: StrictBool
    anginal_events_24h: int = Field(ge=0, le=1000)
    st_deviation: StrictBool
    elevated_biomarkers: StrictBool


@app.post("/api/timi")
def score_timi(payload: TimiRequest):
    """Published integer score and historical 14-day composite event rate."""
    return calculate_metrics(**payload.model_dump())


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "timi-nstemi-risk-score", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    sup = _get_supervisor()
    return {
        "dossiers_processed_total": len(sup.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = _get_supervisor().process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = _get_supervisor().query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs(authorization: str | None = Header(default=None)):
    secret = os.getenv("AUDIT_LOG_READ_TOKEN")
    if not secret:
        raise HTTPException(status_code=404, detail="Audit log endpoint disabled")
    if not secrets.compare_digest(authorization or "", "Bearer " + secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
