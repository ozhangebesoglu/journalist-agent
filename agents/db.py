"""
SQLite Database Layer for Gazeteci
Handles all database operations for persistence and trend tracking
"""
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "gazeteci.db"


@contextmanager
def get_connection():
    """Context manager for database connections."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            -- GitHub Repositories
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_id INTEGER UNIQUE,
                full_name TEXT NOT NULL UNIQUE,
                description TEXT,
                url TEXT NOT NULL,
                language TEXT,
                created_at TIMESTAMP,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Repository snapshots (daily star counts for trend analysis)
            CREATE TABLE IF NOT EXISTS repo_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                forks INTEGER,
                open_issues INTEGER,
                snapshot_date DATE NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(repo_id, snapshot_date)
            );

            -- Repository topics/tags
            CREATE TABLE IF NOT EXISTS repo_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(repo_id, topic)
            );

            -- Repository files (root directory)
            CREATE TABLE IF NOT EXISTS repo_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(repo_id, filename)
            );

            -- README content
            CREATE TABLE IF NOT EXISTS repo_readmes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL UNIQUE,
                content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repo_id) REFERENCES repositories(id)
            );

            -- Hacker News stories
            CREATE TABLE IF NOT EXISTS hn_stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hn_id INTEGER UNIQUE NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                score INTEGER,
                comment_count INTEGER,
                author TEXT,
                hn_link TEXT,
                article_summary TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- HN story comments
            CREATE TABLE IF NOT EXISTS hn_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER NOT NULL,
                author TEXT,
                content TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (story_id) REFERENCES hn_stories(id)
            );

            -- Reddit posts
            CREATE TABLE IF NOT EXISTS reddit_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reddit_id TEXT UNIQUE NOT NULL,
                subreddit TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                selftext TEXT,
                score INTEGER,
                upvote_ratio REAL,
                comment_count INTEGER,
                author TEXT,
                permalink TEXT,
                is_self BOOLEAN,
                created_utc TIMESTAMP,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Reddit comments
            CREATE TABLE IF NOT EXISTS reddit_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                reddit_comment_id TEXT,
                author TEXT,
                content TEXT,
                score INTEGER,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES reddit_posts(id)
            );

            -- Cross-references: GitHub repos mentioned in HN/Reddit
            CREATE TABLE IF NOT EXISTS repo_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                mention_date DATE NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(repo_id, source_type, source_id)
            );

            -- Briefing history
            CREATE TABLE IF NOT EXISTS briefings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_path TEXT
            );

            -- Featured repos per briefing
            CREATE TABLE IF NOT EXISTS briefing_repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                briefing_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                feature_type TEXT,
                FOREIGN KEY (briefing_id) REFERENCES briefings(id),
                FOREIGN KEY (repo_id) REFERENCES repositories(id),
                UNIQUE(briefing_id, repo_id)
            );

            -- Indexes for query performance
            CREATE INDEX IF NOT EXISTS idx_repo_snapshots_date ON repo_snapshots(snapshot_date);
            CREATE INDEX IF NOT EXISTS idx_repo_snapshots_repo ON repo_snapshots(repo_id);
            CREATE INDEX IF NOT EXISTS idx_repo_mentions_repo ON repo_mentions(repo_id);
            CREATE INDEX IF NOT EXISTS idx_repo_mentions_date ON repo_mentions(mention_date);
            CREATE INDEX IF NOT EXISTS idx_hn_stories_fetched ON hn_stories(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_reddit_posts_fetched ON reddit_posts(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_reddit_posts_subreddit ON reddit_posts(subreddit);
            CREATE INDEX IF NOT EXISTS idx_briefing_repos_repo ON briefing_repos(repo_id);
        """)
    print("   [DB] Veritabanı başlatıldı.")


# ============ Repository Operations ============

def upsert_repository(repo_data: dict) -> int:
    """Insert or update a repository, return its ID."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO repositories (github_id, full_name, description, url, language)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                github_id = excluded.github_id,
                description = excluded.description,
                url = excluded.url,
                language = excluded.language,
                last_updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            repo_data.get("github_id"),
            repo_data["name"],
            repo_data.get("desc"),
            repo_data["url"],
            repo_data.get("lang")
        ))
        return cursor.fetchone()[0]


def save_repo_snapshot(repo_id: int, stars: int, forks: int = None, open_issues: int = None):
    """Save a daily snapshot of repo stats."""
    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO repo_snapshots (repo_id, stars, forks, open_issues, snapshot_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, snapshot_date) DO UPDATE SET
                stars = excluded.stars,
                forks = excluded.forks,
                open_issues = excluded.open_issues,
                fetched_at = CURRENT_TIMESTAMP
        """, (repo_id, stars, forks, open_issues, today))


def save_repo_topics(repo_id: int, topics: list):
    """Save repository topics."""
    with get_connection() as conn:
        for topic in topics:
            conn.execute("""
                INSERT OR IGNORE INTO repo_topics (repo_id, topic)
                VALUES (?, ?)
            """, (repo_id, topic))


def save_repo_files(repo_id: int, files: list):
    """Save repository root files."""
    with get_connection() as conn:
        for filename in files:
            conn.execute("""
                INSERT OR IGNORE INTO repo_files (repo_id, filename)
                VALUES (?, ?)
            """, (repo_id, filename))


def save_repo_readme(repo_id: int, content: str):
    """Save or update README content."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO repo_readmes (repo_id, content)
            VALUES (?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                content = excluded.content,
                updated_at = CURRENT_TIMESTAMP
        """, (repo_id, content))


def get_repo_by_name(full_name: str) -> dict | None:
    """Get repository by full_name."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM repositories WHERE full_name = ?",
            (full_name,)
        ).fetchone()
        return dict(row) if row else None


def get_repo_history(repo_id: int, days: int = 30) -> list[dict]:
    """Get star history for a repository."""
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT stars, forks, open_issues, snapshot_date
            FROM repo_snapshots
            WHERE repo_id = ? AND snapshot_date >= ?
            ORDER BY snapshot_date ASC
        """, (repo_id, since)).fetchall()
        return [dict(row) for row in rows]


# ============ HN Operations ============

def save_hn_story(story_data: dict) -> int:
    """Save HN story, return its ID."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO hn_stories (hn_id, title, url, score, comment_count, author, hn_link, article_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(hn_id) DO UPDATE SET
                score = excluded.score,
                comment_count = excluded.comment_count,
                article_summary = excluded.article_summary,
                fetched_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            story_data["id"],
            story_data["title"],
            story_data.get("url"),
            story_data.get("score"),
            story_data.get("comments"),
            story_data.get("author"),
            story_data.get("hn_link"),
            story_data.get("article_summary")
        ))
        return cursor.fetchone()[0]


def save_hn_comments(story_id: int, comments: list[dict]):
    """Save comments for an HN story."""
    with get_connection() as conn:
        for comment in comments:
            conn.execute("""
                INSERT INTO hn_comments (story_id, author, content)
                VALUES (?, ?, ?)
            """, (story_id, comment.get("author"), comment.get("text")))


# ============ Reddit Operations ============

def save_reddit_post(post_data: dict) -> int:
    """Save Reddit post, return its ID."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO reddit_posts (
                reddit_id, subreddit, title, url, selftext, score,
                upvote_ratio, comment_count, author, permalink, is_self, created_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(reddit_id) DO UPDATE SET
                score = excluded.score,
                upvote_ratio = excluded.upvote_ratio,
                comment_count = excluded.comment_count,
                fetched_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            post_data["id"],
            post_data["subreddit"],
            post_data["title"],
            post_data.get("url"),
            post_data.get("selftext"),
            post_data.get("score"),
            post_data.get("upvote_ratio"),
            post_data.get("comments"),
            post_data.get("author"),
            post_data.get("permalink"),
            post_data.get("is_self"),
            post_data.get("created_utc")
        ))
        return cursor.fetchone()[0]


def save_reddit_comments(post_id: int, comments: list[dict]):
    """Save comments for a Reddit post."""
    with get_connection() as conn:
        for comment in comments:
            conn.execute("""
                INSERT INTO reddit_comments (post_id, reddit_comment_id, author, content, score)
                VALUES (?, ?, ?, ?, ?)
            """, (
                post_id,
                comment.get("id"),
                comment.get("author"),
                comment.get("text"),
                comment.get("score")
            ))


# ============ Mention Tracking ============

def save_repo_mention(repo_id: int, source_type: str, source_id: int):
    """Record a mention of a repo in HN/Reddit."""
    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO repo_mentions (repo_id, source_type, source_id, mention_date)
            VALUES (?, ?, ?, ?)
        """, (repo_id, source_type, source_id, today))


def get_mention_counts(repo_id: int, days: int = 7) -> dict:
    """Get HN and Reddit mention counts for a repo."""
    since = (date.today() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT source_type, COUNT(*) as count
            FROM repo_mentions
            WHERE repo_id = ? AND mention_date >= ?
            GROUP BY source_type
        """, (repo_id, since)).fetchall()

        counts = {"hn": 0, "reddit": 0}
        for row in rows:
            counts[row["source_type"]] = row["count"]
        return counts


# ============ Briefing Operations ============

def create_briefing(report_path: str = None) -> int:
    """Create a new briefing record, return its ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO briefings (report_path) VALUES (?)",
            (report_path,)
        )
        return cursor.lastrowid


def mark_repo_featured(briefing_id: int, repo_id: int, feature_type: str = "trending"):
    """Mark a repo as featured in a briefing."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO briefing_repos (briefing_id, repo_id, feature_type)
            VALUES (?, ?, ?)
        """, (briefing_id, repo_id, feature_type))


def get_previously_featured(days: int = 7) -> set[str]:
    """Get repo names featured in the last N days."""
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT r.full_name
            FROM briefing_repos br
            JOIN briefings b ON br.briefing_id = b.id
            JOIN repositories r ON br.repo_id = r.id
            WHERE b.generated_at >= ?
        """, (since,)).fetchall()
        return {row["full_name"] for row in rows}


def get_feature_count(repo_id: int) -> int:
    """Get how many times a repo has been featured."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM briefing_repos WHERE repo_id = ?",
            (repo_id,)
        ).fetchone()
        return row["count"]


# ============ Trend Queries ============

def get_star_growth(repo_id: int, days: int = 7) -> tuple[int, int] | None:
    """Get star count now and N days ago. Returns (current, past) or None."""
    today = date.today().isoformat()
    past = (date.today() - timedelta(days=days)).isoformat()

    with get_connection() as conn:
        current = conn.execute("""
            SELECT stars FROM repo_snapshots
            WHERE repo_id = ? AND snapshot_date = ?
        """, (repo_id, today)).fetchone()

        past_row = conn.execute("""
            SELECT stars FROM repo_snapshots
            WHERE repo_id = ? AND snapshot_date <= ?
            ORDER BY snapshot_date DESC LIMIT 1
        """, (repo_id, past)).fetchone()

        if current and past_row:
            return (current["stars"], past_row["stars"])
        elif current:
            return (current["stars"], None)
        return None


def get_all_repos_with_snapshots() -> list[dict]:
    """Get all repos that have at least one snapshot."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT r.id, r.full_name, r.description, r.url, r.language
            FROM repositories r
            JOIN repo_snapshots rs ON r.id = rs.repo_id
        """).fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
