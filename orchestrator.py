import time
# agents paketinden modülleri çağırıyoruz
from agents import collector
from agents import writer
from agents import analyst

def main():
    print("🚀 GAZETECİ AI BAŞLATILIYOR...\n")

    # ADIM 1: Veri Topla (Sadece bir kez yapılır)
    collector.run_collector()

    MAX_LOOPS = 3
    loop = 0

    # ADIM 2: Yazma ve Kontrol Döngüsü
    while loop < MAX_LOOPS:
        print(f"\n--- 🔄 DÖNGÜ {loop + 1} / {MAX_LOOPS} ---")
        
        # Yazar çalışır
        writer.run_writer()
        
        # Analist kontrol eder
        status = analyst.run_analyst()
        
        if status == "approved":
            print(f"\n✨ SÜREÇ BAŞARILI! Final rapor hazır.")
            break
        
        elif status == "revise":
            print("⚠️ Analist düzeltme istedi, yazar tekrar çalışacak...")
            loop += 1
            time.sleep(2) # API'yi yormamak için kısa bekleme
            
        else:
            print("❌ Beklenmedik bir hata oluştu.")
            break

    if loop == MAX_LOOPS:
        print("\n💀 Maksimum deneme sayısına ulaşıldı. Kalite standartları sağlanamadı.")

if __name__ == "__main__":
    main()