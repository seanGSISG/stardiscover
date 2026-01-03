# Architecture

This document describes the technical architecture of StarDiscover.

## Overview

StarDiscover is a FastAPI-based web application that uses GitHub's API and LLM capabilities to provide personalized repository recommendations.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Browser     │────▶│    FastAPI      │────▶│   GitHub API    │
│                 │     │    (Backend)    │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  SQLite   │ │   Redis   │ │    LLM    │
            │    DB     │ │   Cache   │ │  Server   │
            └───────────┘ └───────────┘ └───────────┘
```

## Components

### Web Layer

**FastAPI Application** (`app/main.py`)
- Handles HTTP requests
- Session management via middleware
- Serves Jinja2 templates for the web UI
- RESTful API endpoints

**Routers** (`app/routers/`)
- `auth.py`: GitHub OAuth flow
- `github.py`: Star synchronization endpoints
- `recommendations.py`: Recommendation generation and retrieval

### Data Layer

**SQLite Database** (`app/database.py`)
- Async SQLAlchemy with aiosqlite
- Stores users, repositories, and recommendations
- File-based for easy deployment

**Models** (`app/models/`)
- `User`: GitHub user info and access tokens
- `Repository`: Cached repository metadata
- `Recommendation`: Generated recommendations with scores

### Service Layer

**GitHub Client** (`app/services/github_client.py`)
- Async HTTP client for GitHub API
- Rate limit handling
- Pagination support
- Redis caching for API responses

**LLM Client** (`app/services/llm_client.py`)
- OpenAI-compatible API client
- Supports any LLM with compatible endpoint
- JSON response parsing

**Profile Analyzer** (`app/services/profile_analyzer.py`)
- Analyzes user's starred repositories
- Generates taste profile using LLM
- Identifies patterns and preferences

**Similar Users** (`app/services/similar_users.py`)
- Finds GitHub users with overlapping stars
- Samples stargazers from user's repos
- Ranks by overlap percentage

**Recommendation Engine** (`app/services/recommendation_engine.py`)
- Orchestrates the recommendation pipeline
- Scores candidate repos against taste profile
- Filters and ranks recommendations

### Background Tasks

**Scheduler** (`app/tasks/scheduler.py`)
- APScheduler for cron-like scheduling
- Weekly recommendation refresh
- Runs full pipeline for all users

## Data Flow

### 1. User Authentication

```
Browser → /auth/login → GitHub OAuth → /auth/callback → Session Created
```

1. User clicks "Login with GitHub"
2. Redirect to GitHub authorization page
3. GitHub redirects back with authorization code
4. Exchange code for access token
5. Fetch user profile from GitHub
6. Create/update user in database
7. Store user ID in session

### 2. Star Synchronization

```
Trigger Sync → Fetch Stars → Cache in Redis → Store in DB
```

1. User triggers sync via UI
2. Background task fetches all starred repos
3. Responses cached in Redis
4. Repository metadata stored in SQLite

### 3. Recommendation Generation

```
Build Profile → Find Similar Users → Gather Candidates → Score & Rank
```

1. **Profile Building**: LLM analyzes starred repos to create taste profile
2. **Similar Users**: Sample stargazers, find users with high overlap
3. **Candidate Gathering**: Collect repos starred by similar users
4. **Scoring**: LLM rates each candidate against taste profile
5. **Storage**: Top recommendations saved to database

## Caching Strategy

### Redis Cache

- **GitHub API responses**: Reduces rate limit consumption
- **TTL**: 1 hour for most responses
- **Keys**: Prefixed with `stardiscover:`

### Database Caching

- Repository metadata cached after first fetch
- User taste profiles stored for quick access
- Recommendations persist until next refresh

## Configuration

All configuration via environment variables (see `app/config.py`):

```python
class Settings(BaseSettings):
    secret_key: str          # Session encryption
    github_client_id: str    # OAuth credentials
    github_client_secret: str
    llm_base_url: str        # LLM server endpoint
    redis_url: str           # Redis connection
    # ... etc
```

## Scalability Considerations

### Current Limitations

- SQLite: Single-writer, file-based
- In-process scheduler: Single instance only
- Session storage: In-memory (lost on restart)

### Production Recommendations

1. **Database**: Migrate to PostgreSQL for concurrent writes
2. **Scheduler**: Use Celery with Redis broker for distributed tasks
3. **Sessions**: Use Redis-backed sessions
4. **Caching**: Consider separate Redis instances for cache vs sessions
5. **Load Balancing**: Stateless design allows horizontal scaling
