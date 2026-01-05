"""
Learning Tracker - Öğrenme Takip Sistemi

Özellikler:
    - Haftalık öğrenme özeti
    - Spaced repetition hatırlatıcılar
    - Konu mastery takibi
    - Öğrenme istatistikleri
"""

import json
from datetime import datetime, timedelta, date
from collections import defaultdict
from dataclasses import dataclass

from agents import db


@dataclass
class LearningStats:
    """Öğrenme istatistikleri."""
    total_topics: int
    topics_this_week: int
    top_categories: list
    mastery_distribution: dict
    streak_days: int
    total_interactions: int


def track_interaction(chat_id: str, content: str, interaction_type: str = "query"):
    """
    Kullanıcı etkileşiminden öğrenme verisi çıkar ve kaydet.
    
    Args:
        chat_id: Kullanıcı ID
        content: Etkileşim içeriği (soru, komut vs.)
        interaction_type: query, bookmark, watch, code
    """
    # Anahtar kelimeleri çıkar
    topics = extract_learning_topics(content)
    
    for topic, category in topics:
        db.track_learning_topic(chat_id, topic, category)


def extract_learning_topics(text: str) -> list[tuple[str, str]]:
    """
    Metinden öğrenme konularını çıkar.
    
    Returns:
        [(topic, category), ...]
    """
    text = text.lower()
    topics = []
    
    # Programlama dilleri
    languages = {
        "python": "language", "rust": "language", "go": "language",
        "golang": "language", "javascript": "language", "typescript": "language",
        "java": "language", "kotlin": "language", "swift": "language",
        "c++": "language", "cpp": "language", "c#": "language",
        "ruby": "language", "php": "language", "scala": "language",
        "elixir": "language", "haskell": "language", "zig": "language"
    }
    
    # Framework'ler
    frameworks = {
        "react": "framework", "vue": "framework", "svelte": "framework",
        "angular": "framework", "nextjs": "framework", "nuxt": "framework",
        "django": "framework", "flask": "framework", "fastapi": "framework",
        "express": "framework", "nest": "framework", "spring": "framework",
        "rails": "framework", "laravel": "framework"
    }
    
    # Teknolojiler
    technologies = {
        "docker": "technology", "kubernetes": "technology", "k8s": "technology",
        "terraform": "technology", "ansible": "technology", "jenkins": "technology",
        "github actions": "technology", "ci/cd": "technology",
        "postgres": "technology", "postgresql": "technology", "mysql": "technology",
        "mongodb": "technology", "redis": "technology", "elasticsearch": "technology",
        "kafka": "technology", "rabbitmq": "technology",
        "aws": "technology", "azure": "technology", "gcp": "technology"
    }
    
    # AI/ML konuları
    ai_topics = {
        "ai": "ai", "ml": "ai", "machine learning": "ai",
        "deep learning": "ai", "neural network": "ai",
        "llm": "ai", "gpt": "ai", "claude": "ai", "gemini": "ai",
        "transformer": "ai", "attention": "ai",
        "fine-tuning": "ai", "rag": "ai", "langchain": "ai",
        "agents": "ai", "embeddings": "ai", "vector": "ai",
        "huggingface": "ai", "pytorch": "ai", "tensorflow": "ai"
    }
    
    # Kavramlar
    concepts = {
        "api": "concept", "rest": "concept", "graphql": "concept",
        "microservices": "concept", "monolith": "concept",
        "async": "concept", "concurrency": "concept", "parallelism": "concept",
        "testing": "concept", "tdd": "concept", "bdd": "concept",
        "solid": "concept", "design patterns": "concept",
        "algorithm": "concept", "data structure": "concept",
        "security": "concept", "authentication": "concept", "oauth": "concept"
    }
    
    # Tüm kategorileri kontrol et
    all_keywords = {**languages, **frameworks, **technologies, **ai_topics, **concepts}
    
    for keyword, category in all_keywords.items():
        if keyword in text:
            # Normalize et (golang -> go gibi)
            normalized = keyword
            if keyword == "golang":
                normalized = "go"
            elif keyword == "k8s":
                normalized = "kubernetes"
            elif keyword in ["cpp", "c++"]:
                normalized = "cpp"
            
            topics.append((normalized, category))
    
    return list(set(topics))


def get_learning_summary(chat_id: str, days: int = 7) -> str:
    """
    Haftalık öğrenme özeti oluştur.
    """
    topics = db.get_learning_topics(chat_id, days=days)
    
    if not topics:
        return "📚 Bu hafta henüz öğrenme aktivitesi yok.\n\nSorular sor, repo'lar incele, öğrenmeye başla!"
    
    # Kategorilere göre grupla
    by_category = defaultdict(list)
    total_interactions = 0
    
    for topic in topics:
        by_category[topic["category"] or "other"].append(topic)
        total_interactions += topic["interaction_count"]
    
    lines = [
        "📚 HAFTALIK ÖĞRENME ÖZETİ",
        "━" * 30,
        f"\n📊 Toplam: {len(topics)} konu, {total_interactions} etkileşim\n"
    ]
    
    category_names = {
        "language": "💻 Programlama Dilleri",
        "framework": "🛠️ Framework'ler",
        "technology": "⚙️ Teknolojiler",
        "ai": "🤖 AI/ML",
        "concept": "📖 Kavramlar",
        "other": "📌 Diğer"
    }
    
    for category, category_topics in by_category.items():
        category_topics.sort(key=lambda x: x["interaction_count"], reverse=True)
        
        lines.append(f"{category_names.get(category, category)}")
        for topic in category_topics[:5]:
            mastery = "⬜" * (5 - topic["mastery_level"]) + "🟩" * topic["mastery_level"]
            lines.append(f"  • {topic['topic'].title()} ({topic['interaction_count']}x) {mastery}")
        lines.append("")
    
    # İlerleme önerisi
    low_mastery = [t for t in topics if t["mastery_level"] < 2 and t["interaction_count"] >= 3]
    if low_mastery:
        suggestion = low_mastery[0]
        lines.append(f"💡 Öneri: {suggestion['topic'].title()} konusunda biraz daha derinleş!")
    
    return "\n".join(lines)


def create_spaced_repetition_reminders(chat_id: str) -> list[dict]:
    """
    Spaced repetition için hatırlatıcılar oluştur.
    
    Kurallar:
        - İlk tekrar: 1 gün sonra
        - İkinci tekrar: 3 gün sonra
        - Üçüncü tekrar: 7 gün sonra
        - Dördüncü tekrar: 14 gün sonra
    """
    topics = db.get_learning_topics(chat_id, days=30)
    reminders = []
    
    # Spaced repetition aralıkları (gün)
    intervals = {
        0: 1,   # Yeni konu -> 1 gün sonra
        1: 3,   # 1. tekrar yapıldı -> 3 gün sonra
        2: 7,   # 2. tekrar yapıldı -> 7 gün sonra
        3: 14,  # 3. tekrar yapıldı -> 14 gün sonra
        4: 30,  # 4. tekrar yapıldı -> 30 gün sonra
    }
    
    for topic in topics:
        # Sadece aktif öğrenilen konular
        if topic["interaction_count"] < 3:
            continue
        
        mastery = topic["mastery_level"]
        if mastery >= 5:
            continue  # Tam ustalaşmış
        
        # Son görülmeden bu yana geçen süre
        last_seen = datetime.fromisoformat(topic["last_seen"])
        days_since = (datetime.now() - last_seen).days
        
        # Tekrar zamanı geldiyse
        interval = intervals.get(mastery, 30)
        if days_since >= interval:
            remind_at = datetime.now() + timedelta(hours=1)  # 1 saat sonra hatırlat
            
            message = f"📚 Tekrar zamanı: {topic['topic'].title()}\n\n"
            message += f"Bu konuyu {days_since} gündür görmedin. Biraz pratik yap!\n"
            message += f"/ask {topic['topic']} hakkında bir soru"
            
            reminders.append({
                "chat_id": chat_id,
                "topic": topic["topic"],
                "message": message,
                "remind_at": remind_at,
                "mastery": mastery
            })
            
            # Hatırlatıcı oluştur
            db.add_reminder(chat_id, message, remind_at)
    
    return reminders


def update_topic_mastery(chat_id: str, topic: str, correct: bool = True):
    """
    Konu mastery seviyesini güncelle.
    
    Args:
        chat_id: Kullanıcı ID
        topic: Konu adı
        correct: Doğru cevap/başarılı pratik mi?
    """
    topics = db.get_learning_topics(chat_id, days=365)
    
    for t in topics:
        if t["topic"] == topic.lower():
            new_level = t["mastery_level"]
            if correct:
                new_level = min(5, new_level + 1)
            else:
                new_level = max(0, new_level - 1)
            
            db.update_mastery_level(chat_id, topic, new_level)
            return new_level
    
    return 0


def get_learning_stats(chat_id: str) -> LearningStats:
    """
    Kullanıcının öğrenme istatistiklerini al.
    """
    all_topics = db.get_learning_topics(chat_id, days=365)
    week_topics = db.get_learning_topics(chat_id, days=7)
    
    # Kategori dağılımı
    category_counts = defaultdict(int)
    mastery_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_interactions = 0
    
    for topic in all_topics:
        category_counts[topic["category"] or "other"] += 1
        mastery_counts[topic["mastery_level"]] = mastery_counts.get(topic["mastery_level"], 0) + 1
        total_interactions += topic["interaction_count"]
    
    # Streak hesapla (art arda kaç gün aktif)
    # Bu basit bir yaklaşım - gerçek streak için daha detaylı veri gerekir
    streak = min(7, len(week_topics))  # Basitleştirilmiş
    
    return LearningStats(
        total_topics=len(all_topics),
        topics_this_week=len(week_topics),
        top_categories=sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3],
        mastery_distribution=mastery_counts,
        streak_days=streak,
        total_interactions=total_interactions
    )


def format_learning_stats(stats: LearningStats) -> str:
    """
    Öğrenme istatistiklerini formatla.
    """
    lines = [
        "📊 ÖĞRENME İSTATİSTİKLERİ",
        "━" * 30,
        "",
        f"📚 Toplam Konu: {stats.total_topics}",
        f"📅 Bu Hafta: {stats.topics_this_week} konu",
        f"🔥 Streak: {stats.streak_days} gün",
        f"💫 Toplam Etkileşim: {stats.total_interactions}",
        "",
        "📈 Mastery Dağılımı:"
    ]
    
    mastery_labels = ["Yeni", "Başlangıç", "Orta", "İyi", "İleri", "Usta"]
    for level, count in stats.mastery_distribution.items():
        if count > 0:
            bar = "█" * count + "░" * (10 - count)
            lines.append(f"  {mastery_labels[level]}: {bar} {count}")
    
    if stats.top_categories:
        lines.append("")
        lines.append("🏆 En Aktif Kategoriler:")
        for category, count in stats.top_categories:
            lines.append(f"  • {category.title()}: {count} konu")
    
    return "\n".join(lines)


def get_mastery_emoji(level: int) -> str:
    """Mastery seviyesi için emoji döndür."""
    emojis = ["⬜", "🟨", "🟧", "🟩", "🟦", "⭐"]
    return emojis[min(level, 5)]


def generate_quiz_question(chat_id: str) -> dict | None:
    """
    Öğrenilen konulardan quiz sorusu oluştur.
    """
    topics = db.get_learning_topics(chat_id, days=30)
    
    if not topics:
        return None
    
    # Orta mastery seviyesindeki konuları tercih et
    candidates = [t for t in topics if 1 <= t["mastery_level"] <= 3]
    if not candidates:
        candidates = topics
    
    import random
    topic = random.choice(candidates)
    
    # Basit soru şablonları
    templates = [
        f"{topic['topic'].title()} nedir ve ne için kullanılır?",
        f"{topic['topic'].title()}'ın temel özellikleri nelerdir?",
        f"{topic['topic'].title()} ile ilgili bir örnek verir misin?",
        f"{topic['topic'].title()}'ın avantajları ve dezavantajları nelerdir?"
    ]
    
    return {
        "topic": topic["topic"],
        "question": random.choice(templates),
        "mastery": topic["mastery_level"],
        "category": topic["category"]
    }


if __name__ == "__main__":
    # Test
    db.init_db()
    test_chat_id = "test_user"
    
    # Etkileşim simüle et
    test_texts = [
        "Python ile FastAPI kullanarak REST API nasıl yazılır?",
        "Rust ownership sistemi nedir?",
        "Docker container'ları kubernetes ile nasıl yönetilir?",
        "LLM fine-tuning için en iyi yaklaşımlar",
        "React hooks nasıl çalışır?"
    ]
    
    for text in test_texts:
        track_interaction(test_chat_id, text, "query")
    
    # Özet al
    print(get_learning_summary(test_chat_id))
    
    # İstatistikler
    stats = get_learning_stats(test_chat_id)
    print("\n" + format_learning_stats(stats))
    
    # Quiz
    quiz = generate_quiz_question(test_chat_id)
    if quiz:
        print(f"\n🧠 Quiz: {quiz['question']}")
