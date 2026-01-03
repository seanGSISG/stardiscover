import json
from typing import List, Dict, Any, Set
from collections import Counter
from sqlalchemy import select, delete

from app.database import async_session
from app.models import StarredRepo, SimilarUser, CandidateRepo
from app.services.github_client import get_github_client
from app.config import get_settings

settings = get_settings()


async def discover_similar_users(user_id: int, access_token: str) -> List[Dict[str, Any]]:
    """
    Find users with similar starring patterns by:
    1. Sampling stargazers from user's starred repos
    2. Counting overlap in starred repos
    3. Ranking by overlap percentage
    """
    async with async_session() as db:
        # Get user's starred repos (sample top by stars)
        result = await db.execute(
            select(StarredRepo)
            .where(StarredRepo.user_id == user_id)
            .order_by(StarredRepo.stars_count.desc())
            .limit(50)  # Sample from top 50 starred repos
        )
        starred_repos = result.scalars().all()

        if not starred_repos:
            return []

        starred_repo_ids = {repo.github_repo_id for repo in starred_repos}

    # Get stargazers from each repo
    client = await get_github_client(access_token)
    user_star_counts: Counter = Counter()

    for repo in starred_repos[:30]:  # Limit API calls
        owner, name = repo.full_name.split("/")
        stargazers = await client.get_repo_stargazers(owner, name, sample_size=50)

        for stargazer in stargazers:
            user_star_counts[stargazer["login"]] += 1

    # Filter to users with significant overlap (starred at least 3 of the same repos)
    similar_users = []
    for username, overlap_count in user_star_counts.most_common(settings.max_similar_users * 2):
        if overlap_count >= 3:
            overlap_percentage = (overlap_count / len(starred_repos)) * 100
            similar_users.append({
                "username": username,
                "overlap_count": overlap_count,
                "overlap_percentage": round(overlap_percentage, 2),
            })

    # Limit to top N
    similar_users = similar_users[:settings.max_similar_users]

    # Store in database
    async with async_session() as db:
        # Clear old similar users
        await db.execute(delete(SimilarUser).where(SimilarUser.user_id == user_id))

        for su in similar_users:
            similar_user = SimilarUser(
                user_id=user_id,
                similar_github_id=0,  # We don't have the ID, just username
                similar_github_username=su["username"],
                overlap_count=su["overlap_count"],
                overlap_percentage=su["overlap_percentage"],
            )
            db.add(similar_user)

        await db.commit()

    return similar_users


async def gather_candidate_repos(
    user_id: int, access_token: str, starred_repo_ids: Set[int]
) -> List[Dict[str, Any]]:
    """
    Fetch starred repos from similar users and collect as candidates
    (excluding repos the user has already starred)
    """
    async with async_session() as db:
        # Get similar users
        result = await db.execute(
            select(SimilarUser)
            .where(SimilarUser.user_id == user_id)
            .order_by(SimilarUser.overlap_count.desc())
            .limit(20)
        )
        similar_users = result.scalars().all()

        if not similar_users:
            return []

    client = await get_github_client(access_token)
    candidate_counts: Dict[int, Dict[str, Any]] = {}

    for su in similar_users:
        repos = await client.get_user_starred(su.similar_github_username, per_page=100, max_pages=2)

        for repo in repos:
            repo_id = repo["id"]
            if repo_id in starred_repo_ids:
                continue  # Skip already starred

            if repo_id in candidate_counts:
                candidate_counts[repo_id]["source_count"] += 1
                candidate_counts[repo_id]["source_users"].append(su.similar_github_username)
            else:
                candidate_counts[repo_id] = {
                    "github_repo_id": repo_id,
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "topics": repo.get("topics", []),
                    "language": repo.get("language"),
                    "stars_count": repo.get("stargazers_count"),
                    "source_count": 1,
                    "source_users": [su.similar_github_username],
                }

    # Sort by source_count (how many similar users starred it)
    candidates = sorted(candidate_counts.values(), key=lambda x: x["source_count"], reverse=True)

    # Store in database
    async with async_session() as db:
        # Clear old candidates
        await db.execute(delete(CandidateRepo).where(CandidateRepo.user_id == user_id))

        for c in candidates[:200]:  # Keep top 200
            candidate = CandidateRepo(
                user_id=user_id,
                github_repo_id=c["github_repo_id"],
                full_name=c["full_name"],
                description=c["description"],
                topics=json.dumps(c["topics"]),
                language=c["language"],
                stars_count=c["stars_count"],
                source_count=c["source_count"],
            )
            db.add(candidate)

        await db.commit()

    return candidates[:100]  # Return top 100
