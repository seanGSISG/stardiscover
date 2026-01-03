import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete

from app.database import async_session
from app.models import User, CandidateRepo, Recommendation, StarredRepo
from app.services.llm_client import get_llm_client


SCORING_PROMPT = """You are evaluating whether a GitHub repository would interest a specific developer.

Developer Profile:
{profile}

Repository to evaluate:
- Name: {repo_name}
- Description: {description}
- Topics: {topics}
- Language: {language}
- Stars: {stars}

Based on the developer's interests and this repository's focus, score the relevance from 0.0 to 1.0:
- 1.0 = Perfect match, exactly what they'd love
- 0.7-0.9 = Strong match, aligned with their interests
- 0.4-0.6 = Moderate match, somewhat related
- 0.1-0.3 = Weak match, tangentially related
- 0.0 = No match

Also provide a brief 1-2 sentence explanation of why this repo might (or might not) interest them.

Return ONLY a JSON object like this:
{{"score": 0.85, "explanation": "This library aligns with their interest in..."}}"""


async def score_candidate(
    candidate: Dict[str, Any], profile: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Score a single candidate repo against user's taste profile"""
    llm = get_llm_client()

    profile_text = f"""
Primary Interests: {', '.join(profile.get('primary_interests', []))}
Preferred Languages: {', '.join(profile.get('languages', []))}
Project Types: {', '.join(profile.get('project_types', []))}
Themes: {', '.join(profile.get('themes', []))}
Summary: {profile.get('summary', 'N/A')}
"""

    topics = candidate.get("topics", [])
    if isinstance(topics, str):
        topics = json.loads(topics)

    prompt = SCORING_PROMPT.format(
        profile=profile_text,
        repo_name=candidate["full_name"],
        description=candidate.get("description") or "No description",
        topics=", ".join(topics) if topics else "No topics",
        language=candidate.get("language") or "Unknown",
        stars=candidate.get("stars_count") or 0,
    )

    result = await llm.generate_json(prompt)
    if result:
        return {
            "score": float(result.get("score", 0)),
            "explanation": result.get("explanation", ""),
        }
    return None


async def generate_recommendations(user_id: int, top_n: int = 20) -> List[Dict[str, Any]]:
    """Generate recommendations by scoring candidates against taste profile"""

    async with async_session() as db:
        # Get user's taste profile
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.taste_profile:
            return []

        profile = json.loads(user.taste_profile)

        # Get top candidates by source_count
        result = await db.execute(
            select(CandidateRepo)
            .where(CandidateRepo.user_id == user_id)
            .order_by(CandidateRepo.source_count.desc())
            .limit(50)
        )
        candidates = result.scalars().all()

        if not candidates:
            return []

    # Score each candidate
    scored = []
    for candidate in candidates:
        candidate_dict = {
            "github_repo_id": candidate.github_repo_id,
            "full_name": candidate.full_name,
            "description": candidate.description,
            "topics": candidate.topics,
            "language": candidate.language,
            "stars_count": candidate.stars_count,
            "source_count": candidate.source_count,
        }

        score_result = await score_candidate(candidate_dict, profile)
        if score_result and score_result["score"] >= 0.4:
            scored.append({
                **candidate_dict,
                "relevance_score": score_result["score"],
                "explanation": score_result["explanation"],
            })

    # Sort by score and take top N
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    top_recommendations = scored[:top_n]

    # Store in database
    batch_id = str(uuid.uuid4())

    async with async_session() as db:
        for rec in top_recommendations:
            topics = rec.get("topics")
            if isinstance(topics, str):
                topics_json = topics
            else:
                topics_json = json.dumps(topics) if topics else "[]"

            recommendation = Recommendation(
                user_id=user_id,
                github_repo_id=rec["github_repo_id"],
                full_name=rec["full_name"],
                description=rec["description"],
                topics=topics_json,
                language=rec["language"],
                stars_count=rec["stars_count"],
                relevance_score=rec["relevance_score"],
                explanation=rec["explanation"],
                batch_id=batch_id,
            )
            db.add(recommendation)

        await db.commit()

    return top_recommendations
