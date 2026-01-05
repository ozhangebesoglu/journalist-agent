import os
import json
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash"

DRAFT_PATH = "data/draft.md"
FEEDBACK_PATH = "data/feedback.json"
FINAL_PATH = "reports/final_report.md"

# Çıktı şemasına 'score' ekledik ki model puanlamayı gerçekten yapsın
class FeedbackSchema(BaseModel):
    score: float = Field(description="Raporun 10 üzerinden kalite puanı.")
    status: str = Field(description="Eğer puan 7.5 veya üzerindeyse 'approved', altındaysa 'revise'.")
    issues: list[str] = Field(description="Eğer reddedildiyse kritik hatalar. Onaylandıysa boş bırak.")

def run_analyst():
    if not os.path.exists(DRAFT_PATH):
        return "error"

    with open(DRAFT_PATH, encoding="utf-8") as f:
        draft = f.read()

    prompt = f"""
    Sen Tony Stark'sın. JARVIS'in yazdığı brifing'i değerlendiriyorsun.
    
    Brifing kısa, öz ve eğlenceli mi? Sıkıcı kurumsal rapor gibi mi yoksa JARVIS gibi mi konuşuyor?
    
    TASLAK:
    {draft}
    
    DEĞERLENDİRME:
    1. Kısa mı? (Uzun uzun anlatıyorsa puan kır)
    2. Samimi mi? (Resmi/kurumsal dil varsa puan kır)  
    3. Esprili mi? (Kuru ve sıkıcıysa puan kır)
    4. Bilgilendirici mi? (Teknik içerik var mı?)
    
    PUANLAMA:
    - **>= 7.5** → "approved" (Güzel iş JARVIS)
    - **< 7.5** → "revise" (Tekrar yaz, bu sefer daha az sıkıcı ol)
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': FeedbackSchema
        }
    )

    try:
        feedback = response.parsed
    except Exception as e:
        print(f"⚠️ JSON Parse Hatası: {e}")
        return "error"

    # Konsola puanı da yazdıralım ki ne kadar beğendiğini görelim
    print(f"📊 [ANALYST] Rapor Puanı: {feedback.score}/10")

    if feedback.status == "approved":
        os.makedirs("reports", exist_ok=True)
        with open(FINAL_PATH, "w", encoding="utf-8") as f:
            f.write(draft)
        
        if os.path.exists(FEEDBACK_PATH):
            os.remove(FEEDBACK_PATH)
            
        print("✅ [ANALYST] Rapor ONAYLANDI -> reports/final_report.md")
        return "approved"
    
    else:
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            json.dump(feedback.model_dump(), f, indent=2, ensure_ascii=False)
            
        print("🛑 [ANALYST] Rapor REDDEDİLDİ. Revizyon istendi.")
        return "revise"

if __name__ == "__main__":
    run_analyst()