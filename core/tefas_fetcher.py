import undetected_chromedriver as uc
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import os

class TefasFetcher:
    def __init__(self):
        print("🔧 Chrome Tarayıcısı Hazırlanıyor...")
        
        self.driver = None
        
        # --- GÜVENLİ AÇILIŞ DÖNGÜSÜ ---
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
                break 
                
            except Exception as e:
                print(f"⚠️ Chrome açılırken hata oldu: {e}")
                if self.driver:
                    try: self.driver.quit()
                    except: pass
                time.sleep(2)
        
        if self.driver is None:
            raise Exception("❌ Chrome 3 denemeye rağmen açılamadı! Lütfen 'taskkill' komutunu çalıştırın.")

    def fetch_data(self, fund_code, start_date, end_date):
        if not self.driver: return pd.DataFrame()

        all_data_frames = []
        
        # String tarihleri datetime objesine çevir
        try:
            current_date = datetime.strptime(start_date, "%Y-%m-%d")
            target_end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return pd.DataFrame()

        # --- PARÇALAMA DÖNGÜSÜ (CHUNKING) ---
        # Tarih aralığı bitene kadar 90'ar gün ilerle
        while current_date <= target_end_date:
            # 90 gün sonrasını hesapla
            chunk_end = current_date + timedelta(days=90)
            
            # Eğer hesaplanan bitiş, hedef tarihten büyükse, hedefte dur
            if chunk_end > target_end_date:
                chunk_end = target_end_date
            
            # API için tarih formatı: Gün.Ay.Yıl
            s_str = current_date.strftime("%d.%m.%Y")
            e_str = chunk_end.strftime("%d.%m.%Y")
            
            # Parça veriyi çekmek için yardımcı fonksiyonu çağır
            df_chunk = self._fetch_chunk_with_js(fund_code, s_str, e_str)
            
            if not df_chunk.empty:
                all_data_frames.append(df_chunk)
            
            # Bir sonraki döngü için başlangıcı 1 gün ileri at
            current_date = chunk_end + timedelta(days=1)
            
            # Siteyi yormamak için kısa bekleme
            time.sleep(random.uniform(0.5, 1.0))

        # --- BİRLEŞTİRME ---
        if all_data_frames:
            full_df = pd.concat(all_data_frames, ignore_index=True)
            # Çakışan tarihleri temizle
            full_df = full_df.drop_duplicates(subset=['Date'])
            return full_df
        
        return pd.DataFrame()

    def _fetch_chunk_with_js(self, fund_code, start_fmt, end_fmt):
        """
        Tek bir 90 günlük parçayı JavaScript enjeksiyonu ile çeken gizli fonksiyon.
        """
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
            result = self.driver.execute_async_script(js_script)
            
            if result and "data" in result:
                df = pd.DataFrame(result["data"])
                if not df.empty:
                    return df.rename(columns={"TARIH": "Date", "FIYAT": "Price", "FONKODU": "FundCode", "FONUNVAN": "FundName"})
            return pd.DataFrame()
        except Exception as e:
            print(f"Parça veri hatası ({start_fmt}-{end_fmt}): {e}")
            return pd.DataFrame()

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass