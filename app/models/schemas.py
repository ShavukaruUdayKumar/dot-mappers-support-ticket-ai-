"""Pydantic models for request/response validation."""
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== Query Models ====================

class QueryRequest(BaseModel):
    """Natural language query request."""
    question: str = Field(..., min_length=3, description="Natural language question")


class QueryIntent(BaseModel):
    """Structured query intent extracted from natural language."""
    intent: Literal["count", "filter", "aggregate", "top_n", "average", "sum", "group"] = Field(
        ..., description="Type of query operation"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filter conditions"
    )
    aggregations: List[str] = Field(
        default_factory=list, description="Aggregation operations"
    )
    group_by: Optional[str] = Field(None, description="Column to group by")
    sort_by: Optional[str] = Field(None, description="Column to sort by")
    order: Literal["asc", "desc"] = Field("desc", description="Sort order")
    limit: Optional[int] = Field(None, description="Number of results to return")


class QueryMetadata(BaseModel):
    """Metadata about query execution."""
    execution_time_ms: float
    rows_returned: int
    query_intent: Optional[QueryIntent] = None
    llm_calls: int = 0


class QueryResponse(BaseModel):
    """Response to a natural language query."""
    question: str
    natural_answer: str
    data: Any
    metadata: QueryMetadata


# ==================== Anomaly Models ====================

class AnomalyItem(BaseModel):
    """Individual anomaly detection result."""
    ticket_id: str
    anomaly_type: str
    severity: Literal["low", "medium", "high", "critical"]
    reason: str
    metadata: Dict[str, Any]
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class AnomalyReport(BaseModel):
    """Complete anomaly detection report."""
    total_anomalies: int
    anomalies_by_type: Dict[str, int]
    critical_anomalies: List[AnomalyItem]
    high_anomalies: List[AnomalyItem]
    medium_anomalies: List[AnomalyItem]
    low_anomalies: List[AnomalyItem]
    detection_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== Stats Models ====================

class DatasetStats(BaseModel):
    """Statistics about the dataset."""
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_tickets: int
    avg_resolution_time_hrs: Optional[float]
    avg_response_time_hrs: float
    avg_customer_rating: Optional[float]
    tickets_by_category: Dict[str, int]
    tickets_by_priority: Dict[str, int]
    tickets_by_status: Dict[str, int]
    top_agents_by_resolution: List[Dict[str, Any]]


# ==================== Schema Models ====================

class ColumnSchema(BaseModel):
    """Schema information for a single column."""
    name: str
    dtype: str
    nullable: bool
    unique_values_sample: List[Any]


class DatasetSchema(BaseModel):
    """Complete dataset schema information."""
    total_rows: int
    total_columns: int
    columns: List[ColumnSchema]


# ==================== Health Models ====================

class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    data_loaded: bool
    total_tickets: int
    llm_service: str
    uptime_seconds: float


# ==================== Error Models ====================

class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
