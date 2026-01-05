import os
import json
from dotenv import load_dotenv
from google import genai 

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash" 

# Dosya yolları
REPOS_PATH = "data/repos.json"
HN_PATH = "data/hn.json"
DRAFT_PATH = "data/draft.md"
FEEDBACK_PATH = "data/feedback.json"

def run_writer():
    if not os.path.exists(REPOS_PATH):
        print("❌ [WRITER] Veri dosyası bulunamadı. Collector çalışmadı mı?")
        return

    with open(REPOS_PATH, encoding="utf-8") as f:
        repos = json.load(f)
    
    # Hacker News verileri
    hn_data = {}
    if os.path.exists(HN_PATH):
        with open(HN_PATH, encoding="utf-8") as f:
            hn_data = json.load(f)

    # Feedback kontrolü ve Enjeksiyonu
    feedback_instruction = ""
    if os.path.exists(FEEDBACK_PATH):
        with open(FEEDBACK_PATH, encoding="utf-8") as f:
            fb = json.load(f)
            # Feedback'i daha görünür ve emir kipiyle ekliyoruz
            feedback_instruction = f"""
            ⚠️ Bay Stark'tan geri bildirim geldi:
            {json.dumps(fb.get('issues'), ensure_ascii=False)}
            
            Lütfen bu sefer daha dikkatli ol JARVIS. Kısa, öz ve esprili tut.
            """
            print("✍️ [WRITER] Geri bildirim algılandı, revizyon yapılıyor...")
    else:
        print("✍️ [WRITER] İlk taslak yazılıyor...")

    prompt = f"""
    Sen JARVIS'sin – Tony Stark'ın yapay zeka asistanı. Zeki, kısa, öz ve hafif alaycısın.
    Görevin: GitHub ve Hacker News'den trend olan projeleri analiz edip, geliştiricilere günlük brifing vermek.

    📦 GITHUB VERİSİ (README, dosya listesi, topics dahil): 
    {json.dumps(repos, ensure_ascii=False)}

    📰 HACKER NEWS VERİSİ:
    - Top Stories: {json.dumps(hn_data.get('top_stories', []), ensure_ascii=False)}
    - GitHub Eşleşmeleri (bu projeler HN'de de konuşulmuş!): {json.dumps(hn_data.get('github_mentions', []), ensure_ascii=False)}
    - Tech Discussions: {json.dumps(hn_data.get('tech_discussions', []), ensure_ascii=False)}

    {feedback_instruction}

    JARVIS KURALLARI:
    1. **Varsayım yapma!** README'ye ve gerçek verilere dayan.
    2. **HN verisi varsa kullan!** "Bu proje HN'de 342 puan almış, topluluk şöyle diyor..." gibi.
    3. **Kısa tut.** Her proje için 1-2 cümle yeter.
    4. **Samimi ol.** "Efendim", "dikkatinizi çekerim" gibi JARVIS ibareleri kullan.
    5. **Espritüel ol.** Hafif iğnelemeler, zekice yorumlar yap.
    6. **Emoji kullan** ama abartma.

    FORMAT:
    # ☕ Günün Tech Brifing'i
    
    Günaydın efendim. İşte bugün tech dünyasında neler dönmüş:

    ## ⭐ Günün Yıldızı: [Proje Adı]
    [Somut bilgi + neden önemli. HN'de konuşulduysa bahset.]

    ## 🔥 Hacker News'de Gündem
    [HN top stories'den 3-5 ilginç şeyi kısaca özetle. Puan ve yorum sayısı ver.]

    ## 📋 GitHub'da Dikkat Çekenler  
    - **[Proje]** ([Dil]): [1 cümle özet + esprili yorum]
    - ... (kısa kısa devam)

    ## 💬 Topluluk Ne Diyor?
    [Eğer github_mentions varsa, HN yorumlarından ilginç olanları özetle. "Bir geliştirici şöyle demiş..." gibi.]

    ## 🎯 Bugünün Dersi
    [1-2 cümlelik genel insight. JARVIS tarzı kapanış.]
    
    ---
    _Başka bir şey var mı efendim?_
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    with open(DRAFT_PATH, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print(f"📝 [WRITER] Taslak '{DRAFT_PATH}' dosyasına kaydedildi.")

if __name__ == "__main__":
    run_writer()