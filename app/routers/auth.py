from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session
from app.models import User

router = APIRouter()
settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/login")
async def login():
    """Redirect to GitHub OAuth"""
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user",
    }
    url = f"{GITHUB_AUTHORIZE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(request: Request, code: str = None, error: str = None):
    """Handle GitHub OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token in response")

        # Get user info
        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()

    # Create or update user in database
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.github_id == user_data["id"])
        )
        user = result.scalar_one_or_none()

        if user:
            user.access_token = access_token
            user.github_username = user_data["login"]
            user.github_avatar_url = user_data.get("avatar_url")
        else:
            user = User(
                github_id=user_data["id"],
                github_username=user_data["login"],
                github_avatar_url=user_data.get("avatar_url"),
                access_token=access_token,
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

        # Store user ID in session
        request.session["user_id"] = user.id

    return RedirectResponse(url="/")


@router.post("/logout")
async def logout(request: Request):
    """Clear session"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/me")
async def me(request: Request):
    """Get current user info"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user.id,
            "github_id": user.github_id,
            "github_username": user.github_username,
            "github_avatar_url": user.github_avatar_url,
            "has_taste_profile": user.taste_profile is not None,
        }
