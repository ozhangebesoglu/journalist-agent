"""
Extra Features - /roadmap, /daily, /meme, /wisdom, /password, /coffee
"""

import os
import random
import string
import secrets
import math
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai

from agents import db

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash"


def generate_roadmap(topic: str) -> str:
    prompt = f"""Sen deneyimli bir yazılım eğitmenisin. "{topic}" konusunda sıfırdan ileri seviyeye öğrenme yol haritası oluştur.

KURALLAR:
1. Türkçe yaz
2. Pratik ve gerçekçi ol
3. Her aşama için tahmini süre ver
4. Ücretsiz kaynaklar öner
5. Mini projeler öner

FORMAT:
🗺️ {topic.upper()} ÖĞRENME YOL HARİTASI

📅 Toplam Süre: X ay (haftada Y saat çalışarak)

🔰 AŞAMA 1: Temel Kavramlar (X hafta)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Konu 1
• Konu 2
📚 Kaynaklar: [ücretsiz kaynaklar]
🛠️ Mini Proje: [basit proje önerisi]

🔵 AŞAMA 2: Orta Seviye (X hafta)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...

🔴 AŞAMA 3: İleri Seviye (X hafta)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...

⭐ AŞAMA 4: Uzmanlaşma (X hafta)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...

💡 İPUÇLARI:
• Önemli tavsiyeler

🎯 HEDEF PROJE:
[Tüm öğrenilenleri birleştiren capstone proje önerisi]
"""

    try:
        response = client.models.generate_content(
            model=MODEL, contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        return response.text or "Yol haritası oluşturulamadı."
    except Exception as e:
        return f"Yol haritası oluşturulurken hata: {str(e)}"


CHALLENGE_CATEGORIES = [
    "algoritma",
    "veri yapısı",
    "string manipülasyon",
    "array/liste",
    "matematik",
    "recursion",
    "dinamik programlama",
    "arama/sıralama",
]

DIFFICULTY_LEVELS = ["kolay", "orta", "zor"]


def get_daily_challenge(difficulty: str | None = None) -> dict:
    if not difficulty:
        difficulty = random.choice(DIFFICULTY_LEVELS)

    category = random.choice(CHALLENGE_CATEGORIES)

    prompt = f"""Bir coding challenge oluştur.

Zorluk: {difficulty}
Kategori: {category}

KURALLAR:
1. Türkçe yaz
2. Gerçekçi ve çözülebilir olsun
3. Herhangi bir dilde çözülebilir olsun
4. Örnek input/output ver

FORMAT (JSON):
{{
    "title": "Challenge başlığı",
    "description": "Detaylı açıklama",
    "difficulty": "{difficulty}",
    "category": "{category}",
    "example_input": "Örnek girdi",
    "example_output": "Beklenen çıktı",
    "hints": ["İpucu 1", "İpucu 2"],
    "bonus": "Ekstra challenge (opsiyonel)"
}}

Sadece JSON döndür, başka bir şey yazma.
"""

    try:
        response = client.models.generate_content(
            model=MODEL, contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        return json.loads(text)
    except Exception:
        return {
            "title": "İki Sayının Toplamı",
            "description": "Bir tamsayı dizisi ve bir hedef sayı verildiğinde, toplamı hedefe eşit olan iki sayının indekslerini bulun.",
            "difficulty": difficulty,
            "category": "array/liste",
            "example_input": "nums = [2, 7, 11, 15], target = 9",
            "example_output": "[0, 1] (çünkü nums[0] + nums[1] = 2 + 7 = 9)",
            "hints": [
                "Hash map kullanmayı dene",
                "Her eleman için hedef - eleman değerini ara",
            ],
            "bonus": "O(n) time complexity ile çöz",
        }


def format_daily_challenge(challenge: dict) -> str:
    difficulty_emoji = {"kolay": "🟢", "orta": "🟡", "zor": "🔴"}
    emoji = difficulty_emoji.get(challenge["difficulty"], "⚪")

    text = f"""🎯 GÜNÜN CODING CHALLENGE'I
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji} Zorluk: {challenge["difficulty"].title()}
📂 Kategori: {challenge["category"].title()}

📋 {challenge["title"]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{challenge["description"]}

📥 Örnek Girdi:
{challenge["example_input"]}

📤 Beklenen Çıktı:
{challenge["example_output"]}

💡 İpuçları:
"""

    for i, hint in enumerate(challenge.get("hints", []), 1):
        text += f"  {i}. {hint}\n"

    if challenge.get("bonus"):
        text += f"\n⭐ Bonus: {challenge['bonus']}"

    text += "\n\n🔑 Çözümünü /solution ile paylaşabilirsin!"

    return text


MEME_SUBREDDITS = ["ProgrammerHumor", "programmingmemes"]


def get_programming_meme() -> dict:
    import requests

    try:
        subreddit = random.choice(MEME_SUBREDDITS)
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=50"

        headers = {"User-Agent": "GazeteciBot/1.0"}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])

            image_posts = []
            for post in posts:
                post_data = post.get("data", {})
                post_url = post_data.get("url", "")

                if any(ext in post_url for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                    if not post_data.get("over_18"):
                        image_posts.append(
                            {
                                "url": post_url,
                                "title": post_data.get("title", ""),
                                "subreddit": subreddit,
                                "score": post_data.get("score", 0),
                            }
                        )

            if image_posts:
                top_posts = sorted(image_posts, key=lambda x: x["score"], reverse=True)[
                    :10
                ]
                return random.choice(top_posts)

    except Exception as e:
        print(f"Meme fetch error: {e}")

    fallback_memes = [
        {
            "url": "https://i.imgur.com/HTisMpC.jpeg",
            "title": "It works on my machine",
            "subreddit": "fallback",
        },
        {
            "url": "https://i.imgur.com/y7Hm9.jpeg",
            "title": "Debugging be like",
            "subreddit": "fallback",
        },
    ]

    return random.choice(fallback_memes)


WISDOM_QUOTES = [
    {
        "quote": "Herhangi bir aptal, bir bilgisayarın anlayabileceği kod yazabilir. İyi programcılar insanların anlayabileceği kod yazar.",
        "author": "Martin Fowler",
        "original": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",
    },
    {
        "quote": "İlk önce çalışmasını sağla, sonra hızlı yap, sonra güzel yap.",
        "author": "Kent Beck",
        "original": "Make it work, make it right, make it fast.",
    },
    {
        "quote": "Basitlik, güvenilirliğin ön koşuludur.",
        "author": "Edsger W. Dijkstra",
        "original": "Simplicity is prerequisite for reliability.",
    },
    {
        "quote": "Kod yazmadan önce düşünmek için harcadığın her saat, hata ayıklamak için harcayacağın on saati kurtarır.",
        "author": "Anonim",
        "original": "Every hour spent thinking before coding saves ten hours of debugging.",
    },
    {
        "quote": "En iyi kod, hiç yazılmamış koddur.",
        "author": "Jeff Atwood",
        "original": "The best code is no code at all.",
    },
    {
        "quote": "Erken optimizasyon, tüm kötülüklerin anasıdır.",
        "author": "Donald Knuth",
        "original": "Premature optimization is the root of all evil.",
    },
    {
        "quote": "Programlama, düşünmenin başka bir yoludur.",
        "author": "Seymour Papert",
        "original": "Programming is another way of thinking.",
    },
    {
        "quote": "Hata ayıklamak, kod yazmaktan iki kat daha zordur.",
        "author": "Brian Kernighan",
        "original": "Debugging is twice as hard as writing the code in the first place.",
    },
    {
        "quote": "Kod tekrarı, tasarım eksikliğinin işaretidir.",
        "author": "Robert C. Martin",
        "original": "Duplication is the primary enemy of a well-designed system.",
    },
    {
        "quote": "İyi programcılar kod yazar, harika programcılar kod siler.",
        "author": "Anonim",
        "original": "Good programmers write code, great programmers delete code.",
    },
    {
        "quote": "Her büyük geliştirici, bir zamanlar kötü bir geliştiriciydi.",
        "author": "Anonim",
        "original": "Every expert was once a beginner.",
    },
    {
        "quote": "Öğrenmeyi bıraktığın an, ölmeye başlarsın.",
        "author": "Albert Einstein",
        "original": "Once you stop learning, you start dying.",
    },
    {
        "quote": "Mükemmellik bir alışkanlıktır, bir eylem değil.",
        "author": "Aristoteles",
        "original": "Excellence is not an act, but a habit.",
    },
    {
        "quote": "Karmaşıklığı yönetmenin tek yolu, onu parçalara ayırmaktır.",
        "author": "Edsger W. Dijkstra",
        "original": "The art of programming is the art of organizing complexity.",
    },
    {
        "quote": "Talk is cheap. Show me the code.",
        "author": "Linus Torvalds",
        "original": "Talk is cheap. Show me the code.",
    },
    {
        "quote": "Bir sorunu çözemiyorsan, daha basit bir sorun bul.",
        "author": "George Pólya",
        "original": "If you can't solve a problem, then there is an easier problem you can solve: find it.",
    },
]


def get_wisdom_quote() -> dict:
    return random.choice(WISDOM_QUOTES)


def format_wisdom_quote(wisdom: dict) -> str:
    return f"""💭 GÜNÜN SÖZÜ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"{wisdom["quote"]}"

— {wisdom["author"]}

🔤 Orijinal:
"{wisdom["original"]}"
"""


def generate_password(
    length: int = 16,
    include_upper: bool = True,
    include_lower: bool = True,
    include_digits: bool = True,
    include_special: bool = True,
    exclude_ambiguous: bool = True,
) -> dict:
    length = max(8, min(128, length))

    chars = ""

    if include_lower:
        chars += (
            "abcdefghjkmnpqrstuvwxyz" if exclude_ambiguous else string.ascii_lowercase
        )

    if include_upper:
        chars += (
            "ABCDEFGHJKMNPQRSTUVWXYZ" if exclude_ambiguous else string.ascii_uppercase
        )

    if include_digits:
        chars += "23456789" if exclude_ambiguous else string.digits

    if include_special:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    if not chars:
        chars = string.ascii_letters + string.digits

    password = "".join(secrets.choice(chars) for _ in range(length))

    entropy = length * math.log2(len(chars))

    if entropy < 40:
        strength, strength_emoji = "Zayıf", "🔴"
    elif entropy < 60:
        strength, strength_emoji = "Orta", "🟡"
    elif entropy < 80:
        strength, strength_emoji = "Güçlü", "🟢"
    else:
        strength, strength_emoji = "Çok Güçlü", "💪"

    return {
        "password": password,
        "strength": strength,
        "strength_emoji": strength_emoji,
        "entropy": round(entropy, 1),
        "length": length,
        "charset_size": len(chars),
    }


def format_password(pwd_info: dict) -> str:
    return f"""🔐 GÜVENLİ ŞİFRE OLUŞTURULDU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`{pwd_info["password"]}`

{pwd_info["strength_emoji"]} Güç: {pwd_info["strength"]}
📏 Uzunluk: {pwd_info["length"]} karakter
🎲 Entropi: {pwd_info["entropy"]} bit
🔢 Karakter seti: {pwd_info["charset_size"]} karakter

⚠️ Bu şifreyi güvenli bir yerde saklayın!
💡 Şifre yöneticisi kullanmanızı öneririz.

🔄 Yeni şifre: /password [uzunluk]
Örn: /password 24
"""


COFFEE_MESSAGES = [
    "☕ Kahve molası zamanı! Ekranından uzaklaş, gözlerini dinlendir.",
    "☕ Beyin yakıtı vakti! Bir fincan kahve/çay seni bekliyor.",
    "☕ Kod yazarken mola vermek üretkenliği artırır. Kahve zamanı!",
    "☕ Pomodoro'ya gerek yok, kahve seni çağırıyor!",
    "☕ Debugging yaparken kahve içmek bilimsel olarak kanıtlanmış bir tedavidir.",
    "☕ İyi bir geliştirici olmak için: Sleep, Code, Coffee, Repeat.",
    "☕ while(tired) { coffee++; }",
    "☕ Exception: CoffeeNotFoundException - Acil kahve gerekli!",
    "☕ git commit -m 'kahve molası'",
    "☕ Kahve içerken harika fikirler gelir. Mola ver!",
]

STRETCH_MESSAGES = [
    "🧘 Esneme vakti! Omuzlarını geriye çek, boynunu esnet.",
    "🧘 20-20-20 kuralı: 20 dakikada bir, 20 saniye boyunca 6m uzağa bak.",
    "🧘 Bileklerini döndür, parmaklarını esnet. RSI'dan korunmak bedava!",
    "🧘 Dik otur, omurganı düzelt. Postür önemli!",
    "🧘 Kalk ve biraz yürü. Kan dolaşımını artır.",
]


def get_coffee_reminder(include_stretch: bool = True) -> str:
    coffee = random.choice(COFFEE_MESSAGES)

    text = f"{coffee}\n\n"

    if include_stretch:
        text += f"{random.choice(STRETCH_MESSAGES)}\n"

    text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ Hatırlatıcı kur: /remind 45 kahve molası
🍅 Pomodoro başlat: /pomodoro 25
"""

    return text.strip()


def schedule_coffee_reminder(chat_id: str, minutes: int = 45) -> str:
    remind_at = datetime.now() + timedelta(minutes=minutes)
    message = get_coffee_reminder(include_stretch=True)

    db.add_reminder(chat_id, message, remind_at)

    return f"☕ {minutes} dakika sonra kahve molası hatırlatılacak! ({remind_at.strftime('%H:%M')})"


if __name__ == "__main__":
    print("=== DAILY CHALLENGE TEST ===")
    challenge = get_daily_challenge("kolay")
    print(format_daily_challenge(challenge))

    print("\n=== WISDOM TEST ===")
    wisdom = get_wisdom_quote()
    print(format_wisdom_quote(wisdom))

    print("\n=== PASSWORD TEST ===")
    pwd = generate_password(20)
    print(format_password(pwd))

    print("\n=== COFFEE TEST ===")
    print(get_coffee_reminder())
