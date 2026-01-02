"""
Data Persister - Bridge between fetchers and database
Handles saving fetched data to SQLite with proper relationships
"""
import re
from agents import db


def extract_github_repo_from_url(url: str) -> str | None:
    """Extract owner/repo from a GitHub URL."""
    if not url:
        return None
    match = re.search(r'github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)', url)
    if match:
        # Remove trailing .git or other extensions
        repo = match.group(1)
        repo = re.sub(r'\.(git|md|html?)$', '', repo)
        return repo.lower()
    return None


def persist_github_repos(repos: list[dict]) -> dict[str, int]:
    """
    Save GitHub repos to DB, return mapping of full_name -> repo_id.
    Also saves snapshots, topics, files, and README.
    """
    repo_id_map = {}

    for repo in repos:
        # Upsert repository
        repo_id = db.upsert_repository(repo)
        repo_id_map[repo["name"].lower()] = repo_id

        # Save daily snapshot
        db.save_repo_snapshot(
            repo_id,
            stars=repo["stars"],
            forks=repo.get("forks"),
            open_issues=repo.get("open_issues")
        )

        # Save topics
        if repo.get("topics"):
            db.save_repo_topics(repo_id, repo["topics"])

        # Save root files
        if repo.get("files"):
            db.save_repo_files(repo_id, repo["files"])

        # Save README
        if repo.get("readme"):
            db.save_repo_readme(repo_id, repo["readme"])

    print(f"   [DB] {len(repos)} repo veritabanına kaydedildi.")
    return repo_id_map


def persist_hn_data(hn_data: dict, repo_name_to_id: dict[str, int]):
    """Save HN stories/comments and record repo mentions."""
    saved_count = 0
    mention_count = 0

    # Process all story categories
    all_stories = (
        hn_data.get("top_stories", []) +
        hn_data.get("github_mentions", []) +
        hn_data.get("tech_discussions", [])
    )

    # Deduplicate by hn_id
    seen_ids = set()
    unique_stories = []
    for story in all_stories:
        if story.get("id") and story["id"] not in seen_ids:
            seen_ids.add(story["id"])
            unique_stories.append(story)

    for story in unique_stories:
        # Save story
        story_id = db.save_hn_story(story)
        saved_count += 1

        # Save comments
        if story.get("top_comments"):
            db.save_hn_comments(story_id, story["top_comments"])

        # Check for GitHub repo mentions
        url = story.get("url", "").lower()
        repo_name = extract_github_repo_from_url(url)

        if repo_name and repo_name in repo_name_to_id:
            db.save_repo_mention(
                repo_id=repo_name_to_id[repo_name],
                source_type="hn",
                source_id=story_id
            )
            mention_count += 1

    print(f"   [DB] {saved_count} HN story, {mention_count} GitHub eşleşmesi kaydedildi.")


def persist_reddit_data(reddit_data: dict, repo_name_to_id: dict[str, int]):
    """Save Reddit posts/comments and record repo mentions."""
    saved_count = 0
    mention_count = 0

    # Process all post categories
    all_posts = reddit_data.get("top_posts", []) + reddit_data.get("github_mentions", [])

    # Also get posts from by_subreddit
    for subreddit_posts in reddit_data.get("by_subreddit", {}).values():
        all_posts.extend(subreddit_posts)

    # Deduplicate by reddit_id
    seen_ids = set()
    unique_posts = []
    for post in all_posts:
        if post.get("id") and post["id"] not in seen_ids:
            seen_ids.add(post["id"])
            unique_posts.append(post)

    for post in unique_posts:
        # Save post
        post_id = db.save_reddit_post(post)
        saved_count += 1

        # Save comments
        if post.get("top_comments"):
            db.save_reddit_comments(post_id, post["top_comments"])

        # Check for GitHub repo mentions in URL
        url = post.get("url", "").lower()
        repo_name = extract_github_repo_from_url(url)

        if repo_name and repo_name in repo_name_to_id:
            db.save_repo_mention(
                repo_id=repo_name_to_id[repo_name],
                source_type="reddit",
                source_id=post_id
            )
            mention_count += 1

        # Also check selftext for GitHub links
        selftext = post.get("selftext", "").lower()
        for tracked_repo in repo_name_to_id:
            if tracked_repo in selftext or tracked_repo.split("/")[-1] in selftext:
                db.save_repo_mention(
                    repo_id=repo_name_to_id[tracked_repo],
                    source_type="reddit",
                    source_id=post_id
                )
                mention_count += 1
                break  # Only count once per post

    print(f"   [DB] {saved_count} Reddit post, {mention_count} GitHub eşleşmesi kaydedildi.")


def mark_featured_repos(briefing_id: int, repos: list[dict], star_of_day: str = None):
    """Mark which repos were featured in the briefing."""
    for repo in repos:
        repo_record = db.get_repo_by_name(repo["name"])
        if repo_record:
            feature_type = "star_of_day" if repo["name"] == star_of_day else "trending"
            db.mark_repo_featured(briefing_id, repo_record["id"], feature_type)
