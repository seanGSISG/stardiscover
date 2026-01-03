import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import User, StarredRepo, JobStatus
from app.services.github_client import get_github_client
from app.services.profile_analyzer import build_taste_profile
from app.services.similar_users import discover_similar_users, gather_candidate_repos
from app.services.recommendation_engine import generate_recommendations

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def refresh_user_recommendations(user_id: int):
    """Run the complete recommendation refresh for a single user"""
    logger.info(f"Starting recommendation refresh for user {user_id}")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.access_token:
            logger.warning(f"User {user_id} not found or no access token")
            return

        # Check if user has starred repos
        result = await db.execute(
            select(StarredRepo).where(StarredRepo.user_id == user_id).limit(1)
        )
        if not result.scalar_one_or_none():
            logger.info(f"User {user_id} has no starred repos, skipping")
            return

        access_token = user.access_token

    # Create job status for tracking
    async with async_session() as db:
        job = JobStatus(
            user_id=user_id,
            job_type="scheduled_refresh",
            status="running",
            progress=0,
            message="Weekly refresh started",
            started_at=datetime.utcnow(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    try:
        # Step 1: Sync stars (0-20%)
        logger.info(f"[User {user_id}] Syncing starred repos...")
        client = await get_github_client(access_token)
        repos = await client.get_starred_repos()

        async with async_session() as db:
            from sqlalchemy import delete
            from app.models import StarredRepo
            import json

            await db.execute(delete(StarredRepo).where(StarredRepo.user_id == user_id))

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
            await db.commit()

            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 20
            job.message = f"Synced {len(repos)} starred repos"
            await db.commit()

        # Step 2: Analyze profile (20-40%)
        logger.info(f"[User {user_id}] Analyzing taste profile...")
        await build_taste_profile(user_id)

        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 40
            job.message = "Taste profile updated"
            await db.commit()

        # Step 3: Find similar users (40-60%)
        logger.info(f"[User {user_id}] Finding similar users...")
        await discover_similar_users(user_id, access_token)

        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 60
            job.message = "Found similar users"
            await db.commit()

        # Step 4: Discover candidates (60-80%)
        logger.info(f"[User {user_id}] Discovering candidate repos...")
        # Get user's starred repo IDs to exclude from candidates
        async with async_session() as db:
            result = await db.execute(select(StarredRepo.github_repo_id).where(StarredRepo.user_id == user_id))
            starred_ids = set(r[0] for r in result.all())
        await gather_candidate_repos(user_id, access_token, starred_ids)

        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 80
            job.message = "Candidate repos discovered"
            await db.commit()

        # Step 5: Generate recommendations (80-100%)
        logger.info(f"[User {user_id}] Generating recommendations...")
        recommendations = await generate_recommendations(user_id)

        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 100
            job.message = f"Generated {len(recommendations)} new recommendations"
            job.completed_at = datetime.utcnow()
            await db.commit()

        logger.info(f"[User {user_id}] Weekly refresh completed with {len(recommendations)} recommendations")

    except Exception as e:
        logger.error(f"[User {user_id}] Refresh failed: {e}")
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.status = "failed"
            job.message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()


async def weekly_refresh_all_users():
    """Run weekly refresh for all users with starred repos"""
    logger.info("Starting weekly recommendation refresh for all users")

    async with async_session() as db:
        result = await db.execute(
            select(User.id)
            .join(StarredRepo, User.id == StarredRepo.user_id)
            .distinct()
        )
        user_ids = [row[0] for row in result.all()]

    logger.info(f"Found {len(user_ids)} users to refresh")

    for user_id in user_ids:
        try:
            await refresh_user_recommendations(user_id)
            # Small delay between users to avoid rate limits
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Failed to refresh user {user_id}: {e}")
            continue

    logger.info("Weekly refresh completed for all users")


def setup_scheduler():
    """Configure and start the APScheduler"""
    # Parse schedule from settings
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    day_of_week = day_map.get(settings.weekly_refresh_day.lower(), 6)  # Default Sunday
    hour = settings.weekly_refresh_hour

    trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=0)

    scheduler.add_job(
        weekly_refresh_all_users,
        trigger=trigger,
        id="weekly_refresh",
        name="Weekly recommendation refresh",
        replace_existing=True,
    )

    logger.info(
        f"Scheduler configured: Weekly refresh on {settings.weekly_refresh_day} at {hour}:00"
    )


def start_scheduler():
    """Start the scheduler (call after FastAPI startup)"""
    setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler (call on FastAPI shutdown)"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
