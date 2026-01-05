"""
Gazeteci Orchestrator - Ana giriş noktası

Kullanım:
    python orchestrator.py                    # Normal çalıştırma
    python orchestrator.py --telegram         # Brifing sonrası Telegram'a gönder
    python orchestrator.py --daemon           # Bot + Scheduler modunda çalış
    python orchestrator.py --bot              # Sadece Telegram bot'u çalıştır
    python orchestrator.py --hour 9 --minute 0  # Scheduler saatini ayarla
"""

import argparse
import time

from agents import collector, writer, analyst


def run_pipeline(send_telegram: bool = False):
    """Ana brifing pipeline'ını çalıştır."""
    print("🚀 GAZETECİ AI BAŞLATILIYOR...\n")

    # ADIM 1: Veri Topla (Sadece bir kez yapılır)
    collector.run_collector()

    MAX_LOOPS = 3
    loop = 0
    approved = False

    # ADIM 2: Yazma ve Kontrol Döngüsü
    while loop < MAX_LOOPS:
        print(f"\n--- 🔄 DÖNGÜ {loop + 1} / {MAX_LOOPS} ---")

        # Yazar çalışır
        writer.run_writer()

        # Analist kontrol eder
        status = analyst.run_analyst()

        if status == "approved":
            print(f"\n✨ SÜREÇ BAŞARILI! Final rapor hazır.")
            approved = True
            break

        elif status == "revise":
            print("⚠️ Analist düzeltme istedi, yazar tekrar çalışacak...")
            loop += 1
            time.sleep(2)  # API'yi yormamak için kısa bekleme

        else:
            print("❌ Beklenmedik bir hata oluştu.")
            break

    if loop == MAX_LOOPS:
        print("\n💀 Maksimum deneme sayısına ulaşıldı. Kalite standartları sağlanamadı.")

    # ADIM 3: Telegram'a gönder (opsiyonel)
    if send_telegram:
        print("\n📤 Telegram'a gönderiliyor...")
        from agents.telegram_bot import send_briefing_sync
        send_briefing_sync()

    return approved


def main():
    parser = argparse.ArgumentParser(
        description="Gazeteci - AI Tech Briefing Sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python orchestrator.py                    Normal çalıştırma
  python orchestrator.py --telegram         Telegram'a gönder
  python orchestrator.py --daemon           Bot + Scheduler
  python orchestrator.py --bot              Sadece bot
  python orchestrator.py --daemon --hour 8  Saat 08:00'de çalış
        """
    )

    parser.add_argument(
        "--telegram", "-t",
        action="store_true",
        help="Brifing sonrası Telegram'a gönder"
    )

    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Daemon modunda çalış (Bot + Scheduler)"
    )

    parser.add_argument(
        "--bot", "-b",
        action="store_true",
        help="Sadece Telegram bot'u çalıştır (komut dinle)"
    )

    parser.add_argument(
        "--hour",
        type=int,
        default=9,
        help="Scheduler saati (varsayılan: 9)"
    )

    parser.add_argument(
        "--minute",
        type=int,
        default=0,
        help="Scheduler dakikası (varsayılan: 0)"
    )

    args = parser.parse_args()

    if args.daemon:
        # Daemon modu: Bot başlat + Scheduler + Keep-alive (Render için)
        print("🤖 Daemon modu başlatılıyor...")
        print("   Bot komutları dinlenecek")
        print(f"   Günlük brifing: {args.hour:02d}:{args.minute:02d}\n")

        # Veritabanı tablolarını oluştur
        from agents.db import init_db
        init_db()
        print("   ✅ Veritabanı hazır")

        # Render.com için keep-alive sunucusu
        try:
            from keep_alive import keep_alive
            keep_alive()
        except ImportError:
            print("   [WARN] keep_alive modülü bulunamadı, HTTP sunucu başlatılmadı")

        import threading
        from agents.telegram_bot import run_bot
        from agents.scheduler import run_scheduler

        # Scheduler'ı ayrı thread'de başlat
        scheduler_thread = threading.Thread(
            target=run_scheduler,
            args=(args.hour, args.minute),
            daemon=True
        )
        scheduler_thread.start()

        # Bot ana thread'de çalışsın
        run_bot()

    elif args.bot:
        # Sadece bot modu
        from agents.telegram_bot import run_bot
        run_bot()

    else:
        # Normal pipeline
        run_pipeline(send_telegram=args.telegram)


if __name__ == "__main__":
    main()
