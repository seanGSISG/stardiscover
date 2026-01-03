from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from sqlalchemy import select, delete
from datetime import datetime
import json

from app.database import async_session
from app.models import User, StarredRepo, JobStatus
from app.services.github_client import get_github_client

router = APIRouter()


async def get_user_from_session(request: Request) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


async def sync_starred_repos_task(user_id: int, access_token: str):
    """Background task to sync starred repos"""
    async with async_session() as db:
        # Create job status
        job = JobStatus(
            user_id=user_id,
            job_type="sync_stars",
            status="running",
            progress=0,
            started_at=datetime.utcnow(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    try:
        client = await get_github_client(access_token)
        repos = await client.get_starred_repos()

        async with async_session() as db:
            # Update progress
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 50
            job.message = f"Found {len(repos)} starred repos"
            await db.commit()

            # Delete old starred repos
            await db.execute(delete(StarredRepo).where(StarredRepo.user_id == user_id))

            # Insert new starred repos
            for repo in repos:
                starred_repo = StarredRepo(
                    user_id=user_id,
                    github_repo_id=repo["id"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    topics=json.dumps(repo.get("topics", [])),
                    language=repo.get("language"),
                    stars_count=repo.get("stargazers_count"),
                    forks_count=repo.get("forks_count"),
                )
                db.add(starred_repo)

            # Update job status
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 100
            job.message = f"Synced {len(repos)} starred repos"
            job.completed_at = datetime.utcnow()
            await db.commit()

    except Exception as e:
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()


@router.post("/sync-stars")
async def sync_stars(request: Request, background_tasks: BackgroundTasks):
    """Trigger sync of starred repositories"""
    user = await get_user_from_session(request)

    # Check if there's already a running sync
    async with async_session() as db:
        result = await db.execute(
            select(JobStatus).where(
                JobStatus.user_id == user.id,
                JobStatus.job_type == "sync_stars",
                JobStatus.status == "running",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Sync already in progress")

    background_tasks.add_task(sync_starred_repos_task, user.id, user.access_token)
    return {"message": "Sync started", "status": "running"}


@router.get("/sync-status")
async def sync_status(request: Request):
    """Get status of the most recent sync job"""
    user = await get_user_from_session(request)

    async with async_session() as db:
        result = await db.execute(
            select(JobStatus)
            .where(JobStatus.user_id == user.id, JobStatus.job_type == "sync_stars")
            .order_by(JobStatus.created_at.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()

        if not job:
            return {"status": "no_sync", "message": "No sync has been performed"}

        return {
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }


@router.get("/starred")
async def get_starred(request: Request, limit: int = 100, offset: int = 0):
    """Get cached starred repositories"""
    user = await get_user_from_session(request)

    async with async_session() as db:
        result = await db.execute(
            select(StarredRepo)
            .where(StarredRepo.user_id == user.id)
            .order_by(StarredRepo.stars_count.desc())
            .limit(limit)
            .offset(offset)
        )
        repos = result.scalars().all()

        return [
            {
                "id": repo.id,
                "github_repo_id": repo.github_repo_id,
                "full_name": repo.full_name,
                "description": repo.description,
                "topics": json.loads(repo.topics) if repo.topics else [],
                "language": repo.language,
                "stars_count": repo.stars_count,
            }
            for repo in repos
        ]


@router.get("/rate-limit")
async def rate_limit(request: Request):
    """Check GitHub API rate limit"""
    user = await get_user_from_session(request)
    client = await get_github_client(user.access_token)
    return await client.get_rate_limit()
