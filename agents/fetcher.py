import os
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}"
}

def fetch_readme(repo_name: str) -> str:
    """Repo'nun README dosyasını çeker (max 2000 karakter)"""
    url = f"https://api.github.com/repos/{repo_name}/readme"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            # İlk 2000 karakter yeterli, token tasarrufu
            return content[:2000] if len(content) > 2000 else content
    except:
        pass
    return ""

def fetch_topics(repo_name: str) -> list:
    """Repo'nun topics/tag'lerini çeker"""
    url = f"https://api.github.com/repos/{repo_name}/topics"
    headers = {**HEADERS, "Accept": "application/vnd.github.mercy-preview+json"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("names", [])
    except:
        pass
    return []

def fetch_tree(repo_name: str) -> list:
    """Repo'nun kök dizinindeki dosyaları listeler"""
    url = f"https://api.github.com/repos/{repo_name}/contents"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            files = [item["name"] for item in r.json() if item["type"] == "file"]
            return files[:15]  # Max 15 dosya
    except:
        pass
    return []

def fetch_repos(limit=10):
    """Trend repoları detaylı bilgilerle çeker"""
    last_week = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    url = (
        "https://api.github.com/search/repositories"
        f"?q=created:>{last_week}&sort=stars&order=desc&per_page={limit}"
    )
    
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        items = r.json().get("items", [])
        
        repos = []
        for i in items:
            repo_name = i["full_name"]
            print(f"   📦 {repo_name} analiz ediliyor...")
            
            repos.append({
                "name": repo_name,
                "stars": i["stargazers_count"],
                "desc": i.get("description") or "Açıklama yok",
                "url": i["html_url"],
                "lang": i.get("language") or "Belirtilmemiş",
                "topics": fetch_topics(repo_name),
                "files": fetch_tree(repo_name),
                "readme": fetch_readme(repo_name)
            })
        
        return repos
        
    except Exception as e:
        print(f"⚠️ Hata (Fetcher): {e}")
        return []