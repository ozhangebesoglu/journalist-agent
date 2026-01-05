import json
import os
# Ana dizinden çalıştırıldığı için 'agents' paketinden import ediyoruz
from agents import fetcher
from agents import hn_fetcher

DATA_DIR = "data"
REPOS_FILE = os.path.join(DATA_DIR, "repos.json")
HN_FILE = os.path.join(DATA_DIR, "hn.json")

def run_collector():
    print("📥 [COLLECTOR] GitHub verileri çekiliyor...")
    
    # GitHub verilerini çek
    repos = fetcher.fetch_repos(limit=10)
    
    if not repos:
        print("❌ [COLLECTOR] GitHub verisi bulunamadı veya hata oluştu.")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    
    with open(REPOS_FILE, "w", encoding="utf-8") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)
        
    print(f"💾 [COLLECTOR] {len(repos)} repo '{REPOS_FILE}' dosyasına kaydedildi.")
    
    # Hacker News verilerini çek (GitHub repoları ile eşleştir)
    print("\n📥 [COLLECTOR] Hacker News verileri çekiliyor...")
    hn_data = hn_fetcher.fetch_hn_data(github_repos=repos)
    
    with open(HN_FILE, "w", encoding="utf-8") as f:
        json.dump(hn_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 [COLLECTOR] HN verileri '{HN_FILE}' dosyasına kaydedildi.")