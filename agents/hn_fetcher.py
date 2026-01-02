"""
Hacker News Fetcher
Top stories ve GitHub ile eşleşen hikayeleri çeker
Makale içeriklerini de scrape eder
"""
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

HN_API = "https://hacker-news.firebaseio.com/v0"

def fetch_article_content(url: str, max_chars: int = 2000) -> dict:
    """
    Bir URL'den makale içeriğini çeker
    Returns: {"content": str, "summary": str}
    """
    if not url or url.startswith("item?id="):
        return {"content": "", "summary": ""}
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; GazeteciBot/1.0)"
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Script, style vs. kaldır
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()
        
        # Makale içeriğini bulmaya çalış (yaygın class/tag'ler)
        content = ""
        
        # Önce article tag'i dene
        article = soup.find("article")
        if article:
            content = article.get_text(separator="\n", strip=True)
        
        # Yoksa main dene
        if not content:
            main = soup.find("main")
            if main:
                content = main.get_text(separator="\n", strip=True)
        
        # Yoksa yaygın class'ları dene
        if not content:
            for class_name in ["post-content", "article-content", "entry-content", "content", "post-body"]:
                elem = soup.find(class_=class_name)
                if elem:
                    content = elem.get_text(separator="\n", strip=True)
                    break
        
        # Son çare: body'nin tamamı
        if not content:
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)
        
        # Temizle
        content = re.sub(r'\n\s*\n', '\n\n', content)  # Çoklu boşlukları azalt
        content = content[:max_chars] if len(content) > max_chars else content
        
        # İlk 500 karakterlik özet
        summary = content[:500] + "..." if len(content) > 500 else content
        
        return {
            "content": content,
            "summary": summary
        }
        
    except Exception as e:
        return {"content": "", "summary": f"(İçerik alınamadı: {str(e)[:50]})"}

def fetch_item(item_id: int) -> dict | None:
    """Tek bir HN item'ı çeker"""
    try:
        r = requests.get(f"{HN_API}/item/{item_id}.json", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fetch_top_comments(item: dict, limit: int = 5) -> list[str]:
    """Bir story'nin top yorumlarını çeker"""
    comments = []
    kids = item.get("kids", [])[:limit]
    
    for kid_id in kids:
        comment = fetch_item(kid_id)
        if comment and comment.get("text") and not comment.get("deleted"):
            # HTML taglerini temizle (basit)
            text = comment["text"]
            text = text.replace("<p>", "\n").replace("</p>", "")
            text = text.replace("<i>", "").replace("</i>", "")
            text = text.replace("<b>", "").replace("</b>", "")
            text = text.replace("<a href=", "[link:").replace("</a>", "]")
            # İlk 500 karakter
            if len(text) > 500:
                text = text[:500] + "..."
            comments.append({
                "author": comment.get("by", "anon"),
                "text": text
            })
    
    return comments

def fetch_top_stories(limit: int = 30) -> list[dict]:
    """
    HN top stories'i çeker
    GitHub linkleri olanları ve ilginç olanları döndürür
    """
    print("📰 [HN] Top stories çekiliyor...")
    
    try:
        # Top story ID'lerini al
        r = requests.get(f"{HN_API}/topstories.json", timeout=10)
        story_ids = r.json()[:limit]
    except Exception as e:
        print(f"⚠️ [HN] Top stories alınamadı: {e}")
        return []
    
    stories = []
    
    # Paralel olarak story'leri çek
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_item, sid): sid for sid in story_ids}
        
        for future in as_completed(futures):
            item = future.result()
            if item and item.get("type") == "story" and not item.get("dead"):
                stories.append(item)
    
    # Skora göre sırala
    stories.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return stories

def fetch_hn_data(github_repos: list[dict] = None) -> dict:
    """
    Ana fonksiyon: HN verilerini toplar
    
    Returns:
        {
            "top_stories": [...],  # Genel top stories
            "github_mentions": [...],  # GitHub repoları ile eşleşenler
            "tech_discussions": [...]  # Teknik tartışmalar (Show HN, programming)
        }
    """
    result = {
        "top_stories": [],
        "github_mentions": [],
        "tech_discussions": []
    }
    
    # Top stories çek
    stories = fetch_top_stories(limit=50)
    
    # GitHub repo URL'leri (eşleştirme için)
    github_urls = set()
    github_names = set()
    if github_repos:
        for repo in github_repos:
            github_urls.add(repo.get("url", "").lower())
            github_names.add(repo.get("name", "").lower())
    
    stories_with_content = 0  # İçerik çekilen story sayısı
    
    for story in stories:
        url = story.get("url", "").lower()
        title = story.get("title", "").lower()
        original_url = story.get("url", "")
        
        story_data = {
            "id": story.get("id"),
            "title": story.get("title"),
            "url": original_url,
            "score": story.get("score", 0),
            "comments": story.get("descendants", 0),
            "author": story.get("by", ""),
            "hn_link": f"https://news.ycombinator.com/item?id={story.get('id')}",
            "article_summary": ""  # Makale özeti
        }
        
        # GitHub ile eşleşme kontrolü
        is_github_match = False
        if "github.com" in url:
            # Direkt GitHub linki
            for gh_url in github_urls:
                if gh_url and gh_url in url:
                    is_github_match = True
                    break
            
            # Repo adı eşleşmesi
            if not is_github_match:
                for name in github_names:
                    if name and name.split("/")[-1] in url:
                        is_github_match = True
                        break
        
        if is_github_match:
            # Top yorumları da çek
            print(f"   💬 GitHub eşleşmesi: {story_data['title'][:50]}...")
            story_data["top_comments"] = fetch_top_comments(story, limit=3)
            result["github_mentions"].append(story_data)
        
        # Show HN veya teknik içerik
        elif any(tag in title for tag in ["show hn", "ask hn", "rust", "python", "javascript", "ai", "llm", "gpt"]):
            result["tech_discussions"].append(story_data)
        
        # Genel top stories (ilk 10) - bunların içeriğini de çek
        if len(result["top_stories"]) < 10:
            # İlk 5 story için makale içeriğini çek (rate limit için sınırlı)
            if stories_with_content < 5 and original_url and not original_url.startswith("item?id="):
                print(f"   📄 Makale içeriği çekiliyor: {story_data['title'][:40]}...")
                article = fetch_article_content(original_url, max_chars=1500)
                story_data["article_summary"] = article.get("summary", "")
                stories_with_content += 1
            
            # Top yorumları da ekle
            story_data["top_comments"] = fetch_top_comments(story, limit=3)
            result["top_stories"].append(story_data)
    
    print(f"📊 [HN] {len(result['top_stories'])} top story ({stories_with_content} içerik), {len(result['github_mentions'])} GitHub eşleşmesi, {len(result['tech_discussions'])} tech discussion")
    
    return result


if __name__ == "__main__":
    # Test
    data = fetch_hn_data()
    print("\n=== TOP STORIES ===")
    for s in data["top_stories"][:5]:
        print(f"  [{s['score']}] {s['title']}")
        if s.get("article_summary"):
            print(f"      📄 {s['article_summary'][:100]}...")
    
    print("\n=== TECH DISCUSSIONS ===")
    for s in data["tech_discussions"][:5]:
        print(f"  [{s['score']}] {s['title']}")
