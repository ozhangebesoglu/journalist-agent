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

            -- ============ ASSISTANT FEATURES ============

            -- Watched repos for notifications
            CREATE TABLE IF NOT EXISTS watched_repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                repo_url TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                last_stars INTEGER,
                last_release TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, repo_url)
            );

            -- Keyword alerts for HN
            CREATE TABLE IF NOT EXISTS keyword_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, keyword)
            );

            -- Bookmarks
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Notes
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Code snippets
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                name TEXT NOT NULL,
                language TEXT,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, name)
            );

            -- Reminders
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                message TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                is_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Chat history for AI context
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_watched_repos_chat ON watched_repos(chat_id);
            CREATE INDEX IF NOT EXISTS idx_bookmarks_chat ON bookmarks(chat_id);
            CREATE INDEX IF NOT EXISTS idx_snippets_chat ON snippets(chat_id);
            CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(is_sent, remind_at);

            -- ============ YENİ ÖZELLİKLER ============

            -- Kullanıcı tercihleri (kişiselleştirilmiş feed)
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT UNIQUE NOT NULL,
                interests TEXT,  -- JSON: ["python", "rust", "ai"]
                languages TEXT,  -- JSON: ["Python", "Rust", "Go"]
                min_stars INTEGER DEFAULT 100,
                notification_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Öğrenme takibi
            CREATE TABLE IF NOT EXISTS learning_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                category TEXT,  -- language, framework, concept
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                interaction_count INTEGER DEFAULT 1,
                mastery_level INTEGER DEFAULT 0  -- 0-5
            );

            -- Akıllı bildirimler geçmişi
            CREATE TABLE IF NOT EXISTS smart_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                notification_type TEXT NOT NULL,  -- star_milestone, security, release, trending
                repo_name TEXT,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Haftalık rapor geçmişi
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                week_start DATE NOT NULL,
                week_end DATE NOT NULL,
                report_data TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Proaktif öneriler geçmişi
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                suggestion_type TEXT NOT NULL,  -- repo, topic, learning
                content TEXT NOT NULL,
                is_shown BOOLEAN DEFAULT FALSE,
                is_accepted BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_user_prefs_chat ON user_preferences(chat_id);
            CREATE INDEX IF NOT EXISTS idx_learning_chat ON learning_topics(chat_id);
            CREATE INDEX IF NOT EXISTS idx_smart_notif_chat ON smart_notifications(chat_id);
            CREATE INDEX IF NOT EXISTS idx_weekly_reports_week ON weekly_reports(week_start);
        """)
    print("   [DB] Veritabanı başlatıldı.")


# ============ Repository Operations ============

def upsert_repository(repo_data: dict) -> int:
    """Insert or update a repository, return its ID."""
    with get_connection() as conn:
        # Önce github_id ile kontrol et
        existing = conn.execute(
            "SELECT id FROM repositories WHERE github_id = ?",
            (repo_data.get("github_id"),)
        ).fetchone()

        if existing:
            # Güncelle
            conn.execute("""
                UPDATE repositories SET
                    full_name = ?,
                    description = ?,
                    url = ?,
                    language = ?,
                    last_updated_at = CURRENT_TIMESTAMP
                WHERE github_id = ?
            """, (
                repo_data["name"],
                repo_data.get("desc"),
                repo_data["url"],
                repo_data.get("lang"),
                repo_data.get("github_id")
            ))
            return existing[0]
        else:
            # Yeni ekle
            cursor = conn.execute("""
                INSERT INTO repositories (github_id, full_name, description, url, language)
                VALUES (?, ?, ?, ?, ?)
            """, (
                repo_data.get("github_id"),
                repo_data["name"],
                repo_data.get("desc"),
                repo_data["url"],
                repo_data.get("lang")
            ))
            return cursor.lastrowid


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


# ============ Watched Repos ============

def add_watched_repo(chat_id: str, repo_url: str, repo_name: str, stars: int = None) -> bool:
    """Add a repo to watch list."""
    with get_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO watched_repos (chat_id, repo_url, repo_name, last_stars)
                VALUES (?, ?, ?, ?)
            """, (chat_id, repo_url, repo_name, stars))
            return True
        except:
            return False


def remove_watched_repo(chat_id: str, repo_name: str) -> bool:
    """Remove a repo from watch list."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM watched_repos WHERE chat_id = ? AND repo_name LIKE ?",
            (chat_id, f"%{repo_name}%")
        )
        return cursor.rowcount > 0


def get_watched_repos(chat_id: str) -> list[dict]:
    """Get all watched repos for a chat."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM watched_repos WHERE chat_id = ?",
            (chat_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_watched_repos() -> list[dict]:
    """Get all watched repos across all chats."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM watched_repos").fetchall()
        return [dict(row) for row in rows]


def update_watched_repo(repo_id: int, stars: int = None, release: str = None):
    """Update watched repo stats."""
    with get_connection() as conn:
        if stars is not None:
            conn.execute(
                "UPDATE watched_repos SET last_stars = ? WHERE id = ?",
                (stars, repo_id)
            )
        if release is not None:
            conn.execute(
                "UPDATE watched_repos SET last_release = ? WHERE id = ?",
                (release, repo_id)
            )


# ============ Keyword Alerts ============

def add_keyword_alert(chat_id: str, keyword: str) -> bool:
    """Add a keyword alert."""
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO keyword_alerts (chat_id, keyword) VALUES (?, ?)",
                (chat_id, keyword.lower())
            )
            return True
        except:
            return False


def remove_keyword_alert(chat_id: str, keyword: str) -> bool:
    """Remove a keyword alert."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM keyword_alerts WHERE chat_id = ? AND keyword = ?",
            (chat_id, keyword.lower())
        )
        return cursor.rowcount > 0


def get_keyword_alerts(chat_id: str) -> list[str]:
    """Get all keyword alerts for a chat."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT keyword FROM keyword_alerts WHERE chat_id = ?",
            (chat_id,)
        ).fetchall()
        return [row["keyword"] for row in rows]


def get_all_keyword_alerts() -> list[dict]:
    """Get all keyword alerts across all chats."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM keyword_alerts").fetchall()
        return [dict(row) for row in rows]


# ============ Bookmarks ============

def add_bookmark(chat_id: str, url: str, title: str = None, tags: str = None) -> int:
    """Add a bookmark."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO bookmarks (chat_id, url, title, tags) VALUES (?, ?, ?, ?)",
            (chat_id, url, title, tags)
        )
        return cursor.lastrowid


def get_bookmarks(chat_id: str, limit: int = 20) -> list[dict]:
    """Get bookmarks for a chat."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM bookmarks WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
            (chat_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]


def delete_bookmark(chat_id: str, bookmark_id: int) -> bool:
    """Delete a bookmark."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM bookmarks WHERE chat_id = ? AND id = ?",
            (chat_id, bookmark_id)
        )
        return cursor.rowcount > 0


def search_bookmarks(chat_id: str, query: str) -> list[dict]:
    """Search bookmarks by title or tags."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM bookmarks
            WHERE chat_id = ? AND (title LIKE ? OR tags LIKE ? OR url LIKE ?)
            ORDER BY created_at DESC
        """, (chat_id, f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        return [dict(row) for row in rows]


# ============ Notes ============

def add_note(chat_id: str, content: str) -> int:
    """Add a note."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO notes (chat_id, content) VALUES (?, ?)",
            (chat_id, content)
        )
        return cursor.lastrowid


def get_notes(chat_id: str, limit: int = 20) -> list[dict]:
    """Get notes for a chat."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
            (chat_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]


def delete_note(chat_id: str, note_id: int) -> bool:
    """Delete a note."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM notes WHERE chat_id = ? AND id = ?",
            (chat_id, note_id)
        )
        return cursor.rowcount > 0


# ============ Snippets ============

def save_snippet(chat_id: str, name: str, code: str, language: str = None) -> bool:
    """Save a code snippet."""
    with get_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO snippets (chat_id, name, code, language)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, name) DO UPDATE SET
                    code = excluded.code,
                    language = excluded.language
            """, (chat_id, name, code, language))
            return True
        except:
            return False


def get_snippet(chat_id: str, name: str) -> dict | None:
    """Get a snippet by name."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM snippets WHERE chat_id = ? AND name = ?",
            (chat_id, name)
        ).fetchone()
        return dict(row) if row else None


def get_all_snippets(chat_id: str) -> list[dict]:
    """Get all snippets for a chat."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM snippets WHERE chat_id = ? ORDER BY name",
            (chat_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def delete_snippet(chat_id: str, name: str) -> bool:
    """Delete a snippet."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM snippets WHERE chat_id = ? AND name = ?",
            (chat_id, name)
        )
        return cursor.rowcount > 0


# ============ Reminders ============

def add_reminder(chat_id: str, message: str, remind_at: datetime) -> int:
    """Add a reminder."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reminders (chat_id, message, remind_at) VALUES (?, ?, ?)",
            (chat_id, message, remind_at.isoformat())
        )
        return cursor.lastrowid


def get_pending_reminders() -> list[dict]:
    """Get all pending reminders that are due."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM reminders
            WHERE is_sent = FALSE AND remind_at <= ?
        """, (now,)).fetchall()
        return [dict(row) for row in rows]


def mark_reminder_sent(reminder_id: int):
    """Mark a reminder as sent."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE reminders SET is_sent = TRUE WHERE id = ?",
            (reminder_id,)
        )


def get_user_reminders(chat_id: str) -> list[dict]:
    """Get pending reminders for a user."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM reminders
            WHERE chat_id = ? AND is_sent = FALSE
            ORDER BY remind_at
        """, (chat_id,)).fetchall()
        return [dict(row) for row in rows]


def delete_reminder(chat_id: str, reminder_id: int) -> bool:
    """Delete a reminder."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM reminders WHERE chat_id = ? AND id = ?",
            (chat_id, reminder_id)
        )
        return cursor.rowcount > 0


# ============ Chat History ============

def add_chat_message(chat_id: str, role: str, content: str):
    """Add a message to chat history."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content)
        )
        # Keep only last 20 messages per chat
        conn.execute("""
            DELETE FROM chat_history WHERE chat_id = ? AND id NOT IN (
                SELECT id FROM chat_history WHERE chat_id = ?
                ORDER BY created_at DESC LIMIT 20
            )
        """, (chat_id, chat_id))


def get_chat_history(chat_id: str, limit: int = 10) -> list[dict]:
    """Get recent chat history."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT role, content FROM chat_history
            WHERE chat_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (chat_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]


def clear_chat_history(chat_id: str):
    """Clear chat history for a user."""
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))


# ============ User Preferences ============

def get_user_preferences(chat_id: str) -> dict | None:
    """Get user preferences."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
        if row:
            import json
            prefs = dict(row)
            prefs['interests'] = json.loads(prefs['interests']) if prefs['interests'] else []
            prefs['languages'] = json.loads(prefs['languages']) if prefs['languages'] else []
            return prefs
        return None


def save_user_preferences(chat_id: str, interests: list = None, languages: list = None, 
                          min_stars: int = None, notification_enabled: bool = None):
    """Save or update user preferences."""
    import json
    with get_connection() as conn:
        existing = get_user_preferences(chat_id)
        if existing:
            updates = []
            params = []
            if interests is not None:
                updates.append("interests = ?")
                params.append(json.dumps(interests))
            if languages is not None:
                updates.append("languages = ?")
                params.append(json.dumps(languages))
            if min_stars is not None:
                updates.append("min_stars = ?")
                params.append(min_stars)
            if notification_enabled is not None:
                updates.append("notification_enabled = ?")
                params.append(notification_enabled)
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(chat_id)
            conn.execute(f"UPDATE user_preferences SET {', '.join(updates)} WHERE chat_id = ?", params)
        else:
            conn.execute("""
                INSERT INTO user_preferences (chat_id, interests, languages, min_stars, notification_enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, json.dumps(interests or []), json.dumps(languages or []), 
                  min_stars or 100, notification_enabled if notification_enabled is not None else True))


def add_user_interest(chat_id: str, interest: str):
    """Add an interest to user preferences."""
    prefs = get_user_preferences(chat_id)
    interests = prefs['interests'] if prefs else []
    if interest.lower() not in [i.lower() for i in interests]:
        interests.append(interest.lower())
        save_user_preferences(chat_id, interests=interests)


def remove_user_interest(chat_id: str, interest: str):
    """Remove an interest from user preferences."""
    prefs = get_user_preferences(chat_id)
    if prefs:
        interests = [i for i in prefs['interests'] if i.lower() != interest.lower()]
        save_user_preferences(chat_id, interests=interests)


# ============ Learning Topics ============

def track_learning_topic(chat_id: str, topic: str, category: str = None):
    """Track a learning topic interaction."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id, interaction_count FROM learning_topics WHERE chat_id = ? AND topic = ?",
            (chat_id, topic.lower())
        ).fetchone()
        
        if existing:
            conn.execute("""
                UPDATE learning_topics SET 
                    last_seen = CURRENT_TIMESTAMP,
                    interaction_count = interaction_count + 1
                WHERE id = ?
            """, (existing['id'],))
        else:
            conn.execute("""
                INSERT INTO learning_topics (chat_id, topic, category)
                VALUES (?, ?, ?)
            """, (chat_id, topic.lower(), category))


def get_learning_topics(chat_id: str, days: int = 30) -> list[dict]:
    """Get learning topics for a user."""
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM learning_topics
            WHERE chat_id = ? AND last_seen >= ?
            ORDER BY interaction_count DESC
        """, (chat_id, since)).fetchall()
        return [dict(row) for row in rows]


def get_top_learning_topics(chat_id: str, limit: int = 10) -> list[dict]:
    """Get top learning topics by interaction count."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT topic, category, interaction_count, 
                   first_seen, last_seen, mastery_level
            FROM learning_topics
            WHERE chat_id = ?
            ORDER BY interaction_count DESC
            LIMIT ?
        """, (chat_id, limit)).fetchall()
        return [dict(row) for row in rows]


def update_mastery_level(chat_id: str, topic: str, level: int):
    """Update mastery level for a topic."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE learning_topics SET mastery_level = ?
            WHERE chat_id = ? AND topic = ?
        """, (level, chat_id, topic.lower()))


# ============ Smart Notifications ============

def add_smart_notification(chat_id: str, notification_type: str, message: str, repo_name: str = None):
    """Add a smart notification."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO smart_notifications (chat_id, notification_type, repo_name, message)
            VALUES (?, ?, ?, ?)
        """, (chat_id, notification_type, repo_name, message))


def get_unread_notifications(chat_id: str) -> list[dict]:
    """Get unread notifications for a user."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM smart_notifications
            WHERE chat_id = ? AND is_read = FALSE
            ORDER BY created_at DESC
        """, (chat_id,)).fetchall()
        return [dict(row) for row in rows]


def mark_notifications_read(chat_id: str):
    """Mark all notifications as read."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE smart_notifications SET is_read = TRUE WHERE chat_id = ?",
            (chat_id,)
        )


# ============ Weekly Reports ============

def save_weekly_report(chat_id: str, week_start: date, week_end: date, report_data: dict):
    """Save a weekly report."""
    import json
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO weekly_reports (chat_id, week_start, week_end, report_data)
            VALUES (?, ?, ?, ?)
        """, (chat_id, week_start.isoformat(), week_end.isoformat(), json.dumps(report_data)))


def get_weekly_reports(chat_id: str = None, limit: int = 4) -> list[dict]:
    """Get recent weekly reports."""
    import json
    with get_connection() as conn:
        if chat_id:
            rows = conn.execute("""
                SELECT * FROM weekly_reports WHERE chat_id = ?
                ORDER BY week_start DESC LIMIT ?
            """, (chat_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM weekly_reports
                ORDER BY week_start DESC LIMIT ?
            """, (limit,)).fetchall()
        
        reports = []
        for row in rows:
            report = dict(row)
            report['report_data'] = json.loads(report['report_data']) if report['report_data'] else {}
            reports.append(report)
        return reports


# ============ Suggestions ============

def add_suggestion(chat_id: str, suggestion_type: str, content: str):
    """Add a proactive suggestion."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO suggestions (chat_id, suggestion_type, content)
            VALUES (?, ?, ?)
        """, (chat_id, suggestion_type, content))


def get_pending_suggestions(chat_id: str, limit: int = 3) -> list[dict]:
    """Get pending suggestions for a user."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM suggestions
            WHERE chat_id = ? AND is_shown = FALSE
            ORDER BY created_at DESC LIMIT ?
        """, (chat_id, limit)).fetchall()
        return [dict(row) for row in rows]


def mark_suggestion_shown(suggestion_id: int, accepted: bool = None):
    """Mark a suggestion as shown."""
    with get_connection() as conn:
        if accepted is not None:
            conn.execute(
                "UPDATE suggestions SET is_shown = TRUE, is_accepted = ? WHERE id = ?",
                (accepted, suggestion_id)
            )
        else:
            conn.execute(
                "UPDATE suggestions SET is_shown = TRUE WHERE id = ?",
                (suggestion_id,)
            )


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
