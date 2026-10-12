from typing import List, Dict, Any
from pydantic import BaseModel

class OverviewKPIResponse(BaseModel):
    published_benchmarks: List[Dict[str, Any]]
    total_responses: int
    high_readiness_pct: float
    high_willingness_pct: float
    country_distribution: List[Dict[str, Any]]
    top_difficulty_topics: List[Dict[str, Any]]
    preferred_formats: List[Dict[str, Any]]

class PreparationAnalyticsResponse(BaseModel):
    low_readiness_pct: float
    no_preparation_pct: float
    experienced_users: int
    high_difficulty_pct: float
    preparation_gaps: List[Dict[str, Any]]
    difficulty_by_country: List[Dict[str, Any]]
    difficulty_by_topic: List[Dict[str, Any]]
    adaptation_barriers: List[Dict[str, Any]]

class PrioritiesAnalyticsResponse(BaseModel):
    high_use_intention_pct: float
    mean_use_intention: float
    top_preferred_format_pct: float
    top_requested_support_pct: float
    requested_support_list: List[Dict[str, Any]]
    preferred_formats_list: List[Dict[str, Any]]
    use_intention_by_stage: List[Dict[str, Any]]
