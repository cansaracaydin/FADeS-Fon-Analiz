# -*- coding: utf-8 -*-
import pandas as pd
import time
import random
from datetime import datetime, timedelta, date
import undetected_chromedriver as uc
import json
import sys

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
                # options.add_argument("--headless") # Görmek için kapalı tutuyoruz
                
                self.driver = uc.Chrome(options=options, use_subprocess=True)
                self.driver.set_page_load_timeout(60)
                
                # Siteye Git
                print(f"🌍 TEFAS'a bağlanılıyor... (Deneme: {deneme+1})")
                self.driver.get("https://www.tefas.gov.tr/TarihselVeriler.aspx")
                
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
            print("❌ KRİTİK HATA: Chrome açılamadı!")

    def fetch_data(self, fund_code, start_date, end_date):
        """
        Fiyat verilerini 90 günlük parçalar halinde çeker.
        """
        if not self.driver: 
            print("❌ Driver yok, işlem iptal.")
            return pd.DataFrame()

        print(f"\n🔍 {fund_code} için veri isteniyor: {start_date} -> {end_date}")

        all_data_frames = []
        
        # --- TARİH FORMATI GARANTİLEME ---
        # Gelen veri datetime objesi mi, string mi? Hepsini datetime yapalım.
        try:
            if isinstance(start_date, (datetime, date)):
                current_date = pd.to_datetime(start_date)
            else:
                current_date = pd.to_datetime(start_date) # String ise çevir
            
            if isinstance(end_date, (datetime, date)):
                target_end_date = pd.to_datetime(end_date)
            else:
                target_end_date = pd.to_datetime(end_date)

        except Exception as e:
            print(f"❌ Tarih format hatası: {e}")
            return pd.DataFrame()

        # Döngü Başlangıcı
        while current_date <= target_end_date:
            chunk_end = current_date + timedelta(days=90)
            if chunk_end > target_end_date:
                chunk_end = target_end_date
            
            # TEFAS'ın istediği format: GG.AA.YYYY (Örn: 01.01.2023)
            s_str = current_date.strftime("%d.%m.%Y")
            e_str = chunk_end.strftime("%d.%m.%Y")
            
            print(f"   ⏳ Parça İsteği: {s_str} - {e_str} ...", end="")
            
            df_chunk = self._fetch_chunk_with_js(fund_code, s_str, e_str)
            
            if not df_chunk.empty:
                print(f" ✅ Geldi ({len(df_chunk)} satır)")
                all_data_frames.append(df_chunk)
            else:
                print(f" ⚠️ Boş döndü")
            
            current_date = chunk_end + timedelta(days=1)
            time.sleep(random.uniform(0.5, 1.0))

        # Birleştirme
        if all_data_frames:
            full_df = pd.concat(all_data_frames, ignore_index=True)
            full_df = full_df.drop_duplicates(subset=['Date'])
            print(f"🎉 TOPLAM: {len(full_df)} satır veri çekildi.")
            return full_df
        
        print("❌ HİÇ VERİ ALINAMADI (Liste boş)")
        return pd.DataFrame()

    def _fetch_chunk_with_js(self, fund_code, start_fmt, end_fmt):
        # JavaScript API Çağrısı
        js_script = f"""
        var callback = arguments[arguments.length - 1];
        var formData = "fontip=YAT&sfontur=&fonkod={fund_code.upper()}&fongrup=&bastarih={start_fmt}&bittarih={end_fmt}&fonturkod=&fonunvantip=";
        
        fetch("https://www.tefas.gov.tr/api/DB/BindHistoryInfo", {{
            method: "POST",
            headers: {{ 
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", 
                "X-Requested-With": "XMLHttpRequest" 
            }},
            body: formData
        }})
        .then(r => r.json())
        .then(d => callback(d))
        .catch(e => callback({{ "error": e.toString() }}));
        """
        try:
            result = self.driver.execute_async_script(js_script)
            
            if result and "data" in result:
                data_list = result["data"]
                # Bazen TEFAS boş liste döner
                if not data_list:
                    return pd.DataFrame()

                df = pd.DataFrame(data_list)
                if not df.empty:
                    # Sütunları yeniden adlandır
                    df = df.rename(columns={"TARIH": "Date", "FIYAT": "Price", "FONKODU": "FundCode", "FONUNVAN": "FundName"})
                    
                    # Tarih formatını (Unix Timestamp) düzelt (TEFAS 1672531200000 gibi döner)
                    if 'Date' in df.columns:
                        # Sayısal veri mi kontrol et
                        df['Date'] = pd.to_numeric(df['Date'], errors='coerce')
                        df['Date'] = pd.to_datetime(df['Date'], unit='ms') # Milisaniye -> Tarih
                        
                    return df
            
            return pd.DataFrame()

        except Exception as e:
            print(f" [JS Hatası]: {e}")
            return pd.DataFrame()

    # ----------------------------------------------------------------
    # FAIL-SAFE VARLIK DAĞILIMI (ÇÖKMEZ)
    # ----------------------------------------------------------------
    def fetch_asset_allocation(self, fund_code, target_date_str):
        if not self.driver: return pd.DataFrame()

        # print(f"🔍 {fund_code} Varlık Dağılımı aranıyor...") # Çok log basmasın diye kapattım

        try:
            # Tarih string mi, datetime mı kontrol et
            if isinstance(target_date_str, str):
                end_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
            else:
                end_dt = pd.to_datetime(target_date_str) # Timestamp ise çevir

            start_dt = end_dt - timedelta(days=365) 
            s_fmt = start_dt.strftime("%d.%m.%Y")
            e_fmt = end_dt.strftime("%d.%m.%Y")

        except Exception as e:
            # print(f"❌ Tarih hatası (Asset): {e}")
            return pd.DataFrame()

        js_script = f"""
        var callback = arguments[arguments.length - 1];
        var formData = "fontip=YAT&sfontur=&fonkod={fund_code.upper()}&fongrup=&bastarih={s_fmt}&bittarih={e_fmt}&fonturkod=&fonunvantip=";
        
        fetch("https://www.tefas.gov.tr/api/DB/BindAllocationInfo", {{
            method: "POST",
            headers: {{ "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest" }},
            body: formData
        }})
        .then(r => r.text()) // Önce text al (HTML gelirse patlamasın)
        .then(text => {{
            try {{
                var json = JSON.parse(text);
                callback(json);
            }} catch (e) {{
                callback({{ "error": "JSON Parse Error" }});
            }}
        }})
        .catch(e => callback({{ "error": e.toString() }}));
        """

        try:
            result = self.driver.execute_async_script(js_script)
            
            if result and "data" in result:
                full_data = pd.DataFrame(result["data"])
                if not full_data.empty and 'TARIH' in full_data.columns:
                    # Tarihi Parse Et
                    full_data['Parsed_Date'] = pd.to_numeric(full_data['TARIH'], errors='coerce')
                    full_data['Parsed_Date'] = pd.to_datetime(full_data['Parsed_Date'], unit='ms')
                    full_data = full_data.dropna(subset=['Parsed_Date'])
                    
                    if not full_data.empty:
                        latest_date = full_data['Parsed_Date'].max()
                        latest_df = full_data[full_data['Parsed_Date'] == latest_date].copy()
                        return latest_df[["ITEM", "DEGER"]].rename(columns={"ITEM": "Varlık Türü", "DEGER": "Oran"})
            
            return pd.DataFrame()

        except: return pd.DataFrame()

    def close(self):
        try:
            if self.driver: self.driver.quit()
        except: pass