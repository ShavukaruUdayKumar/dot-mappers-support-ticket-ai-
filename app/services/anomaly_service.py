"""Anomaly detection service with hybrid approach."""
import logging
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
from scipy import stats

from app.data.loader import data_loader
from app.models.schemas import AnomalyItem, AnomalyReport
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AnomalyService:
    """Service for detecting anomalies in ticket data."""
    
    def __init__(self):
        self.data = data_loader
        self.settings = get_settings()
    
    def _detect_stale_critical_tickets(self) -> List[AnomalyItem]:
        """Detect unresolved critical/high priority tickets older than threshold."""
        anomalies = []
        df = self.data.get_data()
        
        # Calculate age in hours
        now = pd.Timestamp.now()
        df['age_hours'] = (now - df['created_at']).dt.total_seconds() / 3600
        
        # Critical tickets > 24 hours
        critical_stale = df[
            (df['status'] == 'Open') & 
            (df['priority'] == 'Critical') & 
            (df['age_hours'] > self.settings.critical_ticket_hours_threshold)
        ]
        
        for _, ticket in critical_stale.iterrows():
            anomalies.append(AnomalyItem(
                ticket_id=ticket['ticket_id'],
                anomaly_type="stale_critical_ticket",
                severity="critical",
                reason=f"Critical priority ticket open for {ticket['age_hours']:.1f} hours (threshold: {self.settings.critical_ticket_hours_threshold}h)",
                metadata={
                    "age_hours": float(ticket['age_hours']),
                    "priority": ticket['priority'],
                    "category": ticket['category'],
                    "agent_id": ticket['agent_id']
                }
            ))
        
        # High priority tickets > 48 hours
        high_stale = df[
            (df['status'] == 'Open') & 
            (df['priority'] == 'High') & 
            (df['age_hours'] > self.settings.high_priority_hours_threshold)
        ]
        
        for _, ticket in high_stale.iterrows():
            anomalies.append(AnomalyItem(
                ticket_id=ticket['ticket_id'],
                anomaly_type="stale_high_priority_ticket",
                severity="high",
                reason=f"High priority ticket open for {ticket['age_hours']:.1f} hours (threshold: {self.settings.high_priority_hours_threshold}h)",
                metadata={
                    "age_hours": float(ticket['age_hours']),
                    "priority": ticket['priority'],
                    "category": ticket['category'],
                    "agent_id": ticket['agent_id']
                }
            ))
        
        logger.info(f"Detected {len(anomalies)} stale high-priority tickets")
        return anomalies
    
    def _detect_resolution_time_outliers(self) -> List[AnomalyItem]:
        """Detect tickets with abnormally long resolution times using Z-score."""
        anomalies = []
        df = self.data.get_data()
        
        # Filter resolved tickets with resolution time
        resolved = df[(df['status'] == 'Resolved') & (df['resolution_time_hrs'].notna())].copy()
        
        if len(resolved) < 10:
            return anomalies
        
        # Calculate Z-scores per category
        for category in resolved['category'].unique():
            category_df = resolved[resolved['category'] == category].copy()
            
            if len(category_df) < 5:
                continue
            
            # Calculate Z-scores
            category_df['z_score'] = stats.zscore(category_df['resolution_time_hrs'])
            
            # Find outliers
            outliers = category_df[abs(category_df['z_score']) > self.settings.anomaly_z_threshold]
            
            for _, ticket in outliers.iterrows():
                category_mean = category_df['resolution_time_hrs'].mean()
                category_std = category_df['resolution_time_hrs'].std()
                
                anomalies.append(AnomalyItem(
                    ticket_id=ticket['ticket_id'],
                    anomaly_type="resolution_time_outlier",
                    severity="medium",
                    reason=f"Resolution time {ticket['resolution_time_hrs']:.1f}h is {abs(ticket['z_score']):.1f} standard deviations from mean ({category_mean:.1f}h) for {category} category",
                    metadata={
                        "resolution_time_hrs": float(ticket['resolution_time_hrs']),
                        "category": category,
                        "z_score": float(ticket['z_score']),
                        "category_mean": float(category_mean),
                        "category_std": float(category_std),
                        "agent_id": ticket['agent_id']
                    }
                ))
        
        logger.info(f"Detected {len(anomalies)} resolution time outliers")
        return anomalies
    
    def _detect_response_time_outliers(self) -> List[AnomalyItem]:
        """Detect tickets with abnormally long response times."""
        anomalies = []
        df = self.data.get_data()
        
        # Calculate Z-scores for response time
        if len(df) < 10:
            return anomalies
        
        df_copy = df.copy()
        df_copy['z_score'] = stats.zscore(df_copy['response_time_hrs'])
        
        outliers = df_copy[abs(df_copy['z_score']) > self.settings.anomaly_z_threshold]
        
        mean_response = df_copy['response_time_hrs'].mean()
        
        for _, ticket in outliers.iterrows():
            anomalies.append(AnomalyItem(
                ticket_id=ticket['ticket_id'],
                anomaly_type="response_time_outlier",
                severity="low",
                reason=f"Response time {ticket['response_time_hrs']:.1f}h is {abs(ticket['z_score']):.1f} standard deviations from mean ({mean_response:.1f}h)",
                metadata={
                    "response_time_hrs": float(ticket['response_time_hrs']),
                    "z_score": float(ticket['z_score']),
                    "priority": ticket['priority'],
                    "agent_id": ticket['agent_id']
                }
            ))
        
        logger.info(f"Detected {len(anomalies)} response time outliers")
        return anomalies
    
    def _detect_low_rated_agents(self) -> List[AnomalyItem]:
        """Detect agents with consistently low ratings."""
        anomalies = []
        df = self.data.get_data()
        
        # Calculate average rating per agent
        agent_ratings = df[df['customer_rating'].notna()].groupby('agent_id').agg({
            'customer_rating': ['mean', 'count']
        }).reset_index()
        
        agent_ratings.columns = ['agent_id', 'avg_rating', 'rating_count']
        
        # Filter agents with sufficient ratings and low average
        low_rated = agent_ratings[
            (agent_ratings['rating_count'] >= 5) & 
            (agent_ratings['avg_rating'] < self.settings.min_agent_rating)
        ]
        
        for _, agent in low_rated.iterrows():
            # Get a sample ticket for this agent
            sample_ticket = df[df['agent_id'] == agent['agent_id']].iloc[0]
            
            anomalies.append(AnomalyItem(
                ticket_id=f"AGENT-{agent['agent_id']}",
                anomaly_type="low_agent_rating",
                severity="medium",
                reason=f"Agent {agent['agent_id']} has average rating {agent['avg_rating']:.2f} across {int(agent['rating_count'])} tickets (threshold: {self.settings.min_agent_rating})",
                metadata={
                    "agent_id": agent['agent_id'],
                    "avg_rating": float(agent['avg_rating']),
                    "rating_count": int(agent['rating_count']),
                    "threshold": self.settings.min_agent_rating
                }
            ))
        
        logger.info(f"Detected {len(anomalies)} low-rated agents")
        return anomalies
    
    def detect_all_anomalies(self) -> AnomalyReport:
        """
        Run all anomaly detection algorithms and return comprehensive report.
        
        Returns:
            AnomalyReport with all detected anomalies
        """
        logger.info("Starting anomaly detection")
        
        all_anomalies: List[AnomalyItem] = []
        
        # Run all detectors
        all_anomalies.extend(self._detect_stale_critical_tickets())
        all_anomalies.extend(self._detect_resolution_time_outliers())
        all_anomalies.extend(self._detect_response_time_outliers())
        all_anomalies.extend(self._detect_low_rated_agents())
        
        # Categorize by severity
        critical = [a for a in all_anomalies if a.severity == "critical"]
        high = [a for a in all_anomalies if a.severity == "high"]
        medium = [a for a in all_anomalies if a.severity == "medium"]
        low = [a for a in all_anomalies if a.severity == "low"]
        
        # Count by type
        anomalies_by_type: Dict[str, int] = {}
        for anomaly in all_anomalies:
            anomalies_by_type[anomaly.anomaly_type] = anomalies_by_type.get(anomaly.anomaly_type, 0) + 1
        
        report = AnomalyReport(
            total_anomalies=len(all_anomalies),
            anomalies_by_type=anomalies_by_type,
            critical_anomalies=critical,
            high_anomalies=high,
            medium_anomalies=medium,
            low_anomalies=low
        )
        
        logger.info(f"Anomaly detection complete. Total anomalies: {len(all_anomalies)}")
        return report


# Global instance
anomaly_service = AnomalyService()
