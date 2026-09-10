"""
ARGUS Recovery Schemas (Phase 7 - Sections 13, 15, 23)

Pydantic schemas for counterfactual recovery options, human approval requests, and execution responses.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    notes: Optional[str] = Field(default=None, description="Human operator approval notes")
    actor: Optional[str] = Field(default="user:operator", description="Operator identifier")


class StrategyOption(BaseModel):
    id: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    success_probability: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    reversibility: str
    rationale: str
    potential_impact: Optional[str] = None


class RecoveryOptionsResponse(BaseModel):
    incident_id: str
    failure_type: str
    approval_required: bool
    risk_score: float
    recommended_strategy: StrategyOption
    strategies: List[StrategyOption]


class ApprovalResponse(BaseModel):
    incident_id: str
    approval_status: str  # "approved" | "rejected" | "pending"
    execution_status: str  # "pending" | "executed" | "failed" | "blocked"
    message: str
    details: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
