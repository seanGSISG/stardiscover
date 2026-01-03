from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from sqlalchemy import select, delete, func
from datetime import datetime
import json

from app.database import async_session
from app.models import User, StarredRepo, Recommendation, Feedback, JobStatus
from app.services.profile_analyzer import build_taste_profile
from app.services.similar_users import discover_similar_users, gather_candidate_repos
from app.services.recommendation_engine import generate_recommendations

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


async def full_recommendation_pipeline(user_id: int, access_token: str):
    """Background task running the complete recommendation pipeline"""
    async with async_session() as db:
        job = JobStatus(
            user_id=user_id,
            job_type="generate_recs",
            status="running",
            progress=0,
            message="Starting recommendation pipeline...",
            started_at=datetime.utcnow(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    try:
        # Step 1: Build taste profile (10-30%)
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 10
            job.message = "Analyzing your starred repos..."
            await db.commit()

        await build_taste_profile(user_id)

        # Step 2: Find similar users (30-60%)
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 30
            job.message = "Finding users with similar taste..."
            await db.commit()

        await discover_similar_users(user_id, access_token)

        # Step 3: Discover candidate repos (60-80%)
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 60
            job.message = "Discovering candidate repositories..."
            await db.commit()

        # Get user's starred repo IDs to exclude from candidates
        async with async_session() as db:
            result = await db.execute(select(StarredRepo.github_repo_id).where(StarredRepo.user_id == user_id))
            starred_ids = set(r[0] for r in result.all())
        await gather_candidate_repos(user_id, access_token, starred_ids)

        # Step 4: Score and rank (80-100%)
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.progress = 80
            job.message = "Scoring recommendations with AI..."
            await db.commit()

        recommendations = await generate_recommendations(user_id)

        # Complete
        async with async_session() as db:
            result = await db.execute(select(JobStatus).where(JobStatus.id == job_id))
            job = result.scalar_one()
            job.status = "completed"
            job.progress = 100
            job.message = f"Generated {len(recommendations)} recommendations!"
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


@router.post("/generate")
async def generate(request: Request, background_tasks: BackgroundTasks):
    """Start the full recommendation generation pipeline"""
    user = await get_user_from_session(request)

    # Check starred repos exist
    async with async_session() as db:
        result = await db.execute(
            select(func.count(StarredRepo.id)).where(StarredRepo.user_id == user.id)
        )
        count = result.scalar()
        if count == 0:
            raise HTTPException(
                status_code=400,
                detail="No starred repos found. Please sync your stars first.",
            )

        # Check if pipeline is already running
        result = await db.execute(
            select(JobStatus).where(
                JobStatus.user_id == user.id,
                JobStatus.job_type == "generate_recs",
                JobStatus.status == "running",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400, detail="Recommendation generation already in progress"
            )

    background_tasks.add_task(
        full_recommendation_pipeline, user.id, user.access_token
    )
    return {"message": "Recommendation generation started", "status": "running"}


@router.get("/status")
async def status(request: Request):
    """Get status of the most recent recommendation job"""
    user = await get_user_from_session(request)

    async with async_session() as db:
        result = await db.execute(
            select(JobStatus)
            .where(JobStatus.user_id == user.id, JobStatus.job_type == "generate_recs")
            .order_by(JobStatus.created_at.desc())
            .limit(1)
        )
        job = result.scalar_one_or_none()

        if not job:
            return {"status": "no_job", "message": "No recommendations generated yet"}

        return {
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }


@router.get("")
async def list_recommendations(
    request: Request, limit: int = 20, offset: int = 0, batch_id: str = None
):
    """Get recommendations for the current user"""
    user = await get_user_from_session(request)

    async with async_session() as db:
        query = select(Recommendation).where(Recommendation.user_id == user.id)

        if batch_id:
            query = query.where(Recommendation.batch_id == batch_id)
        else:
            # Get the most recent batch
            subq = (
                select(Recommendation.batch_id)
                .where(Recommendation.user_id == user.id)
                .order_by(Recommendation.created_at.desc())
                .limit(1)
            )
            result = await db.execute(subq)
            latest_batch = result.scalar()
            if latest_batch:
                query = query.where(Recommendation.batch_id == latest_batch)

        query = (
            query.order_by(Recommendation.relevance_score.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        recommendations = result.scalars().all()

        # Get feedback for these recommendations
        rec_ids = [r.id for r in recommendations]
        feedback_result = await db.execute(
            select(Feedback).where(
                Feedback.user_id == user.id, Feedback.recommendation_id.in_(rec_ids)
            )
        )
        feedback_map = {f.recommendation_id: f.feedback_type for f in feedback_result.scalars().all()}

        return [
            {
                "id": rec.id,
                "github_repo_id": rec.github_repo_id,
                "full_name": rec.full_name,
                "description": rec.description,
                "topics": json.loads(rec.topics) if rec.topics else [],
                "language": rec.language,
                "stars_count": rec.stars_count,
                "relevance_score": rec.relevance_score,
                "explanation": rec.explanation,
                "batch_id": rec.batch_id,
                "created_at": rec.created_at,
                "feedback": feedback_map.get(rec.id),
            }
            for rec in recommendations
        ]


@router.post("/{recommendation_id}/feedback")
async def submit_feedback(
    request: Request, recommendation_id: int, feedback_type: str
):
    """Submit feedback on a recommendation"""
    user = await get_user_from_session(request)

    if feedback_type not in ("thumbs_up", "thumbs_down", "dismiss"):
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    async with async_session() as db:
        # Verify recommendation exists and belongs to user
        result = await db.execute(
            select(Recommendation).where(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user.id,
            )
        )
        rec = result.scalar_one_or_none()
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        # Upsert feedback
        result = await db.execute(
            select(Feedback).where(
                Feedback.user_id == user.id,
                Feedback.recommendation_id == recommendation_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.feedback_type = feedback_type
        else:
            feedback = Feedback(
                user_id=user.id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
            )
            db.add(feedback)

        await db.commit()

    return {"message": "Feedback submitted", "feedback_type": feedback_type}


@router.get("/profile")
async def get_profile(request: Request):
    """Get the user's taste profile"""
    user = await get_user_from_session(request)

    if not user.taste_profile:
        return {"profile": None, "message": "No taste profile generated yet"}

    return {"profile": json.loads(user.taste_profile)}


@router.post("/profile/analyze")
async def trigger_profile_analysis(request: Request, background_tasks: BackgroundTasks):
    """Trigger taste profile analysis"""
    user = await get_user_from_session(request)

    # Check starred repos exist
    async with async_session() as db:
        result = await db.execute(
            select(func.count(StarredRepo.id)).where(StarredRepo.user_id == user.id)
        )
        count = result.scalar()
        if count == 0:
            raise HTTPException(
                status_code=400,
                detail="No starred repos found. Please sync your stars first.",
            )

    background_tasks.add_task(build_taste_profile, user.id)
    return {"message": "Profile analysis started"}
