from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserResponse(BaseModel):
    id: int
    github_id: int
    github_username: str
    github_avatar_url: Optional[str]
    taste_profile: Optional[dict]
    taste_profile_updated_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RepoBase(BaseModel):
    github_repo_id: int
    full_name: str
    description: Optional[str]
    topics: Optional[List[str]]
    language: Optional[str]
    stars_count: Optional[int]


class StarredRepoResponse(RepoBase):
    id: int
    starred_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    id: int
    github_repo_id: int
    full_name: str
    description: Optional[str]
    topics: Optional[List[str]]
    language: Optional[str]
    stars_count: Optional[int]
    relevance_score: float
    explanation: Optional[str]
    source_users: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    id: int
    job_type: str
    status: str
    progress: int
    message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TasteProfile(BaseModel):
    primary_interests: List[str]
    languages: List[str]
    project_types: List[str]
    themes: List[str]
    summary: str


class FeedbackRequest(BaseModel):
    feedback_type: str  # thumbs_up, thumbs_down, dismiss
