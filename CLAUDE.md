# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gazeteci ("journalist" in Turkish) is a multi-agent AI system that generates daily tech briefings by collecting data from GitHub, Hacker News, and Reddit, then producing a JARVIS-style report (from Iron Man). The system uses Google's Gemini API for content generation and analysis, with SQLite for persistence and trend tracking.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the orchestrator (main entry point)
python orchestrator.py

# Run individual agents for testing
python -m agents.collector       # Collect data from GitHub + HN + Reddit
python -m agents.writer          # Generate draft report
python -m agents.analyst         # Evaluate and approve/reject draft
python -m agents.hn_fetcher      # Test HN fetcher standalone
python -m agents.reddit_fetcher  # Test Reddit fetcher standalone
python -m agents.db              # Initialize database
```

## Environment Variables

Required in `.env`:
- `GEMINI_API_KEY` - Google Gemini API key
- `GITHUB_TOKEN` - GitHub API token for fetching trending repos
- `REDDIT_CLIENT_ID` - Reddit API client ID (from reddit.com/prefs/apps)
- `REDDIT_CLIENT_SECRET` - Reddit API client secret
- `REDDIT_USER_AGENT` - Reddit API user agent (e.g., `gazeteci:v1.0 (by /u/username)`)

## Architecture

**Multi-Agent Pipeline** (`orchestrator.py`):
1. **Collector** → Fetcher + HN Fetcher + Reddit Fetcher → JSON + SQLite
2. **Writer** → Draft markdown report (JARVIS persona) with trend analysis
3. **Analyst** → Score & approve/revise loop (max 3 iterations)

**Agent Roles**:
- `fetcher.py`: GitHub API - trending repos, READMEs, topics, file trees
- `hn_fetcher.py`: Hacker News API - top stories, article scraping, comment extraction
- `reddit_fetcher.py`: Reddit API (PRAW) - posts from r/programming, r/machinelearning, r/Python, r/golang, r/rust, r/webdev, r/LocalLLaMA
- `collector.py`: Orchestrates data collection, saves to JSON and SQLite
- `writer.py`: Generates markdown briefing using Gemini with trend data
- `analyst.py`: Evaluates draft quality (score >= 7.5 = approved), tracks featured repos
- `db.py`: SQLite database layer for persistence
- `data_persister.py`: Bridge between fetchers and database
- `trend_analyzer.py`: Calculates star growth, mention frequency, trend classification

**Data Flow**:
```
GitHub API ──► fetcher ──┐
                         ├──► collector ──► data_persister ──► SQLite DB
HN API ──► hn_fetcher ───┤                                        │
                         │                                        ▼
Reddit API ──► reddit_fetcher ───────────────────────► trend_analyzer
                         │                                        │
                         ▼                                        ▼
                   JSON files ──► writer (with trends) ──► analyst ──► final report
```

**Feedback Loop**: Analyst rejection creates `data/feedback.json` with issues, writer reads this on next iteration to improve the draft.

## Database Schema

SQLite database at `data/gazeteci.db`:
- `repositories`: GitHub repos with metadata
- `repo_snapshots`: Daily star/fork counts for trend analysis
- `hn_stories`, `reddit_posts`: Social media content
- `repo_mentions`: Cross-references between repos and HN/Reddit
- `briefings`, `briefing_repos`: Track which repos were featured when

## Key Patterns

- All agents use `google.genai.Client` with `gemini-2.0-flash` model
- Analyst uses Pydantic schema for structured JSON output (`FeedbackSchema`)
- Writer prompt includes JARVIS persona rules and output format template
- Concurrent fetching with `ThreadPoolExecutor` in HN and Reddit fetchers
- SQLite with context manager pattern for connection handling
- Trend classification: RISING, STEADY, DECLINING, NEW based on star growth acceleration
