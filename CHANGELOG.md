# Changelog

All notable changes to StarDiscover will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-01-03

### Added

- Initial release of StarDiscover
- GitHub OAuth authentication
- Star synchronization from GitHub API
- AI-powered taste profile generation using LLM
- Similar user discovery based on star overlap
- Smart repository recommendations with scoring
- Weekly automatic recommendation refresh
- Thumbs up/down feedback system
- Web dashboard with Jinja2 templates
- RESTful API endpoints
- Redis caching for GitHub API responses
- Docker Compose deployment
- SQLite database for persistence

### Technical

- FastAPI async backend
- SQLAlchemy with async support
- APScheduler for background tasks
- OpenAI-compatible LLM client
- Pydantic settings management
