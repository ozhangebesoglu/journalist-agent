"""
Discovery & Fun - Keşif ve eğlence özellikleri

Özellikler:
    - discover: Rastgele ilginç repo öner
    - quiz: Tech quiz
    - motivation: Motivasyon sözü
"""

import os
import random
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash"


# ============ Motivasyon Sözleri ============

MOTIVATION_QUOTES = [
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("Simplicity is the soul of efficiency.", "Austin Freeman"),
    ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
    ("The best error message is the one that never shows up.", "Thomas Fuchs"),
    ("Delete code. Delete code. Delete code.", "Unknown"),
    ("It's not a bug, it's an undocumented feature.", "Anonymous"),
    ("Programming is thinking, not typing.", "Casey Patton"),
    ("The only way to go fast is to go well.", "Robert C. Martin"),
    ("Debugging is twice as hard as writing the code. So if you write the code as cleverly as possible, you're not smart enough to debug it.", "Brian Kernighan"),
    ("Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.", "Antoine de Saint-Exupéry"),
    ("The computer was born to solve problems that did not exist before.", "Bill Gates"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
]


def get_motivation() -> str:
    """Rastgele motivasyon sözü."""
    quote, author = random.choice(MOTIVATION_QUOTES)
    return f'💡 "{quote}"\n\n— {author}'


# ============ Tech Quiz ============

QUIZ_TOPICS = [
    "Python", "JavaScript", "Git", "Linux", "Docker",
    "SQL", "REST API", "HTTP", "Data Structures", "Algorithms",
    "TypeScript", "React", "Node.js", "Rust", "Go"
]


def generate_quiz() -> dict:
    """Gemini ile quiz sorusu oluştur."""
    topic = random.choice(QUIZ_TOPICS)

    prompt = f"""Bir tech quiz sorusu oluştur.
Konu: {topic}

Kurallar:
- Orta zorlukta olsun
- 4 şık olsun (A, B, C, D)
- Türkçe olsun
- Doğru cevabı belirt

Format (JSON):
{{
    "question": "Soru metni",
    "options": {{
        "A": "Şık A",
        "B": "Şık B",
        "C": "Şık C",
        "D": "Şık D"
    }},
    "correct": "A",
    "explanation": "Kısa açıklama"
}}

Sadece JSON döndür, başka bir şey yazma."""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        # JSON parse
        import json
        text = response.text.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        quiz = json.loads(text)
        quiz["topic"] = topic
        return quiz
    except Exception as e:
        return {
            "error": str(e),
            "question": "Quiz oluşturulamadı, tekrar deneyin."
        }


def format_quiz(quiz: dict) -> str:
    """Quiz'i mesaj formatına çevir."""
    if "error" in quiz:
        return quiz["question"]

    text = f"🎯 Tech Quiz - {quiz.get('topic', 'Genel')}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"{quiz['question']}\n\n"

    for key, value in quiz.get("options", {}).items():
        text += f"{key}) {value}\n"

    text += "\n💭 Cevabınızı yazın (A/B/C/D)"

    return text


def check_quiz_answer(quiz: dict, answer: str) -> str:
    """Quiz cevabını kontrol et."""
    if "error" in quiz:
        return "Quiz verisi bulunamadı."

    correct = quiz.get("correct", "").upper()
    user_answer = answer.strip().upper()

    if user_answer == correct:
        text = "✅ Doğru!\n\n"
    else:
        text = f"❌ Yanlış! Doğru cevap: {correct}\n\n"

    text += f"📝 {quiz.get('explanation', '')}"
    return text


# ============ Repo Discovery ============

DISCOVER_QUERIES = [
    "machine learning",
    "web framework",
    "cli tool",
    "devops",
    "security",
    "database",
    "api",
    "automation",
    "visualization",
    "game engine",
    "blockchain",
    "serverless",
    "testing",
    "documentation",
    "productivity"
]


def discover_repo() -> str:
    """Rastgele ilginç repo öner."""
    query = random.choice(DISCOVER_QUERIES)

    try:
        # Random sayfa (1-5)
        page = random.randint(1, 5)

        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{query} stars:>1000",
                "sort": "stars",
                "order": "desc",
                "per_page": 30,
                "page": page
            },
            headers=HEADERS,
            timeout=10
        )

        if resp.status_code != 200:
            return "Repo araması başarısız oldu."

        data = resp.json()
        items = data.get("items", [])

        if not items:
            return "Repo bulunamadı."

        # Rastgele bir repo seç
        repo = random.choice(items)

        text = f"🔮 Keşif: {repo['full_name']}\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📝 {repo.get('description', 'Açıklama yok')}\n\n"
        text += f"⭐ {repo['stargazers_count']:,} stars\n"
        text += f"🍴 {repo['forks_count']:,} forks\n"
        text += f"💻 {repo.get('language', 'N/A')}\n"

        topics = repo.get("topics", [])[:5]
        if topics:
            text += f"🏷️ {', '.join(topics)}\n"

        text += f"\n🔗 {repo['html_url']}"

        return text
    except Exception as e:
        return f"Keşif hatası: {str(e)}"


def discover_by_topic(topic: str) -> str:
    """Belirli konuda repo öner."""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{topic} stars:>500",
                "sort": "stars",
                "order": "desc",
                "per_page": 10
            },
            headers=HEADERS,
            timeout=10
        )

        if resp.status_code != 200:
            return f"'{topic}' için arama başarısız."

        data = resp.json()
        items = data.get("items", [])

        if not items:
            return f"'{topic}' için repo bulunamadı."

        text = f"🔍 '{topic}' için öneriler\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, repo in enumerate(items[:5], 1):
            text += f"{i}. {repo['full_name']}\n"
            text += f"   ⭐ {repo['stargazers_count']:,} | {repo.get('language', 'N/A')}\n"
            desc = repo.get('description', '')[:60]
            if desc:
                text += f"   {desc}...\n"
            text += "\n"

        return text
    except Exception as e:
        return f"Arama hatası: {str(e)}"


if __name__ == "__main__":
    print(get_motivation())
    print("\n" + discover_repo())
