from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class StarredRepo(Base):
    __tablename__ = "starred_repos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    github_repo_id = Column(Integer, nullable=False)
    full_name = Column(String(255), nullable=False)
    description = Column(Text)
    topics = Column(Text)  # JSON array
    readme_summary = Column(Text)
    language = Column(String(100))
    stars_count = Column(Integer)
    forks_count = Column(Integer)
    starred_at = Column(DateTime)
    fetched_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "github_repo_id", name="uq_starred_repos_user_repo"),
    )


class CandidateRepo(Base):
    __tablename__ = "candidate_repos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    github_repo_id = Column(Integer, nullable=False)
    full_name = Column(String(255), nullable=False)
    description = Column(Text)
    topics = Column(Text)  # JSON array
    language = Column(String(100))
    stars_count = Column(Integer)
    source_count = Column(Integer, default=1)  # How many similar users starred this
    discovered_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "github_repo_id", name="uq_candidate_repos_user_repo"),
    )
