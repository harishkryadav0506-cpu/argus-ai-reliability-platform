from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FaultType:
    LATENCY_SPIKE = "LATENCY_SPIKE"
    LLM_FAILURE = "LLM_FAILURE"
    RAG_DEGRADATION = "RAG_DEGRADATION"
    TOOL_FAILURE = "TOOL_FAILURE"
    COST_SPIKE = "COST_SPIKE"
    AGENT_LOOP = "AGENT_LOOP"

    ALL = [
        LATENCY_SPIKE,
        LLM_FAILURE,
        RAG_DEGRADATION,
        TOOL_FAILURE,
        COST_SPIKE,
        AGENT_LOOP,
    ]


class InjectFaultRequest(BaseModel):
    fault_type: str = Field(
        ...,
        description="Type of fault to inject: LATENCY_SPIKE, LLM_FAILURE, RAG_DEGRADATION, TOOL_FAILURE, COST_SPIKE, AGENT_LOOP",
    )
    severity: str = Field(default="high", description="Fault severity: low | medium | high | critical")
    duration_seconds: int = Field(default=60, ge=5, le=3600, description="Duration of fault in seconds")


class SimulationStatusResponse(BaseModel):
    mode: str = Field(..., description="Current mode: 'normal' or 'fault_active'")
    active_fault: Optional[str] = None
    severity: Optional[str] = None
    remaining_seconds: Optional[int] = None
    ticks_generated: int
    current_metrics: Dict[str, float]


class MetricPoint(BaseModel):
    timestamp: datetime
    metrics: Dict[str, float]


class MetricsResponse(BaseModel):
    current: Dict[str, float]
    history: List[MetricPoint]
    count: int
