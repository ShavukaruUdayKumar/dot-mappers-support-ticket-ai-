"""Natural language query service."""
import logging
import time
import pandas as pd
from typing import Any, Dict

from app.services.llm_service import llm_service
from app.data.loader import data_loader
from app.models.schemas import QueryIntent, QueryResponse, QueryMetadata
from app.core.exceptions import QueryExecutionError, InvalidQueryIntentError

logger = logging.getLogger(__name__)


class QueryService:
    """Service for executing natural language queries."""
    
    def __init__(self):
        self.llm = llm_service
        self.data = data_loader
    
    def _build_intent_prompt(self, question: str) -> tuple[str, str]:
        """Build system and user prompts for intent extraction."""
        
        schema_info = self.data.get_schema_info()
        
        system_prompt = f"""You are a data analyst converting natural language questions into structured query intents for a support ticket dataset.

Dataset Schema:
- ticket_id (string): Unique ticket identifier
- created_at (datetime): Ticket creation timestamp
- category (string): Billing, Technical, or General
- priority (string): Low, Medium, High, or Critical
- status (string): Open, Resolved, or Escalated
- response_time_hrs (float): Hours to first response
- resolution_time_hrs (float): Hours to resolution (null if unresolved)
- agent_id (string): Assigned agent (AGT-01 to AGT-12)
- customer_rating (integer): 1-5 rating (null if unresolved)
- issue_summary (string): Brief description

Total rows: {schema_info['total_rows']}

Return ONLY a JSON object with this structure:
{{
  "intent": "count|filter|aggregate|top_n|average|sum|group",
  "filters": {{"column": "value"}},
  "aggregations": ["count", "avg", "sum", "max", "min"],
  "group_by": "column_name or null",
  "sort_by": "column_name or null",
  "order": "asc or desc",
  "limit": number or null
}}

Examples:
Q: "How many critical tickets are open?"
A: {{"intent": "count", "filters": {{"priority": "Critical", "status": "Open"}}, "aggregations": ["count"], "group_by": null, "sort_by": null, "order": "desc", "limit": null}}

Q: "Which agent resolved the most tickets?"
A: {{"intent": "top_n", "filters": {{"status": "Resolved"}}, "aggregations": ["count"], "group_by": "agent_id", "sort_by": "count", "order": "desc", "limit": 1}}

Q: "What is the average rating for Technical tickets?"
A: {{"intent": "average", "filters": {{"category": "Technical"}}, "aggregations": ["avg"], "group_by": null, "sort_by": null, "order": "desc", "limit": null}}

Return ONLY the JSON object, no explanations."""

        user_prompt = f"Question: {question}\n\nJSON:"
        
        return system_prompt, user_prompt
    
    def _parse_intent(self, question: str) -> QueryIntent:
        """Extract structured intent from natural language question."""
        try:
            system_prompt, user_prompt = self._build_intent_prompt(question)
            response = self.llm.chat(system_prompt, user_prompt)
            
            # Extract JSON
            intent_data = self.llm.extract_json(response)
            
            # Validate with Pydantic
            intent = QueryIntent(**intent_data)
            logger.info(f"Extracted intent: {intent.intent}")
            
            return intent
            
        except Exception as e:
            logger.error(f"Intent parsing failed: {str(e)}")
            raise InvalidQueryIntentError(f"Failed to parse query intent: {str(e)}")
    
    def _execute_intent(self, intent: QueryIntent) -> Any:
        """Execute query intent on DataFrame."""
        try:
            df = self.data.get_data().copy()
            
            # Apply filters
            for column, value in intent.filters.items():
                if column not in df.columns:
                    raise QueryExecutionError(f"Unknown column: {column}")
                df = df[df[column] == value]
            
            # Handle different intents
            if intent.intent == "count":
                result = len(df)
                
            elif intent.intent == "filter":
                if intent.sort_by:
                    df = df.sort_values(intent.sort_by, ascending=(intent.order == "asc"))
                if intent.limit:
                    df = df.head(intent.limit)
                result = df.to_dict(orient='records')
                
            elif intent.intent == "average":
                if "avg" in intent.aggregations and intent.aggregations:
                    # Find numeric columns in filters or use customer_rating
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if 'customer_rating' in numeric_cols:
                        result = df['customer_rating'].mean()
                    elif 'resolution_time_hrs' in numeric_cols:
                        result = df['resolution_time_hrs'].mean()
                    else:
                        result = df[numeric_cols[0]].mean() if len(numeric_cols) > 0 else 0
                else:
                    result = 0
                    
            elif intent.intent == "sum":
                numeric_cols = df.select_dtypes(include=['number']).columns
                result = df[numeric_cols[0]].sum() if len(numeric_cols) > 0 else 0
                
            elif intent.intent == "group":
                if intent.group_by and intent.group_by in df.columns:
                    grouped = df.groupby(intent.group_by).size().reset_index(name='count')
                    if intent.sort_by:
                        grouped = grouped.sort_values('count', ascending=(intent.order == "asc"))
                    result = grouped.to_dict(orient='records')
                else:
                    result = []
                    
            elif intent.intent == "top_n":
                if intent.group_by and intent.group_by in df.columns:
                    grouped = df.groupby(intent.group_by).size().reset_index(name='count')
                    grouped = grouped.sort_values('count', ascending=(intent.order == "asc"))
                    if intent.limit:
                        grouped = grouped.head(intent.limit)
                    result = grouped.to_dict(orient='records')
                else:
                    result = []
                    
            elif intent.intent == "aggregate":
                agg_results = {}
                for agg in intent.aggregations:
                    if agg == "count":
                        agg_results["count"] = len(df)
                    elif agg == "avg":
                        agg_results["avg_rating"] = df['customer_rating'].mean()
                    elif agg == "sum":
                        agg_results["sum"] = df['response_time_hrs'].sum()
                result = agg_results
            else:
                result = len(df)
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise QueryExecutionError(f"Failed to execute query: {str(e)}")
    
    def _generate_natural_answer(self, question: str, data: Any, intent: QueryIntent) -> str:
        """Generate natural language answer from query results."""
        try:
            system_prompt = """You are a data analyst. Convert query results into a clear, concise natural language answer.
Be specific with numbers. Keep it under 2 sentences."""
            
            user_prompt = f"""Question: {question}
Query Result: {data}
Intent: {intent.intent}

Natural Answer:"""
            
            answer = self.llm.chat(system_prompt, user_prompt)
            return answer.strip()
            
        except Exception as e:
            logger.warning(f"Natural answer generation failed: {str(e)}")
            return f"Result: {data}"
    
    def execute_query(self, question: str) -> QueryResponse:
        """
        Execute natural language query end-to-end.
        
        Args:
            question: Natural language question
            
        Returns:
            QueryResponse with answer and metadata
        """
        start_time = time.time()
        llm_calls_before = self.llm.get_call_count()
        
        try:
            # Parse intent
            intent = self._parse_intent(question)
            
            # Execute query
            data = self._execute_intent(intent)
            
            # Generate natural answer
            natural_answer = self._generate_natural_answer(question, data, intent)
            
            # Calculate metadata
            execution_time_ms = (time.time() - start_time) * 1000
            llm_calls = self.llm.get_call_count() - llm_calls_before
            
            rows_returned = len(data) if isinstance(data, (list, pd.DataFrame)) else 1
            
            metadata = QueryMetadata(
                execution_time_ms=execution_time_ms,
                rows_returned=rows_returned,
                query_intent=intent,
                llm_calls=llm_calls
            )
            
            return QueryResponse(
                question=question,
                natural_answer=natural_answer,
                data=data,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise


# Global instance
query_service = QueryService()
