# Deployment Guide

This guide covers various deployment options for StarDiscover.

## Docker Compose (Recommended)

The simplest way to deploy StarDiscover.

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+
- 1GB RAM minimum
- 1GB disk space

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/seanGSISG/stardiscover.git
   cd stardiscover
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env

   # Generate a secure secret key
   echo "SECRET_KEY=$(openssl rand -base64 32)" >> .env

   # Edit .env with your GitHub OAuth credentials
   nano .env
   ```

3. **Start the application**
   ```bash
   docker compose up -d
   ```

4. **Verify deployment**
   ```bash
   curl http://localhost:8085/health
   ```

### Updating

```bash
git pull
docker compose up -d --build
```

---

## Production Deployment

For production environments, additional hardening is recommended.

### Using a Reverse Proxy

#### nginx Configuration

```nginx
server {
    listen 80;
    server_name stardiscover.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name stardiscover.example.com;

    ssl_certificate /etc/letsencrypt/live/stardiscover.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stardiscover.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8085;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Traefik Configuration

```yaml
# docker-compose.override.yml
services:
  stardiscover:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.stardiscover.rule=Host(`stardiscover.example.com`)"
      - "traefik.http.routers.stardiscover.tls.certresolver=letsencrypt"
```

### Environment Variables for Production

```bash
# Required
SECRET_KEY=<long-random-string>
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_CLIENT_SECRET=<your-client-secret>
GITHUB_REDIRECT_URI=https://stardiscover.example.com/auth/callback

# LLM Server
LLM_BASE_URL=http://your-llm-server:11434
LLM_MODEL=gemma3:4b

# Optional tuning
DEBUG=false
WEEKLY_REFRESH_DAY=sunday
WEEKLY_REFRESH_HOUR=3
```

### Data Persistence

The SQLite database is stored in `./data/`. For production:

1. **Backup regularly**
   ```bash
   # Add to crontab
   0 2 * * * cp /path/to/stardiscover/data/stardiscover.db /backups/stardiscover-$(date +\%Y\%m\%d).db
   ```

2. **Consider PostgreSQL** for high-availability setups (requires code modification)

---

## LLM Server Setup

StarDiscover requires an LLM server with OpenAI-compatible API.

### Option 1: Ollama (Recommended)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull gemma3:4b

# Ollama runs on port 11434 by default
```

Update `.env`:
```bash
LLM_BASE_URL=http://host.docker.internal:11434  # For Docker
# or
LLM_BASE_URL=http://localhost:11434  # For local development
```

### Option 2: vLLM

```bash
pip install vllm
vllm serve google/gemma-3-4b --port 8081
```

### Option 3: Text Generation Inference

```bash
docker run -p 8081:80 \
  -v /path/to/models:/data \
  ghcr.io/huggingface/text-generation-inference \
  --model-id google/gemma-3-4b
```

---

## Monitoring

### Health Check

```bash
curl http://localhost:8085/health
```

### Logs

```bash
# All logs
docker compose logs -f

# Application only
docker compose logs -f stardiscover
```

### Metrics

Consider adding Prometheus metrics endpoint for production monitoring.

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs stardiscover

# Common issues:
# - Missing .env file
# - Invalid SECRET_KEY
# - Port 8085 already in use
```

### OAuth fails

1. Verify GitHub OAuth App settings match your `GITHUB_REDIRECT_URI`
2. Check the callback URL uses the correct protocol (http/https)
3. Ensure the GitHub App is not suspended

### LLM connection errors

```bash
# Test LLM connectivity
curl http://your-llm-server:11434/api/tags

# Check Docker networking
docker compose exec stardiscover curl http://host.docker.internal:11434/api/tags
```

### Database issues

```bash
# Reset database
rm data/stardiscover.db
docker compose restart stardiscover
```

---

## Security Checklist

- [ ] Generated strong `SECRET_KEY`
- [ ] Using HTTPS in production
- [ ] GitHub OAuth credentials not in version control
- [ ] Database file permissions restricted
- [ ] Redis not exposed to public network
- [ ] Regular backups configured
- [ ] Log monitoring in place
