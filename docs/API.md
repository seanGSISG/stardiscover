# API Documentation

StarDiscover provides a RESTful API for all operations. This document covers all available endpoints.

## Base URL

```
http://localhost:8085
```

## Authentication

Most API endpoints require authentication via session cookie. Authenticate first using the OAuth flow.

## Endpoints

### Health Check

#### `GET /health`

Check application health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-03T12:00:00Z"
}
```

---

### Authentication

#### `GET /auth/login`

Initiate GitHub OAuth flow. Redirects to GitHub authorization page.

**Response:** Redirect to GitHub

---

#### `GET /auth/callback`

OAuth callback handler. GitHub redirects here after authorization.

**Query Parameters:**
- `code` (string): Authorization code from GitHub

**Response:** Redirect to dashboard on success

---

#### `POST /auth/logout`

Clear user session.

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

### GitHub Operations

#### `POST /api/github/sync-stars`

Trigger synchronization of user's starred repositories.

**Response:**
```json
{
  "message": "Sync started",
  "task_id": "abc123"
}
```

---

#### `GET /api/github/sync-status`

Check the status of star synchronization.

**Response:**
```json
{
  "status": "in_progress",
  "progress": 45,
  "total": 100,
  "message": "Fetching page 5 of 10"
}
```

**Status values:**
- `idle`: No sync in progress
- `in_progress`: Sync running
- `completed`: Sync finished
- `error`: Sync failed

---

#### `GET /api/github/starred`

Get user's cached starred repositories.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `per_page` (int, optional): Items per page (default: 30, max: 100)

**Response:**
```json
{
  "repositories": [
    {
      "id": 12345,
      "full_name": "owner/repo",
      "description": "Repository description",
      "language": "Python",
      "stargazers_count": 1000,
      "topics": ["python", "api"],
      "html_url": "https://github.com/owner/repo"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 30
}
```

---

#### `GET /api/github/rate-limit`

Check GitHub API rate limit status.

**Response:**
```json
{
  "limit": 5000,
  "remaining": 4532,
  "reset": "2025-01-03T13:00:00Z"
}
```

---

### Recommendations

#### `POST /api/recommendations/generate`

Start recommendation generation pipeline.

**Response:**
```json
{
  "message": "Generation started",
  "task_id": "xyz789"
}
```

---

#### `GET /api/recommendations/status`

Check recommendation generation progress.

**Response:**
```json
{
  "status": "in_progress",
  "stage": "scoring_candidates",
  "progress": 60,
  "message": "Scoring repository 12 of 20"
}
```

**Stages:**
1. `building_profile`: Analyzing starred repos
2. `finding_similar_users`: Discovering users with overlap
3. `gathering_candidates`: Collecting candidate repos
4. `scoring_candidates`: LLM scoring each candidate
5. `completed`: Finished

---

#### `GET /api/recommendations`

Get current recommendations.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `per_page` (int, optional): Items per page (default: 10)

**Response:**
```json
{
  "recommendations": [
    {
      "id": 1,
      "repository": {
        "id": 67890,
        "full_name": "owner/recommended-repo",
        "description": "A great repository",
        "language": "TypeScript",
        "stargazers_count": 5000,
        "topics": ["typescript", "framework"],
        "html_url": "https://github.com/owner/recommended-repo"
      },
      "score": 0.92,
      "reason": "Matches your interest in TypeScript frameworks...",
      "feedback": null,
      "created_at": "2025-01-03T10:00:00Z"
    }
  ],
  "total": 20,
  "page": 1,
  "per_page": 10
}
```

---

#### `POST /api/recommendations/{id}/feedback`

Submit feedback for a recommendation.

**Path Parameters:**
- `id` (int): Recommendation ID

**Request Body:**
```json
{
  "feedback": "positive"
}
```

**Feedback values:**
- `positive`: Thumbs up
- `negative`: Thumbs down
- `null`: Clear feedback

**Response:**
```json
{
  "message": "Feedback recorded",
  "recommendation_id": 1,
  "feedback": "positive"
}
```

---

#### `GET /api/recommendations/profile`

Get user's taste profile.

**Response:**
```json
{
  "profile": {
    "summary": "Developer focused on web technologies...",
    "primary_languages": ["Python", "TypeScript", "Go"],
    "interests": [
      "Web frameworks",
      "Developer tools",
      "Machine learning"
    ],
    "patterns": [
      "Prefers well-documented projects",
      "Interested in CLI tools"
    ]
  },
  "generated_at": "2025-01-03T09:00:00Z",
  "based_on_repos": 150
}
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (not logged in)
- `404`: Resource not found
- `429`: Rate limited
- `500`: Internal server error

## Rate Limiting

The API respects GitHub's rate limits. Check `/api/github/rate-limit` to monitor your quota. Heavy operations (sync, generate) are rate-limited to prevent abuse.
