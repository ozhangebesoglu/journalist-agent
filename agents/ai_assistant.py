"""
AI Assistant - Gemini tabanlı akıllı asistan özellikleri

Özellikler:
    - ask: Genel soru-cevap
    - code: Kod yazma
    - explain: Kod açıklama
    - translate: Çeviri
"""

import os
from dotenv import load_dotenv
from google import genai

from agents import db

load_dotenv()

# Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash"

# System prompts
SYSTEM_PROMPTS = {
    "ask": """Sen JARVIS, yardımcı bir AI asistansın.
Kısa, öz ve bilgilendirici cevaplar ver.
Türkçe konuş, teknik terimleri kullanabilirsin.
Esprili ve samimi ol ama profesyonel kal.""",

    "code": """Sen uzman bir yazılım geliştiricisin.
Kullanıcının istediği kodu yaz.
- Temiz, okunabilir kod yaz
- Gerekli yorumları ekle
- Best practice'leri uygula
- Sadece kodu ver, fazla açıklama yapma
Dil belirtilmemişse Python kullan.""",

    "explain": """Sen bir kod açıklama uzmanısın.
Verilen kodu analiz et ve açıkla:
- Ne yaptığını özetle
- Önemli kısımları açıkla
- Potansiyel sorunları belirt
- İyileştirme önerileri sun
Türkçe açıkla, teknik ol ama anlaşılır ol.""",

    "translate": """Sen profesyonel bir çevirmensin.
Verilen metni hedef dile çevir.
- Doğal ve akıcı çeviri yap
- Teknik terimleri doğru çevir
- Bağlamı koru
Varsayılan: Türkçe ↔ İngilizce""",

    "general": """Sen JARVIS, çok yönlü bir AI asistansın.
Kullanıcıya her konuda yardımcı ol.
Türkçe konuş, samimi ve profesyonel ol."""
}


def _build_messages(chat_id: str, system_prompt: str, user_message: str) -> list[dict]:
    """Build message list with chat history."""
    messages = []

    # System prompt
    messages.append({
        "role": "user",
        "parts": [{"text": f"[SYSTEM]: {system_prompt}"}]
    })
    messages.append({
        "role": "model",
        "parts": [{"text": "Anladım, bu role göre davranacağım."}]
    })

    # Chat history
    history = db.get_chat_history(chat_id, limit=6)
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    # Current message
    messages.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    return messages


def ask(chat_id: str, question: str) -> str:
    """Genel soru-cevap."""
    try:
        # Save user message
        db.add_chat_message(chat_id, "user", question)

        messages = _build_messages(chat_id, SYSTEM_PROMPTS["ask"], question)

        response = client.models.generate_content(
            model=MODEL,
            contents=messages
        )

        answer = response.text

        # Save assistant response
        db.add_chat_message(chat_id, "assistant", answer)

        return answer
    except Exception as e:
        return f"Hata oluştu: {str(e)}"


def generate_code(chat_id: str, description: str) -> str:
    """Kod üret."""
    try:
        prompt = f"Şu kodu yaz: {description}"

        messages = _build_messages(chat_id, SYSTEM_PROMPTS["code"], prompt)

        response = client.models.generate_content(
            model=MODEL,
            contents=messages
        )

        return response.text
    except Exception as e:
        return f"Kod üretme hatası: {str(e)}"


def explain_code(chat_id: str, code: str) -> str:
    """Kodu açıkla."""
    try:
        prompt = f"Bu kodu açıkla:\n\n```\n{code}\n```"

        messages = _build_messages(chat_id, SYSTEM_PROMPTS["explain"], prompt)

        response = client.models.generate_content(
            model=MODEL,
            contents=messages
        )

        return response.text
    except Exception as e:
        return f"Kod açıklama hatası: {str(e)}"


def translate(chat_id: str, text: str, target_lang: str = None) -> str:
    """Metin çevir."""
    try:
        if target_lang:
            prompt = f"{target_lang} diline çevir:\n\n{text}"
        else:
            # Auto-detect: Turkish -> English, else -> Turkish
            prompt = f"Bu metni çevir (Türkçe ise İngilizce'ye, değilse Türkçe'ye):\n\n{text}"

        messages = _build_messages(chat_id, SYSTEM_PROMPTS["translate"], prompt)

        response = client.models.generate_content(
            model=MODEL,
            contents=messages
        )

        return response.text
    except Exception as e:
        return f"Çeviri hatası: {str(e)}"


def analyze_repo(repo_url: str) -> str:
    """GitHub repo analizi."""
    try:
        import requests

        # Extract owner/repo from URL
        parts = repo_url.rstrip('/').split('/')
        if 'github.com' in repo_url:
            owner, repo = parts[-2], parts[-1]
        else:
            return "Geçersiz GitHub URL'si"

        # Fetch repo data
        headers = {"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"}

        repo_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers
        )

        if repo_resp.status_code != 200:
            return f"Repo bulunamadı: {owner}/{repo}"

        data = repo_resp.json()

        # Fetch README
        readme_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=headers
        )
        readme = ""
        if readme_resp.status_code == 200:
            import base64
            readme = base64.b64decode(readme_resp.json().get("content", "")).decode("utf-8")[:2000]

        # Build analysis prompt
        prompt = f"""Bu GitHub reposunu analiz et:

Repo: {data.get('full_name')}
Açıklama: {data.get('description', 'Yok')}
Dil: {data.get('language', 'Bilinmiyor')}
Stars: {data.get('stargazers_count', 0):,}
Forks: {data.get('forks_count', 0):,}
Open Issues: {data.get('open_issues_count', 0)}
Created: {data.get('created_at', '')[:10]}
Last Push: {data.get('pushed_at', '')[:10]}
Topics: {', '.join(data.get('topics', []))}

README (ilk 2000 karakter):
{readme}

Analiz et:
1. Bu repo ne işe yarıyor?
2. Hedef kitlesi kim?
3. Güçlü yönleri
4. Zayıf yönleri veya eksikler
5. Benzer alternatifler
6. Tavsiye: Kullanılmalı mı?
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        return response.text
    except Exception as e:
        return f"Analiz hatası: {str(e)}"


def compare_repos(repo1: str, repo2: str) -> str:
    """İki repo/teknolojiyi karşılaştır."""
    try:
        prompt = f"""Bu iki teknolojiyi/repoyu karşılaştır:

1. {repo1}
2. {repo2}

Karşılaştırma kriterleri:
- Amaç ve kullanım alanı
- Performans
- Öğrenme eğrisi
- Topluluk ve destek
- Dokümantasyon
- Avantajlar/Dezavantajlar

Sonuç olarak hangisini, hangi durumda tercih etmeli?
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        return response.text
    except Exception as e:
        return f"Karşılaştırma hatası: {str(e)}"


def clear_context(chat_id: str):
    """Sohbet geçmişini temizle."""
    db.clear_chat_history(chat_id)
    return "Sohbet geçmişi temizlendi."


def analyze_image(image_bytes: bytes, prompt: str = None) -> str:
    """Görsel analizi (Gemini Vision)."""
    try:
        import base64

        # Base64 encode
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        user_prompt = prompt or "Bu görseli analiz et ve açıkla. Türkçe cevap ver."

        response = client.models.generate_content(
            model=MODEL,
            contents=[{
                "role": "user",
                "parts": [
                    {"text": user_prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    }
                ]
            }]
        )

        return response.text
    except Exception as e:
        return f"Görsel analiz hatası: {str(e)}"


def analyze_document(text_content: str, filename: str) -> str:
    """Dosya/döküman analizi."""
    try:
        prompt = f"""Bu dosyayı analiz et:

Dosya adı: {filename}

İçerik:
{text_content[:5000]}

Analiz et:
1. Dosya ne hakkında?
2. Ana noktalar neler?
3. Önemli bilgiler
4. Varsa sorunlar veya öneriler
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        return response.text
    except Exception as e:
        return f"Dosya analiz hatası: {str(e)}"


def summarize_text(text: str) -> str:
    """Metin özetleme."""
    try:
        prompt = f"""Bu metni özetle:

{text[:5000]}

Kısa ve öz bir özet yaz (maksimum 3-4 paragraf).
Türkçe yaz.
"""

        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )

        return response.text
    except Exception as e:
        return f"Özetleme hatası: {str(e)}"


if __name__ == "__main__":
    # Test
    print(ask("test", "Python'da list comprehension nedir?"))
