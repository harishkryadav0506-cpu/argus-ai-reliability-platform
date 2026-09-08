from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(default="")
    severity: str = Field(default="medium")
    failure_type: str = Field(default="UNKNOWN")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metrics: Optional[Dict[str, float]] = None


class MetricSnapshotResponse(BaseModel):
    id: str
    incident_id: str
    metric_name: str
    value: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    failure_type: str
    confidence: float
    created_at: datetime
    resolved_at: Optional[datetime] = None
    metrics: List[MetricSnapshotResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
