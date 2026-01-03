# StarDiscover

A self-hosted application that analyzes your GitHub starred repositories using AI to learn your preferences and recommend new repositories weekly.

## Features

- **GitHub Integration** - Connects via OAuth to access your starred repositories
- **AI-Powered Analysis** - Uses LLMs to understand your coding interests and preferences
- **Taste Profile** - Builds a personalized profile based on your starred repos
- **Similar User Discovery** - Finds GitHub users with overlapping interests
- **Smart Recommendations** - Suggests repositories you might like based on your profile
- **Weekly Updates** - Automatically refreshes recommendations on a schedule
- **Feedback Loop** - Thumbs up/down to improve future recommendations

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A GitHub account
- An LLM server with OpenAI-compatible API (e.g., [Ollama](https://ollama.ai/))

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/stardiscover.git
cd stardiscover

# Copy the example environment file
cp .env.example .env

# Generate a random secret key
echo "SECRET_KEY=$(openssl rand -base64 32)" >> .env
```

### 2. Create a GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in the details:
   - **Application name**: StarDiscover
   - **Homepage URL**: `http://localhost:8085`
   - **Authorization callback URL**: `http://localhost:8085/auth/callback`
4. Click **Register application**
5. Copy the **Client ID** and generate a **Client Secret**
6. Add them to your `.env` file:
   ```
   GITHUB_CLIENT_ID=your-client-id
   GITHUB_CLIENT_SECRET=your-client-secret
   ```

### 3. Configure LLM

StarDiscover requires an LLM server with an OpenAI-compatible API. The easiest option is [Ollama](https://ollama.ai/):

```bash
# Install Ollama and pull a model
ollama pull gemma3:4b
```

Update your `.env` if using a different LLM endpoint:
```
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=gemma3:4b
```

### 4. Start the Application

```bash
docker compose up -d
```

Open http://localhost:8085 in your browser.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Session encryption key | (required) |
| `GITHUB_CLIENT_ID` | OAuth App Client ID | (required) |
| `GITHUB_CLIENT_SECRET` | OAuth App Secret | (required) |
| `GITHUB_REDIRECT_URI` | OAuth callback URL | `http://localhost:8085/auth/callback` |
| `LLM_BASE_URL` | LLM server endpoint | `http://localhost:11434` |
| `LLM_MODEL` | Model name to use | `gemma3:4b` |
| `REDIS_URL` | Redis connection URL | `redis://stardiscover-redis:6379/0` |
| `WEEKLY_REFRESH_DAY` | Day for weekly refresh | `sunday` |
| `WEEKLY_REFRESH_HOUR` | Hour for weekly refresh (24h) | `3` |

## Architecture

```
stardiscover/
├── docker-compose.yml      # FastAPI app + Redis
├── Dockerfile
├── .env.example            # Configuration template
└── app/
    ├── main.py             # FastAPI entry point
    ├── config.py           # Pydantic settings
    ├── database.py         # SQLAlchemy async setup
    ├── models/             # Database models
    ├── routers/            # API endpoints
    │   ├── auth.py         # GitHub OAuth
    │   ├── github.py       # Star syncing
    │   └── recommendations.py
    ├── services/           # Business logic
    │   ├── github_client.py    # GitHub API wrapper
    │   ├── llm_client.py       # LLM API client
    │   ├── profile_analyzer.py # Taste profile generation
    │   ├── similar_users.py    # User overlap analysis
    │   └── recommendation_engine.py
    ├── tasks/
    │   └── scheduler.py    # APScheduler for weekly jobs
    └── templates/          # Jinja2 HTML templates
```

## How It Works

1. **Connect GitHub** - OAuth authentication grants access to your starred repos
2. **Sync Stars** - Fetches all your starred repositories via GitHub API
3. **Build Profile** - LLM analyzes your repos to create a taste profile
4. **Find Similar Users** - Discovers users who star the same repos
5. **Score Candidates** - LLM evaluates candidate repos against your profile
6. **Weekly Refresh** - Scheduler automatically runs discovery on schedule

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard |
| `GET` | `/recommendations` | Recommendations page |
| `GET` | `/auth/login` | Start GitHub OAuth |
| `GET` | `/auth/callback` | OAuth callback |
| `POST` | `/auth/logout` | Clear session |
| `POST` | `/api/github/sync-stars` | Trigger star sync |
| `GET` | `/api/github/sync-status` | Check sync progress |
| `GET` | `/api/github/starred` | Get cached starred repos |
| `GET` | `/api/github/rate-limit` | Check GitHub API quota |
| `POST` | `/api/recommendations/generate` | Generate recommendations |
| `GET` | `/api/recommendations/status` | Check generation progress |
| `GET` | `/api/recommendations` | Get recommendations |
| `POST` | `/api/recommendations/{id}/feedback` | Submit feedback |
| `GET` | `/api/recommendations/profile` | Get taste profile |
| `GET` | `/health` | Health check |

## Development

### Running Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
pytest
```

## Troubleshooting

### Container won't start

```bash
docker logs stardiscover
```

### OAuth redirect fails

Ensure the callback URL in your GitHub OAuth App matches your `GITHUB_REDIRECT_URI` environment variable exactly.

### LLM not responding

Check if your LLM server is running:
```bash
curl http://localhost:11434/api/tags
```

### Reset database

```bash
rm data/stardiscover.db
docker compose restart stardiscover
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
