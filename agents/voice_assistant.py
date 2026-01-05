"""
Voice Assistant - Sesli Asistan Modülü

Özellikler:
    - Speech-to-Text: Ses mesajlarını metne çevir (Whisper API)
    - Text-to-Speech: Metni sese çevir (Edge TTS - ücretsiz)
    - Sesli brifing oluşturma
    - Telegram voice message desteği
"""

import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
VOICE_DIR = DATA_DIR / "voice"
VOICE_DIR.mkdir(parents=True, exist_ok=True)


# ============ Speech-to-Text (Whisper) ============

def transcribe_audio_whisper(audio_path: str) -> str:
    """
    Ses dosyasını Whisper API ile metne çevir.
    
    Args:
        audio_path: Ses dosyası yolu (.ogg, .mp3, .wav, .m4a)
    
    Returns:
        Transkript metni
    """
    try:
        import google.genai as genai
        
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Ses dosyasını yükle
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        # Gemini ile transkript (Gemini 2.0 ses destekliyor)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {
                    "parts": [
                        {"text": "Bu ses kaydını Türkçe olarak transkript et. Sadece konuşulan metni yaz, başka bir şey ekleme."},
                        {
                            "inline_data": {
                                "mime_type": get_mime_type(audio_path),
                                "data": __import__("base64").b64encode(audio_data).decode()
                            }
                        }
                    ]
                }
            ]
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"[ERROR] Whisper transcription failed: {e}")
        # Fallback: OpenAI Whisper API
        return transcribe_audio_openai(audio_path)


def transcribe_audio_openai(audio_path: str) -> str:
    """
    OpenAI Whisper API ile transkript (fallback).
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return "[Ses tanıma için API anahtarı gerekli]"
    
    try:
        import requests
        
        with open(audio_path, "rb") as f:
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {openai_key}"},
                files={"file": f},
                data={"model": "whisper-1", "language": "tr"}
            )
        
        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            return f"[Transkript hatası: {response.status_code}]"
            
    except Exception as e:
        return f"[Ses tanıma hatası: {str(e)}]"


def get_mime_type(file_path: str) -> str:
    """Dosya uzantısından MIME type belirle."""
    ext = Path(file_path).suffix.lower()
    mime_types = {
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac"
    }
    return mime_types.get(ext, "audio/ogg")


# ============ Text-to-Speech (Edge TTS) ============

async def text_to_speech_async(text: str, output_path: str = None, voice: str = "tr-TR-AhmetNeural") -> str:
    """
    Metni Edge TTS ile sese çevir (async).
    
    Args:
        text: Seslendirilecek metin
        output_path: Çıktı dosya yolu (opsiyonel)
        voice: Ses tipi
            - tr-TR-AhmetNeural (erkek)
            - tr-TR-EmelNeural (kadın)
    
    Returns:
        Oluşturulan ses dosyasının yolu
    """
    try:
        import edge_tts
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(VOICE_DIR / f"tts_{timestamp}.mp3")
        
        # Metni temizle
        clean_text = clean_text_for_tts(text)
        
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(output_path)
        
        return output_path
        
    except ImportError:
        print("[WARN] edge-tts not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "edge-tts"], check=True)
        return await text_to_speech_async(text, output_path, voice)
        
    except Exception as e:
        print(f"[ERROR] TTS failed: {e}")
        return None


def text_to_speech(text: str, output_path: str = None, voice: str = "tr-TR-AhmetNeural") -> str:
    """
    Metni Edge TTS ile sese çevir (sync wrapper).
    """
    return asyncio.run(text_to_speech_async(text, output_path, voice))


def clean_text_for_tts(text: str) -> str:
    """TTS için metni temizle."""
    import re
    
    # Markdown formatlamalarını kaldır
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)       # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)         # Code
    text = re.sub(r'#{1,6}\s*', '', text)            # Headers
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
    
    # Emojileri kaldır veya açıklamaya çevir
    emoji_map = {
        "🚀": "roket",
        "⭐": "yıldız",
        "🔥": "ateş",
        "📊": "",
        "📈": "",
        "📉": "",
        "💡": "",
        "🤖": "",
        "📦": "",
        "🔔": "",
        "✅": "",
        "❌": "",
        "⚠️": "uyarı",
        "━": "",
        "─": "",
    }
    
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
    
    # Diğer emojileri kaldır
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    
    # Fazla boşlukları temizle
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()


# ============ Sesli Brifing ============

async def create_voice_briefing(briefing_text: str = None) -> str | None:
    """
    Günlük brifingi sesli olarak oluştur.
    
    Returns:
        Ses dosyasının yolu
    """
    if not briefing_text:
        # Son brifingi oku
        report_path = BASE_DIR / "reports" / "final_report.md"
        if not report_path.exists():
            return None
        briefing_text = report_path.read_text(encoding="utf-8")
    
    # Brifingi kısalt (TTS için çok uzun olabilir)
    summary = summarize_for_voice(briefing_text)
    
    # Sese çevir
    output_path = str(VOICE_DIR / f"briefing_{datetime.now().strftime('%Y%m%d')}.mp3")
    return await text_to_speech_async(summary, output_path)


def summarize_for_voice(text: str, max_chars: int = 3000) -> str:
    """
    Brifingi sesli okuma için özetle.
    """
    # Sadece önemli kısımları al
    lines = text.split('\n')
    important_lines = []
    current_section = ""
    
    for line in lines:
        # Başlıkları al
        if line.startswith('#'):
            current_section = line.strip('#').strip()
            important_lines.append(f"\n{current_section}.\n")
        
        # İçerik satırlarını al (liste öğeleri, önemli bilgiler)
        elif line.strip().startswith(('-', '•', '*', '1.', '2.', '3.')):
            content = line.strip().lstrip('-•* 0123456789.').strip()
            if content and len(content) > 10:
                important_lines.append(content)
    
    summary = '\n'.join(important_lines)
    
    # Çok uzunsa kısalt
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "... Devamı için yazılı brifingi okuyun."
    
    # Giriş ekle
    intro = f"Günaydın efendim. Bugünün teknoloji brifingini sunuyorum. "
    
    return intro + summary


# ============ Voice Message Handler ============

async def handle_voice_message(audio_path: str, chat_id: str) -> tuple[str, str | None]:
    """
    Telegram'dan gelen ses mesajını işle.
    
    Args:
        audio_path: İndirilen ses dosyası yolu
        chat_id: Kullanıcı chat ID
    
    Returns:
        (transkript, yanıt_ses_dosyası)
    """
    from agents import ai_assistant, learning_tracker
    
    # 1. Sesi metne çevir
    transcript = transcribe_audio_whisper(audio_path)
    
    if not transcript or transcript.startswith("["):
        return transcript, None
    
    # 2. Öğrenme takibi
    learning_tracker.track_interaction(chat_id, transcript, "voice")
    
    # 3. AI yanıtı al
    response = ai_assistant.ask(chat_id, transcript)
    
    # 4. Yanıtı sese çevir (kısa yanıtlar için)
    voice_response = None
    if len(response) < 1500:
        voice_response = await text_to_speech_async(response)
    
    return transcript, voice_response


# ============ Kullanılabilir Sesler ============

def get_available_voices() -> list[dict]:
    """Edge TTS'te kullanılabilir Türkçe sesleri listele."""
    return [
        {"id": "tr-TR-AhmetNeural", "name": "Ahmet", "gender": "Male", "style": "Profesyonel erkek sesi"},
        {"id": "tr-TR-EmelNeural", "name": "Emel", "gender": "Female", "style": "Profesyonel kadın sesi"},
    ]


def format_voice_list() -> str:
    """Ses listesini formatla."""
    voices = get_available_voices()
    lines = ["🎙️ MEVCUT SESLER", "━" * 20, ""]
    
    for v in voices:
        lines.append(f"• {v['name']} ({v['gender']})")
        lines.append(f"  {v['style']}")
        lines.append(f"  ID: {v['id']}")
        lines.append("")
    
    lines.append("Değiştir: /voice <id>")
    return "\n".join(lines)


# ============ Test ============

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_text = " ".join(sys.argv[1:])
    else:
        test_text = """
        Günaydın efendim! Bugünün teknoloji dünyasından önemli gelişmeler var.
        
        Birinci sırada, yeni bir Rust projesi büyük ilgi görüyor. 
        Bu hafta 5000 yıldız kazandı.
        
        İkinci olarak, yapay zeka alanında önemli bir gelişme yaşandı.
        Yeni bir dil modeli açık kaynak olarak yayınlandı.
        
        Detaylar için yazılı brifingi inceleyebilirsiniz.
        """
    
    print("🎙️ Ses oluşturuluyor...")
    output = text_to_speech(test_text)
    
    if output:
        print(f"✅ Ses dosyası: {output}")
    else:
        print("❌ Ses oluşturulamadı")
