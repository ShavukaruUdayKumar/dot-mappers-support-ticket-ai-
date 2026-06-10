"""API routes for the support ticket system."""
import logging
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    QueryRequest, QueryResponse, AnomalyReport,
    DatasetStats, DatasetSchema, ColumnSchema, HealthResponse, ErrorResponse
)
from app.services.query_service import query_service
from app.services.anomaly_service import anomaly_service
from app.data.loader import data_loader
from app.core.exceptions import QueryExecutionError, InvalidQueryIntentError, LLMError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns system health status and basic statistics"
)
async def health_check():
    """Check system health and data loading status."""
    try:
        settings = get_settings()
        is_loaded = data_loader.is_loaded()
        total_tickets = len(data_loader.get_data()) if is_loaded else 0
        
        return HealthResponse(
            status="healthy" if is_loaded else "unhealthy",
            version=settings.app_version,
            data_loaded=is_loaded,
            total_tickets=total_tickets,
            llm_service=settings.groq_model,
            uptime_seconds=0.0  # Could track actual uptime if needed
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Natural language query endpoint",
    description="Execute natural language questions against the ticket dataset"
)
async def execute_query(request: QueryRequest):
    """
    Execute a natural language query.
    
    Examples:
    - "How many critical tickets are open?"
    - "Which agent resolved the most tickets?"
    - "What is the average rating for Technical tickets?"
    """
    try:
        logger.info(f"Received query: {request.question}")
        response = query_service.execute_query(request.question)
        return response
        
    except InvalidQueryIntentError as e:
        logger.warning(f"Invalid query intent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not understand the question: {str(e)}"
        )
    except QueryExecutionError as e:
        logger.error(f"Query execution error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )
    except LLMError as e:
        logger.error(f"LLM error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/anomalies",
    response_model=AnomalyReport,
    summary="Detect anomalies in ticket data",
    description="Run hybrid anomaly detection (rule-based + statistical) and return all findings"
)
async def detect_anomalies():
    """
    Detect anomalies in the ticket dataset.
    
    Detection methods:
    - Rule-based: Stale critical/high priority tickets
    - Statistical: Resolution time outliers (Z-score)
    - Statistical: Response time outliers (Z-score)
    - Aggregate: Low-rated agents
    """
    try:
        logger.info("Running anomaly detection")
        report = anomaly_service.detect_all_anomalies()
        return report
        
    except Exception as e:
        logger.error(f"Anomaly detection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=DatasetStats,
    summary="Dataset statistics",
    description="Get comprehensive statistics about the ticket dataset"
)
async def get_stats():
    """Get detailed statistics about the dataset."""
    try:
        df = data_loader.get_data()
        
        # Calculate statistics
        resolved = df[df['status'] == 'Resolved']
        
        stats = DatasetStats(
            total_tickets=len(df),
            open_tickets=len(df[df['status'] == 'Open']),
            resolved_tickets=len(resolved),
            escalated_tickets=len(df[df['status'] == 'Escalated']),
            avg_resolution_time_hrs=resolved['resolution_time_hrs'].mean() if len(resolved) > 0 else None,
            avg_response_time_hrs=df['response_time_hrs'].mean(),
            avg_customer_rating=df['customer_rating'].mean() if df['customer_rating'].notna().any() else None,
            tickets_by_category=df['category'].value_counts().to_dict(),
            tickets_by_priority=df['priority'].value_counts().to_dict(),
            tickets_by_status=df['status'].value_counts().to_dict(),
            top_agents_by_resolution=resolved.groupby('agent_id').size().sort_values(ascending=False).head(5).reset_index(name='resolved_count').to_dict(orient='records')
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Stats calculation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate statistics: {str(e)}"
        )


@router.get(
    "/schema",
    response_model=DatasetSchema,
    summary="Dataset schema information",
    description="Get schema information about the ticket dataset (useful for debugging)"
)
async def get_schema():
    """Get schema information about the dataset."""
    try:
        df = data_loader.get_data()
        
        columns = []
        for col in df.columns:
            columns.append(ColumnSchema(
                name=col,
                dtype=str(df[col].dtype),
                nullable=df[col].isna().any(),
                unique_values_sample=df[col].dropna().unique()[:5].tolist()
            ))
        
        return DatasetSchema(
            total_rows=len(df),
            total_columns=len(df.columns),
            columns=columns
        )
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schema: {str(e)}"
        )
