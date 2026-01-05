"""
Telegram Bot - Gazeteci AI Asistan (Full Version)

TÜM KOMUTLAR:
    BRIFING: /start /briefing /generate /trending /status
    AI: /ask /code /explain /translate /compare /summarize /clear
    GÖRSEL: Fotoğraf gönder -> analiz
    REPO: /watch /unwatch /watches /alert /alerts /analyze
    ARAÇLAR: /bookmark /bookmarks /note /notes /snippet /snippets
    TIMER: /remind /reminders /pomodoro
    UTILITY: /weather /price /shorten /qr
    KEŞİF: /discover /quiz /motivation
    VERİ: /mystats /export /goal /goals
    /help
"""

import os
import re
import json
import asyncio
import io
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
CHAT_ID_FILE = DATA_DIR / "telegram_chat_id.txt"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MAX_MESSAGE_LENGTH = 4096

quiz_cache = {}


def get_chat_id() -> str | None:
    if CHAT_ID_FILE.exists():
        return CHAT_ID_FILE.read_text().strip()
    return None


def save_chat_id(chat_id: str):
    DATA_DIR.mkdir(exist_ok=True)
    CHAT_ID_FILE.write_text(str(chat_id))


async def send_long_message(update: Update, text: str):
    if len(text) <= MAX_MESSAGE_LENGTH:
        await update.message.reply_text(text)
        return

    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
            parts.append(current)
            current = line + "\n"
        else:
            current += line + "\n"
    if current:
        parts.append(current)

    for part in parts:
        await update.message.reply_text(part.strip())
        await asyncio.sleep(0.3)


# ============== TEMEL ==============


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    db.init_db()

    chat_id = str(update.effective_chat.id)
    save_chat_id(chat_id)

    welcome = """Merhaba efendim! Ben JARVIS, AI asistanınız.

🗞️ BRİFİNG
/briefing /generate /trending

🤖 AI ASİSTAN
/ask /code /explain /translate /compare
Fotoğraf gönder -> analiz

👀 TAKİP
/watch /alert /analyze

🔧 ARAÇLAR
/bookmark /note /snippet /remind

🍅 POMODORO
/pomodoro 25

🌐 UTILITY
/weather /price /shorten /qr

🎲 KEŞİF
/discover /quiz /motivation

📊 VERİ
/mystats /export /goal

/help - Tüm komutlar"""

    await update.message.reply_text(welcome)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 JARVIS Komut Rehberi
━━━━━━━━━━━━━━━━━━━━━━

🗞️ BRİFİNG
/briefing - Son brifing
/generate - Yeni oluştur
/trending - Top 5 repo
/status - Sistem durumu
/weekly - Haftalık trend raporu
/monthly - Aylık trend raporu

🤖 AI ASİSTAN
/ask <soru> - Soru sor
/code <açıklama> - Kod yaz
/explain - Kod açıkla (reply)
/translate <metin> - Çevir
/compare X vs Y - Karşılaştır
/summarize - Özetle (reply)
/clear - Geçmişi sil
📷 Fotoğraf gönder - Analiz et

🎯 KİŞİSELLEŞTİRME
/interests - İlgi alanları
/feed - Kişisel feed
/suggest - Öneriler
/learning - Öğrenme özeti
/notifications - Bildirimler

👀 REPO TAKİP
/watch owner/repo - Takibe al
/unwatch repo - Çıkar
/watches - Liste
/alert keyword - HN alert
/alerts - Alert listesi
/analyze <url> - Repo analizi

🔧 ARAÇLAR
/bookmark <url> - Kaydet
/bookmarks - Liste
/note <not> - Not al
/notes - Notlar
/snippet save/get
/snippets - Liste

⏰ ZAMANLAYICI
/remind <dk> <mesaj>
/reminders - Liste
/pomodoro <dakika>

🌐 UTILITY
/weather <şehir>
/price <btc/usd/eur>
/shorten <url>
/qr <metin>

🎲 KEŞİF
/discover [konu]
/quiz - Tech quiz
/motivation

🗺️ ÖĞRENME
/roadmap <konu> - Öğrenme yol haritası
/daily [zorluk] - Günlük challenge
/wisdom - Günün sözü

🎭 EĞLENCE
/meme - Programlama meme'i
/coffee [dk] - Kahve molası

🔐 GÜVENLİK
/password [uzunluk] - Güvenli şifre

🎙️ SESLİ ASİSTAN
🎤 Ses mesajı gönder - Sesli soru sor
/voicebriefing - Sesli brifing
/speak <metin> - Metni seslendir
/voice - Ses ayarları

📊 VERİ
/mystats - İstatistikler
/export - Verileri indir
/goal <hedef> - Hedef ekle
/goals - Hedefler"""

    await update.message.reply_text(help_text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    report_path = REPORTS_DIR / "final_report.md"

    if report_path.exists():
        mtime = datetime.fromtimestamp(report_path.stat().st_mtime)
        last_briefing = mtime.strftime("%Y-%m-%d %H:%M")
    else:
        last_briefing = "Henüz yok"

    chat_id = str(update.effective_chat.id)
    watches = db.get_watched_repos(chat_id)
    alerts = db.get_keyword_alerts(chat_id)
    bookmarks = db.get_bookmarks(chat_id)
    notes = db.get_notes(chat_id)

    status_text = f"""📊 JARVIS Durumu
━━━━━━━━━━━━━━━━

🤖 Bot: Aktif
📅 Son Brifing: {last_briefing}

👤 Verilerin:
👀 {len(watches)} repo takipte
🔔 {len(alerts)} alert
🔖 {len(bookmarks)} bookmark
📝 {len(notes)} not"""

    await update.message.reply_text(status_text)


# ============== BRİFİNG ==============


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_path = REPORTS_DIR / "final_report.md"
    if not report_path.exists():
        await update.message.reply_text("Brifing yok. /generate ile oluşturun.")
        return
    content = report_path.read_text(encoding="utf-8")
    await send_long_message(update, content)


async def cmd_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import collector, writer, analyst

    await update.message.reply_text("🚀 Brifing oluşturuluyor...")

    try:
        await update.message.reply_text("📡 Veriler toplanıyor...")
        collector.run_collector()

        for i in range(3):
            await update.message.reply_text(f"✍️ Yazılıyor... ({i + 1}/3)")
            writer.run_writer()
            if analyst.run_analyst() == "approved":
                await update.message.reply_text("✅ Onaylandı!")
                await cmd_briefing(update, context)
                return

        await update.message.reply_text("⚠️ Son taslak gönderiliyor...")
        await cmd_briefing(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")


async def cmd_trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repos_file = DATA_DIR / "repos.json"
    if not repos_file.exists():
        await update.message.reply_text("Veri yok. /generate ile başlayın.")
        return

    repos = json.loads(repos_file.read_text())
    sorted_repos = sorted(repos, key=lambda x: x.get("stars", 0), reverse=True)[:5]

    text = "🔥 Top 5 Trending\n━━━━━━━━━━━━━━━━\n\n"
    for i, repo in enumerate(sorted_repos, 1):
        text += f"{i}. {repo.get('full_name', 'N/A')}\n"
        text += f"   ⭐ {repo.get('stars', 0):,} | {repo.get('language', 'N/A')}\n\n"

    await update.message.reply_text(text)


# ============== AI ASİSTAN ==============


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if not context.args:
        await update.message.reply_text("Kullanım: /ask <sorunuz>")
        return
    question = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("🤔 Düşünüyorum...")
    response = ai_assistant.ask(chat_id, question)
    await send_long_message(update, response)


async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if not context.args:
        await update.message.reply_text("Kullanım: /code <ne istiyorsun>")
        return
    description = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("💻 Yazılıyor...")
    response = ai_assistant.generate_code(chat_id, description)
    await send_long_message(update, response)


async def cmd_explain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if update.message.reply_to_message:
        code = update.message.reply_to_message.text
    elif context.args:
        code = " ".join(context.args)
    else:
        await update.message.reply_text("Bir koda reply yaparak /explain yazın")
        return
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("🔍 Analiz ediliyor...")
    response = ai_assistant.explain_code(chat_id, code)
    await send_long_message(update, response)


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if update.message.reply_to_message:
        text = update.message.reply_to_message.text
    elif context.args:
        text = " ".join(context.args)
    else:
        await update.message.reply_text("Kullanım: /translate <metin>")
        return
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("🌐 Çevriliyor...")
    response = ai_assistant.translate(chat_id, text)
    await send_long_message(update, response)


async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /compare X vs Y")
        return
    text = " ".join(context.args)
    parts = re.split(r"\s+vs\.?\s+", text, flags=re.IGNORECASE)
    if len(parts) < 2:
        await update.message.reply_text("'vs' ile ayırın: /compare X vs Y")
        return
    await update.message.reply_text("⚖️ Karşılaştırılıyor...")
    response = ai_assistant.compare_repos(parts[0], parts[1])
    await send_long_message(update, response)


async def cmd_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if update.message.reply_to_message:
        text = update.message.reply_to_message.text
    elif context.args:
        text = " ".join(context.args)
    else:
        await update.message.reply_text("Bir metne reply yaparak /summarize yazın")
        return
    await update.message.reply_text("📝 Özetleniyor...")
    response = ai_assistant.summarize_text(text)
    await send_long_message(update, response)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    chat_id = str(update.effective_chat.id)
    ai_assistant.clear_context(chat_id)
    await update.message.reply_text("🧹 Sohbet geçmişi temizlendi.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fotoğraf analizi."""
    from agents import ai_assistant

    await update.message.reply_text("🔍 Görsel analiz ediliyor...")

    photo = update.message.photo[-1]  # En yüksek çözünürlük
    file = await context.bot.get_file(photo.file_id)

    # Dosyayı indir
    photo_bytes = await file.download_as_bytearray()

    # Caption varsa prompt olarak kullan
    prompt = update.message.caption

    response = ai_assistant.analyze_image(bytes(photo_bytes), prompt)
    await send_long_message(update, response)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dosya analizi."""
    from agents import ai_assistant

    doc = update.message.document
    filename = doc.file_name

    # Sadece metin dosyaları
    if not any(
        filename.endswith(ext)
        for ext in [".txt", ".py", ".js", ".md", ".json", ".csv", ".html", ".css"]
    ):
        await update.message.reply_text("Sadece metin dosyaları destekleniyor.")
        return

    await update.message.reply_text("📄 Dosya analiz ediliyor...")

    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    content = file_bytes.decode("utf-8", errors="ignore")

    response = ai_assistant.analyze_document(content, filename)
    await send_long_message(update, response)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ses mesajı işle - hem anla hem sesli yanıt ver."""
    from agents import voice_assistant, ai_assistant, learning_tracker
    import tempfile

    await update.message.reply_text("🎤 Ses mesajı işleniyor...")

    chat_id = str(update.effective_chat.id)

    try:
        # Ses dosyasını indir
        voice = update.message.voice or update.message.audio
        file = await context.bot.get_file(voice.file_id)

        # Geçici dosyaya kaydet
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            audio_path = tmp.name

        # 1. Sesi metne çevir
        transcript = voice_assistant.transcribe_audio_whisper(audio_path)

        if not transcript or transcript.startswith("["):
            await update.message.reply_text(f"❌ Ses anlaşılamadı: {transcript}")
            return

        # Transkripti göster
        await update.message.reply_text(f'📝 Anladığım: "{transcript}"')

        # 2. Öğrenme takibi
        learning_tracker.track_interaction(chat_id, transcript, "voice")

        # 3. AI yanıtı al
        await update.message.reply_text("🤔 Düşünüyorum...")
        response = ai_assistant.ask(chat_id, transcript)

        # 4. Yazılı yanıtı gönder
        await send_long_message(update, response)

        # 5. Sesli yanıt oluştur (kısa yanıtlar için)
        if len(response) < 2000:
            await update.message.reply_text("🎙️ Sesli yanıt hazırlanıyor...")
            voice_path = await voice_assistant.text_to_speech_async(response)

            if voice_path:
                with open(voice_path, "rb") as audio:
                    await update.message.reply_voice(
                        voice=audio, caption="🎙️ Sesli Yanıt"
                    )

                # Geçici dosyayı sil
                import os

                os.unlink(voice_path)

        # Orijinal ses dosyasını sil
        import os

        os.unlink(audio_path)

    except Exception as e:
        await update.message.reply_text(f"❌ Ses işleme hatası: {str(e)}")


async def cmd_voice_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Günlük brifingi sesli olarak gönder."""
    from agents import voice_assistant

    await update.message.reply_text("🎙️ Sesli brifing hazırlanıyor...")

    try:
        voice_path = await voice_assistant.create_voice_briefing()

        if voice_path:
            with open(voice_path, "rb") as audio:
                await update.message.reply_voice(
                    voice=audio, caption="🎙️ Günlük Teknoloji Brifing - JARVIS"
                )
        else:
            await update.message.reply_text(
                "❌ Brifing bulunamadı. Önce /generate ile oluşturun."
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Sesli brifing hatası: {str(e)}")


async def cmd_speak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Metni sesli olarak oku."""
    from agents import voice_assistant

    if not context.args:
        # Reply edilen mesajı oku
        if update.message.reply_to_message:
            text = update.message.reply_to_message.text
        else:
            await update.message.reply_text(
                "Kullanım: /speak <metin> veya bir mesaja reply yaparak /speak"
            )
            return
    else:
        text = " ".join(context.args)

    await update.message.reply_text("🎙️ Ses oluşturuluyor...")

    try:
        voice_path = await voice_assistant.text_to_speech_async(text)

        if voice_path:
            with open(voice_path, "rb") as audio:
                await update.message.reply_voice(voice=audio)

            import os

            os.unlink(voice_path)
        else:
            await update.message.reply_text("❌ Ses oluşturulamadı.")

    except Exception as e:
        await update.message.reply_text(f"❌ TTS hatası: {str(e)}")


async def cmd_voice_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ses ayarlarını göster/değiştir."""
    from agents import voice_assistant

    if not context.args:
        voices = voice_assistant.format_voice_list()
        await update.message.reply_text(voices)
    else:
        # TODO: Ses tercihini kaydet
        voice_id = context.args[0]
        await update.message.reply_text(f"✅ Ses değiştirildi: {voice_id}")


# ============== REPO TAKİP ==============


async def cmd_watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import repo_watcher

    if not context.args:
        await update.message.reply_text("Kullanım: /watch owner/repo")
        return
    repo = context.args[0]
    chat_id = str(update.effective_chat.id)
    response = repo_watcher.watch_repo(chat_id, repo)
    await update.message.reply_text(response)


async def cmd_unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import repo_watcher

    if not context.args:
        await update.message.reply_text("Kullanım: /unwatch <repo>")
        return
    chat_id = str(update.effective_chat.id)
    response = repo_watcher.unwatch_repo(chat_id, context.args[0])
    await update.message.reply_text(response)


async def cmd_watches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import repo_watcher

    chat_id = str(update.effective_chat.id)
    response = repo_watcher.list_watches(chat_id)
    await update.message.reply_text(response)


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import repo_watcher

    if not context.args:
        await update.message.reply_text("Kullanım: /alert <keyword>")
        return
    keyword = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    response = repo_watcher.add_alert(chat_id, keyword)
    await update.message.reply_text(response)


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import repo_watcher

    chat_id = str(update.effective_chat.id)
    response = repo_watcher.list_alerts(chat_id)
    await update.message.reply_text(response)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import ai_assistant

    if not context.args:
        await update.message.reply_text("Kullanım: /analyze <github-url>")
        return
    await update.message.reply_text("🔬 Analiz ediliyor...")
    response = ai_assistant.analyze_repo(context.args[0])
    await send_long_message(update, response)


# ============== ARAÇLAR ==============


async def cmd_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    if not context.args:
        await update.message.reply_text("Kullanım: /bookmark <url> [başlık]")
        return
    url = context.args[0]
    title = " ".join(context.args[1:]) if len(context.args) > 1 else None
    chat_id = str(update.effective_chat.id)
    db.add_bookmark(chat_id, url, title)
    await update.message.reply_text(f"🔖 Kaydedildi!")


async def cmd_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    chat_id = str(update.effective_chat.id)
    bookmarks = db.get_bookmarks(chat_id)
    if not bookmarks:
        await update.message.reply_text("Bookmark yok.")
        return
    text = "🔖 Bookmarklar\n━━━━━━━━━━━━━━\n\n"
    for b in bookmarks[:15]:
        title = b.get("title") or b["url"][:40]
        text += f"• {title}\n  {b['url']}\n\n"
    await send_long_message(update, text)


async def cmd_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    if not context.args:
        await update.message.reply_text("Kullanım: /note <not>")
        return
    content = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    db.add_note(chat_id, content)
    await update.message.reply_text("📝 Kaydedildi!")


async def cmd_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    chat_id = str(update.effective_chat.id)
    notes = db.get_notes(chat_id)
    if not notes:
        await update.message.reply_text("Not yok.")
        return
    text = "📝 Notlar\n━━━━━━━━━━\n\n"
    for n in notes[:15]:
        text += f"• {n['content'][:80]}\n\n"
    await send_long_message(update, text)


async def cmd_snippet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    if not context.args:
        await update.message.reply_text("/snippet save <isim> veya /snippet <isim>")
        return
    chat_id = str(update.effective_chat.id)
    if context.args[0] == "save" and len(context.args) >= 2:
        if update.message.reply_to_message:
            code = update.message.reply_to_message.text
            db.save_snippet(chat_id, context.args[1], code)
            await update.message.reply_text(f"💾 '{context.args[1]}' kaydedildi!")
        else:
            await update.message.reply_text("Koda reply yapın.")
    else:
        snippet = db.get_snippet(chat_id, context.args[0])
        if snippet:
            await update.message.reply_text(f"```\n{snippet['code']}\n```")
        else:
            await update.message.reply_text("Snippet bulunamadı.")


async def cmd_snippets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    chat_id = str(update.effective_chat.id)
    snippets = db.get_all_snippets(chat_id)
    if not snippets:
        await update.message.reply_text("Snippet yok.")
        return
    text = "📋 Snippetlar\n━━━━━━━━━━━━\n\n"
    for s in snippets:
        text += f"• {s['name']}\n"
    await update.message.reply_text(text)


# ============== ZAMANLAYICI ==============


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /remind <dakika> <mesaj>")
        return
    try:
        minutes = int(context.args[0])
    except:
        await update.message.reply_text("Geçersiz dakika.")
        return
    message = " ".join(context.args[1:])
    chat_id = str(update.effective_chat.id)
    remind_at = datetime.now() + timedelta(minutes=minutes)
    db.add_reminder(chat_id, message, remind_at)
    await update.message.reply_text(f"⏰ {minutes} dakika sonra hatırlatılacak!")


async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import db

    chat_id = str(update.effective_chat.id)
    reminders = db.get_user_reminders(chat_id)
    if not reminders:
        await update.message.reply_text("Bekleyen hatırlatıcı yok.")
        return
    text = "⏰ Hatırlatıcılar\n━━━━━━━━━━━━━━━\n\n"
    for r in reminders:
        text += f"• {r['message']}\n"
    await update.message.reply_text(text)


async def cmd_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    chat_id = str(update.effective_chat.id)

    if context.args:
        if context.args[0] == "stop":
            response = utilities.stop_pomodoro(chat_id)
        else:
            try:
                minutes = int(context.args[0])
                result = utilities.start_pomodoro(chat_id, minutes)
                response = result["message"]
            except:
                response = "Kullanım: /pomodoro <dakika> veya /pomodoro stop"
    else:
        response = utilities.get_pomodoro_status(chat_id)

    await update.message.reply_text(response)


# ============== UTILITY ==============


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    if not context.args:
        await update.message.reply_text("Kullanım: /weather <şehir>")
        return
    city = " ".join(context.args)
    await update.message.reply_text("🌤️ Kontrol ediliyor...")
    response = utilities.get_weather(city)
    await update.message.reply_text(response)


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    if not context.args:
        await update.message.reply_text("Kullanım: /price <btc/eth/usd/eur>")
        return
    symbol = context.args[0].lower()
    if symbol in ["usd", "eur", "gbp", "try"]:
        response = utilities.get_exchange_rate(symbol.upper())
    else:
        response = utilities.get_crypto_price(symbol)
    await update.message.reply_text(response)


async def cmd_shorten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    if not context.args:
        await update.message.reply_text("Kullanım: /shorten <url>")
        return
    response = utilities.shorten_url(context.args[0])
    await update.message.reply_text(response)


async def cmd_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    if not context.args:
        await update.message.reply_text("Kullanım: /qr <metin>")
        return
    text = " ".join(context.args)
    qr_url = utilities.generate_qr_url(text)
    await update.message.reply_photo(photo=qr_url, caption=f"QR: {text[:50]}")


# ============== KEŞİF ==============


async def cmd_discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import discovery

    await update.message.reply_text("🔮 Keşfediliyor...")
    if context.args:
        response = discovery.discover_by_topic(" ".join(context.args))
    else:
        response = discovery.discover_repo()
    await send_long_message(update, response)


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import discovery

    chat_id = str(update.effective_chat.id)

    if context.args and context.args[0].upper() in ["A", "B", "C", "D"]:
        if chat_id in quiz_cache:
            result = discovery.check_quiz_answer(quiz_cache[chat_id], context.args[0])
            del quiz_cache[chat_id]
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("Aktif quiz yok. /quiz")
        return

    await update.message.reply_text("🎯 Quiz hazırlanıyor...")
    quiz = discovery.generate_quiz()
    quiz_cache[chat_id] = quiz
    text = discovery.format_quiz(quiz)
    await update.message.reply_text(text)


async def cmd_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import discovery

    quote = discovery.get_motivation()
    await update.message.reply_text(quote)


# ============== VERİ ==============


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    chat_id = str(update.effective_chat.id)
    response = utilities.get_user_stats(chat_id)
    await update.message.reply_text(response)


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("📦 Export hazırlanıyor...")

    filename, content = utilities.export_all(chat_id)

    await update.message.reply_document(
        document=InputFile(io.BytesIO(content), filename=filename),
        caption="📦 Tüm verileriniz",
    )


async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    if not context.args:
        await update.message.reply_text("Kullanım: /goal <hedef>")
        return
    goal = " ".join(context.args)
    chat_id = str(update.effective_chat.id)
    response = utilities.add_goal(chat_id, goal)
    await update.message.reply_text(response)


async def cmd_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import utilities

    chat_id = str(update.effective_chat.id)
    response = utilities.get_goals(chat_id)
    await update.message.reply_text(response)


# ============== YENİ ÖZELLİKLER ==============


async def cmd_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalık trend raporu."""
    from agents import weekly_report

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("📊 Haftalık rapor hazırlanıyor...")

    try:
        report = weekly_report.generate_weekly_report(chat_id)
        text = weekly_report.format_weekly_report_text(report)
        await send_long_message(update, text)
    except Exception as e:
        await update.message.reply_text(f"❌ Rapor hatası: {str(e)}")


async def cmd_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aylık trend raporu."""
    from agents import weekly_report

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("📅 Aylık rapor hazırlanıyor...")

    try:
        report = weekly_report.generate_monthly_report(chat_id)
        text = weekly_report.format_monthly_report_text(report)
        await send_long_message(update, text)
    except Exception as e:
        await update.message.reply_text(f"❌ Rapor hatası: {str(e)}")


async def cmd_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İlgi alanlarını yönet."""
    from agents import db

    chat_id = str(update.effective_chat.id)

    if not context.args:
        # Mevcut ilgi alanlarını göster
        prefs = db.get_user_preferences(chat_id)
        if prefs and prefs.get("interests"):
            interests = ", ".join(prefs["interests"])
            languages = ", ".join(prefs.get("languages", []))
            text = f"""🎯 İLGİ ALANLARIN
━━━━━━━━━━━━━━━━
📌 Konular: {interests or "Yok"}
💻 Diller: {languages or "Yok"}

Ekle: /interests add python ai
Sil: /interests remove python"""
        else:
            text = """🎯 Henüz ilgi alanı eklememişsin!

Ekle: /interests add python rust ai
Örnek konular: python, rust, ai, llm, web, devops"""
        await update.message.reply_text(text)
        return

    action = context.args[0].lower()

    if action == "add" and len(context.args) > 1:
        for interest in context.args[1:]:
            db.add_user_interest(chat_id, interest.lower())
        await update.message.reply_text(f"✅ Eklendi: {', '.join(context.args[1:])}")

    elif action == "remove" and len(context.args) > 1:
        for interest in context.args[1:]:
            db.remove_user_interest(chat_id, interest.lower())
        await update.message.reply_text(f"✅ Silindi: {', '.join(context.args[1:])}")

    elif action == "lang" and len(context.args) > 1:
        prefs = db.get_user_preferences(chat_id)
        languages = prefs.get("languages", []) if prefs else []
        languages.extend([l.title() for l in context.args[1:]])
        db.save_user_preferences(chat_id, languages=list(set(languages)))
        await update.message.reply_text(
            f"✅ Dil eklendi: {', '.join(context.args[1:])}"
        )

    else:
        await update.message.reply_text(
            "Kullanım: /interests add|remove|lang <konular>"
        )


async def cmd_personalized_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kişiselleştirilmiş feed."""
    from agents import personalized_feed

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("📰 Feed hazırlanıyor...")

    try:
        text = personalized_feed.get_feed_summary(chat_id)
        await send_long_message(update, text)
    except Exception as e:
        await update.message.reply_text(f"❌ Feed hatası: {str(e)}")


async def cmd_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proaktif öneriler."""
    from agents import proactive_suggestions

    chat_id = str(update.effective_chat.id)

    try:
        suggestion = proactive_suggestions.get_daily_suggestion(chat_id)
        if suggestion:
            await update.message.reply_text(suggestion)
        else:
            await update.message.reply_text(
                "💡 Şu an için öneri yok. Biraz daha etkileşime gir!"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Öneri hatası: {str(e)}")


async def cmd_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Öğrenme takibi."""
    from agents import learning_tracker

    chat_id = str(update.effective_chat.id)

    if context.args and context.args[0] == "stats":
        # İstatistikler
        stats = learning_tracker.get_learning_stats(chat_id)
        text = learning_tracker.format_learning_stats(stats)
    elif context.args and context.args[0] == "quiz":
        # Quiz sorusu
        quiz = learning_tracker.generate_quiz_question(chat_id)
        if quiz:
            text = f"🧠 Quiz: {quiz['topic'].title()}\n\n{quiz['question']}"
        else:
            text = "Quiz için yeterli veri yok. Biraz daha soru sor!"
    else:
        # Haftalık özet
        text = learning_tracker.get_learning_summary(chat_id)

    await send_long_message(update, text)


async def cmd_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Akıllı bildirimleri göster."""
    from agents import db

    chat_id = str(update.effective_chat.id)

    notifications = db.get_unread_notifications(chat_id)

    if not notifications:
        await update.message.reply_text("🔔 Okunmamış bildirim yok!")
        return

    text = f"🔔 {len(notifications)} BİLDİRİM\n━━━━━━━━━━━━━━━━\n\n"

    for notif in notifications[:10]:
        emoji = {
            "star_milestone": "⭐",
            "security": "🚨",
            "release": "📦",
            "trending": "🔥",
        }.get(notif["notification_type"], "🔔")

        text += f"{emoji} {notif['message'][:100]}...\n\n"

    # Okundu olarak işaretle
    db.mark_notifications_read(chat_id)

    await send_long_message(update, text)


async def cmd_roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import extra_features

    if not context.args:
        await update.message.reply_text(
            "Kullanım: /roadmap <konu>\nÖrnek: /roadmap Python"
        )
        return
    topic = " ".join(context.args)
    await update.message.reply_text(f"🗺️ {topic} için yol haritası hazırlanıyor...")
    response = extra_features.generate_roadmap(topic)
    await send_long_message(update, response)


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import extra_features

    difficulty = context.args[0].lower() if context.args else None
    if difficulty and difficulty not in ["kolay", "orta", "zor"]:
        await update.message.reply_text("Zorluk: kolay, orta, zor\nÖrnek: /daily orta")
        return
    await update.message.reply_text("🎯 Challenge hazırlanıyor...")
    challenge = extra_features.get_daily_challenge(difficulty)
    text = extra_features.format_daily_challenge(challenge)
    await send_long_message(update, text)


async def cmd_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import extra_features

    await update.message.reply_text("😂 Meme aranıyor...")
    meme = extra_features.get_programming_meme()
    try:
        await update.message.reply_photo(
            photo=meme["url"], caption=f"😂 {meme['title']}"
        )
    except Exception:
        await update.message.reply_text(f"😂 {meme['title']}\n\n{meme['url']}")


async def cmd_wisdom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import extra_features

    wisdom = extra_features.get_wisdom_quote()
    text = extra_features.format_wisdom_quote(wisdom)
    await update.message.reply_text(text)


async def cmd_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import extra_features

    length = 16
    if context.args:
        try:
            length = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Geçersiz uzunluk. Örnek: /password 24")
            return
    pwd = extra_features.generate_password(length)
    text = extra_features.format_password(pwd)
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from agents import extra_features

    chat_id = str(update.effective_chat.id)
    if context.args:
        try:
            minutes = int(context.args[0])
            response = extra_features.schedule_coffee_reminder(chat_id, minutes)
            await update.message.reply_text(response)
        except ValueError:
            await update.message.reply_text("Geçersiz dakika. Örnek: /coffee 45")
    else:
        text = extra_features.get_coffee_reminder()
        await update.message.reply_text(text)


# ============== BOT KURULUMU ==============


def create_bot_application() -> Application:
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN ayarlanmamış!")

    app = Application.builder().token(BOT_TOKEN).build()

    # Temel
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))

    # Brifing
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("trending", cmd_trending))

    # AI
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("code", cmd_code))
    app.add_handler(CommandHandler("explain", cmd_explain))
    app.add_handler(CommandHandler("translate", cmd_translate))
    app.add_handler(CommandHandler("compare", cmd_compare))
    app.add_handler(CommandHandler("summarize", cmd_summarize))
    app.add_handler(CommandHandler("clear", cmd_clear))

    # Repo
    app.add_handler(CommandHandler("watch", cmd_watch))
    app.add_handler(CommandHandler("unwatch", cmd_unwatch))
    app.add_handler(CommandHandler("watches", cmd_watches))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(CommandHandler("analyze", cmd_analyze))

    # Araçlar
    app.add_handler(CommandHandler("bookmark", cmd_bookmark))
    app.add_handler(CommandHandler("bookmarks", cmd_bookmarks))
    app.add_handler(CommandHandler("note", cmd_note))
    app.add_handler(CommandHandler("notes", cmd_notes))
    app.add_handler(CommandHandler("snippet", cmd_snippet))
    app.add_handler(CommandHandler("snippets", cmd_snippets))

    # Zamanlayıcı
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("reminders", cmd_reminders))
    app.add_handler(CommandHandler("pomodoro", cmd_pomodoro))

    # Utility
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("shorten", cmd_shorten))
    app.add_handler(CommandHandler("qr", cmd_qr))

    # Keşif
    app.add_handler(CommandHandler("discover", cmd_discover))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("motivation", cmd_motivation))

    # Veri
    app.add_handler(CommandHandler("mystats", cmd_mystats))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("goal", cmd_goal))
    app.add_handler(CommandHandler("goals", cmd_goals))

    # YENİ ÖZELLİKLER
    app.add_handler(CommandHandler("weekly", cmd_weekly_report))
    app.add_handler(CommandHandler("monthly", cmd_monthly_report))
    app.add_handler(CommandHandler("interests", cmd_interests))
    app.add_handler(CommandHandler("feed", cmd_personalized_feed))
    app.add_handler(CommandHandler("suggest", cmd_suggestions))
    app.add_handler(CommandHandler("learning", cmd_learning))
    app.add_handler(CommandHandler("notifications", cmd_notifications))

    # SESLİ ASİSTAN
    app.add_handler(CommandHandler("voicebriefing", cmd_voice_briefing))
    app.add_handler(CommandHandler("speak", cmd_speak))
    app.add_handler(CommandHandler("voice", cmd_voice_settings))

    # EXTRA FEATURES
    app.add_handler(CommandHandler("roadmap", cmd_roadmap))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("meme", cmd_meme))
    app.add_handler(CommandHandler("wisdom", cmd_wisdom))
    app.add_handler(CommandHandler("password", cmd_password))
    app.add_handler(CommandHandler("coffee", cmd_coffee))

    # Fotoğraf, dosya ve ses
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    return app


async def send_briefing_standalone():
    if not BOT_TOKEN:
        return False
    chat_id = get_chat_id()
    if not chat_id:
        return False

    app = Application.builder().token(BOT_TOKEN).build()
    report_path = REPORTS_DIR / "final_report.md"
    if not report_path.exists():
        return False

    content = report_path.read_text(encoding="utf-8")

    async with app:
        parts = []
        current = ""
        for line in content.split("\n"):
            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            parts.append(current)

        for part in parts:
            await app.bot.send_message(chat_id=chat_id, text=part.strip())
            await asyncio.sleep(0.3)

    return True


def run_bot():
    print("🤖 JARVIS başlatılıyor...")
    app = create_bot_application()
    print("Bot hazır! /start ile başlayın.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def send_briefing_sync():
    return asyncio.run(send_briefing_standalone())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--send":
        send_briefing_sync()
    else:
        run_bot()
