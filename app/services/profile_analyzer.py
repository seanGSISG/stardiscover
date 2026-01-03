import json
from typing import Optional, Dict, Any, List
from sqlalchemy import select

from app.database import async_session
from app.models import User, StarredRepo
from app.services.llm_client import get_llm_client


TASTE_PROFILE_PROMPT = """Analyze this GitHub user's starred repositories and create a developer interest profile.

Starred Repositories (showing name, language, and description):
{repo_list}

Based on these repositories, create a detailed profile of this developer's interests.

Return a JSON object with these exact fields:
- "primary_interests": array of top 5 main technology areas they're interested in
- "languages": array of their preferred programming languages, ranked by frequency
- "project_types": array of types of projects they like (e.g., "frameworks", "cli-tools", "libraries", "devops", "web-apps")
- "themes": array of recurring themes across repos (e.g., "machine-learning", "web-development", "infrastructure", "productivity")
- "summary": a 2-3 sentence description of this developer's interests and focus areas

Example response format:
{{
  "primary_interests": ["Machine Learning", "Web Development", "DevOps"],
  "languages": ["Python", "TypeScript", "Go"],
  "project_types": ["libraries", "cli-tools", "frameworks"],
  "themes": ["automation", "data-science", "cloud-native"],
  "summary": "A developer focused on..."
}}"""


async def build_taste_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """Analyze user's starred repos and build a taste profile using LLM"""

    async with async_session() as db:
        # Get starred repos
        result = await db.execute(
            select(StarredRepo)
            .where(StarredRepo.user_id == user_id)
            .order_by(StarredRepo.stars_count.desc())
            .limit(100)  # Use top 100 starred repos
        )
        repos = result.scalars().all()

        if not repos:
            return None

        # Format repos for prompt
        repo_list = []
        for repo in repos:
            topics = json.loads(repo.topics) if repo.topics else []
            topics_str = ", ".join(topics[:5]) if topics else "no topics"
            desc = (repo.description or "")[:100]
            repo_list.append(f"- {repo.full_name} ({repo.language or 'unknown'}): {desc} [Topics: {topics_str}]")

        repo_text = "\n".join(repo_list)
        prompt = TASTE_PROFILE_PROMPT.format(repo_list=repo_text)

        # Generate profile using LLM
        llm = get_llm_client()
        profile = await llm.generate_json(prompt)

        if profile:
            # Store in user record
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            user.taste_profile = json.dumps(profile)
            from datetime import datetime
            user.taste_profile_updated_at = datetime.utcnow()
            await db.commit()

        return profile


def format_profile_for_display(profile: Dict[str, Any]) -> str:
    """Format taste profile as readable text"""
    if not profile:
        return "No profile available"

    lines = []
    lines.append(f"**Summary:** {profile.get('summary', 'N/A')}")
    lines.append("")
    lines.append(f"**Primary Interests:** {', '.join(profile.get('primary_interests', []))}")
    lines.append(f"**Preferred Languages:** {', '.join(profile.get('languages', []))}")
    lines.append(f"**Project Types:** {', '.join(profile.get('project_types', []))}")
    lines.append(f"**Themes:** {', '.join(profile.get('themes', []))}")

    return "\n".join(lines)
