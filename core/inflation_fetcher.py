# -*- coding: utf-8 -*-
import pandas as pd
import requests
import urllib3
from datetime import datetime, timedelta

# Senin Anahtarın
SABIT_API_KEY = "5bWXZH7oXM"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class InflationFetcher:
    def __init__(self, api_key=None):
        if api_key and len(api_key) > 5:
            self.api_key = api_key
        else:
            self.api_key = SABIT_API_KEY

    def fetch_inflation_data(self, start_date_obj=None, end_date_obj=None):
        """
        TAM KARNE MODU (FIXED):
        NaN (Boş) verileri temizler ve tarih formatını bozulmaz hale getirir.
        """
        
        if not end_date_obj:
            end_date_obj = datetime.now()
        if not start_date_obj:
            start_date_obj = end_date_obj - timedelta(days=365)

        # Geçmiş veri ihtiyacı (Hesaplamalar için 2 yıl geriye git)
        api_start_date = start_date_obj - pd.DateOffset(years=2)
        
        str_api_start = api_start_date.strftime("%d-%m-%Y")
        str_api_end = end_date_obj.strftime("%d-%m-%Y")

        url = (
            f"https://evds2.tcmb.gov.tr/service/evds/"
            f"series=TP.FG.J0"
            f"&startDate={str_api_start}"
            f"&endDate={str_api_end}"
            f"&type=json"
            f"&aggregationTypes=avg"
            f"&formulas=0"
            f"&frequency=1"
        )

        headers = {
            "key": self.api_key,
            "User-Agent": "Mozilla/5.0"
        }

        try:
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    print("❌ HATA: Liste boş.")
                    return pd.DataFrame()

                df = pd.DataFrame(items)
                df = df.iloc[:, 0:2]
                df.columns = ["Date", "Index_Value"]

                # 1. TEMİZLİK
                def clean_number(x):
                    x = str(x)
                    if ',' in x:
                        return x.replace('.', '').replace(',', '.')
                    return x

                df["Index_Value"] = df["Index_Value"].apply(clean_number)
                df["Index_Value"] = pd.to_numeric(df["Index_Value"], errors='coerce')
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
                
                df = df.dropna().sort_values("Date")
                
                # 2. HESAPLAMALAR
                # Aylık (MoM)
                df["Aylık Enflasyon"] = df["Index_Value"].pct_change() * 100
                
                # Yıllık (YoY)
                df["Yıllık Enflasyon"] = df["Index_Value"].pct_change(periods=12) * 100
                
                # 12 Aylık Ortalamalar
                df["Rolling_Mean_12"] = df["Index_Value"].rolling(window=12).mean()
                df["12 Aylık Ort. Değ."] = df["Rolling_Mean_12"].pct_change(periods=12) * 100
                
                # YTD (Yılbaşına Göre)
                df["Yıl"] = df["Date"].dt.year
                aralik_degerleri = df[df["Date"].dt.month == 12].set_index("Yıl")["Index_Value"]
                df["Onceki_Yil"] = df["Yıl"] - 1
                df["Ref_Aralik"] = df["Onceki_Yil"].map(aralik_degerleri)
                df["Yılbaşına Göre"] = (df["Index_Value"] / df["Ref_Aralik"] - 1) * 100

                # 3. FİLTRELEME (Kullanıcının Tarihine Dön)
                target_start = pd.to_datetime(start_date_obj)
                df = df[df["Date"] >= target_start]
                
                # --- KRİTİK FIX: NaN TEMİZLİĞİ ---
                # pct_change ilk satırı NaN yapar, bu da grafikleri bozar.
                # dropna() ile temizliyoruz.
                df = df.dropna(subset=["Aylık Enflasyon"]) 
                
                final_df = df[[
                    "Date", 
                    "Aylık Enflasyon", 
                    "Yılbaşına Göre", 
                    "Yıllık Enflasyon", 
                    "12 Aylık Ort. Değ."
                ]].copy()
                
                # Simülasyon için "Oran" sütunu (Aylık Enflasyon baz alınır)
                final_df["Oran"] = final_df["Aylık Enflasyon"]
                
                # Tarih sütunu string değil, datetime kalsın (App.py'da sorun yaşamamak için)
                final_df["Tarih"] = final_df["Date"] 
                
                # Yuvarlama
                cols = ["Aylık Enflasyon", "Yılbaşına Göre", "Yıllık Enflasyon", "12 Aylık Ort. Değ.", "Oran"]
                final_df[cols] = final_df[cols].round(2)
                
                print(f"✅ BAŞARILI: {len(final_df)} aylık veri hazır (NaN temizlendi).")
                return final_df
            
            else:
                print(f"⚠️ Hata Kodu: {response.status_code}")
                return pd.DataFrame()

        except Exception as e:
            print(f"☠️ HATA: {e}")
            return pd.DataFrame()