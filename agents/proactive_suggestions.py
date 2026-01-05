"""
Proactive Suggestions - Proaktif Öneri Sistemi

Özellikler:
    - Kullanıcı davranışına göre repo önerileri
    - "Bu hafta çok X baktın, Y'ye de bak" tarzı öneriler
    - Benzer repo keşfi
    - Öğrenme yolu önerileri
"""

import json
import random
from datetime import datetime, timedelta
from collections import defaultdict

from agents import db


def generate_proactive_suggestions(chat_id: str) -> list[dict]:
    """
    Kullanıcı için proaktif öneriler oluştur.
    
    Returns:
        Öneri listesi
    """
    suggestions = []
    
    # 1. Dil bazlı öneriler
    lang_suggestion = suggest_based_on_languages(chat_id)
    if lang_suggestion:
        suggestions.append(lang_suggestion)
    
    # 2. İlgi alanı önerileri
    interest_suggestion = suggest_based_on_interests(chat_id)
    if interest_suggestion:
        suggestions.append(interest_suggestion)
    
    # 3. Öğrenme yolu önerileri
    learning_suggestion = suggest_learning_path(chat_id)
    if learning_suggestion:
        suggestions.append(learning_suggestion)
    
    # 4. Keşif önerileri
    discovery_suggestion = suggest_discovery(chat_id)
    if discovery_suggestion:
        suggestions.append(discovery_suggestion)
    
    # DB'ye kaydet
    for suggestion in suggestions:
        db.add_suggestion(chat_id, suggestion["type"], json.dumps(suggestion))
    
    return suggestions


def suggest_based_on_languages(chat_id: str) -> dict | None:
    """
    Kullanıcının baktığı dillere göre öneri oluştur.
    """
    topics = db.get_learning_topics(chat_id, days=14)
    
    # Dil topic'lerini bul
    lang_counts = defaultdict(int)
    known_langs = ["python", "rust", "go", "javascript", "typescript", "java", "kotlin", "swift", "c++", "c#"]
    
    for topic in topics:
        if topic["topic"] in known_langs:
            lang_counts[topic["topic"]] += topic["interaction_count"]
    
    if not lang_counts:
        return None
    
    # En çok bakılan dil
    top_lang = max(lang_counts.items(), key=lambda x: x[1])
    
    # İlişkili diller
    related_langs = {
        "python": ["rust", "go"],
        "javascript": ["typescript", "rust"],
        "typescript": ["rust", "go"],
        "rust": ["go", "zig"],
        "go": ["rust", "python"],
        "java": ["kotlin", "scala"],
        "kotlin": ["swift", "java"],
        "swift": ["kotlin", "rust"],
        "c++": ["rust", "zig"],
        "c#": ["f#", "typescript"]
    }
    
    suggestions = related_langs.get(top_lang[0], [])
    if suggestions:
        suggested_lang = random.choice(suggestions)
        return {
            "type": "language",
            "title": f"🔄 Dil Önerisi",
            "message": f"Bu hafta çok **{top_lang[0].title()}** projelerine baktın! "
                      f"**{suggested_lang.title()}** da ilgini çekebilir - benzer kullanım alanları var.",
            "action": f"/discover {suggested_lang}",
            "reason": f"{top_lang[1]} etkileşim {top_lang[0]} ile"
        }
    
    return None


def suggest_based_on_interests(chat_id: str) -> dict | None:
    """
    İlgi alanlarına göre trending repo önerisi.
    """
    prefs = db.get_user_preferences(chat_id)
    if not prefs or not prefs.get("interests"):
        return None
    
    interests = prefs["interests"]
    
    # Trending repo'lardan eşleşenleri bul
    from agents import personalized_feed
    feed = personalized_feed.get_personalized_feed(chat_id, limit=5)
    
    if not feed:
        return None
    
    # En yüksek relevance'lı repo
    top_item = max(feed, key=lambda x: x.get("relevance", 0))
    
    if top_item.get("relevance", 0) > 2:
        matched = ", ".join(top_item.get("matched", [])[:3])
        return {
            "type": "interest",
            "title": "🎯 İlgi Alanı Eşleşmesi",
            "message": f"**{top_item['title']}** projesini gördün mü? "
                      f"İlgi alanlarınla eşleşiyor: {matched}",
            "url": top_item.get("url", ""),
            "action": f"/analyze {top_item['title']}" if top_item["source"] == "github" else None
        }
    
    return None


def suggest_learning_path(chat_id: str) -> dict | None:
    """
    Öğrenme yolu önerisi oluştur.
    """
    topics = db.get_top_learning_topics(chat_id, limit=5)
    
    if not topics:
        return None
    
    # Düşük mastery level'lı topic'ler
    to_improve = [t for t in topics if t["mastery_level"] < 3 and t["interaction_count"] >= 5]
    
    if not to_improve:
        return None
    
    topic = to_improve[0]
    
    # Öğrenme kaynakları
    learning_resources = {
        "python": "Real Python ve Python docs harika kaynaklar",
        "rust": "Rust Book ve Rustlings egzersizleri",
        "go": "Go by Example ve Tour of Go",
        "javascript": "JavaScript.info ve MDN",
        "typescript": "TypeScript Handbook",
        "ai": "FastAI kursu ve Hugging Face docs",
        "llm": "LangChain docs ve OpenAI Cookbook",
        "docker": "Docker docs ve Play with Docker",
        "kubernetes": "Kubernetes.io tutorials"
    }
    
    resource = learning_resources.get(topic["topic"], "ilgili dökümantasyon")
    
    return {
        "type": "learning",
        "title": "📚 Öğrenme Önerisi",
        "message": f"**{topic['topic'].title()}** ile {topic['interaction_count']} kez etkileşime girdin "
                  f"ama henüz başlangıç seviyesindesin. Derinleşmek için: {resource}",
        "topic": topic["topic"],
        "action": f"/ask {topic['topic']} öğrenmek için en iyi kaynaklar neler?"
    }


def suggest_discovery(chat_id: str) -> dict | None:
    """
    Keşif önerisi oluştur - yeni alanlar keşfettir.
    """
    topics = db.get_learning_topics(chat_id, days=30)
    
    if len(topics) < 3:
        # Yeni kullanıcı
        return {
            "type": "discovery",
            "title": "🔮 Keşfet",
            "message": "Henüz çok etkileşimin yok! "
                      "Trending repo'lara göz at ve ilgi alanlarını keşfet.",
            "action": "/trending"
        }
    
    # Mevcut topic'lere dayanarak yeni alan öner
    current_topics = {t["topic"] for t in topics}
    
    # Topic ilişkileri
    related_topics = {
        "python": ["data science", "automation", "web scraping"],
        "ai": ["agents", "rag", "fine-tuning"],
        "llm": ["prompt engineering", "agents", "local models"],
        "web": ["htmx", "edge functions", "jamstack"],
        "rust": ["wasm", "systems programming", "cli tools"],
        "go": ["microservices", "distributed systems", "cli tools"],
        "docker": ["kubernetes", "devops", "gitops"],
        "database": ["vector databases", "time series", "graph db"]
    }
    
    new_suggestions = []
    for topic in current_topics:
        related = related_topics.get(topic, [])
        for r in related:
            if r not in current_topics:
                new_suggestions.append((topic, r))
    
    if new_suggestions:
        base_topic, new_topic = random.choice(new_suggestions)
        return {
            "type": "discovery",
            "title": "🔮 Yeni Alan Keşfi",
            "message": f"**{base_topic.title()}** ile ilgileniyorsun. "
                      f"**{new_topic.title()}** alanına da göz atabilirsin!",
            "action": f"/discover {new_topic}"
        }
    
    return None


def get_daily_suggestion(chat_id: str) -> str | None:
    """
    Günlük öneri mesajı oluştur.
    """
    suggestions = generate_proactive_suggestions(chat_id)
    
    if not suggestions:
        return None
    
    # Rastgele bir öneri seç
    suggestion = random.choice(suggestions)
    
    lines = [
        f"💡 {suggestion['title']}",
        "",
        suggestion["message"]
    ]
    
    if suggestion.get("action"):
        lines.append("")
        lines.append(f"👉 {suggestion['action']}")
    
    return "\n".join(lines)


def get_weekly_insight(chat_id: str) -> str:
    """
    Haftalık özet ve içgörü mesajı.
    """
    topics = db.get_learning_topics(chat_id, days=7)
    prefs = db.get_user_preferences(chat_id)
    
    if not topics:
        return "Bu hafta henüz etkileşim olmadı. /trending ile başla!"
    
    # En aktif topic'ler
    top_topics = sorted(topics, key=lambda x: x["interaction_count"], reverse=True)[:5]
    
    lines = [
        "📊 HAFTALIK ÖZET",
        "━" * 25,
        "",
        "🔥 En çok ilgilendiğin konular:"
    ]
    
    for i, topic in enumerate(top_topics, 1):
        lines.append(f"   {i}. {topic['topic'].title()} ({topic['interaction_count']} etkileşim)")
    
    # Öneri ekle
    suggestion = get_daily_suggestion(chat_id)
    if suggestion:
        lines.append("")
        lines.append("💡 ÖNERİ")
        lines.append(suggestion)
    
    return "\n".join(lines)


def format_suggestion_card(suggestion: dict) -> str:
    """
    Öneriyi kart formatında göster.
    """
    emoji_map = {
        "language": "🔄",
        "interest": "🎯",
        "learning": "📚",
        "discovery": "🔮"
    }
    
    emoji = emoji_map.get(suggestion["type"], "💡")
    
    card = f"""
┌────────────────────────────────┐
│ {emoji} {suggestion['title'][:28]}
├────────────────────────────────┤
│ {suggestion['message'][:60]}...
│
│ 👉 {suggestion.get('action', 'Detay yok')}
└────────────────────────────────┘
"""
    return card


if __name__ == "__main__":
    # Test
    db.init_db()
    test_chat_id = "test_user"
    
    # Birkaç topic ekle
    for topic in ["python", "ai", "llm"]:
        for _ in range(5):
            db.track_learning_topic(test_chat_id, topic, "language")
    
    # Öneriler oluştur
    suggestions = generate_proactive_suggestions(test_chat_id)
    
    print("=== PROACTIVE SUGGESTIONS ===")
    for s in suggestions:
        print(format_suggestion_card(s))
    
    print("\n=== WEEKLY INSIGHT ===")
    print(get_weekly_insight(test_chat_id))
