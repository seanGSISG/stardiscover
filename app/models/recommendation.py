from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class SimilarUser(Base):
    __tablename__ = "similar_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    similar_github_id = Column(Integer, nullable=False)
    similar_github_username = Column(String(255), nullable=False)
    overlap_count = Column(Integer, nullable=False)
    overlap_percentage = Column(Float, nullable=False)
    discovered_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "similar_github_id", name="uq_similar_users"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    github_repo_id = Column(Integer, nullable=False)
    full_name = Column(String(255), nullable=False)
    description = Column(Text)
    topics = Column(Text)  # JSON array
    language = Column(String(100))
    stars_count = Column(Integer)
    relevance_score = Column(Float, nullable=False)
    explanation = Column(Text)
    source_users = Column(Text)  # JSON array of usernames
    batch_id = Column(String(36), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "github_repo_id", "batch_id", name="uq_recommendations"),
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    feedback_type = Column(String(20), nullable=False)  # thumbs_up, thumbs_down, dismiss
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "recommendation_id", name="uq_feedback"),
    )


class JobStatus(Base):
    __tablename__ = "job_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String(50), nullable=False)  # sync_stars, build_profile, find_similar, generate_recs
    status = Column(String(20), nullable=False)  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
