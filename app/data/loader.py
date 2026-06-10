"""Data loading and validation."""
import pandas as pd
import logging
from pathlib import Path
from typing import Optional

from app.core.exceptions import DataLoadError

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading and caching of ticket data."""
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self._loaded = False
    
    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        Load ticket data from CSV with validation.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Loaded and validated DataFrame
            
        Raises:
            DataLoadError: If loading or validation fails
        """
        try:
            logger.info(f"Loading data from {file_path}")
            
            # Check file exists
            if not Path(file_path).exists():
                raise DataLoadError(f"File not found: {file_path}")
            
            # Load CSV
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_columns = [
                'ticket_id', 'created_at', 'category', 'priority', 
                'status', 'response_time_hrs', 'resolution_time_hrs',
                'agent_id', 'customer_rating', 'issue_summary'
            ]
            
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise DataLoadError(f"Missing required columns: {missing_columns}")
            
            # Convert datetime
            df['created_at'] = pd.to_datetime(df['created_at'])
            
            # Validate data types
            if not pd.api.types.is_numeric_dtype(df['response_time_hrs']):
                df['response_time_hrs'] = pd.to_numeric(df['response_time_hrs'], errors='coerce')
            
            if not pd.api.types.is_numeric_dtype(df['resolution_time_hrs']):
                df['resolution_time_hrs'] = pd.to_numeric(df['resolution_time_hrs'], errors='coerce')
            
            if not pd.api.types.is_numeric_dtype(df['customer_rating']):
                df['customer_rating'] = pd.to_numeric(df['customer_rating'], errors='coerce')
            
            # Store
            self.df = df
            self._loaded = True
            
            logger.info(f"Successfully loaded {len(df)} tickets")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            raise DataLoadError(f"Data loading failed: {str(e)}")
    
    def get_data(self) -> pd.DataFrame:
        """Get loaded data."""
        if not self._loaded or self.df is None:
            raise DataLoadError("Data not loaded. Call load_data() first.")
        return self.df
    
    def is_loaded(self) -> bool:
        """Check if data is loaded."""
        return self._loaded
    
    def get_schema_info(self) -> dict:
        """Get schema information for LLM prompts."""
        if not self._loaded:
            raise DataLoadError("Data not loaded")
        
        schema_info = {
            "columns": {},
            "sample_rows": 3,
            "total_rows": len(self.df)
        }
        
        for col in self.df.columns:
            schema_info["columns"][col] = {
                "dtype": str(self.df[col].dtype),
                "nullable": self.df[col].isna().any(),
                "unique_count": self.df[col].nunique(),
                "sample_values": self.df[col].dropna().unique()[:5].tolist()
            }
        
        return schema_info


# Global instance
data_loader = DataLoader()
