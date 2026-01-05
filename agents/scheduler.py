"""
Scheduler - Zamanlanmış görevler ve bildirimler

Görevler:
    - Günlük brifing oluşturma ve gönderme
    - Hatırlatıcı bildirimleri
    - Pomodoro bildirimleri
    - Repo takip kontrolleri
"""

import os
import signal
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

load_dotenv()

# Config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEFAULT_HOUR = int(os.getenv("BRIEFING_HOUR", "9"))
DEFAULT_MINUTE = int(os.getenv("BRIEFING_MINUTE", "0"))


async def send_telegram_message(chat_id: str, text: str):
    """Telegram mesajı gönder."""
    if not BOT_TOKEN:
        print(f"[WARN] Bot token yok, mesaj gönderilemedi: {text[:50]}...")
        return

    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"[ERROR] Telegram mesaj hatası: {e}")


async def check_reminders():
    """Bekleyen hatırlatıcıları kontrol et ve gönder."""
    from agents import db

    try:
        reminders = db.get_pending_reminders()

        for reminder in reminders:
            chat_id = reminder["chat_id"]
            message = reminder["message"]

            text = f"⏰ Hatırlatıcı!\n\n{message}"
            await send_telegram_message(chat_id, text)

            db.mark_reminder_sent(reminder["id"])
            print(f"[INFO] Hatırlatıcı gönderildi: {chat_id}")

    except Exception as e:
        print(f"[ERROR] Reminder kontrol hatası: {e}")


async def check_pomodoros():
    """Biten pomodoroları kontrol et ve bildir."""
    from agents import utilities

    try:
        finished = utilities.get_finished_pomodoros()

        for session in finished:
            chat_id = session["chat_id"]

            if session["type"] == "work":
                text = "🍅 Pomodoro tamamlandı!\n\n☕ Mola zamanı. 5 dakika dinlen.\n\n/pomodoro 5 ile mola başlat"
            else:
                text = "☕ Mola bitti!\n\n🍅 Çalışmaya devam!\n\n/pomodoro 25 ile yeni pomodoro başlat"

            await send_telegram_message(chat_id, text)
            print(f"[INFO] Pomodoro bildirimi gönderildi: {chat_id}")

    except Exception as e:
        print(f"[ERROR] Pomodoro kontrol hatası: {e}")


async def check_watched_repos():
    """Takip edilen repoları kontrol et."""
    from agents import repo_watcher

    try:
        notifications = repo_watcher.check_all_watches()

        for notif in notifications:
            await send_telegram_message(notif["chat_id"], notif["message"])
            print(f"[INFO] Repo bildirimi: {notif['repo']}")

    except Exception as e:
        print(f"[ERROR] Repo kontrol hatası: {e}")


async def check_smart_notifications():
    """Akıllı bildirimleri kontrol et (milestone, security, release)."""
    from agents import smart_notifications

    try:
        notifications = smart_notifications.run_all_checks()

        for notif in notifications:
            await send_telegram_message(notif["chat_id"], notif["message"])
            print(f"[INFO] Smart bildirim: {notif['type']} - {notif.get('repo', 'N/A')}")

    except Exception as e:
        print(f"[ERROR] Smart notification hatası: {e}")


async def send_daily_suggestions():
    """Günlük proaktif öneriler gönder."""
    from agents import proactive_suggestions
    from agents.telegram_bot import get_chat_id

    try:
        chat_id = get_chat_id()
        if not chat_id:
            return

        suggestion = proactive_suggestions.get_daily_suggestion(chat_id)
        if suggestion:
            await send_telegram_message(chat_id, f"💡 Günlük Öneri\n\n{suggestion}")
            print(f"[INFO] Günlük öneri gönderildi")

    except Exception as e:
        print(f"[ERROR] Öneri hatası: {e}")


async def send_weekly_summary():
    """Haftalık öğrenme özeti gönder."""
    from agents import learning_tracker, weekly_report
    from agents.telegram_bot import get_chat_id

    try:
        chat_id = get_chat_id()
        if not chat_id:
            return

        # Öğrenme özeti
        learning_summary = learning_tracker.get_learning_summary(chat_id)
        
        # Haftalık trend raporu
        report = weekly_report.generate_weekly_report(chat_id)
        trend_summary = weekly_report.format_weekly_report_text(report)

        full_message = f"📚 HAFTALIK ÖZET\n\n{learning_summary}\n\n{'='*30}\n\n{trend_summary}"
        
        await send_telegram_message(chat_id, full_message[:4000])
        print(f"[INFO] Haftalık özet gönderildi")

    except Exception as e:
        print(f"[ERROR] Haftalık özet hatası: {e}")


async def run_daily_briefing():
    """Günlük brifing oluştur ve gönder."""
    from agents import collector, writer, analyst
    from agents.telegram_bot import get_chat_id, send_briefing_sync

    print(f"\n{'='*50}")
    print(f"🕐 Günlük brifing: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    try:
        # Veri topla
        print("📡 Veriler toplanıyor...")
        collector.run_collector()

        # Yaz ve kontrol et
        max_loops = 3
        for i in range(max_loops):
            print(f"✍️ Yazılıyor... ({i+1}/{max_loops})")
            writer.run_writer()

            status = analyst.run_analyst()
            if status == "approved":
                print("✅ Onaylandı!")
                break

        # Gönder
        print("📤 Telegram'a gönderiliyor...")
        send_briefing_sync()

        print(f"✨ Brifing tamamlandı: {datetime.now().strftime('%H:%M')}")

    except Exception as e:
        print(f"❌ Brifing hatası: {e}")


def create_scheduler() -> AsyncIOScheduler:
    """Async scheduler oluştur."""
    scheduler = AsyncIOScheduler()

    # Her dakika: Hatırlatıcıları kontrol et
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(seconds=30),
        id='check_reminders',
        name='Hatırlatıcı Kontrolü'
    )

    # Her 10 saniye: Pomodoro kontrolü
    scheduler.add_job(
        check_pomodoros,
        trigger=IntervalTrigger(seconds=10),
        id='check_pomodoros',
        name='Pomodoro Kontrolü'
    )

    # Her 30 dakika: Repo kontrolü
    scheduler.add_job(
        check_watched_repos,
        trigger=IntervalTrigger(minutes=30),
        id='check_repos',
        name='Repo Takip Kontrolü'
    )

    # Her 2 saat: Akıllı bildirimler (milestone, security, release)
    scheduler.add_job(
        check_smart_notifications,
        trigger=IntervalTrigger(hours=2),
        id='smart_notifications',
        name='Akıllı Bildirimler'
    )

    # Her gün saat 10:00: Günlük öneri
    scheduler.add_job(
        send_daily_suggestions,
        trigger=CronTrigger(hour=10, minute=0),
        id='daily_suggestions',
        name='Günlük Öneriler'
    )

    # Her Pazartesi saat 09:00: Haftalık özet
    scheduler.add_job(
        send_weekly_summary,
        trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='weekly_summary',
        name='Haftalık Özet'
    )

    # Günlük brifing
    scheduler.add_job(
        run_daily_briefing,
        trigger=CronTrigger(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE),
        id='daily_briefing',
        name='Günlük Brifing'
    )

    return scheduler


async def run_scheduler_async():
    """Async scheduler çalıştır."""
    scheduler = create_scheduler()

    print(f"⏰ Scheduler başlatıldı!")
    print(f"📅 Günlük brifing: {DEFAULT_HOUR:02d}:{DEFAULT_MINUTE:02d}")
    print(f"🔔 Hatırlatıcı kontrolü: Her 30 saniye")
    print(f"🍅 Pomodoro kontrolü: Her 10 saniye")
    print(f"👀 Repo kontrolü: Her 30 dakika")
    print(f"⭐ Akıllı bildirimler: Her 2 saat")
    print(f"💡 Günlük öneri: Her gün 10:00")
    print(f"📊 Haftalık özet: Her Pazartesi 09:00")
    print(f"\n🔄 Durdurmak için Ctrl+C\n")

    scheduler.start()

    # Sonsuza kadar çalış
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\n🛑 Scheduler durduruldu.")


def run_scheduler(hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE):
    """Scheduler başlat (sync wrapper)."""
    global DEFAULT_HOUR, DEFAULT_MINUTE
    DEFAULT_HOUR = hour
    DEFAULT_MINUTE = minute

    asyncio.run(run_scheduler_async())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gazeteci Scheduler")
    parser.add_argument("--hour", type=int, default=DEFAULT_HOUR)
    parser.add_argument("--minute", type=int, default=DEFAULT_MINUTE)
    parser.add_argument("--now", action="store_true", help="Hemen brifing oluştur")

    args = parser.parse_args()

    if args.now:
        asyncio.run(run_daily_briefing())
    else:
        run_scheduler(args.hour, args.minute)
