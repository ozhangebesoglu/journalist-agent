"""
Reddit Fetcher
Tech subredditlerinden top postları ve GitHub ile eşleşen postları çeker
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import praw
from dotenv import load_dotenv

load_dotenv()

# Takip edilecek subredditler
SUBREDDITS = [
    "programming",
    "machinelearning",
    "Python",
    "golang",
    "rust",
    "webdev",
    "LocalLLaMA"
]


def get_reddit_client() -> praw.Reddit | None:
    """Initialize PRAW client with env credentials."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "gazeteci:v1.0 (by /u/gazeteci_bot)")

    if not client_id or not client_secret:
        print("⚠️ [REDDIT] REDDIT_CLIENT_ID veya REDDIT_CLIENT_SECRET bulunamadı.")
        print("   Reddit entegrasyonu atlanıyor...")
        return None

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        # Test connection
        reddit.user.me()
        return reddit
    except Exception as e:
        print(f"⚠️ [REDDIT] Bağlantı hatası: {e}")
        return None


def extract_github_urls(text: str) -> list[str]:
    """Extract GitHub repo URLs from text."""
    if not text:
        return []
    pattern = r'github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    # Clean up matches (remove .git, trailing slashes, etc.)
    cleaned = []
    for match in matches:
        repo = re.sub(r'\.(git|md|html?)$', '', match)
        repo = repo.rstrip('/')
        if '/' in repo:
            cleaned.append(repo.lower())
    return list(set(cleaned))


def fetch_post_comments(submission, limit: int = 5) -> list[dict]:
    """Fetch top comments from a submission."""
    comments = []
    try:
        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)

        for comment in submission.comments[:limit]:
            if hasattr(comment, 'body') and comment.body and comment.body != '[deleted]':
                text = comment.body
                if len(text) > 500:
                    text = text[:500] + "..."
                comments.append({
                    "id": comment.id,
                    "author": str(comment.author) if comment.author else "[deleted]",
                    "text": text,
                    "score": comment.score
                })
    except Exception:
        pass
    return comments


def fetch_subreddit_posts(reddit: praw.Reddit, subreddit_name: str, limit: int = 10) -> list[dict]:
    """Fetch top posts from a single subreddit."""
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)

        for submission in subreddit.hot(limit=limit):
            # Skip stickied posts
            if submission.stickied:
                continue

            selftext = ""
            if submission.is_self and submission.selftext:
                selftext = submission.selftext[:1500] if len(submission.selftext) > 1500 else submission.selftext

            posts.append({
                "id": submission.id,
                "subreddit": subreddit_name,
                "title": submission.title,
                "url": submission.url if not submission.is_self else None,
                "selftext": selftext,
                "score": submission.score,
                "upvote_ratio": submission.upvote_ratio,
                "comments": submission.num_comments,
                "author": str(submission.author) if submission.author else "[deleted]",
                "permalink": f"https://reddit.com{submission.permalink}",
                "is_self": submission.is_self,
                "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat()
            })
    except Exception as e:
        print(f"   ⚠️ r/{subreddit_name} çekilemedi: {e}")

    return posts


def fetch_reddit_data(github_repos: list[dict] = None) -> dict:
    """
    Ana fonksiyon: Reddit verilerini toplar

    Returns:
        {
            "top_posts": [...],           # En iyi postlar (tüm subredditlerden)
            "github_mentions": [...],     # GitHub repoları ile eşleşenler
            "by_subreddit": {             # Subreddit bazlı postlar
                "programming": [...],
                "machinelearning": [...],
                ...
            }
        }
    """
    result = {
        "top_posts": [],
        "github_mentions": [],
        "by_subreddit": {}
    }

    reddit = get_reddit_client()
    if not reddit:
        return result

    # GitHub repo URL'leri ve isimleri (eşleştirme için)
    github_urls = set()
    github_names = set()
    if github_repos:
        for repo in github_repos:
            url = repo.get("url", "").lower()
            name = repo.get("name", "").lower()
            if url:
                github_urls.add(url)
            if name:
                github_names.add(name)
                # Sadece repo adını da ekle (owner olmadan)
                github_names.add(name.split("/")[-1])

    print(f"📱 [REDDIT] {len(SUBREDDITS)} subreddit taranıyor...")

    all_posts = []

    # Paralel olarak subredditleri tara
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_subreddit_posts, reddit, sub, 15): sub
            for sub in SUBREDDITS
        }

        for future in as_completed(futures):
            subreddit = futures[future]
            try:
                posts = future.result()
                result["by_subreddit"][subreddit] = posts
                all_posts.extend(posts)
                print(f"   📋 r/{subreddit}: {len(posts)} post")
            except Exception as e:
                print(f"   ⚠️ r/{subreddit} hatası: {e}")
                result["by_subreddit"][subreddit] = []

    # Deduplicate ve skora göre sırala
    seen_ids = set()
    unique_posts = []
    for post in all_posts:
        if post["id"] not in seen_ids:
            seen_ids.add(post["id"])
            unique_posts.append(post)

    unique_posts.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Top 15 post
    top_posts = unique_posts[:15]

    # İlk 10 post için yorumları çek
    posts_with_comments = 0
    for post in top_posts:
        if posts_with_comments < 10:
            try:
                submission = reddit.submission(id=post["id"])
                post["top_comments"] = fetch_post_comments(submission, limit=3)
                posts_with_comments += 1
            except Exception:
                post["top_comments"] = []
        else:
            post["top_comments"] = []

    result["top_posts"] = top_posts

    # GitHub eşleşmelerini bul
    for post in unique_posts:
        is_github_match = False

        # URL kontrolü
        url = post.get("url", "") or ""
        if "github.com" in url.lower():
            # Direkt GitHub linki
            extracted = extract_github_urls(url)
            for repo in extracted:
                if repo in github_names or any(repo in gh_url for gh_url in github_urls):
                    is_github_match = True
                    break

        # Selftext kontrolü
        if not is_github_match and post.get("selftext"):
            extracted = extract_github_urls(post["selftext"])
            for repo in extracted:
                if repo in github_names:
                    is_github_match = True
                    break

        # Title kontrolü
        if not is_github_match:
            title_lower = post.get("title", "").lower()
            for name in github_names:
                if name in title_lower:
                    is_github_match = True
                    break

        if is_github_match:
            # Yorumları da çek
            if "top_comments" not in post:
                try:
                    submission = reddit.submission(id=post["id"])
                    post["top_comments"] = fetch_post_comments(submission, limit=3)
                except Exception:
                    post["top_comments"] = []
            result["github_mentions"].append(post)

    print(f"📊 [REDDIT] {len(result['top_posts'])} top post, {len(result['github_mentions'])} GitHub eşleşmesi")

    return result


if __name__ == "__main__":
    # Test
    data = fetch_reddit_data()
    print("\n=== TOP POSTS ===")
    for post in data["top_posts"][:5]:
        print(f"  [{post['score']}] r/{post['subreddit']}: {post['title'][:60]}...")

    print("\n=== BY SUBREDDIT ===")
    for sub, posts in data["by_subreddit"].items():
        print(f"  r/{sub}: {len(posts)} posts")
