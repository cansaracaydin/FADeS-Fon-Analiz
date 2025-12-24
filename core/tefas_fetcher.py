import pandas as pd
import time
import random
from datetime import datetime, timedelta
import undetected_chromedriver as uc
import json

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
                # options.add_argument("--headless") # Hata ayıklarken bunu kapalı tutuyoruz
                
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
            raise Exception("❌ Chrome 3 denemeye rağmen açılamadı! Lütfen 'taskkill' komutunu çalıştırın.")

    def fetch_data(self, fund_code, start_date, end_date):
        if not self.driver: return pd.DataFrame()

        all_data_frames = []
        
        try:
            current_date = datetime.strptime(start_date, "%Y-%m-%d")
            target_end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return pd.DataFrame()

        while current_date <= target_end_date:
            chunk_end = current_date + timedelta(days=90)
            if chunk_end > target_end_date:
                chunk_end = target_end_date
            
            s_str = current_date.strftime("%d.%m.%Y")
            e_str = chunk_end.strftime("%d.%m.%Y")
            
            df_chunk = self._fetch_chunk_with_js(fund_code, s_str, e_str)
            if not df_chunk.empty:
                all_data_frames.append(df_chunk)
            
            current_date = chunk_end + timedelta(days=1)
            time.sleep(random.uniform(0.5, 1.0))

        if all_data_frames:
            full_df = pd.concat(all_data_frames, ignore_index=True)
            full_df = full_df.drop_duplicates(subset=['Date'])
            return full_df
        
        return pd.DataFrame()

    def _fetch_chunk_with_js(self, fund_code, start_fmt, end_fmt):
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
            print(f"Parça veri hatası: {e}")
            return pd.DataFrame()

    # ----------------------------------------------------------------
    # ULTIMATE DEBUG: VARLIK DAĞILIMI
    # ----------------------------------------------------------------
    def fetch_asset_allocation(self, fund_code, target_date_str):
        """
        Varlık dağılımını çekerken her adımı ekrana basar.
        """
        if not self.driver: 
            print("❌ Driver yok!")
            return pd.DataFrame()

        print(f"\n🔍 {fund_code} için Varlık Dağılımı Sorgulanıyor...")

        # 1. TARİH HESAPLAMA
        try:
            end_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
            # Aralığı 1 YILA ÇIKARIYORUZ (Garanti olsun)
            start_dt = end_dt - timedelta(days=365) 
            
            s_fmt = start_dt.strftime("%d.%m.%Y")
            e_fmt = end_dt.strftime("%d.%m.%Y")
            print(f"   📅 Tarih Aralığı: {s_fmt} - {e_fmt}")

        except Exception as e:
            print(f"   ❌ Tarih hatası: {e}")
            return pd.DataFrame()

        # 2. JS SCRIPT ÇALIŞTIRMA
        js_script = f"""
        var callback = arguments[arguments.length - 1];
        var formData = "fontip=YAT&sfontur=&fonkod={fund_code.upper()}&fongrup=&bastarih={s_fmt}&bittarih={e_fmt}&fonturkod=&fonunvantip=";
        
        console.log("İstek atılıyor: " + formData);
        
        fetch("https://www.tefas.gov.tr/api/DB/BindAllocationInfo", {{
            method: "POST",
            headers: {{ "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest" }},
            body: formData
        }})
        .then(r => r.json())
        .then(d => {{
            console.log("Veri geldi:", d);
            callback(d);
        }})
        .catch(e => {{
            console.error("Fetch hatası:", e);
            callback({{ "error": e.toString() }});
        }});
        """

        try:
            result = self.driver.execute_async_script(js_script)
            
            # --- DEBUG: HAM VERİYİ GÖSTER ---
            # Veri çok uzunsa keselim, değilse basalım
            res_str = str(result)
            if len(res_str) > 200:
                print(f"   📥 API Yanıtı (Özet): {res_str[:200]}...")
            else:
                print(f"   📥 API Yanıtı (Tam): {res_str}")

            if result and "data" in result:
                full_data = pd.DataFrame(result["data"])
                
                if not full_data.empty:
                    print(f"   ✅ {len(full_data)} satır veri döndü.")
                    
                    # Kolon İsimlerini Kontrol Et
                    cols = [c.upper() for c in full_data.columns]
                    full_data.columns = cols
                    # print(f"   🏷️ Kolonlar: {cols}")
                    
                    if 'TARIH' in full_data.columns:
                        # Tarih Parse Etme (Hem sayı hem string dene)
                        try:
                            full_data['Parsed_Date'] = pd.to_numeric(full_data['TARIH'], errors='coerce')
                            full_data['Parsed_Date'] = pd.to_datetime(full_data['Parsed_Date'], unit='ms')
                        except:
                            pass
                        
                        # String denemesi (Yedek)
                        mask = full_data['Parsed_Date'].isna()
                        if mask.any():
                            full_data.loc[mask, 'Parsed_Date'] = pd.to_datetime(full_data.loc[mask, 'TARIH'], format="%d.%m.%Y", errors='coerce')

                        full_data = full_data.dropna(subset=['Parsed_Date'])
                        
                        if full_data.empty:
                            print("   ❌ Tarih parse edilemedi (Tüm tarihler NaT).")
                            return pd.DataFrame()
                        
                        # En güncel tarihi bul
                        latest_date = full_data['Parsed_Date'].max()
                        print(f"   📅 En güncel rapor: {latest_date.strftime('%Y-%m-%d')}")
                        
                        # O güne ait veriyi al
                        latest_df = full_data[full_data['Parsed_Date'] == latest_date].copy()
                        
                        # Final dönüşü
                        final_df = latest_df[["ITEM", "DEGER"]].rename(columns={"ITEM": "Varlık Türü", "DEGER": "Oran"})
                        # print(f"   📊 Dönen Veri:\n{final_df.head()}")
                        return final_df

                    else:
                        print("   ❌ 'TARIH' kolonu bulunamadı.")
                else:
                    print("   ⚠️ Veri listesi boş ('data': []). TEFAS bu aralıkta rapor vermedi.")
            else:
                if "error" in result:
                    print(f"   ❌ JS Fetch Hatası: {result['error']}")
                else:
                    print("   ❌ API 'data' alanı döndürmedi.")
            
            return pd.DataFrame()

        except Exception as e:
            print(f"   ❌ Python Tarafında Kritik Hata: {e}")
            return pd.DataFrame()

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass