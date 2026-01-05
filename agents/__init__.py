"""
Gazeteci Agents

Data fetchers, analyzers, and report generators.
"""

from agents import fetcher
from agents import hn_fetcher
from agents import reddit_fetcher
from agents import collector
from agents import writer
from agents import analyst
from agents import db
from agents import data_persister
from agents import trend_analyzer
from agents import telegram_bot
from agents import scheduler
from agents import ai_assistant
from agents import repo_watcher
from agents import discovery
from agents import utilities

__all__ = [
    "fetcher",
    "hn_fetcher",
    "reddit_fetcher",
    "collector",
    "writer",
    "analyst",
    "db",
    "data_persister",
    "trend_analyzer",
    "telegram_bot",
    "scheduler",
    "ai_assistant",
    "repo_watcher",
    "discovery",
    "utilities",
]
