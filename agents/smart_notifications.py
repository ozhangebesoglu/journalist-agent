"""
Smart Notifications - Akıllı Bildirim Sistemi

Özellikler:
    - Star milestone bildirimleri (1K, 5K, 10K, 50K, 100K)
    - Güvenlik açığı tespiti (GitHub Advisory)
    - Breaking change / major release bildirimleri
    - Trending repo bildirimleri
"""

import os
import re
import requests
from datetime import datetime, timedelta

from agents import db

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
} if GITHUB_TOKEN else {}

# Star milestones
MILESTONES = [100, 500, 1000, 5000, 10000, 25000, 50000, 100000]


def check_star_milestones() -> list[dict]:
    """
    Takip edilen repo'larda star milestone kontrolü yap.
    
    Returns:
        Bildirim listesi
    """
    notifications = []
    watched = db.get_all_watched_repos()
    
    for watch in watched:
        try:
            repo_name = watch["repo_name"]
            last_stars = watch.get("last_stars", 0) or 0
            
            # GitHub'dan güncel star sayısını al
            current_stars = get_repo_stars(repo_name)
            if current_stars is None:
                continue
            
            # Milestone kontrolü
            for milestone in MILESTONES:
                if last_stars < milestone <= current_stars:
                    message = format_milestone_notification(repo_name, milestone, current_stars)
                    notifications.append({
                        "chat_id": watch["chat_id"],
                        "type": "star_milestone",
                        "repo": repo_name,
                        "message": message,
                        "milestone": milestone
                    })
                    
                    # DB'ye kaydet
                    db.add_smart_notification(
                        watch["chat_id"],
                        "star_milestone",
                        message,
                        repo_name
                    )
            
            # Son star sayısını güncelle
            if current_stars != last_stars:
                db.update_watched_repo(watch["id"], stars=current_stars)
                
        except Exception as e:
            print(f"[ERROR] Milestone check failed for {watch.get('repo_name')}: {e}")
    
    return notifications


def check_security_advisories() -> list[dict]:
    """
    Takip edilen repo'larda güvenlik açığı kontrolü yap.
    
    Returns:
        Güvenlik bildirimi listesi
    """
    notifications = []
    watched = db.get_all_watched_repos()
    
    for watch in watched:
        try:
            repo_name = watch["repo_name"]
            advisories = get_security_advisories(repo_name)
            
            for advisory in advisories:
                # Son 24 saatte yayınlanan
                published = advisory.get("published_at", "")
                if is_recent(published, hours=24):
                    severity = advisory.get("severity", "unknown")
                    summary = advisory.get("summary", "Güvenlik açığı tespit edildi")
                    
                    message = format_security_notification(repo_name, severity, summary)
                    notifications.append({
                        "chat_id": watch["chat_id"],
                        "type": "security",
                        "repo": repo_name,
                        "message": message,
                        "severity": severity
                    })
                    
                    db.add_smart_notification(
                        watch["chat_id"],
                        "security",
                        message,
                        repo_name
                    )
                    
        except Exception as e:
            print(f"[ERROR] Security check failed for {watch.get('repo_name')}: {e}")
    
    return notifications


def check_new_releases() -> list[dict]:
    """
    Takip edilen repo'larda yeni release kontrolü yap.
    Breaking change içeren major release'leri bildir.
    
    Returns:
        Release bildirimi listesi
    """
    notifications = []
    watched = db.get_all_watched_repos()
    
    for watch in watched:
        try:
            repo_name = watch["repo_name"]
            last_release = watch.get("last_release")
            
            # GitHub'dan son release'i al
            release = get_latest_release(repo_name)
            if not release:
                continue
            
            tag = release.get("tag_name", "")
            
            # Yeni release var mı?
            if tag and tag != last_release:
                is_major = is_major_release(last_release, tag)
                body = release.get("body", "")
                has_breaking = detect_breaking_changes(body)
                
                if is_major or has_breaking:
                    message = format_release_notification(
                        repo_name, tag, is_major, has_breaking, body[:200]
                    )
                    notifications.append({
                        "chat_id": watch["chat_id"],
                        "type": "release",
                        "repo": repo_name,
                        "message": message,
                        "tag": tag,
                        "is_major": is_major,
                        "has_breaking": has_breaking
                    })
                    
                    db.add_smart_notification(
                        watch["chat_id"],
                        "release",
                        message,
                        repo_name
                    )
                
                # Son release'i güncelle
                db.update_watched_repo(watch["id"], release=tag)
                
        except Exception as e:
            print(f"[ERROR] Release check failed for {watch.get('repo_name')}: {e}")
    
    return notifications


def check_trending_alerts(chat_id: str = None) -> list[dict]:
    """
    Trending repo bildirimleri oluştur.
    Kullanıcının ilgi alanlarına göre filtrelenir.
    
    Returns:
        Trending bildirimi listesi
    """
    notifications = []
    
    # Trending repo'ları al
    from agents.fetcher import fetch_trending_repos
    trending = fetch_trending_repos(since="daily")
    
    if not trending:
        return notifications
    
    # Her kullanıcı için kontrol et
    all_chats = get_all_chat_ids()
    
    for cid in all_chats:
        if chat_id and cid != chat_id:
            continue
            
        prefs = db.get_user_preferences(cid)
        if not prefs or not prefs.get("notification_enabled", True):
            continue
        
        interests = prefs.get("interests", [])
        languages = prefs.get("languages", [])
        min_stars = prefs.get("min_stars", 100)
        
        for repo in trending[:10]:
            # Filtrele
            if repo.get("stars", 0) < min_stars:
                continue
            
            repo_lang = (repo.get("lang") or "").lower()
            repo_desc = (repo.get("desc") or "").lower()
            repo_name = (repo.get("name") or "").lower()
            
            # Dil eşleşmesi
            lang_match = not languages or any(
                l.lower() == repo_lang for l in languages
            )
            
            # İlgi alanı eşleşmesi
            interest_match = not interests or any(
                i in repo_desc or i in repo_name for i in interests
            )
            
            if lang_match and interest_match:
                message = format_trending_notification(repo)
                notifications.append({
                    "chat_id": cid,
                    "type": "trending",
                    "repo": repo["name"],
                    "message": message
                })
                
                db.add_smart_notification(cid, "trending", message, repo["name"])
                break  # Kullanıcı başına bir bildirim
    
    return notifications


# ============ Helper Functions ============

def get_repo_stars(repo_name: str) -> int | None:
    """GitHub'dan repo star sayısını al."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo_name}",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("stargazers_count")
    except:
        pass
    return None


def get_security_advisories(repo_name: str) -> list[dict]:
    """GitHub Security Advisories al."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo_name}/security-advisories",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return []


def get_latest_release(repo_name: str) -> dict | None:
    """GitHub'dan son release'i al."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo_name}/releases/latest",
            headers=HEADERS,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def is_recent(timestamp: str, hours: int = 24) -> bool:
    """Timestamp son N saat içinde mi?"""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return datetime.now(dt.tzinfo) - dt < timedelta(hours=hours)
    except:
        return False


def is_major_release(old_tag: str, new_tag: str) -> bool:
    """Semver major version değişikliği var mı?"""
    if not old_tag:
        return False
    
    def extract_major(tag):
        match = re.search(r'v?(\d+)', tag)
        return int(match.group(1)) if match else 0
    
    return extract_major(new_tag) > extract_major(old_tag)


def detect_breaking_changes(release_notes: str) -> bool:
    """Release notes'ta breaking change var mı?"""
    if not release_notes:
        return False
    
    keywords = [
        "breaking change", "breaking:", "BREAKING",
        "backwards-incompatible", "backward-incompatible",
        "migration required", "deprecated and removed"
    ]
    
    notes_lower = release_notes.lower()
    return any(kw.lower() in notes_lower for kw in keywords)


def get_all_chat_ids() -> list[str]:
    """Tüm aktif chat ID'lerini al."""
    from pathlib import Path
    chat_file = Path(__file__).parent.parent / "data" / "telegram_chat_id.txt"
    if chat_file.exists():
        return [chat_file.read_text().strip()]
    return []


# ============ Notification Formatters ============

def format_milestone_notification(repo: str, milestone: int, current: int) -> str:
    """Star milestone bildirimi formatla."""
    emoji = "🌟" if milestone >= 10000 else "⭐" if milestone >= 1000 else "✨"
    return f"""{emoji} Milestone Ulaşıldı!

📦 {repo}
🎯 {milestone:,} yıldız eşiğini geçti!
📊 Şu an: {current:,} ⭐

Tebrikler! Bu proje popülerleşiyor."""


def format_security_notification(repo: str, severity: str, summary: str) -> str:
    """Güvenlik bildirimi formatla."""
    emoji = "🚨" if severity == "critical" else "⚠️" if severity == "high" else "⚡"
    return f"""{emoji} Güvenlik Uyarısı!

📦 {repo}
🔴 Seviye: {severity.upper()}
📋 {summary[:150]}

Lütfen güncelleme yapın."""


def format_release_notification(repo: str, tag: str, is_major: bool, has_breaking: bool, notes: str) -> str:
    """Release bildirimi formatla."""
    emoji = "🚀" if is_major else "📦"
    warning = "⚠️ BREAKING CHANGES içeriyor!" if has_breaking else ""
    
    return f"""{emoji} Yeni Release!

📦 {repo}
🏷️ Version: {tag}
{warning}

{notes[:200]}..."""


def format_trending_notification(repo: dict) -> str:
    """Trending repo bildirimi formatla."""
    return f"""🔥 Trending Repo!

📦 {repo['name']}
⭐ {repo.get('stars', 0):,} yıldız
📝 {repo.get('desc', 'Açıklama yok')[:100]}

İlgi alanlarınıza uygun yeni bir proje!"""


# ============ All-in-one Check ============

def run_all_checks() -> list[dict]:
    """Tüm akıllı bildirim kontrollerini çalıştır."""
    all_notifications = []
    
    print("[INFO] Checking star milestones...")
    all_notifications.extend(check_star_milestones())
    
    print("[INFO] Checking security advisories...")
    all_notifications.extend(check_security_advisories())
    
    print("[INFO] Checking new releases...")
    all_notifications.extend(check_new_releases())
    
    print(f"[INFO] Total notifications: {len(all_notifications)}")
    return all_notifications


if __name__ == "__main__":
    # Test
    notifications = run_all_checks()
    for n in notifications:
        print(f"\n{'='*40}")
        print(f"Type: {n['type']}")
        print(f"Repo: {n.get('repo', 'N/A')}")
        print(n['message'])
