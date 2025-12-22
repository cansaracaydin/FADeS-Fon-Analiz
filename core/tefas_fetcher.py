import undetected_chromedriver as uc
import pandas as pd
import time
import random
from datetime import datetime
import os

class TefasFetcher:
    def __init__(self):
        # Tarayıcı Ayarları
        options = uc.ChromeOptions()
        # options.add_argument('--headless') # Headless kapalı (TEFAS engeli için)
        
        self.driver = uc.Chrome(options=options, use_subprocess=True)
        
        # Pencereyi küçült (Rahatsız etmesin)
        try:
            self.driver.minimize_window()
        except:
            pass
            
        self.driver.set_script_timeout(45)
        self.driver.set_page_load_timeout(45)
        
        # TEFAS'a Bağlan
        self.driver.get("https://www.tefas.gov.tr/TarihselVeriler.aspx")
        
        # İnsan Taklidi (Scroll)
        time.sleep(2)
        self.driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(1)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

    def fetch_data(self, fund_code, start_date, end_date):
        start_fmt = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        end_fmt = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        
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
        .then(response => {{
            if (!response.ok) throw new Error("HTTP Hata");
            return response.json();
        }})
        .then(data => callback(data))
        .catch(error => callback({{ "error": error.toString() }}));
        """

        try:
            time.sleep(random.uniform(1.0, 2.0)) # Bekleme süresi
            result = self.driver.execute_async_script(js_script)
            
            if result and "data" in result:
                data = result["data"]
                df = pd.DataFrame(data)
                df = df.rename(columns={"TARIH": "Date", "FIYAT": "Price", "FONKODU": "FundCode", "FONUNVAN": "FundName"})
                return df
            return pd.DataFrame()

        except Exception:
            return pd.DataFrame()

    def close(self):
        # 1. Kibarca kapat
        try:
            self.driver.quit()
        except:
            pass
        
        # 2. Zorla öldür (Hata almamak için)
        try:
            if hasattr(self.driver, 'service') and self.driver.service.process:
                self.driver.service.process.kill()
        except:
            pass