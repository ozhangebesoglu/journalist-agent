"""
Repo Watcher - GitHub repo takip ve bildirim sistemi

Özellikler:
    - watch: Repo takibe al
    - unwatch: Takibi bırak
    - list_watches: Takip listesi
    - check_updates: Güncellemeleri kontrol et
"""

import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

from agents import db

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def extract_repo_info(repo_input: str) -> tuple[str, str] | None:
    """URL veya owner/repo formatından repo bilgisi çıkar."""
    # GitHub URL
    match = re.match(r'https?://github\.com/([^/]+)/([^/\s]+)', repo_input)
    if match:
        return match.group(1), match.group(2).rstrip('/')

    # owner/repo format
    match = re.match(r'^([^/\s]+)/([^/\s]+)$', repo_input.strip())
    if match:
        return match.group(1), match.group(2)

    return None


def get_repo_data(owner: str, repo: str) -> dict | None:
    """GitHub API'den repo verisi al."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def get_latest_release(owner: str, repo: str) -> dict | None:
    """Son release'i al."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def watch_repo(chat_id: str, repo_input: str) -> str:
    """Repoyu takibe al."""
    info = extract_repo_info(repo_input)
    if not info:
        return "Geçersiz repo formatı. Kullanım: /watch owner/repo veya GitHub URL"

    owner, repo = info
    repo_name = f"{owner}/{repo}"
    repo_url = f"https://github.com/{repo_name}"

    # Repo var mı kontrol et
    data = get_repo_data(owner, repo)
    if not data:
        return f"Repo bulunamadı: {repo_name}"

    stars = data.get("stargazers_count", 0)

    # Son release
    release = get_latest_release(owner, repo)
    release_tag = release.get("tag_name") if release else None

    # Kaydet
    if db.add_watched_repo(chat_id, repo_url, repo_name, stars):
        if release_tag:
            db.update_watched_repo(
                db.get_watched_repos(chat_id)[-1]["id"],
                release=release_tag
            )
        return f"""Takibe alındı: {repo_name}

⭐ {stars:,} stars
📦 Son release: {release_tag or 'Yok'}
🔗 {repo_url}

Değişiklikler olduğunda bildirim alacaksınız."""
    else:
        return f"Bu repo zaten takipte: {repo_name}"


def unwatch_repo(chat_id: str, repo_name: str) -> str:
    """Takibi bırak."""
    if db.remove_watched_repo(chat_id, repo_name):
        return f"Takipten çıkarıldı: {repo_name}"
    else:
        return f"Takipte böyle bir repo yok: {repo_name}"


def list_watches(chat_id: str) -> str:
    """Takip listesini göster."""
    watches = db.get_watched_repos(chat_id)

    if not watches:
        return "Takipte repo yok. /watch <repo> ile ekleyin."

    text = "👀 Takip Listesi\n━━━━━━━━━━━━━━\n\n"

    for w in watches:
        text += f"• {w['repo_name']}\n"
        text += f"  ⭐ {w['last_stars'] or '?'}"
        if w['last_release']:
            text += f" | 📦 {w['last_release']}"
        text += "\n\n"

    return text


def check_all_watches() -> list[dict]:
    """Tüm takipleri kontrol et, değişiklikleri döndür."""
    all_watches = db.get_all_watched_repos()
    notifications = []

    for watch in all_watches:
        info = extract_repo_info(watch['repo_url'])
        if not info:
            continue

        owner, repo = info

        # Repo verisini al
        data = get_repo_data(owner, repo)
        if not data:
            continue

        current_stars = data.get("stargazers_count", 0)
        last_stars = watch.get("last_stars") or 0

        # Star değişimi kontrol
        star_diff = current_stars - last_stars
        if star_diff >= 100:  # 100+ star artışı
            notifications.append({
                "chat_id": watch["chat_id"],
                "type": "stars",
                "repo": watch["repo_name"],
                "message": f"🌟 {watch['repo_name']} +{star_diff:,} star!\n({last_stars:,} → {current_stars:,})"
            })

        # Release kontrol
        release = get_latest_release(owner, repo)
        if release:
            current_release = release.get("tag_name")
            last_release = watch.get("last_release")

            if current_release and current_release != last_release:
                notifications.append({
                    "chat_id": watch["chat_id"],
                    "type": "release",
                    "repo": watch["repo_name"],
                    "message": f"📦 Yeni release: {watch['repo_name']}\n{current_release}\n\n{release.get('name', '')}"
                })
                db.update_watched_repo(watch["id"], release=current_release)

        # Starları güncelle
        db.update_watched_repo(watch["id"], stars=current_stars)

    return notifications


# ============ Keyword Alerts ============

def add_alert(chat_id: str, keyword: str) -> str:
    """Anahtar kelime alerti ekle."""
    if len(keyword) < 2:
        return "Anahtar kelime en az 2 karakter olmalı."

    if db.add_keyword_alert(chat_id, keyword):
        return f"Alert eklendi: '{keyword}'\n\nHN'de bu kelime geçtiğinde bildirim alacaksınız."
    else:
        return f"Bu alert zaten mevcut: '{keyword}'"


def remove_alert(chat_id: str, keyword: str) -> str:
    """Alerti kaldır."""
    if db.remove_keyword_alert(chat_id, keyword):
        return f"Alert kaldırıldı: '{keyword}'"
    else:
        return f"Böyle bir alert yok: '{keyword}'"


def list_alerts(chat_id: str) -> str:
    """Alertleri listele."""
    alerts = db.get_keyword_alerts(chat_id)

    if not alerts:
        return "Alert yok. /alert <keyword> ile ekleyin."

    text = "🔔 Keyword Alerts\n━━━━━━━━━━━━━━━\n\n"
    for keyword in alerts:
        text += f"• {keyword}\n"

    return text


def check_keyword_alerts(stories: list[dict]) -> list[dict]:
    """HN hikayelerinde keyword ara, eşleşmeleri döndür."""
    all_alerts = db.get_all_keyword_alerts()
    notifications = []

    for alert in all_alerts:
        keyword = alert["keyword"].lower()
        chat_id = alert["chat_id"]

        for story in stories:
            title = story.get("title", "").lower()
            url = story.get("url", "").lower()

            if keyword in title or keyword in url:
                notifications.append({
                    "chat_id": chat_id,
                    "type": "keyword",
                    "keyword": keyword,
                    "message": f"🔔 Alert: '{alert['keyword']}'\n\n{story.get('title')}\n{story.get('url', story.get('hn_link', ''))}"
                })

    return notifications


if __name__ == "__main__":
    # Test
    print(watch_repo("test", "anthropics/claude-code"))
