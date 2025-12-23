import undetected_chromedriver as uc
import pandas as pd
import time
import random
from datetime import datetime
import os

class TefasFetcher:
    def __init__(self):
        print("🔧 Chrome Tarayıcısı Hazırlanıyor...")
        
        self.driver = None
        
        # --- GÜVENLİ AÇILIŞ DÖNGÜSÜ ---
        # Chrome bazen ilk seferde açılmazsa, 3 kereye kadar tekrar dener.
        for deneme in range(3):
            try:
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                # options.add_argument("--headless") # Arka planda çalışsın istersen aç
                
                self.driver = uc.Chrome(options=options, use_subprocess=True)
                self.driver.set_page_load_timeout(60)
                
                # Siteye Git
                print(f"🌍 TEFAS'a bağlanılıyor... (Deneme: {deneme+1})")
                self.driver.get("https://www.tefas.gov.tr/TarihselVeriler.aspx")
                
                # Sayfanın oturması için bekle
                time.sleep(3)
                print("✅ Bağlantı Başarılı.")
                break # Başarılıysa döngüden çık
                
            except Exception as e:
                print(f"⚠️ Chrome açılırken hata oldu: {e}")
                # Eğer açıldıysa ama bozuksa kapat
                if self.driver:
                    try: self.driver.quit()
                    except: pass
                time.sleep(2) # Biraz bekle tekrar dene
        
        if self.driver is None:
            raise Exception("❌ Chrome 3 denemeye rağmen açılamadı! Lütfen 'taskkill' komutunu çalıştırın.")

    def fetch_data(self, fund_code, start_date, end_date):
        if not self.driver: return pd.DataFrame()

        start_fmt = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        end_fmt = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        
        js_script = f"""
        var callback = arguments[arguments.length - 1];
        var formData = "fontip=YAT&sfontur=&fonkod={fund_code.upper()}&fongrup=&bastarih={start_fmt}&bittarih={end_fmt}&fonturkod=&fonunvantip=";
        
        fetch("https://www.tefas.gov.tr/api/DB/BindHistoryInfo", {{
            method: "POST",
            headers: {{ "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest" }},
            body: formData
        }}).then(r => r.json()).then(d => callback(d)).catch(e => callback({{ "error": e.toString() }}));
        """

        try:
            # Çok hızlı istek atıp siteyi yormamak için kısa bekleme
            time.sleep(random.uniform(0.5, 1.5))
            
            result = self.driver.execute_async_script(js_script)
            
            if result and "data" in result:
                df = pd.DataFrame(result["data"])
                if not df.empty:
                    # İŞTE DÜZELTİLEN SATIR BURASI:
                    return df.rename(columns={"TARIH": "Date", "FIYAT": "Price", "FONKODU": "FundCode", "FONUNVAN": "FundName"})
            return pd.DataFrame()
        except Exception as e:
            print(f"Veri çekme hatası ({fund_code}): {e}")
            return pd.DataFrame()

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass