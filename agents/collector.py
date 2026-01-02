import json
import os
# Ana dizinden çalıştırıldığı için 'agents' paketinden import ediyoruz
from agents import fetcher
from agents import hn_fetcher
from agents import reddit_fetcher
from agents import db
from agents import data_persister

DATA_DIR = "data"
REPOS_FILE = os.path.join(DATA_DIR, "repos.json")
HN_FILE = os.path.join(DATA_DIR, "hn.json")
REDDIT_FILE = os.path.join(DATA_DIR, "reddit.json")


def run_collector():
    # Veritabanını başlat
    print("🗄️ [COLLECTOR] Veritabanı başlatılıyor...")
    db.init_db()

    print("\n📥 [COLLECTOR] GitHub verileri çekiliyor...")

    # GitHub verilerini çek
    repos = fetcher.fetch_repos(limit=10)

    if not repos:
        print("❌ [COLLECTOR] GitHub verisi bulunamadı veya hata oluştu.")
        return

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(REPOS_FILE, "w", encoding="utf-8") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)

    print(f"💾 [COLLECTOR] {len(repos)} repo '{REPOS_FILE}' dosyasına kaydedildi.")

    # GitHub verilerini veritabanına kaydet
    print("🗄️ [COLLECTOR] GitHub verileri veritabanına kaydediliyor...")
    repo_id_map = data_persister.persist_github_repos(repos)

    # Hacker News verilerini çek (GitHub repoları ile eşleştir)
    print("\n📥 [COLLECTOR] Hacker News verileri çekiliyor...")
    hn_data = hn_fetcher.fetch_hn_data(github_repos=repos)

    with open(HN_FILE, "w", encoding="utf-8") as f:
        json.dump(hn_data, f, indent=2, ensure_ascii=False)

    print(f"💾 [COLLECTOR] HN verileri '{HN_FILE}' dosyasına kaydedildi.")

    # HN verilerini veritabanına kaydet
    print("🗄️ [COLLECTOR] HN verileri veritabanına kaydediliyor...")
    data_persister.persist_hn_data(hn_data, repo_id_map)

    # Reddit verilerini çek (GitHub repoları ile eşleştir)
    print("\n📥 [COLLECTOR] Reddit verileri çekiliyor...")
    reddit_data = reddit_fetcher.fetch_reddit_data(github_repos=repos)

    with open(REDDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(reddit_data, f, indent=2, ensure_ascii=False)

    print(f"💾 [COLLECTOR] Reddit verileri '{REDDIT_FILE}' dosyasına kaydedildi.")

    # Reddit verilerini veritabanına kaydet
    print("🗄️ [COLLECTOR] Reddit verileri veritabanına kaydediliyor...")
    data_persister.persist_reddit_data(reddit_data, repo_id_map)

    print("\n✅ [COLLECTOR] Tüm veriler toplandı ve kaydedildi.")
