"""
Personalized Feed - Kişiselleştirilmiş İçerik Filtresi

Özellikler:
    - Kullanıcı ilgi alanlarına göre içerik filtreleme
    - Dil tercihine göre repo önerileri
    - İlgi puanı hesaplama
    - Tercih öğrenme (kullanıcı etkileşimlerinden)
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass

from agents import db


@dataclass
class FeedItem:
    """Feed öğesi."""
    source: str  # github, hn, reddit
    item_type: str  # repo, story, post
    title: str
    url: str
    score: int
    relevance_score: float
    matched_interests: list
    metadata: dict


def get_personalized_feed(chat_id: str, limit: int = 20) -> list[dict]:
    """
    Kullanıcıya özel feed oluştur.
    
    Args:
        chat_id: Kullanıcı chat ID
        limit: Maksimum öğe sayısı
    
    Returns:
        Sıralanmış feed öğeleri
    """
    prefs = db.get_user_preferences(chat_id)
    
    if not prefs:
        # Varsayılan tercihlerle devam et
        prefs = {
            "interests": [],
            "languages": [],
            "min_stars": 100
        }
    
    feed_items = []
    
    # GitHub repo'larını al
    repos = get_recent_repos()
    for repo in repos:
        score, matched = calculate_relevance(repo, prefs, "repo")
        if score > 0 or not prefs["interests"]:  # İlgi alanı yoksa hepsini göster
            feed_items.append({
                "source": "github",
                "type": "repo",
                "title": repo["full_name"],
                "description": repo.get("description", ""),
                "url": repo["url"],
                "stars": repo.get("stars", 0),
                "language": repo.get("language", ""),
                "relevance": score,
                "matched": matched
            })
    
    # HN stories
    stories = get_recent_hn_stories()
    for story in stories:
        score, matched = calculate_relevance(story, prefs, "hn")
        if score > 0 or not prefs["interests"]:
            feed_items.append({
                "source": "hn",
                "type": "story",
                "title": story["title"],
                "description": story.get("article_summary", ""),
                "url": story.get("url", story.get("hn_link", "")),
                "score": story.get("score", 0),
                "comments": story.get("comment_count", 0),
                "relevance": score,
                "matched": matched
            })
    
    # Reddit posts
    posts = get_recent_reddit_posts()
    for post in posts:
        score, matched = calculate_relevance(post, prefs, "reddit")
        if score > 0 or not prefs["interests"]:
            feed_items.append({
                "source": "reddit",
                "type": "post",
                "title": post["title"],
                "description": post.get("selftext", "")[:200],
                "url": post.get("url", ""),
                "subreddit": post.get("subreddit", ""),
                "score": post.get("score", 0),
                "relevance": score,
                "matched": matched
            })
    
    # Relevance'a göre sırala
    feed_items.sort(key=lambda x: (x["relevance"], x.get("stars", x.get("score", 0))), reverse=True)
    
    return feed_items[:limit]


def calculate_relevance(item: dict, prefs: dict, item_type: str) -> tuple[float, list]:
    """
    Öğenin kullanıcı tercihlerine uygunluk puanını hesapla.
    
    Returns:
        (relevance_score, matched_interests)
    """
    score = 0.0
    matched = []
    interests = [i.lower() for i in prefs.get("interests", [])]
    languages = [l.lower() for l in prefs.get("languages", [])]
    
    if not interests and not languages:
        return 0.5, []  # Tercih yoksa orta puan
    
    # İçerik metinleri
    if item_type == "repo":
        text = f"{item.get('full_name', '')} {item.get('description', '')}".lower()
        item_lang = (item.get("language") or "").lower()
        
        # Dil eşleşmesi (yüksek ağırlık)
        if languages and item_lang in languages:
            score += 3.0
            matched.append(f"lang:{item_lang}")
        
        # Star bonusu
        stars = item.get("stars", 0)
        if stars >= 10000:
            score += 1.0
        elif stars >= 1000:
            score += 0.5
            
    elif item_type == "hn":
        text = f"{item.get('title', '')} {item.get('article_summary', '')}".lower()
        
        # HN score bonusu
        hn_score = item.get("score", 0)
        if hn_score >= 500:
            score += 1.0
        elif hn_score >= 100:
            score += 0.5
            
    elif item_type == "reddit":
        text = f"{item.get('title', '')} {item.get('selftext', '')}".lower()
        subreddit = item.get("subreddit", "").lower()
        
        # Subreddit ile ilgi alanı eşleşmesi
        subreddit_interests = {
            "python": ["python"],
            "golang": ["go", "golang"],
            "rust": ["rust"],
            "machinelearning": ["ai", "ml", "machine learning"],
            "localllama": ["llm", "ai", "local"],
            "webdev": ["web", "frontend", "backend"]
        }
        
        for sub, related in subreddit_interests.items():
            if subreddit == sub:
                for r in related:
                    if r in interests:
                        score += 2.0
                        matched.append(f"r/{sub}")
                        break
    else:
        text = ""
    
    # İlgi alanı eşleşmesi
    for interest in interests:
        if interest in text:
            score += 1.5
            matched.append(interest)
    
    return round(score, 2), list(set(matched))


def get_recent_repos(days: int = 7) -> list[dict]:
    """Son N gündeki repo'ları al."""
    with db.get_connection() as conn:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute("""
            SELECT r.*, rs.stars
            FROM repositories r
            LEFT JOIN repo_snapshots rs ON r.id = rs.repo_id
            WHERE r.first_seen_at >= ?
            ORDER BY rs.stars DESC
            LIMIT 100
        """, (since,)).fetchall()
        return [dict(row) for row in rows]


def get_recent_hn_stories(days: int = 7) -> list[dict]:
    """Son N gündeki HN story'lerini al."""
    with db.get_connection() as conn:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute("""
            SELECT * FROM hn_stories
            WHERE fetched_at >= ?
            ORDER BY score DESC
            LIMIT 50
        """, (since,)).fetchall()
        return [dict(row) for row in rows]


def get_recent_reddit_posts(days: int = 7) -> list[dict]:
    """Son N gündeki Reddit postlarını al."""
    with db.get_connection() as conn:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute("""
            SELECT * FROM reddit_posts
            WHERE fetched_at >= ?
            ORDER BY score DESC
            LIMIT 50
        """, (since,)).fetchall()
        return [dict(row) for row in rows]


def learn_from_interaction(chat_id: str, item_type: str, item_data: dict, action: str):
    """
    Kullanıcı etkileşiminden tercih öğren.
    
    Args:
        chat_id: Kullanıcı ID
        item_type: repo/story/post
        item_data: Öğe verisi
        action: view/bookmark/ask
    """
    # Dil öğren
    if item_type == "repo" and item_data.get("language"):
        lang = item_data["language"]
        prefs = db.get_user_preferences(chat_id)
        if prefs:
            languages = prefs.get("languages", [])
            if lang not in languages:
                # İlk birkaç etkileşimden sonra ekle
                interaction_count = count_language_interactions(chat_id, lang)
                if interaction_count >= 3:
                    languages.append(lang)
                    db.save_user_preferences(chat_id, languages=languages)
    
    # Konu öğren
    keywords = extract_keywords(item_data)
    for keyword in keywords:
        db.track_learning_topic(chat_id, keyword, category="interest")


def extract_keywords(item_data: dict) -> list[str]:
    """Öğeden anahtar kelimeler çıkar."""
    text = f"{item_data.get('title', '')} {item_data.get('description', '')} {item_data.get('full_name', '')}"
    text = text.lower()
    
    # Bilinen teknoloji kelimeleri
    tech_keywords = [
        "python", "rust", "go", "golang", "javascript", "typescript",
        "react", "vue", "svelte", "nextjs", "fastapi", "django", "flask",
        "ai", "ml", "llm", "gpt", "claude", "transformer", "neural",
        "kubernetes", "docker", "devops", "cloud", "aws", "azure",
        "database", "postgres", "redis", "mongodb",
        "security", "crypto", "blockchain", "web3"
    ]
    
    found = []
    for kw in tech_keywords:
        if kw in text:
            found.append(kw)
    
    return found[:5]  # En fazla 5 keyword


def count_language_interactions(chat_id: str, language: str) -> int:
    """Bir dil için etkileşim sayısını al."""
    topics = db.get_learning_topics(chat_id)
    for topic in topics:
        if topic["topic"] == language.lower():
            return topic["interaction_count"]
    return 0


def format_feed_item(item: dict) -> str:
    """Feed öğesini metin formatına çevir."""
    source_emoji = {
        "github": "📦",
        "hn": "🟠",
        "reddit": "🔴"
    }
    
    emoji = source_emoji.get(item["source"], "📌")
    
    if item["source"] == "github":
        stars = item.get("stars", 0)
        lang = item.get("language", "")
        return f"""{emoji} {item['title']}
   ⭐ {stars:,} | 💻 {lang}
   {item['description'][:80]}..."""
    
    elif item["source"] == "hn":
        score = item.get("score", 0)
        comments = item.get("comments", 0)
        return f"""{emoji} {item['title']}
   📊 {score} puan | 💬 {comments} yorum"""
    
    elif item["source"] == "reddit":
        subreddit = item.get("subreddit", "")
        score = item.get("score", 0)
        return f"""{emoji} r/{subreddit}: {item['title']}
   📊 {score} puan"""
    
    return f"{emoji} {item['title']}"


def get_feed_summary(chat_id: str) -> str:
    """Kişiselleştirilmiş feed özeti oluştur."""
    feed = get_personalized_feed(chat_id, limit=10)
    
    if not feed:
        return "Henüz yeterli veri yok. /interests ile ilgi alanlarınızı ekleyin."
    
    lines = ["📰 KİŞİSEL FEED", "━" * 25, ""]
    
    # Kaynaklara göre grupla
    github_items = [f for f in feed if f["source"] == "github"][:3]
    hn_items = [f for f in feed if f["source"] == "hn"][:3]
    reddit_items = [f for f in feed if f["source"] == "reddit"][:3]
    
    if github_items:
        lines.append("📦 GitHub Trending")
        for item in github_items:
            lines.append(format_feed_item(item))
        lines.append("")
    
    if hn_items:
        lines.append("🟠 Hacker News")
        for item in hn_items:
            lines.append(format_feed_item(item))
        lines.append("")
    
    if reddit_items:
        lines.append("🔴 Reddit")
        for item in reddit_items:
            lines.append(format_feed_item(item))
    
    # Eşleşen ilgi alanları
    all_matched = set()
    for item in feed:
        all_matched.update(item.get("matched", []))
    
    if all_matched:
        lines.append("")
        lines.append(f"🎯 Eşleşen: {', '.join(list(all_matched)[:5])}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    test_chat_id = "test_user"
    
    # Tercih ekle
    db.init_db()
    db.save_user_preferences(
        test_chat_id,
        interests=["rust", "ai", "llm"],
        languages=["Rust", "Python"]
    )
    
    # Feed al
    print(get_feed_summary(test_chat_id))
